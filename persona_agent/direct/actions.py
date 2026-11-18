"""What an account does besides answering: a like, a look at a video, a search.

A platform declares its actions; this module holds what every one of them
shares: the three classes, the owner's switches and limits, the day's counts,
and the record of what was done. The process that works the browser owns all
of it and checks before each action, so nothing a model says can go past it.

- respond: acts on the message being answered (like it). On by default.
- look:    reads something public (a video's facts, a search). On by default.
- reach:   acts on other people's content unprompted (like a video, follow).
           Off until the owner turns each one on.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..storage import append_jsonl_rotating, atomic_write_text

RESPOND, LOOK, REACH = "respond", "look", "reach"
CLASSES = (RESPOND, LOOK, REACH)

#: The most of one action in a day whatever the owner sets: more reads as a machine.
CEILING = {RESPOND: 50, LOOK: 80, REACH: 10}
#: Likes one person gets from the account in a day.
PER_PERSON = 3
#: Seconds between two reach actions.
REACH_SPACING_S = 600.0
RECORD_MAX_BYTES = 2_000_000
RECORD_SHOWN = 50

# Why an action did not happen; the page and the terminal explain each.
OFF, PAUSED, DAILY_LIMIT, PER_PERSON_LIMIT, ALREADY, TOO_SOON, BUSY, NOT_FOUND, UNKNOWN = (
    "off", "paused", "daily_limit", "per_person", "already", "too_soon", "busy", "not_found", "unknown_action")


@dataclass(frozen=True)
class Action:
    """One thing a platform's account can do.

    `says` is read by the character's model, so it is one plain sentence. No
    parameter ever takes an id or an address: `which` and `pick` are small
    numbers into lists this process built (the links in the message being
    answered, the last results shown)."""
    name: str
    cls: str
    says: str
    per_day: int
    params: dict = field(default_factory=dict)      # JSON Schema properties
    undo: str = ""                                  # the action that takes it back, if any

    @property
    def on_by_default(self) -> bool:
        return self.cls != REACH

    @property
    def ceiling(self) -> int:
        return CEILING[self.cls]


@dataclass
class Done:
    """What an action came to. `text` is what the character may know of it
    (public facts only); `what` and `link` are for the owner's record."""
    ok: bool
    text: str = ""
    what: str = ""
    link: str = ""
    code: str = ""
    found: list = field(default_factory=list)       # numbered results a later `pick` refers to


def settings_path(home: Path) -> Path:
    return home / "platforms" / "actions.json"


def record_path(home: Path) -> Path:
    return home / "platforms" / "actions.jsonl"


class Settings:
    """The owner's switches: {kind: {"paused": bool, "actions": {name: {"on": bool, "per_day": int}}}}.
    Read again whenever the file's content changes, so the page's change holds at once."""

    def __init__(self, home: Optional[Path]):
        self.path = settings_path(home) if home else None
        self._text: Optional[str] = None
        self._values: dict = {}

    def _read(self) -> dict:
        if self.path is None:
            return self._values
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if text != self._text:
            self._text = text
            try:
                values = json.loads(text) if text.strip() else {}
            except ValueError:
                values = {}
            self._values = values if isinstance(values, dict) else {}
        return self._values

    def _write(self, values: dict) -> None:
        self._values = values
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(values, ensure_ascii=False, indent=1) + "\n"
        atomic_write_text(self.path, text)
        self._text = text

    def paused(self, kind: str) -> bool:
        return bool((self._read().get(kind) or {}).get("paused"))

    def of(self, kind: str, action: Action) -> tuple[bool, int]:
        """(on, per-day limit) for one action: the owner's choice within the ceiling."""
        own = ((self._read().get(kind) or {}).get("actions") or {}).get(action.name) or {}
        on = own.get("on") if isinstance(own.get("on"), bool) else action.on_by_default
        per_day = own.get("per_day") if isinstance(own.get("per_day"), int) else action.per_day
        return on, max(0, min(per_day, action.ceiling))

    def set(self, kind: str, action: Action, *, on: Optional[bool] = None,
            per_day: Optional[int] = None) -> tuple[bool, int]:
        values = json.loads(json.dumps(self._read()))
        own = values.setdefault(kind, {}).setdefault("actions", {}).setdefault(action.name, {})
        if on is not None:
            own["on"] = bool(on)
        if per_day is not None:
            own["per_day"] = max(0, min(int(per_day), action.ceiling))
        self._write(values)
        return self.of(kind, action)

    def pause(self, kind: str, paused: bool) -> None:
        values = json.loads(json.dumps(self._read()))
        values.setdefault(kind, {})["paused"] = bool(paused)
        self._write(values)


class Counts:
    """What one account did today, kept between runs: per action, per person,
    the items already liked, and when it last reached out."""

    def __init__(self, path: Optional[Path]):
        self.path = path
        self.day = ""
        self.actions: dict[str, int] = {}
        self.people: dict[str, int] = {}
        self.items: dict[str, None] = {}
        self.reached_at = 0.0
        try:
            saved = json.loads(path.read_text(encoding="utf-8")) if path else {}
        except (OSError, ValueError):
            saved = {}
        if isinstance(saved, dict):
            self.day = str(saved.get("day") or "")
            self.actions = {str(k): int(v) for k, v in (saved.get("actions") or {}).items() if isinstance(v, int)}
            self.people = {str(k): int(v) for k, v in (saved.get("people") or {}).items() if isinstance(v, int)}
            self.items = {str(k): None for k in saved.get("items") or []}
            self.reached_at = float(saved.get("reached_at") or 0.0)

    def _today(self, now: float) -> None:
        day = time.strftime("%Y-%m-%d", time.localtime(now))
        if day != self.day:
            self.day, self.actions, self.people = day, {}, {}

    def done(self, name: str, now: Optional[float] = None) -> int:
        self._today(time.time() if now is None else now)
        return self.actions.get(name, 0)

    def add(self, action: Action, *, person: str = "", item: str = "", now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        self._today(now)
        self.actions[action.name] = self.actions.get(action.name, 0) + 1
        if person:
            self.people[person] = self.people.get(person, 0) + 1
        if item:
            self.items[item] = None
            while len(self.items) > 5000:
                self.items.pop(next(iter(self.items)))
        if action.cls == REACH:
            self.reached_at = now
        self._save()

    def take_back(self, item: str) -> None:
        if self.items.pop(item, 0) is None:
            self._save()

    def _save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(self.path, json.dumps(
                {"day": self.day, "actions": self.actions, "people": self.people,
                 "items": list(self.items), "reached_at": self.reached_at}, ensure_ascii=False))
        except OSError:
            pass


def refusal(kind: str, action: Action, settings: Settings, counts: Counts, *, person: str = "",
            item: str = "", now: Optional[float] = None) -> str:
    """Why `action` may not happen now, or "" when it may. `person`: who it is
    done for (a like on their message); `item`: what it is done to, for the
    things done once only."""
    now = time.time() if now is None else now
    if settings.paused(kind):
        return PAUSED
    on, per_day = settings.of(kind, action)
    if not on:
        return OFF
    if counts.done(action.name, now) >= per_day:
        return DAILY_LIMIT
    if item and item in counts.items:
        return ALREADY
    if person and action.cls != LOOK and counts.people.get(person, 0) >= PER_PERSON:
        return PER_PERSON_LIMIT
    if action.cls == REACH and now - counts.reached_at < REACH_SPACING_S:
        return TOO_SOON
    return ""


def record(home: Optional[Path], *, kind: str, account: str, action: str, done: Done, why: str = "",
           now: Optional[float] = None) -> None:
    """One line of what the character did, for its owner. Never an id; `what`
    is a few words of the thing itself."""
    if home is None:
        return
    row = {"at": int(time.time() if now is None else now), "kind": kind, "account": account,
           "action": action, "ok": bool(done.ok), "code": done.code, "what": done.what[:80],
           "link": done.link[:300], "why": why[:80]}
    try:
        append_jsonl_rotating(record_path(home), row, max_bytes=RECORD_MAX_BYTES)
    except Exception:
        pass


def recent(home: Path, limit: int = RECORD_SHOWN) -> list[dict]:
    """The latest records, newest first."""
    try:
        lines = record_path(home).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict] = []
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
            if len(rows) >= limit:
                break
    return rows


def function_for(kind: str, action: Action) -> dict[str, Any]:
    """The action as the function a model is offered: its own words, small numbers and short strings only."""
    return {"name": f"{kind}_{action.name}", "description": action.says,
            "parameters": {"type": "object", "properties": dict(action.params), "additionalProperties": False}}
