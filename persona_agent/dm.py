"""The one-on-one turn: admission done, a reply to one person."""
from __future__ import annotations

import asyncio
import logging
import re
import time

from .access import ADMIN_MODE
from . import channels
from .textproc import (
    TextProcessing,
    _REFUSAL_LABELS,
    _truncate_framed,
)

logger = logging.getLogger("agent")

# What the private-chat retry appends to the system prompt (see
# `Agent._chat_dm`). The dominant cause of an empty 1:1 turn is
# deterministic, an emoji-only draft the sanitizer eats, so the second prompt
# has to differ from the first. It amends the output contract rather than
# replacing it: it lands right after `dm_output_protocol`, and "reply in
# plain text" from that last position would talk the model out of the JSON
# the fail-closed parser needs, turning one empty turn into two.
_EMPTY_DRAFT_RETRY_NOTE = (
    "Your previous draft could not be rendered. Emit the same JSON object "
    "again — same keys, same shape — with a `reply` of at least one word "
    "and no emoji or markup inside it."
)



class DirectMessages:
    async def _handle_dm(self, user_id: str, payload: dict,
                              is_admin: bool = True,
                              proactive: bool = False) -> bool:
        """Run one private turn in send/commit order without blocking intake.

        `proactive`: the text is the caller's cue, not the reader's words, so
        it must never be appended to history or attributed to them. It
        reaches the model for this one call, as `proactive_cue`."""
        pkey = channels.dm_routing_key(user_id)
        async with self.send_locks[pkey]:
            self._dm_send_tasks[pkey] = asyncio.current_task()
            # What this turn put in front of the model as the reader's words,
            # and whether they reached dm_history. Any other way out (the
            # model failed or PASSed, the reply was blocked or never
            # delivered) keeps them for the reader's next turn; dropped, that
            # turn had no record of what they said.
            said: list[str] = []
            committed = False
            try:
                text = await self._extract_text(payload)
                if not text:
                    return False

                # Nothing to react TO on a proactive turn: the text is the
                # caller's cue, so matching it against a pending reaction
                # would attribute the caller's words to the reader.
                if self.react_learn_enabled and not proactive:
                    entry = self.pending_reactions.match(
                        channels.dm_learning_key(user_id),
                        sender_uid=user_id, is_dm=True, now=time.time())
                    if entry:
                        self._spawn(self._process_reaction(
                            # The reactor's name as the judge reads it and the
                            # audit row stores it.
                            entry, text, "owner" if is_admin else "friend",
                            user_id, is_admin,
                            conv_id=channels.dm_learning_key(user_id),
                            is_dm=True))

                async with self.locks[pkey]:
                    if proactive:
                        # The reader said nothing. The connector's scheduler
                        # and the agent's own loop share one DM cooldown.
                        self.last_proactive_at[
                            channels.dm_learning_key(user_id)] = time.time()
                    else:
                        self.last_dm_activity_at[user_id] = time.time()
                    history = list(self.dm_history.get(user_id, []))
                    # The one line this flag is about. Appended, the cue stays
                    # for 40 turns as something the reader supposedly said.
                    # Left out, _chat_dm's own internal cue applies —
                    # it fires only when the last turn is not a user message,
                    # so the two halves depend on each other.
                    if not proactive:
                        # Messages whose turns committed nothing join this
                        # one in a single user turn, for the same reason:
                        # stored apart, two user turns would sit in a row
                        # and the stored history could end on the reader.
                        said = self._dm_unanswered.get(user_id, []) + [text]
                        history.append({"role": "user",
                                        "content": "\n".join(said)})
                    history = history[-40:]

                # The cue exists only on a proactive turn, so only that call
                # carries it; an ordinary turn's call is unchanged.
                cue = ({"proactive": True, "proactive_cue": text}
                       if proactive else {})
                try:
                    reply, auto_mem = await self._chat_dm(
                        history, is_admin=is_admin, pkey=pkey, **cue)
                except Exception as e:
                    logger.warning("[Agent] private-chat LLM failed: %s", e)
                    return False
                if not reply:
                    return False

                final = self._finalize_reply(reply, log_ctx=f"private user={user_id}")
                if final is None:
                    return False
                reply, _, pending_core, had_visible_candidate = final
                if had_visible_candidate and not reply:
                    return False
                if not reply or re.match(r"PASS\b", reply, re.IGNORECASE):
                    logger.info("[Agent] PASS (private user=%s)", user_id)
                    return False

                send_result = await self._send_dm(user_id, reply)
                if not send_result.success:
                    logger.warning(
                        "[Agent] private delivery failed (user=%s, partial=%s)",
                        user_id, send_result.partial)
                    # The reader saw the delivered prefix, so it is committed
                    # the way the group path commits one, or the next turn
                    # may say the same line again. The core note and
                    # auto-memory describe the whole answer and are withheld.
                    if send_result.partial and send_result.delivered:
                        async with self.locks[pkey]:
                            history.append({"role": "assistant",
                                            "content": send_result.delivered})
                            self.dm_history[user_id] = history[-40:]
                            if not proactive:
                                self._dm_unanswered.pop(user_id, None)
                            committed = True
                    return send_result.partial

                async with self.locks[pkey]:
                    history.append({"role": "assistant", "content": reply})
                    self.dm_history[user_id] = history[-40:]
                    if not proactive:
                        self._dm_unanswered.pop(user_id, None)
                    committed = True
                    self._commit_core_memory(pkey, pending_core)
                    if auto_mem:
                        self._save_auto_memory(pkey, auto_mem)
                    # Same leak as the history append, one file over:
                    # `ctx_lines` would store the caller's cue as a line the
                    # reader wrote. And what a proactive reply answers is not
                    # a message at all, so there is nothing to attribute.
                    if self.react_learn_enabled and not proactive:
                        self.pending_reactions.record(
                            channels.dm_learning_key(user_id), reply=reply,
                            ctx_lines=[f"user: {_truncate_framed(text, 100)}"],
                            mode=ADMIN_MODE if is_admin else "called",
                            target_uid=user_id, mids=send_result.message_ids,
                            ts=time.time())
                logger.info("[Agent] private (%s): %s", user_id, reply[:80])
                return True
            finally:
                if self._dm_send_tasks.get(pkey) is asyncio.current_task():
                    self._dm_send_tasks.pop(pkey, None)
                # Empty on a proactive turn: its text is the caller's cue.
                if said and not committed:
                    async with self.locks[pkey]:
                        self._dm_unanswered[user_id] = said[-3:]

    def _finalize_reply(self, reply: str, *, log_ctx: str):
        """Post-LLM pipeline shared by every reply path: core-memory tag,
        output filter, sanitize (before any state is committed), [AT:] marker.
        Returns (reply, at_uid, pending_core, had_visible), or None if the
        filter blocked the reply."""
        reply, pending_core = self._extract_core_update(reply or "")
        filtered, blocked = self._apply_output_filter(reply)
        if blocked:
            logger.warning("[Agent] output_filter blocked (%s): %s | original=%s",
                           log_ctx, blocked, reply[:120])
            return None
        had_visible = bool(filtered.strip())
        reply = TextProcessing._sanitize_reply(
            filtered, self._validator_lang(), self.reply_style)
        reply = TextProcessing._unwrap_reply(reply)
        # Non-digit targets included: connector ids look like "telegram:12345".
        at_match = re.search(r'\[AT:([^\]\s]+)\]', reply)
        at_uid = at_match.group(1) if at_match else ""
        # Strip every marker (a second, hallucinated one would ship as text).
        reply = re.sub(r'\[AT:[^\]\s]+\]', '', reply).strip()
        return reply, at_uid, pending_core, had_visible

    @staticmethod
    def _dm_scope_key(pkey: str) -> str:
        """Learning scope (`dm:<uid>`) of the DM whose memory namespace is
        `pkey` (`private:<uid>`); derived, so no call site can desync them."""
        return channels.learning_key(pkey)

    async def _chat_dm(self, history: list[dict], is_admin: bool = True, proactive: bool = False, pkey: str = "", proactive_cue: str = "") -> tuple[str, str]:
        """Private chat. Same OpenAI-compatible endpoint as group chat, with
        LLM_DM_MODEL as an optional alternate model name.

        is_admin=True  → admin-style override (very close, all defenses off)
        is_admin=False → ordinary-friend override (looser than group chat,
                         but doesn't pretend close acquaintance; some
                         distance preserved since the relationship is unclear).
        pkey = "private:<uid>" memory namespace — without it, private-chat
        memories / core notes are write-only (the model saves a mem but never
        sees it next turn, which reads as "forgot everything I told it").
        The LEARNING scope is a different key derived from it — see
        `_dm_scope_key`.

        `proactive_cue` is a connector caller's briefing for a proactive turn.
        It joins the internal cue as bounded external material: the engine's
        own `<proactive>` note still says what the turn is and that PASS is
        allowed, because a scheduler's text has no authority to say either."""
        prompt = self._build_dm_prompt(history, is_admin=is_admin,
                                       proactive=proactive, pkey=pkey,
                                       proactive_cue=proactive_cue)
        system, messages = prompt.system, prompt.messages
        # Grounded here, once, rather than inside `_call_llm`, so a retry
        # below answers from the same research without paying for the gate
        # again. An unprompted opening has no question to research.
        if not proactive:
            messages = await self._ground_with_search(messages)

        async def draft(system_text: str) -> tuple[str, str]:
            raw = await self._call_llm(
                system=system_text,
                messages=messages,
                model=self.llm_dm_model,
                max_tokens=4096,
                enable_search=False,
                json_object=True,
                # The 1:1 reply: `reply` is the whole schema, so prose recovered
                # without response_format is unambiguous. Also the path the
                # blank-JSON defect hits — every turn after the first replays
                # the persona's own assistant turns.
                plain_text_fallback=True,
            )
            reply, reasoning, intent, mem = TextProcessing._parse_model_output(raw)
            if reasoning:
                logger.debug("[Agent] private model metadata parsed (intent=%s, reasoning_chars=%d)",
                             intent or "?", len(reasoning))
            return reply, mem

        reply, mem = await draft(system)
        # The private protocol has no PASS, so a turn that renders to nothing
        # is a failure, worth exactly one more call; a second failure says the
        # trouble is not the draft. Not on a proactive turn: its cue offers
        # PASS, so an empty draft there is the persona declining to speak.
        if not proactive and self._draft_should_be_retried(reply):
            logger.info("[Agent] private draft renders empty, retrying once")
            # "\n\n": the protocol block ends without a newline, and the
            # note must not read as the tail of its closing tag.
            retry_reply, retry_mem = await draft(
                system + "\n\n" + _EMPTY_DRAFT_RETRY_NOTE)
            # The memory the first draft asked to save is a fact about the
            # conversation, not about the draft that failed to render.
            reply, mem = retry_reply, (retry_mem or mem)
        return reply, mem

    def _draft_should_be_retried(self, reply: str) -> bool:
        """Would this draft reach the reader as nothing at all, by accident?

        A preview of `_finalize_reply`, which still runs on whatever comes
        back. Only the sanitize half: a guard refusing the draft (its label
        is in `_REFUSAL_LABELS`) or the output filter blocking it is a
        decision on the words the model produced, and asking again would buy
        the same no at full price, from input a user can choose."""
        text, refusal = TextProcessing._sanitize_reply_with_reason(
            reply or "", self._validator_lang(), self.reply_style)
        if refusal:
            # Still a refusal, but the label set has drifted from the guards.
            if refusal not in _REFUSAL_LABELS:
                logger.warning(
                    "[Agent] unknown sanitizer refusal label %r, not retried; "
                    "add it to textproc._REFUSAL_LABELS", refusal)
            return False
        text = text.strip().strip('"').strip("「」")
        return not re.sub(r'\[AT:[^\]\s]+\]', '', text).strip()
