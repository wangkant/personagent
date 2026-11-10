"""Tests for retract_example, how a human disagreement pulls a reply out of
the hand-approved example pool, and for the gate codes that tell the
character's holds apart. What the ledger decides lives in
tests/test_ledger.py.

Run from the repo root:

    python -m pytest tests/test_promotion.py
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from persona_agent import candidates, evidence, promotion
from persona_agent.promotion import retract_example

from helpers import check

NOW = 1_800_000_000.0
TS = datetime.fromtimestamp(NOW - 60, timezone.utc).isoformat()
SCOPE = dict(lang="en", platform="qq", conv_id="g1", persona="B",
             persona_hash="h", persona_version="v1")
REPLY, FIX = "just restart it lol", "check the logs first"


def event(speaker: str, rtype: str, *, reply: str = REPLY, better: str = "",
          recipient: str | None = None, kind: str = evidence.KIND_REACTION,
          accept: bool = True, text: str = "") -> dict:
    return evidence.make_event(
        kind=kind, ts=TS, **SCOPE, speaker_id=speaker,
        recipient_id=speaker if recipient is None else recipient,
        reply=reply, reaction_text=text or f"{speaker} reacts", reaction_type=rtype,
        adjudication={"accept": accept, "better": better, "mode": "called"})


def pair(better: str = FIX, state: str = "proposed") -> dict:
    c = candidates.make_candidate(
        ctype=candidates.TYPE_PAIR, scope=SCOPE, created_at=TS,
        payload={"reply": REPLY, "better": better, "mode": "called"})
    c["state"] = state
    return c


def example(state: str = "proposed") -> dict:
    c = candidates.make_candidate(
        ctype=candidates.TYPE_EXAMPLE, scope=SCOPE, created_at=TS,
        payload={"reply": REPLY, "mode": "called"})
    c["state"] = state
    return c


def decide(cand, linked, related=(), peers=(), **policy):
    return promotion.decide(cand, linked_events=linked,
                            related_events=list(linked) + list(related),
                            peers=peers, now=NOW,
                            policy=promotion.Policy(**policy))


STRONG_PAIR = [event("alice", "correction", better=FIX),
               event("bob", "correction", better=FIX)]


def test_every_hold_names_its_gate_and_keeps_its_reason() -> None:
    off = decide(pair(), STRONG_PAIR, auto_promote=False)
    check("gate: off", off.gate == promotion.GATE_OFF
          and off.reason == "automatic promotion disabled (PROMOTE_AUTO_ENABLED)",
          repr(off))
    state = decide(pair(state="promoted"), STRONG_PAIR)
    check("gate: state", state.gate == promotion.GATE_STATE
          and state.reason == "state is promoted, not proposed", repr(state))

    laugh = event("carol", "positive")
    against = decide(pair(), STRONG_PAIR, related=[laugh])
    check("gate: against", against.gate == promotion.GATE_AGAINST
          and against.reason == "compatible evidence disagrees — left for review"
          and against.blocked_by == laugh["event_id"]
          and (against.supporting, against.strong) == (2, 2), repr(against))

    rival = pair("restart the service instead")
    rival_ev = event("carol", "correction", better="restart the service instead")
    conflict = decide(pair(), STRONG_PAIR, related=[rival_ev], peers=[rival])
    check("gate: conflict", conflict.gate == promotion.GATE_CONFLICT
          and conflict.reason == "a conflicting candidate exists — left for review"
          and conflict.blocked_by == rival["candidate_id"], repr(conflict))

    person = decide(example(), [event("a", "positive"), event("b", "positive")])
    check("gate: person", person.gate == promotion.GATE_PERSON
          and person.reason == ("positive_example is promotable only by a person: "
                                "nothing that supports one classifies strong "
                                "(2 supporting)"), repr(person))

    weak = decide(pair(), [event("alice", "rejection"), event("bob", "rejection")])
    check("gate: strong", weak.gate == promotion.GATE_STRONG
          and weak.reason == "0/1 strong events (2 supporting)", repr(weak))

    one = decide(pair(), STRONG_PAIR[:1])
    check("gate: events", one.gate == promotion.GATE_EVENTS
          and one.reason == "1/2 compatible events", repr(one))

    alone = decide(pair(), [event("alice", "correction", better=FIX),
                            event("alice", "rejection")], min_speakers=2)
    check("gate: speakers", alone.gate == promotion.GATE_SPEAKERS
          and alone.reason.startswith("1/2 distinct speakers"), repr(alone))

    ok = decide(pair(), STRONG_PAIR)
    check("gate: ok", ok.promote and ok.gate == promotion.GATE_OK
          and ok.reason == "2 compatible events, 2 strong", repr(ok))
    check("gate: every code is listed",
          {off.gate, state.gate, against.gate, conflict.gate, person.gate,
           weak.gate, one.gate, alone.gate, ok.gate} == set(promotion.GATES))
    check("a Decision built by position still works",
          promotion.Decision(False, "x", 1, 0).gate == ""
          and not promotion.Decision(False, "x", 1, 0).otherwise_ready)


def test_only_holds_no_reaction_clears_go_to_the_character() -> None:
    def judged(decision, cand):
        return promotion.needs_character(decision, cand)

    laugh = event("carol", "positive")
    against = decide(pair(), STRONG_PAIR, related=[laugh])
    check("against, otherwise ready: judged",
          against.otherwise_ready and judged(against, pair())
          and promotion.may_adopt(against), repr(against))

    thin = decide(pair(), STRONG_PAIR[:1], related=[laugh])
    check("against, but one event short: not judged, more reactions decide",
          thin.gate == promotion.GATE_AGAINST and not thin.otherwise_ready
          and not judged(thin, pair()), repr(thin))
    weak = decide(pair(), [event("alice", "rejection"), event("bob", "rejection")],
                  related=[laugh])
    check("against, but nothing strong: not judged",
          weak.gate == promotion.GATE_AGAINST and not judged(weak, pair()),
          repr(weak))
    lonely = decide(pair(), [event("alice", "correction", better=FIX),
                             event("alice", "rejection")],
                    related=[laugh], min_speakers=2)
    check("against, but a second person is required: not judged",
          not judged(lonely, pair()), repr(lonely))

    rival = pair("restart the service instead")
    rival_ev = event("carol", "correction", better="restart the service instead")
    conflict = decide(pair(), STRONG_PAIR, related=[rival_ev], peers=[rival])
    check("conflict, otherwise ready: judged", judged(conflict, pair()))

    people = decide(example(), [event("a", "positive"), event("b", "positive")])
    check("example liked by two people: judged",
          people.otherwise_ready and people.person_support == 2
          and judged(people, example()), repr(people))
    selfish = decide(example(), [
        event("", "", kind=evidence.KIND_SELF_EVAL, recipient=""),
        evidence.make_event(kind=evidence.KIND_SELF_EVAL, ts=TS, **SCOPE,
                            reply=REPLY, reaction_text="score 5",
                            adjudication={"accept": True, "score": 5})])
    check("example backed only by self-evaluation: never judged",
          selfish.gate == promotion.GATE_PERSON and selfish.supporting == 2
          and selfish.person_support == 0 and not judged(selfish, example()),
          repr(selfish))
    single = decide(example(), [event("a", "positive")])
    check("example with one reaction: not judged yet",
          not single.otherwise_ready and not judged(single, example()))
    one_voice = decide(example(), [event("a", "positive"),
                                   event("a", "positive", text="again, lol")],
                       min_speakers=2)
    check("example from one person where two are required: not judged",
          not judged(one_voice, example()), repr(one_voice))
    disputed_example = decide(example(), [event("a", "positive"), event("b", "positive")],
                              related=[event("c", "correction", better="x")])
    check("example someone corrected, two people liked: judged",
          disputed_example.gate == promotion.GATE_AGAINST
          and judged(disputed_example, example()), repr(disputed_example))

    for name, d in [
            ("off", decide(pair(), STRONG_PAIR, related=[laugh], auto_promote=False)),
            ("state", decide(pair(state="promoted"), STRONG_PAIR)),
            ("strong", decide(pair(), [event("a", "rejection"), event("b", "rejection")])),
            ("events", decide(pair(), STRONG_PAIR[:1])),
            ("ok", decide(pair(), STRONG_PAIR))]:
        check(f"{name}: never judged", not judged(d, pair()), repr(d))


def test_a_rewrite_its_recipient_refused_is_never_adoptable() -> None:
    later = event("alice", "rejection", reply=FIX)        # alice refused FIX
    refused = decide(pair(), STRONG_PAIR, related=[later])
    check("refused: still for the character, to discard or observe",
          refused.gate == promotion.GATE_AGAINST and refused.refused
          and promotion.needs_character(refused, pair()), repr(refused))
    check("refused: but never adoptable", not promotion.may_adopt(refused))

    # The original reply was for alice; the later one for nobody in particular.
    via_original = event("alice", "rejection", reply=FIX, recipient="")
    check("refused by the original reply's recipient",
          decide(pair(), STRONG_PAIR, related=[via_original]).refused)
    check("refused by the admin",
          promotion.decide(pair(), linked_events=STRONG_PAIR,
                           related_events=STRONG_PAIR + [
                               event("root", "rejection", reply=FIX, recipient="x")],
                           now=NOW, admin_ids=["root"]).refused)
    bystander = event("dave", "rejection", reply=FIX, recipient="erin")
    by = decide(pair(), STRONG_PAIR, related=[bystander])
    check("a bystander's refusal is a disagreement, not a veto",
          by.gate == promotion.GATE_AGAINST and not by.refused
          and promotion.may_adopt(by), repr(by))


def test_a_conflict_is_judged_as_one_group() -> None:
    mine, rival = pair(), pair("restart the service instead")
    live = pair("logs, then restart", state="promoted")
    unwitnessed = pair("an unwitnessed draft")
    gone = pair("long gone", state="rejected")
    related = STRONG_PAIR + [
        event("carol", "correction", better="restart the service instead"),
        event("dan", "correction", better="logs, then restart")]
    group = promotion.conflict_group(mine, [mine, rival, live, unwitnessed, gone],
                                     related_events=related)
    check("group: the candidate first, then every live witnessed rival",
          [c["better"] for c in group]
          == [FIX, "restart the service instead", "logs, then restart"],
          str([c["better"] for c in group]))
    check("group: alone when nothing conflicts",
          promotion.conflict_group(mine, [mine], related_events=related) == [mine])


def test_a_dispute_of_an_item_in_use_is_found() -> None:
    live = pair(state="promoted")
    objection = event("dave", "rejection", reply=FIX, recipient="alice")
    laugh = event("erin", "positive", reply=FIX)
    dismissed = event("frank", "rejection", reply=FIX, accept=False)
    check("dispute: an accepted objection to the taught text",
          promotion.disputes(live, [objection, laugh, dismissed])
          == [objection["event_id"]])
    shown = example(state="promoted")
    check("dispute: an example's taught text is its reply",
          promotion.disputes(shown, [event("dave", "correction", better="x")]) != [])


def ex(reply: str) -> dict:
    return {"reply": reply, "scenario": "s", "mode": "called",
            "intent": "joke", "context": ["[u] hi"], "score": 5}


def test_retract_example_from_pool() -> None:
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "examples.jsonl"
        rows = [ex("keep me"), ex("drop me"), ex("keep me too")]
        f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        n = retract_example(f, "drop me")
        left = [json.loads(l)["reply"] for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        check("retract removes exactly the rejected reply", n == 1 and left == ["keep me", "keep me too"],
              f"n={n} left={left}")
        check("retracting an absent reply rewrites nothing",
              retract_example(f, "not here") == 0)

        # A malformed row must survive untouched rather than be silently eaten.
        f.write_text('{"reply": "drop me"}\nnot json\n', encoding="utf-8")
        retract_example(f, "drop me")
        check("malformed row preserved",
              f.read_text(encoding="utf-8").strip() == "not json")
