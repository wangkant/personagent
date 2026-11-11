"""Whether the persona speaks: the rules that pick a group turn's mode, the
pacing that skips some, the cheap gate model that decides the rest, and the
group turn's model work (`_think`)."""
from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Optional

from .access import ADMIN_MODE
from .search import SEARCH_CONTEXT_LINES, SearchHint
from .textproc import (
    SLEEP_PASS_PROB,
    SUB_TRIGGER_PASS_PROB,
    _TOPIC_LEXICON,
    TextProcessing,
    _clean_prompt_source,
)

logger = logging.getLogger("agent")

#: Unasked modes: the cheap gate model decides before the main model writes.
GATED_MODES = ("judge", "followup", "proactive")

_CORE_TAG_LEFT = re.compile(r"\[\s*/?\s*CORE_UPDATE", re.IGNORECASE)

#: Reasons the callers act on.
STICKY_CALL = "sticky call"
SLEEP_WINDOW = "sleep window"

#: Verdicts of `_final_reply`.
SEND, PASS, BLOCKED = "send", "pass", "blocked"

#: Appended to the system prompt for the one retry of a blocked or empty
#: draft, in a group turn and in a private chat (dm.py).
EMPTY_DRAFT_RETRY_NOTE = (
    "Your previous draft could not be rendered. Emit the same JSON object "
    "again — same keys, same shape — with a `reply` of at least one word "
    "and no emoji or markup inside it."
)


def is_pass_sentinel(text: str) -> bool:
    """The model's bare PASS; "Pass auf dich auf" or "pass the salt" is a reply."""
    return bool(re.fullmatch(r"\W*PASS\W*", (text or "").strip(), re.IGNORECASE))


@dataclass(frozen=True)
class FinalReply:
    verdict: str
    text: str = ""
    at_uid: str = ""
    core_note: str = ""


def choose_group_mode(*, addressed: bool, is_admin: bool,
                      sticky_admin: Optional[bool], in_followup: bool,
                      counter: int, trigger_count: int,
                      never_replied: bool) -> tuple[str, str]:
    """A group turn's mode and why, or ("", why not). `sticky_admin` is None
    without a recent call still pending, else whether its caller is the admin."""
    if addressed:
        # Un-addressed admin chatter takes the same gates as anyone's.
        return (ADMIN_MODE if is_admin else "called"), "addressed"
    if sticky_admin is not None:
        # A call that lost the debounce race ("BOT" then an image) keeps the turn.
        return (ADMIN_MODE if sticky_admin else "called"), STICKY_CALL
    if in_followup:
        return "followup", "followup window"
    if counter >= trigger_count:
        return "judge", "trigger count"
    if never_replied and counter >= max(10, trigger_count // 3):
        # A newcomer speaks up sooner than the regular count.
        return "judge", "first appearance"
    return "", "below the trigger count"


def pacing_skip(mode: str, *, first_appearance: bool, sleep_hour: bool) -> str:
    """Why a spontaneous turn is skipped for rhythm, or "". Never a called,
    admin or first-appearance turn."""
    if mode not in ("judge", "followup") or first_appearance:
        return ""
    if sleep_hour and random.random() < SLEEP_PASS_PROB:
        return SLEEP_WINDOW
    if mode == "judge" and random.random() < SUB_TRIGGER_PASS_PROB:
        return "spontaneous skip"
    return ""


class ReplyDecision:
    async def _think(
        self,
        group_id: str,
        mode: str,
        latest_text: str = "",
        caller_override: Optional[tuple] = None,
        retry_note: str = "",
    ) -> tuple[str, str, str]:
        await self._prepare_retrieval(latest_text, group_id)
        prompt = self._build_group_prompt(group_id, mode, latest_text,
                                          caller_override)
        system = prompt.system + ("\n\n" + retry_note if retry_note else "")
        # Unasked modes first ask the cheap gate whether to speak at all; the
        # sent line is always the main model's (_pick_group_model).
        if mode in GATED_MODES:
            speak, gate_intent = await self._gate(prompt)
            if not speak:
                return "", gate_intent or "chat", ""

        # Counted toward the rate window that can force a downgrade.
        model_to_use = self._pick_group_model(mode)
        self.model_calls.append(time.time())
        # A retry fixes the draft's form; a second search would be a second call.
        enable_search = mode in ("called", ADMIN_MODE, "followup") and not retry_note
        raw = await self._call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt.user}],
            model=model_to_use,
            # An endpoint that insists on reasoning spends it against this cap.
            max_tokens=3000,
            enable_search=enable_search,
            # No hidden reasoning: the protocol carries its own `reasoning`
            # field, and thinking on opens a different prompt than the gate's.
            disable_thinking=True,
            json_object=True,
            # Never on the gate: recovered prose would read as "decided to speak".
            plain_text_fallback=True,
            # Search gates on the trigger text, not the whole prompt.
            search_hint=self._search_hint(group_id, latest_text),
        )
        reply, reasoning, intent, mem = TextProcessing._parse_model_output(
            raw, model_to_use)
        if reasoning:
            logger.debug("[Agent] group model metadata parsed (mode=%s intent=%s, reasoning_chars=%d)",
                         mode, intent or "?", len(reasoning))
        return reply, intent or "chat", mem

    def _search_hint(self, group_id: str, latest_text: str) -> str:
        """The trigger, carrying the buffer lines before it, so "what do you
        think of it?" can be searched for what "it" is."""
        if not latest_text:
            return latest_text
        buf = list(self.buffers.get(group_id) or ())
        trigger = latest_text
        # The trigger is normally the buffer's last line, merged or cut.
        if buf and latest_text[:50] in buf[-1].get("text", ""):
            trigger = f"{_clean_prompt_source(buf.pop().get('name'))}: {latest_text}"
        lines = [f"{_clean_prompt_source(m.get('name'))}: {m.get('text', '')}"
                 for m in buf[-SEARCH_CONTEXT_LINES:]]
        return SearchHint(latest_text, lines + [trigger])

    def _finalize_reply(self, reply: str, *, log_ctx: str):
        """Core-memory tag, output filter, sanitize, [AT:] marker. Returns
        (reply, at_uid, pending_core, had_visible), or None if filtered."""
        reply, pending_core = self._extract_core_update(reply or "")
        # A malformed tag left behind: what follows it may be the private note.
        stray = _CORE_TAG_LEFT.search(reply)
        if stray:
            reply = reply[:stray.start()].rstrip()
        filtered, blocked = self._apply_output_filter(reply)
        if blocked:
            logger.warning("[Agent] output_filter blocked (%s): %s | original=%s",
                           log_ctx, blocked, reply[:120])
            return None
        had_visible = bool(filtered.strip())
        reply = TextProcessing._sanitize_reply(
            filtered, self.agent_lang, self.reply_style)
        reply = TextProcessing._unwrap_reply(reply)
        # Connector ids are not digits ("telegram:12345").
        at_match = re.search(r'\[AT:([^\]\s]+)\]', reply)
        at_uid = at_match.group(1) if at_match else ""
        # Every marker, or a second one would ship as text.
        reply = re.sub(r'\[AT:[^\]\s]+\]', '', reply).strip()
        return reply, at_uid, pending_core, had_visible

    def _final_reply(self, raw: str, *, log_ctx: str) -> FinalReply:
        """`_finalize_reply` plus its verdict: SEND, a deliberate PASS, or
        BLOCKED (filtered, or a visible draft the character policy emptied)."""
        final = self._finalize_reply(raw, log_ctx=log_ctx)
        if final is None:
            return FinalReply(BLOCKED)
        text, at_uid, core_note, had_visible = final
        if had_visible and not text:
            return FinalReply(BLOCKED)
        if not text or is_pass_sentinel(text):
            return FinalReply(PASS)
        return FinalReply(SEND, text, at_uid, core_note)

    async def _gate(self, prompt) -> tuple[bool, str]:
        """The cheap gate: would a person speak here. Returns (speak, intent)."""
        gate_raw = await self._call_llm(
            system=prompt.gate_system,
            messages=[{"role": "user", "content": prompt.user}],
            model=self.llm_judge_model,
            max_tokens=1500,
            enable_search=False,
            disable_thinking=True,
            json_object=True,
            # Low, so whether to speak does not drift at random.
            temperature=0.3,
        )
        gate_reply, _gr, gate_intent, _gm = TextProcessing._parse_model_output(
            gate_raw, self.llm_judge_model)
        speak = bool(gate_reply) and not is_pass_sentinel(gate_reply)
        return speak, gate_intent

    def _compute_chat_signals(self, group_id: str, history: list) -> dict:
        """Topic heat, active speakers, time since the bot spoke, topic type."""
        active_count = len({
            m.get("user_id") for m in history
            if m.get("user_id") and m.get("user_id") != self.qq_bot_id
        })

        heat = "hot" if len(history) >= 15 else ("moderate" if len(history) >= 5 else "quiet")

        last = self.last_reply_at.get(group_id, 0.0)
        if last == 0:
            since = "haven't spoken in a long time"
        else:
            delta = time.time() - last
            if delta < 60:
                since = f"{int(delta)}s ago"
            elif delta < 600:
                since = f"{int(delta // 60)}min ago"
            else:
                since = "10+ min ago"

        recent_text = " ".join(m.get("text", "") for m in history[-8:])
        recent_lc = recent_text.lower()
        lex = _TOPIC_LEXICON.get(self.agent_lang, _TOPIC_LEXICON["en"])
        if any(k in recent_lc for k in lex["work"]):
            ttype = "work/tech"
        elif any(k in recent_lc for k in lex["banter"]):
            ttype = "memes/banter"
        elif "?" in recent_text or "？" in recent_text:
            ttype = "question/discussion"
        else:
            ttype = "chitchat"

        return {
            "heat": heat,
            "active_count": active_count,
            "last_spoke": since,
            "type": ttype,
        }
