"""The one-on-one turn: admission done, a reply to one person."""
from __future__ import annotations

import asyncio
import logging
import re
import time

from .access import ADMIN_MODE
from . import channels
from .decision import PASS, SEND
from .textproc import (
    TextProcessing,
    _REFUSAL_LABELS,
    _truncate_framed,
)

logger = logging.getLogger("agent")

# Appended for the one DM retry: an emoji-only draft the sanitizer eats would
# come back identical from an unchanged prompt. It keeps the JSON contract.
_EMPTY_DRAFT_RETRY_NOTE = (
    "Your previous draft could not be rendered. Emit the same JSON object "
    "again — same keys, same shape — with a `reply` of at least one word "
    "and no emoji or markup inside it."
)


class DirectMessages:
    async def _handle_dm(self, user_id: str, payload: dict,
                              is_admin: bool = True,
                              proactive: bool = False) -> bool:
        """Run one DM turn in send/commit order without blocking intake. A
        `proactive` text is the caller's cue: never history, never the reader's."""
        pkey = channels.dm_routing_key(user_id)
        async with self.send_locks[pkey]:
            self._dm_send_tasks[pkey] = asyncio.current_task()
            # The reader's words this turn; kept for their next turn unless committed.
            said: list[str] = []
            committed = False
            try:
                text = await self._extract_text(payload)
                if not text:
                    return False

                # A proactive cue is not a reaction from the reader.
                if self.react_learn_enabled and not proactive:
                    entry = self.pending_reactions.match(
                        channels.dm_learning_key(user_id),
                        sender_uid=user_id, is_dm=True, now=time.time())
                    if entry:
                        self._spawn(self._process_reaction(
                            entry, text, "owner" if is_admin else "friend",
                            user_id, is_admin,
                            conv_id=channels.dm_learning_key(user_id),
                            is_dm=True))

                async with self.locks[pkey]:
                    if proactive:
                        # Shared with the agent's own proactive loop.
                        self.last_proactive_at[
                            channels.dm_learning_key(user_id)] = time.time()
                    else:
                        self.last_dm_activity_at[user_id] = time.time()
                    history = list(self.dm_history.get(user_id, []))
                    # A proactive turn leaves the history ending on the bot,
                    # which is what lets _build_dm_prompt add its internal cue.
                    if not proactive:
                        # Earlier uncommitted messages join this user turn,
                        # so two user turns never sit in a row.
                        said = self._dm_unanswered.get(user_id, []) + [text]
                        history.append({"role": "user",
                                        "content": "\n".join(said)})
                    history = history[-40:]

                cue = ({"proactive": True, "proactive_cue": text}
                       if proactive else {})
                try:
                    reply, auto_mem = await self._chat_dm(
                        history, is_admin=is_admin, pkey=pkey, **cue)
                except Exception as e:
                    logger.warning("[Agent] DM model call failed: %s", e)
                    # Tell the waiting reader; not committed to the history.
                    if not proactive and self._excuse_begin(pkey):
                        delivered = False
                        try:
                            delivered = (await self._send_dm(
                                user_id, self._model_failure_excuse())).success
                        finally:
                            self._excuse_end(pkey, delivered)
                    return False
                if not reply:
                    return False

                final = self._final_reply(reply, log_ctx=f"DM user={user_id}")
                if final.verdict == PASS:
                    logger.info("[Agent] PASS (DM user=%s)", user_id)
                if final.verdict != SEND:
                    return False
                reply, pending_core = final.text, final.core_note

                send_result = await self._send_dm(user_id, reply)
                if not send_result.success:
                    logger.warning(
                        "[Agent] DM delivery failed (user=%s, partial=%s)",
                        user_id, send_result.partial)
                    # Commit the delivered prefix; the core note and memory are withheld.
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
                    # A proactive reply answers no message of the reader's.
                    if self.react_learn_enabled and not proactive:
                        self.pending_reactions.record(
                            channels.dm_learning_key(user_id), reply=reply,
                            ctx_lines=[f"user: {_truncate_framed(text, 100)}"],
                            mode=ADMIN_MODE if is_admin else "called",
                            target_uid=user_id, mids=send_result.message_ids,
                            ts=time.time())
                logger.info("[Agent] DM reply (%s): %s", user_id, reply[:80])
                return True
            finally:
                if self._dm_send_tasks.get(pkey) is asyncio.current_task():
                    self._dm_send_tasks.pop(pkey, None)
                if said and not committed:
                    async with self.locks[pkey]:
                        self._dm_unanswered[user_id] = said[-3:]

    async def _chat_dm(self, history: list[dict], is_admin: bool = True, proactive: bool = False, pkey: str = "", proactive_cue: str = "") -> tuple[str, str]:
        """One DM model turn (LLM_DM_MODEL): `is_admin` picks the close or
        the friend register, `pkey` ("private:<uid>") the memory namespace,
        and `proactive_cue` is a scheduler's note, framed as external material.
        Returns (reply, memory)."""
        await self._prepare_retrieval(self._last_user_text(history), pkey)
        prompt = self._build_dm_prompt(history, is_admin=is_admin,
                                       proactive=proactive, pkey=pkey,
                                       proactive_cue=proactive_cue)
        system, messages = prompt.system, prompt.messages
        # Searched once here, so the retry reuses it.
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
                # `reply` is the whole schema, so recovered prose is unambiguous.
                plain_text_fallback=True,
            )
            reply, reasoning, intent, mem = TextProcessing._parse_model_output(
                raw, self.llm_dm_model)
            if reasoning:
                logger.debug("[Agent] DM model metadata parsed (intent=%s, reasoning_chars=%d)",
                             intent or "?", len(reasoning))
            return reply, mem

        reply, mem = await draft(system)
        # A DM has no PASS, so an empty render is retried once; a proactive
        # turn's empty draft is the persona declining.
        if not proactive and self._draft_should_be_retried(reply):
            logger.info("[Agent] DM draft renders empty, retrying once")
            # The protocol block ends without a newline.
            retry_reply, retry_mem = await draft(
                system + "\n\n" + _EMPTY_DRAFT_RETRY_NOTE)
            # The first draft's memory is still a fact about the conversation.
            reply, mem = retry_reply, (retry_mem or mem)
        return reply, mem

    def _draft_should_be_retried(self, reply: str) -> bool:
        """Would this draft render to nothing by accident? A guard's refusal is
        a decision, not an accident, and is not retried."""
        text, refusal = TextProcessing._sanitize_reply_with_reason(
            reply or "", self.agent_lang, self.reply_style)
        if refusal:
            if refusal not in _REFUSAL_LABELS:
                logger.warning(
                    "[Agent] unknown sanitizer refusal label %r, not retried; "
                    "add it to textproc._REFUSAL_LABELS", refusal)
            return False
        text = text.strip().strip('"').strip("「」")
        return not re.sub(r'\[AT:[^\]\s]+\]', '', text).strip()
