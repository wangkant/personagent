"""The promotion policy: when may evidence grant a candidate authority.

Evidence (evidence.py) records what happened. Candidates (candidates.py) record
what was proposed. This module decides the one question neither of them may
answer for itself: **is this proposal allowed to change how the agent talks.**

The rule the whole design exists to enforce: *a single automatic signal must
never permanently change behaviour.* One `haha` may be politeness, or aimed at
someone else in the thread. One "no, that's wrong" may be a troll, or a
misreading. The agent's own top score comes from an evaluator documented as
generous. Yet anything reaching a retrieval pool is imitated indefinitely, so
promotion requires corroboration:

- at least ``MIN_EVENTS`` distinct compatible events, and
- at least ``MIN_STRONG`` of them strong (a directed correction from the person
  the reply was aimed at, or a retry that person then accepted),
- combinable only across compatible persona, language, conversation and
  scenario scope,
- and never when compatible evidence points in two directions at once — that
  is left for a human, because guessing which contradiction wins is how a
  feedback loop entrenches a mistake.

Weak evidence never promotes anything at any quantity, so laughter alone can no
longer grow the example pool; it accrues on a candidate and waits for an anchor.

Also here, the pre-ledger gate that still guards the legacy pools:
``CandidatePool`` (weight-based corroboration, retained so existing imports and
on-disk state keep working) and ``retract_example``, which is how a human
disagreement still pulls a row out of a learned pool written before the ledger
existed.

Pure logic — no clock reads, no LLM. Callers pass `now`.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import candidates, evidence
from .storage import append_lock, atomic_write_text

# ---------------------------------------------------------------------------
# Automatic promotion policy
# ---------------------------------------------------------------------------
# Conservative by construction, and every threshold is named: an operator who
# wants a looser loop should have to say so in .env, in a value they can read
# back later, rather than discover it in a diff.

# Two distinct compatible events, one of which must be strong. Two is not a
# statistical claim — it is the smallest number that cannot be produced by one
# misreading.
MIN_EVENTS = 2
MIN_STRONG = 1
# ...from at least this many distinct people, owner exempt.
#
# MIN_EVENTS counts events, and one determined member can produce two by
# themselves: correct a reply, then accept the agent's retry. Delayed
# elicitation even has the agent *solicit* that second event from the same
# person. So "two distinct compatible events" is not "two people agreed".
#
# The default is 1 — today's behaviour — because the attack path and the
# honest path are structurally identical. "that's not what I asked" followed by
# "I meant check the logs" is one person, two events, and it is exactly how a
# real clarification looks; requiring a second voice would refuse it too, and
# solo clarification is the flagship zero-effort loop. What is closed by
# default instead is the part that was unambiguously wrong: a topic change no
# longer counts as acceptance, and an adjudicator verdict of accept=false is no
# longer overridden (see evidence.classify_strength).
#
# Set PROMOTE_MIN_SPEAKERS=2 for a room where strangers should not be able to
# teach the agent unaided. Nothing is lost when it blocks: the candidate is
# still proposed and waits in `candidates_admin.py list` for a human.
MIN_SPEAKERS = 1
# Evidence older than this stops counting as support. A correction from four
# months and one persona revision ago is history, not a mandate.
MAX_EVIDENCE_AGE_DAYS = 30.0
# Combine evidence only within one conversation. The same wording can be right
# in one room and wrong in the next, and cross-room combination is exactly how
# a single loud teacher would reach the threshold everywhere at once.
REQUIRE_SAME_CONVERSATION = True
# Master switch: false leaves every candidate for human review.
AUTO_PROMOTE = True


@dataclass(frozen=True)
class Policy:
    """Promotion thresholds. Defaults are the conservative ones above."""

    min_events: int = MIN_EVENTS
    min_strong: int = MIN_STRONG
    min_speakers: int = MIN_SPEAKERS
    max_evidence_age_days: float = MAX_EVIDENCE_AGE_DAYS
    require_same_conversation: bool = REQUIRE_SAME_CONVERSATION
    auto_promote: bool = AUTO_PROMOTE

    @classmethod
    def from_env(cls, env=None) -> "Policy":
        env = os.environ if env is None else env

        def _int(name: str, default: int) -> int:
            try:
                return int(str(env.get(name, default)).strip() or default)
            except (TypeError, ValueError):
                return default

        def _float(name: str, default: float) -> float:
            try:
                return float(str(env.get(name, default)).strip() or default)
            except (TypeError, ValueError):
                return default

        def _bool(name: str, default: bool) -> bool:
            """`raw == "true"` read every other spelling as False, so
            `PROMOTE_AUTO=1` disabled promotion entirely and said nothing.
            An unrecognised value keeps the default rather than silently
            picking the opposite of what was meant."""
            raw = str(env.get(name, "")).strip().lower()
            if raw in {"true", "1", "yes", "on"}:
                return True
            if raw in {"false", "0", "no", "off"}:
                return False
            return default

        return cls(
            # Floors, not suggestions: PROMOTE_MIN_EVENTS=1 would reintroduce
            # exactly the failure this module exists to prevent.
            min_events=max(2, _int("PROMOTE_MIN_EVENTS", MIN_EVENTS)),
            min_strong=max(1, _int("PROMOTE_MIN_STRONG", MIN_STRONG)),
            # Floor of 1, not 2: an operator running a private single-user
            # deployment has nobody to corroborate with, and should be able to
            # say so explicitly rather than have promotion silently never fire.
            min_speakers=max(1, _int("PROMOTE_MIN_SPEAKERS", MIN_SPEAKERS)),
            max_evidence_age_days=max(
                0.0, _float("PROMOTE_EVIDENCE_MAX_AGE_DAYS", MAX_EVIDENCE_AGE_DAYS)),
            require_same_conversation=_bool(
                "PROMOTE_REQUIRE_SAME_CONVERSATION", REQUIRE_SAME_CONVERSATION),
            auto_promote=_bool("PROMOTE_AUTO", AUTO_PROMOTE),
        )


DEFAULT_POLICY = Policy()


@dataclass(frozen=True)
class Decision:
    """Why a candidate was or was not promoted — logged and auditable."""

    promote: bool
    reason: str
    supporting: int = 0
    strong: int = 0
    blocked_by: str = ""

    def __bool__(self) -> bool:
        return self.promote


def epoch(ts) -> float:
    """ISO timestamp -> epoch seconds; 0.0 when unparsable.

    Naive timestamps are read as local time, matching every other timestamp in
    the pipeline (see pools._retrieval_fields)."""
    if not ts:
        return 0.0
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, OSError, OverflowError):
        return 0.0


def _label_compatible(a: str, b: str) -> bool:
    """An empty label claims nothing and is compatible with anything; two
    non-empty ones must match after normalization."""
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    return not a or not b or a == b


def scope_compatible(a: dict, b: dict, *,
                     require_same_conversation: bool = REQUIRE_SAME_CONVERSATION) -> bool:
    """May evidence in scope `a` be combined with evidence in scope `b`.

    Persona identity and language must match exactly: a correction earned by one
    character in one language says nothing about another. Persona *version* is
    included because a prompt rewrite is a different agent for this purpose —
    evidence about how the old one talked should not authorize changes to the
    new one. Conversation scope is on by default and configurable. Mode is
    compared because it comes from a fixed vocabulary (owner / called / followup
    / judge) and genuinely names a different situation.

    **Scenario** compatibility is enforced structurally, not by label. Every
    combination this module performs already requires the events to be about the
    *identical reply text* in the same conversation and mode, which pins the
    scene far more tightly than the 2-5 word label the adjudicator improvises
    per call — and comparing those labels would reject two accounts of the same
    moment for being worded differently, which in practice means nothing is ever
    corroborated. The label is kept in the scope record for audit.
    """
    for key in ("lang", "platform", "persona", "persona_hash",
                "persona_version"):
        if str(a.get(key) or "") != str(b.get(key) or ""):
            return False
    if require_same_conversation and str(a.get("conv_id") or "") != str(b.get("conv_id") or ""):
        return False
    return _label_compatible(a.get("mode", ""), b.get("mode", ""))


def supports_candidate(event: dict, cand: dict, *,
                       policy: Policy = DEFAULT_POLICY) -> bool:
    """Does `event` argue for *this* candidate specifically.

    Three things have to line up, and the third is the one that is easy to get
    wrong: the event must be about the same reply, in a compatible scope, and —
    for a rewrite — must not be proposing a *different* rewrite. An event
    carrying "replace X with C" is real evidence that X was wrong, but counting
    it as support for "replace X with B" would let one correction authorize a
    rewrite nobody asked for.
    """
    ctype = str(cand.get("type") or "")
    if not evidence.supports(event, ctype):
        return False
    if str(event.get("reply") or "").strip() != str(cand.get("reply") or "").strip():
        return False
    if not scope_compatible(candidates.scope_from_event(event), cand.get("scope") or {},
                            require_same_conversation=policy.require_same_conversation):
        return False
    if ctype == candidates.TYPE_PAIR:
        better = str((event.get("adjudication") or {}).get("better") or "").strip()
        if better and better != str(cand.get("better") or "").strip():
            return False
    return True


def find_conflicts(cand: dict, peers, *, policy: Policy = DEFAULT_POLICY,
                   related_events=()) -> list[str]:
    """Candidate ids that propose something incompatible with `cand`.

    Two proposals conflict when they rewrite the same reply, in compatible
    scope, into different things. Only live proposals count: a rejected or
    superseded candidate has already been adjudicated and must not keep
    blocking its replacement.
    """
    out: list[str] = []
    for other in peers or ():
        if other.get("candidate_id") == cand.get("candidate_id"):
            continue
        if other.get("state") not in (candidates.STATE_PROPOSED,
                                      candidates.STATE_PROMOTED):
            continue
        if other.get("type") != cand.get("type"):
            continue
        if str(other.get("reply") or "") != str(cand.get("reply") or ""):
            continue
        if not scope_compatible(other.get("scope") or {}, cand.get("scope") or {},
                                require_same_conversation=policy.require_same_conversation):
            continue
        if str(other.get("better") or "") != str(cand.get("better") or ""):
            # `related_events` is only consulted when we have it: with no
            # events to read, the conflict stands, because the alternative is
            # a veto silently disappearing whenever a caller omits them.
            if related_events and _rewrite_is_unwitnessed(other, related_events):
                continue
            out.append(other.get("candidate_id", ""))
    return [cid for cid in out if cid]


# The two event kinds nobody witnessed: the agent scoring itself, and the
# agent diagnosing itself. Neither is a person disagreeing with anything.
_UNWITNESSED_KINDS = (evidence.KIND_SELF_REVIEW, evidence.KIND_SELF_EVAL)


def _rewrite_is_unwitnessed(cand: dict, events) -> bool:
    """True when no PERSON has argued for this candidate's rewrite.

    The evolution loop proposes `X -> Y` off a single self-review, and such a
    candidate can never clear `min_strong` — a TYPE_PAIR is auto-promotable
    only when its `better` was authored by a strong event, i.e. by a user's
    correction or by the bot's own accepted retry, and an LLM-authored `Y`
    matches one only by coincidence.

    So before this check, an unpromotable proposal still held a VETO: the
    user's real correction of the same reply became "a conflicting candidate
    exists" and both sat in `proposed` forever, blocking each other, with the
    view empty and a human required to break the tie. Measured — control run
    `states: ['promoted']`, with an evolution proposal present
    `states: ['proposed', 'proposed']`.

    A proposal nobody witnessed does not get to outrank one somebody made."""
    better = str(cand.get("better") or "").strip()
    if not better:
        return False
    for ev in events or ():
        if ev.get("kind") in _UNWITNESSED_KINDS:
            continue
        if str((ev.get("adjudication") or {}).get("better") or "").strip() == better:
            return False
    return True


def counter_evidence(cand: dict, events, *, now: float = 0.0,
                     policy: Policy = DEFAULT_POLICY) -> list[str]:
    """Event ids that argue against `cand` — a rejection of a reply somebody
    else laughed at, a laugh at a reply somebody else corrected."""
    ctype = str(cand.get("type") or "")
    reply = str(cand.get("reply") or "")
    better = str(cand.get("better") or "").strip()
    scope = cand.get("scope") or {}
    max_age = policy.max_evidence_age_days * 86400.0
    out = []
    for ev in events or ():
        ev_reply = str(ev.get("reply") or "")
        about_reply = ev_reply == reply
        # A rejection of the REWRITE argues against the pair as directly as a
        # laugh at the reply it would replace. Only rollback covered this, and
        # only for candidates already promoted, so a pair could be rejected
        # while `proposed` and then promoted anyway on a later event about the
        # original — teaching the text the user had just refused.
        about_rewrite = (ctype == candidates.TYPE_PAIR and better
                         and ev_reply.strip() == better)
        if not (about_reply or about_rewrite):
            continue
        # THE AGE WINDOW APPLIES TO ONE OF THESE AND NOT THE OTHER.
        #
        # Counter-evidence about the REPLY expires on purpose — a stale laugh
        # must not veto a fresh correction, which is what "4b: expired
        # counter-evidence does not block promotion" pins.
        #
        # A rejection of the REWRITE is a different statement: this person
        # refused this exact text, and that does not stop being true because a
        # month passed. Expiring it meant the protection could simply be
        # outwaited — measured: rejection on day 0, two fresh corroborating
        # corrections on days 40 and 41, and the refused text promoted into
        # the prompt. A promoted pair rolled back for the same reason never
        # comes back; a proposed one only had to wait.
        if (about_reply and now and max_age
                and now - epoch(ev.get("ts")) > max_age):
            continue
        if not scope_compatible(candidates.scope_from_event(ev), scope,
                                require_same_conversation=policy.require_same_conversation):
            continue
        if (evidence.opposes(ev, ctype) if about_reply
                else evidence.opposes_rewrite(ev)):
            out.append(ev.get("event_id", ""))
    return [eid for eid in out if eid]


def decide(cand: dict, *, linked_events, related_events=(), peers=(),
           now: float = 0.0, policy: Policy = DEFAULT_POLICY,
           owner_id: str = "") -> Decision:
    """Should `cand` be promoted automatically, right now.

    `linked_events` are the events recorded as supporting it, `related_events`
    every event about the same reply (searched for contradictions), `peers` the
    other candidates (searched for conflicting proposals). `owner_id` is the
    configured owner, who is exempt from the distinct-speaker requirement.
    """
    if not policy.auto_promote:
        return Decision(False, "automatic promotion disabled (PROMOTE_AUTO)")
    if cand.get("state") != candidates.STATE_PROPOSED:
        return Decision(False, f"state is {cand.get('state')}, not proposed")

    ctype = str(cand.get("type") or "")
    max_age = policy.max_evidence_age_days * 86400.0
    supporting: list[dict] = []
    seen_ids: set[str] = set()
    for ev in linked_events or ():
        eid = str(ev.get("event_id") or "")
        if eid in seen_ids:
            continue
        if not supports_candidate(ev, cand, policy=policy):
            continue
        if now and max_age:
            age = now - epoch(ev.get("ts"))
            if age > max_age:
                continue
        seen_ids.add(eid)
        supporting.append(ev)

    strong = [e for e in supporting if e.get("strength") == evidence.STRONG]
    against = counter_evidence(cand, related_events, now=now, policy=policy)
    if against:
        return Decision(False, "compatible evidence disagrees — left for review",
                        len(supporting), len(strong), ",".join(against[:3]))
    conflicting = find_conflicts(cand, peers, policy=policy,
                                 related_events=related_events)
    if conflicting:
        return Decision(False, "a conflicting candidate exists — left for review",
                        len(supporting), len(strong), ",".join(conflicting[:3]))
    if len(strong) < policy.min_strong:
        # Say which kind of "not yet" this is. A positive_example cannot
        # reach `min_strong` from any quantity of the events that support it
        # (see evidence.can_be_strong), so reporting it as a count made the
        # audit log read like a threshold the next reaction might cross.
        if not evidence.can_be_strong(ctype):
            return Decision(
                False,
                f"{ctype} is promotable only by a person: nothing that "
                f"supports one classifies strong ({len(supporting)} "
                f"supporting)",
                len(supporting), len(strong))
        return Decision(
            False,
            f"{len(strong)}/{policy.min_strong} strong events "
            f"({len(supporting)} supporting)",
            len(supporting), len(strong))
    if len(supporting) < policy.min_events:
        return Decision(
            False,
            f"{len(supporting)}/{policy.min_events} compatible events",
            len(supporting), len(strong))
    # Distinct people, not distinct events. One member correcting a reply and
    # then accepting the retry produces two compatible events by themselves —
    # and delayed elicitation has the agent *ask* for that second one. The
    # owner is exempt: whoever deployed the agent may teach it alone.
    speakers = {str(e.get("speaker_id") or "") for e in supporting} - {""}
    owner_spoke = bool(owner_id) and str(owner_id) in speakers
    # `not speakers` means no event carried attribution at all — an adapter
    # that does not supply speaker ids, or older events from before the field
    # existed. Missing data must not veto: fall back to the event count rather
    # than silently refusing to ever promote on such a deployment.
    if speakers and not owner_spoke and len(speakers) < policy.min_speakers:
        return Decision(
            False,
            f"{len(speakers)}/{policy.min_speakers} distinct speakers "
            f"({len(supporting)} events, but corroboration means people)",
            len(supporting), len(strong))
    return Decision(
        True,
        f"{len(supporting)} compatible events, {len(strong)} strong",
        len(supporting), len(strong))


# ---------------------------------------------------------------------------
# Legacy weight-based gate (pre-ledger pools)
# ---------------------------------------------------------------------------
# Kept working, not kept current: the ledger above is what new writes go
# through. This is what guards the example pool of a deployment that learned
# before the ledger existed, and it is still the path that pulls a rejected
# reply back out of that pool.

# What each signal is worth. Deliberately set so that no single event of any
# kind can promote on its own: the cheapest path to the pool is two owner
# reactions, and the self-eval channel needs four.
# Each is set slightly above its exact share of PROMOTE_AT so the intended
# count still clears the bar after the decay applied between sightings —
# 4 x 0.25 lands exactly on 1.0 and then loses a hair to decay, which would
# make "four self-evals promote" quietly false.
WEIGHTS = {
    "reaction_owner": 0.60,   # 2 promote
    "reaction_other": 0.34,   # 3 promote
    "self_eval": 0.26,        # 4 promote
}
PROMOTE_AT = 1.0
HALF_LIFE_DAYS = 21.0
# Below this a candidate is not worth carrying; it is dropped on the next touch.
FLOOR = 0.08
MAX_CANDIDATES = 400


def _decayed(weight: float, age_days: float) -> float:
    if age_days <= 0:
        return weight
    return weight * (0.5 ** (age_days / HALF_LIFE_DAYS))


class CandidatePool:
    """Replies with some evidence behind them, but not yet enough to imitate."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._d: dict[str, dict] = {}
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self._d = {k: v for k, v in loaded.items() if isinstance(v, dict)}
        except (OSError, json.JSONDecodeError):
            self._d = {}

    # -- persistence -------------------------------------------------------
    def _save(self) -> None:
        try:
            atomic_write_text(
                self.path,
                json.dumps(self._d, ensure_ascii=False, indent=1),
            )
        except OSError:
            pass

    # -- queries -----------------------------------------------------------
    def confidence(self, reply: str, now: float) -> float:
        rec = self._d.get((reply or "").strip())
        if not rec:
            return 0.0
        age = max(0.0, (now - float(rec.get("ts", now))) / 86400.0)
        return _decayed(float(rec.get("weight", 0.0)), age)

    def sightings(self, reply: str) -> int:
        rec = self._d.get((reply or "").strip())
        return int(rec.get("n", 0)) if rec else 0

    # -- mutations ---------------------------------------------------------
    def record(self, example: dict, source: str, now: float) -> tuple[bool, float]:
        """Add evidence for `example`. Returns (should_promote, confidence).

        On promotion the candidate is consumed, so a reply is banked once and
        does not keep re-promoting every time someone laughs at it again.
        """
        reply = str(example.get("reply") or "").strip()
        if not reply:
            return False, 0.0
        add = WEIGHTS.get(source, WEIGHTS["self_eval"])
        prior = self.confidence(reply, now)
        rec = self._d.get(reply, {})
        total = prior + add
        self._d[reply] = {
            "weight": total,
            "ts": now,
            "n": int(rec.get("n", 0)) + 1,
            "sources": sorted(set(rec.get("sources", []) + [source])),
            "example": example,
        }
        if total >= PROMOTE_AT:
            self._d.pop(reply, None)
            self._save()
            return True, total
        self._prune(now)
        self._save()
        return False, total

    def withdraw(self, reply: str) -> bool:
        """Drop a candidate outright — a human disagreed with this reply."""
        if self._d.pop((reply or "").strip(), None) is not None:
            self._save()
            return True
        return False

    def _prune(self, now: float) -> None:
        for k in [k for k in self._d if self.confidence(k, now) < FLOOR]:
            self._d.pop(k, None)
        if len(self._d) > MAX_CANDIDATES:
            ordered = sorted(self._d.items(), key=lambda kv: float(kv[1].get("ts", 0)))
            for k, _ in ordered[: len(self._d) - MAX_CANDIDATES]:
                self._d.pop(k, None)


def retract_example(path: Path, reply: str) -> int:
    """Remove every banked example whose reply is `reply`. Returns how many.

    The counterpart to promotion: a reply the user later rejected must stop
    being retrieved as a model answer. Rewrites atomically and leaves every
    other row byte-identical.

    Read and replace happen under the same lock appenders take: this is a
    read-modify-write of the whole pool, and the agent banks new examples into
    it continuously, so any row appended between the read and the replace
    would be erased with no trace. A failed replace is allowed to raise rather
    than being reported as "nothing to retract" — the caller logs it, and
    silently leaving a rejected reply retrievable is the worse outcome.
    """
    reply = (reply or "").strip()
    if not reply or not Path(path).exists():
        return 0
    with append_lock(path):
        try:
            lines = Path(path).read_text(encoding="utf-8").splitlines()
        except OSError:
            return 0
        kept, dropped = [], 0
        for ln in lines:
            if not ln.strip():
                continue
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                kept.append(ln)
                continue
            if isinstance(rec, dict) and str(rec.get("reply") or "").strip() == reply:
                dropped += 1
                continue
            kept.append(ln)
        if not dropped:
            return 0
        atomic_write_text(path, "\n".join(kept) + ("\n" if kept else ""))
    return dropped
