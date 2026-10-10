"""How a message becomes a turn: intake, admission and the group turn."""
from __future__ import annotations

import asyncio
import logging
import random
import time
from contextlib import asynccontextmanager

from . import access
from .decision import (BLOCKED, PASS, SLEEP_WINDOW, STICKY_CALL,
                       choose_group_mode, pacing_skip)
from . import channels
from . import decision_log
from .connector import (ConnectorSink, current_sink,
                      event_connector, event_prefiltered,
                      synthesize_onebot_payload)
from .prompts import MODEL_FAILURE_EXCUSES
from .textproc import (
    TextProcessing,
    _clean_prompt_source,
    _strip_web_desc,
    _truncate_framed,
)

logger = logging.getLogger("agent")

# Bounded: connector-chosen ids would otherwise grow the set with every room.
_MAX_REFUSALS_LOGGED = 4096

# How often one conversation may hear that the model is not answering.
_EXCUSE_COOLDOWN_S = 300.0

# A bare call ("@Bot", "Bot?") waits this long for the message that follows it.
BARE_CALL_DEBOUNCE_S = 5.0


class Turns:
    async def handle_onebot(self, payload: dict, *,
                            proactive: bool = False) -> bool:
        # One OneBot-shaped payload (/v1/onebot, the catch-up sweep or
        # handle_event); `proactive` text is the caller's cue (see _handle_dm).
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
        """Handle one connector event synchronously: a ConnectorSink contextvar
        collects the sends, and the replies go back in the HTTP response."""
        sender, bot = (str(event.get(k, "") or "") for k in ("sender_id", "bot_id"))
        if sender and sender == bot:
            # The bot's own echo: owned, so the connector's model stays quiet too.
            logger.debug("[Agent] dropped the bot's own message (%s)",
                         event.get("platform", "?"))
            return {"handled": False, "owned": True, "replies": []}
        payload = synthesize_onebot_payload(
            event, self._self_mention_id(), self.connector_qq_platforms)
        if payload.get("message_type") == "private":
            route_key = channels.dm_routing_key(payload.get("user_id", ""))
        else:
            route_key = str(payload.get("group_id", ""))
        if route_key:
            self._connector_inflight[route_key] += 1
        # A native platform's ids are bare inside; outbound mentions are
        # namespaced again (see message_to_reply_item).
        sink_platform = str(payload.get("_platform", "") or "")
        sink = ConnectorSink(
            platform=sink_platform,
            native=sink_platform in (self.connector_qq_platforms or ()),
            bot_id=self._self_mention_id(),
            prefiltered=event_prefiltered(event),
        )
        tok = current_sink.set(sink)
        # An argument, not a payload flag: /v1/onebot accepts arbitrary JSON.
        proactive = bool(event.get("proactive"))
        try:
            handled = await self.handle_onebot(payload, proactive=proactive)
        finally:
            # Closed first: background tasks inherit this sink and must not
            # collect into a response that is gone.
            sink.closed = True
            current_sink.reset(tok)
            if route_key:
                remaining = self._connector_inflight.get(route_key, 0) - 1
                if remaining > 0:
                    self._connector_inflight[route_key] = remaining
                else:
                    self._connector_inflight.pop(route_key, None)
                self._trim_connector_convs()
        # Only an admitted turn may leave a handle behind.
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
        # `owned`, not `handled`, tells a connector to suppress its own model:
        # silence is often the persona's answer.
        return {"handled": bool(handled), "owned": sink.owned,
                "replies": sink.items}

    def _claim_connector_turn(self) -> None:
        """Mark the connector turn as ours once admission passes, whatever it says."""
        sink = current_sink.get()
        if sink is not None:
            sink.owned = True

    def _admins(self) -> frozenset[str]:
        """Every admin account (ADMIN_IDS), canonical; re-read since it is edited live."""
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
        """Say once per conversation why it is not answered."""
        key = f"{conv_key}\x00{reason}"
        if key in self._refusals_logged:
            return
        self._refusals_logged[key] = None
        if len(self._refusals_logged) > _MAX_REFUSALS_LOGGED:
            self._refusals_logged.pop(next(iter(self._refusals_logged)))
        logger.info("[Agent] not answering %s: %s", conv_key, reason)

    def _excuse_begin(self, conv_key: str) -> bool:
        """May this conversation be told the model is not answering: once per
        `_EXCUSE_COOLDOWN_S`, counted from a delivered excuse (`_excuse_end`)."""
        if conv_key in self._excuse_inflight:
            return False
        last = self._last_excuse_at.get(conv_key)
        if last is not None and time.monotonic() - last < _EXCUSE_COOLDOWN_S:
            return False
        self._excuse_inflight.add(conv_key)
        return True

    def _excuse_end(self, conv_key: str, delivered: bool) -> None:
        self._excuse_inflight.discard(conv_key)
        if not delivered:
            return
        self._last_excuse_at[conv_key] = time.monotonic()
        if len(self._last_excuse_at) > _MAX_REFUSALS_LOGGED:
            self._last_excuse_at.pop(next(iter(self._last_excuse_at)))

    def _model_failure_excuse(self) -> str:
        return random.choice(MODEL_FAILURE_EXCUSES.get(
            self.agent_lang, MODEL_FAILURE_EXCUSES["en"]))

    async def _handle_inner(self, payload: dict, *,
                            proactive: bool = False) -> bool:
        if not self.enabled:
            return False
        if payload.get("post_type") and payload.get("post_type") != "message":
            return False

        # Remembered only after admission, so refused ids don't churn the ring;
        # str() because the catch-up sweep passes ints.
        mid = payload.get("message_id")
        if mid is not None and str(mid) in self._seen_msg_ids:
            return False

        message_type = payload.get("message_type", "group")
        user_id = str(payload.get("user_id", ""))

        # Only handle_event sets a sink, so /v1/onebot cannot pose as a connector.
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
            # Connector-chosen keys go through the LRU cap.
            if via_connector and not channels.is_native(user_id):
                self._touch_connector_conv(channels.dm_routing_key(user_id))
            # Only the DM path can carry a proactive cue.
            return await self._handle_dm(user_id, payload,
                                              is_admin=is_admin,
                                              proactive=proactive)

        group_id = str(payload.get("group_id", "")).strip()
        if not group_id:
            return False
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
        # A group turn would buffer the cue as the sender's line; claimed and dropped.
        if proactive:
            logger.info("[Agent] proactive cue on a group conversation is not "
                        "supported; dropped (group=%s)", group_id)
            return False
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
        # ctrl_text drops link enrichment, so a fetched page cannot call the bot
        # or run memory commands; text keeps it, marked, for the prompt.
        ctrl_text = _strip_web_desc(text)

        sender = payload.get("sender") or {}  # may be present but null
        # Cleaned here: the name reaches prompts that bypass `_fmt_line`.
        nickname = (_clean_prompt_source(
            sender.get("card") or sender.get("nickname")) or "?")[:8]

        is_at = self._is_at_me(payload)
        is_called = self._names_me(ctrl_text)
        addressed = is_at or is_called
        is_noise = len(text.strip()) < 4 and not addressed

        is_admin_msg = access.is_admin(user_id, self._admins())

        # A directed reaction to a recent reply is adjudicated off the hot path.
        # A memory command is not one and must not consume the pending reply.
        if self.react_learn_enabled and not (
                addressed and self._is_memory_command(ctrl_text)):
            _quote_mid, _quote_by_bot = "", None
            for _seg in payload.get("message", []) or []:
                if isinstance(_seg, dict) and _seg.get("type") == "reply":
                    _qdata = _seg.get("data") or {}
                    _qid = _qdata.get("id")
                    if _qid is not None:
                        _quote_mid = str(_qid)
                    if _qdata.get("quote_self"):
                        _quote_by_bot = True
                    elif _qdata.get("quote_name") not in (None, "", self.persona_name):
                        _quote_by_bot = False
                    break
            _r_entry = self.pending_reactions.match(
                group_id, sender_uid=user_id, quote_mid=_quote_mid,
                at_bot=addressed, now=time.time(), quote_by_bot=_quote_by_bot)
            if _r_entry:
                self._spawn(self._process_reaction(
                    _r_entry, text, nickname, user_id, is_admin_msg,
                    conv_id=group_id, is_dm=False))

        mem_reply = None
        # Phase 1: absorb the message, handle memory commands, stamp the seq.
        async with self._ordered_group_intake(group_id):
            # The cut must not leave an enrichment span open.
            self._append_buffer(group_id, nickname,
                                _truncate_framed(text, 200), user_id)
            if mid is not None:
                self._index_msg(mid, f"{nickname}: {text[:60]}")
            self.last_activity_at[group_id] = time.time()
            self.active_users[group_id].append((user_id, nickname))
            if not is_noise:
                self.counters[group_id] += 1

            # A memory command answers at once: state settles here, the send
            # happens outside the lock.
            if addressed:
                mem_reply = self._handle_memory_command(group_id, ctrl_text, user_id, nickname)

            if mem_reply is None:
                if addressed:
                    self._sticky_call[group_id] = {
                        "user_id": user_id,
                        "nickname": nickname,
                        "ts": time.time(),
                    }

                self._msg_seq[group_id] += 1
                my_seq = self._msg_seq[group_id]

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

        # Debounce outside the lock so a burst batches into one turn.
        bare_after_strip = (
            text.replace(f"@{self.persona_name}", "").replace(self.persona_name, "").strip()
        )
        is_bare_call = addressed and len(bare_after_strip) <= 4
        debounce_sec = BARE_CALL_DEBOUNCE_S if is_bare_call else self.message_debounce_sec
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

        # Phase 2: only the latest message of the burst reaches the model.
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
                decision_log.record(group_id, mode, False, why, ctrl_text,
                                    sender=nickname)
                return False
            caller_override = None
            sender_name = nickname  # before a sticky call swaps in its caller
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
                decision_log.record(group_id, mode, False, skip, ctrl_text,
                                    sender=sender_name)
                return False
            if skip:
                logger.info("[Agent] PASS via spontaneous skip (mode=judge, group=%s)", group_id)
                decision_log.record(group_id, mode, False, skip, ctrl_text,
                                    sender=sender_name)
                return False

            try:
                reply, _intent, auto_mem = await self._think(group_id, mode, text, caller_override=caller_override)
            except Exception as e:
                logger.warning("[Agent] LLM call failed (mode=%s): %s", mode, e)
                # Sent from a background task under the send lock, like a reply.
                if mode in ("called", access.ADMIN_MODE) and self._excuse_begin(group_id):
                    fallback = self._model_failure_excuse()

                    # Outlives the connector response, hence _send_background.
                    async def _send_fallback() -> None:
                        delivered = False
                        try:
                            async with self.send_locks[group_id]:
                                result = await self._send_background(
                                    group_id,
                                    lambda: self._send_group(
                                        group_id, fallback, user_id),
                                    reason="excuse")
                            if result.success:
                                delivered = True
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
                        finally:
                            self._excuse_end(group_id, delivered)

                    self._spawn(_send_fallback())
                return False

            # A PASS commits nothing, neither core note nor auto-memory: both
            # describe a reply that was never sent.
            final = self._final_reply(reply, log_ctx=f"mode={mode}, group={group_id}")
            # Blocked is not a PASS: no log line, no follow-up reset.
            if final.verdict == BLOCKED:
                return False
            if final.verdict == PASS:
                logger.info("[Agent] PASS (mode=%s, group=%s)", mode, group_id)
                decision_log.record(group_id, mode, False, "passed", ctrl_text,
                                    sender=sender_name)
                if mode == "followup":
                    self.last_reply_at[group_id] = (
                        time.time() - self.chat_followup_window_s - 1)
                return False
            reply, at_uid = final.text, final.at_uid
            if not at_uid and mode == "called":
                at_uid = user_id
            # Snapshot now, inside the lock: after the send the buffer has moved on.
            eval_ctx = [f"{m['name']}: {m['text']}" for m in list(self.buffers[group_id])[-5:]]
            outbound_done = asyncio.Event()
            self._pending_outbound[group_id] = outbound_done

        # Outside the group lock, so intake continues while the bot "types".
        try:
            async with self.send_locks[group_id]:
                send_result = await self._send_group(group_id, reply, at_uid)
            if not send_result.success and not send_result.partial:
                logger.warning("[Agent] reply delivery failed (mode=%s, group=%s)",
                               mode, group_id)
                return False

            # A partial send is committed as delivered; core note, auto-memory
            # and self-eval describe the whole answer and are withheld.
            committed = reply if send_result.success else send_result.delivered
            async with self.locks[group_id]:
                self.last_reply_at[group_id] = time.time()
                if committed:
                    self._append_buffer(group_id, self.persona_name, committed)
                if send_result.success:
                    self._commit_core_memory(group_id, final.core_note)
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
        decision_log.record(group_id, mode, True, why, committed,
                            answered=ctrl_text, sender=sender_name)

        # Reactions are judged against what was actually delivered.
        if self.react_learn_enabled and committed:
            self.pending_reactions.record(
                group_id, reply=committed, ctx_lines=eval_ctx, mode=mode,
                intent=_intent,
                target_uid=self._reaction_recipient(group_id, mode, at_uid, user_id),
                target_name=nickname, mids=send_result.message_ids,
                ts=time.time(),
            )

        if self.on_reply and committed:
            try:
                await self.on_reply(group_id, committed)
            except Exception as e:
                logger.warning("[Agent] on_reply callback failed: %s", e)

        # Self-eval only for a complete reply.
        if self.eval_enabled and send_result.success:
            self._spawn(self._evaluate_reply(
                group_id, mode, text, reply, send_result.sticker_files,
                _intent, eval_ctx,
            ))

        return send_result.success
