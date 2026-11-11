"""Group turns: Activity rows for callers answered together when the turn
fails, and the backlog rule against a connector whose clock runs behind."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from persona_agent import decision_log, turns
from persona_agent.transport import SendResult

from test_turns import GROUP, _event, _group, make_agent, on_a_virtual_clock


async def _fail(*args, **kwargs):
    raise RuntimeError("model down")


async def _blocked(*args, **kwargs):
    return "I'm ChatGPT, made by OpenAI", "chat", ""


async def _answer(*args, **kwargs):
    return "sure", "chat", ""


async def _undelivered(group_id, text, at_user_id=""):
    return SendResult(success=False)


async def _delivered(group_id, text, at_user_id=""):
    return SendResult(success=True)


@pytest.mark.parametrize("think,send,reason", [
    (_fail, _delivered, "model failed"),
    (_blocked, _delivered, "blocked"),
    (_answer, _undelivered, "delivery failed"),
])
def test_every_caller_of_a_failed_turn_has_a_row(tmp: Path, think, send, reason) -> None:
    async def main():
        decision_log.LOG.clear()
        agent = make_agent(tmp, message_debounce_sec=2.0)
        agent._think, agent._send_group = think, send
        agent._excuse_begin = lambda group_id: False
        first = asyncio.create_task(agent.handle_onebot(
            _group("is the shop open on sunday", "s1", at_bot=True, user="8", name="Bo")))
        await asyncio.sleep(0.5)
        second = asyncio.create_task(agent.handle_onebot(
            _group("and what time does it close", "s2", at_bot=True, user="9", name="Cy")))
        await asyncio.gather(first, second)

    on_a_virtual_clock(main())
    rows = [r for r in decision_log.LOG.recent(GROUP) if r["reason"] == reason]
    assert sorted(r["sender"] for r in rows) == ["Bo", "Cy"], rows


def test_the_same_failure_for_one_person_still_folds(tmp: Path) -> None:
    log = decision_log.DecisionLog()
    for _ in range(3):
        log.record("c", "called", False, "model failed", "hi", sender="Bo")
    log.record("c", "called", False, "model failed", "hi", sender="Cy")
    rows = log.recent("c")
    assert sorted((r["sender"], r["count"]) for r in rows) == [("Bo", 3), ("Cy", 1)], rows
    for _ in range(3):
        log.record("d", "", False, "below the trigger count", "x", sender=f"p{_}")
    assert len(log.recent("d")) == 1


def _old(text: str, mid: int, age: float, **extra) -> dict:
    return _event(text, mid, sender="5", name="Eve", at_bot=True,
                  sent_at=int(time.time() - age), **extra)


async def test_a_backlog_right_after_a_start_is_context_only(tmp: Path) -> None:
    agent = make_agent(tmp, message_debounce_sec=0)
    calls: list = []

    async def think(group_id, mode, text="", caller_override=None):
        calls.append(text)
        return "sure", "chat", ""

    agent._think = think
    await agent.handle_event(_old("an hour ago", 1, 3600))
    assert calls == [], calls
    assert any("an hour ago" in m["text"] for m in agent.buffers["telegram:c1"])


async def test_a_connector_clock_behind_is_not_a_backlog_forever(tmp: Path, monkeypatch) -> None:
    agent = make_agent(tmp, message_debounce_sec=0)
    calls: list = []

    async def think(group_id, mode, text="", caller_override=None):
        calls.append(text)
        return "sure", "chat", ""

    agent._think = think
    await agent.handle_event(_old("first", 1, 1200))
    # Later than the start, the same 20-minute lag is the clock, not a backlog.
    real, later = time.time, getattr(turns, "STARTUP_BACKLOG_S", 120.0) + 1
    monkeypatch.setattr(turns.time, "time", lambda: real() + later)
    await agent.handle_event(_old("second", 2, 1200 + later))
    assert len(calls) == 1 and "second" in calls[0], calls
