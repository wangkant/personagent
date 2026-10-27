"""Looking things up on the web when a turn needs it."""
from __future__ import annotations

import asyncio
import json
import logging

from .textproc import (
    _SEARCH_HINT_RE,
    _UNTRUSTED_INPUT_RULES,
    _fence_user_data,
    _prepend_search_results,
    _truncate_framed,
)

logger = logging.getLogger("agent")


class WebSearch:
    def _might_need_search(self, text: str) -> bool:
        """Cheap gate: does the message plausibly need a web lookup?"""
        t = (text or "").strip()
        if len(t) < 3:
            return False
        return bool(_SEARCH_HINT_RE.search(t))

    async def _web_search(self, query: str, max_results: int = 4) -> str:
        """Tavily if a key is set, else keyless DuckDuckGo."""
        if self.tavily_key:
            return await self._web_search_tavily(query, max_results)
        return await self._web_search_ddg(query, max_results)

    async def _web_search_tavily(self, query: str, max_results: int = 4) -> str:
        """Tavily results as a compact block, or '' on any failure."""
        try:
            async with self._http(timeout=20) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.tavily_key,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": max_results,
                        "include_answer": False,
                    },
                )
            if resp.status_code != 200:
                logger.warning("[Agent] Tavily HTTP %d: %s", resp.status_code, resp.text[:200])
                return ""
            results = resp.json().get("results", []) or []
        except Exception as e:
            logger.warning("[Agent] Tavily search failed (q=%r): %s", query, e)
            return ""
        return self._fmt_search(results, "content", max_results)

    @staticmethod
    def _fmt_search(results: list, body_key: str, n: int) -> str:
        lines = []
        for r in results[:n]:
            title = (r.get("title") or "").strip()
            body = (r.get(body_key) or "").strip()
            if title or body:
                lines.append((f"- {title}: {body}" if title else f"- {body}")[:300])
        return "\n".join(lines)

    async def _web_search_ddg(self, query: str, max_results: int = 4) -> str:
        """DuckDuckGo (ddgs) results as a compact block, or '' on any failure."""
        from ddgs import DDGS
        try:
            def _run():
                return DDGS().text(query, max_results=max_results) or []
            results = await asyncio.to_thread(_run)
        except Exception as e:
            logger.warning("[Agent] web_search DDG failed (q=%r): %s", query, e)
            return ""
        return self._fmt_search(results, "body", max_results)

    async def _ground_with_search(self, messages: list[dict],
                                  hint: str = "") -> list[dict]:
        """`messages` with any search results folded into the last turn, as a new
        list; a caller making two calls off one turn grounds once up front."""
        results = await self._decide_and_search(messages, hint=hint)
        if not results:
            return messages
        last = messages[-1]
        return messages[:-1] + [{
            **last,
            "content": _prepend_search_results(last.get("content", ""), results),
        }]

    async def _decide_and_search(self, messages: list[dict], hint: str = "") -> str:
        """Let the judge model decide on a web search and its query; the results,
        or '' (never raises). `hint` is the trigger message, since a rendered
        group prompt opens with its oldest history."""
        if not (self.base_url and self.api_key):
            return ""
        latest = (hint or "").strip()
        if not latest:
            for m in reversed(messages):
                if m.get("role") == "user":
                    latest = m.get("content") or ""
                    break
        if not self._might_need_search(latest):
            return ""
        try:
            tool = {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current events, memes, slang, people, products, prices, or any fact you are unsure about.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "concise search query"}},
                        "required": ["query"],
                    },
                },
            }
            payload = {
                # A yes/no-plus-query decision, so the cheap judge model.
                "model": self.llm_judge_model,
                "messages": [
                    {"role": "system", "content": (
                        "You are a search-decision gate. If the user's message "
                        "mentions a meme/slang/person/product/current event/"
                        "price/concrete fact you are unsure about, call "
                        "web_search to look it up; otherwise do nothing. Only "
                        "decide — do not write a reply.\n"
                        f"The user is chatting with a character named "
                        f"{self.persona_name or 'the character'}. Questions about "
                        "the character, the conversation, or the character's "
                        "own home, friends and story are answered in "
                        "character and are NEVER searched; neither are "
                        "greetings, feelings or everyday small talk.\n\n"
                        f"{_UNTRUSTED_INPUT_RULES}"
                    )},
                    # The trigger is a person's words, and this call picks
                    # what gets fetched into the reply's prompt.
                    {"role": "user",
                     "content": _fence_user_data(_truncate_framed(latest, 800))},
                ],
                "tools": [tool],
                "tool_choice": "auto",
                # Decision plus arguments can run to ~360 tokens.
                "max_tokens": 800,
                "temperature": 0.1,
            }
            url, key = self._endpoint_for(self.llm_judge_model)
            # Thinking off: with it on, this endpoint rarely emits tool_calls at
            # all. Spelled for the judge's endpoint, often another vendor's.
            self._thinking_off(payload, url)
            resp = await self._post_chat(url, key, payload, timeout=20)
            if resp.status_code != 200:
                logger.warning("[Agent] search-decide HTTP %d: %s", resp.status_code, resp.text[:200])
                return ""
            data = resp.json()
            tcs = data["choices"][0]["message"].get("tool_calls") or []
            if not tcs:
                return ""
            args = json.loads(tcs[0]["function"].get("arguments") or "{}")
            query = (args.get("query") or "").strip()
            if not query:
                return ""
            results = await self._web_search(query)
            if results:
                logger.info("[Agent] web_search q=%r -> %d chars", query, len(results))
            return results
        except Exception as e:
            logger.warning("[Agent] search-decide failed: %s", e)
            return ""
