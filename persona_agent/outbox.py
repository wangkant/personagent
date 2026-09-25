"""Messages nobody asked for, and how to reach the conversations they are for.

A connector turn answers inside its own HTTP response. A proactive opener, the
follow-up question after a rejection and the excuse for a failed model call
have no request to answer in, so a connector that declared the `outbox`
capability pulls them from ``POST /v1/outbox`` instead
(docs/connectors.md, "Outbox"). Pull, not push: the agent never has to reach
the connector, so one behind NAT works the same.

``HandleStore`` remembers, per routing key, what the connector said to hand
back to address the conversation later. ``Outbox`` queues deliveries, hands
each one out once, and waits for the connector's ack, so the caller commits
only what was actually sent.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import secrets
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .connector import CONVERSATION_TYPES, MAX_CONNECTOR_ID_CHARS, opaque_value
from .storage import atomic_write_text

logger = logging.getLogger("agent.outbox")

#: How long a delivery may wait to be started, per reason (seconds). An
#: excuse is useless a minute later; an opener can wait a few.
REASON_TTL_S = {"proactive": 300.0, "follow_up": 120.0, "excuse": 60.0}
#: A connector that has not pulled for this long is gone: nothing is queued
#: for its conversations until it pulls again, and what it holds unacked
#: counts as not sent.
LIVENESS_S = 90.0
#: Longest long-poll the agent holds, and what it tells the connector to use.
MAX_WAIT_S = 30
DEFAULT_WAIT_S = 25
#: After hand-out, how long past the delivery's own deadline to wait for its
#: ack: the connector sends it with typing pauses, then acks on its next pull.
ACK_GRACE_S = 60.0
MAX_PER_CONVERSATION = 3
MAX_QUEUED = 256
MAX_DELIVERIES_PER_PULL = 50
MAX_ACKS_PER_PULL = 1000
MAX_HANDLES = 4096
MAX_CONNECTORS = 64

#: The body `kind` of a pull (see connector.EVENT_KIND).
PULL_KIND = "outbox.pull"

#: Ack statuses a connector may send (docs/connectors.md).
ACK_STATUSES = frozenset(
    {"sent", "partial", "failed", "expired", "refused", "unsupported"})

_RECORD_FIELDS = ("reply_handle", "connector_id", "capabilities", "platform",
                  "native", "conversation_type", "conversation_id", "prefiltered")


def parse_pull(body) -> Optional[dict]:
    """A pull body as `Outbox.pull` keywords, or None when it is not one."""
    if not isinstance(body, dict) or body.get("kind") != PULL_KIND:
        return None
    connector_id = opaque_value(body.get("connector_id"),
                                MAX_CONNECTOR_ID_CHARS)
    if not connector_id:
        return None
    numbers = []
    for name, default in (("wait_s", DEFAULT_WAIT_S), ("max_deliveries", 10)):
        value = body.get(name, default)
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)):
            return None
        numbers.append(value)
    acks = body.get("acks", [])
    if not isinstance(acks, list) or len(acks) > MAX_ACKS_PER_PULL:
        return None
    return {"connector_id": connector_id, "wait_s": float(numbers[0]),
            "max_deliveries": int(numbers[1]), "acks": acks}


def _clean_record(raw) -> Optional[dict]:
    """A stored handle as written by `HandleStore.record`, or None."""
    if not isinstance(raw, dict):
        return None
    try:
        record = {
            "reply_handle": str(raw.get("reply_handle") or ""),
            "connector_id": str(raw.get("connector_id") or ""),
            "capabilities": sorted(c for c in raw.get("capabilities")
                                   if isinstance(c, str))
            if isinstance(raw.get("capabilities"), list) else [],
            "platform": str(raw.get("platform") or ""),
            "native": raw.get("native") is True,
            "conversation_type": str(raw.get("conversation_type") or ""),
            "conversation_id": str(raw.get("conversation_id") or ""),
            "prefiltered": raw.get("prefiltered") is not False,
            "updated_at": float(raw.get("updated_at") or 0.0),
        }
    except (TypeError, ValueError):
        return None
    if record["conversation_type"] not in CONVERSATION_TYPES:
        return None
    if raw.get("unsupported") is True:
        record["unsupported"] = True
    return record


class HandleStore:
    """How to reach each connector conversation without an incoming message.

    Keyed by the routing key (the group id or ``private:<uid>``), so it names
    conversations the same way every other store does. Bounded: past `cap`
    the entry updated longest ago goes. Loaded on first use, so a harness can
    repoint `path` after construction."""

    #: When only the timestamp moved, write at most this often.
    TOUCH_FLUSH_S = 300.0

    def __init__(self, path, *, cap: int = MAX_HANDLES) -> None:
        self.path = Path(path)
        self.cap = max(1, int(cap))
        self._entries: Optional[dict[str, dict]] = None
        self._dirty = False
        self._last_flush = 0.0

    def _data(self) -> dict[str, dict]:
        if self._entries is None:
            self._entries = self._load()
        return self._entries

    def _load(self) -> dict[str, dict]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as e:
            logger.warning("[Outbox] %s unreadable, starting empty: %s",
                           self.path, e)
            return {}
        if not isinstance(raw, dict):
            return {}
        entries = {}
        for key, value in raw.items():
            record = _clean_record(value)
            if isinstance(key, str) and key and record:
                entries[key] = record
        # Oldest first: eviction pops from the front.
        return dict(sorted(entries.items(),
                           key=lambda kv: kv[1]["updated_at"]))

    def get(self, key: str) -> Optional[dict]:
        record = self._data().get(str(key))
        return dict(record) if record else None

    def keys(self) -> list[str]:
        return list(self._data())

    def record(self, key: str, *, reply_handle: str, connector_id: str,
               capabilities, platform: str, native: bool,
               conversation_type: str, conversation_id: str,
               prefiltered: bool = True) -> None:
        data = self._data()
        old = data.pop(str(key), None)
        record = {
            "reply_handle": str(reply_handle or ""),
            "connector_id": str(connector_id or ""),
            "capabilities": sorted(str(c) for c in capabilities or ()),
            "platform": str(platform or ""),
            "native": bool(native),
            "conversation_type": str(conversation_type or ""),
            "conversation_id": str(conversation_id or ""),
            "prefiltered": bool(prefiltered),
            "updated_at": time.time(),
        }
        # "unsupported" sticks while the connector keeps the same address;
        # otherwise every inbound message would re-arm one wasted opener.
        if (old and old.get("unsupported")
                and old.get("reply_handle") == record["reply_handle"]
                and old.get("connector_id") == record["connector_id"]):
            record["unsupported"] = True
        data[str(key)] = record
        while len(data) > self.cap:
            data.pop(next(iter(data)))
        changed = old is None or any(
            old.get(f) != record.get(f) for f in _RECORD_FIELDS)
        self._dirty = True
        self.flush(force=changed)

    def mark_unsupported(self, key: str, reply_handle: str) -> None:
        """The connector said it cannot send unprompted here."""
        record = self._data().get(str(key))
        if record and record.get("reply_handle") == reply_handle:
            record["unsupported"] = True
            self._dirty = True
            self.flush(force=True)

    def flush(self, force: bool = False) -> None:
        if not self._dirty:
            return
        now = time.monotonic()
        if not force and now - self._last_flush < self.TOUCH_FLUSH_S:
            return
        try:
            # No fsync: the next inbound message rebuilds any lost entry.
            atomic_write_text(
                self.path,
                json.dumps(self._data(), ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")) + "\n",
                fsync=False)
        except Exception as e:
            logger.warning("[Outbox] handle store write failed: %s", e)
            return
        self._dirty = False
        self._last_flush = now


@dataclass
class OutboxResult:
    """How one delivery ended. `status` is an ack status, or one of the
    agent's own: full, expired_unpulled, gone, no_ack, closed."""

    status: str
    sent_items: int = 0


@dataclass(eq=False)
class _Delivery:
    delivery_id: str
    seq: int
    key: str
    handle: dict
    reason: str
    items: list
    created: float
    ttl: float
    future: asyncio.Future
    handed_out: float = 0.0
    #: Which pull handed it out (Outbox._pulls); 0 while queued.
    handed_by: int = 0
    expires_in: int = 0

    @property
    def connector_id(self) -> str:
        return self.handle.get("connector_id", "")


class Outbox:
    """Deliveries waiting for a connector, handed out at most once.

    One delivery per call to `deliver`, which waits until the connector acks
    it, the connector goes quiet, or its time runs out. Callers hold the
    conversation's send lock across that wait, which keeps one conversation's
    deliveries in order and behind any reply already being sent."""

    def __init__(self, handles: HandleStore) -> None:
        self.handles = handles
        # Attributes rather than constants so a harness can shorten them.
        self.ttl_s = dict(REASON_TTL_S)
        self.liveness_s = LIVENESS_S
        self.ack_grace_s = ACK_GRACE_S
        self.poll_s = 1.0
        self._queues: dict[str, deque[_Delivery]] = {}
        self._queued = 0
        self._handed: dict[str, _Delivery] = {}
        self._last_pull: dict[str, float] = {}
        self._seq = 0
        self._pulls = 0
        self._cond: Optional[asyncio.Condition] = None
        self._closed = False

    def _condition(self) -> asyncio.Condition:
        # Built on first use so it binds to the loop that runs the agent.
        if self._cond is None:
            self._cond = asyncio.Condition()
        return self._cond

    async def _notify(self) -> None:
        cond = self._condition()
        async with cond:
            cond.notify_all()

    # ---- liveness ------------------------------------------------------

    def _stamp(self, connector_id: str) -> None:
        self._last_pull.pop(connector_id, None)
        self._last_pull[connector_id] = time.monotonic()
        while len(self._last_pull) > MAX_CONNECTORS:
            self._last_pull.pop(next(iter(self._last_pull)))

    def live(self, connector_id: str) -> bool:
        last = self._last_pull.get(connector_id)
        return last is not None and time.monotonic() - last <= self.liveness_s

    def route(self, key: str) -> Optional[dict]:
        """The stored handle for `key` if a live connector can deliver there
        unprompted, else None."""
        record = self.handles.get(key)
        if (not record or "outbox" not in record["capabilities"]
                or record.get("unsupported")
                or not record["reply_handle"] or not record["connector_id"]):
            return None
        return record if self.live(record["connector_id"]) else None

    # ---- the sending side ----------------------------------------------

    async def deliver(self, key: str, handle: dict, items: list,
                      *, reason: str) -> OutboxResult:
        """Queue `items` for `key` and wait for the outcome."""
        if self._closed:
            return OutboxResult("closed")
        queue = self._queues.setdefault(key, deque())
        if len(queue) >= MAX_PER_CONVERSATION or self._queued >= MAX_QUEUED:
            logger.warning("[Outbox] queue full; not queuing %s for %s",
                           reason, key)
            if not queue:
                self._queues.pop(key, None)
            return OutboxResult("full")
        self._seq += 1
        delivery = _Delivery(
            delivery_id="d_" + secrets.token_hex(12), seq=self._seq, key=key,
            handle=dict(handle), reason=reason, items=list(items),
            created=time.monotonic(),
            ttl=float(self.ttl_s.get(reason, REASON_TTL_S["proactive"])),
            future=asyncio.get_running_loop().create_future())
        queue.append(delivery)
        self._queued += 1
        try:
            await self._notify()
            return await self._outcome(delivery)
        finally:
            self._forget(delivery)

    async def _outcome(self, d: _Delivery) -> OutboxResult:
        while not d.future.done():
            now = time.monotonic()
            if not d.handed_out:
                deadline = d.created + d.ttl
                if now >= deadline:
                    self._resolve(d, "expired_unpulled")
                    break
                if not self.live(d.connector_id):
                    self._resolve(d, "gone")
                    break
            else:
                deadline = d.handed_out + d.expires_in + self.ack_grace_s
                # The ReadTimeout of this channel: it may have gone out. A
                # connector that stopped pulling ends the wait early, since
                # the caller holds the conversation's send lock meanwhile.
                if now >= deadline or not self.live(d.connector_id):
                    self._resolve(d, "no_ack")
                    break
            await asyncio.wait(
                {d.future}, timeout=max(0.0, min(deadline - now, self.poll_s)))
        result = d.future.result()
        if result.status != "sent":
            logger.info("[Outbox] %s for %s ended %s (%d of %d items)",
                        d.reason, d.key, result.status, result.sent_items,
                        len(d.items))
        return result

    @staticmethod
    def _resolve(d: _Delivery, status: str, sent_items: int = 0) -> None:
        if not d.future.done():
            d.future.set_result(OutboxResult(status, sent_items))

    def _forget(self, d: _Delivery) -> None:
        queue = self._queues.get(d.key)
        if queue is not None:
            try:
                queue.remove(d)
                self._queued -= 1
            except ValueError:
                pass
            if not queue:
                self._queues.pop(d.key, None)
        self._handed.pop(d.delivery_id, None)

    # ---- the connector side --------------------------------------------

    def _ready(self, connector_id: str) -> list[_Delivery]:
        now = time.monotonic()
        return sorted(
            (d for queue in self._queues.values() for d in queue
             if d.connector_id == connector_id and not d.future.done()
             and now < d.created + d.ttl),
            key=lambda d: d.seq)

    def _hand_out(self, d: _Delivery, pull_no: int) -> dict:
        now = time.monotonic()
        self._queues[d.key].remove(d)
        self._queued -= 1
        if not self._queues[d.key]:
            self._queues.pop(d.key, None)
        d.handed_out = now
        d.handed_by = pull_no
        d.expires_in = max(1, int(d.created + d.ttl - now))
        self._handed[d.delivery_id] = d
        h = d.handle
        return {
            "delivery_id": d.delivery_id,
            "conversation_key": d.key,
            "reply_handle": h.get("reply_handle", ""),
            "platform": h.get("platform", ""),
            "conversation_type": h.get("conversation_type", ""),
            "conversation_id": h.get("conversation_id", ""),
            "reason": d.reason,
            "expires_in_s": d.expires_in,
            "items": d.items,
        }

    def ack(self, connector_id: str, ack) -> None:
        """Settle one handed-out delivery. Unknown, repeated or foreign acks
        are ignored: the delivery was handed out once and is settled once."""
        if not isinstance(ack, dict):
            return
        d = self._handed.get(str(ack.get("delivery_id") or ""))
        if d is None or d.connector_id != connector_id or d.future.done():
            return
        status = ack.get("status")
        total = len(d.items)
        if status == "sent":
            sent = total
        elif status == "partial":
            try:
                sent = min(max(int(ack.get("sent_items") or 0), 0), total)
            except (TypeError, ValueError, OverflowError):  # Infinity parses
                sent = 0
            status = ("sent" if sent >= total
                      else "partial" if sent else "failed")
        else:
            sent = 0
            if status not in ACK_STATUSES:
                status = "failed"
        if status == "unsupported":
            self.handles.mark_unsupported(d.key, d.handle.get("reply_handle", ""))
        self._handed.pop(d.delivery_id, None)
        self._resolve(d, status, sent)

    async def pull(self, connector_id: str, *, wait_s: float = DEFAULT_WAIT_S,
                   max_deliveries: int = 10, acks=(), disconnected=None) -> dict:
        """Settle `acks`, then hand out what is queued for this connector,
        holding the request up to `wait_s` seconds until something is.

        `disconnected`, when given, is awaited before handing anything out:
        a caller that has hung up gets nothing, and its deliveries wait for
        the next pull instead of being lost with the socket."""
        # Numbered rather than timed: a clock can give two pulls one tick.
        self._pulls += 1
        pull_no = self._pulls
        self._stamp(connector_id)
        for ack in acks or ():
            self.ack(connector_id, ack)
        # Acks come on the next pull, so what this connector was handed
        # before it and has not acked went to a pull that never got through:
        # a restarted connector's abandoned long-poll, or a lost response.
        # Settling it here frees the conversation's send lock now rather
        # than after expires_in plus the grace.
        for d in list(self._handed.values()):
            if d.connector_id == connector_id and d.handed_by < pull_no:
                self._handed.pop(d.delivery_id, None)
                self._resolve(d, "no_ack")
        wait_s = min(max(float(wait_s), 0.0), MAX_WAIT_S)
        limit = min(max(int(max_deliveries), 1), MAX_DELIVERIES_PER_PULL)
        cond = self._condition()
        async with cond:
            if not self._closed and wait_s > 0 and not self._ready(connector_id):
                try:
                    await asyncio.wait_for(
                        cond.wait_for(lambda: self._closed
                                      or bool(self._ready(connector_id))),
                        wait_s)
                except asyncio.TimeoutError:
                    pass
            gone = disconnected is not None and await disconnected()
            deliveries = [] if gone else [
                self._hand_out(d, pull_no) for d in self._ready(connector_id)[:limit]]
        self._stamp(connector_id)
        return {"deliveries": deliveries, "next_wait_s": DEFAULT_WAIT_S}

    async def aclose(self) -> None:
        """Settle every waiting delivery as not sent and release pulls."""
        self._closed = True
        for queue in list(self._queues.values()):
            for d in list(queue):
                self._resolve(d, "closed")
        for d in list(self._handed.values()):
            self._resolve(d, "closed")
        if self._cond is not None:
            await self._notify()
