"""The chat log (chatlog.py): each chat's lines on disk for MEMORY_LOG_DAYS,
searchable, cited by notes, and reached by every forget.

Run from the repo root:

    python -m pytest tests/test_memory_log.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from persona_agent import chatlog

from helpers import check
from test_turns import make_agent

ROOM = "telegram:g"
OTHER = "telegram:h"
DAY = 86400.0


def row(seq: int, text: str, uid: str = "7", name: str = "Ann", t: float = 0.0) -> dict:
    return {"seq": seq, "t": t or time.time(), "user_id": uid, "name": name, "text": text}


def log_of(tmp: Path, **kw) -> chatlog.ChatLog:
    return chatlog.ChatLog(tmp / "log", **kw)


# ---- the store ---------------------------------------------------------------

def test_lines_are_appended_once_and_a_grown_line_is_read_at_its_newest(tmp: Path) -> None:
    log = log_of(tmp)
    check("two new lines taken", log.take(ROOM, [row(1, "hi"), row(2, "tea?")]) == 2)
    check("nothing new: nothing taken", log.take(ROOM, [row(1, "hi"), row(2, "tea?")]) == 0)
    check("the newest grew: taken again", log.take(ROOM, [row(2, "tea? green")]) == 1)
    check("read keeps the grown text once",
          [r["text"] for r in log.read(ROOM)] == ["hi", "tea? green"], repr(log.read(ROOM)))
    again = log_of(tmp)
    check("a new process knows where it stopped", again.take(ROOM, [row(2, "tea? green")]) == 0
          and again.last_seq(ROOM) == 2)


def test_a_chat_key_never_names_a_path(tmp: Path) -> None:
    log = log_of(tmp)
    for key in ("../../evil", "a/b\\c", "C:\\x", "\x00", "telegram:../../.."):
        log.take(key, [row(1, "x")])
    files = list((tmp / "log").iterdir())
    check("every file sits in the log folder, named by a hash",
          all(f.parent == tmp / "log" and len(f.stem) == 32 for f in files
              if f.suffix == ".jsonl"), repr(files))
    check("nothing outside it", not (tmp / "evil").exists() and not (tmp.parent / "evil").exists())


def test_a_write_cut_short_is_skipped_and_the_next_one_lands_whole(tmp: Path) -> None:
    log = log_of(tmp)
    log.take(ROOM, [row(1, "hi")])
    with open(log.path(ROOM), "ab") as fh:
        fh.write(b'{"seq": 2, "t": 1, "te')
    fresh = log_of(tmp)
    check("the fragment is skipped", [r["seq"] for r in fresh.read(ROOM)] == [1])
    fresh.take(ROOM, [row(2, "again")])
    check("the next line is read whole", [r["text"] for r in fresh.read(ROOM)] == ["hi", "again"])


def test_old_lines_and_lines_past_the_cap_are_pruned(tmp: Path) -> None:
    now = time.time()
    log = log_of(tmp, days=30, max_lines=3)
    log._append(ROOM, [row(1, "old", t=now - 31 * DAY)] + [
        row(i, f"line {i}", t=now - 60 + i) for i in range(2, 7)])
    log._append(OTHER, [row(1, "very old", t=now - 40 * DAY)])
    check("pruned: the old line and two past the cap", log.prune(now) == 3 + 1)
    check("the newest three stay", [r["seq"] for r in log.read(ROOM)] == [4, 5, 6])
    check("a chat with nothing left loses its file", not log.path(OTHER).exists())
    check("a line older than the days is not taken at all",
          log.take(OTHER, [row(2, "stale", t=now - 31 * DAY)]) == 1
          and not log.read(OTHER))


def test_search_by_words_by_speaker_and_by_time(tmp: Path) -> None:
    now = time.time()
    log = log_of(tmp)
    log.take(ROOM, [row(1, "I adopted a cat named Miso", "7", "Ann", now - 5 * DAY),
                    row(2, "nice weather today", "9", "Bo", now - 4 * DAY),
                    row(3, "Miso knocked over my plant", "7", "Ann", now - DAY),
                    row(4, "我下周去杭州出差", "9", "Bo", now - 3600)])
    check("words, best first",
          [r["seq"] for r in log.search(ROOM, "Miso the cat")][:1] == [1])
    check("Chinese words", [r["seq"] for r in log.search(ROOM, "杭州")] == [4])
    check("by speaker", [r["seq"] for r in log.search(ROOM, speakers=["9"])] == [4, 2])
    check("by time", [r["seq"] for r in log.search(ROOM, since=now - 2 * DAY)] == [4, 3])
    check("lines asked to skip stay out",
          [r["seq"] for r in log.search(ROOM, "Miso", skip=[1])] == [3])
    check("words that make no token find nothing", log.search(ROOM, "a") == [])
    check("bounded", len(log.search(ROOM, limit=999)) <= chatlog.SEARCH_MAX)


def test_a_forgotten_newest_line_is_not_logged_again(tmp: Path) -> None:
    log = log_of(tmp)
    log.take(ROOM, [row(1, "hi"), row(2, "my secret")])
    check("one line forgotten", log.forget(ROOM, lambda r: "secret" in r["text"]) == 1)
    check("gone from reads", [r["text"] for r in log.read(ROOM)] == ["hi"])
    check("not in the file", "secret" not in log.path(ROOM).read_text(encoding="utf-8"))
    again = log_of(tmp)
    check("a new process does not log it again from the window",
          again.take(ROOM, [row(1, "hi"), row(2, "my secret")]) == 0
          and [r["text"] for r in again.read(ROOM)] == ["hi"])


def test_refs_are_read_defensively() -> None:
    check("ints only, positive, unique, bounded",
          chatlog.refs_of({"refs": [3, "4", -1, True, 3, 5, 6, 7, 8, 9, 10]}) == [3, 5, 6, 7, 8, 9])
    check("absent or malformed is none", chatlog.refs_of({}) == [] == chatlog.refs_of(
        {"refs": "1,2"}) == chatlog.refs_of(None))


# ---- the agent's log ---------------------------------------------------------

async def test_the_agent_logs_a_rooms_lines_with_the_windows_numbers(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent._append_buffer(ROOM, "Ann", "hello", "7")
    agent._append_buffer(ROOM, "Luna", "hi Ann", "")
    agent.flush_state()
    rows = agent.chat_log.read(ROOM)
    check("both lines, with the window's seq",
          [(r["seq"], r["text"]) for r in rows] == [
              (r["seq"], r["text"]) for r in agent.buffers[ROOM]], repr(rows))
    check("the character's own line is marked", rows[1].get("self") and not rows[0].get("self"))
    check("in runtime/log beside memory.json", agent.chat_log.folder == tmp / "log")


async def test_numbers_stay_ahead_of_the_log_when_the_window_file_is_lost(tmp: Path) -> None:
    agent = make_agent(tmp)
    for i in range(3):
        agent._append_buffer(ROOM, "Ann" if i % 2 else "Cy", f"line {i}", str(i % 2))
    agent.flush_state()
    (tmp / "recent.json").unlink()
    again = make_agent(tmp)
    again._append_buffer(ROOM, "Bo", "new line", "9")
    again.flush_state()
    check("the new line gets a new number and is logged",
          [r["text"] for r in again.chat_log.read(ROOM)][-1] == "new line"
          and again.chat_log.last_seq(ROOM) == 4)


async def test_no_log_when_off_and_an_old_one_goes(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent._append_buffer(ROOM, "Ann", "hello", "7")
    agent.flush_state()
    check("on by default", agent.chat_log.path(ROOM).is_file())
    off = make_agent(tmp, memory_log_days=0)
    check("MEMORY_LOG_DAYS=0: the old log is deleted at start",
          not off.chat_log.path(ROOM).exists())
    off._append_buffer(ROOM, "Ann", "again", "7")
    off.flush_state()
    check("and nothing is written", not off.chat_log.path(ROOM).exists())
    quiet = make_agent(tmp / "b", memory_keep_recent=False)
    quiet._append_buffer(ROOM, "Ann", "hello", "7")
    quiet.flush_state()
    check("MEMORY_KEEP_RECENT=false keeps no log either", not quiet.chat_log.on
          and not (tmp / "b" / "log").exists())


async def test_a_paused_group_leaves_nothing_in_the_log(tmp: Path) -> None:
    from test_turns import _group
    agent = make_agent(tmp, access_paused_groups=("123",))
    await agent.handle_event(_group("hello there", "m1", group="123"))
    agent.flush_state()
    check("no line of it is logged", not (tmp / "log").exists()
          or not any((tmp / "log").glob("*.jsonl")))


async def test_a_forget_in_chat_removes_the_lines_from_the_log(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent._append_buffer(ROOM, "Ann", "my pin is tangerine", "7")
    agent._append_buffer(ROOM, "Bo", "ok", "9")
    agent.flush_state()
    agent._handle_memory_command(ROOM, "Luna forget tangerine", "42", "Admin")
    agent.flush_state()
    check("gone from the log", "tangerine" not in agent.chat_log.path(ROOM).read_text(
        encoding="utf-8"))
    check("and from the search", agent.chat_log.search(ROOM, "tangerine") == [])
    check("the rest stays", [r["text"] for r in agent.chat_log.read(ROOM)] == ["ok"])


async def test_forget_this_chat_removes_its_log_and_no_other(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent._append_buffer(ROOM, "Ann", "hello", "7")
    agent._append_buffer(OTHER, "Ann", "hello", "7")
    agent.flush_state()
    agent._forget_chat(ROOM)
    agent.flush_state()
    check("the chat's log is gone", not agent.chat_log.path(ROOM).exists())
    check("the other chat's stays", agent.chat_log.path(OTHER).is_file())


async def test_forgetting_one_note_removes_the_lines_it_cites(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent._append_buffer(ROOM, "Ann", "I work at the aquarium", "7")
    agent._append_buffer(ROOM, "Bo", "cool", "9")
    agent.flush_state()
    seq = agent.chat_log.read(ROOM)[0]["seq"]
    agent._append_memory(ROOM, {"text": "Ann works at the aquarium", "time": time.time(),
                                "auto": True, "refs": [seq], "user_id": "7"})
    nid = agent.memories[ROOM][0]["id"]
    check("forgotten", agent._forget_item(ROOM, "note", nid))
    check("the cited line left the log",
          [r["text"] for r in agent.chat_log.read(ROOM)] == ["cool"])


async def test_the_terminal_forget_reaches_the_log(tmp: Path) -> None:
    from persona_agent import memory_admin
    agent = make_agent(tmp)
    agent._append_buffer(ROOM, "Ann", "I work at the aquarium", "7")
    agent.flush_state()
    seq = agent.chat_log.read(ROOM)[0]["seq"]
    agent._append_memory(ROOM, {"text": "Ann works at the aquarium", "time": time.time(),
                                "auto": True, "refs": [seq], "user_id": "7"})
    nid = agent.memories[ROOM][0]["id"]
    backend = memory_admin.FileBackend(agent.memory_file, agent.core_memory_file, tmp,
                                       agent.settings)
    check("the terminal forgets it", backend.forget(ROOM, "note", nid))
    check("and the line it cites", agent.chat_log.read(ROOM) == [])


def test_a_backup_never_holds_the_log(tmp: Path) -> None:
    from persona_agent.panels import desk
    home = tmp / "home"
    (home / "runtime" / "log").mkdir(parents=True)
    (home / "runtime" / "log" / "x.jsonl").write_text(json.dumps(row(1, "hi")), encoding="utf-8")
    (home / "runtime" / "memory.json").write_text("{}", encoding="utf-8")
    d = desk.Desk.__new__(desk.Desk)
    d.home = home
    d._roots = lambda: {"runtime": home / "runtime"}
    members = [name for _p, name in d._members()]
    check("memory is in the backup, the log is not",
          "runtime/memory.json" in members and not any("log/" in m for m in members),
          repr(members))
