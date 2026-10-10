"""Whether the persona speaks: the rules that pick a group turn's mode, the
pacing that skips some, the cheap gate model that decides the rest, and the
group turn's model work (`_think`)."""
from __future__ import annotations

import logging
import random
import time
from typing import Optional

from .access import ADMIN_MODE
from .textproc import (
    SLEEP_PASS_PROB,
    SUB_TRIGGER_PASS_PROB,
    _TOPIC_LEXICON,
    TextProcessing,
)

logger = logging.getLogger("agent")

#: Modes the persona chose to speak in rather than was asked; the gate model
#: decides these before the main model writes anything.
GATED_MODES = ("judge", "followup", "proactive")

#: Reasons the callers act on.
STICKY_CALL = "sticky call"
SLEEP_WINDOW = "sleep window"


def choose_group_mode(*, addressed: bool, is_admin: bool,
                      sticky_admin: Optional[bool], in_followup: bool,
                      counter: int, trigger_count: int,
                      never_replied: bool) -> tuple[str, str]:
    """A group turn's mode and why, or ("", why not). `sticky_admin` is None
    without a recent call still pending, else whether its caller is the admin."""
    if addressed:
        # The admin @/naming the bot gets the warmer admin persona; anyone
        # else goes through called. Un-addressed admin chatter takes the same
        # gates as everyone else's.
        return (ADMIN_MODE if is_admin else "called"), "addressed"
    if sticky_admin is not None:
        # A call whose own message lost the debounce race (e.g. "BOT" then an
        # image) still owns the turn, in the caller's register.
        return (ADMIN_MODE if sticky_admin else "called"), STICKY_CALL
    if in_followup:
        return "followup", "followup window"
    if counter >= trigger_count:
        return "judge", "trigger count"
    if never_replied and counter >= max(10, trigger_count // 3):
        # First-time presence: a real person would chime in well before 30
        # messages of pure lurking; after the first reply the regular count
        # applies.
        return "judge", "first appearance"
    return "", "below the trigger count"


def pacing_skip(mode: str, *, first_appearance: bool, sleep_hour: bool) -> str:
    """Why a spontaneous turn is skipped for the sake of a natural rhythm, or
    "". Called and admin turns are explicit asks and never skipped, and the
    first appearance in a group is not either: the persona has to surface
    once to be a member."""
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
        # Model routing — two stages for self-initiated modes:
        #   1. GATE (cheapest model): judge / followup / proactive first ask the
        #      cheap "judgment" model only "would a real person reply here, or
        #      stay quiet?". Most spontaneous messages PASS here and cost nothing
        #      more than one cheap call.
        #   2. REPLY (unified, main model): the line that actually gets sent is
        #      always written by the main model (_pick_group_model — main unless a
        #      rate spike forces a downgrade). called / admin are addressed
        #      directly and skip straight to stage 2.
        # Net: cheap, high-frequency gating; every reply the group sees is pro.
        if mode in GATED_MODES:
            speak, gate_intent = await self._gate(prompt)
            if not speak:
                # Stayed quiet — only the cheap gate call was spent.
                return "", gate_intent or "chat", ""

        # Stage 2 (and the only stage for called / admin): the main model writes
        # the reply that's actually sent. Count it toward the rate window so a
        # genuine burst can still trigger a temporary downgrade (but called/
        # admin are exempt from the frequency downgrade — see _pick_group_model).
        model_to_use = self._pick_group_model(mode)
        self.model_calls.append(time.time())
        enable_search = mode in ("called", ADMIN_MODE, "followup")
        raw = await self._call_llm(
            system=prompt.system,
            messages=[{"role": "user", "content": prompt.user}],
            model=model_to_use,
            # 3000, not 1200: on a reasoning model the hidden thinking tokens
            # bill against this cap, and 1200 sits under the measured tail
            # (~940 for the visible completion alone), truncating about 1 turn
            # in 10.
            max_tokens=3000,
            enable_search=enable_search,
            disable_thinking=False,
            json_object=True,
            # The group reply, same schema as the 1:1 one. Never on the gate
            # call above: its output is a PASS/reply decision nobody reads,
            # and recovered prose would turn "could not decide" into "decided
            # to say this".
            plain_text_fallback=True,
            # Search decisions judge the real trigger text, not the whole
            # rendered prompt (see _decide_and_search).
            search_hint=latest_text,
        )
        reply, reasoning, intent, mem = TextProcessing._parse_model_output(
            raw, model_to_use)
        if reasoning:
            logger.debug("[Agent] group model metadata parsed (mode=%s intent=%s, reasoning_chars=%d)",
                         mode, intent or "?", len(reasoning))
        return reply, intent or "chat", mem

    async def _gate(self, prompt) -> tuple[bool, str]:
        """Stage 1 for the gated modes: the cheapest model decides only
        whether a person would speak here. Returns (speak, intent)."""
        gate_raw = await self._call_llm(
            system=prompt.gate_system,
            messages=[{"role": "user", "content": prompt.user}],
            model=self.llm_judge_model,
            max_tokens=1500,
            enable_search=False,
            disable_thinking=True,
            json_object=True,
            # The PASS/reply gate can't run at the default temperature=1.0
            # (hot sampling → whether-to-reply drifts randomly). 0.3 makes
            # the decision stable and cuts pointless chime-ins / cold PASSes.
            temperature=0.3,
        )
        gate_reply, _gr, gate_intent, _gm = TextProcessing._parse_model_output(
            gate_raw, self.llm_judge_model)
        speak = bool(gate_reply) and gate_reply.strip().upper() != "PASS"
        return speak, gate_intent

    def _compute_chat_signals(self, group_id: str, history: list) -> dict:
        """Compute chat signals for prompt: topic heat / active count / time since bot spoke / topic type."""
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
