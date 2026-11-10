"""The recent lines of each chat on disk (runtime/recent.json), so a restart
does not lose the conversation. Rebuildable: written without fsync, and a
damaged file is moved aside and every chat starts empty."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from .storage import atomic_write_text, load_rebuildable_json

FORMAT = 1
KEEP_HOURS = 72.0
MAX_CONVS = 256
LINES_MAX = 60
SPILL_MAX = 240
DM_MAX = 60
DM_SPILL_MAX = 120
UNANSWERED_MAX = 3

#: Each list of a chat's entry and how many of its newest rows are kept.
CAPS = {"lines": LINES_MAX, "spill": SPILL_MAX, "dm": DM_MAX,
        "dm_spill": DM_SPILL_MAX, "unanswered": UNANSWERED_MAX}


def _num(value, kind=float):
    try:
        return kind(value or 0)
    except (TypeError, ValueError):
        return kind(0)


def clean_entry(entry: dict) -> tuple[dict, int]:
    """One chat's entry with every list capped to its newest rows: (entry,
    how many spill rows did not fit)."""
    out: dict = {"seq": _num(entry.get("seq"), int),
                 "folded_upto": _num(entry.get("folded_upto"), int),
                 "last_at": _num(entry.get("last_at"))}
    lost = 0
    for key, cap in CAPS.items():
        rows = entry.get(key)
        rows = list(rows) if isinstance(rows, list) else []
        if key == "unanswered":
            rows = [str(r) for r in rows if isinstance(r, str)]
        else:
            rows = [r for r in rows if isinstance(r, dict)]
        if len(rows) > cap:
            if key in ("spill", "dm_spill"):
                lost += len(rows) - cap
            rows = rows[-cap:]
        out[key] = rows
    return out, lost


def _parse(data) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("convs"), dict):
        raise ValueError("not a recent.json")
    return {str(conv): clean_entry(entry)[0]
            for conv, entry in data["convs"].items() if isinstance(entry, dict)}


class RecentStore:
    """{conv: entry}; see `clean_entry` for an entry's keys."""

    def __init__(self, path: Path, keep_hours: float = KEEP_HOURS,
                 max_convs: int = MAX_CONVS):
        self.path = Path(path)
        self.keep_hours = keep_hours
        self.max_convs = max_convs
        self.convs: dict[str, dict] = {}

    def load(self) -> dict:
        self.convs = load_rebuildable_json(self.path, _parse) or {}
        return self.convs

    def snapshot(self, conv: str) -> Optional[dict]:
        return self.convs.get(conv)

    def put(self, conv: str, state: dict) -> int:
        """Store a chat's entry, capped; returns the spill rows that did not fit."""
        entry, lost = clean_entry(state)
        self.convs[conv] = entry
        return lost

    def drop(self, conv: str) -> bool:
        return self.convs.pop(conv, None) is not None

    def trim(self, now: Optional[float] = None) -> list[str]:
        """Drop chats quiet for longer than keep_hours, then all but the
        newest max_convs; returns the dropped keys."""
        now = time.time() if now is None else now
        cutoff = now - self.keep_hours * 3600.0
        order = sorted(self.convs, key=lambda c: self.convs[c]["last_at"],
                       reverse=True)
        keep = [c for c in order if self.convs[c]["last_at"] >= cutoff][:self.max_convs]
        kept = set(keep)
        dropped = [c for c in order if c not in kept]
        for conv in dropped:
            del self.convs[conv]
        return dropped

    def write(self) -> None:
        atomic_write_text(self.path, json.dumps(
            {"format": FORMAT, "convs": self.convs}, ensure_ascii=False,
            separators=(",", ":")), fsync=False)

    def delete(self) -> None:
        """MEMORY_KEEP_RECENT=false: nothing of the chats stays on disk."""
        self.convs = {}
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
