"""Optional embedding vectors for retrieval: the /embeddings call and its cache.

Off unless EMBEDDING_MODEL is set. Vectors are fetched in the async path ahead
of a turn and cached in memory and on disk by model and text hash; the
ranking only ever reads the cache."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import os
import sys
from array import array
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from .storage import atomic_write_text

logger = logging.getLogger("agent")

#: Texts per request: some OpenAI-compatible providers refuse more than 10.
BATCH_SIZE = 10
#: Fits a 512-token model; a longer input is refused by some, failing its batch.
MAX_TEXT_CHARS = 500
#: The query is embedded while the turn waits for it.
QUERY_TIMEOUT_S = 3.0
BATCH_TIMEOUT_S = 30.0
#: How long a failed endpoint is left alone before the next try.
RETRY_AFTER_S = 300.0
QUERY_CACHE_SIZE = 64


def clip(text: str) -> str:
    return (text or "").strip()[:MAX_TEXT_CHARS]


def text_key(text: str) -> str:
    """Cache key of a text as it is embedded."""
    return hashlib.sha256(clip(text).encode("utf-8")).hexdigest()[:32]


def unit(values) -> array:
    vec = array("f", values)
    norm = math.sqrt(sum(x * x for x in vec))
    if not norm:
        raise ValueError("zero or empty embedding")
    return array("f", (x / norm for x in vec))


async def fetch(client, url: str, api_key: str, model: str,
                texts: list[str]) -> list[array]:
    """Unit vectors for `texts`, in order, from one OpenAI-style request."""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    resp = await client.post(url, headers=headers, json={
        "model": model, "input": [clip(t) for t in texts]})
    resp.raise_for_status()
    rows = sorted(resp.json()["data"], key=lambda row: row.get("index", 0))
    if len(rows) != len(texts):
        raise ValueError(f"{len(texts)} texts sent, {len(rows)} vectors back")
    return [unit(row["embedding"]) for row in rows]


def _encode(vec: array) -> str:
    vec = array("f", vec)
    if sys.byteorder == "big":
        vec.byteswap()
    return base64.b64encode(vec.tobytes()).decode("ascii")


def _decode(text: str) -> array:
    vec = array("f")
    vec.frombytes(base64.b64decode(text))
    if sys.byteorder == "big":
        vec.byteswap()
    return vec


def _line(model: str, key: str, vec: array) -> str:
    return json.dumps({"model": model, "key": key, "vec": _encode(vec)}) + "\n"


class EmbeddingCache:
    """Unit vectors of one model by text key, kept in memory and appended to
    a JSONL file so a restart does not re-embed. Query vectors are one-off,
    so they stay in a small in-memory LRU and never reach the file."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._model: Optional[str] = None
        self._stored: dict[str, array] = {}
        self._queries: OrderedDict[str, array] = OrderedDict()
        self._lines = 0
        self._write_warned = False

    def _load(self, model: str) -> None:
        if model == self._model:
            return
        self._model, self._stored, self._lines = model, {}, 0
        self._queries.clear()
        try:
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    self._lines += 1
                    try:
                        rec = json.loads(line)
                        if rec["model"] == model:
                            self._stored[rec["key"]] = _decode(rec["vec"])
                    except (ValueError, KeyError, TypeError):
                        continue  # a torn append costs one vector
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.warning("[Agent] embedding cache unreadable, starting empty: %s", e)

    def get(self, model: str, key: str) -> Optional[array]:
        self._load(model)
        vec = self._stored.get(key)
        return self._queries.get(key) if vec is None else vec

    def has(self, model: str, key: str) -> bool:
        return self.get(model, key) is not None

    def put(self, model: str, vectors: dict[str, array], *, persist: bool) -> None:
        self._load(model)
        if not persist:
            for key, vec in vectors.items():
                self._queries[key] = vec
                self._queries.move_to_end(key)
            while len(self._queries) > QUERY_CACHE_SIZE:
                self._queries.popitem(last=False)
            return
        self._stored.update(vectors)
        data = "".join(_line(model, k, v) for k, v in vectors.items()).encode("ascii")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND
                         | getattr(os, "O_BINARY", 0), 0o600)
            try:
                view = memoryview(data)
                while view:
                    view = view[os.write(fd, view):]
            finally:
                os.close(fd)
            self._lines += len(vectors)
        except OSError as e:
            if not self._write_warned:
                self._write_warned = True
                logger.warning("[Agent] embedding cache not saved, a restart "
                               "will re-embed: %s", e)

    def prune(self, model: str, keep: set[str]) -> None:
        """Rewrite the file with only `keep` once most of it is dead weight:
        vectors of forgotten memories, rotated rows, another model's."""
        self._load(model)
        if self._lines <= 2 * len(keep) + 100:
            return
        self._stored = {k: v for k, v in self._stored.items() if k in keep}
        try:
            atomic_write_text(self.path, "".join(
                _line(model, k, v) for k, v in self._stored.items()), fsync=False)
        except OSError as e:
            logger.warning("[Agent] embedding cache prune failed: %s", e)
        # Also on failure: the next try waits until the file has grown again.
        self._lines = len(self._stored)
