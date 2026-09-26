"""One group turn's model work: the prompt, the gate, then the reply."""
from __future__ import annotations

import logging
import time
from typing import Optional

from .access import ADMIN_MODE
from .decision import GATED_MODES
from .textproc import (
    TextProcessing,
)

logger = logging.getLogger("agent")


class Thinking:
    async def _think(
        self,
        group_id: str,
        mode: str,
        latest_text: str = "",
        caller_override: Optional[tuple] = None,
    ) -> tuple[str, str, str]:
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
            # bill against this cap; 1200 sat under the measured tail (~940
            # visible completion alone) and truncated about 1 turn in 10.
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
        reply, reasoning, intent, mem = TextProcessing._parse_model_output(raw)
        if reasoning:
            logger.debug("[Agent] group model metadata parsed (mode=%s intent=%s, reasoning_chars=%d)",
                         mode, intent or "?", len(reasoning))
        return reply, intent or "chat", mem
