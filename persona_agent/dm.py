"""The one-on-one turn: admission done, a reply to one person."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from contextlib import asynccontextmanager

from .access import ADMIN_MODE, PAGE_PLATFORM
from . import channels
from . import decision_log
from .connector import current_sink
from .messages import message_time
# An emoji-only draft the sanitizer eats would come back identical from an
# unchanged prompt, so the one retry carries a note.
from .decision import EMPTY_DRAFT_RETRY_NOTE as _EMPTY_DRAFT_RETRY_NOTE
from .decision import PASS, SEND
from .textproc import (
    TextProcessing,
    _clean_prompt_source,
    _strip_web_desc,
    _truncate_framed,
)

logger = logging.getLogger("agent")

# The empty-draft note's contract, for a draft that was PASS or that a guard refused.
_PASS_DRAFT_RETRY_NOTE = (
    "Your previous draft was PASS, but a private chat has no PASS: the person "
    "is waiting for an answer. Emit the same JSON object again — same keys, "
    "same shape — with a `reply` of at least one word."
)
_REFUSED_DRAFT_RETRY_NOTE = (
    "Your previous draft was refused ({reason}) and was not sent. Emit the "
    "same JSON object again — same keys, same shape — with a `reply` of at "
    "least one word, in character, without what was refused."
)

# A refusal or a PASS is the model's answer to these words: one reader gets a
# second draft for it this often, so an induced refusal cannot double the spend.
_DECLINED_RETRY_GAP_S = 300.0
_DECLINED_RETRY_READERS = 4096

_DM_HISTORY_MAX = 60
_DM_HISTORY_KEEP = 40
_UNANSWERED_KEEP_CHARS = 1500


def _kept_unanswered(said: list[str]) -> list[str]:
    """The newest lines within _UNANSWERED_KEEP_CHARS, and never fewer
    than the last: what someone said during an outage waits for a reply."""
    kept: list[str] = []
    size = 0
    for line in reversed(said):
        size += len(line) + (1 if kept else 0)
        if kept and size > _UNANSWERED_KEEP_CHARS:
            break
        kept.append(line)
    return kept[::-1]


def _trimmed_history(history: list[dict]) -> list[dict]:
    """Drop a batch of old turns at once: dropping a little every turn would
    shift the whole history and lose its prefix cache each time."""
    return history[-_DM_HISTORY_KEEP:] if len(history) > _DM_HISTORY_MAX else history


def _page_turns(path, conversation: str) -> list[dict]:
    """The page's own saved copy of its chat (browser-chat.json) as turns,
    for a page chat that has no recent window yet; [] if it is another chat."""
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(saved, dict) or str(saved.get("conversation") or "") != conversation:
        return []
    turns: list[dict] = []
    for message in saved.get("messages") or []:
        if not isinstance(message, dict):
            continue
        role, text = message.get("role"), message.get("text")
        if role not in ("user", "assistant") or not isinstance(text, str) or not text.strip():
            continue
        # One turn per side in a row, as the history keeps them.
        if turns and turns[-1]["role"] == role:
            turns[-1]["content"] += "\n" + text
        else:
            turns.append({"role": role, "content": text})
    # The words still waiting for this answer are the turn being answered.
    while turns and turns[-1]["role"] == "user":
        turns.pop()
    return turns[-_DM_HISTORY_KEEP:]


class DirectMessages:
    async def _handle_dm(self, user_id: str, payload: dict,
                              is_admin: bool = True,
                              proactive: bool = False) -> bool:
        """One DM, in arrival order: a memory command, a caller's `proactive`
        cue (never history, never the reader's), or the reader's words, which
        take the next turn unless a newer message of theirs is waiting to."""
        pkey = channels.dm_routing_key(user_id)
        # Its place is taken before the first await: DMs are answered in the
        # order they came, however long each takes to read.
        gate, item = self._enter_line(pkey)
        # Whatever goes wrong before it is read gives the place back: an
        # unread place would hold up every later DM of theirs.
        try:
            text = await self._extract_text(payload)
            ctrl_text = _strip_web_desc(text) if text else ""
            # A cue is the caller's text: it cannot run a memory command.
            is_command = (bool(text) and not proactive
                          and self._is_memory_command(ctrl_text))
        except BaseException:
            self._leave_line(pkey, gate, item)
            raise
        if not text:
            self._leave_line(pkey, gate, item)
            return False

        sender = payload.get("sender") or {}
        nickname = (_clean_prompt_source(
            sender.get("card") or sender.get("nickname")) or "?")[:8]

        def run_command() -> str:
            """Answered like a room's: no model call, no history, and it does
            not consume the pending reply."""
            self.last_dm_activity_at[user_id] = time.time()
            return self._handle_memory_command(
                pkey, ctrl_text, user_id, nickname)

        async def say(answer: str, *, background: bool = False) -> bool:
            return await self._say_dm_memory_answer(
                user_id, answer, background=background)

        # The local page answers at once; elsewhere a burst becomes one turn.
        debounce = (0.0 if channels.platform_of(pkey) == PAGE_PLATFORM
                    else self.message_debounce_sec)

        sent_at = message_time(payload)

        def take_in() -> int:
            """The reader's words wait for their next turn. Run in line, so a
            reaction is matched against the replies committed before it.
            Returns the message's number in this conversation."""
            self.last_dm_activity_at[user_id] = time.time()
            self._wake(pkey)
            # The turn is dated by the newest message it answers.
            self.__dict__.setdefault("_dm_heard_at", {})[user_id] = min(
                sent_at or time.time(), time.time())
            self._recent_dirty.add(pkey)
            if self.react_learn_enabled:
                entry = self.pending_reactions.match(
                    channels.dm_learning_key(user_id),
                    sender_uid=user_id, is_dm=True, now=time.time())
                if entry:
                    self._spawn(self._process_reaction(
                        entry, text, nickname, user_id, is_admin,
                        conv_id=channels.dm_learning_key(user_id),
                        is_dm=True))
            self._dm_unanswered.setdefault(user_id, []).append(text)
            self._msg_seq[pkey] += 1
            return self._msg_seq[pkey]

        waiting = not is_command and not proactive and debounce > 0
        if is_command:
            self._ready(pkey, gate, item, run_command, message=False, say=say)
        elif proactive:
            # A cue is not a reaction from the reader, and joins no user turn.
            self._ready(pkey, gate, item, lambda: True, message=False, turn=True)
        else:
            # Taken in now; with a debounce the turn is asked for after it.
            self._ready(pkey, gate, item, take_in, message=True,
                        turn=not waiting)
        try:
            outcome = await item.waiter
        except BaseException:
            # Cancelled (only at shutdown) with the turn already its own.
            if item.granted:
                self._end_turn(pkey, gate)
            raise
        if outcome is None:
            # Overtaken by a newer message, whose turn answers this one too,
            # or a command that is answered once the turn in flight is over.
            return False
        if waiting:
            await asyncio.sleep(debounce)
            # A newer message of theirs asks for the turn that answers both.
            if self._msg_seq.get(pkey, 0) != outcome:
                return False
            gate, item = self._enter_line(pkey)
            self._ready(pkey, gate, item, lambda: True, message=False, turn=True)
            try:
                if await item.waiter is None:
                    return False
            except BaseException:
                if item.granted:
                    self._end_turn(pkey, gate)
                raise
            # One still being read when this asked was taken in ahead of it.
            if self._msg_seq.get(pkey, 0) != outcome:
                self._end_turn(pkey, gate)
                return False
        if is_command:
            try:
                handled = await say(outcome)
            except Exception as e:
                if not item.carried:
                    raise
                # The response must still be given: others' answers ride in it.
                logger.warning("[Agent] memory command answer failed "
                               "(conversation=%s): %s", pkey, e)
                handled = False
            # Later commands whose answers had no way out but this response.
            await self._say_carried(pkey, item.carried)
            return handled
        try:
            return await self._dm_turn(user_id, pkey, text, is_admin, proactive,
                                       nickname=nickname)
        finally:
            self._end_turn(pkey, gate)

    @asynccontextmanager
    async def _dm_sending(self, pkey: str):
        """The DM's send lock, which `_send_dm` inside it does not take again."""
        async with self.send_locks[pkey]:
            self._dm_send_tasks[pkey] = asyncio.current_task()
            try:
                yield
            finally:
                if self._dm_send_tasks.get(pkey) is asyncio.current_task():
                    self._dm_send_tasks.pop(pkey, None)

    def _commit_dm_history(self, user_id: str, pkey: str, history: list[dict]) -> None:
        """Keep `history` as the reader's turns, trimmed; the unconsolidated
        turns the trim drops wait in the DM spill for consolidation."""
        before = self.dm_history.get(user_id, [])
        kept = _trimmed_history(history)
        held = {id(turn) for turn in kept}
        folded = self.folded_upto.get(pkey, 0)
        dropped = {id(turn): turn for turn in [*before, *history]
                   if id(turn) not in held and int(turn.get("seq") or 0) > folded}
        if dropped:
            self._spill_rows(pkey, sorted(dropped.values(),
                                          key=lambda turn: int(turn.get("seq") or 0)),
                             dm_reader=user_id)
        self.dm_history[user_id] = kept
        vars(self).get("_dm_heard_at", {}).pop(user_id, None)
        self._recent_dirty.add(pkey)
        self._maybe_flush_recent()

    def _rehydrate_page(self, user_id: str, pkey: str) -> None:
        """A page chat with no turns held reads the page's saved copy once."""
        if user_id in self.dm_history or channels.platform_of(pkey) != PAGE_PLATFORM:
            return
        done = self.__dict__.setdefault("_page_rehydrated", set())
        if pkey in done:
            return
        done.add(pkey)
        turns = _page_turns(self.memory_file.parent / "desktop" / "browser-chat.json",
                            user_id.split(":", 1)[-1])
        for turn in turns:
            turn["t"], turn["seq"] = 0.0, self._next_seq(pkey)
        if turns:
            self.dm_history[user_id] = turns
            self._recent_dirty.add(pkey)

    async def _say_dm_memory_answer(self, user_id: str, answer: str, *,
                                    background: bool = False) -> bool:
        """Send a memory command's answer to a DM. `background`: no request
        of the conversation is open to carry it."""
        pkey = channels.dm_routing_key(user_id)
        async with self._dm_sending(pkey):
            if background:
                send_result = await self._send_background(
                    pkey, lambda: self._send_dm(user_id, answer),
                    reason="follow_up")
            else:
                send_result = await self._send_dm(user_id, answer)
        if not send_result.success:
            logger.warning("[Agent] memory command delivery failed (user=%s)",
                           user_id)
            return send_result.partial
        logger.info("[Agent] memory command (user=%s): %s", user_id, answer[:60])
        return True

    async def _dm_turn(self, user_id: str, pkey: str, text: str,
                       is_admin: bool, proactive: bool, *,
                       nickname: str = "?") -> bool:
        """The turn the line gave this handler: one model call under the turn
        budget, the send, the commit. Nothing of this user's enters meanwhile."""
        # The reader's words this turn; kept for their next turn unless committed.
        said: list[str] = []
        committed = False
        mode = "proactive" if proactive else ADMIN_MODE if is_admin else "called"

        def silent(reason: str) -> None:
            # Activity shows a turn that said nothing, and why.
            asked = "\n".join(said)
            decision_log.record(pkey, mode, False, reason, asked,
                                answered=asked, sender=nickname)

        try:
            async with self.locks[pkey]:
                if proactive:
                    # Shared with the agent's own proactive loop.
                    self.last_proactive_at[
                        channels.dm_learning_key(user_id)] = time.time()
                self._wake(pkey)
                self._rehydrate_page(user_id, pkey)
                history = list(self.dm_history.get(user_id, []))
                # A proactive turn leaves the history ending on the bot,
                # which is what lets _build_dm_prompt add its internal cue.
                if not proactive:
                    # Everything let in since the last committed reply is one
                    # user turn, so two user turns never sit in a row.
                    said = list(self._dm_unanswered.get(user_id) or [text])
                    heard = vars(self).get("_dm_heard_at", {}).get(user_id)
                    history.append({"role": "user",
                                    "content": "\n".join(said),
                                    "name": nickname, "t": heard or time.time(),
                                    "seq": self._next_seq(pkey)})
                history = _trimmed_history(history)

            cue = ({"proactive": True, "proactive_cue": text}
                   if proactive else {})
            try:
                reply, auto_mem = await self._within_turn_budget(self._chat_dm(
                    history, is_admin=is_admin, pkey=pkey, **cue))
            except Exception as e:
                logger.warning("[Agent] DM model call failed: %s", e)
                # The page's chat reports every failure: there the admin checks the setup.
                page = channels.platform_of(pkey) == PAGE_PLATFORM
                # Tell the waiting reader; not committed to the history.
                if not proactive and (page or self._excuse_begin(pkey)):
                    delivered = False
                    sink = current_sink.get()
                    start = len(sink.items) if sink is not None else 0
                    try:
                        async with self._dm_sending(pkey):
                            delivered = (await self._send_dm(
                                user_id, self._model_failure_excuse(text))).success
                    finally:
                        if not page:
                            self._excuse_end(pkey, delivered)
                    # Marked, so a connector can tell the excuse from a reply.
                    for item in sink.items[start:] if sink is not None else ():
                        item["reason"] = "excuse"
                silent("model failed")
                return False
            if not reply:
                silent("passed")
                return False

            final = self._final_reply(reply, log_ctx=f"DM user={user_id}")
            if final.verdict == PASS:
                logger.info("[Agent] PASS (DM user=%s)", user_id)
            if final.verdict != SEND:
                silent("passed" if final.verdict == PASS else "blocked")
                return False
            reply, pending_core = final.text, final.core_note

            def record(spoken: str) -> None:
                # A one-on-one chat shows in Activity what was said, as a group does.
                decision_log.record(
                    pkey, mode, True, "proactive" if proactive else "addressed",
                    spoken, answered="\n".join(said))

            async with self._dm_sending(pkey):
                send_result = await self._send_dm(user_id, reply)
            if not send_result.success:
                logger.warning(
                    "[Agent] DM delivery failed (user=%s, partial=%s)",
                    user_id, send_result.partial)
                # Commit the delivered prefix; the core note and memory are withheld.
                if send_result.partial and send_result.delivered:
                    async with self.locks[pkey]:
                        history.append({"role": "assistant",
                                        "content": send_result.delivered,
                                        "t": time.time(), "seq": self._next_seq(pkey)})
                        self._commit_dm_history(user_id, pkey, history)
                        if not proactive:
                            self._dm_unanswered.pop(user_id, None)
                        committed = True
                    record(send_result.delivered)
                else:
                    silent("delivery failed")
                return send_result.partial

            async with self.locks[pkey]:
                history.append({"role": "assistant", "content": reply,
                                "t": time.time(), "seq": self._next_seq(pkey)})
                self._commit_dm_history(user_id, pkey, history)
                if not proactive:
                    self._dm_unanswered.pop(user_id, None)
                committed = True
                self._commit_core_memory(pkey, pending_core)
                if auto_mem:
                    self._save_auto_memory(pkey, auto_mem)
                self._mark_used(pkey, reply)
                self._maybe_consolidate(pkey, "trim")
                # A proactive reply answers no message of the reader's. On
                # record before the line moves: the next message may react.
                if self.react_learn_enabled and not proactive:
                    self.pending_reactions.record(
                        channels.dm_learning_key(user_id), reply=reply,
                        ctx_lines=[f"{nickname}: {_truncate_framed(text, 100)}"],
                        mode=ADMIN_MODE if is_admin else "called",
                        target_uid=user_id, mids=send_result.message_ids,
                        ts=time.time())
            record(reply)
            logger.info("[Agent] DM reply (%s): %s", user_id, reply[:80])
            return True
        finally:
            # No await: this also runs when the turn is cancelled.
            if said and not committed:
                self._dm_unanswered[user_id] = _kept_unanswered(said)
                self._recent_dirty.add(pkey)

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
        # Searched once here, so the retry reuses it. Before the context joins
        # the last turn: the search decision reads that turn as the person's.
        if not proactive:
            messages = await self._ground_with_search(messages)
        messages = prompt.messages_with_context(messages)

        async def draft(system_text: str) -> tuple[str, str]:
            raw = await self._call_llm(
                system=system_text,
                messages=messages,
                model=self.llm_dm_model,
                max_tokens=4096,
                enable_search=False,
                # No hidden reasoning: the protocol carries its own `reasoning` field.
                disable_thinking=True,
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
        # A DM has no PASS, so a draft that would send nothing is retried
        # once; a proactive turn's empty draft is the persona declining.
        note = "" if proactive else self._draft_retry_note(reply)
        if note and note != _EMPTY_DRAFT_RETRY_NOTE and not self._declined_retry_free(pkey):
            note = ""
        if note:
            logger.info("[Agent] DM draft would send nothing, retrying once")
            # The protocol block ends without a newline.
            retry_reply, retry_mem = await draft(system + "\n\n" + note)
            # The first draft's memory is still a fact about the conversation.
            reply, mem = retry_reply, (retry_mem or mem)
        return reply, mem

    def _declined_retry_free(self, pkey: str) -> bool:
        """Whether this reader's declined draft may be asked for again now."""
        asked = vars(self).setdefault("_declined_retry_at", {})
        now = time.monotonic()
        last = asked.get(pkey)
        if last is not None and now - last < _DECLINED_RETRY_GAP_S:
            return False
        if len(asked) >= _DECLINED_RETRY_READERS:
            asked.clear()
        asked[pkey] = now
        return True

    def _draft_retry_note(self, reply: str) -> str:
        """The note for a second draft when this one would send nothing: a
        PASS, a guard's refusal, or a render to nothing; else ""."""
        if re.fullmatch(r"\W*PASS\W*", (reply or "").strip(), re.IGNORECASE):
            return _PASS_DRAFT_RETRY_NOTE
        filtered, blocked = self._apply_output_filter(reply or "")
        text, refusal = TextProcessing._sanitize_reply_with_reason(
            filtered, self.agent_lang, self.reply_style)
        if blocked or refusal:
            return _REFUSED_DRAFT_RETRY_NOTE.format(reason=refusal or blocked)
        text = text.strip().strip('"').strip("「」")
        if re.sub(r'\[AT:[^\]\s]+\]', '', text).strip():
            return ""
        return _EMPTY_DRAFT_RETRY_NOTE
