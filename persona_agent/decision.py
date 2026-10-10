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
from .textproc import (
    SLEEP_PASS_PROB,
    SUB_TRIGGER_PASS_PROB,
    _TOPIC_LEXICON,
    TextProcessing,
)

logger = logging.getLogger("agent")

#: Unasked modes: the cheap gate model decides before the main model writes.
GATED_MODES = ("judge", "followup", "proactive")

#: Reasons the callers act on.
STICKY_CALL = "sticky call"
SLEEP_WINDOW = "sleep window"

#: Verdicts of `_final_reply`.
SEND, PASS, BLOCKED = "send", "pass", "blocked"


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
    ) -> tuple[str, str, str]:
        await self._prepare_retrieval(latest_text, group_id)
        prompt = self._build_group_prompt(group_id, mode, latest_text,
                                          caller_override)
        # Unasked modes first ask the cheap gate whether to speak at all; the
        # sent line is always the main model's (_pick_group_model).
        if mode in GATED_MODES:
            speak, gate_intent = await self._gate(prompt)
            if not speak:
                return "", gate_intent or "chat", ""

        # Counted toward the rate window that can force a downgrade.
        model_to_use = self._pick_group_model(mode)
        self.model_calls.append(time.time())
        enable_search = mode in ("called", ADMIN_MODE, "followup")
        raw = await self._call_llm(
            system=prompt.system,
            messages=[{"role": "user", "content": prompt.user}],
            model=model_to_use,
            # Hidden reasoning tokens count against this cap.
            max_tokens=3000,
            enable_search=enable_search,
            disable_thinking=False,
            json_object=True,
            # Never on the gate: recovered prose would read as "decided to speak".
            plain_text_fallback=True,
            # Search decides on the trigger text, not the whole prompt.
            search_hint=latest_text,
        )
        reply, reasoning, intent, mem = TextProcessing._parse_model_output(
            raw, model_to_use)
        if reasoning:
            logger.debug("[Agent] group model metadata parsed (mode=%s intent=%s, reasoning_chars=%d)",
                         mode, intent or "?", len(reasoning))
        return reply, intent or "chat", mem

    def _finalize_reply(self, reply: str, *, log_ctx: str):
        """Core-memory tag, output filter, sanitize, [AT:] marker. Returns
        (reply, at_uid, pending_core, had_visible), or None if filtered."""
        reply, pending_core = self._extract_core_update(reply or "")
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
        if not text or re.match(r"PASS\b", text, re.IGNORECASE):
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
        speak = bool(gate_reply) and gate_reply.strip().upper() != "PASS"
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
