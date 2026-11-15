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


async def test_the_last_line_of_a_turn_is_written_without_a_later_line(tmp: Path) -> None:
    """A reply follows its question within the write interval; a stop right
    after it used to lose the reply and leave the question looking unanswered."""
    import asyncio
    from persona_agent import agent as agent_mod
    agent = make_agent(tmp)
    interval, agent_mod._RECENT_FLUSH_S = agent_mod._RECENT_FLUSH_S, 0.2
    try:
        agent._append_buffer(ROOM, "Ann", "hello", "7")
        agent._maybe_flush_recent()
        agent._append_buffer(ROOM, "Luna", "hi Ann", "")
        agent._maybe_flush_recent()
        check("held back by the interval", len(agent.chat_log.read(ROOM)) == 1)
        await asyncio.sleep(0.6)
        check("and written when it has passed, with no further line",
              [r["text"] for r in agent.chat_log.read(ROOM)] == ["hello", "hi Ann"])
        recent = agent.memory_file.with_name("recent.json").read_text(encoding="utf-8")
        check("in the recent messages too", "hi Ann" in recent)
    finally:
        agent_mod._RECENT_FLUSH_S = interval


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


async def test_a_note_forgotten_before_its_line_is_logged_keeps_it_out(tmp: Path) -> None:
    """The log is written a little after a line arrives; a forget in that
    gap must still keep the line out of the log and out of the window."""
    agent = make_agent(tmp)
    log = agent.chat_log
    log.take = lambda conv, rows: 0     # the write has not happened yet
    agent._append_buffer(ROOM, "Bob", "my pin is 9921", "52")
    agent._append_buffer(ROOM, "Bo", "cool", "9")
    del log.take
    seq = next(r["seq"] for r in agent._log_rows(ROOM) if r["text"] == "my pin is 9921")
    check("nothing is logged yet", agent.chat_log.read(ROOM) == [])
    agent._append_memory(ROOM, {"text": "Bob's pin is 9921", "time": time.time(),
                                "auto": True, "refs": [seq], "user_id": "52"})
    nid = agent.memories[ROOM][0]["id"]
    check("forgotten", agent._forget_item(ROOM, "note", nid))
    check("the line left the window",
          [r["text"] for r in agent._log_rows(ROOM)] == ["cool"])
    agent.flush_state()
    check("and the later write does not log it",
          [r["text"] for r in agent.chat_log.read(ROOM)] == ["cool"])
    check("nor keep it among the recent lines on disk",
          "9921" not in agent.memory_file.with_name("recent.json").read_text(encoding="utf-8"))


async def test_forget_this_chat_drops_the_replies_awaiting_a_reaction(tmp: Path) -> None:
    """They hold the chat's own lines as context, on disk."""
    agent = make_agent(tmp)
    page, other = "private:browser:abc", "private:telegram:7"
    for conv in (page, other):
        agent.pending_reactions.record(
            "dm:" + conv[len("private:"):], reply="noted", mode="dm",
            ctx_lines=["you: I live in Hangzhou"], ts=time.time())
    agent.pending_reactions.flush()
    agent._forget_chat(page)
    agent.pending_reactions.flush()
    kept = agent.pending_reactions.state_file.read_text(encoding="utf-8")
    check("the forgotten chat's pending replies are gone", "dm:browser:abc" not in kept, kept)
    check("another chat's stay", "dm:telegram:7" in kept, kept)


async def test_a_command_said_one_to_one_is_its_own_evidence(tmp: Path) -> None:
    agent = make_agent(tmp)
    conv = "private:telegram:7"
    name = agent.persona_name
    check("saved", agent._handle_memory_command(conv, f"{name}, remember I am allergic to peanuts",
                                                "telegram:7", "Ann"))
    note = agent.memories[conv][0]
    lines = agent.chat_log.lines(conv, note.get("refs") or [])
    check("the note cites the command itself",
          [r["text"] for r in lines] == [f"{name}, remember I am allergic to peanuts"], repr(lines))


async def test_a_line_that_shares_a_word_is_not_evidence(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent._append_buffer(ROOM, "Ann", "Ann here, I work as a nurse", "7")
    agent.flush_state()
    refs = agent._cause_refs(ROOM, "Ann works night shifts on weekends", "7")
    check("one shared name does not make a source", refs == [], repr(refs))
    refs = agent._cause_refs(ROOM, "Ann works as a nurse", "7")
    check("most of the note's words do", len(refs) == 1, repr(refs))


async def test_forgetting_a_note_spares_a_line_another_note_rests_on(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent._append_buffer(ROOM, "Ann", "I work at the aquarium and I keep bees", "7")
    agent.flush_state()
    seq = agent.chat_log.read(ROOM)[0]["seq"]
    for text in ("Ann works at the aquarium", "Ann keeps bees"):
        agent._append_memory(ROOM, {"text": text, "time": time.time(), "auto": True,
                                    "refs": [seq], "user_id": "7"})
    first = agent.memories[ROOM][0]["id"]
    check("forgotten", agent._forget_item(ROOM, "note", first))
    check("the shared line stays for the other note", len(agent.chat_log.read(ROOM)) == 1)
    check("forgotten too", agent._forget_item(ROOM, "note", agent.memories[ROOM][0]["id"]))
    check("and goes with the last note that cites it", agent.chat_log.read(ROOM) == [])


async def test_a_forget_that_removes_only_its_own_line_says_nothing_was_forgotten(
        tmp: Path) -> None:
    from persona_agent import chatlangs
    agent = make_agent(tmp)
    replies = chatlangs.spec("en").replies
    agent._append_memory(ROOM, {"text": "Ann has a parrot", "time": time.time(),
                                "user_id": "7", "user_name": "Ann"})
    agent._append_buffer(ROOM, "Bo", "Luna forget parrot", "9")
    said = agent._handle_memory_command(ROOM, "Luna forget parrot", "9", "Bo")
    check("another member's note stays", len(agent.memories[ROOM]) == 1)
    check("and the answer does not claim otherwise",
          said in replies["nothing_to_forget"], repr(said))
    check("the command's own line still leaves the window",
          [r["text"] for r in agent._log_rows(ROOM)] == [])
    agent._append_buffer(ROOM, "Bo", "my parrot bites", "9")
    agent._append_buffer(ROOM, "Bo", "Luna forget parrot", "9")
    said = agent._handle_memory_command(ROOM, "Luna forget parrot", "9", "Bo")
    check("a line of the caller's own that went counts", said in replies["forgotten"], repr(said))


async def test_a_forgotten_note_takes_the_characters_own_recital_with_it(tmp: Path) -> None:
    agent = make_agent(tmp)
    name = agent.persona_name
    for text in ("Ann works at the aquarium", "Ann keeps bees."):
        agent._append_memory(ROOM, {"text": text, "time": time.time(),
                                    "user_id": "7", "user_name": "Ann"})
    agent._append_buffer(ROOM, name, "Here is what I have:\nAnn works at the aquarium", "")
    agent._append_buffer(ROOM, "Bo", "Ann works at the aquarium, right?", "9")
    agent._append_buffer(ROOM, name, "I also have: ann keeps bees", "")
    agent._append_buffer(ROOM, "Bo", "fine", "9")
    agent._append_buffer(ROOM, name, "good morning", "")
    agent.flush_state()
    nid = next(it["id"] for it in agent.memories[ROOM] if "aquarium" in it["text"])
    check("forgotten on the page", agent._forget_item(ROOM, "note", nid))
    check("the character's line that read it back is gone; a member's line is not its to take",
          [r["text"] for r in agent.chat_log.read(ROOM)] == [
              "Ann works at the aquarium, right?", "I also have: ann keeps bees", "fine",
              "good morning"], repr(agent.chat_log.read(ROOM)))
    agent._handle_memory_command(ROOM, f"{name} forget bees", "7", "Ann")
    agent.flush_state()
    check("a forget asked in chat does the same, punctuation and case aside",
          [r["text"] for r in agent._log_rows(ROOM)] == [
              "Ann works at the aquarium, right?", "fine", "good morning"],
          repr(agent._log_rows(ROOM)))
    check("and in the log", "bees" not in agent.chat_log.path(ROOM).read_text(encoding="utf-8"))


async def test_a_note_removed_in_an_earlier_page_chat_can_be_restored_from_the_new_one(
        tmp: Path) -> None:
    """New chat gives the page a new conversation; the earlier one's notes
    still show there, so their removal must be restorable there too."""
    from persona_agent import dashboard
    agent = make_agent(tmp)
    old, new = "private:browser:aaa", "private:browser:bbb"
    agent._append_memory(old, {"text": "I have a cat called Dumpling", "time": time.time()})
    nid = agent.memories[old][0]["id"]
    check("the note reaches the new chat", [w for w, _ in agent._notes_from_rooms(new)] == [old])
    check("removed where it lives", agent._forget_item(old, "note", nid))
    shown = dashboard.conversation_payload(agent, new)["removed"]
    check("and listed as restorable in the new chat",
          [r["text"] for r in shown] == ["I have a cat called Dumpling"], repr(shown))
    check("a stranger's chat does not list it",
          dashboard.conversation_payload(agent, "private:telegram:9")["removed"] == [])
    check("restored", agent._restore(shown[0]["tid"]) == "ok")
    check("back where it was", [it["text"] for it in agent.memories[old]] == [
        "I have a cat called Dumpling"])


async def test_the_terminal_forget_reaches_the_log(tmp: Path) -> None:
    from persona_agent import memory_admin
    agent = make_agent(tmp)
    agent._append_buffer(ROOM, "Ann", "I work at the aquarium", "7")
    agent._append_buffer(ROOM, agent.persona_name, "I have: Ann works at the aquarium", "")
    agent.flush_state()
    seq = agent.chat_log.read(ROOM)[0]["seq"]
    agent._append_memory(ROOM, {"text": "Ann works at the aquarium", "time": time.time(),
                                "auto": True, "refs": [seq], "user_id": "7"})
    nid = agent.memories[ROOM][0]["id"]
    backend = memory_admin.FileBackend(agent.memory_file, agent.core_memory_file, tmp,
                                       agent.settings)
    check("the terminal forgets it", backend.forget(ROOM, "note", nid))
    check("and the line it cites, and the character's recital of it",
          agent.chat_log.read(ROOM) == [])


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
