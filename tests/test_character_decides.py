"""The character decides what no further reaction can settle.

Driven through the real reaction path (PendingReplies, _process_reaction,
the ledger and the views) with a scripted model: reaction verdicts for the
reaction judge, and the character's own verdicts for the adoption judge.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from persona_agent import adoption, candidates, evidence, learning, reactions
from persona_agent.agent import Agent
from persona_agent.settings import AgentSettings

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent

CONV = "g1"
CTX = ["alex: Nova the deploy failed again, third time today"]
REPLY = "did you check the logs? roll back first, then diff the configs"
RETRY = "ugh, third time? that's brutal"
SECOND = "oof, rough"

CORRECTION = {"reaction": "correction", "accept": True, "reason": "wanted sympathy",
              "better": "oof, that sucks", "ask": "", "scenario": "venting"}
REJECTION = {"reaction": "rejection", "accept": True, "reason": "misread a vent",
             "better": "", "ask": "", "scenario": "venting"}
THANKS = {"reaction": "positive", "accept": True, "reason": "took the retry",
          "better": "", "ask": "", "scenario": "accepted"}

ADOPTION_HEADS = ("deciding for yourself whether to keep", "现在要你自己决定")


class Model:
    """Reaction verdicts for the reaction judge; scripted lines for the
    character's judgement, and an unusable answer once they run out."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.prompts: list[str] = []
        self.verdicts: list[str] = []
        self.adjudication: dict = THANKS

    async def __call__(self, system, messages, model, **kw):
        prompt = messages[-1]["content"]
        if any(head in prompt for head in ADOPTION_HEADS):
            self.calls.append("adopt")
            self.prompts.append(prompt)
            return self.verdicts.pop(0) if self.verdicts else "not json"
        self.calls.append("judge")
        return json.dumps(self.adjudication)

    def say(self, decision: str, reason: str, choice: str = "") -> None:
        self.verdicts.append(json.dumps(
            {"decision": decision, "choice": choice, "reason": reason}))


def make_agent(tmp: Path, *, judging: bool = False) -> tuple[Agent, Model]:
    a = isolated_agent(tmp, seeds=True, qq_bot_id="1", persona_name="Nova",
                       lang="en", qq_onebot_url=CLOSED_ONEBOT_URL,
                       persona="test persona", react_elicit_enabled=False)
    a.pending_reactions = reactions.PendingReplies()
    a.promote_judge_enabled = judging
    model = Model()
    a._call_llm = model
    return a, model


def send(a: Agent, reply: str, to: str, *, mode: str = "called") -> None:
    a.pending_reactions.record(CONV, reply=reply, ctx_lines=CTX, mode=mode,
                               target_uid=to, ts=time.time())


async def react(a: Agent, model: Model, uid: str, adj: dict, *,
                name: str = "alex", is_admin: bool = False,
                text: str = "reaction") -> None:
    entry = a.pending_reactions.match(CONV, sender_uid=uid, at_bot=True,
                                      now=time.time())
    assert entry is not None, f"nothing pending for {uid}"
    model.adjudication = adj
    await a._process_reaction(entry, text, name, uid, is_admin, conv_id=CONV)


async def settle(a: Agent) -> None:
    while a._bg_tasks:
        await asyncio.gather(*list(a._bg_tasks), return_exceptions=True)


def cand(a: Agent, better: str) -> dict:
    found = [c for c in a.candidate_ledger.all() if c.get("better") == better]
    assert len(found) == 1, [c.get("better") for c in a.candidate_ledger.all()]
    return found[0]


def pairs(a: Agent) -> list[tuple[str, str]]:
    path = a.promoted_feedback_file
    if not path.exists():
        return []
    return [(r["reply"], r["better"]) for r in
            (json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
             if ln.strip())]


async def taught(a: Agent, model: Model) -> None:
    """alex corrects REPLY and accepts the retry: RETRY is in use."""
    send(a, REPLY, "42")
    await react(a, model, "42", CORRECTION)
    send(a, RETRY, "42")
    await react(a, model, "42", THANKS)
    assert pairs(a) == [(REPLY, RETRY)], pairs(a)


async def rival(a: Agent, model: Model, better: str = SECOND) -> str:
    """The same reply corrected again and that retry accepted: a second,
    fully corroborated rewrite that only the character can settle."""
    await taught(a, model)
    send(a, REPLY, "42", mode="followup")
    await react(a, model, "42", dict(CORRECTION, better=better))
    send(a, better, "42")
    await react(a, model, "42", THANKS)
    return cand(a, better)["candidate_id"]


# ---------------------------------------------------------------------------
# Choosing among rewrites, discarding, observing
# ---------------------------------------------------------------------------

async def test_a_conflicting_rewrite_is_chosen_and_the_rival_retired(tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await rival(a, model)
    old = cand(a, RETRY)["candidate_id"]
    check("setup: the rival is held for the character",
          a._decide_promotion(cid).gate == "conflict")
    a.promote_judge_enabled = True
    model.say("adopt", "The newer wording is warmer and was accepted.", "A")
    outcome = await a._character_decide(cid)
    new, gone = a.candidate_ledger.get(cid), a.candidate_ledger.get(old)
    check("adopted", outcome == "adopted" and new["state"] == "promoted", outcome)
    check("the rival is replaced, not left beside it",
          gone["state"] == "superseded" and pairs(a) == [(REPLY, SECOND)], str(pairs(a)))
    last = new["history"][-1]
    check("the character is the actor, with its reason and the judge",
          last["actor"] == candidates.ACTOR_CHARACTER
          and last["reason"] == "The newer wording is warmer and was accepted."
          and last["judge"] == adoption.ADOPTION_VERSION, str(last))
    check("one judgement, both options offered",
          model.calls.count("adopt") == 1 and "A. " in model.prompts[0]
          and "B. " in model.prompts[0] and "(already in use)" in model.prompts[0])


async def test_keeping_the_rewrite_in_use_discards_the_newcomer(tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await rival(a, model)
    a.promote_judge_enabled = True
    model.say("adopt", "The wording in use already fits.", "B")
    check("kept", await a._character_decide(cid) == "adopted")
    check("the newcomer is discarded by the character",
          a.candidate_ledger.get(cid)["state"] == "rejected"
          and a.candidate_ledger.get(cid)["history"][-1]["actor"] == "character"
          and pairs(a) == [(REPLY, RETRY)], str(pairs(a)))


async def disagreed(a: Agent, model: Model) -> str:
    """bob liked REPLY, then alex corrected it and accepted the retry: the
    rewrite meets every threshold, but accepted evidence disagrees."""
    send(a, REPLY, "42")
    await react(a, model, "7", THANKS, name="bob")
    send(a, REPLY, "42")
    await react(a, model, "42", CORRECTION)
    send(a, RETRY, "42")
    await react(a, model, "42", THANKS)
    return cand(a, RETRY)["candidate_id"]


async def test_disagreeing_evidence_can_be_discarded_with_the_reason_kept(
        tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await disagreed(a, model)
    check("setup: held by disagreement", a._decide_promotion(cid).gate == "against"
          and pairs(a) == [])
    a.promote_judge_enabled = True
    model.say("discard", "Another member liked the original reply.")
    check("discarded", await a._character_decide(cid) == "discarded")
    row = a.candidate_ledger.get(cid)
    check("by the character, with its reason",
          row["state"] == "rejected" and row["history"][-1]["actor"] == "character"
          and row["history"][-1]["reason"] == "Another member liked the original reply.",
          str(row["history"]))
    check("the prompt shows the evidence against",
          "opposes" in model.prompts[0] and "supports" in model.prompts[0],
          model.prompts[0])
    check("bob's view stays nothing", pairs(a) == [])


async def test_observe_is_recorded_and_not_asked_again_until_evidence_changes(
        tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await disagreed(a, model)
    a.promote_judge_enabled = True
    model.say("observe", "The reactions point both ways so far.")
    check("observed", await a._character_decide(cid) == "observed")
    row = a.candidate_ledger.get(cid)
    check("a review row with its reason, state unchanged",
          row["state"] == "proposed"
          and row["review"]["reason"] == "The reactions point both ways so far."
          and row["review"]["actor"] == "character" and row["review"]["seen"],
          str(row.get("review")))
    check("replayed from the file too",
          candidates.CandidateLedger(a.candidate_ledger_file).get(cid)["review"]
          == row["review"])
    before = model.calls.count("adopt")
    check("the same evidence is not judged twice",
          await a._character_decide(cid) == "seen"
          and (await a._adoption_tick()) == {}
          and model.calls.count("adopt") == before, str(model.calls))

    # A new reaction about the same reply.
    a.promote_judge_enabled = False
    send(a, REPLY, "42")
    await react(a, model, "8", THANKS, name="carl")
    a.promote_judge_enabled = True
    # Two people now liked REPLY itself: that liked reply is judged as well.
    model.say("discard", "A second member liked the original reply.")
    model.say("discard", "A second member liked the original reply.")
    out = await a._adoption_tick()
    check("new evidence: judged again by the sweep",
          a.candidate_ledger.get(cid)["state"] == "rejected"
          and out.get("discarded") == 2 and model.calls.count("adopt") == before + 2,
          str(out))


async def test_an_unusable_answer_writes_nothing_and_backs_off(tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await rival(a, model)
    a.promote_judge_enabled = True
    ledger_before = a.candidate_ledger_file.read_bytes()
    now = time.time()
    check("failed", await a._character_decide(cid) == "failed")
    check("asked twice, then nothing written",
          model.calls.count("adopt") == 2
          and a.candidate_ledger_file.read_bytes() == ledger_before)
    attempts, next_at = a._adoption_retry[cid]
    interval = a.promote_judge_interval_s
    check("backs off one interval", attempts == 1
          and interval - 5 <= next_at - now <= interval + 5, str((attempts, next_at - now)))
    check("not asked again while backing off",
          await a._character_decide(cid) == "backoff"
          and await a._adoption_tick() == {} and model.calls.count("adopt") == 2)
    a._adoption_retry[cid] = (1, 0.0)
    a._adoption_calls.clear()
    now = time.time()
    check("failed again", await a._character_decide(cid) == "failed")
    attempts, next_at = a._adoption_retry[cid]
    check("the delay doubles", attempts == 2
          and 2 * interval - 5 <= next_at - now <= 2 * interval + 5,
          str((attempts, next_at - now)))
    a._adoption_retry[cid] = (30, 0.0)
    a._back_off(cid, 0.0)
    check("capped at a day", a._adoption_retry[cid][1] == learning.MAX_BACKOFF_S)


async def test_the_budget_caps_judgements_per_interval(tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await rival(a, model)
    a.promote_judge_enabled = True
    a.promote_judge_batch = 1
    a._judgement_budget(time.time())
    check("deferred, no call", await a._character_decide(cid) == "deferred"
          and "adopt" not in model.calls)


async def test_the_code_rules_discard_without_a_model_call(tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await rival(a, model, better="**oof**, rough")
    a.promote_judge_enabled = True
    check("ruled", await a._character_decide(cid) == "ruled")
    row = a.candidate_ledger.get(cid)
    check("discarded by rule, not by the character, with no call",
          row["state"] == "rejected" and row["history"][-1]["actor"] == "auto"
          and row["history"][-1]["reason"] == learning.REASON_POLICY
          and row["history"][-1]["judge"] == learning.RULES_VERSION
          and "adopt" not in model.calls, str(row["history"][-1]))
    check("a rule discard is not one a person brings back",
          not candidates.restorable(row))

    b, model = make_agent(tmp / "blocked")
    cid = await rival(b, model)
    b.promote_judge_enabled = True
    b.teacher_stats.hard_block = lambda uid: uid == "42"
    check("a blocked teacher's support is discarded by rule",
          await b._character_decide(cid) == "ruled"
          and b.candidate_ledger.get(cid)["history"][-1]["reason"]
          == learning.REASON_BLOCKED and "adopt" not in model.calls)


async def refused(a: Agent, model: Model) -> str:
    """alex corrects REPLY, rejects that line when the bot says it, then
    corrects REPLY to it once more: corroborated, but refused by its recipient."""
    send(a, REPLY, "42")
    await react(a, model, "42", CORRECTION, text="i was venting")
    send(a, CORRECTION["better"], "42")
    await react(a, model, "42", REJECTION)
    send(a, REPLY, "42")
    await react(a, model, "42", CORRECTION, text="again, i was venting")
    return cand(a, CORRECTION["better"])["candidate_id"]


async def test_a_rewrite_its_recipient_refused_is_never_adopted(tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await refused(a, model)
    decision = a._decide_promotion(cid)
    check("setup: held by a refusal, every other threshold met",
          decision.gate == "against" and decision.refused
          and decision.otherwise_ready, str(decision))
    a.promote_judge_enabled = True
    model.say("adopt", "It is better.")
    model.say("adopt", "It is still better.")
    check("adopt is unusable here", await a._character_decide(cid) == "failed")
    check("nothing promoted, nothing written",
          a.candidate_ledger.get(cid)["state"] == "proposed" and pairs(a) == []
          and not a.candidate_ledger.get(cid).get("review"))
    check("the prompt says adopting is not available",
          "Adopting is not available here" in model.prompts[0], model.prompts[0][-400:])
    a._adoption_retry.clear()
    model.say("discard", "The person it was for refused this wording.")
    check("it may still be discarded", await a._character_decide(cid) == "discarded")


# ---------------------------------------------------------------------------
# What does not reach the judgement
# ---------------------------------------------------------------------------

async def test_a_single_correction_makes_no_judgement_call(tmp: Path) -> None:
    a, model = make_agent(tmp, judging=True)
    send(a, REPLY, "42")
    await react(a, model, "42", CORRECTION)
    await settle(a)
    check("only the reaction judge was asked", model.calls == ["judge"], str(model.calls))
    check("and the sweep finds nothing to decide",
          await a._adoption_tick() == {} and model.calls == ["judge"])


async def test_the_master_switch_off_makes_no_call(tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await rival(a, model)
    a.promote_judge_enabled = True
    a.promotion_policy = type(a.promotion_policy)(auto_promote=False)
    calls = list(model.calls)
    check("off", await a._character_decide(cid) == "off"
          and await a._character_review_promoted(cid) == "off"
          and await a._adoption_tick() == {})
    send(a, REPLY, "42")
    await react(a, model, "9", REJECTION, name="dan")
    await settle(a)
    check("a new reaction queues nothing either",
          model.calls == calls + ["judge"], str(model.calls))
    check("and nothing changed", a.candidate_ledger.get(cid)["state"] == "proposed")


async def test_the_judge_switch_off_leaves_the_hold(tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await rival(a, model)
    await settle(a)
    check("off by setting", await a._character_decide(cid) == "off"
          and "adopt" not in model.calls)


async def test_the_reaction_itself_triggers_the_judgement(tmp: Path) -> None:
    a, model = make_agent(tmp, judging=True)
    model.say("adopt", "The newer wording was accepted.", "A")
    await rival(a, model)
    await settle(a)
    check("one judgement, off the reply path",
          model.calls.count("adopt") == 1 and pairs(a) == [(REPLY, SECOND)],
          str(model.calls))


# ---------------------------------------------------------------------------
# A person can still undo, and bring back what the character discarded
# ---------------------------------------------------------------------------

async def test_a_persons_undo_of_an_adoption_stays_undone(tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await rival(a, model)
    a.promote_judge_enabled = True
    model.say("adopt", "The newer wording was accepted.", "A")
    await a._character_decide(cid)
    a.candidate_ledger.rollback(cid, ts="t", actor="admin", reason="not this one")
    a._rebuild_promoted_views()
    model.say("adopt", "Again.", "A")
    calls = len(model.calls)
    out = await a._adoption_tick()
    check("the sweep leaves the undo alone",
          a.candidate_ledger.get(cid)["state"] == "rolled_back"
          and len(model.calls) == calls and pairs(a) == [], str(out))


async def test_bring_back_a_character_discard_but_not_a_persons(tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await disagreed(a, model)
    a.promote_judge_enabled = True
    model.say("discard", "Another member liked the original reply.")
    await a._character_decide(cid)
    ledger = a.candidate_ledger
    check("no automatic actor brings it back",
          not ledger.restore(cid, ts="t", actor="character")
          and not ledger.restore(cid, ts="t", actor="auto"))
    check("a person does", ledger.restore(cid, ts="t", actor="dashboard",
                                          reason="local page")
          and ledger.get(cid)["state"] == "promoted")
    ledger.rollback(cid, ts="t", actor="dashboard")
    ledger.reject(cid, ts="t", actor="dashboard")
    check("a person's own discard stays final",
          not ledger.restore(cid, ts="t", actor="admin")
          and ledger.get(cid)["state"] == "rejected")


# ---------------------------------------------------------------------------
# A bystander's dispute of an item in use
# ---------------------------------------------------------------------------

async def disputed(a: Agent, model: Model) -> str:
    """RETRY is in use, taught by alex; bob, a bystander, calls it wrong when
    the bot says it to carol."""
    await taught(a, model)
    send(a, RETRY, "55")
    await react(a, model, "7", REJECTION, name="bob")
    return cand(a, RETRY)["candidate_id"]


async def test_a_dispute_the_character_upholds_stops_the_item(tmp: Path) -> None:
    a, model = make_agent(tmp, judging=True)
    model.say("discard", "The objection is fair; the line is too flippant.")
    cid = await disputed(a, model)
    await settle(a)
    row = a.candidate_ledger.get(cid)
    check("withdrawn by the character",
          row["state"] == "rolled_back" and row["history"][-1]["actor"] == "character"
          and pairs(a) == [], str(row["history"][-1]))
    check("one call, with the dispute hold",
          model.calls.count("adopt") == 1
          and "someone the reply was not for disagreed" in model.prompts[0])


async def test_a_dispute_the_character_rejects_keeps_the_item(tmp: Path) -> None:
    a, model = make_agent(tmp, judging=True)
    model.say("adopt", "The person it was for asked for this.")
    cid = await disputed(a, model)
    await settle(a)
    row = a.candidate_ledger.get(cid)
    check("kept, and recorded", row["state"] == "promoted"
          and row["review"]["reason"] == "The person it was for asked for this."
          and pairs(a) == [(REPLY, RETRY)], str(row.get("review")))
    check("not asked again on the same evidence",
          await a._character_review_promoted(cid) == "seen"
          and model.calls.count("adopt") == 1)


async def test_what_its_teacher_confirmed_since_is_kept_without_a_call(
        tmp: Path) -> None:
    a, model = make_agent(tmp)
    cid = await disputed(a, model)
    confirm = evidence.make_event(
        kind=evidence.KIND_REACTION, ts="2099-01-01T00:00:00",
        **a._scope_fields(CONV), speaker_id="42", speaker_name="alex",
        recipient_id="42", reply=RETRY, reaction_type="positive",
        reaction_text="yes, exactly", directed=True, direction="at",
        adjudication=dict(THANKS, mode="called"))
    a.evidence_log.append(confirm)
    a.promote_judge_enabled = True
    check("kept by rule", await a._character_review_promoted(cid) == "kept")
    row = a.candidate_ledger.get(cid)
    check("no call, the rule's reason on record",
          "adopt" not in model.calls and row["state"] == "promoted"
          and row["review"]["reason"] == learning.REASON_CONFIRMED
          and row["review"]["actor"] == "auto", str(row.get("review")))


# ---------------------------------------------------------------------------
# Nothing waits for ever; settings
# ---------------------------------------------------------------------------

async def test_an_item_with_no_new_reaction_is_set_aside_by_rule(tmp: Path) -> None:
    a, model = make_agent(tmp, judging=True)
    send(a, REPLY, "42")
    await react(a, model, "42", CORRECTION)
    cid = cand(a, CORRECTION["better"])["candidate_id"]
    check("not before its time", a._expire_observing(time.time()) == 0)
    a.promote_observe_max_days = 0
    check("0 never sets aside", a._expire_observing(time.time() + 400 * 86400) == 0)
    a.promote_observe_max_days = 30
    check("set aside after 30 quiet days",
          a._expire_observing(time.time() + 31 * 86400) == 1)
    row = a.candidate_ledger.get(cid)
    check("by rule, with the reason",
          row["state"] == "rejected" and row["history"][-1]["actor"] == "auto"
          and row["history"][-1]["reason"]
          == "Set aside by rule: no new reactions for 30 days."
          and "adopt" not in model.calls, str(row["history"][-1]))


def test_the_settings_and_their_defaults() -> None:
    s = AgentSettings(api_key="k")
    check("on by default, modest batch and interval",
          s.promote_judge_enabled is True and s.promote_judge_batch == 5
          and s.promote_judge_interval_s == 900.0
          and s.promote_observe_max_days == 30.0)
    check("the model falls back to the reaction judge's",
          AgentSettings(api_key="k", react_model="r").promote_judge_model == "r"
          and AgentSettings(api_key="k").promote_judge_model
          == AgentSettings(api_key="k").react_model)
    env = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "PROMOTE_JUDGE_ENABLED": "false",
        "PROMOTE_JUDGE_INTERVAL_S": "5", "PROMOTE_JUDGE_BATCH": "0",
        "PROMOTE_JUDGE_MODEL": "cheap", "PROMOTE_OBSERVE_MAX_DAYS": "0"})
    check("read from the environment, with floors",
          env.promote_judge_enabled is False and env.promote_judge_interval_s == 900.0
          and env.promote_judge_batch == 5 and env.promote_judge_model == "cheap"
          and env.promote_observe_max_days == 0.0,
          repr((env.promote_judge_interval_s, env.promote_judge_batch)))
