"""Tests for the self-evolution loop (evolution.py + Agent.loop_evolve).

Run from the repo root with no test framework required:

    python tests/test_evolution.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Make the repo root importable when invoked as `python tests/test_evolution.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from persona_agent import evolution  # noqa: E402
from persona_agent.agent import Agent  # noqa: E402

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


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
    check("parse: empty -> None", evolution.parse_review("") is None)


# ---------------------------------------------------------------------------
# Unit: load_evals / load_reviewed_ts / load_pending_candidates
# ---------------------------------------------------------------------------

def test_loaders(tmp: Path) -> None:
    evals = tmp / "eval.jsonl"
    _write_jsonl(evals, [
        {"ts": "t1", "score": 1, "reply": "a"},
        {"ts": "t2", "score": 3, "reply": "b"},
        {"ts": "t3", "score": 5, "reply": "c"},
        {"ts": "t4", "score": "junk", "reply": "d"},
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
    pending = evolution.load_pending_candidates(cands)
    check("load_pending: applied entries excluded",
          [c.get("src_eval_ts") for c in pending] == ["t2", None])


# ---------------------------------------------------------------------------
# Unit: pair_from_candidate
# ---------------------------------------------------------------------------

def test_pair_from_candidate() -> None:
    ev = {"ts": "t1", "score": 1, "mode": "followup"}
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

    strctx = json.loads(json.dumps(cand))
    strctx["pair_draft"]["context"] = "single line, not a list"
    p = evolution.pair_from_candidate(strctx, "ts")
    check("pair: string context coerced to list",
          p is not None and p["context"] == ["single line, not a list"])


# ---------------------------------------------------------------------------
# Unit: append_jsonl cap + feedback dedup keys
# ---------------------------------------------------------------------------

def test_append_and_dedup(tmp: Path) -> None:
    fb = tmp / "feedback.jsonl"
    pair = evolution.pair_from_candidate(
        evolution.candidate_record({"ts": "t1"}, GOOD_DIAG), "ts")
    n = evolution.append_jsonl(fb, [pair])
    check("append: writes one", n == 1 and fb.exists())
    keys = evolution.load_feedback_keys(fb)
    check("dedup keys: (reply, better) present",
          (pair["reply"], pair["better"]) in keys)

    capped = evolution.append_jsonl(fb, [pair], max_bytes=10)
    check("append: refuses past size cap", capped == 0)


# ---------------------------------------------------------------------------
# Unit: mark_candidates
# ---------------------------------------------------------------------------

def test_mark_candidates(tmp: Path) -> None:
    cands = tmp / "candidates.jsonl"
    _write_jsonl(cands, [
        {"src_eval_ts": "t1"},
        {"src_eval_ts": "t2"},
        {"src_eval_ts": "t3", "applied": "auto"},
    ])
    evolution.mark_candidates(cands, {"t1": "approved", "t3": "rejected"})
    rows = {r["src_eval_ts"]: r for r in
            [json.loads(l) for l in cands.read_text(encoding="utf-8").splitlines()]}
    check("mark: verdict stamped", rows["t1"].get("applied") == "approved")
    check("mark: untouched entry stays pending", "applied" not in rows["t2"])
    check("mark: existing verdict not overwritten",
          rows["t3"].get("applied") == "auto")


# ---------------------------------------------------------------------------
# Integration: Agent._evolve_tick with a stubbed model
# ---------------------------------------------------------------------------

def _make_agent(tmp: Path) -> Agent:
    a = Agent(
        api_key="test-key",
        bot_qq="10001",
        bot_name="TestBot",
        napcat_api="http://127.0.0.1:9",
        memory_file=str(tmp / "memory.json"),
        persona="test persona",
        eval_enable=False,
        eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"),
        stickers_file=str(tmp / "stickers.json"),
        message_debounce_sec=0,
        lang="en",
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.core_memory_file = tmp / "core_memory.json"
    a._seen_msg_ids.clear()
    a.core_memory.clear()
    # Redirect every evolve-loop file into the temp dir.
    a.candidates_file = tmp / "candidates.jsonl"
    a.feedback_file = tmp / "feedback.jsonl"
    a.evolve_threshold = 2
    a.evolve_batch = 5
    return a


async def integration_evolve_tick(tmp: Path) -> None:
    a = _make_agent(tmp)
    _write_jsonl(a.eval_file, [
        {"ts": "t1", "score": 1, "mode": "called",
         "user_msg": "is the build broken", "reply": "Great question!", "reason": "AI tone"},
        {"ts": "t2", "score": 5, "mode": "called",
         "user_msg": "hi", "reply": "yo", "reason": "fine"},
    ])

    calls: list[str] = []

    async def fake_llm(system, messages, model, **kw):
        calls.append(messages[-1]["content"])
        return json.dumps(GOOD_DIAG)

    a._call_anthropic = fake_llm

    added = await a._evolve_tick()
    check("tick: only the low score is diagnosed", len(calls) == 1)
    check("tick: one pair added", added == 1)
    pairs = evolution.load_feedback_keys(a.feedback_file)
    check("tick: pair landed in feedback", len(pairs) == 1)
    cand = evolution.load_reviewed_ts(a.candidates_file)
    check("tick: audit trail written", cand == {"t1"})

    # Agent hot-reload actually picks the auto pair up.
    a._reload_pairs_if_stale()
    check("tick: hot-reload sees the pair",
          any(p.get("src") == "auto_reviewer" for p in a._pairs_cache))

    # Second tick: nothing new -> no calls, no duplicates.
    added2 = await a._evolve_tick()
    check("tick: second run is a no-op", added2 == 0 and len(calls) == 1)

    # A rewrite-into-itself draft is recorded but never appended to feedback.
    _write_jsonl(a.eval_file, [
        {"ts": "t1", "score": 1, "mode": "called", "reply": "x", "reason": "r"},
        {"ts": "t9", "score": 2, "mode": "called", "reply": "y", "reason": "r"},
    ])

    async def fake_llm_noop_pair(system, messages, model, **kw):
        d = json.loads(json.dumps(GOOD_DIAG))
        d["pair_draft"]["better"] = d["pair_draft"]["reply"]
        return json.dumps(d)

    a._call_anthropic = fake_llm_noop_pair
    added3 = await a._evolve_tick()
    fb_lines = a.feedback_file.read_text(encoding="utf-8").splitlines()
    check("tick: unusable draft adds nothing", added3 == 0 and len(fb_lines) == 1)
    check("tick: unusable draft still marked reviewed",
          evolution.load_reviewed_ts(a.candidates_file) == {"t1", "t9"})


def main() -> int:
    test_parse_review()
    test_pair_from_candidate()
    with tempfile.TemporaryDirectory() as td:
        test_loaders(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_append_and_dedup(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_mark_candidates(Path(td))
    with tempfile.TemporaryDirectory() as td:
        asyncio.run(integration_evolve_tick(Path(td)))
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
