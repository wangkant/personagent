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
from .gateway import current_sink

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
    message_ids: list[str] = field(default_factory=list)
    sticker_files: list[str] = field(default_factory=list)
    # The text the group actually saw. On a partial send this is the prefix
    # that posted before the failure — the caller has to commit it, because
    # from every reader's point of view the bot said it.
    delivered: str = ""


class Transport:
    """Mixed into Agent; see agent.py."""

    def _touch_gateway_conv(self, key: str) -> None:
        """Record a gateway conversation as active; past _MAX_GATEWAY_CONVS,
        evict the least-recently-active conversation's in-memory state. Only
        gateway keys are registered — QQ groups/DMs are whitelisted and
        naturally bounded, so they never enter (or get evicted from) the LRU.
        A conversation whose lock is currently held is skipped in favor of the
        next-oldest one."""
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
        if count <= _MAX_GATEWAY_CONVS:
            return
        for old in sorted(self._gateway_conv_lru, key=self._gateway_conv_lru.get):
            if old == key:
                continue
            if self._gateway_inflight.get(old, 0):
                continue
            lock = self.locks.get(old)
            send_lock = self.send_locks.get(old)
            if (lock and lock.locked()) or (send_lock and send_lock.locked()):
                continue  # mid-handling — try the next-oldest instead
            self._evict_conversation(old)
            break

    def _evict_conversation(self, key: str) -> None:
        """Drop all of a conversation's in-memory state (buffer / locks /
        counters / throttle window / ...).

        The persisted memories / core_memory / pending-reply rows under the
        same key are dropped too (`PendingReplies.drop_conversation` for the
        pending table): `_save_memories` / `_save_core_memory` rewrite the
        whole JSON dict, so they cannot preserve a key the in-memory dict no
        longer holds without a read-merge layer that is not worth building for
        a path that does not evict at volume. Only gateway conversations ever
        enter the LRU — QQ groups/DMs never do — so real user data on the QQ
        path is unaffected either way."""
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
            self.last_dm_activity_at.pop(uid, None)
            self.last_proactive_at.pop(reaction_key, None)
        # `reaction_key` IS `key` for a room, so the branch these two used to
        # sit in was spelling the same mapping twice more.
        self._last_elicit_at.pop(reaction_key, None)
        self.pending_reactions.drop_conversation(reaction_key)
        # Group-conversation memory key = the group_id itself; gateway DM
        # memory key = "private:<uid>" = key.
        had_memories = self.memories.pop(key, None) is not None
        had_core = self.core_memory.pop(key, None) is not None
        if had_memories:
            self._save_memories()
        if had_core:
            self._save_core_memory()
        logger.info("[Agent] gateway conversation evicted (over the %d cap): %s",
                    _MAX_GATEWAY_CONVS, key)

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
                    # Remember the outbound message_id: reaction learning needs
                    # it to attribute later quote-replies to this bot message.
                    try:
                        _mid = ((r.json() or {}).get("data") or {}).get("message_id")
                        if _mid is not None:
                            self._sent_mids.setdefault(mids_key, []).append(str(_mid))
                    except Exception:
                        pass
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
                                at_user_id: str = "", label: str = "") -> SendResult:
        """Send parsed (kind, value) segments one chunk at a time through
        ``send(message) -> bool``, stopping at the first failure so a reply is
        never split across a network gap. ``at_user_id`` is prefixed to the
        first chunk that actually goes out."""
        # Behind a sink these sleeps are invisible: the sink hands the whole
        # list back and the caller paces it itself. Only the split survives.
        collected = current_sink.get() is not None
        at_head = ([{"type": "at", "data": {"qq": str(at_user_id)}}]
                   if at_user_id else [])
        sendable = False
        sent_any = False
        delivered: list[str] = []
        failed = False
        sent_stickers: list[str] = []
        for kind, value in segments:
            if kind == "sticker":
                file_path = self.stickers.pick_by_tag(value)
                if not file_path or not file_path.exists():
                    logger.info("[Agent] sticker tag %r → no match, skipping%s",
                                value, label)
                    continue
                if not collected:
                    await asyncio.sleep(random.uniform(0.6, 1.4))
                try:
                    img_b64 = base64.b64encode(file_path.read_bytes()).decode()
                except Exception as e:
                    logger.warning("[Agent] sticker read failed (%s): %s", file_path, e)
                    failed = True
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
            for chunk in self._split_text(value):
                sendable = True
                # Delay before every chunk including the first — reads as
                # typing rather than an instant emit.
                if not collected:
                    await asyncio.sleep(self._typing_delay(chunk))
                if at_head:
                    message = at_head + [{"type": "text", "data": {"text": chunk}}]
                    at_head = []
                else:
                    message = chunk
                if not await send(message):
                    failed = True
                    logger.warning("[Agent] send aborted (text chunk failed), "
                                   "dropping remaining chunks (%s)", target_key)
                    break
                sent_any = True
                delivered.append(chunk)
            if failed:
                break
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
        text = self._sanitize_reply(text, self._validator_lang(), self.reply_style)
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
            self._parse_sticker_markers(text),
            partial(self._napcat_send_group, group_id),
            target_key=target_key, at_user_id=at_user_id)

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
        text = self._sanitize_reply(text, self._validator_lang(), self.reply_style)
        # Private chat is 1:1 — there's no "target someone" semantics. The
        # model still occasionally emits [AT:xxx] (STYLE_GUIDE teaches the
        # marker); the group path extracts it, private has no extractor — left
        # unstripped it would go out as literal text.
        text = re.sub(r'\[AT:[^\]\s]+\]', '', text).strip()
        if not text:
            return SendResult()
        return await self._deliver_segments(
            self._parse_sticker_markers(text),
            partial(self._napcat_send_private, user_id),
            target_key=target_key, label=" (private)")

    async def check_missed_mentions(self) -> None:
        """On startup, pull the most recent ~10 group messages; if any of them
        @ed or named the bot and weren't replied to, process one of them."""
        if not self.enabled:
            return
        # Single source of truth: allowed_groups is parsed from QQ_GROUPS in __init__.
        for group_id in list(self.buffers.keys()) or list(self.allowed_groups):
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
        replay idempotent."""
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
