"""The search decision reads the trigger with the chat lines before it, so a
question that refers back ("what do you think of it?") can name its subject;
whether the decision runs at all still depends on the trigger alone."""
from __future__ import annotations

import json
from pathlib import Path

from persona_agent.agent import Agent
from persona_agent.textproc import _USER_DATA_CLOSE, _USER_DATA_OPEN

from helpers import check, isolated_agent

TRIGGER = "@TestBot what do you think of it?"


class _Response:
    status_code = 200

    def __init__(self, data: dict):
        self._data = data
        self.text = json.dumps(data)

    def json(self) -> dict:
        return self._data


class _Client:
    """Records every POST; answers as a decision that searches for nothing."""

    def __init__(self, posts: list):
        self.posts = posts

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def post(self, _url, **kwargs):
        self.posts.append(kwargs["json"])
        return _Response({"choices": [{"message": {"content": ""},
                                       "finish_reason": "stop"}], "usage": {}})


def _agent(tmp: Path, lines: list[tuple[str, str]]) -> Agent:
    agent = isolated_agent(tmp, seeds=True)
    for i, (name, text) in enumerate(lines):
        agent._append_buffer("g", name, text, str(100 + i))
    return agent


async def _hint_from_think(agent: Agent, trigger: str) -> str:
    captured: dict = {}

    async def fake_call(system, messages, model, **kw):
        captured.update(kw)
        return '{"reasoning": "r", "intent": "chat", "reply": "ok", "mem": ""}'

    agent._call_llm = fake_call
    await agent._think("g", "called", trigger)
    return captured["search_hint"]


async def _decision_posts(agent: Agent, hint: str) -> list:
    posts: list = []
    agent._http = lambda **kw: _Client(posts)
    try:
        await agent._decide_and_search([], hint=hint)
    finally:
        await agent.aclose()
    return posts


async def test_the_decision_reads_the_line_the_trigger_refers_back_to(tmp: Path) -> None:
    agent = _agent(tmp, [("Ann", "the new Pixel 11 launched yesterday"),
                         ("Bob", "yeah saw the ads"),
                         ("Cat", TRIGGER)])
    hint = await _hint_from_think(agent, TRIGGER)
    check("the hint is still the trigger itself", hint == TRIGGER, repr(hint))
    posts = await _decision_posts(agent, hint)
    check("one decision call", len(posts) == 1, repr(posts))
    content = posts[0]["messages"][1]["content"]
    check("the decision input is one data frame",
          content.startswith(_USER_DATA_OPEN) and content.endswith(_USER_DATA_CLOSE),
          repr(content))
    body = content[1:-1]
    check("the earlier line reaches the decision, with its speaker",
          "Ann: the new Pixel 11 launched yesterday" in body, repr(body))
    check("the trigger comes last, with its speaker",
          body.endswith(f"Cat: {TRIGGER}"), repr(body))


async def test_only_the_three_lines_before_the_trigger_are_read(tmp: Path) -> None:
    agent = _agent(tmp, [("Ann", "line one"), ("Bob", "line two"), ("Cat", "line three"),
                         ("Dan", "line four"), ("Eve", "line five"), ("Fay", TRIGGER)])
    body = (await _decision_posts(agent, await _hint_from_think(agent, TRIGGER))
            )[0]["messages"][1]["content"][1:-1]
    check("three lines of context, then the trigger",
          body.split("\n") == ["Cat: line three", "Dan: line four",
                               "Eve: line five", f"Fay: {TRIGGER}"], repr(body))


async def test_context_never_opens_a_decision_the_trigger_would_not(tmp: Path) -> None:
    agent = _agent(tmp, [("Ann", "what is the price of gold today"), ("Bob", "lol nice")])
    hint = await _hint_from_think(agent, "lol nice")
    check("no decision call for a trigger the gate skips",
          await _decision_posts(agent, hint) == [], repr(hint))


async def test_a_trigger_without_a_buffer_is_decided_alone(tmp: Path) -> None:
    agent = isolated_agent(tmp, seeds=True)
    posts = await _decision_posts(agent, "what is the price of gold today")
    check("a plain hint is framed alone, as before",
          posts[0]["messages"][1]["content"]
          == f"{_USER_DATA_OPEN}what is the price of gold today{_USER_DATA_CLOSE}",
          repr(posts))
