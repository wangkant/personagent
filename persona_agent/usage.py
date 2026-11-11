"""What the model calls use, per model and day, from each answer's `usage`:
kept in a small file beside the memory file that the page and `doctor` read."""
from __future__ import annotations

import json
import time
from pathlib import Path

USAGE_FILE = "model_usage.json"
# Today and the six days before it, plus one so a week never loses its first day.
KEEP_DAYS = 8
WEEK_DAYS = 7
WRITE_EVERY_S = 60.0
TOKENS = ("prompt_tokens", "completion_tokens", "cached_tokens")


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

    def add(self, model: str, usage, now: float) -> None:
        usage = usage if isinstance(usage, dict) else {}
        row = self.days.setdefault(day_of(now), {}).setdefault(model or "?", {})
        row["calls"] = _count(row.get("calls")) + 1
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

    def flush(self, now: float) -> None:
        if not self.dirty:
            return
        from .storage import atomic_write_text

        keep = sorted(self.days)[-KEEP_DAYS:]
        self.days = {day: self.days[day] for day in keep}
        # Rebuildable tallies: no disk wait on the event loop.
        atomic_write_text(self.path, json.dumps({"days": self.days}, ensure_ascii=False),
                          fsync=False)
        self.written_at, self.dirty = now, False


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
            "models": sorted(({"model": m, **_total(rows)} for m, rows in models.items()),
                             key=lambda r: (-r["calls"], r["model"]))}


def read_summary(path: Path, now: float | None = None) -> dict:
    return summary(load(path), now)
