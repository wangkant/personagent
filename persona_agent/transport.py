"""Outbound delivery: throttling, chunking, typing simulation, sends.

Also owns the connector conversation LRU, since that bounds the same
per-conversation state the send path writes."""

from __future__ import annotations

import asyncio
import base64
import logging
import random
import re
import time
from functools import partial

import httpx

from dataclasses import dataclass, field

from . import channels
from .connector import ConnectorSink, current_sink
from .outbox import OutboxResult
from .textproc import MAX_REPLY_MESSAGES, TextProcessing

logger = logging.getLogger("agent")


# Anti-flood: a jittered minimum gap between any two sends, plus a per-target
# cap per window.
_SEND_MIN_INTERVAL = 0.6

_SEND_JITTER = 0.5

_SEND_MAX_PER_MIN = 20

_SEND_WINDOW_SEC = 60.0

# Connector-chosen keys are capped, or a runaway connector grows every
# per-conversation dict forever; past it the least recently active is evicted.
_MAX_CONNECTOR_CONVS = 256

# Eviction is silent, so warn before the cap starts dropping dm_history.
_CONNECTOR_CONV_WARN_THRESHOLD = 200

@dataclass
class SendResult:
    """Outcome of one logical reply, which may contain several chunks."""

    success: bool = False
    partial: bool = False
    #: NapCat receipt ids; always empty behind a connector sink, so a group
    #: reaction there can only be matched by @, never by quote.
    message_ids: list[str] = field(default_factory=list)
    sticker_files: list[str] = field(default_factory=list)
    # What readers saw; on a partial send the caller commits this prefix.
    delivered: str = ""


def _acked_result(items: list, outcome: OutboxResult,
                  collected: SendResult) -> SendResult:
    """An outbox ack as a SendResult: the first `sent_items` items, no ids."""
    sent = outcome.sent_items if outcome.status in ("sent", "partial") else 0
    sent = min(max(sent, 0), len(items))
    texts = [item.get("text", "") for item in items[:sent]
             if item.get("type") == "text"]
    complete = sent == len(items)
    return SendResult(
        success=complete, partial=0 < sent < len(items),
        delivered="\n".join(texts),
        sticker_files=list(collected.sticker_files) if complete else [])


class Transport:
    """Mixed into Agent; see agent.py."""

    # Covers a restart; older @s may have left the seen-id ring and would be
    # answered again on every sweep.
    MISSED_MENTION_MAX_AGE_SEC = 3600

    def _touch_connector_conv(self, key: str) -> None:
        """Mark a connector conversation active and evict past the cap. QQ keys
        are whitelisted, hence bounded, and never enter the LRU."""
        self._connector_conv_lru.pop(key, None)
        self._connector_conv_lru[key] = time.monotonic()
        count = len(self._connector_conv_lru)
        # A flag, not `count == threshold`, which a steady count hits every message.
        if (count >= _CONNECTOR_CONV_WARN_THRESHOLD
                and not getattr(self, "_connector_conv_warned", False)):
            self._connector_conv_warned = True
            logger.warning(
                "[Agent] connector conversation count crossed %d (cap %d) for "
                "bot=%s; least-recently-active conversations will start "
                "losing their in-memory dm_history once the cap is hit",
                _CONNECTOR_CONV_WARN_THRESHOLD, _MAX_CONNECTOR_CONVS,
                self.qq_bot_id)
        self._trim_connector_convs(keep=key)

    def _trim_connector_convs(self, *, keep: str = "") -> None:
        """Reclaim idle state after admission or completion of a connector burst."""
        if len(self._connector_conv_lru) <= _MAX_CONNECTOR_CONVS:
            return
        # Insertion order is LRU order; snapshot, since eviction mutates it.
        for old in tuple(self._connector_conv_lru):
            if len(self._connector_conv_lru) <= _MAX_CONNECTOR_CONVS:
                break
            if old == keep:
                continue
            if self._connector_inflight.get(old, 0):
                continue
            lock = self.locks.get(old)
            send_lock = self.send_locks.get(old)
            if (lock and lock.locked()) or (send_lock and send_lock.locked()):
                continue  # mid-handling — try the next-oldest instead
            self._evict_conversation(old)

    def _evict_conversation(self, key: str) -> None:
        """Drop a conversation's in-memory state and pending reactions; its
        long-term memories stay."""
        self._connector_conv_lru.pop(key, None)
        for d in (self.locks, self.send_locks, self.buffers, self.counters,
                  self.last_reply_at, self.active_users, self._msg_seq,
                  self._vision_in_flight, self._sticky_call,
                  self.last_activity_at, self.last_proactive_at,
                  self._send_window, self._sent_mids):
            d.pop(key, None)
        pending = self._pending_outbound.pop(key, None)
        if pending is not None:
            pending.set()
        self._dm_send_tasks.pop(key, None)
        self._last_excuse_at.pop(key, None)
        self._send_window.pop(f"group:{key}", None)
        reaction_key = channels.learning_key(key)
        if channels.is_dm(key):
            uid = key.split(":", 1)[1]
            self.dm_history.pop(uid, None)
            self._dm_unanswered.pop(uid, None)
            self.last_dm_activity_at.pop(uid, None)
            self.last_proactive_at.pop(reaction_key, None)
        # For a room `reaction_key` is `key`.
        self._last_elicit_at.pop(reaction_key, None)
        self.pending_reactions.drop_conversation(reaction_key)
        logger.info("[Agent] connector conversation evicted (over the %d cap): %s",
                    _MAX_CONNECTOR_CONVS, key)

    @staticmethod
    def _typing_delay(chunk: str) -> float:
        """Simulate human typing speed: ~6-8 chars/sec + small pause. Capped at 7s."""
        chars_per_sec = random.uniform(6.0, 8.0)
        base = len(chunk) / chars_per_sec
        pause = random.uniform(0.4, 1.2)
        return min(base + pause, 7.0)

    async def _throttle_send(self, target_key: str) -> bool:
        """Wait out the global gap; False when the target's window is full (the
        caller aborts the rest of the reply). Holds only `_send_gate`."""
        async with self._send_gate:
            now = time.monotonic()
            wait = self._last_send_mono + _SEND_MIN_INTERVAL + random.uniform(0, _SEND_JITTER) - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
            w = self._send_window[target_key]
            while w and w[0] < now - _SEND_WINDOW_SEC:
                w.popleft()
            if len(w) >= _SEND_MAX_PER_MIN:
                logger.warning("[Agent] outbound throttle hit (%s, %d/%ds), dropping message",
                               target_key, len(w), int(_SEND_WINDOW_SEC))
                return False
            w.append(now)
            self._last_send_mono = now
            return True

    def _send_budget(self, throttle_key: str) -> int:
        """Sends `_throttle_send` would still accept for this target (read-only)."""
        now = time.monotonic()
        w = self._send_window.get(throttle_key) or ()
        return _SEND_MAX_PER_MIN - sum(1 for t in w if t >= now - _SEND_WINDOW_SEC)

    async def _onebot_send(self, endpoint: str, id_field: str, target_id: str,
                           message, *, throttle_key: str, mids_key: str,
                           label: str) -> bool:
        """POST one message (text or segments) to NapCat, retrying connect
        errors; False stops the rest of the reply."""
        sink = current_sink.get()
        if sink is not None:
            return sink.add(message)
        if not self.qq_onebot_url:
            if "\x00onebot" not in self._no_route_logged:
                self._no_route_logged["\x00onebot"] = None
                logger.warning("[Agent] cannot send a %s message to QQ: "
                               "QQ_ONEBOT_URL (NapCat's HTTP server) is not set",
                               label)
            return False
        if not await self._throttle_send(throttle_key):
            return False
        attempts = 3  # 1 initial + 2 retries
        for attempt in range(attempts):
            try:
                async with self._local_http(timeout=10) as client:
                    r = await client.post(
                        f"{self.qq_onebot_url}/{endpoint}",
                        json={id_field: int(target_id), "message": message},
                    )
                if r.status_code == 200:
                    # OneBot answers 200 for failed and queued actions too: only
                    # an ok with a receipt counts as delivered.
                    result = r.json()
                    if (not isinstance(result, dict)
                            or result.get("status") != "ok"
                            or type(result.get("retcode")) is not int
                            or result["retcode"] != 0):
                        logger.warning("[Agent] NapCat %s did not confirm delivery", label)
                        return False
                    data = result.get("data")
                    mid = data.get("message_id") if isinstance(data, dict) else None
                    if (type(mid) not in (int, str)
                            or not str(mid).strip()):
                        logger.warning("[Agent] NapCat %s returned no message receipt", label)
                        return False
                    self._sent_mids.setdefault(mids_key, []).append(str(mid))
                    return True
                logger.warning("[Agent] NapCat %s returned %d: %s",
                               label, r.status_code, r.text[:200])
                return False
            except (httpx.ConnectError, httpx.ConnectTimeout,
                    httpx.PoolTimeout) as e:
                if attempt == attempts - 1:
                    logger.warning("[Agent] send %s msg failed after %d attempts: %s",
                                   label, attempts, e)
                    return False
                await asyncio.sleep(0.5 * (attempt + 1))
            except (httpx.ReadTimeout, httpx.WriteTimeout) as e:
                # Maybe delivered: a retry could post the message twice.
                logger.warning("[Agent] send %s msg outcome unknown; not retrying: %s",
                               label, e)
                return False
            except Exception as e:
                logger.warning("[Agent] send %s msg failed: %s", label, e)
                return False
        return False

    async def _onebot_send_group(self, group_id: str, message) -> bool:
        return await self._onebot_send(
            "send_group_msg", "group_id", group_id, message,
            throttle_key=f"group:{group_id}", mids_key=group_id, label="group")

    async def _onebot_send_dm(self, user_id: str, message) -> bool:
        key = channels.dm_routing_key(user_id)
        return await self._onebot_send(
            "send_private_msg", "user_id", user_id, message,
            throttle_key=key, mids_key=key, label="DM")

    async def _deliver_segments(self, segments, send, *, target_key: str,
                                at_user_id: str = "", label: str = "",
                                throttle_key: str = "") -> SendResult:
        """Send (kind, value) segments one message at a time through
        ``send(message) -> bool``, stopping at the first failure; ``at_user_id``
        prefixes the first message that goes out."""
        # Behind a sink nothing sleeps: the connector paces the replies itself.
        collected = current_sink.get() is not None
        # Fold the overflow where the throttle still accepts it, rather than
        # losing the tail to a refusal.
        cap = MAX_REPLY_MESSAGES
        if not collected and throttle_key:
            cap = min(cap, self._send_budget(throttle_key))
        at_head = ([{"type": "at", "data": {"qq": str(at_user_id)}}]
                   if at_user_id else [])
        sendable = False
        sent_any = False
        delivered: list[str] = []
        failed = False
        sent_stickers: list[str] = []
        # Never the same sticker twice in one reply.
        used_md5s: set[str] = set()
        for kind, value in TextProcessing._delivery_units(segments, cap):
            if kind == "sticker":
                file_path = self.stickers.pick_by_tag(value, exclude_md5s=used_md5s)
                if not file_path:
                    logger.info("[Agent] sticker tag %r → no match, skipping%s",
                                value, label)
                    continue
                rel = file_path.relative_to(self.stickers.dir).as_posix()
                used_md5s.add(self.stickers.entries[rel].get("md5", ""))
                if not collected:
                    await asyncio.sleep(random.uniform(0.6, 1.4))
                img_b64 = base64.b64encode(file_path.read_bytes()).decode()
                sendable = True
                message = at_head + [
                    {"type": "image", "data": {"file": f"base64://{img_b64}"}}]
                at_head = []
                if not await send(message):
                    failed = True
                    logger.warning("[Agent] send aborted (sticker chunk failed), "
                                   "dropping remaining segments (%s)", target_key)
                    break
                sent_any = True
                sent_stickers.append(rel)
                continue
            sendable = True
            if not collected:
                await asyncio.sleep(self._typing_delay(value))
            if at_head:
                message = at_head + [{"type": "text", "data": {"text": value}}]
                at_head = []
            else:
                message = value
            if not await send(message):
                failed = True
                logger.warning("[Agent] send aborted (text chunk failed), "
                               "dropping remaining chunks (%s)", target_key)
                break
            sent_any = True
            delivered.append(value)
        return SendResult(
            success=sendable and not failed,
            partial=sent_any and failed,
            delivered=chr(10).join(delivered),
            message_ids=list(self._sent_mids.get(target_key, [])),
            sticker_files=sent_stickers,
        )

    async def _send_group(self, group_id: str, text: str,
                       at_user_id: str = "") -> SendResult:
        """Send a reply (text and [STICKER:tag] markers) to a group."""
        target_key = group_id
        self._sent_mids[target_key] = []
        text = TextProcessing._sanitize_reply(
            text, self.agent_lang, self.reply_style)
        if not text:
            return SendResult()
        # On QQ an at target must be a number; connector ids pass as they are.
        if at_user_id and not at_user_id.isdigit() and current_sink.get() is None:
            logger.warning("[Agent] dropping non-numeric at target %r (group=%s)",
                           at_user_id, group_id)
            at_user_id = ""
        return await self._deliver_segments(
            TextProcessing._parse_sticker_markers(text),
            partial(self._onebot_send_group, group_id),
            target_key=target_key, at_user_id=at_user_id,
            throttle_key=f"group:{group_id}")

    async def _send_dm(self, user_id: str, text: str) -> SendResult:
        """Send a DM under its send lock, unless this task already holds it."""
        key = channels.dm_routing_key(user_id)
        if self._dm_send_tasks.get(key) is asyncio.current_task():
            return await self._send_dm_unlocked(user_id, text)
        async with self.send_locks[key]:
            return await self._send_dm_unlocked(user_id, text)

    async def _send_dm_unlocked(
            self, user_id: str, text: str) -> SendResult:
        target_key = channels.dm_routing_key(user_id)
        self._sent_mids[target_key] = []
        text = TextProcessing._sanitize_reply(
            text, self.agent_lang, self.reply_style)
        # A DM has no mention: strip stray [AT:] markers.
        text = re.sub(r'\[AT:[^\]\s]+\]', '', text).strip()
        if not text:
            return SendResult()
        return await self._deliver_segments(
            TextProcessing._parse_sticker_markers(text),
            partial(self._onebot_send_dm, user_id),
            target_key=target_key, label=" (DM)",
            throttle_key=target_key)

    def _background_route(self, key: str):
        """How an unprompted message reaches `key`: the outbox handle, else
        "onebot" for a QQ key, else None."""
        route = self.outbox.route(key) if self.connector_outbox_enabled else None
        if route is None and channels.is_native(key) and self.qq_onebot_url:
            return "onebot"
        return route

    async def _send_background(self, key: str, send, *,
                               reason: str) -> SendResult:
        """Run `send()` for `key` with no inbound request open. The inherited
        (closed) sink is replaced: none for NapCat, a fresh one whose items
        become one outbox delivery, counted as acked. `reason`: proactive,
        follow_up or excuse."""
        route = self._background_route(key)
        if route is None:
            why = ("QQ_ONEBOT_URL is not set and no connector pulls the outbox "
                   "for it" if channels.is_native(key) and not self.qq_onebot_url
                   else "its connector does not pull the outbox, or has stopped")
            self._log_no_route(key, reason, why=why)
            return SendResult()
        if route == "onebot":
            tok = current_sink.set(None)
            try:
                return await send()
            finally:
                current_sink.reset(tok)
        collector = ConnectorSink(platform=route["platform"],
                                native=route["native"],
                                bot_id=self._self_mention_id())
        tok = current_sink.set(collector)
        try:
            collected = await send()
        finally:
            collector.closed = True
            current_sink.reset(tok)
        if not collector.items:
            return collected
        outcome = await self.outbox.deliver(
            key, route, collector.items, reason=reason)
        return _acked_result(collector.items, outcome, collected)

    def _log_no_route(self, key: str, reason: str, *,
                      why: str = "its connector does not pull the outbox, "
                                 "or has stopped") -> None:
        marker = f"{key}\x00{reason}"
        if marker in self._no_route_logged:
            return
        self._no_route_logged[marker] = None
        if len(self._no_route_logged) > 1024:
            self._no_route_logged.pop(next(iter(self._no_route_logged)))
        logger.info("[Agent] no way to send the %s to %s unprompted: %s",
                    reason.replace("_", "-"), key, why)

    def _missed_mention_sweep_on(self) -> bool:
        if not (self.enabled and self.qq_onebot_url):
            return False
        if not self.qq_bot_id:
            if not getattr(self, "_sweep_off_logged", False):
                self._sweep_off_logged = True
                logger.info("[Agent] missed-mention sweep is off: QQ_BOT_ID "
                            "is not set")
            return False
        return True

    async def check_missed_mentions(self) -> None:
        """Replay one unanswered recent @ or name-call per QQ group from the
        last 10 messages (needs QQ_ONEBOT_URL and QQ_BOT_ID)."""
        if not self._missed_mention_sweep_on():
            return
        # Both: a missed @ is in a group with no traffic this run.
        for group_id in dict.fromkeys(
                list(self.buffers.keys()) + list(self._group_allowlist())):
            # Connector conversations cannot be polled.
            if ":" in group_id:
                continue
            try:
                async with self._local_http(timeout=15) as client:
                    r = await client.post(
                        f"{self.qq_onebot_url}/get_group_msg_history",
                        json={"group_id": int(group_id), "count": 10},
                    )
                    r.raise_for_status()
                    msgs = (r.json().get("data") or {}).get("messages", [])
                    for msg in reversed(msgs):
                        # str(): history ids are ints, the ring holds strings.
                        mid = msg.get("message_id")
                        if mid is not None and str(mid) in self._seen_msg_ids:
                            continue
                        sender_id = str((msg.get("sender") or {}).get("user_id", ""))
                        if sender_id == self.qq_bot_id:
                            continue
                        ts = msg.get("time")
                        if (isinstance(ts, (int, float))
                                and time.time() - ts
                                > self.MISSED_MENTION_MAX_AGE_SEC):
                            continue
                        raw = msg.get("raw_message", "")
                        # An @ arrives as a CQ code, so match both forms.
                        if (self._names_me(raw)
                                or f"@{self.qq_bot_id}" in raw
                                or f"[CQ:at,qq={self.qq_bot_id}]" in raw):
                            logger.info("[Agent] missed offline @-mention detected; replaying (group=%s)", group_id)
                            await self.handle_onebot(msg)
                            break
            except Exception as e:
                logger.warning("[Agent] missed-mention check failed (group=%s): %s", group_id, e)

    async def loop_check_missed(self, interval: int = 1800) -> None:
        """Re-run check_missed_mentions every `interval` s: NapCat can drop
        webhooks across restarts."""
        if not self._missed_mention_sweep_on():
            return
        while True:
            try:
                await asyncio.sleep(interval)
                await self.check_missed_mentions()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.warning("[Agent] loop_check_missed iteration failed: %s", e)
