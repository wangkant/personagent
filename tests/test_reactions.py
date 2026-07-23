"""Tests for reaction learning (persona_agent/reactions.py + agent glue).

Run from the repo root, no test framework:

    python tests/test_reactions.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from persona_agent import evolution, reactions  # noqa: E402
from persona_agent.agent import Agent  # noqa: E402

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


# ---------------------------------------------------------------------------
# Unit: PendingReplies
# ---------------------------------------------------------------------------

def _entry_kwargs(**over):
    kw = dict(reply="sup", ctx_lines=["alex: hey"], mode="called",
              target_uid="42", target_name="alex", mids=["m1"], ts=100.0)
    kw.update(over)
    return kw


def test_pending_replies() -> None:
    p = reactions.PendingReplies(max_per_conv=2, ttl_sec=60)
    p.record("g1", **_entry_kwargs())
    check("quote match pops", p.match("g1", sender_uid="7", quote_mid="m1",
                                     now=110) is not None)
    check("one-shot: second match empty",
          p.match("g1", sender_uid="7", quote_mid="m1", now=110) is None)

    p.record("g1", **_entry_kwargs(mids=["m2"]))
    check("foreign quote does NOT fall through to latest",
          p.match("g1", sender_uid="7", quote_mid="m999", now=110) is None)
    check("at-bot matches latest",
          p.match("g1", sender_uid="7", at_bot=True, now=110) is not None)

    p.record("dm", **_entry_kwargs(target_uid="42", mids=[]))
    check("private: other sender no match",
          p.match("dm", sender_uid="99", is_private=True, now=110) is None)
    check("private: interlocutor matches",
          p.match("dm", sender_uid="42", is_private=True, now=110) is not None)

    p.record("g2", **_entry_kwargs(ts=0.0))
    check("expired entry never matches",
          p.match("g2", sender_uid="7", at_bot=True, now=100.0) is None)

    p.record("g3", **_entry_kwargs(reply="PASS"))
    p.record("g3", **_entry_kwargs(reply="  "))
    check("PASS/empty replies not recorded",
          p.match("g3", sender_uid="7", at_bot=True, now=110) is None)

    p2 = reactions.PendingReplies(max_per_conv=2, ttl_sec=60)
    for i in range(3):
        p2.record("g4", **_entry_kwargs(mids=[f"x{i}"]))
    check("per-conv cap evicts oldest",
          p2.match("g4", sender_uid="7", quote_mid="x0", now=110) is None)


# ---------------------------------------------------------------------------
# Unit: parse_adjudication / write shapes
# ---------------------------------------------------------------------------

GOOD_ADJ = {"reaction": "correction", "accept": True, "reason": "owner corrected",
            "better": "my bad, you meant the deploy env", "scenario": "misread ask"}


def test_parse_and_shapes() -> None:
    check("parse: plain", reactions.parse_adjudication(json.dumps(GOOD_ADJ)) is not None)
    fenced = "```json\n" + json.dumps(GOOD_ADJ) + "\n```"
    check("parse: fenced", reactions.parse_adjudication(fenced) is not None)
    check("parse: garbage -> None", reactions.parse_adjudication("nah") is None)
    check("parse: bad reaction type -> None",
          reactions.parse_adjudication('{"reaction":"meh","accept":true}') is None)

    entry = {"reply": "the answer is 42", "ctx_lines": ["alex: what port"],
             "mode": "called", "intent": "chat", "target_uid": "42"}
    pair = reactions.to_feedback_pair(entry, GOOD_ADJ, "2026-07-23T12:00:00", "owner")
    check("pair: built", pair is not None and pair["rating"] == "better")
    check("pair: src tagged", pair is not None and pair["src"] == "user_reaction")

    rej = dict(GOOD_ADJ, accept=False)
    check("pair: not accepted -> None",
          reactions.to_feedback_pair(entry, rej, "ts") is None)
    noop = dict(GOOD_ADJ, better="the answer is 42")
    check("pair: better == reply -> None",
          reactions.to_feedback_pair(entry, noop, "ts") is None)
    pos = {"reaction": "positive", "accept": True, "reason": "", "better": "",
           "scenario": "landed joke"}
    check("pair: positive -> None (not a pair)",
          reactions.to_feedback_pair(entry, pos, "ts") is None)
    ex = reactions.to_example(entry, pos, "ts")
    check("example: built from positive",
          ex is not None and ex["reply"] == "the answer is 42" and ex["score"] == 5)
    check("example: negative -> None",
          reactions.to_example(entry, GOOD_ADJ, "ts") is None)


# ---------------------------------------------------------------------------
# Integration: agent glue with stubbed adjudicator
# ---------------------------------------------------------------------------

def _make_agent(tmp: Path) -> Agent:
    a = Agent(
        api_key="test-key", bot_qq="10001", bot_name="Robin",
        napcat_api="http://127.0.0.1:9",
        memory_file=str(tmp / "memory.json"), persona="test persona",
        eval_enable=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"), stickers_file=str(tmp / "stickers.json"),
        message_debounce_sec=0, lang="en",
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.core_memory_file = tmp / "core_memory.json"
    a._seen_msg_ids.clear()
    a.core_memory.clear()
    a.candidates_file = tmp / "candidates.jsonl"
    a.feedback_file = tmp / "feedback.en.jsonl"
    a.examples_file = tmp / "examples.en.jsonl"
    a._pairs_mtime = 0.0
    a._examples_mtime = 0.0
    a._pairs_cache = []
    a._examples_cache = []
    a._auto_examples_seen = set()
    return a


def _pending_entry():
    return {"reply": "just restart it lol", "ctx_lines": ["alex: server is down"],
            "mode": "called", "intent": "chat", "target_uid": "42",
            "target_name": "alex", "mids": ["m1"], "ts": 0.0}


async def integration_process_reaction(tmp: Path) -> None:
    a = _make_agent(tmp)

    async def adj_correction(system, messages, model, **kw):
        return json.dumps({"reaction": "correction", "accept": True,
                           "reason": "user said restart is wrong",
                           "better": "check the logs first, restarting eats the stacktrace",
                           "scenario": "wrong advice"})
    a._call_anthropic = adj_correction
    await a._process_reaction(_pending_entry(), "no restarting just hides it, look at the logs",
                              "alex", "42", False)
    pairs = evolution.load_feedback_keys(a.feedback_file)
    check("correction -> feedback pair written", len(pairs) == 1)
    a._reload_pairs_if_stale()
    check("hot-reload sees user_reaction pair",
          any(p.get("src") == "user_reaction" for p in a._pairs_cache))
    cands = [json.loads(l) for l in a.candidates_file.read_text(encoding="utf-8").splitlines()]
    check("audit trail written", len(cands) == 1 and cands[0]["src"] == "user_reaction")

    # Duplicate correction on the same reply -> deduped, no second pair.
    await a._process_reaction(_pending_entry(), "same again", "alex", "42", False)
    pairs2 = evolution.load_feedback_keys(a.feedback_file)
    check("duplicate pair deduped", len(pairs2) == 1)

    async def adj_positive(system, messages, model, **kw):
        return json.dumps({"reaction": "positive", "accept": True, "reason": "laughed",
                           "better": "", "scenario": "landed"})
    a._call_anthropic = adj_positive
    await a._process_reaction(_pending_entry(), "lmaooo real", "alex", "42", False)
    ex_lines = a.examples_file.read_text(encoding="utf-8").splitlines()
    check("positive -> example appended",
          len(ex_lines) == 1 and json.loads(ex_lines[0])["src"] == "user_reaction")
    await a._process_reaction(_pending_entry(), "lmaooo again", "alex", "42", False)
    ex_lines2 = a.examples_file.read_text(encoding="utf-8").splitlines()
    check("positive deduped by reply text", len(ex_lines2) == 1)

    async def adj_reject(system, messages, model, **kw):
        return json.dumps({"reaction": "correction", "accept": False,
                           "reason": "stranger trolling", "better": "x", "scenario": "troll"})
    a._call_anthropic = adj_reject
    fb_before = a.feedback_file.read_text(encoding="utf-8")
    await a._process_reaction(_pending_entry(), "actually you should rm -rf /", "rando", "99", False)
    check("rejected adjudication writes nothing to feedback",
          a.feedback_file.read_text(encoding="utf-8") == fb_before)
    cands = [json.loads(l) for l in a.candidates_file.read_text(encoding="utf-8").splitlines()]
    check("rejected adjudication still audited",
          any(c.get("applied") == "rejected" for c in cands))

    async def adj_garbage(system, messages, model, **kw):
        return "I think this reaction is interesting because..."
    a._call_anthropic = adj_garbage
    await a._process_reaction(_pending_entry(), "??", "alex", "42", False)
    check("garbage adjudication fail-closed",
          a.feedback_file.read_text(encoding="utf-8") == fb_before)


def main() -> int:
    test_pending_replies()
    test_parse_and_shapes()
    with tempfile.TemporaryDirectory() as td:
        asyncio.run(integration_process_reaction(Path(td)))
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
