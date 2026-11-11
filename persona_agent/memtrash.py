"""What the character's memory removed, for a while: the undo store and the
record of why something went (runtime/memory_trash.jsonl).

One row per removal, appended (locked, fsync) before the store it came from
is rewritten, and one marker row when a removal is restored. A forget a
person asked for in chat, Forget this chat and Clear memory write nothing."""
from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from typing import Callable, Optional

from .storage import append_jsonl, atomic_write_text, read_validated_jsonl

KINDS = ("note", "episode", "thread", "core")
REASONS = ("replaced", "merged", "ended", "evicted", "rolled_up", "rewritten",
           "forgotten_page", "unreadable")
BYS = ("fold", "cap", "reply", "page", "terminal", "load")
#: How long a removal stays restorable, by who removed it.
RESTORE_S = {"page": 86400.0, "terminal": 86400.0}
DEFAULT_RESTORE_S = 30 * 86400.0
MAX_ROWS = 3000


def restorable_until(row: dict) -> float:
    return float(row.get("at") or 0.0) + RESTORE_S.get(
        str(row.get("by") or ""), DEFAULT_RESTORE_S)


def _validate(row: dict) -> Optional[str]:
    if not isinstance(row.get("tid"), str):
        return "no tid"
    if "restored_at" in row:
        float(row["restored_at"])
        return None
    for key in ("conv", "kind", "why", "by"):
        if not isinstance(row.get(key), str):
            return f"no {key}"
    float(row["at"])
    if not isinstance(row.get("item"), dict):
        return "no item"
    return None


class MemoryTrash:
    """memory_trash.jsonl. `list` shows what can still be restored."""

    def __init__(self, path: Path):
        self.path = Path(path)
        #: Lines the last read skipped, for the health report.
        self.skipped = 0

    def _read(self) -> tuple[list[dict], dict[str, float]]:
        """(removal rows in file order, {tid: restored_at})."""
        result = read_validated_jsonl(self.path, _validate)
        self.skipped = len(result.quarantined)
        rows, restored = [], {}
        for row in result.rows:
            if "restored_at" in row:
                restored[row["tid"]] = float(row["restored_at"])
            else:
                rows.append(row)
        return rows, restored

    def put(self, conv: str, kind: str, item: dict, why: str, by: str,
            ref: str = "", now: Optional[float] = None) -> str:
        tid = "r" + secrets.token_hex(5)
        row = {"tid": tid, "at": time.time() if now is None else now,
               "conv": str(conv), "kind": kind, "why": why, "by": by,
               "item": item}
        if ref:
            row["ref"] = ref
        append_jsonl(self.path, row)
        return tid

    def get(self, tid: str) -> Optional[dict]:
        """The removal row, with `restored_at` when it was restored."""
        rows, restored = self._read()
        for row in reversed(rows):
            if row["tid"] == tid:
                if tid in restored:
                    row = dict(row, restored_at=restored[tid])
                return row
        return None

    def list(self, conv: Optional[str] = None, now: Optional[float] = None,
             live: Optional[Callable[[dict], bool]] = None) -> list[dict]:
        """Restorable rows, newest first: not expired, not restored, and not
        still live (a crash between the append and the store's rewrite)."""
        now = time.time() if now is None else now
        rows, restored = self._read()
        out = []
        for row in reversed(rows):
            if conv is not None and row["conv"] != conv:
                continue
            if row["tid"] in restored or restorable_until(row) <= now:
                continue
            if live is not None and live(row):
                continue
            out.append(row)
        return out

    def mark_restored(self, tid: str, now: Optional[float] = None) -> None:
        append_jsonl(self.path, {
            "tid": tid, "restored_at": time.time() if now is None else now})

    def _rewrite(self, keep: Callable[[dict], bool]) -> int:
        """Rewrite the file with the rows `keep` accepts; markers stay only
        beside a kept row. How many removal rows went?"""
        rows, restored = self._read()
        kept = [row for row in rows if keep(row)]
        if len(kept) == len(rows) and not self.skipped and set(restored) <= {
                row["tid"] for row in kept}:
            return 0
        tids = {row["tid"] for row in kept}
        lines = [json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                 for row in kept]
        lines += [json.dumps({"tid": tid, "restored_at": at})
                  for tid, at in restored.items() if tid in tids]
        atomic_write_text(self.path, "".join(line + "\n" for line in lines))
        return len(rows) - len(kept)

    def drop_conv(self, conv: str) -> int:
        """Forget this chat: its removals are no longer restorable."""
        return self._rewrite(lambda row: row["conv"] != conv)

    def prune(self, now: Optional[float] = None) -> int:
        """Drop expired and restored rows, then all but the newest MAX_ROWS."""
        now = time.time() if now is None else now
        rows, restored = self._read()
        alive = [row for row in rows
                 if row["tid"] not in restored and restorable_until(row) > now]
        keep = {row["tid"] for row in alive[-MAX_ROWS:]}
        return self._rewrite(lambda row: row["tid"] in keep)
