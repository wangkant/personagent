"""A one-on-one turn whose model is slow: what becomes of the DMs that arrive
meanwhile, in what order they are answered, and how long the turn may take.
The group counterpart, and the storm borrowed at the end, are in
tests/test_turns.py.

Run from the repo root:

    python -m pytest tests/test_dm_turns.py
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from pathlib import Path

from persona_agent import dm
from persona_agent.agent import Agent
from persona_agent.prompts import MODEL_FAILURE_EXCUSES
from persona_agent.textproc import TextProcessing
from persona_agent.transport import SendResult

from helpers import check
from test_turns import (NOTED, SEEDS, Storm, _dm, _dm_event, _settle,
                        make_agent, on_a_virtual_clock)

PKEY = "private:42"


def _collect_dms(agent: Agent) -> list:
    sent: list = []

    async def fake_send(user_id, text):
        sent.append((user_id, text))
        return SendResult(success=True, message_ids=[f"out-{len(sent)}"])

    agent._send_dm = fake_send
    return sent


def _hang_the_first_call(agent: Agent):
    """`_chat_dm` whose first call waits for `release`; later ones answer at
    once. `seen` is what each call was given: (history, proactive, cue)."""
    started, release, seen = asyncio.Event(), asyncio.Event(), []

    async def chat(history, is_admin=False, pkey="", proactive=False,
                   proactive_cue=""):
        seen.append(([dict(m) for m in history], proactive, proactive_cue))
        mine = len(seen)
        if mine == 1:
            started.set()
            await release.wait()
        return f"answer {mine}", ""

    agent._chat_dm = chat
    return started, release, seen


def _user(*lines: str) -> dict:
    return {"role": "user", "content": "\n".join(lines)}


def _bot(text: str) -> dict:
    return {"role": "assistant", "content": text}


# ---- DMs that arrive while the model is being asked --------------------------

async def test_dms_during_a_model_call_leave_and_are_answered_in_one_turn(
        tmp: Path) -> None:
    """Every DM handler waited on the send lock for the whole model call of
    the one before it, each holding a webhook admission slot: one person and
    a stuck model answered 429 for every chat. Now only the newest waits, and
    its turn answers all of them, in the order they came."""
    agent = make_agent(tmp)
    sent = _collect_dms(agent)
    started, release, seen = _hang_the_first_call(agent)
    first = asyncio.create_task(agent.handle_onebot(_dm("question one", "d0")))
    await started.wait()
    later = [asyncio.create_task(agent.handle_onebot(_dm(f"more {i}", f"d{i}")))
             for i in range(1, 21)]
    await _settle()

    check("the model is still being asked", not first.done())
    check("all but the newest handler have returned, without the model",
          [t.done() for t in later] == [True] * 19 + [False],
          repr([t.done() for t in later]))
    check("...unanswered", all(t.result() is False for t in later[:19]))
    check("neither lock of the conversation is held while the model is asked",
          not agent.locks[PKEY].locked() and not agent.send_locks[PKEY].locked())
    check("none of them is in what the reply is being written from",
          agent._dm_unanswered.get("42") == ["question one"],
          repr(agent._dm_unanswered))

    release.set()
    handled = await asyncio.gather(first, *later)
    words = [f"more {i}" for i in range(1, 21)]
    check("one more turn answers all twenty, in the order they came",
          len(seen) == 2 and seen[1][0] == [
              _user("question one"), _bot("answer 1"), _user(*words)],
          repr(seen[1:]))
    check("it is the newest request's own", handled[0] is True
          and handled[-1] is True, repr(handled))
    check("the first reply sits right after what it saw, the rest after it",
          agent.dm_history["42"] == [
              _user("question one"), _bot("answer 1"), _user(*words),
              _bot("answer 2")], repr(agent.dm_history["42"]))
    check("both replies went out, once each",
          sent == [("42", "answer 1"), ("42", "answer 2")], repr(sent))
    check("nothing waits, nothing stays held",
          not agent._dm_unanswered.get("42") and PKEY not in agent._pending_outbound)


async def test_dms_keep_arrival_order_however_long_each_takes_to_read(
        tmp: Path) -> None:
    """Reading a message (an image to caption, a link to fetch) is not done
    under a lock any more, so order is kept by the place each DM takes in
    line before it is read."""
    agent = make_agent(tmp)
    _collect_dms(agent)
    _started, release, seen = _hang_the_first_call(agent)
    release.set()
    slow_read = asyncio.Event()
    read = agent._extract_text

    async def reading(payload):
        if payload["message_id"] == "slow":
            await slow_read.wait()
        return await read(payload)

    agent._extract_text = reading
    one = asyncio.create_task(agent.handle_onebot(_dm("one", "slow")))
    await _settle()
    two = asyncio.create_task(agent.handle_onebot(_dm("two", "quick-1")))
    three = asyncio.create_task(agent.handle_onebot(_dm("three", "quick-2")))
    await _settle()
    check("nothing is answered ahead of a message still being read", seen == [],
          repr(seen))
    check("of the ones behind it, only the newest handler waits",
          two.done() and two.result() is False and not three.done())

    slow_read.set()
    handled = await asyncio.gather(one, two, three)
    check("one turn, with the three in the order they arrived",
          [h for h, _p, _c in seen] == [[_user("one", "two", "three")]], repr(seen))
    check("answered in the newest request", handled == [False, False, True],
          repr(handled))

    # A message that turns out to hold nothing gives its place up.
    async def nothing(payload):
        await slow_read.wait()
        return "" if payload["message_id"] == "empty" else await read(payload)

    slow_read.clear()
    agent._extract_text = nothing
    empty = asyncio.create_task(agent.handle_onebot(_dm("", "empty")))
    four = asyncio.create_task(agent.handle_onebot(_dm("four", "quick-3")))
    await _settle()
    slow_read.set()
    check("an empty message is not handled, and does not block the next",
          await asyncio.gather(empty, four) == [False, True])
    check("the line is gone once it is empty", PKEY not in agent._pending_outbound)


# ---- one time budget for the whole turn --------------------------------------

async def test_a_dm_turn_over_its_budget_ends_with_the_failure_line_once(
        tmp: Path) -> None:
    """A DM's model call was bounded per attempt per model, never as a turn."""
    agent = make_agent(tmp)
    agent.llm_timeout_s = 0.02
    sent = _collect_dms(agent)
    cancelled: list = []
    answers = False

    async def chat(history, is_admin=False, pkey="", proactive=False,
                   proactive_cue=""):
        if answers:
            return "there you are", ""
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(history[-1]["content"])

    agent._chat_dm = chat
    first = asyncio.create_task(agent.handle_onebot(_dm("you there?", "b1")))
    await _settle()
    held = asyncio.create_task(agent.handle_onebot(_dm("hello??", "b2")))
    handled = await asyncio.wait_for(first, 5)
    check("the turn ends unanswered when its budget runs out", handled is False)
    check("the reader is told once, with the usual line",
          len(sent) == 1 and sent[0][1] in MODEL_FAILURE_EXCUSES["en"], repr(sent))
    check("what arrived meanwhile then gets its own turn, with the words the "
          "first one left", await asyncio.wait_for(held, 5) is False
          and cancelled == ["you there?", "you there?\nhello??"], repr(cancelled))
    check("that one says nothing more (cooldown)", len(sent) == 1, repr(sent))
    check("the words wait for a turn that answers",
          agent._dm_unanswered.get("42") == ["you there?", "hello??"],
          repr(agent._dm_unanswered))

    answers = True
    check("which the next message gets",
          await asyncio.wait_for(agent.handle_onebot(_dm("ok?", "b3")), 5) is True
          and agent.dm_history["42"] == [
              _user("you there?", "hello??", "ok?"), _bot("there you are")],
          repr(agent.dm_history.get("42")))
    check("nothing stays held", PKEY not in agent._pending_outbound)


# ---- the follow-up question, and a message that cannot be read ----------------

async def test_a_follow_up_question_waits_for_the_turn_and_stays_on_record(
        tmp: Path) -> None:
    """The question asked after a complaint went out while the model was
    still being asked, and the turn's commit then wrote the history over it:
    they read "what did you mean?", answered it, and the model never knew."""
    agent = make_agent(tmp)
    agent.react_elicit_delay_s = 0.0
    sent = _collect_dms(agent)
    started, release, seen = _hang_the_first_call(agent)
    first = asyncio.create_task(agent.handle_onebot(_dm("question one", "d0")))
    await started.wait()
    entry = {"reply": "an earlier reply", "ctx_lines": [], "mode": "called"}
    ask = asyncio.create_task(agent._maybe_elicit(
        "dm:42", entry, "wait, what did you mean?", "42", True))
    await _settle()
    check("nothing is said while the model is being asked",
          sent == [] and not ask.done(), repr(sent))

    release.set()
    await asyncio.gather(first, ask)
    await agent.handle_onebot(_dm("I meant the other one", "d1"))
    check("the reply goes out first, then the question, then the next reply",
          sent == [("42", "answer 1"), ("42", "wait, what did you mean?"),
                   ("42", "answer 2")], repr(sent))
    check("the question is in the history the next turn is written from",
          seen[1][0] == [_user("question one"), _bot("answer 1"),
                         _bot("wait, what did you mean?"),
                         _user("I meant the other one")], repr(seen[1][0]))
    check("nothing stays held", PKEY not in agent._pending_outbound)


async def test_a_dm_that_cannot_be_read_gives_its_place_back(
        tmp: Path, monkeypatch) -> None:
    agent = make_agent(tmp)
    sent = _collect_dms(agent)
    _hang_the_first_call(agent)[1].set()

    def broken(text):
        raise RuntimeError("cannot tell")

    monkeypatch.setattr(agent, "_is_memory_command", broken)
    try:
        await agent.handle_onebot(_dm("hello", "d0"))
    except RuntimeError:
        pass
    check("no place is left behind", PKEY not in agent._pending_outbound)
    monkeypatch.undo()
    check("the next DM is answered", await agent.handle_onebot(_dm("hello again", "d1"))
          is True and sent == [("42", "answer 1")], repr(sent))


# ---- memory commands and cues in line ----------------------------------------

async def test_a_held_dm_command_runs_after_the_turn_without_its_handler(
        tmp: Path) -> None:
    agent = make_agent(tmp)
    sent = _collect_dms(agent)
    started, release, seen = _hang_the_first_call(agent)
    first = asyncio.create_task(agent.handle_onebot(_dm("question one", "d0")))
    await started.wait()
    commands = [asyncio.create_task(agent.handle_onebot(
        _dm(f"Luna remember k{i} likes tea", f"m{i}"))) for i in range(70)]
    await _settle()
    check("every command's handler has returned: more than there are slots",
          all(t.done() and t.result() is False for t in commands),
          repr(sum(not t.done() for t in commands)))
    check("no command has run or been answered yet",
          agent.memories.get(PKEY, []) == [] and sent == [])

    agent.memory_max_per_conversation = 200
    release.set()
    await first
    for _ in range(20):
        await _settle()
    check("every command ran once the turn was over, in the order it came",
          [m["text"] for m in agent.memories[PKEY]]
          == [f"k{i} likes tea" for i in range(70)],
          repr(agent.memories.get(PKEY))[:300])
    check("the reply went out first, then one answer per command",
          sent[0] == ("42", "answer 1") and len(sent) == 71
          and all(text in NOTED for _, text in sent[1:]), repr(sent[:3]))
    check("a command is no model call and no history",
          len(seen) == 1 and agent.dm_history["42"] == [
              _user("question one"), _bot("answer 1")],
          repr(agent.dm_history["42"]))

    handled = await agent.handle_onebot(_dm("Luna remember I like cats", "m-now"))
    check("with no turn in flight a command is answered in its own request",
          handled is True and sent[-1][1] in NOTED and len(sent) == 72, repr(sent[-2:]))
    check("nothing stays held", PKEY not in agent._pending_outbound)


async def test_a_cue_waits_its_turn_in_line_and_runs_its_own(tmp: Path) -> None:
    """A connector's proactive cue is a turn of its own: it is not merged
    into the reader's words, and not overtaken by them."""
    agent = make_agent(tmp)
    started, release, seen = _hang_the_first_call(agent)
    first = asyncio.create_task(agent.handle_event(_dm_event("hello", 1)))
    await started.wait()
    cue = asyncio.create_task(agent.handle_event(
        _dm_event("they have an exam today", 2, proactive=True)))
    await _settle()
    words = asyncio.create_task(agent.handle_event(_dm_event("you there", 3)))
    await _settle()
    check("both wait behind the turn in flight", not cue.done() and not words.done())

    release.set()
    one, two, three = await asyncio.gather(first, cue, words)
    check("each request carries its own reply",
          [[r.get("text") for r in x["replies"]] for x in (one, two, three)]
          == [["answer 1"], ["answer 2"], ["answer 3"]], repr((one, two, three)))
    check("the cue ran second, as a cue, on a history ending on the bot",
          seen[1][1] is True and seen[1][2] == "they have an exam today"
          and seen[1][0] == [_user("hello"), _bot("answer 1")], repr(seen[1]))
    check("the reader's words ran third, after both replies",
          seen[2][1] is False and seen[2][0] == [
              _user("hello"), _bot("answer 1"), _bot("answer 2"),
              _user("you there")], repr(seen[2]))
    check("nothing stays held",
          "private:telegram:9" not in agent._pending_outbound)


# ---- the agent speaking first ------------------------------------------------

async def test_a_proactive_dm_turn_has_the_budget_and_holds_no_lock(
        tmp: Path) -> None:
    """The proactive loop held the conversation's lock while it asked the
    model, with no budget: every DM of that person waited on the lock, each
    holding a slot, for as long as the model took."""
    agent = make_agent(tmp)
    agent.proactive_dm_prob = 1.0
    sent = _collect_dms(agent)

    def go_quiet() -> None:
        agent.last_dm_activity_at["42"] = (
            time.time() - agent.proactive_dm_min_silence_s - 100)

    cancelled: list = []

    async def never_answers(history, is_admin=False, pkey="", proactive=False,
                            proactive_cue=""):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(proactive)

    agent._chat_dm = never_answers
    agent.llm_timeout_s = 0.02
    go_quiet()
    acted = await asyncio.wait_for(agent._maybe_proactive_dms(), 5)
    check("an opener the model never writes is given up at the turn budget",
          acted is False and cancelled == [True], repr((acted, cancelled)))
    check("and leaves nothing held", PKEY not in agent._pending_outbound)

    agent.llm_timeout_s = 120.0
    started, release, seen = _hang_the_first_call(agent)
    go_quiet()
    opener = asyncio.create_task(agent._maybe_proactive_dms())
    await started.wait()
    check("no lock is held while the opener is written",
          not agent.locks[PKEY].locked() and not agent.send_locks[PKEY].locked())
    later = [asyncio.create_task(agent.handle_onebot(_dm(word, f"p-{word}")))
             for word in ("a", "b", "c")]
    await _settle()
    check("what they write meanwhile waits behind it, one handler only",
          [t.done() for t in later] == [True, True, False],
          repr([t.done() for t in later]))
    release.set()
    check("the opener goes out", await opener is True
          and sent[0] == ("42", "answer 1"), repr(sent))
    await asyncio.gather(*later)
    check("on record before the words it did not see, which get one turn",
          agent.dm_history["42"] == [
              _bot("answer 1"), _user("a", "b", "c"), _bot("answer 2")],
          repr(agent.dm_history["42"]))
    check("nothing stays held", PKEY not in agent._pending_outbound)


# ---- a storm of DMs ----------------------------------------------------------

#: DMs only, more of them: messages, memory commands, a connector's cues and
#: the proactive loop, for three people at once.
DMS_ONLY = {"d_chat": 60, "d_cmd": 14, "d_cue": 8, "p_dm": 8}
ARRIVALS = 90


def test_a_storm_of_dms_keeps_every_invariant(tmp: Path, monkeypatch) -> None:
    """The DM side of tests/test_turns.py's storm, denser: each message takes
    a random time to read, so arrival order is the line's doing alone."""
    monkeypatch.setattr(TextProcessing, "_is_sleep_hour", staticmethod(lambda: False))
    # The check reads the whole history: nothing may be trimmed out of it.
    monkeypatch.setattr(dm, "_DM_HISTORY_MAX", 10_000)
    totals: dict = defaultdict(int)
    for seed in SEEDS:
        storm = on_a_virtual_clock(
            Storm(tmp / str(seed), seed, DMS_ONLY, ARRIVALS).run())
        storm.verify()
        for name, count in storm.stats().items():
            totals[name] += count
    check("the storm did what it is for: replies, silences, failures, budget "
          "overruns, merged turns, commands and handlers that left early",
          totals["replies"] >= 100 and all(
              totals[k] >= 10 for k in ("overruns", "failures", "passes",
                                        "merged", "left early", "commands")),
          repr(dict(totals)))
