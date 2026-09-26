"""How a message becomes a turn: intake, admission and the group turn."""
from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from contextlib import asynccontextmanager

from . import access
from .decision import (SLEEP_WINDOW, STICKY_CALL, choose_group_mode,
                       pacing_skip)
from . import channels
from .connector import (ConnectorSink, current_sink,
                      event_connector, event_prefiltered,
                      synthesize_onebot_payload)
from .textproc import (
    TextProcessing,
    _clean_prompt_source,
    _strip_web_desc,
    _truncate_framed,
)

logger = logging.getLogger("agent")

# Conversations whose refusal has been logged, kept bounded: forwarded ids are
# chosen by the connector, so an unbounded set would grow with every room.
_MAX_REFUSALS_LOGGED = 4096


class Turns:
    async def handle_onebot(self, payload: dict, *,
                            proactive: bool = False) -> bool:
        # One OneBot-shaped payload: from /v1/onebot, the catch-up sweep, or
        # handle_event after synthesize_onebot_payload.
        # `proactive`: this turn's text is a cue its CALLER wrote, not a
        # message from the person on the other end. See _handle_dm.
        # Top-level guard so any failure in the message pipeline is logged
        # loudly instead of silently dying as an unretrieved-task warning.
        try:
            return await self._handle_inner(payload, proactive=proactive)
        except Exception:
            logger.exception("[Agent] handle failed")
            return False

    @asynccontextmanager
    async def _ordered_group_intake(self, group_id: str):
        """Wait for the prior outbound commit, then acquire the intake lock."""
        lock = self.locks[group_id]
        while True:
            pending = self._pending_outbound.get(group_id)
            if pending is not None:
                await pending.wait()
                continue
            await lock.acquire()
            pending = self._pending_outbound.get(group_id)
            if pending is None:
                break
            lock.release()
            await pending.wait()
        try:
            yield
        finally:
            lock.release()

    async def handle_event(self, event: dict) -> dict:
        """Handle one platform-neutral event posted by a connector.

        Synchronous round-trip: a ConnectorSink is installed as a contextvar so
        the NapCat send funnels divert their messages into it, then the normal
        pipeline runs to completion and the collected replies go back in the
        HTTP response (the connector relays them to the source platform)."""
        payload = synthesize_onebot_payload(
            event, self._self_mention_id(), self.connector_qq_platforms)
        if payload.get("message_type") == "private":
            route_key = channels.dm_routing_key(payload.get("user_id", ""))
        else:
            route_key = str(payload.get("group_id", ""))
        if route_key:
            self._connector_inflight[route_key] += 1
        # The sink needs to know which platform this turn came from: on a
        # native platform `_ns` mints ids BARE for the ledgers, and an
        # outbound mention has to be handed back namespaced or the connector
        # cannot resolve it (see message_to_reply_item).
        sink_platform = str(payload.get("_platform", "") or "")
        sink = ConnectorSink(
            platform=sink_platform,
            native=sink_platform in (self.connector_qq_platforms or ()),
            bot_id=self._self_mention_id(),
            prefiltered=event_prefiltered(event),
        )
        tok = current_sink.set(sink)
        # Read off `event` (synthesize drops unknown keys) and passed as an
        # argument, not a payload flag: /v1/onebot accepts arbitrary JSON.
        proactive = bool(event.get("proactive"))
        try:
            handled = await self.handle_onebot(payload, proactive=proactive)
        finally:
            # Close before reset: background tasks spawned during handling
            # inherit a context that still references this sink, and a send
            # after the response is gone should be dropped, not collected.
            sink.closed = True
            current_sink.reset(tok)
            if route_key:
                remaining = self._connector_inflight.get(route_key, 0) - 1
                if remaining > 0:
                    self._connector_inflight[route_key] = remaining
                else:
                    self._connector_inflight.pop(route_key, None)
                self._trim_connector_convs()
        # Only an admitted turn may leave an address behind: a connector must
        # not plant handles for conversations the agent refuses.
        connector = event_connector(event)
        if (route_key and sink.owned
                and (connector["reply_handle"] or connector["connector_id"])):
            dm = payload.get("message_type") == "private"
            self.connector_handles.record(
                route_key, **connector, platform=sink.platform,
                native=sink.native,
                conversation_type="dm" if dm else "group",
                conversation_id=str(event.get(
                    "sender_id" if dm else "conversation_id") or ""),
                prefiltered=sink.prefiltered)
        # `owned` is not `handled`. See ConnectorSink: a connector needs to know
        # whether to suppress its own model, and "produced no reply" is the
        # wrong signal for that — silence is frequently the persona's answer.
        return {"handled": bool(handled), "owned": sink.owned,
                "replies": sink.items}

    def _claim_connector_turn(self) -> None:
        """Mark the current connector turn as ours, whatever it decides to say.

        Called once the admission gates pass, which is the moment the answer
        to "is this conversation mine" is known — everything after it is about
        what to say, including saying nothing.
        """
        sink = current_sink.get()
        if sink is not None:
            sink.owned = True

    def _admins(self) -> frozenset[str]:
        """Every admin account (ADMIN_IDS), canonical. Re-read on each call
        because it is a live attribute the tests and admin paths edit; the
        set is tiny."""
        return access.parse_ids(
            self.admin_ids, native_platforms=self.connector_qq_platforms)

    def _dm_allowlist(self) -> frozenset[str]:
        """ACCESS_DM_USERS, canonical."""
        return access.parse_ids(
            self.access_dm_users,
            native_platforms=self.connector_qq_platforms)

    def _group_allowlist(self) -> frozenset[str]:
        """ACCESS_GROUPS, canonical."""
        return access.parse_ids(
            self.access_groups, native_platforms=self.connector_qq_platforms)

    def _log_refusal(self, conv_key: str, reason: str) -> None:
        """Say once per conversation why it is not answered. Silent refusals
        are one of the reasons deploy.md lists for "it never replies"."""
        key = f"{conv_key}\x00{reason}"
        if key in self._refusals_logged:
            return
        self._refusals_logged[key] = None
        if len(self._refusals_logged) > _MAX_REFUSALS_LOGGED:
            self._refusals_logged.pop(next(iter(self._refusals_logged)))
        logger.info("[Agent] not answering %s: %s", conv_key, reason)

    async def _handle_inner(self, payload: dict, *,
                            proactive: bool = False) -> bool:
        if not self.enabled:
            return False
        if payload.get("post_type") and payload.get("post_type") != "message":
            return False

        # De-dup check only; remembering happens after the admission gates so
        # unauthorized ids don't churn the ring. str(): catch-up replay passes
        # NapCat's raw int while the webhook path stringifies.
        mid = payload.get("message_id")
        if mid is not None and str(mid) in self._seen_msg_ids:
            return False

        message_type = payload.get("message_type", "group")
        user_id = str(payload.get("user_id", ""))

        # Admission, per platform (access.py). The sink is set only by
        # handle_event, so /v1/onebot cannot claim to be a connector: there
        # a namespaced id is forged, and a bare one is QQ's to gate.
        sink = current_sink.get()
        via_connector = sink is not None
        prefiltered = getattr(sink, "prefiltered", True)
        if message_type == "private":
            admins = self._admins()
            refusal = access.dm_refusal(
                user_id, admins, self._dm_allowlist(),
                via_connector=via_connector, prefiltered=prefiltered)
            if refusal:
                self._log_refusal(channels.dm_routing_key(user_id), refusal)
                return False
            is_admin = access.is_admin(user_id, admins)
            self._claim_connector_turn()
            if mid is not None:
                self._remember_msg_id(mid)
            # Connector DM keys are connector-chosen → register in the LRU so an
            # over-the-cap flood evicts the least-recently-active conversation.
            if via_connector and not channels.is_native(user_id):
                self._touch_connector_conv(channels.dm_routing_key(user_id))
            # `proactive` is honoured on the private path only, which can
            # hand the cue to the model for one call. A group event carrying
            # it is claimed and dropped below.
            return await self._handle_dm(user_id, payload,
                                              is_admin=is_admin,
                                              proactive=proactive)

        group_id = str(payload.get("group_id", "")).strip()
        if not group_id:
            return False
        # A bare id is QQ's from either door, a native connector's included,
        # so it is measured against the QQ entries like any other.
        refusal = access.group_refusal(
            group_id, self._group_allowlist(),
            via_connector=via_connector, prefiltered=prefiltered,
            user_id=user_id)
        if refusal:
            self._log_refusal(group_id, refusal)
            return False
        self._claim_connector_turn()
        if mid is not None:
            self._remember_msg_id(mid)
        # A group turn has no transient cue to carry the caller's text as:
        # past this point it is buffered as the sender's line, counted toward
        # the triggers and can be saved as a memory about them. Claimed, so
        # the connector does not answer the cue with its own model either.
        # _maybe_proactive_groups composes the QQ groups' own proactive turns.
        if proactive:
            logger.info("[Agent] proactive cue on a group conversation is not "
                        "supported; dropped (group=%s)", group_id)
            return False
        # Connector group keys are connector-chosen → register in the LRU.
        if via_connector and not channels.is_native(group_id):
            self._touch_connector_conv(group_id)

        has_image = any(
            isinstance(seg, dict) and seg.get("type") == "image"
            for seg in payload.get("message", [])
        )
        if has_image:
            self._vision_in_flight[group_id] += 1
        try:
            text = await self._extract_text(payload)
        finally:
            if has_image:
                self._vision_in_flight[group_id] = max(0, self._vision_in_flight[group_id] - 1)
        if not text:
            return False
        # Two views of the same text: ctrl_text excludes web-fetched
        # enrichment so a third-party page can't trigger name-call mode or
        # memory commands; text keeps it, sentinels included, so the prompt
        # can still tell the model which part a third party wrote.
        ctrl_text = _strip_web_desc(text)

        # `or {}` (not a default of {}) because the protocol can emit
        # "sender": null — a present-but-null key, where .get("sender", {})
        # still returns None and the following .get() raises AttributeError.
        sender = payload.get("sender") or {}
        # Cleaned once here: the name also reaches the active-members list,
        # the self-eval context and the reaction judge, none of which pass
        # through `_fmt_line`, so a U+0002 in a card must not open a span.
        nickname = (_clean_prompt_source(
            sender.get("card") or sender.get("nickname")) or "?")[:8]

        is_at = self._is_at_me(payload)
        # Guard the substring test: an empty persona_name (the shipped default
        # when PERSONA_NAME is unset) would make `"" in text` always True and the
        # bot would treat every message as a named call, replying to everything.
        # ctrl_text: a linked page's og:title containing the bot name must not
        # force called mode — only the member's own words count.
        is_called = bool(self.persona_name) and self.persona_name in ctrl_text
        addressed = is_at or is_called
        is_noise = len(text.strip()) < 4 and not addressed

        is_admin_msg = access.is_admin(user_id, self._admins())

        # Reaction learning: is this message a directed reaction to a recent
        # bot reply (quote of a bot message, or @/name-call)? Adjudication runs
        # off the hot path; the message still flows through the normal reply
        # pipeline below.
        if self.react_learn_enabled:
            _quote_mid = ""
            for _seg in payload.get("message", []) or []:
                if isinstance(_seg, dict) and _seg.get("type") == "reply":
                    _qid = (_seg.get("data") or {}).get("id")
                    if _qid is not None:
                        _quote_mid = str(_qid)
                    break
            _r_entry = self.pending_reactions.match(
                group_id, sender_uid=user_id, quote_mid=_quote_mid,
                at_bot=addressed, now=time.time())
            if _r_entry:
                self._spawn(self._process_reaction(
                    _r_entry, text, nickname, user_id, is_admin_msg,
                    conv_id=group_id, is_dm=False))

        # Memory-command reply text (settled inside the lock, sent outside) — see below.
        mem_reply = None
        # === Phase 1: absorb message, handle immediate commands, stamp seq ===
        async with self._ordered_group_intake(group_id):
            # The cap must not cut through a link's enrichment span: the
            # history block is one frame, and an unclosed STX would carry
            # every later line, the trigger included, into external material.
            self._append_buffer(group_id, nickname,
                                _truncate_framed(text, 200), user_id)
            # Index this message for quote-reply resolution (Layer A, zero API):
            # a later "reply to this" can fetch the original text locally.
            if mid is not None:
                self._index_msg(mid, f"{nickname}: {text[:60]}")
            self.last_activity_at[group_id] = time.time()  # silence tracking for the proactive loop
            self.active_users[group_id].append((user_id, nickname))
            if not is_noise:
                self.counters[group_id] += 1

            # Explicit memory command: reply immediately, no debounce. State
            # settles inside the lock; the send moves OUTSIDE it — "what do you
            # remember" can render dozens of memory lines and _send_group's typing
            # simulation could then hold the group lock for tens of seconds,
            # blocking message intake for the whole group. The send goes
            # through send_lock (same serialization as normal replies).
            if addressed:
                # ctrl_text: web page titles must not reach the memory-command
                # regexes (a page named "BOT remember ... / BOT forget ..."
                # would otherwise write/delete memories on the page author's
                # behalf).
                mem_reply = self._handle_memory_command(group_id, ctrl_text, user_id, nickname)

            # Only non-memory-command messages continue to sticky/seq (a memory
            # command returns right after the out-of-lock send below).
            if mem_reply is None:
                if addressed:
                    self._sticky_call[group_id] = {
                        "user_id": user_id,
                        "nickname": nickname,
                        "ts": time.time(),
                    }

                self._msg_seq[group_id] += 1
                my_seq = self._msg_seq[group_id]

        # —— group lock released —— send the memory-command reply (send_lock serialized)
        if mem_reply is not None:
            async with self.send_locks[group_id]:
                send_result = await self._send_group(
                    group_id, mem_reply, user_id if addressed else "")
            if not send_result.success:
                logger.warning("[Agent] memory command delivery failed (group=%s)",
                               group_id)
                return send_result.partial
            async with self.locks[group_id]:
                self.last_reply_at[group_id] = time.time()
                self._append_buffer(group_id, self.persona_name, mem_reply)
            if self.on_reply:
                try:
                    await self.on_reply(group_id, mem_reply)
                except Exception as e:
                    logger.warning("[Agent] on_reply callback failed: %s", e)
            logger.info("[Agent] memory command (group=%s): %s", group_id, mem_reply[:60])
            return True

        # === Debounce: short wait outside the lock so consecutive messages batch up ===
        bare_after_strip = (
            text.replace(f"@{self.persona_name}", "").replace(self.persona_name, "").strip()
        )
        is_bare_call = addressed and len(bare_after_strip) <= 4
        debounce_sec = 5.0 if is_bare_call else self.message_debounce_sec
        if debounce_sec > 0:
            try:
                await asyncio.sleep(debounce_sec)
            except asyncio.CancelledError:
                return False

        vision_waited = 0.0
        while self._vision_in_flight.get(group_id, 0) > 0 and vision_waited < 4.0:
            await asyncio.sleep(0.3)
            vision_waited += 0.3
        if vision_waited > 0:
            logger.debug("[Agent] waited %.1fs for vision in group=%s", vision_waited, group_id)

        # === Phase 2: re-acquire lock; only the latest message in the burst hits the LLM ===
        async with self.locks[group_id]:
            if self._msg_seq.get(group_id, 0) != my_seq:
                logger.debug("[Agent] debounce drop (group=%s seq=%d latest=%d)",
                             group_id, my_seq, self._msg_seq.get(group_id, 0))
                return False

            sticky = self._sticky_call.get(group_id)
            sticky_active = (
                sticky is not None
                and time.time() - sticky["ts"] < self.message_debounce_sec + 5.0
            )
            never_replied = self.last_reply_at[group_id] == 0.0
            mode, why = choose_group_mode(
                addressed=addressed, is_admin=is_admin_msg,
                sticky_admin=(access.is_admin(sticky["user_id"], self._admins())
                              if sticky_active else None),
                in_followup=(time.time() - self.last_reply_at[group_id]
                             < self.chat_followup_window_s),
                counter=self.counters[group_id],
                trigger_count=self.chat_trigger_count,
                never_replied=never_replied)
            if not mode:
                return False
            caller_override = None
            if why == STICKY_CALL:
                user_id = sticky["user_id"]
                nickname = sticky["nickname"]
                caller_override = (nickname, user_id)
                logger.info(
                    "[Agent] sticky-call upgrade (group=%s caller=%s nick=%s age=%.1fs)",
                    group_id, user_id, nickname, time.time() - sticky["ts"],
                )

            self.counters[group_id] = 0
            self._sticky_call.pop(group_id, None)

            skip = pacing_skip(mode, first_appearance=never_replied,
                               sleep_hour=TextProcessing._is_sleep_hour())
            if skip == SLEEP_WINDOW:
                logger.info("[Agent] PASS via sleep window (mode=%s, hour=%d, group=%s)",
                            mode, time.localtime().tm_hour, group_id)
                return False
            if skip:
                logger.info("[Agent] PASS via spontaneous skip (mode=judge, group=%s)", group_id)
                return False

            try:
                reply, _intent, auto_mem = await self._think(group_id, mode, text, caller_override=caller_override)
            except Exception as e:
                logger.warning("[Agent] LLM call failed (mode=%s): %s", mode, e)
                # Commit state under the group lock, but send OUTSIDE it via a
                # background task holding send_locks — mirroring the main
                # path: _send_group's typing sleeps + protocol-side retries can
                # take tens of seconds, and holding the group lock that long
                # stalls Phase-1 message absorption for the whole group;
                # skipping send_locks would let this chunk interleave with an
                # in-flight reply.
                if mode == "called":
                    # Three short, persona-consistent excuses for upstream LLM
                    # failure. Customize these in your fork to match the bot's
                    # voice (the strings ARE shipped to the group on failure).
                    fallback = random.choice([
                        "ugh, hanging here for a sec",
                        "hold on, connection's wonky",
                        "signal weird rn, gimme a min",
                    ])

                    # The task outlives a connector turn's response, so it goes
                    # out the way unprompted messages do (_send_background).
                    async def _send_fallback() -> None:
                        try:
                            async with self.send_locks[group_id]:
                                result = await self._send_background(
                                    group_id,
                                    lambda: self._send_group(
                                        group_id, fallback, user_id),
                                    reason="excuse")
                            if result.success:
                                async with self.locks[group_id]:
                                    self.last_reply_at[group_id] = time.time()
                                    self._append_buffer(
                                        group_id, self.persona_name, fallback)
                            else:
                                logger.warning(
                                    "[Agent] fallback delivery failed (group=%s)",
                                    group_id)
                        except Exception:
                            logger.exception("[Agent] fallback send failed")

                    self._spawn(_send_fallback())
                return False

            # A PASS commits nothing, neither core note nor auto-memory: both
            # describe a reply that was never sent.
            final = self._finalize_reply(reply, log_ctx=f"mode={mode}, group={group_id}")
            if final is None:
                return False
            reply, at_uid, _pending_core, had_visible_candidate = final
            if not at_uid and mode == "called":
                at_uid = user_id
            # A visible candidate that validation reduced to nothing is
            # rejected, not treated as a state-bearing PASS.
            if had_visible_candidate and not reply:
                return False
            if not reply or re.match(r"PASS\b", reply, re.IGNORECASE):
                logger.info("[Agent] PASS (mode=%s, group=%s)", mode, group_id)
                if mode == "followup":
                    self.last_reply_at[group_id] = (
                        time.time() - self.chat_followup_window_s - 1)
                return False
            # Eval context snapshot: must be taken before appending the bot's
            # own reply, and inside the lock. Otherwise _evaluate_reply runs
            # after the send (seconds of typing simulation), the buffer has
            # been pushed past by new messages → it scores the wrong context,
            # and worse, writes the mismatched context into examples.jsonl's
            # few-shot pool (slow degradation).
            eval_ctx = [f"{m['name']}: {m['text']}" for m in list(self.buffers[group_id])[-5:]]
            outbound_done = asyncio.Event()
            self._pending_outbound[group_id] = outbound_done

        # —— group lock released ——
        # The send still runs under a per-group send lock so same-group sends
        # stay serialized (no interleaved text/sticker chunks), but new
        # messages can be absorbed while the bot is "typing".
        try:
            async with self.send_locks[group_id]:
                send_result = await self._send_group(group_id, reply, at_uid)
            if not send_result.success and not send_result.partial:
                logger.warning("[Agent] reply delivery failed (mode=%s, group=%s)",
                               mode, group_id)
                return False

            # A partial send still put text in front of everyone. Returning
            # early here left last_reply_at, the buffer and pending_reactions
            # untouched for words the group had already read — so the followup
            # window never opened and the next _think could re-emit the same
            # line verbatim. Commit what was actually delivered; withhold only
            # what belongs to the reply as a whole (core memory, auto-memory
            # and the self-eval below all describe the complete answer).
            committed = reply if send_result.success else send_result.delivered
            async with self.locks[group_id]:
                self.last_reply_at[group_id] = time.time()
                if committed:
                    self._append_buffer(group_id, self.persona_name, committed)
                if send_result.success:
                    self._commit_core_memory(group_id, _pending_core)
                    if auto_mem:
                        self._save_auto_memory(group_id, auto_mem)
            if not send_result.success:
                logger.warning(
                    "[Agent] reply PARTIALLY delivered (mode=%s, group=%s): "
                    "committed %d of %d chars",
                    mode, group_id, len(committed), len(reply))
        finally:
            if self._pending_outbound.get(group_id) is outbound_done:
                self._pending_outbound.pop(group_id, None)
                outbound_done.set()
        logger.info("[Agent] reply (mode=%s, group=%s): %s", mode, group_id, reply[:60])

        # Reaction learning tracks what was actually said: a reaction to a
        # truncated reply is a reaction to the truncation, and adjudicating it
        # against the full text would attribute a complaint to words nobody read.
        if self.react_learn_enabled and committed:
            self.pending_reactions.record(
                group_id, reply=committed, ctx_lines=eval_ctx, mode=mode,
                intent=_intent, target_uid=at_uid or user_id,
                target_name=nickname, mids=send_result.message_ids,
                ts=time.time(),
            )

        if self.on_reply and committed:
            try:
                await self.on_reply(group_id, committed)
            except Exception as e:
                logger.warning("[Agent] on_reply callback failed: %s", e)

        # Self-eval only for a complete reply. Scoring a half-delivered answer
        # measures the network, not the persona, and a low score would feed the
        # learning loop a verdict about text the model never got to finish.
        if self.eval_enabled and send_result.success:
            self._spawn(self._evaluate_reply(
                group_id, mode, text, reply, send_result.sticker_files,
                _intent, eval_ctx,
            ))

        return send_result.success
