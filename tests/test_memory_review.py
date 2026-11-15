"""The review: a consolidation also checks a few notes against the chat's
log, and a quiet chat gets a review of its own once a day. Every verdict is
checked by code and fails closed. Scripted answers only.

Run from the repo root:

    python -m pytest tests/test_memory_review.py
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from persona_agent import consolidate

from helpers import check
from test_memory_fold import ALEX, KIM, ROOM, SAM, fold_agent, note, say, script, trash

DAY = 86400.0


def logged(agent, lines, start=None):
    """Say `lines` long ago and log them; {text: seq}."""
    say(agent, ROOM, lines, start or time.time() - 3 * DAY, step=60)
    agent.flush_state()
    return {row["text"]: row["seq"] for row in agent.chat_log.read(ROOM)}


def ev(inp, text: str) -> str:
    return next(k for k, ln in inp.lines.items() if ln.get("evidence") and ln["text"] == text)


def rlabel(inp, text: str) -> str:
    return next(r for r, (it, _t, _l) in inp.reviews.items() if it["text"] == text)


async def review(agent, *checks):
    """A review-only call answering with `checks(inp)`."""
    inp = agent._fold_input(ROOM, "review")
    assert inp is not None, "nothing to review"
    script(agent, {"thread": None, "episodes": [], "facts": [c(inp) for c in checks]})
    return inp, await agent._fold(ROOM, "review", inp)


def texts(agent) -> dict:
    return {it["text"]: it for it in agent.memories.get(ROOM, [])}


# ---- verdicts ---------------------------------------------------------------------

async def test_a_wrong_note_is_corrected_from_the_lines_that_show_it(tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "I moved to Lisbon in May"), (ALEX, "nice")])
    agent.memories[ROOM] = [note("Sam lives in Berlin", SAM,
                                 refs=[seqs["I moved to Lisbon in May"]])]
    inp, res = await review(agent, lambda inp: {
        "op": "check", "r": rlabel(inp, "Sam lives in Berlin"), "verdict": "wrong",
        "text": "Sam moved to Lisbon", "src": [ev(inp, "I moved to Lisbon in May")]})
    fact = agent.memories[ROOM][0]
    check("corrected", fact["text"] == "Sam moved to Lisbon" and not res.refused,
          repr((fact, res.refused)))
    check("and found true as it now reads", fact["checked"] > time.time() - 60)
    check("the old text is restorable", any(r["why"] == "replaced" and
                                            r["item"]["text"] == "Sam lives in Berlin"
                                            for r in trash(agent)))
    check("nothing of the window moved", agent.folded_upto.get(ROOM, 0) == 0)


async def test_a_stale_note_is_ended_and_restorable(tmp: Path) -> None:
    agent = fold_agent(tmp)
    logged(agent, [(ALEX, "I am looking for a job"), (SAM, "good luck"),
                   (ALEX, "I got the job at the bakery, starting Monday")])
    agent.memories[ROOM] = [note("Alex is looking for a job", ALEX)]
    inp, res = await review(agent, lambda inp: {
        "op": "check", "r": rlabel(inp, "Alex is looking for a job"), "verdict": "stale",
        "src": [ev(inp, "I got the job at the bakery, starting Monday")]})
    check("ended", not agent.memories[ROOM] and res.done["end"] == 1, repr(res))
    check("restorable for 30 days",
          any(r["why"] == "ended" and r["by"] == "fold" for r in trash(agent)))


async def test_a_correct_note_is_confirmed_and_left_alone(tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "I have a beagle, his name is Rex"), (ALEX, "cute")])
    before = note("Sam has a beagle called Rex", SAM,
                  refs=[seqs["I have a beagle, his name is Rex"]])
    agent.memories[ROOM] = [dict(before)]
    inp, res = await review(agent, lambda inp: {
        "op": "check", "r": rlabel(inp, "Sam has a beagle called Rex"), "verdict": "holds"})
    fact = agent.memories[ROOM][0]
    check("stamped", fact["checked"] > time.time() - 60 and res.done["checked"] == 1)
    check("nothing else changed", {k: v for k, v in fact.items() if k != "checked"} == before)
    again = agent._fold_input(ROOM, "review")
    check("not offered again within the week", again is None
          or not any(it is fact for it, _t, _l in again.reviews.values()))


async def test_holds_is_refused_when_the_lines_do_not_carry_it(tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "I like rock music"), (ALEX, "ok")])
    agent.memories[ROOM] = [note("Sam plays the violin in an orchestra", SAM,
                                 refs=[seqs["I like rock music"]])]
    _inp, res = await review(agent, lambda inp: {
        "op": "check", "r": "R1", "verdict": "holds"})
    check("refused, not stamped", res.refused["grounding"] == 1
          and "checked" not in agent.memories[ROOM][0], repr(res))


async def test_an_unsupported_note_ends_only_when_all_its_lines_are_there_and_say_otherwise(
        tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "the weather is lovely today"), (ALEX, "it is")])
    s = seqs["the weather is lovely today"]
    agent.memories[ROOM] = [note("Sam owns a red bicycle", SAM, refs=[s]),
                            note("Sam owns a blue kayak", SAM, refs=[s], age_days=0.1)]
    _inp, res = await review(
        agent,
        lambda inp: {"op": "check", "r": rlabel(inp, "Sam owns a red bicycle"),
                     "verdict": "unsupported"},
        lambda inp: {"op": "check", "r": rlabel(inp, "Sam owns a blue kayak"),
                     "verdict": "unsupported"})
    check("the old one ends, the young one stays",
          list(texts(agent)) == ["Sam owns a blue kayak"] and res.refused["age"] == 1,
          repr((texts(agent), res.refused)))


async def test_a_note_saved_on_purpose_is_confirmed_but_never_changed(tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "I am vegetarian"), (ALEX, "noted"),
                          (SAM, "I eat fish again now")])
    saved = note("Sam is vegetarian", SAM, auto=False, saved_by="s",
                 refs=[seqs["I am vegetarian"]])
    agent.memories[ROOM] = [saved]
    _inp, res = await review(agent, lambda inp: {
        "op": "check", "r": "R1", "verdict": "wrong", "text": "Sam eats fish again",
        "src": [ev(inp, "I am vegetarian")]})
    check("not changed", res.refused["fixed"] == 1
          and agent.memories[ROOM][0]["text"] == "Sam is vegetarian", repr(res))
    agent.memory_state.data["review_offered"] = {}
    _inp, res = await review(agent, lambda inp: {"op": "check", "r": "R1", "verdict": "holds"})
    check("but confirmed", agent.memories[ROOM][0].get("checked"), repr(res))


async def test_every_refusal_of_a_check(tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "I moved to Lisbon in May"), (ALEX, "I moved to Porto"),
                          (KIM, "hello all")])
    agent.memories[ROOM] = [note("Sam lives in Berlin", SAM,
                                 refs=[seqs["I moved to Lisbon in May"],
                                       seqs["I moved to Porto"]])]
    cases = {
        "label": lambda inp: {"op": "check", "r": "R9", "verdict": "holds"},
        "shape": lambda inp: {"op": "check", "r": "R1", "verdict": "maybe"},
        "src": lambda inp: {"op": "check", "r": "R1", "verdict": "wrong",
                            "text": "Sam lives in Lisbon", "src": ["L99"]},
        "grounding": lambda inp: {"op": "check", "r": "R1", "verdict": "wrong",
                                  "text": "Sam lives in Tokyo",
                                  "src": [ev(inp, "I moved to Lisbon in May")]},
        "owner": lambda inp: {"op": "check", "r": "R1", "verdict": "wrong",
                              "text": "Sam lives in Porto",
                              "src": [ev(inp, "I moved to Porto")]},
        "stale without lines": lambda inp: {"op": "check", "r": "R1", "verdict": "stale"},
    }
    for why, op in cases.items():
        agent.memory_state.data["review_offered"] = {}
        _inp, res = await review(agent, op)
        reason = {"stale without lines": "src"}.get(why, why)
        check(f"{why}: refused as {reason}", res.refused[reason] == 1
              and sum(res.refused.values()) == 1 and not res.done["checked"], repr(res))
        check(f"{why}: the note unchanged", agent.memories[ROOM][0]["text"]
              == "Sam lives in Berlin" and "checked" not in agent.memories[ROOM][0])


async def test_a_note_whose_lines_left_the_log_is_not_reviewed(tmp: Path) -> None:
    agent = fold_agent(tmp)
    logged(agent, [(SAM, "hello"), (ALEX, "hi")])
    agent.memories[ROOM] = [note("Sam lives in Berlin", SAM, refs=[999])]
    check("nothing to review: no call", agent._fold_input(ROOM, "review") is None)
    check("and it is not stamped", "checked" not in agent.memories[ROOM][0])


async def test_a_forgotten_line_does_not_come_back_through_a_review(tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "my locker code is 4471"), (ALEX, "ok")])
    agent.memories[ROOM] = [note("Sam's locker code is 4471", SAM,
                                 refs=[seqs["my locker code is 4471"]])]
    nid = agent.memories[ROOM][0]["id"]
    agent._forget_item(ROOM, "note", nid)
    check("the line left the log", "4471" not in agent.chat_log.path(ROOM).read_text(
        encoding="utf-8"))
    check("nothing is left to review", agent._fold_input(ROOM, "review") is None)


# ---- what is reviewed first ---------------------------------------------------

async def test_the_review_order(tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, f"fact number {i} about me") if i % 2 else
                          (ALEX, f"fact number {i} about me") for i in range(10)])
    now = time.time()
    rows = []
    for i, (text, seq) in enumerate(seqs.items()):
        who = SAM if i % 2 else ALEX
        rows.append(note(f"{who[1]} said {text}", who, refs=[seq], uses=i))
    rows[9]["checked"] = now - 8 * DAY       # checked long ago: after the unchecked
    rows[8]["checked"] = now - 2 * DAY       # checked this week: not again
    rows[0]["checked"] = now - 30 * DAY
    agent.memories[ROOM] = rows
    order = [it["uses"] for it in agent._review_order(ROOM, now)]
    check("never checked, most drawn on first; then checked longest ago; none this week",
          order == [7, 6, 5, 4, 3, 2, 1, 0, 9], repr(order))
    inp = agent._fold_input(ROOM, "review")
    check("at most six a call", len(inp.reviews) == consolidate.REVIEW_MAX)
    again = agent._fold_input(ROOM, "review")
    check("one offered and not judged waits a day; the rest come next",
          sorted(it["uses"] for it, _t, _l in again.reviews.values()) == [0, 1, 9],
          repr([it["uses"] for it, _t, _l in again.reviews.values()]))


async def test_a_note_without_refs_is_judged_by_its_persons_best_lines(tmp: Path) -> None:
    agent = fold_agent(tmp)
    logged(agent, [(SAM, "Alex works at the bakery"), (ALEX, "I work at the bakery"),
                   (SAM, "ok"), (ALEX, "unrelated chatter about the bakery")])
    agent.memories[ROOM] = [note("Alex works at the bakery", ALEX)]
    inp = agent._fold_input(ROOM, "review")
    _it, _t, labels = inp.reviews["R1"]
    check("only Alex's own lines, best first",
          [inp.lines[lab]["text"] for lab in labels][0] == "I work at the bakery"
          and all(inp.lines[lab]["uid"] == "a" for lab in labels),
          repr([inp.lines[lab] for lab in labels]))
    payload = inp.payload["review"][0]
    check("the model sees the note and its dated lines",
          payload["text"] == "Alex works at the bakery" and payload["evidence"][0]["at"])


async def test_a_fold_carries_reviews_and_an_ordinary_update_cannot_cite_them(
        tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "I moved to Lisbon in May"), (ALEX, "nice")])
    agent.memories[ROOM] = [note("Sam lives in Berlin", SAM,
                                 refs=[seqs["I moved to Lisbon in May"]])]
    say(agent, ROOM, [(SAM, "hello again"), (ALEX, "hey")], time.time() - 4 * 3600)
    inp = agent._fold_input(ROOM, "idle")
    check("the idle fold reviews too", "review" in inp.payload and inp.reviews)
    n = next(k for k, (it, _t) in inp.notes.items() if it["text"] == "Sam lives in Berlin")
    script(agent, {"thread": None, "episodes": [], "facts": [
        {"op": "update", "n": n, "text": "Sam lives in Lisbon",
         "src": [ev(inp, "I moved to Lisbon in May")]}]})
    res = await agent._fold(ROOM, "idle", inp)
    check("an update may cite only the stretch it reads", res.refused["src"] == 1
          and agent.memories[ROOM][0]["text"] == "Sam lives in Berlin", repr(res))


async def test_the_prompt_says_what_a_review_is(tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "I have a beagle"), (ALEX, "cute")])
    agent.memories[ROOM] = [note("Sam has a beagle", SAM, refs=[seqs["I have a beagle"]])]
    inp = agent._fold_input(ROOM, "review")
    prompts = script(agent, {"thread": None, "facts": [], "episodes": []})
    await agent._fold(ROOM, "review", inp)
    sent = prompts[0]
    check("the review is explained", '"review"' in sent and "holds" in sent)
    data = json.loads(sent[sent.index("{", len(consolidate._FOLD_PROMPT)):].rsplit("}", 1)[0]
                      + "}")
    check("a review-only call reads no stretch and no notes",
          data["lines"] == [] and data["notes"] == [] and data["review"], repr(data))


# ---- a review of its own ----------------------------------------------------------

async def test_a_quiet_chat_with_unchecked_notes_gets_one_review_a_day(tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "I have a beagle"), (ALEX, "cute")])
    agent.memories[ROOM] = [note("Sam has a beagle", SAM, refs=[seqs["I have a beagle"]])]
    check("quiet, with a note to check: a review", agent._fold_due(ROOM) == "review")
    script(agent, {"thread": None, "episodes": [], "facts": [
        {"op": "check", "r": "R1", "verdict": "holds"}]})
    check("it starts, inside the budget", agent._maybe_consolidate(ROOM, "idle") == "review")
    for _ in range(20):
        if not agent._folding:
            break
        await asyncio.sleep(0.01)
    check("the note is checked", agent.memories[ROOM][0].get("checked"))
    check("one call counted", agent.memory_state.data["per_conv"][ROOM]["count"] == 1)
    agent.memories[ROOM].append(note("Sam likes beagles", SAM, refs=[seqs["I have a beagle"]]))
    check("not twice in a day", agent._fold_due(ROOM) is None)


async def test_no_review_of_its_own_while_a_chat_talks_or_with_nothing_to_check(
        tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "I have a beagle"), (ALEX, "cute")], start=time.time() - 600)
    agent.memories[ROOM] = [note("Sam has a beagle", SAM, refs=[seqs["I have a beagle"]])]
    check("talking ten minutes ago: no review", agent._fold_due(ROOM) is None)
    quiet = fold_agent(tmp / "b")
    logged(quiet, [(SAM, "hello"), (ALEX, "hi")])
    quiet.memories[ROOM] = [note("Sam lives in Berlin", SAM, refs=[999])]
    script(quiet)
    check("no evidence left: no review and no call", quiet._fold_due(ROOM) is None
          and quiet._scan_folds() == [])
    off = fold_agent(tmp / "c", memory_calls_per_day=0)
    seqs = logged(off, [(SAM, "I have a beagle"), (ALEX, "cute")])
    off.memories[ROOM] = [note("Sam has a beagle", SAM, refs=[seqs["I have a beagle"]])]
    script(off)
    check("with calls off, none", off._maybe_consolidate(ROOM, "idle") is None)


async def test_the_scan_reviews_a_chat_no_longer_held(tmp: Path) -> None:
    agent = fold_agent(tmp)
    seqs = logged(agent, [(SAM, "I have a beagle"), (ALEX, "cute")])
    agent.memories[ROOM] = [note("Sam has a beagle", SAM, refs=[seqs["I have a beagle"]])]
    for held in (agent.window_seq, agent.buffers, agent.folded_upto):
        held.pop(ROOM, None)
    script(agent, {"thread": None, "episodes": [], "facts": []})
    check("the scan starts its review", agent._scan_folds() == [ROOM])
