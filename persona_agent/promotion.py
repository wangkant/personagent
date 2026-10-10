"""The promotion policy: when may evidence grant a candidate authority.

A single automatic signal must never permanently change behaviour, so
promotion needs ``MIN_EVENTS`` compatible events (same persona, language and
conversation), ``MIN_STRONG`` of them strong, and no compatible evidence
pointing the other way; contradictions are left for a human. Weak evidence
never promotes at any quantity. Also ``retract_example``, how a human
disagreement pulls a row out of the hand-approved example pool.

Pure logic: no clock reads, no LLM. Callers pass `now`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import candidates, evidence
from .config_env import env_bool, env_float, env_int
from .ranking import epoch  # noqa: F401  (re-export; tests and the CLI use promotion.epoch)
from .storage import append_lock, atomic_write_text

# Two events is the smallest number one misreading cannot produce.
MIN_EVENTS = 2
MIN_STRONG = 1
# Distinct people, admin exempt. 1 by default: one person's correction then
# acceptance is how a real clarification looks. Set PROMOTE_MIN_SPEAKERS=2
# where strangers should not teach unaided; blocked candidates wait for a human.
MIN_SPEAKERS = 1
# Older evidence stops counting. 0 disables the window in both directions,
# so stale rejections keep vetoing too.
MAX_EVIDENCE_AGE_DAYS = 30.0
# Cross-room combination would let one loud teacher reach the threshold everywhere.
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
        """Read through config_env, so a typo or a value under a floor is
        logged and falls back to the default, like every other setting."""
        return cls(
            # Floors: PROMOTE_MIN_EVENTS=1 would let one signal promote.
            min_events=env_int("PROMOTE_MIN_EVENTS", MIN_EVENTS,
                               minimum=MIN_EVENTS, env=env),
            min_strong=env_int("PROMOTE_MIN_STRONG", MIN_STRONG,
                               minimum=MIN_STRONG, env=env),
            # Floor of 1: a single-user deployment has nobody to corroborate with.
            min_speakers=env_int("PROMOTE_MIN_SPEAKERS", MIN_SPEAKERS,
                                 minimum=1, env=env),
            max_evidence_age_days=env_float(
                "PROMOTE_EVIDENCE_MAX_AGE_DAYS", MAX_EVIDENCE_AGE_DAYS,
                minimum=0.0, env=env),
            require_same_conversation=env_bool(
                "PROMOTE_REQUIRE_SAME_CONVERSATION", REQUIRE_SAME_CONVERSATION,
                env=env),
            auto_promote=env_bool("PROMOTE_AUTO_ENABLED", AUTO_PROMOTE, env=env),
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


def _label_compatible(a: str, b: str) -> bool:
    """An empty label claims nothing and is compatible with anything; two
    non-empty ones must match after normalization."""
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    return not a or not b or a == b


def scope_compatible(a: dict, b: dict, *,
                     require_same_conversation: bool = REQUIRE_SAME_CONVERSATION,
                     compare_mode: bool = True) -> bool:
    """May evidence in scope `a` be combined with evidence in scope `b`.

    Language, platform, persona (through its lineage) and persona version must
    match; conversation too when required; mode unless `compare_mode=False`
    (would two rewrites meet in one prompt). The adjudicator's scenario label
    is not compared: identical reply text already pins the scene.
    """
    for key in ("lang", "platform", "persona", "persona_version"):
        if str(a.get(key) or "") != str(b.get(key) or ""):
            return False
    # An edited persona document is the same character; a new version is not.
    if evidence.persona_identity(a) != evidence.persona_identity(b):
        return False
    if require_same_conversation and str(a.get("conv_id") or "") != str(b.get("conv_id") or ""):
        return False
    return not compare_mode or _label_compatible(a.get("mode", ""), b.get("mode", ""))


def supports_candidate(event: dict, cand: dict, *,
                       policy: Policy = DEFAULT_POLICY) -> bool:
    """Does `event` argue for *this* candidate: same reply, compatible scope,
    and for a rewrite, not a person proposing a different rewrite (a
    rejection's guessed draft and the complaint a retry answers still count).
    """
    ctype = str(cand.get("type") or "")
    if not evidence.supports(event, ctype):
        return False
    if str(event.get("reply") or "").strip() != str(cand.get("reply") or "").strip():
        return False
    if not scope_compatible(candidates.scope_from_event(event), cand.get("scope") or {},
                            require_same_conversation=policy.require_same_conversation):
        return False
    if ctype == candidates.TYPE_PAIR and not _vouches_for(event, cand):
        answers = str((cand.get("payload") or {}).get("answers") or "")
        guess = (event.get("kind") == evidence.KIND_REACTION
                 and event.get("reaction_type") == "rejection")
        if not (guess or (answers and event.get("event_id") == answers)):
            return False
    return True


def anchors(event: dict, cand: dict) -> bool:
    """Can `event` be the strong one `cand` needs: strong, and for a rewrite,
    naming no rewrite or this one."""
    return (evidence.classify_strength(event) == evidence.STRONG
            and (cand.get("type") != candidates.TYPE_PAIR
                 or _vouches_for(event, cand)))


def _vouches_for(event: dict, cand: dict) -> bool:
    """Does `event` name no rewrite, or this candidate's own one."""
    better = str((event.get("adjudication") or {}).get("better") or "").strip()
    return not better or better == str(cand.get("better") or "").strip()


def find_conflicts(cand: dict, peers, *, policy: Policy = DEFAULT_POLICY,
                   related_events=()) -> list[str]:
    """Live candidates rewriting the same reply, in compatible scope, into
    something else. A proposed rewrite no person argued for (or only the
    complaint `cand` answers) is a draft, not a rival; a promoted one always
    conflicts.
    """
    # None without events: then every conflict stands rather than a veto vanishing.
    witnessed = witnessed_rewrites(related_events) if related_events else None
    answers = str((cand.get("payload") or {}).get("answers") or "")
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
                                require_same_conversation=policy.require_same_conversation,
                                compare_mode=False):
            continue
        if str(other.get("better") or "") != str(cand.get("better") or ""):
            if other.get("state") == candidates.STATE_PROPOSED:
                backing = set(other.get("evidence") or ())
                if answers and backing and backing <= {answers}:
                    continue
                if witnessed is not None:
                    rewrite = str(other.get("better") or "").strip()
                    # An empty rewrite keeps its veto.
                    if rewrite and rewrite not in witnessed:
                        continue
            out.append(other.get("candidate_id", ""))
    return [cid for cid in out if cid]


def answered_drafts(cand: dict, peers, *,
                    policy: Policy = DEFAULT_POLICY) -> list[str]:
    """Proposed rewrites of `cand`'s reply backed only by `cand`'s own
    evidence: drafts of the complaint it answered."""
    if cand.get("type") != candidates.TYPE_PAIR:
        return []
    backing = set(cand.get("evidence") or ())
    out = []
    for other in peers or ():
        if (other.get("candidate_id") == cand.get("candidate_id")
                or other.get("state") != candidates.STATE_PROPOSED
                or other.get("type") != candidates.TYPE_PAIR
                or str(other.get("reply") or "") != str(cand.get("reply") or "")
                or str(other.get("better") or "") == str(cand.get("better") or "")):
            continue
        if not scope_compatible(other.get("scope") or {}, cand.get("scope") or {},
                                require_same_conversation=policy.require_same_conversation,
                                compare_mode=False):
            continue
        ids = set(other.get("evidence") or ())
        if ids and ids <= backing:
            out.append(str(other.get("candidate_id") or ""))
    return [cid for cid in out if cid]


def active_rivals(cand: dict, ledger_rows, *,
                  policy: Policy = DEFAULT_POLICY) -> list[dict]:
    """Promoted rewrites of `cand`'s reply into something else that one
    prompt would carry beside it (an operator uses `supersede` instead)."""
    if cand.get("type") != candidates.TYPE_PAIR:
        return []
    reply = str(cand.get("reply") or "").strip()
    better = str(cand.get("better") or "").strip()
    return [
        other for other in ledger_rows or ()
        if other.get("candidate_id") != cand.get("candidate_id")
        and other.get("state") == candidates.STATE_PROMOTED
        and other.get("type") == candidates.TYPE_PAIR
        and str(other.get("reply") or "").strip() == reply
        and str(other.get("better") or "").strip() != better
        and scope_compatible(other.get("scope") or {}, cand.get("scope") or {},
                             require_same_conversation=policy.require_same_conversation,
                             compare_mode=False)
    ]


# The agent scoring or diagnosing itself: no person witnessed either.
_UNWITNESSED_KINDS = (evidence.KIND_SELF_REVIEW, evidence.KIND_SELF_EVAL)


def witnessed_rewrites(events) -> frozenset:
    """Every rewrite a person argued for: not a rejection's guessed draft, a
    dismissed event's, or a retry the person merely moved on from."""
    return frozenset(
        str((event.get("adjudication") or {}).get("better") or "").strip()
        for event in events or ()
        if event.get("kind") not in _UNWITNESSED_KINDS
        and (event.get("adjudication") or {}).get("accept")
        and not (event.get("kind") == evidence.KIND_REACTION
                 and event.get("reaction_type") == "rejection")
    ) - {""}


def related_events(cand: dict, events) -> list[dict]:
    """Events about the reply `cand` replaces or the rewrite it proposes:
    `decide`'s related_events, shared so every caller judges from one list."""
    wanted = {str(cand.get("reply") or "").strip()}
    better = str(cand.get("better") or "").strip()
    if better:
        wanted.add(better)
    return [event for event in events or ()
            if str(event.get("reply") or "").strip() in wanted]


class EvidenceIndex:
    """Events and candidates by reply text, built once, so judging many
    candidates reads only what each one is about instead of the whole log."""

    def __init__(self, events: list[dict], peers: list[dict]) -> None:
        self.events = events
        self.by_id = {e.get("event_id"): e for e in events}
        self._pos = {e.get("event_id"): i for i, e in enumerate(events)}
        self._by_text: dict[str, list[int]] = {}
        for i, event in enumerate(events):
            self._by_text.setdefault(str(event.get("reply") or "").strip(), []).append(i)
        self._peers: dict[str, list[dict]] = {}
        for cand in peers:
            self._peers.setdefault(str(cand.get("reply") or ""), []).append(cand)

    def linked(self, cand: dict) -> list[dict]:
        """`cand`'s own evidence, once each, in log order."""
        ids = {eid for eid in cand.get("evidence") or [] if eid in self.by_id}
        return [self.by_id[eid] for eid in sorted(ids, key=self._pos.__getitem__)]

    def related(self, cand: dict) -> list[dict]:
        # Narrowed by text, then still filtered by related_events' own rule.
        texts = {str(cand.get("reply") or "").strip(),
                 str(cand.get("better") or "").strip()}
        hits = sorted(i for text in texts for i in self._by_text.get(text, ()))
        return related_events(cand, [self.events[i] for i in hits])

    def peers(self, cand: dict) -> list[dict]:
        """The only candidates find_conflicts can match: same reply text."""
        return self._peers.get(str(cand.get("reply") or ""), [])


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
        # Rollback only covers promoted pairs; this stops a proposed one whose
        # rewrite was refused.
        about_rewrite = (ctype == candidates.TYPE_PAIR and better
                         and ev_reply.strip() == better)
        if not (about_reply or about_rewrite):
            continue
        # Only evidence about the reply expires: a refused rewrite must not be
        # outwaited.
        if (about_reply and now and max_age > 0
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
           admin_ids=()) -> Decision:
    """Should `cand` be promoted automatically, right now. `related_events`
    are searched for contradictions, `peers` for conflicting proposals."""
    if not policy.auto_promote:
        return Decision(False, "automatic promotion disabled (PROMOTE_AUTO_ENABLED)")
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
        if now and max_age > 0:
            age = now - epoch(ev.get("ts"))
            if age > max_age:
                continue
        seen_ids.add(eid)
        supporting.append(ev)

    # Re-derived, not read: `strength` is outside the event id, so a hand edit
    # could change it without breaking the row.
    strong = [e for e in supporting if anchors(e, cand)]
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
        # A type no event can make strong must not read like a reachable count.
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
    # Distinct people, not events; the admin may teach alone.
    speakers = {str(e.get("speaker_id") or "") for e in supporting} - {""}
    # Compared as stored: make_event cuts speaker_id at 64 characters.
    admins = {evidence._text(o, 64) for o in admin_ids} - {""}
    admin_spoke = bool(admins & speakers)
    # No attribution at all must not veto: the event count decides.
    if speakers and not admin_spoke and len(speakers) < policy.min_speakers:
        return Decision(
            False,
            f"{len(speakers)}/{policy.min_speakers} distinct speakers "
            f"({len(supporting)} events, but corroboration means people)",
            len(supporting), len(strong))
    return Decision(
        True,
        f"{len(supporting)} compatible events, {len(strong)} strong",
        len(supporting), len(strong))


def retract_example(path: Path, reply: str) -> int:
    """Remove every banked example whose reply is `reply`; returns how many.

    Atomic, other rows byte-identical, under the appenders' lock so a
    concurrent append is not erased. A failed replace raises rather than
    silently leaving the rejected reply retrievable.
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
