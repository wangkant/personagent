"""The durable memory files: ids, strict loading, the daily copy and the
one-time migration of memory.json. No model call and no Agent import."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
import shutil
import time
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

from .embeddings import text_key
from .storage import atomic_write_text
from .textproc import _focus_tokens

logger = logging.getLogger("agent")

#: memory_state.json's `format` once memory.json carries ids and the new fields.
FORMAT = 2
#: The untouched copy of memory.json made before the migration rewrites it.
PRE_V2_SUFFIX = ".pre-v2"
BAK_SUFFIX = ".bak"

#: Where a fact came from.
SOURCES = ("reply", "command", "fold", "migration")
#: A reply's own note, a person's command; the fold rates the rest.
IMP_REPLY, IMP_COMMAND, IMP_DEFAULT = 3, 4, 3

# The chat's own media markers, as prompt.py's focus pattern reads them.
_MARKER = re.compile(r"\[(image|sticker)(?::[^\]\x02\x03]+)?\]")


class MemoryFileDamaged(RuntimeError):
    """A durable memory file does not load; the start stops and names the
    daily copy rather than starting empty."""

    def __init__(self, path: Path):
        path = Path(path)
        bak = path.with_name(path.name + BAK_SUFFIX)
        message = f"{path.name} is damaged and was left untouched."
        if bak.is_file():
            day = datetime.fromtimestamp(bak.stat().st_mtime).strftime("%Y-%m-%d")
            message += (f" A copy from {day} is at {bak}; move it in place of "
                        f"{path.name} to start from it.")
        super().__init__(message)
        self.path = path
        self.backup = bak if bak.is_file() else None


def new_id(prefix: str, taken: Iterable[str] = ()) -> str:
    """prefix + 10 random hex characters, never one already in `taken`."""
    taken = set(taken)
    while True:
        candidate = prefix + secrets.token_hex(5)
        if candidate not in taken:
            return candidate


def legacy_id(text: str, n: int = 0) -> str:
    """The id a migrated note gets: derived from its text, so a repeated
    migration gives the same one; `n` draws again after a collision."""
    return "m" + text_key(text if not n else f"{text}#{n}")[:10]


def token_hashes(text: str) -> list[str]:
    """What a tombstone keeps of a forgotten text: hashes of its focus tokens."""
    return sorted({hashlib.sha256(tok.encode("utf-8")).hexdigest()[:16]
                   for tok in _focus_tokens(str(text or ""), "zh")})


def relax_markers(text: str) -> str:
    """[image:...] and [sticker] as plain words, so an event or a summary that
    mentions one passes the bracket rule of the memory validator."""
    return _MARKER.sub(lambda m: f"({m.group(1)})", str(text or ""))


def fill_fields(row: dict, src: str, imp: int, taken: Iterable[str] = (),
                now: Optional[float] = None) -> dict:
    """Give a new note the fields this version keeps; existing values stay."""
    now = time.time() if now is None else now
    row.setdefault("time", now)
    if "id" not in row:
        row["id"] = new_id("m", taken)
    row.setdefault("imp", imp)
    row.setdefault("uses", 0)
    row.setdefault("used", 0.0)
    row.setdefault("src", src)
    row.setdefault("born", float(row.get("time") or now))
    return row


def readable_row(row) -> bool:
    return isinstance(row, dict) and isinstance(row.get("text"), str)


def _read_strict(path: Path, shape: Callable[[object], bool]):
    """JSON from a durable file; None when it is absent, MemoryFileDamaged
    when it is not JSON or not the expected shape."""
    path = Path(path)
    try:
        blob = path.read_bytes()
    except FileNotFoundError:
        return None
    try:
        data = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MemoryFileDamaged(path) from exc
    if not shape(data):
        raise MemoryFileDamaged(path)
    return data


def load_memory_file(path: Path) -> dict:
    """memory.json as {conv: [row, ...]}; missing is {}. Rows are not checked
    here (see `drop_unreadable`)."""
    data = _read_strict(path, lambda d: isinstance(d, dict) and all(
        isinstance(v, list) for v in d.values()))
    return {} if data is None else data


def load_core_file(path: Path) -> dict:
    """core_memory.json as {conv: text}; a value that is not text is dropped
    (it could never have been written by the agent)."""
    data = _read_strict(path, lambda d: isinstance(d, dict))
    if data is None:
        return {}
    return {str(k): v for k, v in data.items() if isinstance(v, str)}


def save_json(path: Path, obj) -> None:
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


def daily_backup(path: Path, state) -> bool:
    """Copy `path` to `<name>.bak` before its first write of a local day.
    `state` is the MemoryState that remembers the day per file."""
    path = Path(path)
    today = date.today().isoformat()
    days = state.data.setdefault("bak_day", {})
    if not isinstance(days, dict):
        days = state.data["bak_day"] = {}
    if days.get(path.name) == today:
        return False
    made = False
    if path.is_file():
        try:
            shutil.copy2(path, path.with_name(path.name + BAK_SUFFIX))
            made = True
        except OSError as exc:
            logger.warning("[Agent] daily copy of %s failed: %s", path.name, exc)
            return False
    days[path.name] = today
    state.touch()
    state.save(force=True)
    return made


def drop_unreadable(memories: dict, trash) -> int:
    """Move every row that is not a note (not a dict, no text) to the trash
    and out of its list; the rest load as before. How many went?"""
    dropped = 0
    for conv, rows in memories.items():
        kept = [row for row in rows if readable_row(row)]
        if len(kept) == len(rows):
            continue
        for row in rows:
            if not readable_row(row):
                item = row if isinstance(row, dict) else {"value": row}
                if trash is not None:
                    trash.put(conv, "note", item, "unreadable", "load")
                dropped += 1
        rows[:] = kept
    return dropped


def migrate(memories: dict, trash, state, memory_path: Path,
            now: Optional[float] = None) -> int:
    """Bring memory.json to FORMAT once, losing nothing: a byte copy first,
    then only missing fields added. Safe to run twice. Returns the rows
    changed or dropped."""
    memory_path = Path(memory_path)
    now = time.time() if now is None else now
    try:
        done = int(state.data.get("format") or 0) >= FORMAT
    except (TypeError, ValueError):
        done = False
    pre = memory_path.with_name(memory_path.name + PRE_V2_SUFFIX)
    if not done and memory_path.is_file() and not pre.exists():
        shutil.copy2(memory_path, pre)
    changed = drop_unreadable(memories, trash)
    if not done:
        for rows in memories.values():
            taken: set[str] = {str(r["id"]) for r in rows if r.get("id")}
            for row in rows:
                before = len(row)
                if "id" not in row:
                    n = 0
                    while legacy_id(row["text"], n) in taken:
                        n += 1
                    row["id"] = legacy_id(row["text"], n)
                    taken.add(row["id"])
                row.setdefault("imp", IMP_DEFAULT if row.get("auto") else IMP_COMMAND)
                row.setdefault("uses", 0)
                row.setdefault("used", 0.0)
                row.setdefault("src", "migration")
                if "born" not in row:
                    row["born"] = float(row.get("time") or 0.0)
                if len(row) != before:
                    changed += 1
    if changed and (memory_path.is_file() or any(memories.values())):
        save_json(memory_path, memories)
    if not done:
        state.data["format"] = FORMAT
        state.data["migrated_at"] = now
        state.touch()
        try:
            state.save(force=True)
        except OSError as exc:
            # The next start migrates again, which changes nothing.
            logger.warning("[Agent] memory state save failed: %s", exc)
    return changed
