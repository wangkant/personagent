"""Who is the same person across chats, and what travels between chats.

    python -m pytest tests/test_memory_people.py
"""
from __future__ import annotations

from pathlib import Path

from persona_agent import people
from persona_agent.agent import Agent

from helpers import check, isolated_agent


def make_agent(tmp: Path, **kw) -> Agent:
    a = isolated_agent(tmp, persona_name="Luna", **kw)
    a.memories.clear()
    return a


def _note(text: str, uid: str = "", name: str = "", **extra) -> dict:
    row = {"text": text, "time": 1.0}
    if uid:
        row.update(user_id=uid, user_name=name or uid)
    row.update(extra)
    return row


def test_the_admins_accounts_are_one_person(tmp: Path) -> None:
    a = make_agent(tmp)
    a.admin_ids = {"telegram:42", "12345"}
    a.memories["telegram:c1"] = [_note("Boss loves sailing", "telegram:42", "Boss")]
    a.memories["private:telegram:42"] = [_note("I keep bees on the roof")]
    a.memories["private:12345"] = []
    prompt = a._memories_for_prompt("private:12345")
    check("a room's note about the admin's Telegram id reaches the admin's QQ DM",
          "loves sailing" in prompt, prompt)
    check("so does a fact from the admin's Telegram DM", "keep bees" in prompt, prompt)
    check("but a room never gets a DM's fact",
          "keep bees" not in a._memories_for_prompt("telegram:c2"))
    ops = a._operator_ids()
    check("the operator set", {"telegram:42", "12345"} <= ops)
    check("same_person of an admin id is the set",
          people.same_person("12345", ops) >= {"telegram:42", "12345"})


def test_page_chats_are_the_operator(tmp: Path) -> None:
    a = make_agent(tmp)
    old, new = "browser:" + "a" * 32, "browser:" + "b" * 32
    a.memories["private:" + old] = [_note("I am learning the violin", auto=True)]
    a.memories["private:" + new] = []
    check("an old page chat's fact reaches the new page chat",
          "violin" in a._memories_for_prompt("private:" + new))
    check("the page ids join the operator set", {old, new} <= a._operator_ids())


def test_nobody_else_is_ever_linked(tmp: Path) -> None:
    a = make_agent(tmp, memory_share_rooms=True)
    a.admin_ids = {"telegram:42"}
    a.memories["private:telegram:7"] = [_note("I owe Kim money")]
    a.memories["telegram:c1"] = [_note("Sam plays chess", "telegram:7", "Sam")]
    a.memories["private:7"] = []
    prompt = a._memories_for_prompt("private:7")
    check("the same number on another platform is someone else",
          "owe Kim" not in prompt and "chess" not in prompt, prompt)
    check("a member's DM facts never reach another member's DM",
          "owe Kim" not in a._memories_for_prompt("private:telegram:9"))
    check("same_person of a member is the member",
          people.same_person("telegram:7", a._operator_ids()) == {"telegram:7"})
    check("a claim in chat links nothing", people.same_person(
        "telegram:7", people.operator_ids({"telegram:42"}, {})) == {"telegram:7"})


def test_reported_speech_never_travels(tmp: Path) -> None:
    a = make_agent(tmp, memory_share_rooms=True)
    a.memories["telegram:c1"] = [
        _note("Sam cheats at cards", "telegram:7", "Sam", said_by="telegram:9",
              said_by_name="Kim"),
        _note("Sam plays chess", "telegram:7", "Sam"),
    ]
    a._append_buffer("telegram:c2", "Sam", "hi", "telegram:7")
    room = a._memories_for_prompt("telegram:c2")
    check("with sharing on, Sam's own fact travels", "chess" in room, room)
    check("what someone else said about him does not", "cheats" not in room, room)
    check("nor into his DM", "cheats" not in a._memories_for_prompt("private:telegram:7"))
    a._append_buffer("telegram:c1", "Sam", "hey", "telegram:7")
    check("in its own room it stays", "cheats" in a._memories_for_prompt("telegram:c1"))


def test_recall_in_a_room_lists_only_that_room(tmp: Path) -> None:
    a = make_agent(tmp, memory_share_rooms=True)
    a.memories["telegram:c1"] = [_note("Sam plays chess", "telegram:7", "Sam")]
    a.memories["telegram:c2"] = [_note("Sam bakes bread", "telegram:7", "Sam")]
    out = a._handle_memory_command("telegram:c2", "Luna what do you remember",
                                   "telegram:7", "Sam") or ""
    check("this room's note", "bakes bread" in out, out)
    check("not another room's, even with sharing on", "chess" not in out, out)
    dm = a._handle_memory_command("private:telegram:7", "Luna what do you remember",
                                  "telegram:7", "Sam") or ""
    check("a DM recall lists the rooms' notes about its reader",
          "chess" in dm and "bakes bread" in dm, dm)
    a._handle_memory_command("telegram:c2", "Luna forget chess", "telegram:7", "Sam")
    check("forget in a room still reaches the caller's notes elsewhere with sharing on",
          a.memories["telegram:c1"] == [])


def test_names_in_text() -> None:
    rows = [_note("x", "telegram:7", "Sam"), _note("y", "telegram:8", "小夏"),
            _note("z", "telegram:9", "Al")]
    check("a whole word, any case", people.names_in("did sam call?", rows)
          == {"telegram:7"})
    check("not inside a word", people.names_in("Samsung phones", rows) == set())
    check("CJK by substring", people.names_in("问问小夏吧", rows) == {"telegram:8"})
    check("two characters are enough", people.names_in("ask Al", rows) == {"telegram:9"})
