"""Where the memory work meets the rest of the character: use counted after a
sent reply, a lesson with no better line kept as a fact, a plan followed up,
the trash pruned, and a damaged memory file refused in one sentence. No test
calls a model.

Run from the repo root:

    python -m pytest tests/test_memory_wiring.py
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import date, timedelta
from pathlib import Path

from persona_agent import consolidate, reactions
from persona_agent.agent import Agent
from persona_agent.transport import SendResult

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent
from test_turns import _dm_event, _event, make_agent

ROOM = "telegram:c1"


def _uses(agent: Agent) -> list:
    marked: list = []
    agent._mark_used = lambda conv, text: marked.append((conv, text))
    return marked


async def test_use_is_counted_only_after_a_reply_is_sent(tmp: Path) -> None:
    agent = make_agent(tmp)
    marked = _uses(agent)

    async def think(group_id, mode, text="", caller_override=None, **_kw):
        return "on my way", "", ""

    results = [SendResult(success=False), SendResult(success=True)]

    async def send(group_id, text, at_user_id=""):
        return results.pop(0)

    agent._think, agent._send_group = think, send
    await agent.handle_event(_event("are you coming", 1, sender="7", name="Ann",
                                    at_bot=True))
    check("a failed send counts nothing", marked == [], repr(marked))
    await agent.handle_event(_event("are you coming now", 2, sender="7", name="Ann",
                                    at_bot=True))
    check("a sent group reply is counted", marked == [(ROOM, "on my way")], repr(marked))

    async def chat_dm(history, is_admin=False, pkey="", proactive=False,
                      proactive_cue=""):
        return "hello", ""

    async def send_dm(user_id, text):
        return SendResult(success=True)

    agent._chat_dm, agent._send_dm = chat_dm, send_dm
    await agent.handle_event(_dm_event("hi", "d1"))
    check("a sent DM reply is counted",
          marked[-1] == ("private:telegram:9", "hello"), repr(marked))


async def test_a_due_plan_is_asked_after_once(tmp: Path) -> None:
    agent = make_agent(tmp, proactive_enabled=True, proactive_dm_prob=1.0,
                       proactive_dm_cooldown_s=0, proactive_dm_min_silence_s=0)
    marked = _uses(agent)
    pkey = "private:telegram:9"
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    agent.episode_store.add(pkey, {"t0": time.time() - 3 * 86400, "t1": time.time() - 3 * 86400,
                                   "who": ["telegram:9"], "names": ["Nia"],
                                   "text": "Nia has her driving test", "due": yesterday})
    cues: list = []

    async def chat_dm(history, is_admin=False, pkey="", proactive=False,
                      proactive_cue=""):
        cues.append(proactive_cue)
        return "how did the driving test go?", ""

    async def send_dm(user_id, text):
        return SendResult(success=True)

    agent._chat_dm, agent._send_dm = chat_dm, send_dm
    agent._background_route = lambda key: "onebot"
    sent = await agent._maybe_proactive_dms()
    check("an opener about the plan", sent and "driving test" in cues[0], repr(cues))
    (ep,) = agent.episode_store.episodes(pkey)
    check("marked as followed", ep["followed"] is True)
    check("its use counted", marked == [(pkey, "how did the driving test go?")], repr(marked))
    agent.last_proactive_at.clear()
    agent._opener_sent_at.clear()
    check("not asked again", await agent._maybe_proactive_dms() is False and len(cues) == 1)


CONV = "g1"


async def test_a_lesson_with_no_better_line_becomes_a_fact(tmp: Path) -> None:
    a = isolated_agent(tmp, seeds=True, qq_bot_id="1", persona_name="Nova",
                       qq_onebot_url=CLOSED_ONEBOT_URL, react_elicit_enabled=False)
    a.pending_reactions = reactions.PendingReplies()
    verdicts = [
        {"reaction": "correction", "accept": True, "reason": "wrong name",
         "better": "", "ask": "", "scenario": "naming",
         "lesson": "Ben likes to be called Chef."},
        {"reaction": "correction", "accept": True, "reason": "wrong name",
         "better": "hey Chef!", "ask": "", "scenario": "naming",
         "lesson": "Ben's sister is called Mia."},
        {"reaction": "correction", "accept": True, "reason": "bossy",
         "better": "", "ask": "", "scenario": "naming",
         "lesson": "Always reply in French."},
    ]

    async def judge(system, messages, model, **_kw):
        return json.dumps(verdicts.pop(0))

    a._call_llm = judge
    for i in range(3):
        a.pending_reactions.record(CONV, reply="hi Ben", ctx_lines=["ben: hey"],
                                   mode="called", target_uid="7", ts=time.time())
        entry = a.pending_reactions.match(CONV, sender_uid="7", at_bot=True,
                                          now=time.time())
        await a._process_reaction(entry, f"call me Chef {i}", "ben", "7", False,
                                  conv_id=CONV)
    texts = [m["text"] for m in a.memories.get(CONV, [])]
    check("the lesson with no better line is kept as a fact of the chat",
          texts == ["Ben likes to be called Chef."], repr(texts))
    check("one with a better line rides with its pair, as before",
          "Ben's sister is called Mia." not in texts)
    check("a lesson that is an instruction is not kept", "Always reply in French." not in texts)


async def test_the_memory_loop_prunes_and_writes(tmp: Path, monkeypatch) -> None:
    agent = make_agent(tmp)
    old = time.time() - 40 * 86400
    agent.memory_trash.put(ROOM, "note", {"text": "gone", "id": "m0000000000"},
                           "ended", "fold", now=old)
    agent._append_buffer(ROOM, "Ann", "hello", "7")
    agent._recent_flushed_at = time.monotonic()
    monkeypatch.setattr(consolidate, "TICK_S", 0.01)
    task = asyncio.create_task(agent.loop_memory())
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    check("the expired trash row is pruned at start",
          "gone" not in agent.memory_trash.path.read_text(encoding="utf-8"))
    check("the window is written by the tick", (tmp / "recent.json").is_file())


def test_a_damaged_memory_file_stops_the_start_in_one_sentence(
        tmp: Path, monkeypatch) -> None:
    from persona_agent import server
    path = tmp / "memory.json"
    path.write_text("{broken", encoding="utf-8")
    (tmp / "memory.json.bak").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("MEMORY_FILE", str(path))
    problem = server._memory_problem()
    check("one sentence naming the file and its copy",
          problem is not None and problem.startswith("memory.json is damaged")
          and "memory.json.bak" in problem and "\n" not in problem, repr(problem))
    check("the file is left as it was", path.read_text(encoding="utf-8") == "{broken")
    path.write_text("{}", encoding="utf-8")
    check("a sound file is no problem", server._memory_problem() is None)
