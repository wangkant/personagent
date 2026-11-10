"""A group turn whose model is slow: what becomes of the messages that arrive
meanwhile, and how long the turn may take. The one-on-one counterpart is
tests/test_dm_turns.py, which borrows the storm at the end of this file.

Run from the repo root:

    python -m pytest tests/test_turns.py
"""
from __future__ import annotations

import asyncio
import random
import re
import time
from collections import defaultdict
from pathlib import Path

from persona_agent import memory, reactions, turns
from persona_agent.agent import Agent
from persona_agent.prompts import MODEL_FAILURE_EXCUSES
from persona_agent.textproc import TextProcessing
from persona_agent.transport import SendResult

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent

QQ_BOT_ID = "10001"
GROUP = "555"
#: What a "remember ..." command is answered with.
NOTED = memory._COMMAND_REPLIES["en"]["noted"]
#: The fields that give a connector conversation an outbox address.
OUTBOX = {"connector_id": "fw1", "reply_handle": "tg-bot:GroupMessage:c1",
          "capabilities": ["outbox"]}


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
           at_bot: bool = False, **extra) -> dict:
    segments = [{"type": "mention", "user_id": "999000", "name": "Luna"}] if at_bot else []
    return {"platform": "telegram", "conversation_type": "group",
            "conversation_id": "c1", "sender_id": sender, "sender_name": name,
            "bot_id": "999000", "message_id": mid, "addressed": at_bot,
            "segments": segments + [{"type": "text", "text": text}], "text": text,
            **extra}


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
    check("the command's handler has returned, and its slot with it",
          command.done() and command.result() is False, repr(command))
    check("nothing is remembered before its turn in line",
          agent.memories.get(GROUP, []) == [], repr(agent.memories.get(GROUP)))
    check("and nothing is answered yet", sent == [], repr(sent))

    release.set()
    await asyncio.gather(first, chatter)
    await _settle()
    check("the command ran once the turn was over",
          [m["text"] for m in agent.memories[GROUP]] == ["I like cats"],
          repr(agent.memories.get(GROUP)))
    lines = _lines(agent)
    check("the reply still precedes everything it did not see",
          lines[:3] == [("Ann", "@Luna question one"), ("Luna", "answer 1"),
                        ("Kay", "@Luna remember I like cats")], repr(lines))
    check("both went out: the reply, then the command's answer",
          len(sent) == 2 and sent[0] == (GROUP, "answer 1")
          and sent[1][0] == GROUP and sent[1][1] in NOTED, repr(sent))
    check("the answer is on record", lines[-1] == ("Luna", sent[1][1]), repr(lines))
    check("the command was no model call", len(calls) == 1, repr(calls))


async def test_held_commands_hold_no_slot_and_none_is_lost(tmp: Path) -> None:
    """A held command used to keep its handler until the turn ended, so one
    person could fill every admission slot with commands during one slow
    call. Over NapCat a reply needs no open request: the handler leaves."""
    agent = make_agent(tmp)
    agent.memory_max_per_conversation = 200
    sent = _collect_sends(agent)
    started, release, calls = _hang_the_first_call(agent)
    first = asyncio.create_task(
        agent.handle_onebot(_group("question one", "q1", at_bot=True)))
    await started.wait()
    commands = [asyncio.create_task(agent.handle_onebot(_group(
        f" remember k{i} likes tea", f"m{i}", user="42", name="Kay", at_bot=True)))
        for i in range(80)]
    await _settle()
    check("every command's handler has returned: more than there are slots",
          all(t.done() for t in commands),
          repr(sum(not t.done() for t in commands)))
    check("the model is still being asked, and nothing has run",
          not first.done() and agent.memories.get(GROUP, []) == [])

    release.set()
    await first
    for _ in range(20):
        await _settle()
    check("every command ran, once, in the order it came",
          [m["text"] for m in agent.memories[GROUP]]
          == [f"k{i} likes tea" for i in range(80)],
          repr([m["text"] for m in agent.memories[GROUP]][:5]))
    check("the reply went out first, then one answer per command",
          sent[0] == (GROUP, "answer 1") and len(sent) == 81
          and all(text in NOTED for _, text in sent[1:]), repr(sent[:3]))
    check("no command cost a model call", len(calls) == 1, repr(calls))
    check("nothing stays held", GROUP not in agent._pending_outbound)


async def test_behind_a_connector_a_held_commands_answer_rides_in_a_response(
        tmp: Path) -> None:
    """A connector with no outbox can only be answered in a response. Two
    held commands keep their request for that; a later one returns at once
    and its answer rides in the last waiting request's response."""
    agent = make_agent(tmp)
    started, release, calls = _hang_the_first_call(agent)
    first = asyncio.create_task(agent.handle_event(
        _event(" question one", 1, sender="1", name="Ann", at_bot=True)))
    await started.wait()
    commands = [asyncio.create_task(agent.handle_event(_event(
        f" remember k{i} likes tea", 10 + i, sender=str(20 + i), name=f"M{i}",
        at_bot=True))) for i in range(6)]
    await _settle()
    check("only the first two keep their request",
          [t.done() for t in commands] == [False, False] + [True] * 4,
          repr([t.done() for t in commands]))
    check("the others return at once, owned and empty",
          all(t.result() == {"handled": False, "owned": True, "replies": []}
              for t in commands[2:]))
    check("no command has run yet", agent.memories.get("telegram:c1", []) == [])

    release.set()
    answers = await asyncio.gather(first, *commands)
    check("every command ran, in the order it came",
          [m["text"] for m in agent.memories["telegram:c1"]]
          == [f"k{i} likes tea" for i in range(6)],
          repr(agent.memories.get("telegram:c1")))
    one, two = answers[1]["replies"], answers[2]["replies"]
    check("the first waiting request carries its own answer",
          answers[1]["handled"] is True and len(one) == 1
          and one[0]["text"] in NOTED
          and one[0]["mention_user_id"] == "telegram:20", repr(answers[1]))
    check("the second carries its own and the four that could not wait, in "
          "order, each for its caller",
          answers[2]["handled"] is True
          and [r["mention_user_id"] for r in two]
          == [f"telegram:{20 + i}" for i in range(1, 6)]
          and all(r["text"] in NOTED for r in two), repr(answers[2]))
    check("nothing stays held", "telegram:c1" not in agent._pending_outbound)


async def test_a_flood_of_commands_never_runs_one_it_cannot_answer(
        tmp: Path, monkeypatch) -> None:
    """Past the bound a waiting request used to be the one let go, and the
    commands whose answers it carried then ran with nowhere to answer."""
    monkeypatch.setattr(turns, "_MAX_HELD", 6)
    agent = make_agent(tmp)
    started, release, _calls = _hang_the_first_call(agent)
    first = asyncio.create_task(agent.handle_event(
        _event(" question one", 1, sender="1", name="Ann", at_bot=True)))
    await started.wait()
    commands = [asyncio.create_task(agent.handle_event(_event(
        f" remember k{i} likes tea", 10 + i, sender=str(20 + i), name=f"M{i}",
        at_bot=True))) for i in range(8)]
    await _settle()
    release.set()
    answers = (await asyncio.gather(first, *commands))[1:]
    ran = [m["text"] for m in agent.memories.get("telegram:c1", [])]
    answered = [r["mention_user_id"] for a in answers for r in a["replies"]
                if r["text"] in NOTED]
    check("two were let go, and neither ran", len(ran) == 6, repr(ran))
    check("every command that ran is answered, to its own caller",
          sorted(answered) == sorted(
              f"telegram:{20 + int(text[1:].split()[0])}" for text in ran),
          repr((ran, answered)))
    check("nothing stays held", "telegram:c1" not in agent._pending_outbound)


async def test_a_waiting_commands_own_failure_does_not_cost_the_ones_it_carries(
        tmp: Path) -> None:
    agent = make_agent(tmp)
    started, release, _calls = _hang_the_first_call(agent)
    first = asyncio.create_task(agent.handle_event(
        _event(" question one", 1, sender="1", name="Ann", at_bot=True)))
    await started.wait()
    commands = [asyncio.create_task(agent.handle_event(_event(
        f" remember k{i} likes tea", 10 + i, sender=str(20 + i), name=f"M{i}",
        at_bot=True))) for i in range(4)]
    await _settle()

    async def hook(conversation, text):
        if text in NOTED:
            raise RuntimeError("the hook is broken")

    agent.on_reply = hook
    release.set()
    answers = await asyncio.gather(first, *commands, return_exceptions=True)
    check("a request that carries nothing fails as it always did",
          isinstance(answers[1], RuntimeError), repr(answers[1]))
    check("the one that carries others still gives its response, with all three",
          isinstance(answers[2], dict)
          and [r["mention_user_id"] for r in answers[2]["replies"]]
          == [f"telegram:{20 + i}" for i in (1, 2, 3)], repr(answers[2]))


async def test_a_held_command_is_answered_through_the_outbox_when_there_is_one(
        tmp: Path) -> None:
    agent = make_agent(tmp)
    agent.outbox.poll_s = 0.02
    await agent.outbox.pull("fw1", wait_s=0)
    # An admitted event leaves the room's address behind.
    await agent.handle_event(_event("hello all", 1, sender="5", name="Eve", **OUTBOX))
    started, release, calls = _hang_the_first_call(agent)
    first = asyncio.create_task(agent.handle_event(
        _event(" question one", 2, sender="1", name="Ann", at_bot=True, **OUTBOX)))
    await started.wait()
    command = asyncio.create_task(agent.handle_event(_event(
        " remember I like cats", 3, sender="2", name="Bob", at_bot=True, **OUTBOX)))
    await _settle()
    check("the command's request returns at once, owned and empty",
          command.done() and command.result() == {
              "handled": False, "owned": True, "replies": []},
          repr(command.result() if command.done() else None))

    release.set()
    await first
    pulled = await agent.outbox.pull("fw1", wait_s=3)
    check("its answer is queued for the room as a follow-up",
          len(pulled["deliveries"]) == 1
          and pulled["deliveries"][0]["reason"] == "follow_up"
          and pulled["deliveries"][0]["conversation_key"] == "telegram:c1"
          and pulled["deliveries"][0]["items"][0]["text"] in NOTED, repr(pulled))
    delivery = pulled["deliveries"][0]
    await agent.outbox.pull("fw1", wait_s=0, acks=[{
        "delivery_id": delivery["delivery_id"], "status": "sent", "sent_items": 1}])
    await _settle()
    check("and the command ran",
          [m["text"] for m in agent.memories["telegram:c1"]] == ["I like cats"],
          repr(agent.memories.get("telegram:c1")))
    check("the acked answer is on record",
          _lines(agent, "telegram:c1")[-1] == ("Luna", delivery["items"][0]["text"]),
          repr(_lines(agent, "telegram:c1")))


async def test_a_cancelled_waiting_handler_leaves_its_call_to_the_next_message(
        tmp: Path) -> None:
    """Pins what happens when the one handler still waiting behind a turn is
    cancelled, which only a shutdown does: nothing it displaced is lost, no
    turn runs on its behalf, and the call it displaced is still pending for
    the next message in the room."""
    agent = make_agent(tmp)
    _collect_sends(agent)
    started, release, calls = _hang_the_first_call(agent)
    first = asyncio.create_task(
        agent.handle_onebot(_group("question one", "q1", at_bot=True)))
    await started.wait()
    called = asyncio.create_task(agent.handle_onebot(_group(
        "and one more thing", "q2", user="8", name="Bob", at_bot=True)))
    await _settle()
    newest = asyncio.create_task(agent.handle_onebot(
        _group("lol", "c1", user="9", name="Cy")))
    await _settle()
    check("the call's handler left for the newer message",
          called.done() and called.result() is False and not newest.done())
    newest.cancel()
    await asyncio.gather(newest, return_exceptions=True)

    release.set()
    await first
    await _settle()
    check("both held messages are on record behind the reply",
          _lines(agent) == [("Ann", "@Luna question one"), ("Luna", "answer 1"),
                            ("Bob", "@Luna and one more thing"), ("Cy", "lol")],
          repr(_lines(agent)))
    check("no turn runs for the displaced call on its own", len(calls) == 1,
          repr(calls))
    check("nothing stays held", GROUP not in agent._pending_outbound)

    handled = await agent.handle_onebot(_group("so?", "c2", user="9", name="Cy"))
    check("the next message in the room picks the call up",
          handled is True and [mode for mode, _ in calls] == ["called", "called"],
          repr(calls))


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


# ---- the agent speaking first is a turn like any other ------------------------

async def test_a_proactive_group_turn_has_the_budget_and_holds_what_arrives(
        tmp: Path) -> None:
    """The proactive loop asked the model with no budget and no place in the
    room: a stuck model stalled the loop for every retry of every model, and
    the opener was put on record after messages it had never seen."""
    agent = make_agent(tmp)
    agent.proactive_prob = 1.0
    sent = _collect_sends(agent)
    agent._append_buffer(GROUP, "Ann", "anyone up for dinner", "7")

    def go_quiet() -> None:
        agent.last_activity_at[GROUP] = (
            time.time() - agent.proactive_min_silence_s - 100)

    cancelled: list = []

    async def never_answers(group_id, mode, text="", caller_override=None):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(mode)

    agent._think = never_answers
    agent.llm_timeout_s = 0.02
    go_quiet()
    acted = await asyncio.wait_for(agent._maybe_proactive_groups(), 5)
    check("an opener the model never writes is given up at the turn budget",
          acted is False and cancelled == ["proactive"], repr((acted, cancelled)))
    check("and leaves nothing held", GROUP not in agent._pending_outbound)

    agent.llm_timeout_s = 120.0
    started, release, _calls = _hang_the_first_call(agent)
    go_quiet()
    opener = asyncio.create_task(agent._maybe_proactive_groups())
    await started.wait()
    later = [asyncio.create_task(agent.handle_onebot(
        _group(f"chatter {i}", f"p{i}", user=str(100 + i), name=f"M{i}")))
        for i in range(5)]
    await _settle()
    check("what arrives while the opener is written waits behind it, and "
          "only the newest handler stays",
          [t.done() for t in later] == [True] * 4 + [False],
          repr([t.done() for t in later]))
    release.set()
    check("the opener goes out", await opener is True
          and sent == [(GROUP, "answer 1")], repr(sent))
    await asyncio.gather(*later)
    check("on record before the messages it did not see",
          _lines(agent) == [("Ann", "anyone up for dinner"), ("Luna", "answer 1")]
          + [(f"M{i}", f"chatter {i}") for i in range(5)], repr(_lines(agent)))
    check("nothing stays held", GROUP not in agent._pending_outbound)


# ---- a storm: seeded interleavings of everything at once ----------------------

class _VirtualClockLoop(asyncio.SelectorEventLoop):
    """An event loop whose clock jumps to the next timer whenever nothing
    else can run: sleeps and timeouts take no time and fire in one fixed
    order, so a seed replays the same interleaving on every machine."""

    def __init__(self) -> None:
        super().__init__()
        self._virtual_now = 0.0

    def time(self) -> float:
        return self._virtual_now

    def _run_once(self) -> None:
        if not self._ready:
            # Not the head of the heap: a cancelled timer there is skipped by
            # the loop, which would then really sleep until the next live one.
            live = [timer.when() for timer in self._scheduled if not timer.cancelled()]
            if live:
                self._virtual_now = max(self._virtual_now, min(live))
        super()._run_once()


def on_a_virtual_clock(main):
    loop = _VirtualClockLoop()
    try:
        return loop.run_until_complete(main)
    finally:
        loop.close()


def _dm(text: str, mid: str, user: str = "42") -> dict:
    return {"post_type": "message", "message_type": "private", "user_id": user,
            "message_id": mid, "sender": {"nickname": "Kay"},
            "message": [{"type": "text", "data": {"text": text}}],
            "raw_message": text}


def _dm_event(text: str, mid, *, sender: str = "9", **extra) -> dict:
    return {"platform": "telegram", "conversation_type": "dm",
            "conversation_id": sender, "sender_id": sender, "sender_name": "Nia",
            "bot_id": "999000", "message_id": mid, "addressed": False,
            "segments": [{"type": "text", "text": text}], "text": text, **extra}


#: w<n>: a chat message; k<n>: what a memory command saves; r<n>: a reply.
_TOKEN = re.compile(r"\b[wkr]\d+\b")


def _tokens(texts) -> list:
    return _TOKEN.findall(" \n ".join(texts))


SEEDS = (3, 7, 11, 19, 23, 42, 77, 101, 256, 1009, 4242, 90210)

#: How often each kind of arrival comes: chatter, a call and a memory command
#: in a group; a message, a command and a connector's cue in a DM; a tick of
#: the proactive loop for groups and for DMs.
MIXED = {"g_chat": 30, "g_call": 14, "g_cmd": 8, "d_chat": 26, "d_cmd": 8,
         "d_cue": 3, "p_group": 4, "p_dm": 4}


class Storm:
    """One seeded run of mixed traffic against a real Agent. The model, the
    sends and the reading of a DM are stubs that take random virtual time;
    the model also passes, fails and outlives the turn budget at random.
    `verify` asserts what must hold however the run interleaved."""

    GROUPS = (("onebot", "601"), ("onebot", "602"), ("event", "telegram:c1"))
    DMS = (("onebot", "42"), ("onebot", "7"), ("event", "telegram:9"))

    def __init__(self, tmp: Path, seed: int, weights: dict,
                 arrivals: int = 70) -> None:
        self.tmp, self.seed, self.weights, self.arrivals = tmp, seed, weights, arrivals
        self.rng = random.Random(seed)
        self.calls: list = []
        # call number -> the w tokens of the user turn a DM call was given.
        self.said: dict = {}
        self.sends: list = []
        self.reactions: list = []
        self.broken: list = []
        self.inflight: dict = defaultdict(int)
        self.longest = 0.0
        # conversation -> what arrived there, in order; and its commands.
        self.arrived: dict = defaultdict(list)
        self.commands: dict = defaultdict(list)

    # -- the stubs --

    def _build(self) -> None:
        # The agent's own draws: pacing, which excuse, the proactive shuffle.
        random.seed(self.seed)
        agent = self.agent = make_agent(
            self.tmp, chat_followup_window_s=3600, chat_context_messages=5000)
        agent.message_debounce_sec = 0.5 if self.seed % 2 else 0.0
        agent.access_dm_users = {"7"}
        agent.memory_max_per_conversation = 1000
        agent.pending_reactions = reactions.PendingReplies()
        agent.proactive_prob = agent.proactive_dm_prob = 1.0
        # Below zero: the wall clock can never decide whether a tick speaks.
        agent.proactive_min_silence_s = agent.proactive_cooldown_s = -1
        agent.proactive_dm_min_silence_s = agent.proactive_dm_cooldown_s = -1
        self.budget = agent.llm_timeout_s * turns._TURN_BUDGET_CALLS

        async def think(group_id, mode, text="", caller_override=None):
            seen = _tokens(m["text"] for m in agent.buffers[group_id])
            return await self._model(group_id, seen), "chat", ""

        async def chat_dm(history, is_admin=False, pkey="", proactive=False,
                          proactive_cue=""):
            # The whole record, not the slice a proactive turn is given.
            stored = agent.dm_history.get(pkey.split(":", 1)[1], [])
            if not proactive:
                self.said[len(self.calls)] = _tokens([history[-1]["content"]])
            seen = _tokens(m["content"] for m in [*stored, *history])
            return await self._model(pkey, seen), ""

        async def send_group(group_id, text, at_user_id=""):
            return await self._send(group_id, text)

        async def send_dm(user_id, text):
            return await self._send(f"private:{user_id}", text)

        read = agent._extract_text

        async def slow_read(payload):
            if payload.get("message_type") == "private":
                wait = self.rng.choice((0, 0, 0, 0.3, 4.0))
                if wait:
                    await asyncio.sleep(wait)
            return await read(payload)

        async def process_reaction(entry, text, name, uid, is_admin,
                                   conv_id="", is_dm=False):
            self.reactions.append(
                (conv_id, _tokens([entry["reply"]]), _tokens([text])))

        agent._think, agent._chat_dm = think, chat_dm
        agent._send_group, agent._send_dm = send_group, send_dm
        agent._extract_text = slow_read
        agent._process_reaction = process_reaction

    async def _model(self, conv: str, seen: list) -> str:
        n = len(self.calls)
        fate = self.rng.choices(("reply", "pass", "raise", "hang"),
                                (60, 10, 15, 15))[0]
        delay = self.rng.choice((0, 0.1, 1.0, 6.0, 30.0))
        self.calls.append({"n": n, "conv": conv, "saw": set(seen), "fate": fate})
        self.inflight[conv] += 1
        if self.inflight[conv] > 1:
            self.broken.append(f"call {n}: a second turn of {conv} at once")
        loop = asyncio.get_running_loop()
        began = loop.time()
        try:
            await asyncio.sleep(delay)
            if fate == "hang":
                await asyncio.sleep(self.budget * 10)
            if fate == "raise":
                raise RuntimeError("provider blip")
            return "PASS" if fate == "pass" else f"answer r{n}"
        finally:
            self.inflight[conv] -= 1
            self.longest = max(self.longest, loop.time() - began)

    async def _send(self, conv: str, text: str) -> SendResult:
        ok = self.rng.random() >= 0.08
        if self.rng.random() < 0.3:
            await asyncio.sleep(0.2)
        self.sends.append((conv, text, ok))
        return SendResult(success=ok)

    # -- the traffic --

    def _arrive(self, i: int):
        agent = self.agent
        kind = self.rng.choices(list(self.weights), list(self.weights.values()))[0]
        if kind == "p_group":
            return agent._maybe_proactive_groups()
        if kind == "p_dm":
            return agent._maybe_proactive_dms()
        if kind == "d_cue":
            return agent.handle_event(_dm_event(f"nudge c{i}", i, proactive=True))
        if kind.startswith("g_"):
            via, conv = self.rng.choice(self.GROUPS)
            user = self.rng.choice(("101", "102", "42"))
            text = {"g_chat": f"w{i} lol", "g_call": f" w{i} you there",
                    "g_cmd": f" remember k{i} likes tea"}[kind]
            # A command's line is buffered like any other message.
            self.arrived[conv].append(_tokens([text])[0])
            if kind == "g_cmd":
                self.commands[conv].append(f"k{i}")
            at_bot = kind != "g_chat"
            if via == "event":
                return agent.handle_event(_event(
                    text, i, sender=user, name=f"U{user}", at_bot=at_bot))
            return agent.handle_onebot(_group(
                text, f"g{i}", group=conv, user=user, name=f"U{user}",
                at_bot=at_bot))
        via, uid = self.rng.choice(self.DMS)
        if kind == "d_cmd":
            text = f"Luna remember k{i} likes tea"
            self.commands[f"private:{uid}"].append(f"k{i}")
        else:
            text = f"w{i} hey"
            self.arrived[f"private:{uid}"].append(f"w{i}")
        if via == "event":
            return agent.handle_event(_dm_event(text, i))
        return agent.handle_onebot(_dm(text, f"d{i}", uid))

    async def run(self) -> "Storm":
        self._build()
        tasks = []
        for i in range(self.arrivals):
            await asyncio.sleep(self.rng.choice((0, 0, 0, 0.05, 0.5, 2.0, 20.0)))
            tasks.append(asyncio.create_task(self._arrive(i)))
        # On the virtual clock: a handler that never returns fails the run
        # here instead of hanging it.
        self.results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True), 1_000_000)
        await asyncio.sleep(3600)
        self.unfinished = [t for t in self.agent._bg_tasks if not t.done()]
        return self

    # -- what must hold --

    def verify(self) -> None:
        agent = self.agent

        def ok(name: str, cond, detail="") -> None:
            check(f"seed {self.seed}: {name}", cond, repr(detail))

        ok("every handler returned",
           not [r for r in self.results if isinstance(r, BaseException)],
           [r for r in self.results if isinstance(r, BaseException)])
        ok("no line is left behind", agent._pending_outbound == {},
           agent._pending_outbound)
        ok("no background work is left", not self.unfinished, self.unfinished)
        ok("one turn at a time in a conversation", not self.broken, self.broken)
        ok("no model call outlives the turn budget",
           self.longest <= self.budget + 1e-6, self.longest)

        saw = {f"r{c['n']}": c["saw"] for c in self.calls}
        delivered: dict = defaultdict(list)
        for conv, text, sent in self.sends:
            if sent:
                delivered[conv] += _tokens([text])

        def replies_in_place(conv: str, order: list) -> None:
            ok(f"{conv}: each delivered reply is on record once, and no other",
               sorted(t for t in order if t[0] == "r") == sorted(delivered[conv]),
               (order, delivered[conv]))
            for at, token in enumerate(order):
                if token[0] == "r":
                    unseen = set(order[:at]) - saw[token]
                    ok(f"{conv}: {token} is placed after nothing it did not see",
                       not unseen, unseen)

        for _via, conv in self.GROUPS:
            order = _tokens(m["text"] for m in agent.buffers[conv])
            ok(f"{conv}: every message is on record once, in the order it came",
               [t for t in order if t[0] != "r"] == self.arrived[conv],
               (order, self.arrived[conv]))
            replies_in_place(conv, order)

        for _via, uid in self.DMS:
            conv = f"private:{uid}"
            history = agent.dm_history.get(uid, [])
            ok(f"{conv}: no two user turns in a row",
               not any(a["role"] == b["role"] == "user"
                       for a, b in zip(history, history[1:])), history)
            order = _tokens(m["content"] for m in history)
            ok(f"{conv}: no command or cue is in the history",
               all(t[0] in "wr" for t in order), order)
            waiting = _tokens(agent._dm_unanswered.get(uid, []))
            kept = [t for t in order if t[0] == "w"] + waiting
            ok(f"{conv}: no message is doubled", len(set(kept)) == len(kept), kept)
            ok(f"{conv}: messages keep the order they came in",
               kept == [t for t in self.arrived[conv] if t in set(kept)],
               (kept, self.arrived[conv]))
            # A turn that commits nothing keeps its last three messages.
            capped = {t for c in self.calls
                      if c["conv"] == conv and f"r{c['n']}" not in order
                      for t in self.said.get(c["n"], [])[:-3]}
            ok(f"{conv}: no message is lost",
               set(self.arrived[conv]) - set(kept) <= capped,
               set(self.arrived[conv]) - set(kept) - capped)
            replies_in_place(conv, order)

        for conv in [c for _via, c in self.GROUPS] + [
                f"private:{uid}" for _via, uid in self.DMS]:
            ran = _tokens(m["text"] for m in agent.memories.get(conv, []))
            ok(f"{conv}: every command ran once, in the order it came",
               ran == self.commands[conv], (ran, self.commands[conv]))
            answers = [text for c, text, _sent in self.sends
                       if c == conv and text in NOTED]
            ok(f"{conv}: every command was answered once",
               len(answers) == len(self.commands[conv]),
               (len(answers), len(self.commands[conv])))

        matched = [r for _conv, replies, _said in self.reactions for r in replies]
        ok("a reply is reacted to at most once",
           len(set(matched)) == len(matched), matched)

    def fingerprint(self) -> tuple:
        agent = self.agent
        return (
            [(conv, [m["text"] for m in agent.buffers[conv]])
             for _via, conv in self.GROUPS],
            [(uid, agent.dm_history.get(uid, [])) for _via, uid in self.DMS],
            [(c["conv"], c["fate"]) for c in self.calls], self.sends,
            [repr(r) for r in self.results])

    def stats(self) -> dict:
        fates = [c["fate"] for c in self.calls]
        return {
            "calls": len(fates), "overruns": fates.count("hang"),
            "failures": fates.count("raise"), "passes": fates.count("pass"),
            "replies": sum(len(_tokens([t])) for _c, t, sent in self.sends if sent),
            "merged": sum(len(said) > 1 for said in self.said.values()),
            "left early": sum(r is False or (isinstance(r, dict) and not r["handled"])
                              for r in self.results),
            "commands": sum(len(v) for v in self.commands.values()),
        }


def test_a_storm_of_groups_and_dms_keeps_every_invariant(tmp: Path, monkeypatch) -> None:
    """Groups and DMs at once, over NapCat and a connector, with memory
    commands, cues and the proactive loop, against a model that is slow,
    silent, failing or stuck: whatever the interleaving, no reply is placed
    after a message it did not see, nothing is lost or doubled, every
    handler returns and no line is left behind."""
    monkeypatch.setattr(TextProcessing, "_is_sleep_hour", staticmethod(lambda: False))
    totals: dict = defaultdict(int)
    for seed in SEEDS:
        storm = on_a_virtual_clock(Storm(tmp / str(seed), seed, MIXED).run())
        storm.verify()
        for name, count in storm.stats().items():
            totals[name] += count
    check("the storm did what it is for: replies, silences, failures, budget "
          "overruns, merged DM turns, commands and handlers that left early",
          totals["replies"] >= 100 and all(
              totals[k] >= 10 for k in ("overruns", "failures", "passes",
                                        "merged", "left early", "commands")),
          repr(dict(totals)))

    again = on_a_virtual_clock(Storm(tmp / "again", SEEDS[0], MIXED).run())
    first = on_a_virtual_clock(Storm(tmp / "first", SEEDS[0], MIXED).run())
    check("a seed replays the same run", again.fingerprint() == first.fingerprint())
