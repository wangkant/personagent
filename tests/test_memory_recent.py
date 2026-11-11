"""The recent window on disk (recent.json): the time and number of every line
and turn, what a restart brings back, what is never kept, and a backlog that
is kept as context without being answered. No test calls a model.

Run from the repo root:

    python -m pytest tests/test_memory_recent.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from persona_agent import recent
from persona_agent.agent import Agent
from persona_agent.transport import _MAX_CONNECTOR_CONVS, SendResult

from helpers import check
from test_turns import _dm_event, _event, make_agent

ROOM = "telegram:c1"
READER = "telegram:9"
PKEY = "private:telegram:9"


def _quiet(agent: Agent) -> list:
    """Group turns pass and DMs answer "hello", without a model; returns
    the histories the DM model was given."""
    seen: list = []

    async def think(group_id, mode, text="", caller_override=None, **_kw):
        return "PASS", "", ""

    async def chat_dm(history, is_admin=False, pkey="", proactive=False,
                      proactive_cue=""):
        seen.append([dict(m) for m in history])
        return "hello", ""

    async def send_dm(user_id, text):
        return SendResult(success=True, message_ids=["out"])

    agent._think = think
    agent._chat_dm = chat_dm
    agent._send_dm = send_dm
    return seen


def _restart(tmp: Path, first: Agent, **settings) -> Agent:
    first.flush_state()
    return make_agent(tmp, **settings)


async def test_lines_and_turns_carry_the_time_they_were_sent(tmp: Path) -> None:
    agent = make_agent(tmp)
    _quiet(agent)
    said = time.time() - 120
    await agent.handle_event(_event("the trail opens at nine", 1, sender="7",
                                    name="Ann", sent_at=int(said)))
    await agent.handle_event(_event("I will bring the map", 2, sender="8",
                                    name="Bo", sent_at=int(said) + 30))
    lines = list(agent.buffers[ROOM])
    check("each line has the platform's time", [ln["t"] for ln in lines]
          == [float(int(said)), float(int(said) + 30)], repr(lines))
    check("each line has the next number", [ln["seq"] for ln in lines] == [1, 2],
          repr(lines))
    await agent.handle_event(_dm_event("is the trail open", "d1",
                                       sent_at=int(said) + 60))
    turns = agent.dm_history[READER]
    check("the reader's turn has its time and number",
          turns[0]["t"] == float(int(said) + 60) and turns[0]["seq"] == 1, repr(turns))
    check("the reply has a time and the next number",
          turns[1]["role"] == "assistant" and turns[1]["seq"] == 2
          and turns[1]["t"] >= turns[0]["t"], repr(turns))


async def test_a_line_that_grows_keeps_its_number_and_gains_an_end(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent._append_buffer("g", "Ann", "first", "7", at=1000.0)
    agent._append_buffer("g", "Ann", "second", "7", at=1060.0)
    (line,) = agent.buffers["g"]
    check("merged into one line", line["text"] == "first second", repr(line))
    check("its time, number and end", (line["t"], line["seq"], line["t1"])
          == (1000.0, 1, 1060.0), repr(line))
    agent.folded_upto["g"] = 1
    agent._append_buffer("g", "Ann", "third", "7", at=1100.0)
    check("a consolidated line takes no more words",
          [ln["text"] for ln in agent.buffers["g"]] == ["first second", "third"],
          repr(list(agent.buffers["g"])))


async def test_a_restart_brings_back_the_window(tmp: Path) -> None:
    agent = make_agent(tmp, chat_context_messages=10)
    _quiet(agent)
    for i in range(13):
        agent._append_buffer(ROOM, f"P{i % 3}", f"line {i}", str(i % 3), at=1e9 + 9e8 + i)
    check("the lines pushed out wait in the spill",
          [r["seq"] for r in agent._spill[ROOM]] == [1, 2, 3], repr(agent._spill))
    agent.folded_upto[ROOM] = 1
    agent._recent_dirty.add(ROOM)
    agent._opener_sent_at[ROOM] = 1.9e9
    agent.last_proactive_at[ROOM] = 1.9e9
    await agent.handle_event(_dm_event("my cat is called Momo", "d1"))

    async def down(*_a, **_k):
        raise RuntimeError("provider down")
    agent._chat_dm = down
    await agent.handle_event(_dm_event("are you there", "d2"))
    check("the unanswered words wait", agent._dm_unanswered.get(READER) == [
        "are you there"], repr(agent._dm_unanswered))

    again = _restart(tmp, agent)
    check("the room's lines are back",
          [ln["text"] for ln in again.buffers[ROOM]]
          == [f"line {i}" for i in range(3, 13)], repr(list(again.buffers[ROOM])))
    check("the spill and the cursor are back",
          [r["seq"] for r in again._spill[ROOM]] == [1, 2, 3]
          and again.folded_upto[ROOM] == 1, repr((again._spill, again.folded_upto)))
    again._append_buffer(ROOM, "Zed", "one more", "z")
    check("numbering goes on", again.buffers[ROOM][-1]["seq"] == 14,
          repr(again.buffers[ROOM][-1]))
    check("the reader's turns are back",
          [(m["role"], m["content"]) for m in again.dm_history[READER]]
          == [("user", "my cat is called Momo"), ("assistant", "hello")],
          repr(again.dm_history))
    check("so are the unanswered words and the reader's last activity",
          again._dm_unanswered.get(READER) == ["are you there"]
          and again.last_dm_activity_at[READER] > 0,
          repr((again._dm_unanswered, again.last_dm_activity_at)))
    check("it does not open again where an opener went unanswered",
          again._opener_sent_at.get(ROOM) == 1.9e9
          and again.last_proactive_at.get(ROOM) == 1.9e9,
          repr((again._opener_sent_at, again.last_proactive_at)))


async def test_with_keep_recent_off_nothing_is_written_and_an_old_file_goes(
        tmp: Path) -> None:
    agent = make_agent(tmp)
    agent._append_buffer(ROOM, "Ann", "hello", "7")
    agent.flush_state()
    path = tmp / "recent.json"
    check("on by default the window is written", path.is_file())
    off = make_agent(tmp, memory_keep_recent=False)
    check("off: the old file is deleted at start", not path.exists())
    check("off: nothing comes back", not off.buffers.get(ROOM), repr(off.buffers))
    off._append_buffer(ROOM, "Ann", "again", "7")
    off.flush_state()
    check("off: nothing is written", not path.exists())


async def test_a_damaged_window_file_is_set_aside_and_memory_is_untouched(
        tmp: Path) -> None:
    (tmp / "recent.json").write_text("{not json", encoding="utf-8")
    facts = json.dumps({ROOM: [{"text": "Ann likes tea", "time": 1.0}]})
    (tmp / "memory.json").write_text(facts, encoding="utf-8")
    before = (tmp / "memory.json").read_bytes()
    agent = make_agent(tmp)
    check("set aside", (tmp / "recent.json.corrupt").is_file())
    check("every chat starts empty", not agent.window_seq and not agent.dm_history)
    check("the facts are read", agent.memories[ROOM][0]["text"] == "Ann likes tea")
    agent.flush_state()
    check("a start that wrote nothing new left memory.json alone",
          (tmp / "memory.json").read_bytes() == before or json.loads(
              (tmp / "memory.json").read_text(encoding="utf-8"))[ROOM][0]["text"]
          == "Ann likes tea")


async def test_only_recent_and_at_most_256_chats_are_kept(tmp: Path) -> None:
    now = time.time()
    convs = {f"telegram:g{i}": {"seq": 1, "folded_upto": 0, "last_at": now - i,
                                "lines": [{"name": "A", "text": "hi", "user_id": "1",
                                           "t": now - i, "seq": 1}]}
             for i in range(260)}
    convs["telegram:old"] = {"seq": 1, "last_at": now - 73 * 3600, "lines": [
        {"name": "A", "text": "old", "user_id": "1", "t": now - 73 * 3600, "seq": 1}]}
    (tmp / "recent.json").write_text(json.dumps({"format": 1, "convs": convs}),
                                     encoding="utf-8")
    agent = make_agent(tmp)
    check("past 72 hours a chat is not restored", "telegram:old" not in agent.window_seq)
    check("at most 256 chats, the newest", len(agent.window_seq) == recent.MAX_CONVS
          and "telegram:g0" in agent.window_seq and "telegram:g259" not in agent.window_seq,
          repr(len(agent.window_seq)))


async def test_an_evicted_conversation_comes_back_with_its_lines(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent._append_buffer("tg:0", "Ann", "we meet at nine", "7")
    agent._append_buffer("tg:0", "Bo", "I bring the map", "8")
    agent._touch_connector_conv("tg:0")
    for i in range(1, _MAX_CONNECTOR_CONVS + 2):
        agent._touch_connector_conv(f"tg:{i}")
    check("evicted from memory", "tg:0" not in agent.buffers
          and "tg:0" not in agent.window_seq)
    saved = json.loads((tmp / "recent.json").read_text(encoding="utf-8"))["convs"]
    check("written to disk on the way out",
          [ln["text"] for ln in saved["tg:0"]["lines"]]
          == ["we meet at nine", "I bring the map"], repr(saved.get("tg:0")))
    agent._append_buffer("tg:0", "Ann", "see you", "7")
    check("back with its lines, numbered on",
          [(ln["text"], ln["seq"]) for ln in agent.buffers["tg:0"]]
          == [("we meet at nine", 1), ("I bring the map", 2), ("see you", 3)],
          repr(list(agent.buffers["tg:0"])))


async def test_the_page_chat_reads_the_pages_copy_once(tmp: Path) -> None:
    agent = make_agent(tmp)
    seen = _quiet(agent)
    page = tmp / "desktop" / "browser-chat.json"
    page.parent.mkdir()
    page.write_text(json.dumps({"conversation": "abc", "messages": [
        {"role": "user", "text": "I like tea", "seq": 1},
        {"role": "assistant", "text": "Noted.", "seq": 2},
        {"role": "assistant", "picture": "x.png", "seq": 3},
        {"role": "user", "text": "and now?", "seq": 4}]}), encoding="utf-8")
    payload = {"post_type": "message", "message_type": "private",
               "user_id": "browser:abc", "message_id": "p1",
               "sender": {"nickname": "you"}, "raw_message": "and now?",
               "message": [{"type": "text", "data": {"text": "and now?"}}]}
    await agent._handle_dm("browser:abc", payload, is_admin=True)
    check("the earlier turns come from the page's copy, the waiting words once",
          [(m["role"], m["content"]) for m in seen[0]]
          == [("user", "I like tea"), ("assistant", "Noted."), ("user", "and now?")],
          repr(seen))
    agent.dm_history.pop("browser:abc")
    await agent._handle_dm("browser:abc", {**payload, "message_id": "p2"},
                           is_admin=True)
    check("read only once", [m["content"] for m in seen[1]] == ["and now?"],
          repr(seen[1]))


async def test_turns_go_to_the_model_with_role_and_content_only(tmp: Path) -> None:
    agent = make_agent(tmp)
    seen = _quiet(agent)
    await agent.handle_event(_dm_event("first", "d1"))
    await agent.handle_event(_dm_event("second", "d2"))
    history = seen[-1]
    check("the stored turns carry times", all("t" in m for m in history), repr(history))
    prompt = agent._build_dm_prompt(history, is_admin=False, pkey=PKEY)
    check("what the model is sent carries role and content only",
          all(set(m) <= {"role", "content"} for m in prompt.messages),
          repr(prompt.messages))


async def test_a_backlog_call_is_kept_as_context_and_not_answered(tmp: Path) -> None:
    agent = make_agent(tmp)
    calls: list = []

    async def think(group_id, mode, text="", caller_override=None, **_kw):
        calls.append(text)
        return "on my way", "", ""

    async def send(group_id, text, at_user_id=""):
        return SendResult(success=True)

    agent._think, agent._send_group = think, send
    old = int(time.time()) - 3600
    out = await agent.handle_event(_event("are you coming", 1, sender="7", name="Ann",
                                          at_bot=True, sent_at=old))
    check("an hour-old call opens no turn", calls == [] and out["handled"] is False,
          repr((calls, out)))
    check("it is in the window, with its own time",
          agent.buffers[ROOM][-1]["t"] == float(old), repr(list(agent.buffers[ROOM])))
    await agent.handle_event(_event("are you coming now", 2, sender="7", name="Ann",
                                    at_bot=True, sent_at=int(time.time()) - 60))
    check("a call of a minute ago is answered", len(calls) == 1, repr(calls))
