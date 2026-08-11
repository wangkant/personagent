"""Outbound delivery: throttling, chunking, typing simulation, sends.

Also owns the gateway conversation LRU, since that bounds the same
per-conversation state the send path writes."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import heapq
import io
import ipaddress
import json
import logging
import os
import random
import re
import socket
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Optional
from urllib.parse import urlencode, urlsplit

import httpx

from dataclasses import dataclass, field

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
        # A one-bit "already warned" flag, NOT a `count == threshold`
        # transition check: `dict[key] = value` on an EXISTING key (the
        # common case -- most touches are a conversation that was already
        # in the LRU, and this method runs on every touch, several times
        # per gateway message) does not change len(). Once a deployment's
        # live conversation count settles AT or ABOVE the threshold,
        # `count == _GATEWAY_CONV_WARN_THRESHOLD` would be true again on
        # every subsequent re-touch of an existing key -- not just once --
        # spamming a warning per message in exactly the steady state it
        # exists to flag. `getattr(..., False)` avoids needing an __init__
        # addition in agent.py for a flag only this one warning needs.
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
        reaction_key = key
        if key.startswith("private:"):
            uid = key.split(":", 1)[1]
            reaction_key = f"dm:{uid}"
            self.private_history.pop(uid, None)
            self.last_dm_activity_at.pop(uid, None)
            self.last_proactive_at.pop(f"dm:{uid}", None)
            self._last_elicit_at.pop(reaction_key, None)
        else:
            self._last_elicit_at.pop(key, None)
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

    async def _napcat_send_group(self, group_id: str, message) -> bool:
        """Send to NapCat with a small bounded retry on connect/timeout errors.

        message: str or list of segments. Returns True on success so callers
        (e.g. _send_qq) can stop emitting later chunks on a hard failure and
        avoid truncated / out-of-order replies."""
        sink = current_sink.get()
        if sink is not None:
            # Gateway capture: hand the reply back over HTTP instead of
            # posting to NapCat (gateway ids aren't ints anyway).
            return sink.add(message)
        if not await self._throttle_send(f"group:{group_id}"):
            return False
        attempts = 3  # 1 initial + 2 retries
        for attempt in range(attempts):
            try:
                async with self._http(timeout=10) as client:
                    r = await client.post(
                        f"{self.napcat_api}/send_group_msg",
                        json={"group_id": int(group_id), "message": message},
                    )
                if r.status_code == 200:
                    # Remember the outbound message_id: reaction learning needs
                    # it to attribute later quote-replies to this bot message.
                    try:
                        _mid = ((r.json() or {}).get("data") or {}).get("message_id")
                        if _mid is not None:
                            self._sent_mids.setdefault(group_id, []).append(str(_mid))
                    except Exception:
                        pass
                    return True
                # Non-200 is a server-side reject, not a transient network
                # error — retrying rarely helps, so log and stop.
                logger.warning("[Agent] NapCat returned %d: %s",
                               r.status_code, r.text[:200])
                return False
            except (httpx.ConnectError, httpx.ConnectTimeout,
                    httpx.PoolTimeout) as e:
                if attempt == attempts - 1:
                    logger.warning("[Agent] send group msg failed after %d attempts: %s",
                                   attempts, e)
                    return False
                await asyncio.sleep(0.5 * (attempt + 1))
            except (httpx.ReadTimeout, httpx.WriteTimeout) as e:
                # The peer may have accepted the request before its response
                # was lost. Retrying an ambiguous timeout duplicates a chat
                # message, so fail this logical chunk instead of replaying it.
                logger.warning("[Agent] send group msg outcome unknown; not retrying: %s", e)
                return False
            except Exception as e:
                logger.warning("[Agent] send group msg failed: %s", e)
                return False
        return False

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
        sent_stickers: list[str] = []
        if not text:
            return SendResult()
        sendable = False
        sent_any = False
        delivered: list[str] = []
        failed = False
        # On the QQ path an at target must be a bare QQ number — a hallucinated
        # non-numeric [AT:] marker would produce a broken NapCat at segment, so
        # drop the mention (the marker text was already stripped upstream).
        # Gateway sends keep prefixed ids like "telegram:12345" as-is.
        if at_user_id and not at_user_id.isdigit() and current_sink.get() is None:
            logger.warning("[Agent] dropping non-numeric at target %r (group=%s)",
                           at_user_id, group_id)
            at_user_id = ""
        segments = self._parse_sticker_markers(text)
        is_first = True
        for kind, value in segments:
            if kind == "sticker":
                file_path = self.stickers.pick_by_tag(value)
                if not file_path or not file_path.exists():
                    logger.info("[Agent] sticker tag %r → no match, skipping", value)
                    continue
                await asyncio.sleep(random.uniform(0.6, 1.4))
                try:
                    img_b64 = base64.b64encode(file_path.read_bytes()).decode()
                except Exception as e:
                    logger.warning("[Agent] sticker read failed (%s): %s", file_path, e)
                    failed = True
                    continue
                sendable = True
                msg_segs: list = []
                if is_first and at_user_id:
                    msg_segs.append({"type": "at", "data": {"qq": str(at_user_id)}})
                msg_segs.append({"type": "image", "data": {"file": f"base64://{img_b64}"}})
                ok = await self._napcat_send_group(group_id, msg_segs)
                is_first = False
                if not ok:
                    failed = True
                    logger.warning("[Agent] send aborted (sticker chunk failed), "
                                   "dropping remaining segments (group=%s)", group_id)
                    break
                sent_any = True
                try:
                    rel = str(file_path.relative_to(self.stickers.dir)).replace("\\", "/")
                    sent_stickers.append(rel)
                except ValueError:
                    pass
                continue
            chunks = self._split_text(value)
            for chunk in chunks:
                sendable = True
                # Delay before every chunk including the first — feels like typing
                # rather than instant emit. Already had debounce + _think latency
                # upstream, so an extra ~1-3s on first chunk reads natural.
                await asyncio.sleep(self._typing_delay(chunk))
                if is_first and at_user_id:
                    message = [
                        {"type": "at", "data": {"qq": str(at_user_id)}},
                        {"type": "text", "data": {"text": chunk}},
                    ]
                else:
                    message = chunk
                ok = await self._napcat_send_group(group_id, message)
                is_first = False
                if not ok:
                    failed = True
                    # Stop on a hard failure so we don't emit a reply split
                    # across a network gap (truncated / out-of-order chunks).
                    logger.warning("[Agent] send aborted (text chunk failed), "
                                   "dropping remaining chunks (group=%s)", group_id)
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

    async def _napcat_send_private(self, user_id: str, message) -> bool:
        """Private send with a small bounded retry on connect/timeout errors
        (mirrors _napcat_send_group). message: str or list of segments. Returns
        True on success so callers can stop emitting later chunks on a hard
        failure instead of silently dropping owner/whitelist DMs on a transient
        NapCat blip."""
        sink = current_sink.get()
        if sink is not None:
            # Gateway capture: hand the reply back over HTTP instead of
            # posting to NapCat (gateway ids aren't ints anyway).
            return sink.add(message)
        if not await self._throttle_send(f"private:{user_id}"):
            return False
        attempts = 3  # 1 initial + 2 retries
        for attempt in range(attempts):
            try:
                async with self._http(timeout=10) as client:
                    r = await client.post(
                        f"{self.napcat_api}/send_private_msg",
                        json={"user_id": int(user_id), "message": message},
                    )
                if r.status_code == 200:
                    # Remember the outbound message_id: reaction learning needs
                    # it to attribute later quote-replies to this bot message.
                    try:
                        _mid = ((r.json() or {}).get("data") or {}).get("message_id")
                        if _mid is not None:
                            self._sent_mids.setdefault(
                                f"private:{user_id}", []).append(str(_mid))
                    except Exception:
                        pass
                    return True
                # Non-200 is a server-side reject, not a transient network
                # error — retrying rarely helps, so log and stop.
                logger.warning("[Agent] NapCat private %d: %s", r.status_code, r.text[:200])
                return False
            except (httpx.ConnectError, httpx.ConnectTimeout,
                    httpx.PoolTimeout) as e:
                if attempt == attempts - 1:
                    logger.warning("[Agent] send private msg failed after %d attempts: %s",
                                   attempts, e)
                    return False
                await asyncio.sleep(0.5 * (attempt + 1))
            except (httpx.ReadTimeout, httpx.WriteTimeout) as e:
                logger.warning(
                    "[Agent] send private msg outcome unknown; not retrying: %s", e)
                return False
            except Exception as e:
                logger.warning("[Agent] send private msg failed: %s", e)
                return False
        return False

    async def _send_private_qq(self, user_id: str, text: str) -> SendResult:
        """Serialize standalone private sends.

        Full private conversation paths already hold this lock across delivery
        and state commit and call ``_send_private_qq_unlocked`` directly.
        Background callers (for example delayed elicitation) use this wrapper.
        """
        key = f"private:{user_id}"
        if self._private_send_owners.get(key) is asyncio.current_task():
            return await self._send_private_qq_unlocked(user_id, text)
        async with self.send_locks[key]:
            return await self._send_private_qq_unlocked(user_id, text)

    async def _send_private_qq_unlocked(
            self, user_id: str, text: str) -> SendResult:
        target_key = f"private:{user_id}"
        self._sent_mids[target_key] = []
        text = self._sanitize_reply(text, self._validator_lang(), self.reply_style)
        # Private chat is 1:1 — there's no "target someone" semantics. The
        # model still occasionally emits [AT:xxx] (STYLE_GUIDE teaches the
        # marker); the group path extracts it, private has no extractor — left
        # unstripped it would go out as literal text.
        text = re.sub(r'\[AT:[^\]\s]+\]', '', text).strip()
        if not text:
            return SendResult()
        segments = self._parse_sticker_markers(text)
        # Typing rhythm belongs to whoever the user is actually watching.
        #
        # On QQ, sleeping here IS the pause the user sees: this coroutine and
        # the chat window are the same timeline. Behind a `GatewaySink` they
        # are not. The sink collects every chunk and hands the finished list
        # back to `handle_gateway`'s caller, which does its own pacing —
        # so these sleeps happen BEFORE the caller has been given anything
        # to show. Measured 2026-08-06 behind a sink: 7.0s of the 12.3s turn
        # was spent here, invisible, and the caller then emitted typing,
        # chunk and done 0.00s apart because the waiting was already over.
        #
        # The sink extraction rerouted the DATA through it and left the
        # TIMING behind. This is that half.
        collected = current_sink.get() is not None
        sendable = False
        sent_any = False
        delivered: list[str] = []
        failed = False
        sent_stickers: list[str] = []
        for kind, value in segments:
            if kind == "sticker":
                file_path = self.stickers.pick_by_tag(value)
                if not file_path or not file_path.exists():
                    logger.info("[Agent] sticker tag %r → no match, skipping (private)", value)
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
                msg = [{"type": "image", "data": {"file": f"base64://{img_b64}"}}]
                if not await self._napcat_send_private(user_id, msg):
                    failed = True
                    break
                sent_any = True
                try:
                    sent_stickers.append(
                        str(file_path.relative_to(self.stickers.dir)).replace("\\", "/"))
                except ValueError:
                    pass
                continue
            # text chunk — split for typing simulation. The SPLIT still
            # happens behind a sink (multi-bubble texture costs no time and
            # the web layer wants the same units); only the WAIT is skipped.
            chunks = self._split_text(value)
            for chunk in chunks:
                sendable = True
                if not collected:
                    await asyncio.sleep(self._typing_delay(chunk))
                if not await self._napcat_send_private(user_id, chunk):
                    failed = True
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
                async with self._http(timeout=15) as client:
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
                        mid = msg.get("message_id")
                        if mid is not None and mid in self._seen_msg_ids:
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
