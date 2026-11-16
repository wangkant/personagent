"""Recent speak decisions per conversation, in memory for the dashboard."""
from __future__ import annotations

import contextvars
import threading
import time
from collections import OrderedDict, deque

MAX_PER_CONVERSATION = 50
MAX_CONVERSATIONS = 256
EXCERPT_CHARS = 60
NAME_CHARS = 32
_REASON_CHARS = 80
# Outcomes of a call: each person who called gets their own row.
_PER_PERSON = frozenset({"model failed", "blocked", "delivery failed",
                         "answered together"})


# What the turn under way looked up (a web search, a tool by name); a list
# shared by reference, so a task the turn starts adds to the same one.
_LOOKUPS: contextvars.ContextVar = contextvars.ContextVar("turn_lookups", default=None)


def start_turn() -> list:
    lookups: list = []
    _LOOKUPS.set(lookups)
    return lookups


def note_lookup(kind: str, name: str = "") -> None:
    lookups = _LOOKUPS.get()
    if lookups is not None:
        lookups.append({"kind": kind, "name": name})


def _take_lookup() -> dict:
    """The turn's last lookup, once: the next turn starts with none."""
    lookups = _LOOKUPS.get()
    if not lookups:
        return {}
    last = lookups[-1]
    lookups.clear()
    return {"kind": _clip(last.get("kind"), 16), "name": _clip(last.get("name"), 120)}


def _clip(text, limit: int) -> str:
    value = "".join(ch if ch.isprintable() else " " for ch in str(text or ""))
    value = " ".join(value.split())
    return value if len(value) <= limit else value[:limit - 1] + "…"


class DecisionLog:
    def __init__(self, per_conversation: int = MAX_PER_CONVERSATION,
                 conversations: int = MAX_CONVERSATIONS) -> None:
        self.per_conversation = per_conversation
        self.max_conversations = conversations
        self._rows: OrderedDict[str, deque] = OrderedDict()
        self._lock = threading.Lock()

    def record(self, conv_id: str, mode: str, spoke: bool, reason: str,
               excerpt: str = "", *, answered: str = "", sender: str = "",
               now: float | None = None) -> None:
        key = str(conv_id or "")
        row = {"ts": time.time() if now is None else float(now),
               "mode": _clip(mode, 16), "spoke": bool(spoke),
               "reason": _clip(reason, _REASON_CHARS),
               "excerpt": _clip(excerpt, EXCERPT_CHARS),
               "answered": _clip(answered, EXCERPT_CHARS) if spoke else "",
               "sender": _clip(sender, NAME_CHARS), "count": 1}
        if spoke:
            lookup = _take_lookup()
            if lookup:
                row["lookup"] = lookup
        with self._lock:
            rows = self._rows.pop(key, None)
            if rows is None:
                rows = deque(maxlen=self.per_conversation)
            last = rows[-1] if rows else None
            # A run of identical silences (every message below the trigger
            # count) is one line, or it would push out every real decision.
            # A failure that silenced someone else is not the same line.
            if (last is not None and not spoke and not last["spoke"]
                    and last["mode"] == row["mode"]
                    and last["reason"] == row["reason"]
                    and (row["reason"] not in _PER_PERSON
                         or last["sender"] == row["sender"])):
                row["count"] = last["count"] + 1
                rows[-1] = row
            else:
                rows.append(row)
            self._rows[key] = rows
            while len(self._rows) > self.max_conversations:
                self._rows.popitem(last=False)

    def recent(self, conv_id: str) -> list[dict]:
        """Newest first."""
        with self._lock:
            rows = self._rows.get(str(conv_id or ""))
            return [dict(r) for r in reversed(rows)] if rows else []

    def drop_where(self, conv_id: str, gone) -> int:
        """Remove one conversation's rows whose message or answer `gone(text)`
        holds; how many went."""
        with self._lock:
            rows = self._rows.get(str(conv_id or ""))
            if not rows:
                return 0
            kept = [r for r in rows if not (gone(r["excerpt"]) or gone(r["answered"]))]
            cut = len(rows) - len(kept)
            rows.clear()
            rows.extend(kept)
            return cut

    def last_seen(self) -> dict[str, float]:
        with self._lock:
            return {key: rows[-1]["ts"] for key, rows in self._rows.items() if rows}

    def clear(self) -> None:
        with self._lock:
            self._rows.clear()


LOG = DecisionLog()


def record(conv_id: str, mode: str, spoke: bool, reason: str,
           excerpt: str = "", *, answered: str = "", sender: str = "") -> None:
    """Note a final speak or stay-quiet decision. `answered` is the message a
    reply answered; `sender` wrote that message, or the one it let pass."""
    LOG.record(conv_id, mode, spoke, reason, excerpt,
               answered=answered, sender=sender)
