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
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import candidates, evidence

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
            raw = str(env.get(name, "")).strip().lower()
            return default if not raw else raw == "true"

        return cls(
            # Floors, not suggestions: PROMOTE_MIN_EVENTS=1 would reintroduce
            # exactly the failure this module exists to prevent.
            min_events=max(2, _int("PROMOTE_MIN_EVENTS", MIN_EVENTS)),
            min_strong=max(1, _int("PROMOTE_MIN_STRONG", MIN_STRONG)),
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
    for key in ("lang", "persona", "persona_hash", "persona_version"):
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


def find_conflicts(cand: dict, peers, *, policy: Policy = DEFAULT_POLICY) -> list[str]:
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
            out.append(other.get("candidate_id", ""))
    return [cid for cid in out if cid]


def counter_evidence(cand: dict, events, *,
                     policy: Policy = DEFAULT_POLICY) -> list[str]:
    """Event ids that argue against `cand` — a rejection of a reply somebody
    else laughed at, a laugh at a reply somebody else corrected."""
    ctype = str(cand.get("type") or "")
    reply = str(cand.get("reply") or "")
    scope = cand.get("scope") or {}
    out = []
    for ev in events or ():
        if str(ev.get("reply") or "") != reply:
            continue
        if not scope_compatible(candidates.scope_from_event(ev), scope,
                                require_same_conversation=policy.require_same_conversation):
            continue
        if evidence.opposes(ev, ctype):
            out.append(ev.get("event_id", ""))
    return [eid for eid in out if eid]


def decide(cand: dict, *, linked_events, related_events=(), peers=(),
           now: float = 0.0, policy: Policy = DEFAULT_POLICY) -> Decision:
    """Should `cand` be promoted automatically, right now.

    `linked_events` are the events recorded as supporting it, `related_events`
    every event about the same reply (searched for contradictions), `peers` the
    other candidates (searched for conflicting proposals).
    """
    if not policy.auto_promote:
        return Decision(False, "automatic promotion disabled (PROMOTE_AUTO)")
    if cand.get("state") != candidates.STATE_PROPOSED:
        return Decision(False, f"state is {cand.get('state')}, not proposed")

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
    against = counter_evidence(cand, related_events, policy=policy)
    if against:
        return Decision(False, "compatible evidence disagrees — left for review",
                        len(supporting), len(strong), ",".join(against[:3]))
    conflicting = find_conflicts(cand, peers, policy=policy)
    if conflicting:
        return Decision(False, "a conflicting candidate exists — left for review",
                        len(supporting), len(strong), ",".join(conflicting[:3]))
    if len(strong) < policy.min_strong:
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
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(self._d, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
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
    """
    reply = (reply or "").strip()
    if not reply or not Path(path).exists():
        return 0
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
    try:
        fd, tmp = tempfile.mkstemp(dir=str(Path(path).parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(kept) + ("\n" if kept else ""))
        os.replace(tmp, path)
    except OSError:
        return 0
    return dropped
