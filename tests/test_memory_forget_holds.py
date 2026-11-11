"""A forget holds against everything in flight and everything stored: a
consolidation under way, the running summary, older versions in the trash,
the daily copies and the migration copy. Every answer is scripted.

Run from the repo root:

    python -m pytest tests/test_memory_forget_holds.py
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from persona_agent import memstore

from helpers import check
from test_memory_fold import ALEX, ROOM, SAM, fold_agent, note, say, script


def _files(agent) -> list[Path]:
    """Every file under the agent's memory folder, copies included."""
    return [p for p in agent.memory_file.parent.rglob("*") if p.is_file()]


def _holding(agent, word: str) -> list[str]:
    return sorted(p.name for p in _files(agent)
                  if word in p.read_text(encoding="utf-8", errors="replace"))


async def _fold_in_flight(agent, forget) -> None:
    """Start a fold whose model answers only after `forget` ran under the lock."""
    say(agent, ROOM, [(SAM, "my home address is 12 Elm Street"), (ALEX, "we hike on Saturday"),
                      (SAM, "Saturday works for me")], time.time() - 2 * 3600)
    inp = agent._fold_input(ROOM, "idle")
    sam = inp.lines["L1"]["speaker"]
    gate = asyncio.Event()

    async def slow():
        await gate.wait()
        return {"thread": "Sam lives at 12 Elm Street; a hike on Saturday",
                "facts": [{"op": "add", "about": sam, "text": "Sam's home address is 12 Elm Street",
                           "imp": 4, "src": ["L1"]}],
                "episodes": [{"op": "add", "text": "Sam and Alex planned a hike on Saturday",
                              "imp": 3, "src": ["L2", "L3"]}]}
    script(agent, slow)
    agent._folding.add(ROOM)
    task = asyncio.ensure_future(agent._fold(ROOM, "idle", inp))
    await asyncio.sleep(0)
    async with agent.locks[ROOM]:
        forget()
    gate.set()
    await task


async def test_forget_this_chat_during_a_fold_is_not_undone(tmp: Path) -> None:
    agent = fold_agent(tmp)
    await _fold_in_flight(agent, lambda: agent._forget_chat(ROOM))
    check("no fact", not agent.memories.get(ROOM), repr(agent.memories.get(ROOM)))
    check("no event, no summary", not agent.episode_store.episodes(ROOM)
          and not agent.episode_store.thread(ROOM))
    check("nothing on disk holds it", _holding(agent, "Elm") == [], repr(_holding(agent, "Elm")))


async def test_a_chat_forget_during_a_fold_is_not_undone(tmp: Path) -> None:
    agent = fold_agent(tmp)
    replies = []
    await _fold_in_flight(agent, lambda: replies.append(agent._handle_memory_command(
        ROOM, "Luna, forget Elm Street", "s", "Sam")))
    check("the forget ran", replies and replies[0] is not None)
    texts = [it["text"] for it in agent.memories.get(ROOM, [])]
    thread = (agent.episode_store.thread(ROOM) or {}).get("text", "")
    check("nothing of it came back", not any("Elm" in t for t in texts) and "Elm" not in thread,
          repr((texts, thread)))


async def test_a_page_forget_during_a_fold_is_not_undone(tmp: Path) -> None:
    agent = fold_agent(tmp)
    agent.memories[ROOM] = [note("Sam's home address is 12 Elm Street", SAM)]
    gone = agent.memories[ROOM][0]["id"]
    await _fold_in_flight(agent, lambda: agent._forget_item(ROOM, "note", gone))
    check("the forgotten fact stays gone",
          not any("Elm" in it["text"] for it in agent.memories.get(ROOM, [])),
          repr(agent.memories.get(ROOM)))
    check("and is not written into the summary",
          "Elm" not in (agent.episode_store.thread(ROOM) or {}).get("text", ""))


async def test_the_summary_respects_what_was_forgotten(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(ALEX, "Sam told me his salary is 9000 a month"), (SAM, "ok whatever"),
                      (ALEX, "we hike on Saturday")], time.time() - 2 * 3600)
    agent.memories[ROOM] = [note("Sam's salary is 9000 a month", SAM)]
    agent._handle_memory_command(ROOM, "Luna, forget salary", "s", "Sam")
    inp = agent._fold_input(ROOM, "idle")
    script(agent, {"thread": "Alex says Sam's salary is 9000 a month. A hike on Saturday.",
                   "facts": []})
    await agent._fold(ROOM, "idle", inp)
    thread = (agent.episode_store.thread(ROOM) or {}).get("text", "")
    check("the forgotten sentence is not in the summary", "salary" not in thread, thread)
    check("the rest is", "hike on Saturday" in thread, thread)


def test_a_chat_forget_also_empties_the_trash_of_it(tmp: Path) -> None:
    agent = fold_agent(tmp)
    old = note("Sam lives at 12 Elm Street flat 3", SAM)
    tid = agent._trash_put(ROOM, "note", old, "replaced", "fold", ref=old["id"])
    keep = note("Sam likes tea", SAM)
    other = agent._trash_put(ROOM, "note", keep, "ended", "fold")
    agent.memories[ROOM] = [dict(old, text="Sam lives at 12 Elm Street")]
    agent._handle_memory_command(ROOM, "Luna, forget Elm Street", "s", "Sam")
    check("no older version left to restore",
          [r["text"] for r in agent._removed_items(ROOM)] == ["Sam likes tea"],
          repr(agent._removed_items(ROOM)))
    check("restore refuses it", agent._restore(tid) == "gone")
    check("the trash file no longer holds it", "Elm" not in agent.memory_trash.path.read_text(
        encoding="utf-8"))
    check("what was not asked for is still restorable", agent._restore(other) == "ok")


def test_a_chat_forget_leaves_no_copy_on_disk(tmp: Path) -> None:
    agent = fold_agent(tmp)
    agent.memories[ROOM] = [note("Sam lives at 12 Elm Street", SAM), note("Sam likes tea", SAM)]
    agent._save_memories()
    agent.memory_state.data["bak_day"] = {}
    agent.memories[ROOM].append(note("Sam has a cat", SAM))
    agent._save_memories()
    check("the daily copy was made", agent.memory_file.with_name("memory.json.bak").is_file())
    agent._handle_memory_command(ROOM, "Luna, forget Elm Street", "s", "Sam")
    check("no file holds it", _holding(agent, "Elm") == [], repr(_holding(agent, "Elm")))
    check("the copy still holds the rest", "Sam likes tea" in agent.memory_file.with_name(
        "memory.json.bak").read_text(encoding="utf-8"))


def test_forget_this_chat_leaves_no_copy_on_disk(tmp: Path) -> None:
    agent = fold_agent(tmp)
    agent.memories[ROOM] = [note("Sam lives at 12 Elm Street", SAM)]
    agent.memories["telegram:keep"] = [note("Kim likes tea")]
    agent._save_memories()
    agent.core_memory[ROOM] = "Sam's street is Elm Street."
    agent._save_core_memory()
    agent.episode_store.add(ROOM, {"t0": 1.0, "t1": 2.0, "text": "Sam showed Elm Street"})
    agent._save_episodes()
    agent.memory_state.data["bak_day"] = {}
    agent._save_memories()
    agent._save_core_memory()
    agent._save_episodes()
    check("the daily copies were made", all(
        p.with_name(p.name + ".bak").is_file() for p in (
            agent.memory_file, agent.core_memory_file, agent.episode_store.path)))
    agent._forget_chat(ROOM)
    check("no file holds it", _holding(agent, "Elm") == [], repr(_holding(agent, "Elm")))
    check("other chats are kept in the copy", "Kim likes tea" in agent.memory_file.with_name(
        "memory.json.bak").read_text(encoding="utf-8"))


def test_the_migration_copy_forgets_too(tmp: Path) -> None:
    path = tmp / "memory.json"
    path.write_text(json.dumps({ROOM: [{"text": "Sam lives at 12 Elm Street", "user_id": "s",
                                        "user_name": "Sam", "time": 1.0}],
                                "telegram:keep": [{"text": "Kim likes tea", "time": 1.0}]}),
                    encoding="utf-8")
    agent = fold_agent(tmp)
    pre = path.with_name("memory.json" + memstore.PRE_V2_SUFFIX)
    check("the migration made its copy", pre.is_file() and "Elm" in pre.read_text(
        encoding="utf-8"))
    agent._handle_memory_command(ROOM, "Luna, forget Elm Street", "s", "Sam")
    check("the copy no longer holds it", "Elm" not in pre.read_text(encoding="utf-8"))
    check("nor the rest of it", "Kim likes tea" in pre.read_text(encoding="utf-8"))
    agent._forget_chat("telegram:keep")
    check("forget this chat empties it there too",
          "Kim likes tea" not in pre.read_text(encoding="utf-8"))
