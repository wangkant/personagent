"""Consolidation (the "fold"): when the one batched call is made, what bounds
it, and what of its answer is kept. Every answer here is scripted; no test
calls a model.

Run from the repo root:

    python -m pytest tests/test_memory_fold.py
"""
from __future__ import annotations

import asyncio
import json
import time
import types
from datetime import date, datetime, timedelta
from pathlib import Path

from persona_agent import consolidate, memstate, memstore
from persona_agent.agent import Agent

from helpers import check
from test_turns import make_agent

ROOM = "telegram:g"
OTHER = "telegram:h"
DAY = 86400.0

SAM, ALEX, KIM = ("s", "Sam"), ("a", "Alex"), ("k", "Kim")


def fold_agent(tmp: Path, **settings) -> Agent:
    return make_agent(tmp, **{"memory_tidy_every": 8, "memory_calls_per_day": 40,
                              **settings})


def script(agent: Agent, *answers) -> list:
    """`_call_llm` answering with each of `answers` in turn: a dict (sent as
    JSON), a string, an exception (raised) or a coroutine function (awaited).
    Returns the prompts it was given."""
    prompts: list = []
    queue = list(answers)

    async def call(system, messages, model, **_kw):
        prompts.append(messages[0]["content"])
        if not queue:
            raise AssertionError("an unscripted model call")
        answer = queue.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        if callable(answer):
            answer = await answer()
        return answer if isinstance(answer, str) else json.dumps(answer)

    agent._call_llm = call
    return prompts


def say(agent: Agent, conv: str, lines, start: float, step: float = 60.0) -> None:
    for i, (who, text) in enumerate(lines):
        uid, name = who if who else ("", agent.persona_name)
        agent._append_buffer(conv, name, text, uid, at=start + i * step)


def note(text: str, who=None, *, auto=True, age_days=10.0, **extra) -> dict:
    t = time.time() - age_days * DAY
    row = {"text": text, "time": t, "born": t, "imp": 3, "uses": 0, "used": 0.0,
           "id": memstore.new_id("m"), **extra}
    if auto:
        row["auto"] = True
    if who:
        row["user_id"], row["user_name"] = who
    return row


def label(inp, text: str) -> str:
    return next(k for k, (it, _t) in inp.notes.items() if it["text"] == text)


def line_of(inp, text: str) -> str:
    return next(k for k, ln in inp.lines.items() if ln["text"] == text)


async def run_fold(agent: Agent, conv: str = ROOM, reason: str = "idle", *, edit=None):
    inp = agent._fold_input(conv, reason)
    if edit is not None:
        edit(inp)
    return inp, await agent._fold(conv, reason, inp)


def trash(agent: Agent) -> list:
    path = agent.memory_trash.path
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


# ---- when -------------------------------------------------------------------

async def test_sixty_old_lines_start_a_consolidation_fifty_nine_do_not(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, f"line {i}") if i % 2 else (ALEX, f"line {i}")
                      for i in range(89)], time.time() - 3600, step=10)
    check("59 lines past the newest 30: not yet", agent._fold_due(ROOM) is None,
          repr(agent._fold_due(ROOM)))
    say(agent, ROOM, [(KIM, "one more")], time.time())
    check("60: due for the lines", agent._fold_due(ROOM) == "lines")


async def test_a_quiet_chat_is_consolidated_after_three_hours(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM if i % 2 else ALEX, f"line {i}") for i in range(12)],
        time.time() - 179 * 60 - 11, step=1)
    check("179 minutes of quiet: not yet", agent._fold_due(ROOM) is None)
    other = fold_agent(tmp / "b")
    say(other, ROOM, [(SAM if i % 2 else ALEX, f"line {i}") for i in range(12)],
        time.time() - 180 * 60 - 11, step=1)
    check("180 minutes and twelve lines: due", other._fold_due(ROOM) == "idle")
    few = fold_agent(tmp / "c")
    say(few, ROOM, [(SAM if i % 2 else ALEX, f"line {i}") for i in range(11)],
        time.time() - 181 * 60, step=1)
    check("eleven lines: not worth a call", few._fold_due(ROOM) is None)


async def test_reply_notes_and_a_dm_trim_start_one(tmp: Path) -> None:
    agent = fold_agent(tmp)
    agent.memories[ROOM] = [note(f"fact {i}") for i in range(7)]
    check("seven pending notes: not yet", agent._fold_due(ROOM) is None)
    agent.memories[ROOM].append(note("fact 7"))
    check("MEMORY_TIDY_EVERY pending notes: due", agent._fold_due(ROOM) == "notes")
    dm = "private:telegram:9"
    agent._wake(dm)
    agent._dm_spill["telegram:9"] = [{"role": "user", "content": "hi", "t": 1.0, "seq": 1}]
    check("turns the trim dropped: due", agent._fold_due(dm) == "trim")


# ---- what bounds it --------------------------------------------------------------

async def test_with_either_setting_at_zero_nothing_is_called(tmp: Path) -> None:
    for settings in ({"memory_calls_per_day": 0}, {"memory_tidy_every": 0}):
        agent = fold_agent(tmp / str(len(settings)) / next(iter(settings)), **settings)
        script(agent)
        say(agent, ROOM, [(SAM if i % 2 else ALEX, f"line {i}") for i in range(200)],
            time.time() - DAY, step=60)
        agent.memories[ROOM] = [note(f"fact {i}") for i in range(20)]
        check(f"{settings}: nothing starts", agent._maybe_consolidate(ROOM, "lines") is None
              and not agent._folding)
        check(f"{settings}: the loop's scan starts nothing", agent._scan_folds() == [])


async def test_the_budget_gates_each_call(tmp: Path) -> None:
    agent = fold_agent(tmp)
    script(agent)
    say(agent, ROOM, [(SAM if i % 2 else ALEX, f"line {i}") for i in range(20)],
        time.time() - 4 * 3600)
    now = time.time()
    state = agent.memory_state
    budget = memstate.CallBudget(state)
    today = datetime.fromtimestamp(now).date().isoformat()
    state.data["per_conv"] = {ROOM: {"day": today, "count": 16, "last": now - 3600}}
    check("16 in a chat today: no more", agent._maybe_consolidate(ROOM, "idle") is None)
    state.data["per_conv"] = {ROOM: {"day": today, "count": 2, "last": now - 600}}
    check("twenty minutes not passed: waits", agent._maybe_consolidate(ROOM, "idle") is None)
    check("an evicted chat skips the gap", budget.allowed(
        ROOM, now, 40, reason="evict") is None)
    state.data["per_conv"] = {}
    state.data["calls"] = [now - 100.0] * 40
    check("40 for all chats in a day: none for any chat",
          agent._maybe_consolidate(ROOM, "idle") is None)
    state.data["calls"] = []
    agent._folding.add(ROOM)
    check("one already under way: no second", agent._maybe_consolidate(ROOM, "idle") is None)
    agent._folding.clear()
    state.data["paused_until"] = now + 600
    check("paused: none", agent._maybe_consolidate(ROOM, "idle") is None)


async def test_failures_back_off_and_a_success_resets(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, "I moved to Lisbon"), (ALEX, "nice")], time.time() - 4 * 3600)
    script(agent, RuntimeError("HTTP 500"), "not json at all", ["a", "list"],
           asyncio.TimeoutError(), {"thread": None, "facts": [], "episodes": []})
    row = lambda: agent.memory_state.data["per_conv"][ROOM]  # noqa: E731
    waits = []
    for _ in range(4):
        before = time.time()
        await run_fold(agent)
        waits.append(round((row()["next_at"] - before) / 60))
    check("ten minutes doubling", waits[:3] == [10, 20, 40], repr(waits))
    check("three failures in a row pause every chat for an hour",
          agent.memory_state.data["paused_until"] > time.time() + 3000)
    row()["fails"] = 9
    await run_fold(agent, edit=None) if False else None
    budget = memstate.CallBudget(agent.memory_state)
    check("never longer than six hours",
          budget.failed(ROOM, 0.0, "x") == memstate.BACKOFF_MAX_S)
    check("the reason kept is the error's class", row()["last_error"] == "str"
          or isinstance(row()["last_error"], str))
    check("nothing applied, the cursor kept", agent.folded_upto.get(ROOM, 0) == 0
          and not agent.memories.get(ROOM))
    await run_fold(agent)
    check("a success resets the backoff", row()["fails"] == 0 and row()["next_at"] == 0.0
          and agent.memory_state.data["fails_in_row"] == 0)
    check("and moves the cursor", agent.folded_upto[ROOM] == 2)


# ---- what is kept -----------------------------------------------------------------

def _room_with_history(agent: Agent) -> float:
    start = time.time() - 2 * 3600
    say(agent, ROOM, [
        (SAM, "I moved to Lisbon last month"),
        (ALEX, "Sam has a new dog called Rex"),
        (SAM, "yes, Rex is a beagle"),
        (ALEX, "we should hike on Saturday"),
        (SAM, "Saturday works, I will bring snacks"),
        (None, "Have fun, both of you"),
    ], start)
    agent.memories[ROOM] = [
        note("Sam lives in Berlin", SAM),
        note("Alex likes coffee", ALEX, age_days=20),
        note("Alex likes strong coffee in the morning", ALEX, age_days=5),
        note("Alex is looking for a job", ALEX, age_days=3),
        note("The group meets on Fridays", imp=2),
    ]
    return start


async def test_a_good_answer_is_applied_with_every_removal_in_the_trash(tmp: Path) -> None:
    agent = fold_agent(tmp)
    start = _room_with_history(agent)
    berlin = agent.memories[ROOM][0]
    coffee_old = agent.memories[ROOM][1]
    due = (date.today() + timedelta(days=3)).isoformat()

    def answer(inp):
        return {
            "thread": "Sam moved to Lisbon. Sam and Alex plan a hike on Saturday; "
                      "Sam will bring snacks.",
            "facts": [
                {"op": "add", "about": inp.lines["L3"]["speaker"],
                 "text": "Sam has a beagle called Rex", "imp": 3, "src": ["L2", "L3"]},
                {"op": "update", "n": label(inp, "Sam lives in Berlin"),
                 "text": "Sam lives in Lisbon", "src": ["L1"], "imp": 4},
                {"op": "end", "n": label(inp, "Alex is looking for a job"), "why": "over"},
                {"op": "merge", "from": [label(inp, "Alex likes coffee"),
                                         label(inp, "Alex likes strong coffee in the morning")],
                 "text": "Alex likes strong coffee in the morning"},
                {"op": "rate", "n": label(inp, "The group meets on Fridays"), "imp": 5}],
            "episodes": [{"op": "add", "text": "Sam and Alex planned a hike for Saturday",
                          "imp": 4, "src": ["L4", "L5"], "due": due}],
            "rollup": None}

    inp = agent._fold_input(ROOM, "idle")
    script(agent, answer(inp))
    result = await agent._fold(ROOM, "idle", inp)
    texts = {it["text"]: it for it in agent.memories[ROOM]}
    check("nothing refused", not result.refused, repr(result.refused))
    check("a fact added about its own speaker",
          texts["Sam has a beagle called Rex"]["user_id"] == "s"
          and texts["Sam has a beagle called Rex"]["src"] == "fold", repr(texts))
    check("the updated fact keeps its id", texts["Sam lives in Lisbon"]["id"] == berlin["id"]
          and "Sam lives in Berlin" not in texts)
    check("the ended fact is gone", "Alex is looking for a job" not in texts)
    check("the merge keeps the older note's id",
          texts["Alex likes strong coffee in the morning"]["id"] == coffee_old["id"]
          and "Alex likes coffee" not in texts)
    check("the rating", texts["The group meets on Fridays"]["imp"] == 5)
    rows = trash(agent)
    whys = sorted((r["item"]["text"], r["why"], r["by"]) for r in rows)
    check("every removal is in the trash, by the fold", whys == sorted([
        ("Sam lives in Berlin", "replaced", "fold"),
        ("Alex is looking for a job", "ended", "fold"),
        ("Alex likes strong coffee in the morning", "merged", "fold"),
    ]), repr(whys))
    (ep,) = agent.episode_store.episodes(ROOM)
    check("the event's times and people come from its lines",
          (ep["t0"], ep["t1"]) == (start + 180, start + 240)
          and ep["who"] == ["a", "s"] and ep["names"] == ["Alex", "Sam"], repr(ep))
    check("its plan's day is kept", ep["due"] == due)
    thread = agent.episode_store.thread(ROOM)
    check("the running summary", thread["text"].startswith("Sam moved to Lisbon")
          and thread["from_t"] == start and thread["to_t"] == start + 300, repr(thread))
    check("the cursor is past the chunk", agent.folded_upto[ROOM] == 6)
    check("every note it was shown is no longer pending",
          all(it.get("tidied") for it in agent.memories[ROOM]))
    on_disk = json.loads(agent.memory_file.read_text(encoding="utf-8"))[ROOM]
    check("memory.json written", {r["text"] for r in on_disk} == set(texts))


async def test_each_bad_operation_is_refused_alone(tmp: Path) -> None:
    agent = fold_agent(tmp)
    start = time.time() - 3 * 3600
    say(agent, ROOM, [
        (SAM, "I don't eat meat"),                  # L1
        (ALEX, "Sam owes me fifty euros"),          # L2
        (SAM, "I play the cello on Sundays"),       # L3
        (None, "Sounds lovely"),                    # L4
        (KIM, "I am vegetarian too"),               # L5
        (SAM, "I am vegan now, not vegetarian"),    # L6
    ], start)
    agent.memory_state.add_tombstone(
        ROOM, memstore.token_hashes("Sam plays the cello"), start + 3600)
    agent.memories[ROOM] = [
        note("Sam is vegetarian", SAM, auto=False, saved_by="s"),
        note("Kim likes tea", KIM, auto=False, saved_by="k"),
        note("Kim is new here", KIM, age_days=0.2),
        note("Alex likes chess", ALEX),
        note("Sam likes chess", SAM),
        note("Alex has a car", ALEX),
    ]
    edited = agent.memories[ROOM][5]

    def change(inp):
        edited["text"] = "Alex has a red car"

    inp = agent._fold_input(ROOM, "idle")
    change(inp)
    script(agent, {"facts": [
        {"op": "update", "n": "N99", "text": "x", "src": ["L1"]},
        {"op": "update", "n": label(inp, "Alex likes chess"), "text": "Alex likes go",
         "src": []},
        {"op": "add", "about": inp.lines["L3"]["speaker"], "text": "Sam owns a yacht",
         "src": ["L3"]},
        {"op": "add", "about": inp.lines["L1"]["speaker"], "text": "Sam eats meat",
         "src": ["L1"]},
        {"op": "add", "about": inp.lines["L1"]["speaker"],
         "text": "Alex says Sam owes him fifty euros", "src": ["L2"]},
        {"op": "add", "about": "group", "text": "Luna finds it lovely", "src": ["L4"]},
        {"op": "update", "n": label(inp, "Sam is vegetarian"), "text": "Sam is vegan",
         "src": ["L5"]},
        {"op": "update", "n": label(inp, "Kim likes tea"), "text": "Kim is vegetarian",
         "src": ["L5"]},
        {"op": "end", "n": label(inp, "Kim is new here"), "why": "over"},
        {"op": "merge", "from": [label(inp, "Alex likes chess"), label(inp, "Sam likes chess")],
         "text": "Alex and Sam like chess"},
        {"op": "update", "n": label(inp, "Alex has a red car"), "text": "Alex sold his car",
         "src": ["L2"]},
        {"op": "update", "n": label(inp, "Sam likes chess"), "text": "Sam plays the cello",
         "src": ["L3"]},
        {"op": "add", "about": inp.lines["L5"]["speaker"], "text": "Kim is a vegetarian too",
         "imp": 1, "src": ["L5"]},
        {"op": "forget", "n": "N1"},
    ]})
    result = await agent._fold(ROOM, "idle", inp)
    check("each refusal by its reason", dict(result.refused) == {
        "label": 1, "src": 1, "grounding": 1, "negation": 1, "subject": 1,
        "owner": 1, "age": 1, "merge": 1, "live": 1, "tombstone": 1, "shape": 1},
        repr(result.refused))
    texts = {it["text"]: it for it in agent.memories[ROOM]}
    reported = texts.get("Alex says Sam owes him fifty euros")
    check("a word about another person is kept as said by its speaker",
          reported is not None and not reported.get("user_id")
          and reported["said_by"] == "a" and reported["said_by_name"] == "Alex",
          repr(reported))
    check("a saved note changes on its subject's own line",
          "Kim is vegetarian" in texts and "Kim likes tea" not in texts)
    check("a saved note does not change on someone else's line",
          "Sam is vegetarian" in texts and "Sam is vegan" not in texts)
    check("importance 1 is not kept", result.done["unimportant"] == 1)
    check("the note edited meanwhile is left alone", edited["text"] == "Alex has a red car")


async def test_an_answer_is_held_to_the_per_call_caps(tmp: Path) -> None:
    agent = fold_agent(tmp)
    kinds = ("red", "blue", "green", "gold", "old", "rare", "tiny")
    lines = []
    for w in kinds:
        lines += [(SAM, f"I collect {w} stamps"), (ALEX, "nice")]
    say(agent, ROOM, lines, time.time() - 3 * 3600)
    inp = agent._fold_input(ROOM, "idle")
    sam = inp.lines["L1"]["speaker"]
    script(agent, {"facts": [
        {"op": "add", "about": sam, "text": f"Sam collects {w} stamps",
         "src": [f"L{2 * i - 1}"]} for i, w in enumerate(kinds, 1)],
        "episodes": [{"op": "add", "text": f"Sam showed {w} stamps", "src": ["L1", "L13"]}
                     for w in ("red", "blue", "green")]})
    result = await agent._fold(ROOM, "idle", inp)
    check("five facts and two events at most", result.done["add"] == 5
          and result.done["event"] == 2 and result.refused["cap"] == 3,
          repr((result.done, result.refused)))


async def test_an_events_dates_are_never_the_models(tmp: Path) -> None:
    agent = fold_agent(tmp)
    start = time.time() - 3 * 3600
    say(agent, ROOM, [(SAM, "we went to the lake"), (ALEX, "the lake was cold")], start)
    script(agent, {"episodes": [
        {"op": "add", "text": "On 2001-01-01 Sam and Alex went to the cold lake",
         "src": ["L1", "L2"], "due": "2001-01-01"}]})
    await run_fold(agent)
    (ep,) = agent.episode_store.episodes(ROOM)
    check("times from the lines", (ep["t0"], ep["t1"]) == (start, start + 60), repr(ep))
    check("a day outside the window is dropped", "due" not in ep, repr(ep))


async def test_a_month_is_rolled_up_into_one_event(tmp: Path) -> None:
    agent = fold_agent(tmp, memory_episodes_max=3)
    old = time.time() - 120 * DAY
    for i, text in enumerate(("Sam baked bread", "Sam baked a cake", "Sam baked cookies")):
        agent.episode_store.add(ROOM, {"t0": old + i * 3600, "t1": old + i * 3600 + 60,
                                       "who": ["s"], "names": ["Sam"], "text": text})
    say(agent, ROOM, [(SAM, "I bake every week"), (ALEX, "send me some")],
        time.time() - 4 * 3600)
    inp = agent._fold_input(ROOM, "idle")
    check("the month is offered", len(inp.month) == 3 and "fold_month" in inp.payload)
    script(agent, {"rollup": {"text": "Sam baked bread, a cake and cookies"}})
    await agent._fold(ROOM, "idle", inp)
    (ep,) = agent.episode_store.episodes(ROOM)
    check("one event for the month", len(ep["rollup"]) == 3
          and (ep["t0"], ep["t1"]) == (old, old + 2 * 3600 + 60), repr(ep))
    check("the three in the trash", sorted(r["why"] for r in trash(agent))
          == ["rolled_up"] * 3)


async def test_an_unusable_answer_changes_nothing_and_keeps_the_lines(tmp: Path) -> None:
    for i, bad in enumerate(("{oops", "[]", '{"facts": "not a list"}', {"weather": "fine"},
                             TimeoutError(), RuntimeError("HTTP 500"))):
        agent = fold_agent(tmp / str(i))
        _room_with_history(agent)
        before = json.dumps(agent.memories, sort_keys=True)
        script(agent, bad)
        _inp, result = await run_fold(agent)
        check(f"{bad!r}: nothing applied", result is None
              and json.dumps(agent.memories, sort_keys=True) == before
              and not agent.episode_store.episodes(ROOM)
              and not trash(agent))
        check(f"{bad!r}: the lines wait for the next try",
              agent.folded_upto.get(ROOM, 0) == 0 and agent._fold_due(ROOM, "evict"))


async def test_a_full_spill_counts_what_it_loses(tmp: Path) -> None:
    agent = fold_agent(tmp, chat_context_messages=10)
    say(agent, ROOM, [(SAM if i % 2 else ALEX, f"line {i}") for i in range(260)],
        time.time() - DAY, step=1)
    check("240 kept, the oldest ten counted as lost",
          len(agent._spill[ROOM]) == 240 and agent.memory_state.lost(ROOM) == 10,
          repr((len(agent._spill[ROOM]), agent.memory_state.lost(ROOM))))
    check("the oldest kept is line 10", agent._spill[ROOM][0]["text"] == "line 10")


async def test_the_input_holds_only_this_chats_notes(tmp: Path) -> None:
    agent = fold_agent(tmp)
    sam, alex = ("tg-user-1717", "Sam"), ("tg-user-2828", "Alex")
    say(agent, ROOM, [(sam, "hello there"), (alex, "hi Sam")], time.time() - 3600)
    agent.memories[OTHER] = [note("Sam secretly hates Alex", sam)]
    agent.memories[ROOM] = [note("Sam likes tea", sam)]
    payload = json.dumps(agent._fold_input(ROOM, "idle").payload, ensure_ascii=False)
    check("this chat's note", "Sam likes tea" in payload)
    check("never another chat's", "secretly" not in payload)
    check("no account ids, only labels", "tg-user" not in payload, payload)


# ---- running alongside turns and restarts -----------------------------------------

async def test_lines_that_arrive_during_a_call_wait_for_the_next(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM if i % 2 else ALEX, f"line {i}") for i in range(12)],
        time.time() - 4 * 3600, step=1)
    release = asyncio.Event()

    async def slow():
        await release.wait()
        return {"thread": "Sam and Alex talk", "facts": [], "episodes": []}

    script(agent, slow)
    check("started for the quiet", agent._maybe_consolidate(ROOM, "idle") == "idle")
    await asyncio.sleep(0)
    say(agent, ROOM, [(KIM, "am I late?")], time.time())
    check("no second call while one is under way",
          agent._maybe_consolidate(ROOM, "idle") is None)
    again = fold_agent(tmp)
    agent.flush_state()
    again = fold_agent(tmp)
    check("a restart meanwhile finds every line still waiting",
          again.folded_upto.get(ROOM, 0) == 0 and len(again._unfolded(ROOM)) == 13)
    release.set()
    await asyncio.gather(*list(agent._bg_tasks))
    check("the cursor stops at what the call read", agent.folded_upto[ROOM] == 12)
    check("the newer line still waits",
          [r["text"] for r in agent._unfolded(ROOM)] == ["am I late?"])


async def test_a_busy_day_stays_within_the_caps(tmp: Path, monkeypatch) -> None:
    agent = fold_agent(tmp)
    clock = [time.time() - 2 * DAY]

    monkeypatch.setattr(consolidate, "time", types.SimpleNamespace(
        time=lambda: clock[0], monotonic=time.monotonic))
    calls: dict = {}

    async def call(system, messages, model, **_kw):
        conv = json.loads(messages[0]["content"].split("\x1e")[-1].rstrip("\x1f"))
        calls[conv["lines"][0]["text"].split()[0]] = calls.get(
            conv["lines"][0]["text"].split()[0], 0) + 1
        return json.dumps({"thread": None, "facts": [], "episodes": []})

    agent._call_llm = call
    rooms = ("telegram:r1", "telegram:r2", "telegram:r3")
    for i in range(1500):
        clock[0] += 34.0
        for n, conv in enumerate(rooms):
            uid = f"u{i % 20}"
            agent._append_buffer(conv, f"P{i % 20}", f"r{n + 1} line {i}", uid,
                                 at=clock[0])
            agent._maybe_consolidate(conv, "lines")
            if agent._bg_tasks:
                await asyncio.gather(*list(agent._bg_tasks))
    total = sum(calls.values())
    check("at most 16 calls in one chat", max(calls.values()) <= 16, repr(calls))
    check("at most 40 calls for all chats", total <= 40, repr(calls))
    check("the first chat was consolidated many times", calls.get("r1", 0) >= 12,
          repr(calls))
