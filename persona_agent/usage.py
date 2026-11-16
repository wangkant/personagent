"""What the model calls use, per model and day, from each answer's `usage`:
kept in a small file beside the memory file that the page and `doctor` read."""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

logger = logging.getLogger("agent")

USAGE_FILE = "model_usage.json"
# The page's own requests (a persona draft): the service rewrites its file from memory.
PAGE_USAGE_FILE = "model_usage.page.json"
# Today and the six days before it, plus one so a week never loses its first day.
KEEP_DAYS = 8
WEEK_DAYS = 7
WRITE_EVERY_S = 60.0
TOKENS = ("prompt_tokens", "completion_tokens", "cached_tokens")
# What a call was for; anything else counts as "other".
PURPOSES = ("reply", "gate", "search", "tools", "learning", "memory", "check", "persona", "other")


def purpose_of(label) -> str:
    return label if label in PURPOSES else "other"


def day_of(now: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(now))


def _count(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return 0
    return max(0, value)


def cached_tokens(usage: dict) -> float:
    """Cached prompt tokens, in DeepSeek's or the OpenAI-style spelling."""
    hit = usage.get("prompt_cache_hit_tokens")
    if hit is None and isinstance(usage.get("prompt_tokens_details"), dict):
        hit = usage["prompt_tokens_details"].get("cached_tokens")
    return _count(hit)


def load(path: Path) -> dict:
    """{day: {model: row}}; a missing or damaged file is an empty one."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    days = data.get("days") if isinstance(data, dict) else None
    if not isinstance(days, dict):
        return {}
    return {day: {str(m): dict(r) for m, r in models.items() if isinstance(r, dict)}
            for day, models in days.items() if isinstance(models, dict)}


class UsageBook:
    """The running tally, written at most once a WRITE_EVERY_S."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.days = load(self.path)
        self.written_at: float | None = None
        self.dirty = False
        self._pool: ThreadPoolExecutor | None = None
        self._pending: Future | None = None

    def add(self, model: str, usage, now: float, purpose: str = "other") -> None:
        usage = usage if isinstance(usage, dict) else {}
        row = self.days.setdefault(day_of(now), {}).setdefault(model or "?", {})
        row["calls"] = _count(row.get("calls")) + 1
        purposes = row.get("purposes")
        if not isinstance(purposes, dict):
            purposes = row["purposes"] = {}
        label = purpose_of(purpose)
        purposes[label] = _count(purposes.get(label)) + 1
        row["prompt_tokens"] = _count(row.get("prompt_tokens")) + _count(usage.get("prompt_tokens"))
        row["completion_tokens"] = (_count(row.get("completion_tokens"))
                                    + _count(usage.get("completion_tokens")))
        row["cached_tokens"] = _count(row.get("cached_tokens")) + cached_tokens(usage)
        cost = usage.get("cost")
        if not isinstance(cost, bool) and isinstance(cost, (int, float)) and cost >= 0:
            row["cost"] = _count(row.get("cost")) + cost
            row["costed"] = _count(row.get("costed")) + 1
        self.dirty = True

    def due(self, now: float) -> float:
        """Seconds until the next write may happen; 0 when it may now."""
        if self.written_at is None:
            return 0.0
        return max(0.0, self.written_at + WRITE_EVERY_S - now)

    def _take(self, now: float) -> str | None:
        """The file's text as of now, marking it written; None when unchanged."""
        if not self.dirty:
            return None
        keep = sorted(self.days)[-KEEP_DAYS:]
        self.days = {day: self.days[day] for day in keep}
        self.written_at, self.dirty = now, False
        return json.dumps({"days": self.days}, ensure_ascii=False)

    def _write(self, text: str) -> None:
        from . import storage

        # Rebuildable tallies: no fsync.
        storage.atomic_write_text(self.path, text, fsync=False)

    def _write_quietly(self, text: str) -> None:
        try:
            self._write(text)
        except OSError as e:
            logger.debug("[Agent] model use tally not written: %s", e)

    def flush_soon(self, now: float) -> None:
        """Write on a worker thread, in order, so the event loop never waits on the disk."""
        text = self._take(now)
        if text is None:
            return
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="usage-tally")
        self._pending = self._pool.submit(self._write_quietly, text)

    def flush(self, now: float) -> None:
        """Write now, after any write in flight, so the newest tally lands last."""
        text = self._take(now)
        pending, self._pending = self._pending, None
        if pending is not None:
            pending.result()
        if text is not None:
            self._write(text)


def _total(rows) -> dict:
    out = {"calls": 0, "tokens": 0, "cost": None, "costed": 0,
           **{name: 0 for name in TOKENS}}
    for row in rows:
        out["calls"] += int(_count(row.get("calls")))
        for name in TOKENS:
            out[name] += int(_count(row.get(name)))
        if _count(row.get("costed")):
            out["cost"] = (out["cost"] or 0.0) + float(_count(row.get("cost")))
            out["costed"] += int(_count(row.get("costed")))
    out["tokens"] = out["prompt_tokens"] + out["completion_tokens"]
    return out


def _purposes(rows) -> dict:
    """Requests per purpose; calls from before purposes were kept count as "other"."""
    out: dict = {}
    for row in rows:
        calls = int(_count(row.get("calls")))
        split = row.get("purposes") if isinstance(row.get("purposes"), dict) else {}
        named = 0
        for label, n in split.items():
            n = int(_count(n))
            out[purpose_of(label)] = out.get(purpose_of(label), 0) + n
            named += n
        if calls > named:
            out["other"] = out.get("other", 0) + calls - named
    return {label: out[label] for label in PURPOSES if out.get(label)}


def summary(days: dict, now: float | None = None) -> dict:
    """Today's and the last seven days' totals, and each model's for the week."""
    now = time.time() if now is None else now
    week = {day_of(now - 86400 * back) for back in range(WEEK_DAYS)}
    today = days.get(day_of(now), {})
    recent = [(model, row) for day, models in days.items() if day in week
              for model, row in models.items()]
    models = {}
    for model, row in recent:
        models.setdefault(model, []).append(row)
    return {"today": _total(today.values()), "week": _total(row for _, row in recent),
            "todayPurposes": _purposes(today.values()),
            "models": sorted(({"model": m, **_total(rows)} for m, rows in models.items()),
                             key=lambda r: (-r["calls"], r["model"]))}


def merged(*books: dict) -> dict:
    """Several {day: {model: row}} added together row by row."""
    out: dict = {}
    for days in books:
        for day, models in days.items():
            for model, row in models.items():
                into = out.setdefault(day, {}).setdefault(model, {})
                for key, value in row.items():
                    if key == "purposes" and isinstance(value, dict):
                        mine = into.setdefault("purposes", {})
                        for label, n in value.items():
                            mine[label] = _count(mine.get(label)) + _count(n)
                    elif not isinstance(value, (dict, list, str)):
                        into[key] = _count(into.get(key)) + _count(value)
    return out


def read_summary(path: Path, now: float | None = None) -> dict:
    path = Path(path)
    return summary(merged(load(path), load(path.with_name(PAGE_USAGE_FILE))), now)
