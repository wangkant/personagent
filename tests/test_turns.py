"""A group turn whose model is slow: what becomes of the messages that arrive
meanwhile, and how long the turn may take.

Run from the repo root:

    python -m pytest tests/test_turns.py
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from persona_agent import turns
from persona_agent.agent import Agent
from persona_agent.prompts import MODEL_FAILURE_EXCUSES
from persona_agent.transport import SendResult

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent

QQ_BOT_ID = "10001"
GROUP = "555"


def make_agent(tmp: Path, **overrides) -> Agent:
    a = isolated_agent(tmp, **{
        "qq_bot_id": QQ_BOT_ID, "persona_name": "Luna", "admin_ids": ("42",),
        "qq_onebot_url": CLOSED_ONEBOT_URL,
        # No follow-up turns: each test counts the model calls it caused.
        "chat_followup_window_s": 0, **overrides})
    a._typing_delay = lambda chunk: 0.0
    return a


def _group(text: str, mid: str, *, group: str = GROUP, user: str = "7",
           name: str = "Ann", at_bot: bool = False) -> dict:
    segments = [{"type": "at", "data": {"qq": QQ_BOT_ID}}] if at_bot else []
    return {"post_type": "message", "message_type": "group", "group_id": group,
            "user_id": user, "message_id": mid, "sender": {"nickname": name},
            "message": segments + [{"type": "text", "data": {"text": text}}],
            "raw_message": text}


def _event(text: str, mid: int, *, sender: str, name: str,
           at_bot: bool = False) -> dict:
    segments = [{"type": "mention", "user_id": "999000", "name": "Luna"}] if at_bot else []
    return {"platform": "telegram", "conversation_type": "group",
            "conversation_id": "c1", "sender_id": sender, "sender_name": name,
            "bot_id": "999000", "message_id": mid, "addressed": at_bot,
            "segments": segments + [{"type": "text", "text": text}], "text": text}


async def _settle() -> None:
    """Run everything that can run without the model answering."""
    for _ in range(50):
        await asyncio.sleep(0)


def _collect_sends(agent: Agent) -> list:
    sent: list = []

    async def fake_send(group_id, text, at_user_id=""):
        sent.append((group_id, text))
        return SendResult(success=True)

    agent._send_group = fake_send
    return sent


def _hang_the_first_call(agent: Agent):
    """`_think` whose first call waits for `release`; later ones answer at once."""
    started, release, calls = asyncio.Event(), asyncio.Event(), []

    async def think(group_id, mode, text="", caller_override=None):
        calls.append((mode, text))
        if len(calls) == 1:
            started.set()
            await release.wait()
        return f"answer {len(calls)}", "chat", ""

    agent._think = think
    return started, release, calls


def _lines(agent: Agent, group: str = GROUP) -> list:
    return [(m["name"], m["text"]) for m in agent.buffers[group]]


# ---- messages that arrive while the model is being asked ---------------------

async def test_messages_during_a_model_call_are_held_and_their_handlers_return(
        tmp: Path) -> None:
    """Every handler holds a webhook admission slot until it returns. Waiting
    on the group's lock for the model call, twenty messages held twenty slots,
    and one busy group with a stuck model answered 429 for every chat."""
    agent = make_agent(tmp)
    _collect_sends(agent)
    started, release, calls = _hang_the_first_call(agent)
    first = asyncio.create_task(
        agent.handle_onebot(_group("question one", "q1", at_bot=True)))
    await started.wait()
    later = [asyncio.create_task(agent.handle_onebot(
        _group(f"chatter {i}", f"c{i}", user=str(100 + i), name=f"M{i}")))
        for i in range(20)]
    await _settle()

    check("the model is still being asked", not first.done())
    check("all but the newest handler have returned, without the model",
          [t.done() for t in later] == [True] * 19 + [False],
          repr([t.done() for t in later]))
    check("...unanswered", all(t.result() is False for t in later[:19]))
    gate = agent._pending_outbound.get(GROUP)
    check("all twenty are held behind the turn",
          gate is not None and len(gate.held) == 20, repr(gate))
    check("none is in the buffer the reply is being written from",
          _lines(agent) == [("Ann", "@Luna question one")], repr(_lines(agent)))

    release.set()
    await asyncio.gather(first, *later)
    check("the reply sits right after what it saw, the held messages after it "
          "in arrival order",
          _lines(agent) == [("Ann", "@Luna question one"), ("Luna", "answer 1")]
          + [(f"M{i}", f"chatter {i}") for i in range(20)], repr(_lines(agent)))
    check("the newest handler went on to the usual decision, which was no turn",
          later[-1].result() is False and len(calls) == 1, repr(calls))
    check("nothing stays held", GROUP not in agent._pending_outbound)


async def test_another_group_and_a_dm_are_answered_meanwhile(tmp: Path) -> None:
    agent = make_agent(tmp)
    sent = _collect_sends(agent)
    started, release = asyncio.Event(), asyncio.Event()
    dms: list = []

    async def think(group_id, mode, text="", caller_override=None):
        if group_id == GROUP:
            started.set()
            await release.wait()
        return f"answer for {group_id}", "chat", ""

    async def chat_dm(history, is_admin=False, proactive=False, pkey=""):
        return "dm answer", ""

    async def send_dm(user_id, text):
        dms.append((user_id, text))
        return SendResult(success=True)

    agent._think, agent._chat_dm, agent._send_dm = think, chat_dm, send_dm
    stuck = asyncio.create_task(
        agent.handle_onebot(_group("question", "s1", at_bot=True)))
    await started.wait()
    held = [asyncio.create_task(agent.handle_onebot(
        _group(f"chatter {i}", f"h{i}", user=str(100 + i), name=f"M{i}")))
        for i in range(20)]
    await _settle()

    other = await asyncio.wait_for(agent.handle_onebot(
        _group("hello there", "o1", group="556", at_bot=True)), 5)
    check("another group is answered", other is True
          and ("556", "answer for 556") in sent, repr(sent))
    dm = await asyncio.wait_for(agent.handle_onebot({
        "post_type": "message", "message_type": "private", "user_id": "42",
        "message_id": "d1", "sender": {"nickname": "K"},
        "message": [{"type": "text", "data": {"text": "hi"}}],
        "raw_message": "hi"}), 5)
    check("a DM is answered", dm is True and dms == [("42", "dm answer")], repr(dms))
    check("the stuck group has sent nothing", not any(g == GROUP for g, _ in sent))
    release.set()
    await asyncio.gather(stuck, *held)


async def test_the_newest_held_message_takes_the_next_turn_in_its_own_request(
        tmp: Path) -> None:
    """Behind a connector a reply travels in the HTTP response of the request
    that caused it, so the one message that can still become a turn keeps its
    handler; the ones before it could only have been debounced away."""
    agent = make_agent(tmp)
    started, release, calls = _hang_the_first_call(agent)
    first = asyncio.create_task(agent.handle_event(
        _event(" question one", 1, sender="1", name="Ann", at_bot=True)))
    await started.wait()
    called = asyncio.create_task(agent.handle_event(
        _event(" and one more thing", 2, sender="2", name="Bob", at_bot=True)))
    await _settle()
    check("a held call waits while it is the newest", not called.done())
    newest = asyncio.create_task(agent.handle_event(
        _event("lol", 3, sender="3", name="Cy")))
    await _settle()
    check("the request before the newest returns at once, owned and empty",
          called.done() and called.result() == {
              "handled": False, "owned": True, "replies": []},
          repr(called.result() if called.done() else None))
    check("the newest keeps waiting", not newest.done() and not first.done())

    release.set()
    answered, _, last = await asyncio.gather(first, called, newest)
    check("the first request carries its own reply",
          [r.get("text") for r in answered["replies"]] == ["answer 1"],
          repr(answered))
    check("the held call is answered in the newest request's response",
          last["handled"] is True
          and [r.get("text") for r in last["replies"]] == ["answer 2"],
          repr(last))
    check("...as the call it was", [mode for mode, _ in calls] == ["called", "called"],
          repr(calls))
    check("the buffer keeps arrival order around both replies",
          _lines(agent, "telegram:c1") == [
              ("Ann", "@Luna question one"), ("Luna", "answer 1"),
              ("Bob", "@Luna and one more thing"), ("Cy", "lol"),
              ("Luna", "answer 2")], repr(_lines(agent, "telegram:c1")))


async def test_a_held_memory_command_is_answered_after_the_turn(tmp: Path) -> None:
    agent = make_agent(tmp)
    sent = _collect_sends(agent)
    started, release, calls = _hang_the_first_call(agent)
    first = asyncio.create_task(
        agent.handle_onebot(_group("question one", "q1", at_bot=True)))
    await started.wait()
    command = asyncio.create_task(agent.handle_onebot(_group(
        " remember I like cats", "m1", user="42", name="Kay", at_bot=True)))
    chatter = asyncio.create_task(agent.handle_onebot(
        _group("lol", "c1", user="8", name="Bob")))
    await _settle()
    check("a command is not dropped for a newer message", not command.done())
    check("nothing is remembered before its turn in line",
          agent.memories.get(GROUP, []) == [], repr(agent.memories.get(GROUP)))

    release.set()
    handled = await asyncio.gather(first, command, chatter)
    check("the command is handled", handled[1] is True, repr(handled))
    check("and remembered", [m["text"] for m in agent.memories[GROUP]]
          == ["I like cats"], repr(agent.memories.get(GROUP)))
    lines = _lines(agent)
    check("the reply still precedes everything it did not see",
          lines[:3] == [("Ann", "@Luna question one"), ("Luna", "answer 1"),
                        ("Kay", "@Luna remember I like cats")], repr(lines))
    check("both went out: the reply, then the command's answer",
          len(sent) == 2 and sent[0] == (GROUP, "answer 1"), repr(sent))
    check("the command was no model call", len(calls) == 1, repr(calls))


async def test_a_flood_during_one_turn_is_held_up_to_a_bound(
        tmp: Path, monkeypatch) -> None:
    monkeypatch.setattr(turns, "_MAX_HELD", 3)
    agent = make_agent(tmp)
    _collect_sends(agent)
    started, release, _calls = _hang_the_first_call(agent)
    first = asyncio.create_task(
        agent.handle_onebot(_group("question one", "q1", at_bot=True)))
    await started.wait()
    later = [asyncio.create_task(agent.handle_onebot(
        _group(f"chatter {i}", f"c{i}", user=str(100 + i), name=f"M{i}")))
        for i in range(5)]
    await _settle()
    check("no more than the bound is held",
          len(agent._pending_outbound[GROUP].held) == 3)
    release.set()
    await asyncio.gather(first, *later)
    check("the oldest of the flood are the ones let go",
          _lines(agent)[2:] == [(f"M{i}", f"chatter {i}") for i in (2, 3, 4)],
          repr(_lines(agent)))


async def test_a_turn_that_fails_or_is_cancelled_lets_its_held_messages_in(
        tmp: Path) -> None:
    for ending in ("raises", "cancelled"):
        agent = make_agent(tmp / ending)
        _collect_sends(agent)
        started, release = asyncio.Event(), asyncio.Event()

        async def think(group_id, mode, text="", caller_override=None):
            started.set()
            await release.wait()
            raise RuntimeError("boom")

        agent._think = think
        first = asyncio.create_task(agent.handle_onebot(
            _group("question one", "f1", at_bot=True)))
        await started.wait()
        held = asyncio.create_task(agent.handle_onebot(
            _group("later", "l1", user="8", name="Bob")))
        await _settle()
        check(f"{ending}: held while the model is asked", not held.done())
        if ending == "raises":
            release.set()
            await first
        else:
            first.cancel()
            await asyncio.gather(first, return_exceptions=True)
        await asyncio.wait_for(held, 5)
        check(f"{ending}: the held message is buffered once the turn is over",
              _lines(agent)[:2] == [("Ann", "@Luna question one"), ("Bob", "later")],
              repr(_lines(agent)))
        check(f"{ending}: nothing stays held", GROUP not in agent._pending_outbound)
        await _settle()


# ---- one time budget for the whole turn --------------------------------------

async def test_a_turn_over_its_budget_ends_with_the_failure_line_once(
        tmp: Path) -> None:
    """The model call used to be bounded per attempt per model (LLM_TIMEOUT_S
    times the retries, times two models); a turn has one budget now."""
    agent = make_agent(tmp)
    agent.llm_timeout_s = 0.02
    sent = _collect_sends(agent)
    started = asyncio.Event()
    cancelled: list = []

    async def never_answers(group_id, mode, text="", caller_override=None):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(text)

    agent._think = never_answers
    first = asyncio.create_task(
        agent.handle_onebot(_group("you there?", "b1", at_bot=True)))
    await started.wait()
    held = asyncio.create_task(agent.handle_onebot(
        _group("lol", "b2", user="8", name="Bob")))
    handled = await asyncio.wait_for(first, 5)
    await asyncio.wait_for(held, 5)
    await _settle()
    check("the turn ends unanswered when its budget runs out", handled is False)
    check("the model call is abandoned, not left running", len(cancelled) == 1,
          repr(cancelled))
    check("the caller is told once, with the usual line",
          len(sent) == 1 and sent[0][1] in MODEL_FAILURE_EXCUSES["en"], repr(sent))
    check("what arrived meanwhile is buffered behind it",
          ("Bob", "lol") in _lines(agent), repr(_lines(agent)))

    handled = await asyncio.wait_for(
        agent.handle_onebot(_group("hello??", "b3", at_bot=True)), 5)
    await _settle()
    check("a second turn over budget says nothing more (cooldown)",
          handled is False and len(sent) == 1, repr(sent))
    check("the budget is one and a half model timeouts",
          turns._TURN_BUDGET_CALLS == 1.5)
