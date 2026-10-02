"""Recent speak decisions per conversation, kept in memory for the dashboard.

Bounded twice (entries per conversation, conversations per process) and never
written to disk. A record holds the mode, whether it spoke, a short reason, a
short excerpt (its reply, or the message it let pass), the start of the message
it answered and that sender's display name: no prompt text and no whole
message bodies.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque

MAX_PER_CONVERSATION = 50
MAX_CONVERSATIONS = 256
EXCERPT_CHARS = 60
NAME_CHARS = 32
_REASON_CHARS = 80


def _clip(text, limit: int) -> str:
    value = "".join(ch if ch.isprintable() else " " for ch in str(text or ""))
    value = " ".join(value.split())
    return value if len(value) <= limit else value[:limit - 1] + "…"


class DecisionLog:
    def __init__(self, per_conversation: int = MAX_PER_CONVERSATION,
                 conversations: int = MAX_CONVERSATIONS) -> None:
        self.per_conversation = max(1, int(per_conversation))
        self.max_conversations = max(1, int(conversations))
        self._rows: OrderedDict[str, deque] = OrderedDict()
        self._lock = threading.Lock()

    def record(self, conv_id: str, mode: str, spoke: bool, reason: str,
               excerpt: str = "", *, answered: str = "", sender: str = "",
               now: float | None = None) -> None:
        key = str(conv_id or "")
        if not key:
            return
        row = {"ts": time.time() if now is None else float(now),
               "mode": _clip(mode, 16), "spoke": bool(spoke),
               "reason": _clip(reason, _REASON_CHARS),
               "excerpt": _clip(excerpt, EXCERPT_CHARS),
               "answered": _clip(answered, EXCERPT_CHARS) if spoke else "",
               "sender": _clip(sender, NAME_CHARS), "count": 1}
        with self._lock:
            rows = self._rows.pop(key, None)
            if rows is None:
                rows = deque(maxlen=self.per_conversation)
            last = rows[-1] if rows else None
            # A run of identical silences (every message below the trigger
            # count) is one line, or it would push out every real decision.
            if (last is not None and not spoke and not last["spoke"]
                    and last["mode"] == row["mode"]
                    and last["reason"] == row["reason"]):
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

    def last_seen(self) -> dict[str, float]:
        with self._lock:
            return {key: rows[-1]["ts"] for key, rows in self._rows.items() if rows}

    def clear(self) -> None:
        with self._lock:
            self._rows.clear()


LOG = DecisionLog()


def record(conv_id: str, mode: str, spoke: bool, reason: str,
           excerpt: str = "", *, answered: str = "", sender: str = "") -> None:
    """Note a final speak or stay-quiet decision. Never raises into a turn.

    `answered` is the message a reply answered; `sender` wrote that message,
    or the one it let pass."""
    try:
        LOG.record(conv_id, mode, spoke, reason, excerpt,
                   answered=answered, sender=sender)
    except Exception:
        pass
