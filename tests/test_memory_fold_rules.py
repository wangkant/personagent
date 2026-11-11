"""Consolidation rules that hold for every operation of an answer: whose a
fact is, and what a malformed answer does. Every answer is scripted.

Run from the repo root:

    python -m pytest tests/test_memory_fold_rules.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from helpers import check
from test_memory_fold import ALEX, KIM, ROOM, OTHER, SAM, fold_agent, label, note, say, script

DM = "private:telegram:9"


def _start() -> float:
    return time.time() - 2 * 3600


# ---- whose a fact is ------------------------------------------------------------

async def test_a_claim_about_a_person_stays_the_claimers_word(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(ALEX, "Sam stole my bike last week"), (SAM, "hello everyone")], _start())
    inp = agent._fold_input(ROOM, "idle")
    sam = inp.lines["L2"]["speaker"]
    script(agent, {"facts": [
        {"op": "add", "about": sam, "text": "Sam stole a bike", "imp": 4, "src": ["L1", "L2"]}]})
    await agent._fold(ROOM, "idle", inp)
    (row,) = agent.memories[ROOM]
    check("filed as Alex's word, not as Sam's own",
          not row.get("user_id") and row.get("said_by") == "a", repr(row))
    check("it never reaches another chat",
          agent._room_notes_about("s", OTHER) == [])


async def test_words_someone_forwards_or_pictures_are_the_posters(tmp: Path) -> None:
    for i, text in enumerate((
            "\x1e[forwarded from Sam]\x1f \x1eI stole the bike\x1f",
            "[image: a note that reads Sam stole the bike]",
            "[file: sam_stole_the_bike.txt]")):
        agent = fold_agent(tmp / str(i))
        say(agent, ROOM, [(ALEX, text), (SAM, "hello everyone")], _start())
        inp = agent._fold_input(ROOM, "idle")
        script(agent, {"facts": [{"op": "add", "about": inp.lines["L2"]["speaker"],
                                  "text": "Sam stole the bike", "src": ["L1", "L2"]}]})
        await agent._fold(ROOM, "idle", inp)
        (row,) = agent.memories[ROOM]
        check(f"{text[:20]!r}: Alex's word", not row.get("user_id")
              and row.get("said_by") == "a", repr(row))


async def test_a_persons_own_line_still_makes_their_fact(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(ALEX, "Sam has a new dog called Rex"), (SAM, "yes, Rex is a beagle")],
        _start())
    inp = agent._fold_input(ROOM, "idle")
    script(agent, {"facts": [
        {"op": "add", "about": inp.lines["L2"]["speaker"], "text": "Sam has a beagle called Rex",
         "src": ["L1", "L2"]}]})
    await agent._fold(ROOM, "idle", inp)
    (row,) = agent.memories[ROOM]
    check("Sam's own", row.get("user_id") == "s" and not row.get("said_by"), repr(row))


async def test_a_text_naming_only_others_is_the_speakers_word(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, "Alex cheats at cards"), (ALEX, "no I do not")], _start())
    inp = agent._fold_input(ROOM, "idle")
    script(agent, {"facts": [
        {"op": "add", "about": inp.lines["L1"]["speaker"], "text": "Alex cheats at cards",
         "src": ["L1"]}]})
    await agent._fold(ROOM, "idle", inp)
    (row,) = agent.memories[ROOM]
    check("Sam's word about Alex, not a fact of Sam's",
          not row.get("user_id") and row.get("said_by") == "s", repr(row))


async def test_a_group_fact_naming_a_person_needs_that_persons_line(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(ALEX, "Sam stole my bike last week"), (SAM, "let us hike on Saturday"),
                      (ALEX, "Saturday works for me")], _start())
    inp = agent._fold_input(ROOM, "idle")
    script(agent, {"facts": [
        {"op": "add", "about": "group", "text": "Sam stole Alex's bike", "src": ["L1"]},
        {"op": "add", "about": "group", "text": "Sam and Alex hike on Saturday",
         "src": ["L2", "L3"]},
        {"op": "add", "about": "group", "text": "The bike was stolen last week", "src": ["L1"]}]})
    await agent._fold(ROOM, "idle", inp)
    rows = {it["text"]: it for it in agent.memories[ROOM]}
    claim = rows.get("Sam stole Alex's bike") or {}
    check("a claim naming Sam is Alex's word",
          claim.get("said_by") == "a" and not claim.get("user_id"), repr(rows))
    hike = rows.get("Sam and Alex hike on Saturday") or {}
    check("both named said it: the group's",
          hike and not hike.get("said_by") and not hike.get("user_id"), repr(rows))
    plain = rows.get("The bike was stolen last week") or {}
    check("naming nobody: the group's as before",
          plain and not plain.get("said_by"), repr(rows))


async def test_another_members_line_never_rewrites_a_persons_fact(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, "morning all"), (ALEX, "Sam cheats at cards every game")], _start())
    agent.memories[ROOM] = [note("Sam likes cards", SAM)]
    inp = agent._fold_input(ROOM, "idle")
    script(agent, {"facts": [
        {"op": "update", "n": label(inp, "Sam likes cards"),
         "text": "Sam cheats at cards", "src": ["L1", "L2"]}]})
    res = await agent._fold(ROOM, "idle", inp)
    check("refused", res.refused["grounding"] + res.refused["owner"] == 1, repr(res.refused))
    check("Sam's note unchanged", [it["text"] for it in agent.memories[ROOM]]
          == ["Sam likes cards"])


async def test_another_members_line_never_ends_a_persons_fact(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, "morning all"), (ALEX, "Sam quit his job at the bakery")], _start())
    agent.memories[ROOM] = [note("Sam works at the bakery", SAM)]
    inp = agent._fold_input(ROOM, "idle")
    script(agent, {"facts": [
        {"op": "end", "n": label(inp, "Sam works at the bakery"), "why": "contradicted",
         "src": ["L1", "L2"]}]})
    res = await agent._fold(ROOM, "idle", inp)
    check("refused", sum(res.refused.values()) == 1 and not res.done["end"], repr(res.refused))
    check("Sam's note kept", [it["text"] for it in agent.memories[ROOM]]
          == ["Sam works at the bakery"])


async def test_its_subject_ends_a_fact_on_their_own_line(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, "I left the bakery job last week"), (ALEX, "oh")], _start())
    agent.memories[ROOM] = [note("Sam works at the bakery", SAM)]
    inp = agent._fold_input(ROOM, "idle")
    script(agent, {"facts": [
        {"op": "end", "n": label(inp, "Sam works at the bakery"), "why": "contradicted",
         "src": ["L1"]}]})
    res = await agent._fold(ROOM, "idle", inp)
    check("ended", res.done["end"] == 1 and not agent.memories[ROOM], repr(res.refused))


async def test_a_claim_never_merges_into_a_persons_own_fact(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, "hi"), (ALEX, "hey")], _start())
    agent.memories[ROOM] = [note("Sam likes cards", SAM),
                            note("Sam likes cards a lot", SAM, said_by="a",
                                 said_by_name="Alex")]
    inp = agent._fold_input(ROOM, "idle")
    script(agent, {"facts": [
        {"op": "merge", "from": [label(inp, "Sam likes cards"),
                                 label(inp, "Sam likes cards a lot")],
         "text": "Sam likes cards a lot"}]})
    res = await agent._fold(ROOM, "idle", inp)
    check("refused", res.refused["merge"] == 1, repr(res.refused))
    check("both kept", len(agent.memories[ROOM]) == 2)


async def test_reported_speech_changes_only_on_its_speakers_line(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(KIM, "Sam owes Alex a hundred euros now")], _start())
    agent.memories[ROOM] = [note("Alex says Sam owes him fifty euros", said_by="a",
                                 said_by_name="Alex")]
    inp = agent._fold_input(ROOM, "idle")
    script(agent, {"facts": [
        {"op": "update", "n": label(inp, "Alex says Sam owes him fifty euros"),
         "text": "Alex says Sam owes him a hundred euros", "src": ["L1"]}]})
    res = await agent._fold(ROOM, "idle", inp)
    check("Kim cannot reword Alex's word", res.refused["owner"] == 1, repr(res.refused))


async def test_a_fixed_note_is_not_rated(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, "hi"), (ALEX, "hey")], _start())
    agent.memories[ROOM] = [note("Sam is vegetarian", SAM, auto=False, saved_by="s", imp=4)]
    inp = agent._fold_input(ROOM, "idle")
    script(agent, {"facts": [{"op": "rate", "n": label(inp, "Sam is vegetarian"), "imp": 1}]})
    res = await agent._fold(ROOM, "idle", inp)
    check("refused", res.refused["fixed"] == 1, repr(res.refused))
    check("its importance kept", agent.memories[ROOM][0]["imp"] == 4)


async def test_a_dm_fact_needs_the_readers_own_line(tmp: Path) -> None:
    agent = fold_agent(tmp)
    agent._wake(DM)
    t = _start()
    agent.dm_history["telegram:9"] = [
        {"role": "assistant", "content": "You work as a nurse in Leeds, right?", "t": t, "seq": 1},
        {"role": "user", "content": "hmm", "name": "Jo", "t": t + 60, "seq": 2},
        {"role": "user", "content": "I play the violin", "name": "Jo", "t": t + 120, "seq": 3}]
    inp = agent._fold_input(DM, "idle")
    script(agent, {"facts": [
        {"op": "add", "about": "S1", "text": "Jo works as a nurse in Leeds", "src": ["L1", "L2"]},
        {"op": "add", "about": "S1", "text": "Jo plays the violin", "src": ["L3"]}]})
    res = await agent._fold(DM, "idle", inp)
    check("the character's own words are not the reader's fact",
          [it["text"] for it in agent.memories.get(DM, [])] == ["Jo plays the violin"],
          repr((agent.memories.get(DM), res.refused)))


def test_a_reply_note_restating_a_claim_is_the_claimers_word(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, "hello everyone, I got a red bike"),
                      (ALEX, "Sam stole my bike last week")], time.time() - 600)
    agent.memories[ROOM] = [note("Sam got a red bike", SAM, age_days=0.01)]
    agent._save_auto_memory(ROOM, "Sam stole a bike last week from Alex")
    rows = {it["text"]: it for it in agent.memories[ROOM]}
    claim = rows.get("Sam stole a bike last week from Alex") or {}
    check("filed as Alex's word about Sam", claim.get("user_id") == "s"
          and claim.get("said_by") == "a", repr(rows))
    check("Sam's own note is not rewritten", "Sam got a red bike" in rows, repr(rows))
    check("it never reaches Sam's DM", not [it for _c, it in agent._room_notes_about(
        "s", "private:telegram:s") if "stole" in it["text"]])
    agent._save_auto_memory(ROOM, "Sam got a red bike recently")
    own = next(it for it in agent.memories[ROOM] if it["text"].startswith("Sam got"))
    check("a note his own words carry stays his", own.get("user_id") == "s"
          and not own.get("said_by"), repr(own))


def test_a_plans_day_is_judged_in_the_characters_zone(tmp: Path, monkeypatch) -> None:
    from datetime import date, datetime, timedelta, timezone

    agent = fold_agent(tmp)
    hours = next(h for h in range(-12, 15) if datetime.now(
        timezone(timedelta(hours=h))).date() != date.today())
    monkeypatch.setenv("PERSONA_TZ_OFFSET_HOURS", str(hours))
    today = datetime.now(timezone(timedelta(hours=hours))).date()
    for day in (today - timedelta(days=1), today + timedelta(days=366)):
        check(f"{day} is inside the window of UTC{hours:+d}",
              agent._fold_due_date(day.isoformat()) == day.isoformat())
    check("a day before it is not",
          agent._fold_due_date((today - timedelta(days=2)).isoformat()) == "")


# ---- a malformed answer ---------------------------------------------------------

async def test_a_malformed_operation_is_refused_and_counts_as_a_failure(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, "I play the cello on Sundays"), (ALEX, "nice")],
        time.time() - 4 * 3600)
    inp = agent._fold_input(ROOM, "idle")
    sam = inp.lines["L1"]["speaker"]
    script(agent, {"facts": [
        {"op": "add", "about": sam, "text": "Sam plays the cello on Sundays", "imp": 3,
         "src": ["L1"]},
        {"op": ["add"], "about": sam, "text": "x", "src": ["L1"]},
        {"op": {"a": 1}, "n": ["N1"]}],
        "episodes": [{"op": ["add"]}, {"op": "add", "text": ["x"], "src": [["L1"]]}]})
    agent._folding.add(ROOM)
    res = await agent._fold(ROOM, "idle", inp)
    check("no exception; each bad one refused", res is not None
          and res.refused["shape"] == 3, repr(res and res.refused))
    disk = json.loads(agent.memory_file.read_text(encoding="utf-8"))
    check("the good one applied and saved",
          [r["text"] for r in disk[ROOM]] == ["Sam plays the cello on Sundays"])
    check("the cursor moved", agent.folded_upto.get(ROOM) == 2)
    row = agent.memory_state.data["per_conv"][ROOM]
    check("the chat backs off", row["fails"] == 1 and row["next_at"] > time.time(), repr(row))


async def test_an_unexpected_error_while_applying_changes_nothing(tmp: Path) -> None:
    agent = fold_agent(tmp)
    say(agent, ROOM, [(SAM, "I play the cello on Sundays"), (ALEX, "nice")],
        time.time() - 4 * 3600)
    agent.memories[ROOM] = [note("Sam likes chess", SAM)]
    inp = agent._fold_input(ROOM, "idle")
    sam = inp.lines["L1"]["speaker"]
    script(agent, {"thread": "Sam plays the cello on Sundays",
                   "facts": [{"op": "add", "about": sam, "text": "Sam plays the cello on Sundays",
                              "src": ["L1"]},
                             {"op": "rate", "n": label(inp, "Sam likes chess"), "imp": 5},
                             {"op": "end", "n": label(inp, "Sam likes chess"), "why": "over"}]})

    def boom(*_a, **_k):
        raise KeyError("boom")
    agent._fold_end = boom
    agent._folding.add(ROOM)
    res = await agent._fold(ROOM, "idle", inp)
    check("nothing escapes", res is None)
    check("nothing applied", [(it["text"], it["imp"]) for it in agent.memories[ROOM]]
          == [("Sam likes chess", 3)] and not agent.episode_store.thread(ROOM),
          repr(agent.memories[ROOM]))
    check("the lines wait", agent.folded_upto.get(ROOM, 0) == 0)
    row = agent.memory_state.data["per_conv"][ROOM]
    check("counted as a failure", row["fails"] == 1, repr(row))
    check("no longer marked as running", ROOM not in agent._folding)
