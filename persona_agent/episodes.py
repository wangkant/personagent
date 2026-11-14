"""Events and the running summary of each chat (runtime/episodes.json).

{conv: {"thread": {...} | absent, "episodes": [{...}, ...]}}. Durable like
memory.json: a damaged file stops the start. Times and people of an event
come from the chat lines it cites, never from a model."""
from __future__ import annotations

import time
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Optional

from . import memstore, ranking
from .storage import num as _num

THREAD_MAX_CHARS = 400
EPISODE_MAX_CHARS = 240


class EpisodeStore:
    """Loaded on first use; `unreadable` lists (conv, row) the load dropped,
    for the caller's trash."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: Optional[dict] = None
        self.unreadable: list[tuple[str, dict]] = []

    @property
    def data(self) -> dict:
        if self._data is None:
            self.load()
        return self._data

    def load(self) -> dict:
        raw = memstore._read_strict(self.path, lambda d: isinstance(d, dict) and all(
            isinstance(v, dict) for v in d.values()))
        data: dict = {}
        self.unreadable = []
        for conv, entry in (raw or {}).items():
            rows = entry.get("episodes")
            rows = rows if isinstance(rows, list) else []
            for row in rows:
                if not memstore.readable_row(row):
                    self.unreadable.append(
                        (conv, row if isinstance(row, dict) else {"value": row}))
            clean: dict = {"episodes": [r for r in rows if memstore.readable_row(r)]}
            if memstore.readable_row(entry.get("thread")):
                clean["thread"] = entry["thread"]
            data[conv] = clean
        self._data = data
        return data

    def save(self) -> None:
        # Chats left with nothing are not written.
        memstore.save_json(self.path, {
            conv: entry for conv, entry in self.data.items()
            if entry.get("episodes") or entry.get("thread")})

    def _entry(self, conv: str) -> dict:
        return self.data.setdefault(conv, {"episodes": []})

    def convs(self) -> list[str]:
        return [c for c, e in self.data.items()
                if e.get("episodes") or e.get("thread")]

    def thread(self, conv: str) -> Optional[dict]:
        return self.data.get(conv, {}).get("thread")

    def set_thread(self, conv: str, text: str, from_t: float, to_t: float,
                   now: Optional[float] = None) -> Optional[dict]:
        """Replace the summary; the old one is returned for the trash."""
        entry = self._entry(conv)
        old = entry.get("thread")
        entry["thread"] = {
            "id": memstore.new_id("t", [old["id"]] if old and old.get("id") else []),
            "text": str(text)[:THREAD_MAX_CHARS],
            "updated": time.time() if now is None else now,
            "from_t": float(from_t), "to_t": float(to_t)}
        return old

    def drop_thread(self, conv: str) -> Optional[dict]:
        return self.data.get(conv, {}).pop("thread", None)

    def episodes(self, conv: str) -> list[dict]:
        return self.data.get(conv, {}).get("episodes", [])

    def ids(self, conv: str) -> set[str]:
        return {str(e.get("id")) for e in self.episodes(conv) if e.get("id")}

    def add(self, conv: str, row: dict) -> dict:
        """Append an event; an id and the use fields are given when missing."""
        if not row.get("id") or row["id"] in self.ids(conv):
            row["id"] = memstore.new_id("e", self.ids(conv))
        row["text"] = str(row.get("text", ""))[:EPISODE_MAX_CHARS]
        row.setdefault("imp", memstore.IMP_DEFAULT)
        row.setdefault("uses", 0)
        row.setdefault("used", 0.0)
        row.setdefault("who", [])
        row.setdefault("names", [])
        row.setdefault("followed", False)
        self._entry(conv)["episodes"].append(row)
        return row

    def get(self, conv: str, eid: str) -> Optional[dict]:
        return next((e for e in self.episodes(conv) if e.get("id") == eid), None)

    def remove(self, conv: str, eid: str) -> Optional[dict]:
        rows = self.episodes(conv)
        for i, row in enumerate(rows):
            if row.get("id") == eid:
                return rows.pop(i)
        return None

    def drop_conv(self, conv: str) -> bool:
        return self.data.pop(conv, None) is not None

    def evict_one(self, conv: str, now: Optional[float] = None) -> Optional[dict]:
        """Remove the event least worth keeping (retention), the oldest on a tie."""
        rows = self.episodes(conv)
        if not rows:
            return None
        now = time.time() if now is None else now

        def key(i: int):
            row = rows[i]
            last = max(_num(row.get("t1")), _num(row.get("used")))
            return (ranking.retention(row.get("imp"), row.get("uses"), last, now),
                    _num(row.get("t1")), i)
        return rows.pop(min(range(len(rows)), key=key))

    def oldest_month(self, conv: str, now: Optional[float] = None,
                     min_age_days: float = 60, min_count: int = 3,
                     tz: Optional[tzinfo] = None) -> list[dict]:
        """The events of the oldest calendar month (in `tz`, else local) that
        has at least `min_count` events older than `min_age_days`; roll-ups
        are not rolled up again. Empty when no month qualifies."""
        now = time.time() if now is None else now
        cutoff = now - min_age_days * 86400.0
        months: dict[tuple[int, int], list[dict]] = {}
        for row in self.episodes(conv):
            if row.get("rollup") or _num(row.get("t1")) >= cutoff:
                continue
            d = datetime.fromtimestamp(_num(row.get("t0")), tz)
            months.setdefault((d.year, d.month), []).append(row)
        for month in sorted(months):
            if len(months[month]) >= min_count:
                return sorted(months[month], key=lambda r: _num(r.get("t0")))
        return []

