"""Tests for the self-evolution loop (evolution.py + Agent.loop_evolve).

Run from the repo root:

    python -m pytest tests/test_evolution.py
"""
from __future__ import annotations

import json
from pathlib import Path

from persona_agent import evolution
from persona_agent.agent import Agent

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )


GOOD_DIAG = {
    "failure_mode": "service-desk tone",
    "bad_diagnosis": "opens with a greeting and offers help",
    "tag_to_patch": "style",
    "constraint_to_add": "BAD 'Great question!' -> OK 'depends'",
    "pair_draft": {
        "scenario": "casual question",
        "context": ["alex: is the build broken again"],
        "mode": "called",
        "reply": "Great question! Let me check that for you right away.",
        "better": "probably, it was your commit",
    },
}


# ---------------------------------------------------------------------------
# Unit: parse_review
# ---------------------------------------------------------------------------

def test_parse_review() -> None:
    check("parse: plain JSON", evolution.parse_review(json.dumps(GOOD_DIAG)) is not None)
    fenced = "```json\n" + json.dumps(GOOD_DIAG) + "\n```"
    check("parse: fenced JSON", evolution.parse_review(fenced) is not None)
    check("parse: garbage -> None", evolution.parse_review("sorry, I can't") is None)
    check("parse: no pair_draft -> None",
          evolution.parse_review('{"failure_mode": "x"}') is None)
    check("parse: pair_draft not dict -> None",
          evolution.parse_review('{"pair_draft": "x"}') is None)
    malformed = json.loads(json.dumps(GOOD_DIAG))
    malformed["pair_draft"]["context"] = "not a list"
    check("parse: pair context must be a string list",
          evolution.parse_review(json.dumps(malformed)) is None)
    malformed = json.loads(json.dumps(GOOD_DIAG))
    malformed["bad_diagnosis"] = ["not", "text"]
    check("parse: diagnosis fields are type checked",
          evolution.parse_review(json.dumps(malformed)) is None)
    check("parse: empty -> None", evolution.parse_review("") is None)


# ---------------------------------------------------------------------------
# Unit: load_evals / load_reviewed_ts
# ---------------------------------------------------------------------------

def test_loaders(tmp: Path) -> None:
    evals = tmp / "eval.jsonl"
    _write_jsonl(evals, [
        {"ts": "t1", "score": 1, "reply": "a"},
        {"ts": "t2", "score": 3, "reply": "b"},
        {"ts": "t3", "score": 5, "reply": "c"},
    ])
    low = evolution.load_evals(evals, 2)
    check("load_evals: threshold filters", [e["ts"] for e in low] == ["t1"])
    check("load_evals: missing file -> empty",
          evolution.load_evals(tmp / "nope.jsonl", 2) == [])

    cands = tmp / "candidates.jsonl"
    _write_jsonl(cands, [
        {"src_eval_ts": "t1", "applied": "approved"},
        {"src_eval_ts": "t2"},
        {"no_ts": True},
    ])
    check("load_reviewed_ts: all candidates count",
          evolution.load_reviewed_ts(cands) == {"t1", "t2"})


# ---------------------------------------------------------------------------
# Unit: pair_from_candidate
# ---------------------------------------------------------------------------

def test_pair_from_candidate() -> None:
    ev = {"ts": "t1", "score": 1, "mode": "followup",
          "reply": GOOD_DIAG["pair_draft"]["reply"]}
    cand = evolution.candidate_record(ev, GOOD_DIAG)
    pair = evolution.pair_from_candidate(cand, "2026-07-22T12:00:00")
    check("pair: converts", pair is not None)
    check("pair: rating=better (agent loader contract)",
          pair is not None and pair["rating"] == "better")
    check("pair: keeps BAD reply verbatim",
          pair is not None and pair["reply"] == GOOD_DIAG["pair_draft"]["reply"])
    check("pair: mode from draft", pair is not None and pair["mode"] == "called")
    check("pair: provenance kept",
          pair is not None and pair["src_eval_ts"] == "t1" and pair["src"] == "auto_reviewer")

    bad = json.loads(json.dumps(cand))
    bad["pair_draft"]["better"] = ""
    check("pair: empty better -> None",
          evolution.pair_from_candidate(bad, "ts") is None)

    same = json.loads(json.dumps(cand))
    same["pair_draft"]["better"] = same["pair_draft"]["reply"]
    check("pair: reply == better -> None",
          evolution.pair_from_candidate(same, "ts") is None)

    weird = json.loads(json.dumps(cand))
    weird["pair_draft"]["mode"] = "hallucinated-mode"
    p = evolution.pair_from_candidate(weird, "ts")
    check("pair: invalid mode falls back to src_mode",
          p is not None and p["mode"] == "followup")

    fabricated = json.loads(json.dumps(cand))
    fabricated["pair_draft"]["reply"] = "a different reply never evaluated"
    check("pair: draft must be bound to the evaluated reply",
          evolution.pair_from_candidate(fabricated, "ts") is None)

    missing_source = json.loads(json.dumps(cand))
    missing_source.pop("src_reply", None)
    check("pair: missing source binding fails closed",
          evolution.pair_from_candidate(missing_source, "ts") is None)

    # The reviewer sees the reply fenced in U+001E/U+001F; a model that copies
    # the marks along with it still copied the reply verbatim.
    fenced = json.loads(json.dumps(cand))
    fenced["pair_draft"]["reply"] = f"\x1e{fenced['pair_draft']['reply']}\x1f"
    p = evolution.pair_from_candidate(fenced, "ts")
    check("pair: a copy carrying the fence marks is still bound",
          p is not None and p["reply"] == GOOD_DIAG["pair_draft"]["reply"],
          repr(p))


# ---------------------------------------------------------------------------
# Unit: append_jsonl cap + feedback dedup keys
# ---------------------------------------------------------------------------

def test_append_and_dedup(tmp: Path) -> None:
    fb = tmp / "feedback.jsonl"
    pair = evolution.pair_from_candidate(
        evolution.candidate_record({
            "ts": "t1", "reply": GOOD_DIAG["pair_draft"]["reply"]},
            GOOD_DIAG), "ts")
    n = evolution.append_jsonl(fb, [pair])
    check("append: writes one", n == 1 and fb.exists())
    keys = evolution.load_feedback_keys(fb)
    check("dedup keys: (reply, better) present",
          (pair["reply"], pair["better"]) in keys)

    capped = evolution.append_jsonl(fb, [pair], max_bytes=10)
    check("append: refuses past size cap", capped == 0)

    seed = tmp / "feedback.seed.jsonl"
    runtime = tmp / "feedback.runtime.jsonl"
    seed_pair = {**pair, "reply": "seed bad", "better": "seed good"}
    runtime_pair = {**pair, "reply": "runtime bad", "better": "runtime good"}
    _write_jsonl(seed, [seed_pair])
    _write_jsonl(runtime, [runtime_pair])
    merged = evolution.load_feedback_keys([seed, runtime])
    check("dedup keys: seed + runtime merged",
          merged == {("seed bad", "seed good"),
                     ("runtime bad", "runtime good")},
          repr(merged))


# ---------------------------------------------------------------------------
# Integration: Agent._evolve_tick with a stubbed model
# ---------------------------------------------------------------------------

def _make_agent(tmp: Path) -> Agent:
    a = isolated_agent(tmp, seeds=True, qq_onebot_url=CLOSED_ONEBOT_URL)
    a.evolve_threshold = 2
    a.evolve_batch = 5
    return a


class _Scripted:
    """The reviewer's diagnosis, the reaction judge's verdict, and the
    character's own verdicts, told apart by their prompts."""

    def __init__(self, reaction: dict) -> None:
        self.reaction = reaction
        self.verdicts: list[str] = []
        self.calls: list[str] = []

    async def __call__(self, system, messages, model, **kw):
        prompt = messages[-1]["content"]
        if "deciding for yourself whether to keep" in prompt:
            self.calls.append("adopt")
            return self.verdicts.pop(0) if self.verdicts else "not json"
        if '"failure_mode"' in prompt:
            self.calls.append("review")
            return json.dumps(GOOD_DIAG)
        self.calls.append("judge")
        return json.dumps(self.reaction)


async def _diagnosed_then_complained(tmp: Path, reactor: str):
    from persona_agent import promotion

    a = _make_agent(tmp)
    a.promote_judge_enabled = False
    reply = GOOD_DIAG["pair_draft"]["reply"]
    _write_jsonl(a.eval_file, [{"ts": "t1", "group_id": "g1", "score": 1,
                                "mode": "called", "user_msg": "is it broken",
                                "reply": reply, "reason": "AI tone"}])
    model = _Scripted({"reaction": "rejection", "accept": True, "reason": "missed",
                       "better": "", "ask": "", "scenario": "s"})
    a._call_llm = model
    check("setup: one self-review pair", await a._evolve_tick() == 1)
    cid = a.candidate_ledger.all()[0]["candidate_id"]
    alone = a._basis(cid)
    check("the self-review alone is never the character's",
          alone.decision.gate == promotion.GATE_STRONG
          and not promotion.needs_character(alone.decision, alone.cand), repr(alone.decision))
    entry = {"reply": reply, "ctx_lines": ["alex: is it broken"], "mode": "called",
             "target_uid": "42", "mids": ["m1"], "ts": 0.0}
    await a._process_reaction(entry, "that's not what I asked", "someone", reactor,
                              False, conv_id="g1")
    return a, model, cid


async def test_a_self_review_its_recipient_also_rejected_goes_to_the_character(
        tmp: Path) -> None:
    from persona_agent import promotion

    a, model, cid = await _diagnosed_then_complained(tmp, "42")
    basis = a._basis(cid)
    check("the recipient's complaint plus the diagnosis: the character decides",
          basis.decision.gate == promotion.GATE_STRONG
          and promotion.needs_character(basis.decision, basis.cand), repr(basis.decision))
    a.promote_judge_enabled = True
    model.verdicts.append(json.dumps({"decision": "adopt", "choice": "",
                                      "reason": "The person it was for disliked it."}))
    check("adopted by the character", await a._character_decide(cid) == "adopted"
          and model.calls.count("adopt") == 1, str(model.calls))
    check("the rewrite is in use",
          evolution.load_feedback_keys(a.promoted_feedback_file)
          == {(GOOD_DIAG["pair_draft"]["reply"], GOOD_DIAG["pair_draft"]["better"])})

    b, model, cid = await _diagnosed_then_complained(tmp / "b", "42")
    b.promote_judge_enabled = True
    model.verdicts.append(json.dumps({"decision": "discard", "choice": "",
                                      "reason": "The new wording is not mine."}))
    check("or discarded by it", await b._character_decide(cid) == "discarded"
          and b.candidate_ledger.get(cid)["state"] == "rejected")


async def test_a_self_review_no_person_can_settle_awaits_no_second_voice(
        tmp: Path) -> None:
    a = _make_agent(tmp)
    a.promote_judge_enabled = True
    _write_jsonl(a.eval_file, [{"ts": "t1", "group_id": "g1", "score": 1,
                                "mode": "called", "user_msg": "is it broken",
                                "reply": GOOD_DIAG["pair_draft"]["reply"],
                                "reason": "AI tone"}])
    a._call_llm = _Scripted({})
    await a._evolve_tick()
    summary = a._learned_summary("g1", "en")
    check("its own rewrite alone is not counted as under observation",
          "0 under observation until another agreeing reaction arrives, 0 under my own review" in summary, summary)
    b, _model, _cid = await _diagnosed_then_complained(tmp / "b", "42")
    b.promote_judge_enabled = True
    summary = b._learned_summary("g1", "en")
    check("with its recipient's complaint it is under my own review",
          "0 under observation until another agreeing reaction arrives, 1 under my own review" in summary, summary)


async def test_a_self_review_a_bystander_rejected_is_not_judged(tmp: Path) -> None:
    from persona_agent import promotion

    a, model, cid = await _diagnosed_then_complained(tmp, "7")
    basis = a._basis(cid)
    check("a bystander's complaint does not make it the character's",
          not promotion.needs_character(basis.decision, basis.cand), repr(basis.decision))


async def test_evolve_tick(tmp: Path) -> None:
    a = _make_agent(tmp)
    _write_jsonl(a.eval_file, [
        {"ts": "t1", "score": 1, "mode": "called",
         "user_msg": "is the build broken",
         "reply": GOOD_DIAG["pair_draft"]["reply"], "reason": "AI tone"},
        {"ts": "t2", "score": 5, "mode": "called",
         "user_msg": "hi", "reply": "yo", "reason": "fine"},
    ])

    calls: list[str] = []

    async def fake_llm(system, messages, model, **kw):
        calls.append(messages[-1]["content"])
        return json.dumps(GOOD_DIAG)

    a._call_llm = fake_llm

    added = await a._evolve_tick()
    check("tick: only the low score is diagnosed", len(calls) == 1)
    check("tick: one candidate proposed", added == 1)
    cand = evolution.load_reviewed_ts(a.candidates_file)
    check("tick: audit trail written", cand == {"t1"})

    # A self-diagnosis is one automatic signal that nobody witnessed: it is
    # recorded as evidence and proposed, and it changes nothing until a real
    # user event corroborates it or a human promotes it.
    evs = a.evidence_log.all()
    check("tick: recorded as self-review evidence",
          len(evs) == 1 and evs[0]["kind"] == "self_review"
          and evs[0]["strength"] == "negative_only", str(evs))
    cands = a.candidate_ledger.all()
    check("tick: proposed, not promoted",
          len(cands) == 1 and cands[0]["state"] == "proposed", str(cands))
    check("tick: nothing written to the feedback pool",
          not a.feedback_file.exists())
    a._reload_pairs_if_stale()
    a._reload_views_if_stale()
    check("tick: retrieval does not see an unpromoted candidate",
          not a._pairs_cache and not a._view_pairs_cache)

    # A human (`personagent learned`) can grant it authority, and then it
    # hot-reloads into retrieval like any other pair.
    cid = cands[0]["candidate_id"]
    a.candidate_ledger.promote(cid, ts="2026-07-25T12:00:00", actor="admin",
                               reason="reviewed by hand")
    a._rebuild_promoted_views()
    a._reload_views_if_stale()
    check("tick: promoted candidate reaches retrieval",
          any(p.get("src") == "auto_reviewer" for p in a._view_pairs_cache),
          str(a._view_pairs_cache))

    # Second tick: nothing new -> no calls, no duplicates.
    added2 = await a._evolve_tick()
    check("tick: second run is a no-op", added2 == 0 and len(calls) == 1)

    # A rewrite-into-itself draft is recorded in the audit trail but proposes
    # nothing.
    _write_jsonl(a.eval_file, [
        {"ts": "t1", "score": 1, "mode": "called", "reply": "x", "reason": "r"},
        {"ts": "t9", "score": 2, "mode": "called", "reply": "y", "reason": "r"},
    ])

    async def fake_llm_noop_pair(system, messages, model, **kw):
        d = json.loads(json.dumps(GOOD_DIAG))
        d["pair_draft"]["reply"] = "y"
        d["pair_draft"]["better"] = "y"
        return json.dumps(d)

    a._call_llm = fake_llm_noop_pair
    added3 = await a._evolve_tick()
    check("tick: unusable draft proposes nothing",
          added3 == 0 and len(a.candidate_ledger.all()) == 1)
    check("tick: unusable draft still marked reviewed",
          evolution.load_reviewed_ts(a.candidates_file) == {"t1", "t9"})
