"""Tests for the evidence -> candidate -> promotion path.

The rule being protected: **a single automatic signal must never permanently
change behaviour.** A reaction is evidence, adjudication proposes a candidate,
promotion grants authority, and rollback or supersession takes it away. These
tests assert each of those boundaries holds — including the ones that are only
visible by their absence, like "five people laughed and the example pool is
still empty".

Run from the repo root, no test framework:

    python tests/test_ledger.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from persona_agent import candidates, evidence, promotion  # noqa: E402
from persona_agent.agent import Agent  # noqa: E402
from persona_agent.paths import runtime_dir  # noqa: E402

_failures: list[str] = []
NOW = 1_800_000_000.0


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def make_agent(tmp: Path) -> Agent:
    """Agent with every learned-state path inside `tmp`.

    The evidence log, the ledger and both views are sidecars of
    examples_file.parent, so redirecting the pools moves the whole learning
    layer with them — see test_paths_never_touch_real_runtime_state."""
    tmp.mkdir(parents=True, exist_ok=True)
    a = Agent(
        api_key="k", bot_qq="1", bot_name="B", lang="en",
        napcat_api="http://127.0.0.1:9",
        memory_file=str(tmp / "memory.json"), persona="test persona",
        eval_enable=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"), stickers_file=str(tmp / "stickers.json"),
        message_debounce_sec=0,
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a._seen_msg_ids.clear()
    a.core_memory_file = tmp / "core_memory.json"
    a.core_memory = {}
    a.candidates_file = tmp / "candidates.jsonl"
    a.examples_seed_file = tmp / "seed_examples.jsonl"
    a.examples_file = tmp / "examples.jsonl"
    a.feedback_seed_file = tmp / "seed_feedback.jsonl"
    a.feedback_file = tmp / "feedback.jsonl"
    a.react_elicit = False          # no elicitation sends in these tests
    return a


def entry(reply: str = "just restart it lol", *, target_uid: str = "42",
          mode: str = "called", **over) -> dict:
    e = {"reply": reply, "ctx_lines": ["alex: server is down"], "mode": mode,
         "intent": "chat", "target_uid": target_uid, "target_name": "alex",
         "mids": ["m1"], "ts": 0.0, "matched_by": "at"}
    e.update(over)
    return e


def adjudicator(**adj):
    """Stub _call_anthropic returning one fixed adjudication."""
    payload = {"reaction": "positive", "accept": True, "reason": "r",
               "better": "", "ask": "", "scenario": ""}
    payload.update(adj)

    async def _call(system, messages, model, **kw):
        return json.dumps(payload)
    return _call


async def react(agent: Agent, adj: dict, *, reply: str = "just restart it lol",
                text: str = "reaction", uid: str = "42", name: str = "alex",
                is_owner: bool = False, conv_id: str = "g1",
                pending: dict | None = None) -> None:
    agent._call_anthropic = adjudicator(**adj)
    await agent._process_reaction(
        pending if pending is not None else entry(reply),
        text, name, uid, is_owner, conv_id=conv_id)


def view_pairs(agent: Agent) -> list[dict]:
    if not agent.promoted_feedback_file.exists():
        return []
    return [json.loads(l) for l in
            agent.promoted_feedback_file.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def view_examples(agent: Agent) -> list[dict]:
    if not agent.promoted_examples_file.exists():
        return []
    return [json.loads(l) for l in
            agent.promoted_examples_file.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def states(agent: Agent) -> list[str]:
    return sorted(c.get("state") for c in agent.candidate_ledger.all())


CORRECTION = {"reaction": "correction", "accept": True,
              "reason": "restarting hides the stacktrace",
              "better": "check the logs first", "scenario": "wrong advice"}
REJECTION = {"reaction": "rejection", "accept": True, "reason": "misread",
             "better": "", "ask": "", "scenario": "missed ask"}
POSITIVE = {"reaction": "positive", "accept": True, "reason": "laughed",
            "better": "", "scenario": "landed"}


# ---------------------------------------------------------------------------
# 1-2. Weak evidence never promotes, at any quantity
# ---------------------------------------------------------------------------

async def test_one_positive_promotes_nothing(tmp: Path) -> None:
    a = make_agent(tmp)
    await react(a, POSITIVE, text="lmaooo real")
    check("1: positive reaction recorded as evidence",
          len(a.evidence_log.all()) == 1)
    check("1: positive reaction proposes a candidate",
          [c["type"] for c in a.candidate_ledger.all()] == ["positive_example"])
    check("1: nothing promoted", states(a) == ["proposed"], str(states(a)))
    check("1: nothing in the retrieval view", view_examples(a) == [])
    check("1: nothing written to the learned pool",
          not a.examples_file.exists())
    check("1: retrieval does not surface it",
          "just restart it lol" not in a._examples_for_prompt("server down", "called"))


async def test_repeated_weak_promotes_nothing(tmp: Path) -> None:
    a = make_agent(tmp)
    for i in range(5):
        await react(a, POSITIVE, text=f"lmao {i}")
    log = a.evidence_log.all()
    check("2: five distinct weak events recorded", len(log) == 5, str(len(log)))
    check("2: all weak", {e["strength"] for e in log} == {"weak"})
    check("2: still one candidate, still proposed", states(a) == ["proposed"])
    check("2: quantity of laughter never promotes", view_examples(a) == [])


# ---------------------------------------------------------------------------
# 3-4. One correction proposes; two events including a strong one promote
# ---------------------------------------------------------------------------

async def test_single_correction_proposes_only(tmp: Path) -> None:
    a = make_agent(tmp)
    await react(a, CORRECTION, text="no, look at the logs")
    cands = a.candidate_ledger.all()
    check("3: correction creates a preference-pair candidate",
          [c["type"] for c in cands] == ["preference_pair"], str(cands))
    check("3: strong, but a single event", len(a.evidence_log.all()) == 1
          and a.evidence_log.all()[0]["strength"] == "strong")
    check("3: not promoted", states(a) == ["proposed"])
    check("3: retrieval view empty", view_pairs(a) == [])
    check("3: legacy feedback pool untouched", not a.feedback_file.exists())
    decision = a._decide_promotion(cands[0]["candidate_id"])
    check("3: policy explains the hold", not decision.promote
          and "1/2" in decision.reason, decision.reason)


async def test_two_events_with_a_strong_one_promote(tmp: Path) -> None:
    a = make_agent(tmp)
    # A rejection first (real evidence, but it authorizes nothing on its own),
    # then the same person says what they actually wanted.
    await react(a, REJECTION, text="thats not what i asked")
    check("4: rejection alone promotes nothing", view_pairs(a) == [])
    await react(a, CORRECTION, text="i meant check the logs")
    check("4: two compatible events, one strong -> promoted",
          "promoted" in states(a), str(states(a)))
    rows = view_pairs(a)
    check("4: pair materialized into the view",
          len(rows) == 1 and rows[0]["better"] == "check the logs first",
          str(rows))
    cand = [c for c in a.candidate_ledger.all() if c["state"] == "promoted"][0]
    check("4: both events cited", len(cand["evidence"]) == 2, str(cand["evidence"]))
    a._reload_views_if_stale()
    check("4: retrieval surfaces the promoted pair",
          "check the logs first" in a._examples_for_prompt("restart server", "called"))


# ---------------------------------------------------------------------------
# 5. Scope isolation
# ---------------------------------------------------------------------------

async def test_incompatible_scopes_are_not_combined(tmp: Path) -> None:
    a = make_agent(tmp)
    await react(a, CORRECTION, text="no, the logs", conv_id="g1")
    await react(a, CORRECTION, text="no, the logs", conv_id="g2")
    cands = a.candidate_ledger.all()
    check("5: one candidate per conversation", len(cands) == 2, str(len(cands)))
    check("5: neither promoted on its own event",
          states(a) == ["proposed", "proposed"], str(states(a)))
    check("5: no cross-conversation evidence sharing",
          all(len(c["evidence"]) == 1 for c in cands),
          str([c["evidence"] for c in cands]))
    check("5: nothing reached retrieval", view_pairs(a) == [])

    base = {"lang": "en", "persona": "B", "persona_hash": "h",
            "persona_version": "", "conv_id": "g1", "mode": "called"}
    check("5: same scope is compatible",
          promotion.scope_compatible(base, dict(base)))
    for key, value in (("lang", "zh"), ("persona", "C"),
                       ("persona_hash", "other"), ("persona_version", "2"),
                       ("conv_id", "g2"), ("mode", "owner")):
        check(f"5: {key} mismatch blocks combination",
              not promotion.scope_compatible(base, dict(base, **{key: value})))
    check("5: conversation scope can be widened by configuration",
          promotion.scope_compatible(base, dict(base, conv_id="g2"),
                                     require_same_conversation=False))


# ---------------------------------------------------------------------------
# 6. Contradiction blocks automatic promotion
# ---------------------------------------------------------------------------

async def test_conflicting_evidence_blocks_promotion(tmp: Path) -> None:
    # (a) Two people want the same reply rewritten two different ways.
    a = make_agent(tmp / "a")
    await react(a, dict(CORRECTION, better="check the logs first"),
                text="use the logs", uid="99", name="rando")   # bystander: not strong
    await react(a, dict(CORRECTION, better="roll it back instead"),
                text="no, roll back", uid="42")                # recipient: strong
    await react(a, REJECTION, text="still wrong", uid="42")     # supports both
    ledger = a.candidate_ledger
    check("6a: both rewrites are on record", len(ledger.all()) == 2)
    check("6a: neither is promoted", states(a) == ["proposed", "proposed"],
          str(states(a)))
    check("6a: retrieval sees neither", view_pairs(a) == [])
    strong_cand = [c for c in ledger.all()
                   if c["better"] == "roll it back instead"][0]
    decision = a._decide_promotion(strong_cand["candidate_id"])
    check("6a: blocked by the conflicting candidate, not by weight",
          not decision.promote and bool(decision.blocked_by)
          and "conflicting" in decision.reason, decision.reason)

    # (b) A laugh and a correction of the same reply cannot both be right.
    b = make_agent(tmp / "b")
    await react(b, POSITIVE, text="lol nice")
    await react(b, dict(CORRECTION), text="no that was wrong", uid="42")
    ex_cand = [c for c in b.candidate_ledger.all()
               if c["type"] == "positive_example"][0]
    decision = b._decide_promotion(ex_cand["candidate_id"])
    check("6b: counter-evidence blocks the example",
          not decision.promote and bool(decision.blocked_by)
          and "disagrees" in decision.reason, decision.reason)


# ---------------------------------------------------------------------------
# 7. A successful retry is supporting evidence
# ---------------------------------------------------------------------------

async def test_retry_provides_supporting_evidence(tmp: Path) -> None:
    a = make_agent(tmp)
    bad = entry("just restart it lol")
    # The user rejects A; the bot's next reply B is tracked as the fix.
    await react(a, REJECTION, text="thats not what i asked", pending=bad)
    check("7: rejection armed the retry window",
          "g1" in a.pending_reactions._awaiting_fix)
    a.pending_reactions.record(
        "g1", reply="check the logs first", ctx_lines=["alex: server is down"],
        mode="called", target_uid="42", mids=["m2"], ts=time.time())
    retry = a.pending_reactions.match("g1", sender_uid="42", at_bot=True,
                                     now=time.time())
    check("7: retry entry carries the rejected reply and its evidence id",
          retry is not None and retry["fixes"]["reply"] == "just restart it lol"
          and bool(retry["fixes"]["evidence_id"]))

    # The user just moves on: that accepts the fix.
    await react(a, {"reaction": "neutral", "accept": False, "reason": "moved on",
                    "better": "", "scenario": ""},
                text="anyway, lunch?", pending=retry)
    kinds = {e["kind"]: e["strength"] for e in a.evidence_log.all()}
    check("7: retry acceptance recorded as strong evidence",
          kinds.get("retry_acceptance") == "strong", str(kinds))
    rows = view_pairs(a)
    check("7: rejection + accepted retry promote the pair",
          len(rows) == 1 and rows[0]["reply"] == "just restart it lol"
          and rows[0]["better"] == "check the logs first", str(rows))
    promoted = [c for c in a.candidate_ledger.all() if c["state"] == "promoted"][0]
    check("7: the retry chain is linked back to the complaint",
          any(e.get("parent_event_id") for e in a.evidence_log.all()))
    check("7: promotion cites two events", len(promoted["evidence"]) == 2,
          str(promoted["evidence"]))


# ---------------------------------------------------------------------------
# 8-9. Idempotence and replay
# ---------------------------------------------------------------------------

async def test_duplicate_events_are_idempotent(tmp: Path) -> None:
    a = make_agent(tmp)
    for _ in range(3):
        await react(a, CORRECTION, text="no, look at the logs")
    check("8: identical reactions collapse to one event",
          len(a.evidence_log.all()) == 1, str(len(a.evidence_log.all())))
    check("8: and to one candidate", len(a.candidate_ledger.all()) == 1)
    check("8: a repeat cannot promote by itself", states(a) == ["proposed"])

    log = a.evidence_log
    ev = log.all()[0]
    check("8: append reports the duplicate", log.append(dict(ev)) is False)
    check("8: log length unchanged", len(log.all()) == 1)

    # A rejected candidate stays rejected when the same reaction arrives again.
    cid = a.candidate_ledger.all()[0]["candidate_id"]
    a.candidate_ledger.reject(cid, ts="2026-07-25T10:00:00", actor="admin",
                              reason="not a real correction")
    await react(a, CORRECTION, text="no, look at the logs")
    check("8: a repeat does not resurrect a rejected candidate",
          states(a) == ["rejected"], str(states(a)))


async def test_restart_and_replay_are_identical(tmp: Path) -> None:
    a = make_agent(tmp)
    await react(a, REJECTION, text="thats not what i asked")
    await react(a, CORRECTION, text="i meant check the logs")
    await react(a, POSITIVE, text="haha ok that one landed",
                reply="fine, checking the logs")

    def normalize(ledger):
        return sorted(
            (c["candidate_id"], c.get("type"), c.get("state"),
             tuple(c.get("evidence") or []),
             tuple((h.get("state"), h.get("actor")) for h in c.get("history") or []))
            for c in ledger.all())

    live = normalize(a.candidate_ledger)
    replayed = normalize(candidates.CandidateLedger(a.candidate_ledger_file))
    check("9: replaying the log reproduces the projection", live == replayed,
          f"{live}\n{replayed}")

    fresh = make_agent(tmp)          # a restarted process, same files
    check("9: a restart sees the same candidates",
          normalize(fresh.candidate_ledger) == live)
    check("9: and the same evidence",
          [e["event_id"] for e in fresh.evidence_log.all()]
          == [e["event_id"] for e in a.evidence_log.all()])
    before = view_pairs(a)
    fresh._rebuild_promoted_views()
    check("9: rebuilding the view from the log is a no-op",
          view_pairs(fresh) == before, str(before))
    fresh._reload_views_if_stale()
    a._reload_views_if_stale()
    check("9: retrieval output matches across the restart",
          fresh._examples_for_prompt("restart server", "called")
          == a._examples_for_prompt("restart server", "called"))


# ---------------------------------------------------------------------------
# 10-11. Authority can be taken back
# ---------------------------------------------------------------------------

async def test_rollback_removes_from_retrieval(tmp: Path) -> None:
    a = make_agent(tmp)
    await react(a, REJECTION, text="thats not what i asked")
    await react(a, CORRECTION, text="i meant check the logs")
    a._reload_views_if_stale()
    check("10: promoted pair is retrievable",
          "check the logs first" in a._examples_for_prompt("restart", "called"))
    cid = [c["candidate_id"] for c in a.candidate_ledger.all()
           if c["state"] == "promoted"][0]

    ok = a.candidate_ledger.rollback(cid, ts="2026-07-25T12:00:00",
                                     actor="admin", reason="wrong after all")
    a._rebuild_promoted_views()
    a._reload_views_if_stale()
    check("10: rollback accepted", ok is True)
    check("10: view no longer carries it", view_pairs(a) == [])
    check("10: retrieval no longer surfaces it",
          "check the logs first" not in a._examples_for_prompt("restart", "called"))
    check("10: history survives the rollback",
          [h["state"] for h in a.candidate_ledger.history(cid)]
          == ["promoted", "rolled_back"])
    check("10: the candidate itself is still on record",
          a.candidate_ledger.get(cid) is not None)
    check("10: the evidence is still on record", len(a.evidence_log.all()) == 2)


async def test_supersession_replaces_the_active_preference(tmp: Path) -> None:
    a = make_agent(tmp)
    await react(a, REJECTION, text="thats not what i asked")
    await react(a, CORRECTION, text="i meant check the logs")
    old = [c["candidate_id"] for c in a.candidate_ledger.all()
           if c["state"] == "promoted"][0]
    # A better rewrite for the same reply arrives later.
    await react(a, dict(CORRECTION, better="logs first, then restart if clean"),
                text="actually phrase it like this", uid="42")
    new = [c["candidate_id"] for c in a.candidate_ledger.all()
           if c["candidate_id"] != old][0]
    check("11: the replacement is not promoted automatically",
          a.candidate_ledger.get(new)["state"] == "proposed")

    ok = a.candidate_ledger.supersede(old, new, ts="2026-07-25T12:00:00",
                                      actor="admin", reason="better wording")
    a._rebuild_promoted_views()
    a._reload_views_if_stale()
    check("11: supersede accepted", ok is True)
    check("11: old candidate deactivated",
          a.candidate_ledger.get(old)["state"] == "superseded")
    check("11: new candidate active",
          a.candidate_ledger.get(new)["state"] == "promoted")
    rows = view_pairs(a)
    check("11: exactly one active row, the replacement",
          len(rows) == 1 and rows[0]["better"] == "logs first, then restart if clean",
          str(rows))
    check("11: both records preserved",
          a.candidate_ledger.get(old) is not None
          and a.candidate_ledger.get(new).get("supersedes") == old)
    check("11: superseding a superseded candidate is refused",
          a.candidate_ledger.supersede(old, new, ts="t", actor="admin") is False)


# ---------------------------------------------------------------------------
# 12. Both logs are append-only
# ---------------------------------------------------------------------------

async def test_logs_are_append_only(tmp: Path) -> None:
    a = make_agent(tmp)
    await react(a, REJECTION, text="thats not what i asked")
    await react(a, CORRECTION, text="i meant check the logs")
    ev_before = a.evidence_file.read_bytes()
    led_before = a.candidate_ledger_file.read_bytes()
    lines_before = len(led_before.splitlines())

    cid = [c["candidate_id"] for c in a.candidate_ledger.all()
           if c["state"] == "promoted"][0]
    a.candidate_ledger.rollback(cid, ts="t1", actor="admin", reason="no")
    a.candidate_ledger.promote(cid, ts="t2", actor="admin", reason="yes again")
    a.candidate_ledger.reject(cid, ts="t3", actor="admin", reason="final answer")
    await react(a, POSITIVE, text="different reaction entirely")

    check("12: evidence log only ever grew",
          a.evidence_file.read_bytes().startswith(ev_before)
          and len(a.evidence_file.read_bytes()) > len(ev_before))
    led_after = a.candidate_ledger_file.read_bytes()
    check("12: ledger only ever grew", led_after.startswith(led_before))
    check("12: every transition is its own row",
          len(led_after.splitlines()) == lines_before + 4,
          f"{lines_before} -> {len(led_after.splitlines())}")
    check("12: the full lifecycle is readable back",
          [h["state"] for h in a.candidate_ledger.history(cid)]
          == ["promoted", "rolled_back", "promoted", "rejected"])
    # The view is derived, so it only reflects the log once re-derived — every
    # mutation path in the agent and the CLI does that for you.
    a._rebuild_promoted_views()
    check("12: a rejected candidate is not in the rebuilt view",
          all(r.get("candidate_id") != cid for r in view_pairs(a)),
          str(view_pairs(a)))
    check("12: illegal transitions write nothing",
          a.candidate_ledger.rollback(cid, ts="t4", actor="admin") is False
          and a.candidate_ledger_file.read_bytes() == led_after)


# ---------------------------------------------------------------------------
# 13. Backward compatibility
# ---------------------------------------------------------------------------

def test_legacy_feedback_still_loads(tmp: Path) -> None:
    a = make_agent(tmp)
    # A pair approved by hand through prompt_lab.py (no "src" marker), a
    # machine pair banked by a pre-ledger build, and a seed row.
    a.feedback_seed_file.write_text(json.dumps(
        {"scenario": "seed", "context": ["u: hi"], "mode": "called",
         "reply": "seed bad", "rating": "better", "better": "seed good"}) + "\n",
        encoding="utf-8")
    a.feedback_file.write_text("\n".join([
        json.dumps({"scenario": "manual", "context": ["u: hi"], "mode": "called",
                    "reply": "manual bad", "rating": "better",
                    "better": "manual good"}),
        json.dumps({"scenario": "legacy", "context": ["u: hi"], "mode": "called",
                    "reply": "legacy bad", "rating": "better",
                    "better": "legacy good", "src": "user_reaction"}),
    ]) + "\n", encoding="utf-8")
    a.examples_file.write_text(json.dumps(
        {"scenario": "legacy", "mode": "called", "context": ["u: hi"],
         "reply": "legacy example", "score": 5, "src": "user_reaction"}) + "\n",
        encoding="utf-8")
    before = a.examples_file.read_bytes(), a.feedback_file.read_bytes()

    block = a._examples_for_prompt("hi", "called")
    for label in ("seed good", "manual good", "legacy good", "legacy example"):
        check(f"13: {label} still reaches the prompt", label in block)
    check("13: legacy rows are left byte-identical",
          (a.examples_file.read_bytes(), a.feedback_file.read_bytes()) == before)
    check("13: legacy rows are not reclassified into the ledger",
          a.candidate_ledger.all() == [])


async def test_legacy_rows_still_retractable(tmp: Path) -> None:
    """A rejection must still pull a pre-ledger auto row out of the pool — that
    deletion is the old design's only way to revoke, and a deployment that
    learned before the ledger existed still has such rows."""
    a = make_agent(tmp)
    a.examples_file.write_text(json.dumps(
        {"scenario": "legacy", "mode": "called", "context": ["u: hi"],
         "reply": "just restart it lol", "score": 5, "src": "user_reaction"}
    ) + "\n", encoding="utf-8")
    a._reload_examples_if_stale()
    check("13b: legacy auto row is retrievable",
          "just restart it lol" in a._examples_for_prompt("restart", "called"))
    await react(a, CORRECTION, text="no, look at the logs")
    a._examples_mtime = 0.0
    a._reload_examples_if_stale()
    check("13b: an accepted correction retracts it",
          "just restart it lol" not in a._examples_for_prompt("restart", "called"))


# ---------------------------------------------------------------------------
# 14. The suite never touches real state
# ---------------------------------------------------------------------------

def test_paths_never_touch_real_runtime_state(tmp: Path) -> None:
    a = make_agent(tmp)
    real = runtime_dir().resolve()
    paths = {
        "evidence": a.evidence_file, "ledger": a.candidate_ledger_file,
        "examples view": a.promoted_examples_file,
        "feedback view": a.promoted_feedback_file,
        "examples": a.examples_file, "feedback": a.feedback_file,
        "legacy candidate pool": a.example_candidates.path,
        "audit": a.candidates_file, "eval": a.eval_file,
    }
    for label, path in paths.items():
        resolved = Path(path).resolve()
        check(f"14: {label} is inside the temp dir",
              str(resolved).startswith(str(tmp.resolve())), str(resolved))
        check(f"14: {label} is not under the real runtime dir",
              real not in resolved.parents, str(resolved))


def main() -> int:
    real = runtime_dir()
    before = sorted(p.name for p in real.glob("*")) if real.exists() else []

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        asyncio.run(test_one_positive_promotes_nothing(tmp / "t1"))
        asyncio.run(test_repeated_weak_promotes_nothing(tmp / "t2"))
        asyncio.run(test_single_correction_proposes_only(tmp / "t3"))
        asyncio.run(test_two_events_with_a_strong_one_promote(tmp / "t4"))
        asyncio.run(test_incompatible_scopes_are_not_combined(tmp / "t5"))
        asyncio.run(test_conflicting_evidence_blocks_promotion(tmp / "t6"))
        asyncio.run(test_retry_provides_supporting_evidence(tmp / "t7"))
        asyncio.run(test_duplicate_events_are_idempotent(tmp / "t8"))
        asyncio.run(test_restart_and_replay_are_identical(tmp / "t9"))
        asyncio.run(test_rollback_removes_from_retrieval(tmp / "t10"))
        asyncio.run(test_supersession_replaces_the_active_preference(tmp / "t11"))
        asyncio.run(test_logs_are_append_only(tmp / "t12"))
        test_legacy_feedback_still_loads(tmp / "t13")
        asyncio.run(test_legacy_rows_still_retractable(tmp / "t13b"))
        test_paths_never_touch_real_runtime_state(tmp / "t14")

    after = sorted(p.name for p in real.glob("*")) if real.exists() else []
    check("14: the real runtime directory was not written",
          before == after, f"{before} -> {after}")

    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
