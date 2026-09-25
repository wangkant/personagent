"""Outbound delivery: throttling, chunking, typing simulation, sends.

Also owns the gateway conversation LRU, since that bounds the same
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
from .gateway import GatewaySink, current_sink
from .outbox import OutboxResult
from .textproc import MAX_REPLY_MESSAGES, TextProcessing

logger = logging.getLogger("agent")


# Outbound send throttle (anti-flood / platform rate-control): a minimum gap
# between any two outbound messages (jittered upper bound) plus a per-target
# cap per 60s window. Sentence pacing inside a single reply is already handled
# by the typing simulation; this mainly stops "several groups fire at the same
# instant" cross-group bursts and per-target flooding.
_SEND_MIN_INTERVAL = 0.6

_SEND_JITTER = 0.5

_SEND_MAX_PER_MIN = 20

_SEND_WINDOW_SEC = 60.0

# Gateway conversation cap: QQ groups/DMs are whitelisted so their key count
# is naturally bounded, but gateway conversation keys ("<platform>:<id>") are
# chosen by the forwarder — without a cap a runaway or malicious forwarder can
# mint new keys forever and grow the per-conversation dicts (buffers/locks/
# counters/throttle windows/...) without bound. Past the cap the least-
# recently-active gateway conversation is evicted (see _touch_gateway_conv).
_MAX_GATEWAY_CONVS = 256

# Warn well before the cap bites: an operator seeing "it forgot our
# conversation" reports has no error to grep for today (eviction is a normal,
# silent cache-capacity decision, not a bug) -- this is the one signal that a
# deployment is approaching the point where _evict_conversation starts
# dropping `private_history` for its least-recently-active conversations.
_GATEWAY_CONV_WARN_THRESHOLD = 200

@dataclass
class SendResult:
    """Outcome of one logical reply, which may contain several chunks."""

    success: bool = False
    partial: bool = False
    #: Receipt ids for the chunks that went out. ALWAYS EMPTY behind a gateway
    #: sink: `_napcat_send` diverts into the sink and returns before the
    #: receipt is parsed, and the forwarder only learns the platform's own
    #: message id after the HTTP response is already on its way back (the
    #: outbound reply item has no id field to carry it). Consequence, and it
    #: is narrower than it looks: `reactions.PendingReplies.match`'s
    #: `quote_mid` path can never hit on a forwarded platform, so a reaction
    #: there is attributable only by the `at_bot` fallback. DM replies are
    #: unaffected — that path passes no `quote_mid` on any platform. Not a
    #: defect to fix here: the synchronous round-trip is deliberate.
    message_ids: list[str] = field(default_factory=list)
    sticker_files: list[str] = field(default_factory=list)
    # The text the group actually saw. On a partial send this is the prefix
    # that posted before the failure — the caller has to commit it, because
    # from every reader's point of view the bot said it.
    delivered: str = ""


def _acked_result(items: list, outcome: OutboxResult,
                  collected: SendResult) -> SendResult:
    """What an outbox delivery put in front of people, as a SendResult: the
    first `sent_items` items and nothing past them. No message ids: an ack
    carries none."""
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

    # The oldest @ check_missed_mentions will still replay. Long enough to
    # cover a restart or a NapCat reconnect; short enough that an @ the
    # seen-id ring has since forgotten (busy groups can cycle it within the
    # half-hour between sweeps) is not answered again on every later sweep.
    MISSED_MENTION_MAX_AGE_SEC = 3600

    def _touch_gateway_conv(self, key: str) -> None:
        """Record a gateway conversation as active; past _MAX_GATEWAY_CONVS,
        evict the least-recently-active conversation's in-memory state. Only
        gateway keys are registered — QQ groups/DMs are whitelisted and
        naturally bounded, so they never enter (or get evicted from) the LRU.
        A conversation whose lock is currently held is skipped in favor of the
        next-oldest one."""
        self._gateway_conv_lru.pop(key, None)
        self._gateway_conv_lru[key] = time.monotonic()
        count = len(self._gateway_conv_lru)
        # One-shot flag, not `count == threshold`: re-touching an existing key
        # leaves len() unchanged, so the equality would fire on every message
        # once the count settles at the threshold.
        if (count >= _GATEWAY_CONV_WARN_THRESHOLD
                and not getattr(self, "_gateway_conv_warned", False)):
            self._gateway_conv_warned = True
            logger.warning(
                "[Agent] gateway conversation count crossed %d (cap %d) for "
                "bot=%s; least-recently-active conversations will start "
                "losing their in-memory private_history once the cap is hit",
                _GATEWAY_CONV_WARN_THRESHOLD, _MAX_GATEWAY_CONVS,
                self.bot_qq)
        self._trim_gateway_convs(keep=key)

    def _trim_gateway_convs(self, *, keep: str = "") -> None:
        """Reclaim idle state after admission or completion of a gateway burst."""
        if len(self._gateway_conv_lru) <= _MAX_GATEWAY_CONVS:
            return
        # Touching a key moves it to the end, so insertion order is LRU order.
        # Snapshot because eviction removes entries while we walk the cache.
        for old in tuple(self._gateway_conv_lru):
            if len(self._gateway_conv_lru) <= _MAX_GATEWAY_CONVS:
                break
            if old == keep:
                continue
            if self._gateway_inflight.get(old, 0):
                continue
            lock = self.locks.get(old)
            send_lock = self.send_locks.get(old)
            if (lock and lock.locked()) or (send_lock and send_lock.locked()):
                continue  # mid-handling — try the next-oldest instead
            self._evict_conversation(old)

    def _evict_conversation(self, key: str) -> None:
        """Drop all of a conversation's in-memory state (buffer / locks /
        counters / throttle window / ...).

        Pending reactions expire with the session. Long-term memories remain
        in their authoritative maps and files: a cache capacity decision must
        not erase learned facts or cause the next whole-file save to do so."""
        self._gateway_conv_lru.pop(key, None)
        for d in (self.locks, self.send_locks, self.buffers, self.counters,
                  self.last_reply_at, self.active_users, self._msg_seq,
                  self._vision_in_flight, self._sticky_call,
                  self.last_activity_at, self.last_proactive_at,
                  self._send_window, self._sent_mids):
            d.pop(key, None)
        pending = self._pending_outbound.pop(key, None)
        if pending is not None:
            pending.set()
        self._private_send_owners.pop(key, None)
        self._send_window.pop(f"group:{key}", None)
        # Through `channels`, not spelled here: this was the third independent
        # copy of the private: -> dm: step and the other two had drifted.
        reaction_key = channels.learning_key(key)
        if channels.is_dm(key):
            uid = key.split(":", 1)[1]
            self.private_history.pop(uid, None)
            self._dm_unanswered.pop(uid, None)
            self.last_dm_activity_at.pop(uid, None)
            self.last_proactive_at.pop(reaction_key, None)
        # `reaction_key` IS `key` for a room, so the branch these two used to
        # sit in was spelling the same mapping twice more.
        self._last_elicit_at.pop(reaction_key, None)
        self.pending_reactions.drop_conversation(reaction_key)
        logger.info("[Agent] gateway conversation evicted (over the %d cap): %s",
                    _MAX_GATEWAY_CONVS, key)

    @staticmethod
    def _typing_delay(chunk: str) -> float:
        """Simulate human typing speed: ~6-8 chars/sec + small pause. Capped at 7s."""
        chars_per_sec = random.uniform(6.0, 8.0)
        base = len(chunk) / chars_per_sec
        pause = random.uniform(0.4, 1.2)
        return min(base + pause, 7.0)

    async def _throttle_send(self, target_key: str) -> bool:
        """Outbound send throttle (anti-flood / platform rate-control). A
        global minimum interval (jittered) stops cross-group simultaneous
        bursts; a per-target sliding window stops flooding one target. Returns
        False = per-target cap exceeded; the caller treats it as a send failure
        and aborts the remaining chunks. Gateway sink replies don't come
        through here (the sink branch returns earlier).

        Holds only self._send_gate (and only while waiting) — never acquires a
        group lock or send_lock, so it can't reintroduce the old
        "group lock held across a send" bug. send_locks stay the upper
        per-conversation ordering layer."""
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
        """How many sends `_throttle_send` would still accept for this target
        right now. Read-only: `.get` so asking does not mint a window."""
        now = time.monotonic()
        w = self._send_window.get(throttle_key) or ()
        return _SEND_MAX_PER_MIN - sum(1 for t in w if t >= now - _SEND_WINDOW_SEC)

    async def _napcat_send(self, endpoint: str, id_field: str, target_id: str,
                           message, *, throttle_key: str, mids_key: str,
                           label: str) -> bool:
        """POST one message to NapCat with a small bounded retry on
        connect/timeout errors. message: str or list of segments. Returns True
        on success so callers can stop emitting later chunks on a hard failure
        (truncated / out-of-order replies, silently dropped DMs)."""
        sink = current_sink.get()
        if sink is not None:
            # Gateway capture: hand the reply back over HTTP instead of
            # posting to NapCat (gateway ids aren't ints anyway).
            return sink.add(message)
        if not await self._throttle_send(throttle_key):
            return False
        attempts = 3  # 1 initial + 2 retries
        for attempt in range(attempts):
            try:
                async with self._local_http(timeout=10) as client:
                    r = await client.post(
                        f"{self.napcat_api}/{endpoint}",
                        json={id_field: int(target_id), "message": message},
                    )
                if r.status_code == 200:
                    # OneBot also returns HTTP 200 for failed and queued actions.
                    # Only a synchronous success with a receipt can be committed
                    # as delivered or attributed to later reaction evidence.
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
                # Non-200 is a server-side reject, not a transient network
                # error — retrying rarely helps, so log and stop.
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
                # The peer may have accepted the request before its response
                # was lost. Retrying an ambiguous timeout duplicates a chat
                # message, so fail this logical chunk instead of replaying it.
                logger.warning("[Agent] send %s msg outcome unknown; not retrying: %s",
                               label, e)
                return False
            except Exception as e:
                logger.warning("[Agent] send %s msg failed: %s", label, e)
                return False
        return False

    async def _napcat_send_group(self, group_id: str, message) -> bool:
        return await self._napcat_send(
            "send_group_msg", "group_id", group_id, message,
            throttle_key=f"group:{group_id}", mids_key=group_id, label="group")

    async def _napcat_send_private(self, user_id: str, message) -> bool:
        key = channels.dm_routing_key(user_id)
        return await self._napcat_send(
            "send_private_msg", "user_id", user_id, message,
            throttle_key=key, mids_key=key, label="private")

    async def _deliver_segments(self, segments, send, *, target_key: str,
                                at_user_id: str = "", label: str = "",
                                throttle_key: str = "") -> SendResult:
        """Send parsed (kind, value) segments one message at a time through
        ``send(message) -> bool``, stopping at the first failure so a reply is
        never split across a network gap. ``at_user_id`` is prefixed to the
        first message that actually goes out. How many messages one reply
        becomes is capped in ``TextProcessing._delivery_units``; on NapCat
        the cap is also held to what ``throttle_key``'s window will accept."""
        # Behind a sink these sleeps are invisible: the sink hands the whole
        # list back and the caller paces it itself. Only the split survives.
        collected = current_sink.get() is not None
        # The per-target throttle refuses the 21st send in a minute, and a
        # refusal ends the reply: under the plain cap of 24, a runaway reply
        # of short lines lost its 21st-24th messages, the folded overflow
        # among them. Fold where the throttle will still let the message
        # through. Taken once up front, the budget only grows while the
        # reply goes out (old stamps age out), and send_locks keep any other
        # reply to this target from spending it in the meantime.
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
        # One reply can carry several [STICKER:] markers, and pick_by_tag's own
        # cooldown cannot help here: it stamps the winner only after returning,
        # so a second marker for a narrow tag re-picks the same image through
        # the cooled-down fallback. Sending the same sticker twice in one breath
        # is the tell that there is a bot on the other end.
        used_md5s: set[str] = set()
        for kind, value in TextProcessing._delivery_units(segments, cap):
            if kind == "sticker":
                file_path = self.stickers.pick_by_tag(value, exclude_md5s=used_md5s)
                if not file_path or not file_path.exists():
                    logger.info("[Agent] sticker tag %r → no match, skipping%s",
                                value, label)
                    continue
                picked_md5 = str(
                    (self.stickers.entries.get(file_path.name) or {}).get("md5", ""))
                if picked_md5:
                    used_md5s.add(picked_md5)
                if not collected:
                    await asyncio.sleep(random.uniform(0.6, 1.4))
                try:
                    img_b64 = base64.b64encode(file_path.read_bytes()).decode()
                except Exception as e:
                    # Skipped, not failed — the same local miss as the
                    # .exists() check above, one step later. `failed` means the
                    # NETWORK stopped mid-reply: it breaks out of the remaining
                    # segments and makes the caller withhold the core-memory,
                    # auto-memory and eval commit. None of that is right for
                    # text the group has already read.
                    logger.warning("[Agent] sticker read failed (%s): %s", file_path, e)
                    continue
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
                try:
                    sent_stickers.append(
                        str(file_path.relative_to(self.stickers.dir)).replace("\\", "/"))
                except ValueError:
                    pass
                continue
            sendable = True
            # Delay before every chunk including the first — reads as
            # typing rather than an instant emit.
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

    async def _send_qq(self, group_id: str, text: str,
                       at_user_id: str = "") -> SendResult:
        """Send a reply (possibly mixed text + [STICKER:tag] markers) to the
        group. Returns full/partial delivery state, NapCat message IDs, and
        sticker filenames used by reaction learning and quality evaluation."""
        # Fresh mid list for this call; _napcat_send_group appends each sent
        # chunk's message_id (same-group sends are serialized by send_locks).
        target_key = group_id
        self._sent_mids[target_key] = []
        text = TextProcessing._sanitize_reply(
            text, self._validator_lang(), self.reply_style)
        if not text:
            return SendResult()
        # On the QQ path an at target must be a bare QQ number — a hallucinated
        # non-numeric [AT:] marker would produce a broken NapCat at segment, so
        # drop the mention (the marker text was already stripped upstream).
        # Gateway sends keep prefixed ids like "telegram:12345" as-is.
        if at_user_id and not at_user_id.isdigit() and current_sink.get() is None:
            logger.warning("[Agent] dropping non-numeric at target %r (group=%s)",
                           at_user_id, group_id)
            at_user_id = ""
        return await self._deliver_segments(
            TextProcessing._parse_sticker_markers(text),
            partial(self._napcat_send_group, group_id),
            target_key=target_key, at_user_id=at_user_id,
            throttle_key=f"group:{group_id}")

    async def _send_private_qq(self, user_id: str, text: str) -> SendResult:
        """Serialize standalone private sends.

        Full private conversation paths already hold this lock across delivery
        and state commit and call ``_send_private_qq_unlocked`` directly.
        Background callers (for example delayed elicitation) use this wrapper.
        """
        key = channels.dm_routing_key(user_id)
        if self._private_send_owners.get(key) is asyncio.current_task():
            return await self._send_private_qq_unlocked(user_id, text)
        async with self.send_locks[key]:
            return await self._send_private_qq_unlocked(user_id, text)

    async def _send_private_qq_unlocked(
            self, user_id: str, text: str) -> SendResult:
        target_key = channels.dm_routing_key(user_id)
        self._sent_mids[target_key] = []
        text = TextProcessing._sanitize_reply(
            text, self._validator_lang(), self.reply_style)
        # Private chat is 1:1 — there's no "target someone" semantics. The
        # model still occasionally emits [AT:xxx] (STYLE_GUIDE teaches the
        # marker); the group path extracts it, private has no extractor — left
        # unstripped it would go out as literal text.
        text = re.sub(r'\[AT:[^\]\s]+\]', '', text).strip()
        if not text:
            return SendResult()
        return await self._deliver_segments(
            TextProcessing._parse_sticker_markers(text),
            partial(self._napcat_send_private, user_id),
            target_key=target_key, label=" (private)",
            throttle_key=target_key)

    def _background_route(self, key: str):
        """How a message no request is waiting for reaches routing key `key`.

        "onebot" for a QQ key, which goes to NapCat as it always has; the
        stored handle when a live connector pulls the outbox for it; None
        when nothing can deliver there unprompted."""
        if channels.is_native(key):
            return "onebot"
        if not self.gateway_outbox:
            return None
        return self.outbox.route(key)

    async def _send_background(self, key: str, send, *,
                               reason: str) -> SendResult:
        """Run `send()` (a _send_qq or _send_private_qq call) for `key` when
        no inbound request is open to answer in.

        A task spawned by a gateway turn inherits that turn's sink, closed by
        now, so the sink is replaced either way: with none on the QQ route,
        so NapCat is reached, and with a fresh one on the outbox route, whose
        items become one delivery. The result counts only what the connector
        acked as sent. `reason` is the outbox's: proactive, follow_up or
        excuse."""
        route = self._background_route(key)
        if route is None:
            self._log_no_route(key, reason)
            return SendResult()
        if route == "onebot":
            tok = current_sink.set(None)
            try:
                return await send()
            finally:
                current_sink.reset(tok)
        collector = GatewaySink(platform=route["platform"],
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

    def _log_no_route(self, key: str, reason: str) -> None:
        marker = f"{key}\x00{reason}"
        if marker in self._no_route_logged:
            return
        self._no_route_logged[marker] = None
        if len(self._no_route_logged) > 1024:
            self._no_route_logged.pop(next(iter(self._no_route_logged)))
        logger.info("[Agent] no way to send the %s to %s unprompted: its "
                    "connector does not pull the outbox, or has stopped",
                    reason.replace("_", "-"), key)

    async def check_missed_mentions(self) -> None:
        """On startup, pull the most recent ~10 group messages; if any of them
        @ed or named the bot within MISSED_MENTION_MAX_AGE_SEC and weren't
        replied to, process one of them.

        The seen-id ring is the only record of what was replied to, and it
        holds the last 2000 ids across every conversation, so busy groups
        push a quiet group's old @ out of it. The age bound is what stops that
        @ from being answered again on every sweep; a message without a
        timestamp is replayed as before."""
        if not self.enabled:
            return
        # Both, not `buffers or allowed_groups`: buffers gains a key for ANY
        # conversation with traffic — a DM included — so the `or` stopped
        # consulting the whitelist the moment one message arrived anywhere.
        # A missed @ is by definition in a group with no traffic this run,
        # which is exactly the group that fell out of the poll.
        for group_id in dict.fromkeys(
                list(self.buffers.keys()) + list(self._group_allowlist())):
            # Gateway conversations ("<platform>:<id>") are inbound-only; the
            # NapCat history API can't poll them (and int() would crash).
            if ":" in group_id:
                continue
            try:
                async with self._local_http(timeout=15) as client:
                    r = await client.post(
                        f"{self.napcat_api}/get_group_msg_history",
                        json={"group_id": int(group_id), "count": 10},
                    )
                    r.raise_for_status()
                    # `or {}` because the protocol can return "data": null.
                    msgs = (r.json().get("data") or {}).get("messages", [])
                    for msg in reversed(msgs):
                        # Skip messages already processed in a previous run
                        # / poll. Without this, the same offline @ mention
                        # would log "replaying" every 30 minutes even though
                        # handle() short-circuits via the seen-id ring.
                        # str(): NapCat's history carries an int here while
                        # the ring is keyed on the webhook path's string —
                        # see the dedup gate in agent.handle().
                        mid = msg.get("message_id")
                        if mid is not None and str(mid) in self._seen_msg_ids:
                            continue
                        sender_id = str((msg.get("sender") or {}).get("user_id", ""))
                        if sender_id == self.bot_qq:
                            continue
                        ts = msg.get("time")
                        if (isinstance(ts, (int, float))
                                and time.time() - ts
                                > self.MISSED_MENTION_MAX_AGE_SEC):
                            continue
                        raw = msg.get("raw_message", "")
                        # @s arrive in raw_message as CQ codes ([CQ:at,qq=...]);
                        # matching only "@<qq>" never hits, so match both forms.
                        if ((self.bot_name and self.bot_name in raw)
                                or f"@{self.bot_qq}" in raw
                                or f"[CQ:at,qq={self.bot_qq}]" in raw):
                            logger.info("[Agent] missed offline @-mention detected; replaying (group=%s)", group_id)
                            await self.handle(msg)
                            break
            except Exception as e:
                logger.warning("[Agent] missed-mention check failed (group=%s): %s", group_id, e)

    async def loop_check_missed(self, interval: int = 1800) -> None:
        """Periodic catch-up loop. NapCat can drop webhooks during reboots / restarts;
        every `interval` seconds we re-poll recent group history and replay any @-mention
        that didn't go through handle() yet. The message_id ring in handle() makes the
        replay idempotent while the id is still in the ring; an @ older than
        MISSED_MENTION_MAX_AGE_SEC is not replayed at all, so one the ring has
        forgotten is not answered on every later sweep."""
        if not self.enabled:
            return
        while True:
            try:
                await asyncio.sleep(interval)
                await self.check_missed_mentions()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.warning("[Agent] loop_check_missed iteration failed: %s", e)
