"""The screenshot tool's seeding: the story it tells the dashboard.

Runs the real agent against the tool's stand-in model over real HTTP, with no
browser. Taking the screenshots themselves (headless Edge) is manual:

    python tools/dashboard_snapshot.py --out DIR
"""
from __future__ import annotations

import asyncio
import json
import urllib.request
from pathlib import Path

import pytest

from persona_agent import candidates, decision_log, demo
from persona_agent.agent import Agent
from persona_agent.textproc import TextProcessing
from tools import dashboard_snapshot as snap


@pytest.fixture(autouse=True)
def daytime(monkeypatch):
    monkeypatch.setattr(TextProcessing, "_is_sleep_hour", staticmethod(lambda: False))


def build_agent(lang: str, root: Path, base_url: str) -> Agent:
    """demo.build_agent, but its model is the stand-in's HTTP endpoint."""
    agent, _ = demo.build_agent(lang, root, offline=True)
    agent.base_url, agent.model, agent.api_key = base_url, "deepseek-flash", "sk-snapshot"
    agent.api_max_retries = 0
    # A reaction is judged in the background while the reply is written.
    agent.message_debounce_sec = 0.3
    del agent._call_llm  # back to the class's real HTTP caller
    return agent


@pytest.mark.parametrize("lang", ["en", "zh"])
async def test_the_seeded_story_leaves_one_promoted_and_one_waiting(
        tmp: Path, lang: str) -> None:
    decision_log.LOG.clear()
    with snap.StandIn() as standin, demo.throwaway_home(str(tmp)) as root:
        agent = build_agent(lang, root, standin.base_url)

        async def post(event: dict) -> dict:
            reply = await agent.handle_event(event)
            if agent._bg_tasks:
                await asyncio.gather(*list(agent._bg_tasks), return_exceptions=True)
            return reply

        replies = await snap.seed(post, standin, lang)
        await agent.aclose()
        spoke = [r for r in replies if r.get("replies")]
        assert len(spoke) >= 9
        pairs = [c for c in agent.candidate_ledger.all()
                 if c["type"] == candidates.TYPE_PAIR]
        states = sorted(c["state"] for c in pairs if c["state"] in (
            candidates.STATE_PROMOTED, candidates.STATE_PROPOSED))
        assert states == [candidates.STATE_PROMOTED, candidates.STATE_PROPOSED]
        promoted = next(c for c in pairs if c["state"] == candidates.STATE_PROMOTED)
        assert promoted["better"] == demo._RETRY[lang]
        assert agent.memories, "the memory note was saved"
    decision_log.LOG.clear()


def test_the_stand_in_answers_each_kind_of_call_from_the_loaded_beat() -> None:
    beat = snap.Beat("sam", "hi", gate=True, reply="hello")
    with snap.StandIn() as standin:
        standin.load(beat)

        def ask(payload: dict) -> str:
            req = urllib.request.Request(
                standin.base_url + "/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"content-type": "application/json"})
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]

        gate = ask({"model": "m", "temperature": 0.3, "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": "g"},
                                 {"role": "user", "content": "x"}]})
        assert json.loads(gate)["reply"] != "PASS"
        reply = ask({"model": "m", "response_format": {"type": "json_object"},
                     "messages": [{"role": "system", "content": "s"},
                                  {"role": "user", "content": "x"}]})
        assert json.loads(reply)["reply"] == "hello"
        assert standin.requests == ["gate", "reply"]


def test_every_shot_name_has_a_spec() -> None:
    assert set(snap.SHOTS) == {"en-light", "en-dark", "zh-light", "zh-dark",
                               "en-mobile", "zh-mobile", "en-empty"}
