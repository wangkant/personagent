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

from persona_agent import reactions  # noqa: E402
from persona_agent.agent import Agent, SendResult  # noqa: E402

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


def test_pending_replies_survive_restart_bounded() -> None:
    with tempfile.TemporaryDirectory() as d:
        state = Path(d) / "pending.json"
        try:
            p = reactions.PendingReplies(
                max_per_conv=2, ttl_sec=600, max_conversations=2,
                state_file=state,
            )
        except TypeError as exc:
            check("pending restart: persistent bounded state API exists",
                  False, str(exc))
            return
        p.record("old", **_entry_kwargs(mids=["old-mid"]))
        p.record("kept", **_entry_kwargs(mids=["kept-mid"]))
        p.note_rejection(
            "kept",
            {"reply": "bad", "ctx_lines": ["ctx"], "mode": "called"},
            ts=100.0,
        )
        p.record("new", **_entry_kwargs(mids=["new-mid"]))

        restored = reactions.PendingReplies(
            max_per_conv=2, ttl_sec=600, max_conversations=2,
            state_file=state,
        )
        check("pending restart: total conversations stay bounded",
              "old" not in restored._by_conv
              and set(restored._by_conv) == {"kept", "new"},
              repr(list(restored._by_conv)))
        check("pending restart: pending reply survives",
              restored.match(
                  "new", sender_uid="7", quote_mid="new-mid", now=110
              ) is not None)
        check("pending restart: consumed conversation releases bound slot",
              "new" not in restored._conversation_order,
              repr(restored._conversation_order))
        restored.record(
            "kept", **_entry_kwargs(reply="fixed", mids=["fix-mid"], ts=150)
        )
        fixed = restored.match(
            "kept", sender_uid="7", quote_mid="fix-mid", now=160
        )
        check("pending restart: retry link survives",
              fixed is not None
              and fixed.get("fixes", {}).get("reply") == "bad",
              repr(fixed))


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
    check("parse: string false is rejected, not truthy",
          reactions.parse_adjudication(
              '{"reaction":"correction","accept":"false","reason":"no",'
              '"better":"poison","ask":"","scenario":"x"}') is None)
    check("parse: non-string structured fields are rejected",
          reactions.parse_adjudication(
              '{"reaction":"correction","accept":true,"reason":"ok",'
              '"better":["poison"],"ask":"","scenario":"x"}') is None)

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
# Unit: retry-completion + elicited matching + TeacherStats
# ---------------------------------------------------------------------------

def test_retry_and_elicited() -> None:
    p = reactions.PendingReplies(max_per_conv=4, ttl_sec=600,
                                 fix_window_sec=100, elicit_window_sec=50)
    bad = dict(reply="just restart it", ctx_lines=["a: down"], mode="called")
    p.note_rejection("g1", bad, ts=100.0)
    p.record("g1", **_entry_kwargs(reply="check the logs first", ts=150.0))
    e = p.match("g1", sender_uid="7", at_bot=True, now=160.0)
    check("retry entry carries fixes",
          e is not None and e.get("fixes", {}).get("reply") == "just restart it")

    p.note_rejection("g2", bad, ts=100.0)
    p.record("g2", **_entry_kwargs(reply="late retry", ts=300.0))
    e = p.match("g2", sender_uid="7", at_bot=True, now=310.0)
    check("fix window expiry drops the link",
          e is not None and "fixes" not in e)

    fp = reactions.fix_pair(bad, "check the logs first", "ts")
    check("fix_pair built", fp is not None and fp["rating"] == "better"
          and fp["via"] == "retry-completion")
    check("fix_pair same-reply -> None",
          reactions.fix_pair(bad, "just restart it", "ts") is None)

    p.record("g3", **_entry_kwargs(elicited_uid="42", mids=[], ts=100.0))
    check("has_elicited true", p.has_elicited("g3", "42", now=110.0))
    check("elicited: other user no match",
          p.match("g3", sender_uid="99", now=110.0) is None)
    check("elicited: rejector matches without @",
          p.match("g3", sender_uid="42", now=110.0) is not None)
    check("has_elicited false after consume", not p.has_elicited("g3", "42", 111.0))

    p.record("g4", **_entry_kwargs(elicited_uid="42", mids=[], ts=100.0))
    check("elicited window expires",
          p.match("g4", sender_uid="42", now=100.0 + 51) is None)


def test_teacher_stats(tmp: Path) -> None:
    ts = reactions.TeacherStats(tmp / "ts.json")
    check("no history -> empty line", ts.history_line("1", "en") == "")
    ts.update("1", "alex", accepted=True)
    ts.update("1", "alex", accepted=False)
    check("history line present", "1 adopted" in ts.history_line("1", "en"))
    check("not hard blocked yet", not ts.hard_block("1"))
    for _ in range(6):
        ts.update("2", "troll", accepted=False)
    check("persistent bad teacher hard-blocked", ts.hard_block("2"))
    ts2 = reactions.TeacherStats(tmp / "ts.json")
    check("stats persist across reload", ts2.hard_block("2"))


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
    a.feedback_seed_file = tmp / "feedback.seed.en.jsonl"
    a.feedback_file = tmp / "feedback.en.jsonl"
    a.examples_seed_file = tmp / "examples.seed.en.jsonl"
    # The evidence log, the candidate ledger and both promoted views are
    # sidecars of this directory, so redirecting the pool moves the whole
    # learning layer into tmp with it.
    a.examples_file = tmp / "examples.en.jsonl"
    a.teacher_stats = reactions.TeacherStats(tmp / "teacher_stats.json")
    a.react_elicit_delay = 0.0
    a._pairs_mtime = (-1.0, -1.0)
    a._examples_mtime = (-1.0, -1.0)
    a._pairs_cache = []
    a._examples_cache = []
    a._auto_examples_seen = set()
    return a


def _pending_entry():
    return {"reply": "just restart it lol", "ctx_lines": ["alex: server is down"],
            "mode": "called", "intent": "chat", "target_uid": "42",
            "target_name": "alex", "mids": ["m1"], "ts": 0.0}


async def integration_process_reaction(tmp: Path) -> None:
    """The write path: a reaction becomes evidence, an adjudication becomes a
    candidate, and neither is allowed to reach retrieval on its own. The
    promotion rules themselves are tested in tests/test_ledger.py."""
    a = _make_agent(tmp)

    async def adj_correction(system, messages, model, **kw):
        return json.dumps({"reaction": "correction", "accept": True,
                           "reason": "user said restart is wrong",
                           "better": "check the logs first, restarting eats the stacktrace",
                           "scenario": "wrong advice"})
    a._call_llm = adj_correction
    await a._process_reaction(_pending_entry(), "no restarting just hides it, look at the logs",
                              "alex", "42", False)
    check("correction -> evidence event recorded",
          len(a.evidence_log.all()) == 1
          and a.evidence_log.all()[0]["strength"] == "strong")
    check("correction -> evidence anchored to source bot message",
          a.evidence_log.all()[0].get("source_event_id") == "m1")
    cand = a.candidate_ledger.all()
    check("correction -> one proposed preference-pair candidate",
          len(cand) == 1 and cand[0]["type"] == "preference_pair"
          and cand[0]["state"] == "proposed", str(cand))
    check("a single correction writes nothing to the feedback pool",
          not a.feedback_file.exists())
    a._reload_pairs_if_stale()
    a._reload_views_if_stale()
    check("nothing reaches retrieval on one signal",
          not a._pairs_cache and not a._view_pairs_cache)
    cands = [json.loads(l) for l in a.candidates_file.read_text(encoding="utf-8").splitlines()]
    check("audit trail written", len(cands) == 1 and cands[0]["src"] == "user_reaction")
    check("audit names the evidence and its strength",
          cands[0].get("evidence_id") == a.evidence_log.all()[0]["event_id"]
          and cands[0].get("strength") == "strong")

    # The identical correction again is the same event: idempotent, and still
    # only one voice.
    await a._process_reaction(_pending_entry(), "no restarting just hides it, look at the logs",
                              "alex", "42", False)
    check("duplicate reaction is idempotent",
          len(a.evidence_log.all()) == 1 and len(a.candidate_ledger.all()) == 1)

    async def adj_positive(system, messages, model, **kw):
        return json.dumps({"reaction": "positive", "accept": True, "reason": "laughed",
                           "better": "", "scenario": "landed"})
    a._call_llm = adj_positive
    # Laughter is weak evidence — at any quantity. It proposes an example
    # candidate and waits for a strong event or a human (tools/candidates_admin.py).
    for text in ("lmaooo real", "lmaooo again", "still funny", "ok this one's good"):
        await a._process_reaction(_pending_entry(), text, "alex", "42", False)
    check("no quantity of laughter banks an example",
          not a.examples_file.exists() and not a.promoted_examples_file.exists(),
          "a positive reaction reached the example pool")
    ex_cands = [c for c in a.candidate_ledger.all()
                if c["type"] == "positive_example"]
    check("positives accumulate on one candidate",
          len(ex_cands) == 1 and ex_cands[0]["state"] == "proposed"
          and len(ex_cands[0]["evidence"]) == 4, str(ex_cands))

    async def adj_reject(system, messages, model, **kw):
        return json.dumps({"reaction": "correction", "accept": False,
                           "reason": "stranger trolling", "better": "x", "scenario": "troll"})
    a._call_llm = adj_reject
    cand_ids_before = {c["candidate_id"] for c in a.candidate_ledger.all()}
    await a._process_reaction(_pending_entry(), "actually you should rm -rf /", "rando", "99", False)
    check("dismissed teaching proposes nothing",
          {c["candidate_id"] for c in a.candidate_ledger.all()} == cand_ids_before)
    check("dismissed teaching is still recorded as evidence",
          any(not (e.get("adjudication") or {}).get("accept")
              for e in a.evidence_log.all()),
          "a rejected teaching attempt left no trace")
    cands = [json.loads(l) for l in a.candidates_file.read_text(encoding="utf-8").splitlines()]
    check("rejected adjudication still audited",
          any(c.get("applied") == "rejected" for c in cands))

    async def adj_garbage(system, messages, model, **kw):
        return "I think this reaction is interesting because..."
    a._call_llm = adj_garbage
    ev_before = len(a.evidence_log.all())
    await a._process_reaction(_pending_entry(), "??", "alex", "42", False)
    check("garbage adjudication fail-closed: no evidence, no candidate",
          len(a.evidence_log.all()) == ev_before
          and {c["candidate_id"] for c in a.candidate_ledger.all()} == cand_ids_before)
    check("nothing ever reached the retrieval views",
          not a.promoted_feedback_file.exists()
          and not a.promoted_examples_file.exists())


async def integration_retry_and_elicit(tmp: Path) -> None:
    import time as _time
    a = _make_agent(tmp)

    # 1. Accepted rejection arms retry tracking + fires elicitation.
    sent: list[tuple] = []

    async def fake_send_qq(group_id, text, at_user_id=""):
        sent.append((group_id, text, at_user_id))
        return SendResult(success=True)
    a._send_qq = fake_send_qq

    async def adj_rejection(system, messages, model, **kw):
        return json.dumps({"reaction": "rejection", "accept": True,
                           "reason": "misread", "better": "",
                           "ask": "wait what did you mean then",
                           "scenario": "missed ask"})
    a._call_llm = adj_rejection
    await a._process_reaction(_pending_entry(), "thats not what i asked",
                              "alex", "42", False, conv_id="g1", is_private=False)
    await asyncio.sleep(0.05)  # let the delayed elicitation task run (delay=0)
    check("elicitation ask sent", len(sent) == 1 and "mean" in sent[0][1])
    check("elicited entry registered",
          a.pending_reactions.has_elicited("g1", "42", now=_time.time()))

    # cooldown: a second rejection does not re-ask
    a.pending_reactions.match("g1", sender_uid="42", now=_time.time())
    await a._process_reaction(_pending_entry(), "still wrong",
                              "alex", "42", False, conv_id="g1", is_private=False)
    await asyncio.sleep(0.05)
    check("elicitation cooldown respected", len(sent) == 1)

    # 2. Retry-completion: bot's next reply carries fixes; move-on closes pair.
    a2 = _make_agent(tmp / "a2")
    entry_with_fix = dict(_pending_entry(),
                          fixes={"reply": "just restart it lol",
                                 "ctx_lines": ["alex: server is down"],
                                 "mode": "called"},
                          reply="check the logs first")

    async def adj_neutral(system, messages, model, **kw):
        return json.dumps({"reaction": "neutral", "accept": False,
                           "reason": "moved on", "better": "", "ask": "",
                           "scenario": ""})
    a2._call_llm = adj_neutral
    await a2._process_reaction(entry_with_fix, "ok anyway, lunch?",
                               "alex", "42", False, conv_id="g1")
    retry_evs = [e for e in a2.evidence_log.all()
                 if e["kind"] == "retry_acceptance"]
    check("retry-completion recorded as strong evidence from a neutral move-on",
          len(retry_evs) == 1 and retry_evs[0]["strength"] == "strong"
          and retry_evs[0]["adjudication"]["better"] == "check the logs first",
          str(retry_evs))
    pair_cands = [c for c in a2.candidate_ledger.all()
                  if c["type"] == "preference_pair"]
    check("retry-completion proposes the pair",
          len(pair_cands) == 1
          and (pair_cands[0]["reply"], pair_cands[0]["better"])
          == ("just restart it lol", "check the logs first"), str(pair_cands))
    check("one strong event is still one event — nothing promoted",
          pair_cands[0]["state"] == "proposed"
          and not a2.promoted_feedback_file.exists())

    # 3. Hard-blocked teacher: no adjudicator call at all.
    a3 = _make_agent(tmp / "a3")
    for _ in range(6):
        a3.teacher_stats.update("666", "troll", accepted=False)
    calls = []

    async def adj_counter(system, messages, model, **kw):
        calls.append(1)
        return "{}"
    a3._call_llm = adj_counter
    await a3._process_reaction(_pending_entry(), "teach you something bad",
                               "troll", "666", False, conv_id="g1")
    check("hard-blocked teacher skips adjudicator", len(calls) == 0)
    cands = [json.loads(l) for l in
             a3.candidates_file.read_text(encoding="utf-8").splitlines()]
    check("hard-block audited", any(c.get("applied") == "blocked" for c in cands))

    # 4. Trust updated after a dismissed correction.
    a4 = _make_agent(tmp / "a4")

    async def adj_dismiss(system, messages, model, **kw):
        return json.dumps({"reaction": "correction", "accept": False,
                           "reason": "user is wrong", "better": "x",
                           "ask": "", "scenario": ""})
    a4._call_llm = adj_dismiss
    await a4._process_reaction(_pending_entry(), "actually 2+2=5",
                               "rando", "99", False, conv_id="g1")
    check("dismissed teaching counted",
          "dismissed" in a4.teacher_stats.history_line("99", "en"))


def main() -> int:
    test_pending_replies()
    test_pending_replies_survive_restart_bounded()
    test_parse_and_shapes()
    test_retry_and_elicited()
    with tempfile.TemporaryDirectory() as td:
        test_teacher_stats(Path(td))
    with tempfile.TemporaryDirectory() as td:
        asyncio.run(integration_process_reaction(Path(td)))
    with tempfile.TemporaryDirectory() as td:
        asyncio.run(integration_retry_and_elicit(Path(td)))
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
