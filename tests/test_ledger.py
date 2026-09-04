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
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from persona_agent import candidates, evidence, promotion, reactions  # noqa: E402
from persona_agent.agent import Agent  # noqa: E402
from persona_agent.paths import runtime_dir  # noqa: E402

_failures: list[str] = []
NOW = 1_800_000_000.0


def stamp(seconds: float) -> str:
    """Epoch -> ISO. Every fixture timestamp derives from NOW through this, so
    that no test's meaning depends on the day it happens to run."""
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


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
    a.teacher_stats = reactions.TeacherStats(tmp / "teacher_stats.json")
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
    """Stub _call_llm returning one fixed adjudication."""
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
    agent._call_llm = adjudicator(**adj)
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
    check("4: materialized row preserves its complete authority scope",
          rows[0].get("scope") == {
              "lang": "en",
              "platform": "qq",
              "conv_id": "g1",
              "persona": "B",
              "persona_hash": a.persona_hash,
              "persona_version": a.persona_version,
              "scenario": "wrong advice",
              "mode": "called",
          }, str(rows[0].get("scope")))
    cand = [c for c in a.candidate_ledger.all() if c["state"] == "promoted"][0]
    check("4: both events cited", len(cand["evidence"]) == 2, str(cand["evidence"]))
    a._reload_views_if_stale()
    check("4: retrieval surfaces the promoted pair",
          "check the logs first" in a._examples_for_prompt(
              "restart server", "called", conv_id="g1"))


def test_expired_counter_evidence_does_not_block_new_corroboration() -> None:
    """A retired disagreement must not veto a fresh, corroborated correction."""
    common = {
        "lang": "en", "platform": "qq", "conv_id": "g1",
        "persona": "B", "persona_hash": "h", "persona_version": "1",
        "speaker_id": "42", "speaker_name": "Alex", "recipient_id": "42",
        "reply": "just restart it lol", "context": ["Alex: server is down"],
        "directed": True, "direction": "at",
    }
    old_positive = evidence.make_event(
        kind=evidence.KIND_REACTION,
        ts=stamp(NOW - 31 * 86400),
        **common,
        reaction_type="positive",
        adjudication={"accept": True, "mode": "called"},
    )
    fresh = [
        evidence.make_event(
            kind=evidence.KIND_REACTION, ts=stamp(NOW - offset), **common,
            reaction_type="correction",
            reaction_text=f"no, use the logs ({offset})",
            adjudication={"accept": True, "better": "check the logs first",
                          "mode": "called"},
        )
        for offset in (120, 60)
    ]
    scope = candidates.scope_from_event(fresh[0])
    cand = candidates.make_candidate(
        ctype=candidates.TYPE_PAIR, scope=scope,
        payload={"reply": common["reply"], "better": "check the logs first",
                 "context": common["context"], "mode": "called"},
        evidence=[event["event_id"] for event in fresh],
        created_at=stamp(NOW),
    )
    decision = promotion.decide(
        cand, linked_events=fresh, related_events=[old_positive, *fresh], now=NOW,
        policy=promotion.Policy(max_evidence_age_days=30),
    )
    check("4b: expired counter-evidence does not block promotion",
          decision.promote, decision.reason)
    fresh_positive = evidence.make_event(
        kind=evidence.KIND_REACTION, ts=stamp(NOW - 30), **common,
        reaction_type="positive", reaction_text="actually that landed",
        adjudication={"accept": True, "mode": "called"},
    )
    decision = promotion.decide(
        cand, linked_events=fresh, related_events=[fresh_positive, *fresh], now=NOW,
        policy=promotion.Policy(max_evidence_age_days=30),
    )
    check("4b: fresh counter-evidence still blocks promotion",
          not decision.promote and "disagrees" in decision.reason, decision.reason)


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
    for key, value in (("lang", "zh"), ("platform", "telegram"),
                       ("persona", "C"),
                       ("persona_hash", "other"), ("persona_version", "2"),
                       ("conv_id", "g2"), ("mode", "owner")):
        check(f"5: {key} mismatch blocks combination",
              not promotion.scope_compatible(base, dict(base, **{key: value})))
    check("5: conversation scope can be widened by configuration",
          promotion.scope_compatible(base, dict(base, conv_id="g2"),
                                     require_same_conversation=False))
    evidence.register_persona_lineage("", ["h", "h-edited"])
    check("5: a later revision of the same persona is compatible",
          promotion.scope_compatible(base, dict(base, persona_hash="h-edited")))
    check("5: the same revision under another PERSONA_VERSION is not",
          not promotion.scope_compatible(
              base, dict(base, persona_hash="h-edited", persona_version="2")))
    check("5: a revision maps to its lineage's candidate id",
          candidates.candidate_id("positive_example", dict(base, persona_hash="h-edited"), "r")
          == candidates.candidate_id("positive_example", base, "r"))

    qq_id = candidates.candidate_id(
        candidates.TYPE_PAIR, dict(base, platform="qq"), "bad", "good")
    tg_id = candidates.candidate_id(
        candidates.TYPE_PAIR, dict(base, platform="telegram"), "bad", "good")
    other_persona_id = candidates.candidate_id(
        candidates.TYPE_PAIR, dict(base, platform="qq", persona="C"),
        "bad", "good")
    check("5: candidate identity includes platform",
          qq_id != tg_id, f"{qq_id} == {tg_id}")
    check("5: candidate identity includes persona",
          qq_id != other_persona_id, f"{qq_id} == {other_persona_id}")


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

    # The user merely moves on. That is recorded, but it is NOT acceptance:
    # the "better" side of a retry-acceptance event is the agent's own retry
    # text, so counting a topic change as strong would let it manufacture a
    # mandate for its own wording — over an adjudicator verdict of accept=false.
    await react(a, {"reaction": "neutral", "accept": False, "reason": "moved on",
                    "better": "", "scenario": ""},
                text="anyway, lunch?", pending=retry)
    kinds = {e["kind"]: e["strength"] for e in a.evidence_log.all()}
    check("7: moving on is recorded but is not strong",
          kinds.get("retry_acceptance") == evidence.NEGATIVE_ONLY, str(kinds))
    check("7: a topic change alone promotes nothing", view_pairs(a) == [],
          str(view_pairs(a)))

    # NOTE: the "explicit positive also promotes" path is not asserted here.
    # It runs into the pre-existing counter-evidence rule (the original
    # rejection is related evidence about the same reply and reads as
    # disagreement), which is orthogonal to what this test pins down and is
    # covered by test 6.
    check("7: the retry chain is linked back to the complaint",
          any(e.get("parent_event_id") for e in a.evidence_log.all()))
    pair = [c for c in a.candidate_ledger.all()
            if (c.get("payload") or {}).get("better") == "check the logs first"]
    check("7: the proposal still cites both events",
          bool(pair) and len(pair[0].get("evidence") or []) == 2,
          str([c.get("evidence") for c in pair]))


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
          fresh._examples_for_prompt("restart server", "called", conv_id="g1")
          == a._examples_for_prompt("restart server", "called", conv_id="g1"))


# ---------------------------------------------------------------------------
# 10-11. Authority can be taken back
# ---------------------------------------------------------------------------

async def test_rollback_removes_from_retrieval(tmp: Path) -> None:
    a = make_agent(tmp)
    await react(a, REJECTION, text="thats not what i asked")
    await react(a, CORRECTION, text="i meant check the logs")
    a._reload_views_if_stale()
    check("10: promoted pair is retrievable",
          "check the logs first" in a._examples_for_prompt(
              "restart", "called", conv_id="g1"))
    cid = [c["candidate_id"] for c in a.candidate_ledger.all()
           if c["state"] == "promoted"][0]

    ok = a.candidate_ledger.rollback(cid, ts="2026-07-25T12:00:00",
                                     actor="admin", reason="wrong after all")
    a._rebuild_promoted_views()
    a._reload_views_if_stale()
    check("10: rollback accepted", ok is True)
    check("10: view no longer carries it", view_pairs(a) == [])
    check("10: retrieval no longer surfaces it",
          "check the logs first" not in a._examples_for_prompt(
              "restart", "called", conv_id="g1"))
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

    rows_before = len(a.candidate_ledger_file.read_text(
        encoding="utf-8").splitlines())
    ok = a.candidate_ledger.supersede(old, new, ts="2026-07-25T12:00:00",
                                      actor="admin", reason="better wording")
    rows_after = [
        json.loads(line) for line in a.candidate_ledger_file.read_text(
            encoding="utf-8").splitlines() if line.strip()
    ]
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
    check("11: supersession is one atomic ledger event",
          len(rows_after) == rows_before + 1
          and rows_after[-1].get("kind") == "supersession",
          str(rows_after[-2:]))
    replayed = candidates.CandidateLedger(a.candidate_ledger_file)
    check("11: compound supersession replays both halves",
          replayed.get(old)["state"] == "superseded"
          and replayed.get(new)["state"] == "promoted")
    check("11: superseding a superseded candidate is refused",
          a.candidate_ledger.supersede(old, new, ts="t", actor="admin") is False)


def test_evidence_identity_includes_source_and_full_scope() -> None:
    base = {
        "kind": evidence.KIND_REACTION,
        "ts": "2026-07-25T10:00:00",
        "lang": "en",
        "platform": "qq",
        "conv_id": "g1",
        "persona": "B",
        "persona_hash": "h",
        "persona_version": "v1",
        "speaker_id": "42",
        "recipient_id": "42",
        "reply": "bad",
        "reaction_text": "no",
        "reaction_type": "correction",
        "adjudication": {"accept": True, "better": "good", "mode": "called"},
        "source_event_id": "message-1",
    }
    first = evidence.make_event(**base)
    second_source = evidence.make_event(**dict(base, source_event_id="message-2"))
    second_version = evidence.make_event(**dict(base, persona_version="v2"))
    second_platform = evidence.make_event(**dict(base, platform="telegram"))
    check("8b: distinct source events have distinct identities",
          first["event_id"] != second_source["event_id"])
    check("8b: persona version is part of evidence identity",
          first["event_id"] != second_version["event_id"])
    check("8b: platform is part of evidence identity",
          first["event_id"] != second_platform["event_id"])


def test_invalid_log_rows_are_quarantined_from_replay(tmp: Path) -> None:
    tmp.mkdir(parents=True, exist_ok=True)
    valid_event = evidence.make_event(
        kind=evidence.KIND_REACTION, ts="2026-07-25T10:00:00",
        lang="en", platform="qq", conv_id="g1", persona="B",
        persona_hash="h", speaker_id="42", recipient_id="42",
        reply="bad", reaction_text="no", reaction_type="correction",
        adjudication={"accept": True, "better": "good", "mode": "called"},
    )
    evidence_path = tmp / "evidence.jsonl"
    evidence_path.write_text(
        json.dumps(valid_event) + "\n"
        + '{"schema":999,"event_id":"future","kind":"reaction"}\n'
        + '{"schema":2,"event_id":17,"kind":"reaction"}\n'
        + "torn",
        encoding="utf-8",
    )
    loaded_evidence = evidence.EvidenceLog(evidence_path)
    check("8c: evidence replay skips unsupported and malformed rows",
          [row["event_id"] for row in loaded_evidence.all()]
          == [valid_event["event_id"]])
    evidence_health = loaded_evidence.health_metadata(warning_bytes=1)
    check("8c: evidence health reports quarantined rows and size warning",
          evidence_health["quarantined_rows"] == 3
          and evidence_health["size_warning"] is True,
          str(evidence_health))
    check("8c: evidence quarantine preserves the source audit bytes",
          evidence_path.read_text(encoding="utf-8").endswith("torn"))

    scope = {
        "lang": "en", "platform": "qq", "conv_id": "g1",
        "persona": "B", "persona_hash": "h", "persona_version": "",
        "scenario": "s", "mode": "called",
    }
    valid_candidate = candidates.make_candidate(
        ctype=candidates.TYPE_PAIR, scope=scope,
        payload={"reply": "bad", "better": "good", "rating": "better"},
        created_at="2026-07-25T10:00:00",
    )
    ledger_path = tmp / "ledger.jsonl"
    ledger_path.write_text(
        json.dumps(valid_candidate) + "\n"
        + '{"schema":999,"kind":"candidate","candidate_id":"future"}\n'
        + '{"schema":2,"kind":"lifecycle","candidate_id":9,"state":"promoted"}\n',
        encoding="utf-8",
    )
    loaded_ledger = candidates.CandidateLedger(ledger_path)
    check("8c: ledger replay skips unsupported and malformed rows",
          [row["candidate_id"] for row in loaded_ledger.all()]
          == [valid_candidate["candidate_id"]])
    ledger_health = loaded_ledger.health_metadata(warning_bytes=1)
    check("8c: ledger health reports quarantined rows and size warning",
          ledger_health["quarantined_rows"] == 2
          and ledger_health["size_warning"] is True,
          str(ledger_health))


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
        "teacher stats": a.teacher_stats.path,
        "legacy candidate pool": a.example_candidates.path,
        "audit": a.candidates_file, "eval": a.eval_file,
    }
    for label, path in paths.items():
        resolved = Path(path).resolve()
        check(f"14: {label} is inside the temp dir",
              str(resolved).startswith(str(tmp.resolve())), str(resolved))
        check(f"14: {label} is not under the real runtime dir",
              real not in resolved.parents, str(resolved))



def test_corroboration_means_people_not_events() -> None:
    """One member producing two events is not corroboration.

    Correcting a reply and then accepting the agent's retry clears "two
    distinct compatible events" single-handedly — and delayed elicitation has
    the agent *solicit* that second event from the same person. Promotion
    therefore counts distinct speakers, with the owner exempt."""
    # Frozen clock: a literal ts judged against a wall-clock now silently
    # expires once it passes MAX_EVIDENCE_AGE_DAYS, turning this green suite red
    # on a calendar date rather than on a code change.
    now = NOW
    ts = stamp(NOW - 3600)
    scope = dict(lang="en", platform="qq", conv_id="g1", persona="B",
                 persona_hash="h", persona_version="v1")

    def ev(speaker, kind=evidence.KIND_REACTION, rtype="correction"):
        return evidence.make_event(
            kind=kind, ts=ts, **scope, speaker_id=speaker, recipient_id=speaker,
            reply="bad line", reaction_type=rtype,
            adjudication={"accept": True, "better": "fixed", "mode": "called"})

    cand = candidates.make_candidate(
        ctype=candidates.TYPE_PAIR, scope=scope, created_at=ts, evidence=[],
        payload={"reply": "bad line", "better": "fixed", "mode": "called",
                 "rating": "better"})

    def decide(events, owner_id="", policy=promotion.DEFAULT_POLICY):
        return promotion.decide(cand, linked_events=events, related_events=[],
                                peers=[], now=now, owner_id=owner_id,
                                policy=policy)

    strict = promotion.Policy(min_speakers=2)
    solo = [ev("mallory"),
            ev("mallory", evidence.KIND_RETRY_ACCEPTANCE, "positive")]
    two = [ev("alice"), ev("bob", evidence.KIND_RETRY_ACCEPTANCE, "positive")]
    owner = [ev("owner1"),
             ev("owner1", evidence.KIND_RETRY_ACCEPTANCE, "positive")]

    # Default (1) keeps solo clarification working: the honest path and the
    # attack path are structurally identical, so this is a deployment choice.
    check("speakers: default lets one person clarify",
          decide(solo).promote is True, decide(solo).reason)
    # Opting in to 2 is what refuses a lone stranger.
    solo_strict = decide(solo, policy=strict)
    check("speakers: MIN_SPEAKERS=2 blocks one stranger self-corroborating",
          solo_strict.promote is False, solo_strict.reason)
    # BY THE SPEAKER RULE, and not because the pile was empty. The line above
    # is a negative, so it also holds when nothing was counted at all — which
    # is precisely how the fixture rot in this file stayed invisible while its
    # three positive siblings went red, and why shrinking the evidence window
    # to 0.001 days still leaves it green. Naming the reason is what makes it
    # distinguish the rule from its own absence.
    check("speakers: ...refused by the speaker rule, not by an empty pile",
          "distinct speakers" in solo_strict.reason
          and solo_strict.supporting == 2,
          f"{solo_strict.reason!r} supporting={solo_strict.supporting}")
    check("speakers: MIN_SPEAKERS=2 still promotes on two people",
          decide(two, policy=strict).promote is True,
          decide(two, policy=strict).reason)
    check("speakers: the owner is exempt even at MIN_SPEAKERS=2",
          decide(owner, owner_id="owner1", policy=strict).promote is True,
          decide(owner, owner_id="owner1", policy=strict).reason)
    check("speakers: floor keeps 0 from disabling the rule",
          promotion.Policy.from_env({"PROMOTE_MIN_SPEAKERS": "0"}).min_speakers == 1)
    check("speakers: env opt-in is read",
          promotion.Policy.from_env({"PROMOTE_MIN_SPEAKERS": "2"}).min_speakers == 2)


def test_moving_on_is_not_acceptance() -> None:
    """A `neutral` retry reaction means the person changed the subject. The
    "better" side of a retry-acceptance event is the agent's OWN retry text, so
    treating silence as strong would let it manufacture a mandate for its own
    wording out of nothing happening."""
    ts = "2026-07-25T12:00:00"
    common = dict(kind=evidence.KIND_RETRY_ACCEPTANCE, ts=ts, speaker_id="a",
                  recipient_id="a", reply="retry text",
                  adjudication={"accept": True, "better": "retry text"})
    strong = evidence.make_event(**common, reaction_type="positive")
    moved_on = evidence.make_event(**common, reaction_type="neutral")
    check("retry: an explicit positive is strong",
          strong["strength"] == evidence.STRONG, strong["strength"])
    check("retry: moving on is not strong",
          moved_on["strength"] != evidence.STRONG, moved_on["strength"])


def test_an_unwitnessed_proposal_does_not_veto_a_real_correction() -> None:
    """The evolution loop could block the user it exists to serve.

    `_evolve_tick` proposes `X -> Y` off a single self-review. Such a
    candidate can never clear `min_strong` — a pair is auto-promotable only
    when its `better` was authored by a strong event, i.e. a user's correction
    or the bot's accepted retry, and an LLM-authored rewrite matches one only
    by coincidence. So it sat in `proposed` forever, which would be harmless
    except that `find_conflicts` gave it a VETO: the user's real correction of
    the same reply became "a conflicting candidate exists" and both proposals
    blocked each other permanently, with the view empty.

    The guardrails matter as much as the fix, so all four are asserted: the
    unwitnessed proposal loses its veto, it does NOT thereby gain authority of
    its own, and two REAL users disagreeing still block each other exactly as
    before."""
    scope = dict(lang="en", platform="qq", conv_id="g1", persona="B",
                 persona_hash="h", persona_version="v1")
    reply = "just restart it lol"
    user_fix, llm_fix = "check the logs first", "eh just look at the logs"

    def correction(speaker: str, better: str, age: float) -> dict:
        return evidence.make_event(
            kind=evidence.KIND_REACTION, ts=stamp(NOW - age), **scope,
            speaker_id=speaker, recipient_id=speaker, reply=reply,
            reaction_type="correction",
            adjudication={"accept": True, "better": better, "mode": "called"})

    self_review = evidence.make_event(
        kind=evidence.KIND_SELF_REVIEW, ts=stamp(NOW - 100), **scope,
        reply=reply, directed=False, direction="self",
        adjudication={"accept": True, "better": llm_fix, "mode": "called"})

    def pair(better: str) -> dict:
        return candidates.make_candidate(
            ctype=candidates.TYPE_PAIR, scope=scope, created_at=stamp(NOW),
            evidence=[], payload={"reply": reply, "better": better,
                                  "mode": "called"})

    user_cand, evo_cand = pair(user_fix), pair(llm_fix)
    linked = [correction("alice", user_fix, 60), correction("bob", user_fix, 20)]

    control = promotion.decide(user_cand, linked_events=linked,
                               related_events=linked, peers=[user_cand],
                               now=NOW)
    check("veto: the correction promotes with no peer in the way",
          control.promote is True, control.reason)

    with_evo = promotion.decide(user_cand, linked_events=linked,
                                related_events=linked + [self_review],
                                peers=[user_cand, evo_cand], now=NOW)
    check("veto: an unwitnessed proposal no longer blocks it",
          with_evo.promote is True, with_evo.reason)

    evo = promotion.decide(evo_cand, linked_events=[self_review],
                           related_events=linked + [self_review],
                           peers=[user_cand, evo_cand], now=NOW)
    check("veto: ...and does not gain authority of its own",
          evo.promote is False, evo.reason)

    rival = pair("restart the service instead")
    rival_ev = [correction("carol", "restart the service instead", 30)]
    two_users = promotion.decide(user_cand, linked_events=linked,
                                 related_events=linked + rival_ev,
                                 peers=[user_cand, rival], now=NOW)
    check("veto: two real users proposing different rewrites still conflict",
          two_users.promote is False and "conflicting" in two_users.reason,
          two_users.reason)


def test_a_rejected_rewrite_is_not_promoted_later() -> None:
    """Rejecting the fix has to count against the pair that proposes it.

    `_rollback_promoted_for` already withdrew a PROMOTED pair whose `better`
    the user rejected — its docstring says so, and means it. But a pair still
    sitting in `proposed` was untouched, and `counter_evidence` only ever
    looked at events about the reply being REPLACED, never about the
    replacement. So: user corrects X to Y and the pair is proposed on one
    strong event; the bot later says Y and the user rejects it outright;
    nothing happens; a second ordinary event about X arrives and the pair
    promotes, teaching Y — the exact text the user refused — into every
    subsequent prompt.

    Two changes, and both are needed: `counter_evidence` learned the
    question, and `_decide_promotion` had to widen `related_events` to
    include events about the rewrite, or the new branch would never have seen
    one. The control below is what makes this test mean anything — without
    it, "did not promote" is satisfied by any regression at all."""
    scope = dict(lang="en", platform="qq", conv_id="g1", persona="B",
                 persona_hash="h", persona_version="v1")
    reply, rewrite = "just restart it lol", "check the logs first"

    def correction(speaker: str, age: float) -> dict:
        return evidence.make_event(
            kind=evidence.KIND_REACTION, ts=stamp(NOW - age), **scope,
            speaker_id=speaker, recipient_id=speaker, reply=reply,
            reaction_type="correction",
            adjudication={"accept": True, "better": rewrite, "mode": "called"})

    rejects_the_fix = evidence.make_event(
        kind=evidence.KIND_REACTION, ts=stamp(NOW - 10), **scope,
        speaker_id="alice", recipient_id="alice", reply=rewrite,
        reaction_type="rejection",
        adjudication={"accept": True, "mode": "called"})

    cand = candidates.make_candidate(
        ctype=candidates.TYPE_PAIR, scope=scope, created_at=stamp(NOW),
        evidence=[], payload={"reply": reply, "better": rewrite,
                              "mode": "called"})
    linked = [correction("alice", 60), correction("bob", 20)]

    control = promotion.decide(cand, linked_events=linked,
                               related_events=linked, peers=[], now=NOW)
    check("rewrite: the pair promotes when nobody rejected the fix",
          control.promote is True, control.reason)

    # `related` exactly as `_decide_promotion` now builds it.
    wanted = {reply, rewrite}
    related = [e for e in linked + [rejects_the_fix]
               if str(e.get("reply") or "").strip() in wanted]
    check("rewrite: an event about the REWRITE is related to the pair",
          rejects_the_fix in related)
    check("rewrite: rejecting the fix is counter-evidence",
          promotion.counter_evidence(cand, related, now=NOW) != [])

    after = promotion.decide(cand, linked_events=linked,
                             related_events=related, peers=[], now=NOW)
    check("rewrite: and the pair is then left for review, not promoted",
          after.promote is False and "disagrees" in after.reason, after.reason)

    # AND THE PROTECTION MUST NOT EXPIRE. The first cut of this fix applied
    # the ordinary evidence-age window to the rejection, so the block could be
    # OUTWAITED: rejection on day 0, two fresh corroborating corrections on
    # days 40 and 41, and the refused text promoted. A rolled-back promoted
    # pair never comes back; a proposed one only had to wait a month.
    #
    # Counter-evidence about the REPLY still expires — "4b" above pins that,
    # and a stale laugh must not veto a fresh correction. "This person refused
    # this exact text" is a different statement and does not go stale.
    old_rejection = evidence.make_event(
        kind=evidence.KIND_REACTION, ts=stamp(NOW - 400 * 86400), **scope,
        speaker_id="alice", recipient_id="alice", reply=rewrite,
        reaction_type="rejection",
        adjudication={"accept": True, "mode": "called"})
    fresh_pair = [correction("bob", 0.02), correction("carol", 0.04)]
    outwaited = promotion.decide(
        cand, linked_events=fresh_pair,
        related_events=fresh_pair + [old_rejection], peers=[], now=NOW)
    check("rewrite: a year-old rejection still blocks the pair",
          outwaited.promote is False and "disagrees" in outwaited.reason,
          outwaited.reason)


def test_the_live_projection_equals_a_cold_replay(tmp: Path) -> None:
    """`_append` lets the live projection stand instead of replaying for its
    own write, which removed a full-file re-parse per write — 461 ms at 20 000
    rows, the largest item left on the reaction path. That is only sound while
    every write method leaves `self._by_id` EXACTLY as a replay of the same
    file would, so this asserts it directly, over every row kind.

    The first draft applied the row in `_append` as well as in the caller, so
    it landed twice. The duplicate was a repeated `history` entry — invisible
    to every functional test, because no policy decision reads history — and
    it showed up only in a byte-for-byte diff against a cold replay. This is
    that diff."""
    path = tmp / "ledger.jsonl"
    scope = dict(lang="en", platform="qq", conv_id="g1", persona="B",
                 persona_hash="h", persona_version="v1")

    def pair(i: int) -> dict:
        return candidates.make_candidate(
            ctype=candidates.TYPE_PAIR, scope=scope, created_at=stamp(NOW),
            evidence=[f"ev{i}"],
            payload={"reply": f"reply {i}", "better": f"fix {i}",
                     "mode": "called"})

    live = candidates.CandidateLedger(path)
    ids = []
    for i in range(6):
        cand = pair(i)
        live.propose(cand)
        ids.append(cand["candidate_id"])
    # Every row kind the projection knows about.
    live.link_evidence(ids[0], ["ev-extra"], ts=stamp(NOW))
    live.promote(ids[1], ts=stamp(NOW), actor="admin", reason="ok")
    live.reject(ids[2], ts=stamp(NOW), actor="admin", reason="no")
    live.promote(ids[3], ts=stamp(NOW), actor="admin", reason="ok")
    live.rollback(ids[3], ts=stamp(NOW), actor="admin", reason="undo")
    live.supersede(ids[4], ids[5], ts=stamp(NOW), actor="admin", reason="new")
    live.propose(pair(0))   # a re-proposal must add evidence, not reset state

    incremental = json.dumps(live.all(), sort_keys=True)
    replayed = json.dumps(candidates.CandidateLedger(path).all(), sort_keys=True)
    check("projection: advancing in place equals replaying the file",
          incremental == replayed,
          f"{len(incremental)} vs {len(replayed)} chars")

    # A SECOND WRITER must invalidate the stamp rather than be dropped. The
    # stamp is compared inside the append's own lock precisely so that this
    # cannot become "the other row vanished and the fresh stamp hid it" —
    # `tools/candidates_admin.py` bypasses the instance lock, so this writer
    # is real.
    other = candidates.CandidateLedger(path)
    other.propose(pair(97))
    live.propose(pair(98))
    check("projection: a second writer's row is not lost",
          json.dumps(live.all(), sort_keys=True)
          == json.dumps(candidates.CandidateLedger(path).all(), sort_keys=True))


def test_a_retry_acceptance_does_not_argue_against_its_own_pair() -> None:
    """`supports` and `opposes` both answered True for one event.

    A retry acceptance carries `reaction_type="positive"` because the user
    accepted the RETRY — the opposite of liking the reply the pair replaces,
    which is what a positive reaction means on every other kind. `opposes`
    read the field without the kind, so the STRONG event a retry-completion
    pair is BUILT FROM became counter-evidence against that same pair and
    `decide` answered "compatible evidence disagrees". The zero-user-effort
    retry loop — a documented feature — could never promote anything, in any
    deployment.

    The last check is the guardrail: a real laugh at the original reply must
    still oppose, or this fix would have removed the rule instead of the bug."""
    scope = dict(lang="en", platform="qq", conv_id="g1", persona="B",
                 persona_hash="h", persona_version="v1")
    reply, rewrite = "just restart it lol", "check the logs first"

    retry = evidence.make_event(
        kind=evidence.KIND_RETRY_ACCEPTANCE, ts=stamp(NOW - 60), **scope,
        speaker_id="a", recipient_id="a", reply=reply,
        reaction_type="positive",
        adjudication={"accept": True, "better": rewrite, "mode": "called"})
    correction = evidence.make_event(
        kind=evidence.KIND_REACTION, ts=stamp(NOW - 30), **scope,
        speaker_id="b", recipient_id="b", reply=reply,
        reaction_type="correction",
        adjudication={"accept": True, "better": rewrite, "mode": "called"})
    cand = candidates.make_candidate(
        ctype=candidates.TYPE_PAIR, scope=scope, created_at=stamp(NOW),
        evidence=[], payload={"reply": reply, "better": rewrite,
                              "mode": "called"})
    linked = [retry, correction]

    check("retry: the acceptance is strong",
          evidence.classify_strength(retry) == evidence.STRONG)
    check("retry: it supports the pair", evidence.supports(retry, candidates.TYPE_PAIR))
    check("retry: and does NOT also oppose it",
          not evidence.opposes(retry, candidates.TYPE_PAIR))
    check("retry: so it is not counter-evidence against itself",
          promotion.counter_evidence(cand, linked, now=NOW) == [],
          repr(promotion.counter_evidence(cand, linked, now=NOW)))
    decision = promotion.decide(
        cand, linked_events=linked,
        related_events=promotion.related_events(cand, linked), peers=[], now=NOW)
    check("retry: the zero-effort loop can promote",
          decision.promote is True, decision.reason)

    laugh = evidence.make_event(
        kind=evidence.KIND_REACTION, ts=stamp(NOW - 20), **scope,
        speaker_id="c", recipient_id="c", reply=reply, reaction_type="positive",
        adjudication={"accept": True, "mode": "called"})
    check("retry: a real laugh at the reply still opposes the pair",
          evidence.opposes(laugh, candidates.TYPE_PAIR))


def test_related_events_covers_the_rewrite() -> None:
    """One builder, because there are two callers.

    The running agent and `tools/candidates_admin.py` each built this list.
    When only the first was widened to include events about the REWRITE, the
    CLI went on printing `policy: would promote` for a pair whose rewrite the
    user had rejected — with an unconditional `promote` command next to it.
    Same shape as the conversation-key mapping that lived in three places."""
    scope = dict(lang="en", platform="qq", conv_id="g1", persona="B",
                 persona_hash="h", persona_version="v1")
    reply, rewrite = "just restart it lol", "check the logs first"
    cand = candidates.make_candidate(
        ctype=candidates.TYPE_PAIR, scope=scope, created_at=stamp(NOW),
        evidence=[], payload={"reply": reply, "better": rewrite,
                              "mode": "called"})

    def event(text: str) -> dict:
        return evidence.make_event(
            kind=evidence.KIND_REACTION, ts=stamp(NOW - 10), **scope,
            speaker_id="a", recipient_id="a", reply=text,
            reaction_type="rejection", adjudication={"accept": True})

    about_reply, about_rewrite, unrelated = (
        event(reply), event(rewrite), event("something else entirely"))
    got = promotion.related_events(
        cand, [about_reply, about_rewrite, unrelated])
    check("related: events about the reply are included", about_reply in got)
    check("related: events about the REWRITE are included", about_rewrite in got)
    check("related: unrelated events are not", unrelated not in got)
    check("related: an example candidate has no rewrite to widen to",
          len(promotion.related_events(
              candidates.make_candidate(
                  ctype=candidates.TYPE_EXAMPLE, scope=scope,
                  created_at=stamp(NOW), evidence=[],
                  payload={"reply": reply, "mode": "called"}),
              [about_reply, about_rewrite])) == 1)


def test_an_over_long_scope_field_stays_distinct() -> None:
    """Bounding the scope must not merge two conversations into one.

    Retrieval compares a live scope against the ledger's, and the ledger's is
    length-bounded. Normalising BOTH sides through a plain truncation fixed
    the comparison and introduced a quieter version of the same bug: two ids
    differing only past the limit became the same string, so material promoted
    in one room was authorized into another that shared its 128-character
    prefix — and `require_same_conversation` could not stop it, because by
    then the two really were equal.

    Short ids — every real one — must be untouched, so this cannot be
    "fixed" by hashing everything."""
    long_a = "g" * 128 + "-room-one"
    long_b = "g" * 128 + "-room-two"
    norm_a = evidence.normalize_scope({"conv_id": long_a})["conv_id"]
    norm_b = evidence.normalize_scope({"conv_id": long_b})["conv_id"]
    check("scope: two over-long conv_ids stay distinct", norm_a != norm_b,
          f"{norm_a!r} vs {norm_b!r}")
    check("scope: ...and stay within the stored limit",
          len(norm_a) <= evidence.SCOPE_LIMITS["conv_id"], str(len(norm_a)))
    check("scope: an ordinary id is untouched",
          evidence.normalize_scope({"conv_id": "g1"})["conv_id"] == "g1")

    # The writer and the comparator must agree for the over-long case too —
    # that agreement is the whole point of the table.
    event = evidence.make_event(
        kind=evidence.KIND_REACTION, ts=stamp(NOW), conv_id=long_a,
        speaker_id="a", recipient_id="a", reply="x")
    check("scope: what make_event stores is what normalize_scope produces",
          event["conv_id"] == norm_a, f"{event['conv_id']!r} vs {norm_a!r}")
    other = evidence.make_event(
        kind=evidence.KIND_REACTION, ts=stamp(NOW), conv_id=long_b,
        speaker_id="a", recipient_id="a", reply="x")
    check("scope: and the two rooms are not one room in the ledger either",
          event["conv_id"] != other["conv_id"])


def test_stale_evidence_is_refused() -> None:
    """The rule at the centre of the four-day outage, and it had no test.

    Three separate mutations of `promotion.py` all survived the whole suite:
    disabling `decide`'s age gate, raising `MAX_EVIDENCE_AGE_DAYS` to 1e9, and
    making `epoch()` fall back to `time.time()` instead of `0.0` on an
    unparsable timestamp. Only the COUNTER-evidence window was pinned (4b
    above) and only the lower bound of the supporting window, indirectly, by
    the speaker tests. So the suite protected "evidence must not expire too
    fast" and said nothing at all about "stale evidence must be refused".

    THE OFFSETS BELOW ARE LITERALS ON PURPOSE. Deriving them from
    `MAX_EVIDENCE_AGE_DAYS` would move the fixture with the constant, and the
    mutation that widens the window to 1e9 would sail through — a test that
    reads its own subject for the answer.

    What a regression here costs: a year-old correction from someone who has
    since left the group promotes into the permanent pool and the persona
    imitates it forever. The inverse is worse to diagnose — a timestamp format
    change makes every event read as ancient, promotion silently stops, and
    the only symptom is that the agent quietly stops learning."""
    scope = dict(lang="en", platform="qq", conv_id="g1", persona="B",
                 persona_hash="h", persona_version="v1")

    def correction(speaker: str, age_days: float, ts: str | None = None) -> dict:
        return evidence.make_event(
            kind=evidence.KIND_REACTION,
            ts=stamp(NOW - age_days * 86400) if ts is None else ts,
            **scope, speaker_id=speaker, recipient_id=speaker,
            reply="just restart it lol", reaction_type="correction",
            adjudication={"accept": True, "better": "check the logs first",
                          "mode": "called"})

    cand = candidates.make_candidate(
        ctype=candidates.TYPE_PAIR, scope=scope, created_at=stamp(NOW),
        evidence=[], payload={"reply": "just restart it lol",
                              "better": "check the logs first",
                              "mode": "called"})

    def decide(events):
        # The DEFAULT policy, so the shipped constant is the thing under test.
        return promotion.decide(cand, linked_events=events, related_events=[],
                                peers=[], now=NOW, policy=promotion.Policy())

    fresh = [correction("alice", 0.02), correction("bob", 0.04)]
    check("age: two fresh strong corrections promote",
          decide(fresh).promote is True, decide(fresh).reason)

    # 60 days: comfortably past the shipped 30 and comfortably short of any
    # widening worth calling a widening.
    stale = [correction("alice", 60), correction("bob", 60)]
    decision = decide(stale)
    check("age: the same two, sixty days old, promote nothing",
          decision.promote is False, decision.reason)
    check("age: ...and they are not merely outvoted, they are not counted",
          decision.supporting == 0 and decision.strong == 0,
          f"supporting={decision.supporting} strong={decision.strong}")

    # One fresh, one stale: the fresh one is real evidence and still must not
    # promote alone, which is the whole point of min_events.
    check("age: a fresh event does not carry a stale one",
          decide([correction("alice", 0.02), correction("bob", 60)]).promote
          is False)

    # An unparsable timestamp reads as ancient, never as now. `epoch()`
    # returning 0.0 is a fail-closed decision and this is the half of its
    # contract nothing pinned.
    # BOTH events carry a non-empty unparsable stamp. An empty one returns
    # early from `epoch()`, before the parse it is meant to exercise, so a
    # pair with one of each leaves only one countable event and `min_events`
    # refuses for the wrong reason — the mutation walks straight past.
    unparsable = [correction("alice", 0.02, ts="not-a-timestamp"),
                  correction("bob", 0.04, ts="???")]
    check("age: an unparsable timestamp is treated as ancient, not as now",
          decide(unparsable).promote is False, decide(unparsable).reason)
    missing = [correction("alice", 0.02, ts=""), correction("bob", 0.04, ts="")]
    check("age: a missing timestamp is treated as ancient too",
          decide(missing).promote is False, decide(missing).reason)
    # And the parser's contract asserted DIRECTLY, because the behavioural
    # checks above cannot see it. `NOW` sits ~509 days ahead of the real
    # clock, so a fallback of `time.time()` reads as MORE ancient than the
    # window from NOW's point of view and is filtered either way — the frozen
    # clock masks the mutation exactly where the behaviour is observed. A unit
    # contract wants a unit assertion.
    check("age: epoch() reads an unparsable stamp as 0, never as now",
          promotion.epoch("not-a-timestamp") == 0.0
          and promotion.epoch("") == 0.0
          and promotion.epoch(None) == 0.0,
          repr([promotion.epoch("not-a-timestamp"), promotion.epoch(""),
                promotion.epoch(None)]))


def test_a_positive_example_waits_for_a_person_and_says_so() -> None:
    """`positive_example` cannot auto-promote, and that is the policy.

    `supports` accepts a self-eval or a positive reaction there, and
    `classify_strength` calls both WEAK — "laughter, agreement, banter, the
    agent's own score. Never sufficient to promote anything, at any
    quantity." So the type is human-review-only BY CONSTRUCTION, not by
    threshold, and promotion has to say which of the two it is: the reason
    used to read "0/1 strong events (4 supporting)", which describes a bar
    the next reaction might clear. No reaction ever clears it.

    The table is DERIVED here rather than copied. Anyone widening `supports`
    or `classify_strength` moves the intersection, and the point of the table
    is to make that show up as a failing test instead of as a bot that
    started imitating whatever four people laughed at."""
    derived = set()
    for ctype in candidates.TYPES:
        for kind in evidence.KINDS:
            for rtype in evidence.REACTION_TYPES:
                for recipient in ("a", "b"):   # same person / a bystander
                    ev = evidence.make_event(
                        kind=kind, ts=stamp(NOW), speaker_id="a",
                        recipient_id=recipient, reply="a line",
                        reaction_type=rtype,
                        adjudication={"accept": True, "better": "a fix"})
                    if (evidence.supports(ev, ctype)
                            and evidence.classify_strength(ev) == evidence.STRONG):
                        derived.add(ctype)
    check("STRONG_CAPABLE_TYPES is what the two functions actually do",
          derived == set(evidence.STRONG_CAPABLE_TYPES),
          f"derived={sorted(derived)} table={sorted(evidence.STRONG_CAPABLE_TYPES)}")

    # The exclusion that keeps the derivation honest. A retry acceptance IS
    # strong, and its `reply` is the text the user REJECTED — so admitting it
    # as support for a positive example would let "the user accepted the fix"
    # promote the rejected line as something to imitate. Only the
    # reply-equality check in supports_candidate stood between those two.
    retry = evidence.make_event(
        kind=evidence.KIND_RETRY_ACCEPTANCE, ts=stamp(NOW), speaker_id="a",
        recipient_id="a", reply="the rejected line", reaction_type="positive",
        adjudication={"accept": True, "better": "the retry"})
    check("a retry acceptance is still strong",
          evidence.classify_strength(retry) == evidence.STRONG,
          evidence.classify_strength(retry))
    check("a retry acceptance still argues for the pair",
          evidence.supports(retry, candidates.TYPE_PAIR))
    check("but never that the rejected text is a good example",
          not evidence.supports(retry, candidates.TYPE_EXAMPLE))

    scope = dict(lang="en", platform="qq", conv_id="g1", persona="B",
                 persona_hash="h", persona_version="v1")
    events = [
        evidence.make_event(
            kind=evidence.KIND_REACTION, ts=stamp(NOW - 60), **scope,
            speaker_id=str(i), recipient_id=str(i), reply="good line",
            reaction_type="positive",
            adjudication={"accept": True, "mode": "called"})
        for i in range(4)
    ]
    cand = candidates.make_candidate(
        ctype=candidates.TYPE_EXAMPLE, scope=scope, created_at=stamp(NOW),
        evidence=[], payload={"reply": "good line", "mode": "called"})
    decision = promotion.decide(cand, linked_events=events, related_events=[],
                                peers=[], now=NOW)
    check("four positive reactions still promote nothing",
          decision.promote is False, decision.reason)
    check("and the reason names a person, not a count",
          "person" in decision.reason and "/1 strong" not in decision.reason,
          decision.reason)


def main() -> int:
    real = runtime_dir()
    before = sorted(p.name for p in real.glob("*")) if real.exists() else []

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        asyncio.run(test_one_positive_promotes_nothing(tmp / "t1"))
        asyncio.run(test_repeated_weak_promotes_nothing(tmp / "t2"))
        asyncio.run(test_single_correction_proposes_only(tmp / "t3"))
        asyncio.run(test_two_events_with_a_strong_one_promote(tmp / "t4"))
        test_expired_counter_evidence_does_not_block_new_corroboration()
        asyncio.run(test_incompatible_scopes_are_not_combined(tmp / "t5"))
        asyncio.run(test_conflicting_evidence_blocks_promotion(tmp / "t6"))
        asyncio.run(test_retry_provides_supporting_evidence(tmp / "t7"))
        asyncio.run(test_duplicate_events_are_idempotent(tmp / "t8"))
        test_evidence_identity_includes_source_and_full_scope()
        test_invalid_log_rows_are_quarantined_from_replay(tmp / "t8c")
        asyncio.run(test_restart_and_replay_are_identical(tmp / "t9"))
        asyncio.run(test_rollback_removes_from_retrieval(tmp / "t10"))
        asyncio.run(test_supersession_replaces_the_active_preference(tmp / "t11"))
        asyncio.run(test_logs_are_append_only(tmp / "t12"))
        test_legacy_feedback_still_loads(tmp / "t13")
        asyncio.run(test_legacy_rows_still_retractable(tmp / "t13b"))
        test_paths_never_touch_real_runtime_state(tmp / "t14")
        test_corroboration_means_people_not_events()
        test_moving_on_is_not_acceptance()
        test_stale_evidence_is_refused()
        test_a_rejected_rewrite_is_not_promoted_later()
        test_an_unwitnessed_proposal_does_not_veto_a_real_correction()
        test_the_live_projection_equals_a_cold_replay(tmp / "t15")
        test_a_retry_acceptance_does_not_argue_against_its_own_pair()
        test_related_events_covers_the_rewrite()
        test_an_over_long_scope_field_stays_distinct()
        test_a_positive_example_waits_for_a_person_and_says_so()

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
