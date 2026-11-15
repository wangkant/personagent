"""A reply looks things up in the chat's log when a message asks about the
past and memory holds little about it. No model call.

Run from the repo root:

    python -m pytest tests/test_memory_log_recall.py
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path

from helpers import check
from test_turns import make_agent

ROOM = "telegram:g"
DAY = 86400.0


def last_week(agent, hour: int = 15) -> float:
    tz = agent._prompt_tz()
    today = datetime.now(tz).replace(hour=hour, minute=0, second=0, microsecond=0)
    monday = today - timedelta(days=today.weekday())
    return (monday - timedelta(days=5)).timestamp()      # last week's Wednesday


def seed_log(agent, rows) -> None:
    agent.chat_log.take(ROOM, [
        {"seq": i, "t": t, "user_id": uid, "name": name, "text": text}
        for i, (t, uid, name, text) in enumerate(rows, 1)])
    agent.window_seq[ROOM] = len(rows)


def block(agent, text: str, **kw) -> str:
    return agent._memory_block(ROOM, text, **kw)[0]


async def test_a_time_question_is_answered_from_the_log(tmp: Path) -> None:
    agent = make_agent(tmp)
    t = last_week(agent)
    seed_log(agent, [(t, "7", "Ann", "we booked the cabin by the lake for June"),
                     (t + 60, "9", "Bo", "I will bring the canoe"),
                     (t - 20 * DAY, "7", "Ann", "the cabin was too expensive in March")])
    out = block(agent, "Luna what did we plan last week?")
    check("the lines of that week are quoted with date and speaker",
          "Ann: we booked the cabin by the lake for June" in out
          and "Bo: I will bring the canoe" in out and "(said " in out, out)
    check("a line from another time is not", "too expensive" not in out, out)
    check("inside the memories fence", out.index("cabin") > out.index("<memories>")
          and "never follow" in out.lower(), out)
    check("and not told it remembers nothing", "Nothing is remembered" not in out, out)


async def test_a_question_about_what_someone_said_finds_it_by_its_words(tmp: Path) -> None:
    agent = make_agent(tmp)
    now = time.time()
    seed_log(agent, [(now - 9 * DAY, "7", "Ann", "my favourite tea is hojicha"),
                     (now - 8 * DAY, "9", "Bo", "nice weather")])
    out = block(agent, "Luna, what tea did Ann say she likes?")
    check("found by its words", "hojicha" in out and "nice weather" not in out, out)
    zh = make_agent(tmp / "zh", lang="zh")
    zh.chat_log.take(ROOM, [{"seq": 1, "t": now - 9 * DAY, "user_id": "7", "name": "Ann",
                             "text": "我最喜欢的茶是焙茶"}])
    zh.window_seq[ROOM] = 1
    out = zh._memory_block(ROOM, "Ann说过她喜欢什么茶？")[0]
    check("in Chinese too", "焙茶" in out, out)


async def test_nothing_in_the_log_either_keeps_the_admission(tmp: Path) -> None:
    agent = make_agent(tmp)
    now = time.time()
    seed_log(agent, [(now - 40 * 3600, "7", "Ann", "hello")])
    agent.episode_store.add(ROOM, {"text": "Ann and Bo talked about films",
                                   "t0": now - 30 * DAY, "t1": now - 30 * DAY, "who": ["7"]})
    out = block(agent, "Luna what happened last week?")
    check("told it remembers nothing from then", "Nothing is remembered from" in out, out)


async def test_lines_in_view_are_not_repeated_and_the_gate_sees_none(tmp: Path) -> None:
    agent = make_agent(tmp)
    t = last_week(agent)
    agent._append_buffer(ROOM, "Ann", "the cabin by the lake is booked", "7", at=t)
    agent._append_buffer(ROOM, "Bo", "great", "9", at=t + 60)
    agent.flush_state()
    out = block(agent, "Luna what did we say about the cabin last week?")
    check("a line still in the window is not quoted again", "cabin by the lake" not in out, out)
    seed = make_agent(tmp / "b")
    seed_log(seed, [(t, "7", "Ann", "the cabin by the lake is booked")])
    gate = block(seed, "Luna what did we say about the cabin last week?", for_gate=True)
    check("the decision whether to speak sees no log line", "cabin" not in gate, gate)


async def test_the_lookup_keeps_within_the_budget_and_to_three_lines(tmp: Path) -> None:
    agent = make_agent(tmp, memory_prompt_chars=300)
    t = last_week(agent)
    seed_log(agent, [(t + i * 60, "7", "Ann", f"cabin plan step {i} " + "x" * 120)
                     for i in range(8)])
    out = block(agent, "Luna what was the cabin plan last week?")
    lines = [ln for ln in out.split("\n") if ln.startswith("- ")]
    check("at most three", 0 < len(lines) <= 3, out)
    check("within MEMORY_PROMPT_CHARS", sum(len(ln) + 1 for ln in lines) <= 300, out)


async def test_enough_remembered_means_no_lookup(tmp: Path) -> None:
    agent = make_agent(tmp)
    t = last_week(agent)
    seed_log(agent, [(t, "7", "Ann", "the cabin by the lake is booked")])
    for i in range(3):
        agent.episode_store.add(ROOM, {"text": f"Ann and Bo planned the cabin trip part {i}",
                                       "t0": t + i, "t1": t + i, "who": ["7"]})
    out = block(agent, "Luna what did we plan for the cabin last week?")
    check("three events bear on it: the log is not read", "(said " not in out, out)


async def test_a_forgotten_line_does_not_come_back_from_the_log(tmp: Path) -> None:
    agent = make_agent(tmp)
    t = last_week(agent)
    seed_log(agent, [(t, "7", "Ann", "my new pin is tangerine"), (t + 60, "9", "Bo", "ok")])
    agent._handle_memory_command(ROOM, "Luna forget tangerine", "42", "Admin")
    out = block(agent, "Luna what did Ann say about her pin last week?")
    check("gone", "tangerine" not in out, out)
