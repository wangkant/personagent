"""Parsing and per-row precomputation for the few-shot retrieval datasets."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from .embeddings import text_key

logger = logging.getLogger("agent")


def _parse_jsonl(blob: bytes) -> list[dict]:
    """Parse newline-delimited JSON objects, skipping blank and malformed lines.

    Skip-the-bad-line (rather than abandoning the whole file) keeps one
    corrupted append from freezing the few-shot pool at its pre-corruption
    state."""
    out: list[dict] = []
    for ln in blob.decode("utf-8", "replace").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out

def epoch(ts) -> float:
    """ISO timestamp -> epoch seconds; 0.0 when unparsable. Naive stamps are
    read as local time, matching every other timestamp in the pipeline."""
    if not ts:
        return 0.0
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, OSError, OverflowError):
        return 0.0


def embedding_text(rec: dict) -> str:
    """What a row is embedded as: the situation it answers, not the reply."""
    ctx = rec.get("context") or []
    if not isinstance(ctx, list):
        ctx = [ctx]
    return "\n".join([str(rec.get("scenario") or ""), *(str(c) for c in ctx)])


def _retrieval_fields(rec: dict) -> tuple[str, str, float, str]:
    """Precompute what the few-shot relevance scorer needs, once per record at
    load time instead of once per record on every LLM turn: the lowercased
    scenario / context blobs the focus tokens are matched against, the
    entry's timestamp as an epoch float for the recency decay, and the key
    its embedding is cached under.

    ts_epoch is 0.0 when there is no parsable timestamp, which skips the
    recency bonus. Naive timestamps are read as local time, aware ones as
    absolute."""
    ts_epoch = epoch(rec.get("ts"))
    ctx = rec.get("context") or []
    if not isinstance(ctx, list):
        ctx = [ctx]
    return (
        str(rec.get("scenario") or "").lower(),
        " ".join(str(c) for c in ctx).lower(),
        ts_epoch,
        text_key(embedding_text(rec)),
    )
