"""Append-only record of what happened in a conversation.

An evidence event says *a thing occurred*: this reply was sent, that person
quoted it and said "no, I meant X", the adjudicator read the exchange and
returned this verdict. Nothing more. An event carries no authority over future
behaviour — it cannot change a prompt, grow a retrieval pool, or silence a
reply. It is testimony, and testimony is worth keeping even when it is wrong,
because the record of a bad teaching is how you find out you were taught badly.

Authority lives one layer up: adjudicating evidence produces a *candidate*
(candidates.py), and only a *promoted* candidate reaches retrieval. The split
exists because the two have opposite requirements — evidence must be cheap to
write and never rewritten, authority must be expensive to grant and reversible.

What is deliberately NOT stored:

- **Chain of thought.** Only the structured verdict and the one-sentence reason
  the adjudicator was asked for. The raw model output never lands on disk.
- Anything outside the runtime directory. Events quote real conversations, so
  the log lives with the other gitignored learned state (see paths.py).

Event identity is the sha256 of the semantic payload, so the same event
recorded twice — a retried background task, a replayed webhook — is one row.
Pure logic: no clock reads, no LLM. Callers pass timestamps.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .storage import (
    append_jsonl_unlocked,
    append_lock,
    append_only_health,
    read_validated_jsonl,
)

SCHEMA = 2

# What produced the event.
KIND_REACTION = "reaction"              # a directed user reaction to a reply
KIND_RETRY_ACCEPTANCE = "retry_acceptance"  # a retry the user then accepted
KIND_SELF_EVAL = "self_eval"            # the agent's own quality score
KIND_SELF_REVIEW = "self_review"        # the agent's own failure diagnosis
KINDS = (KIND_REACTION, KIND_RETRY_ACCEPTANCE, KIND_SELF_EVAL, KIND_SELF_REVIEW)

# How much authority a single event can lend. See classify_strength.
STRONG = "strong"
NEGATIVE_ONLY = "negative_only"
WEAK = "weak"

REACTION_TYPES = ("correction", "rejection", "positive", "neutral")

_MAX_TEXT = 1000
_MAX_CTX_LINES = 4
_MAX_CTX_CHARS = 300
_MAX_REASON = 200

# Fields that define an event's identity. Timestamps and derived fields are
# excluded: the same reaction re-adjudicated a second later is the same event.
_ID_FIELDS = (
    "kind", "lang", "platform", "conv_id", "persona", "persona_hash",
    "persona_version", "speaker_id", "recipient_id", "reply", "context",
    "reaction_text", "reaction_type", "directed", "direction", "scope_mode",
    "source_event_id", "parent_event_id",
)

_SUPPORTED_SCHEMAS = (1, SCHEMA)
_DEFAULT_WARNING_BYTES = 50_000_000


def _text(value, limit: int = _MAX_TEXT) -> str:
    return str(value or "").strip()[:limit]


def _context(lines) -> list[str]:
    if isinstance(lines, str):
        lines = [lines]
    return [_text(line, _MAX_CTX_CHARS) for line in (lines or [])][-_MAX_CTX_LINES:]


def event_id(payload: dict) -> str:
    """Stable identity for an event: sha256 over its semantic fields."""
    blob = json.dumps(
        {k: payload.get(k, "") for k in _ID_FIELDS},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _validate_event(record: dict) -> str | None:
    schema = record.get("schema")
    if not isinstance(schema, int) or schema not in _SUPPORTED_SCHEMAS:
        return "unsupported schema"
    if not isinstance(record.get("event_id"), str) or not record["event_id"]:
        return "event_id must be a non-empty string"
    if record.get("kind") not in KINDS:
        return "unknown evidence kind"
    if not isinstance(record.get("context"), list):
        return "context must be a list"
    if not isinstance(record.get("adjudication"), dict):
        return "adjudication must be an object"
    if schema == SCHEMA and record["event_id"] != event_id(record):
        return "event_id does not match semantic payload"
    return None


def _file_stamp(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
        return stat.st_size, stat.st_mtime_ns
    except OSError:
        return 0, 0


def _warning_bytes(override: int | None = None) -> int:
    if override is not None:
        return max(0, int(override))
    try:
        return max(0, int(os.getenv(
            "AGENT_EVIDENCE_WARN_BYTES", str(_DEFAULT_WARNING_BYTES))))
    except ValueError:
        return _DEFAULT_WARNING_BYTES


def classify_strength(event: dict) -> str:
    """How much this single event may authorize on its own.

    - ``STRONG`` — an explicit directed correction from the person the reply
      was aimed at, carrying a concrete replacement; or a retry the user then
      accepted. Someone told the agent it was wrong *about them* and said what
      right looks like.
    - ``NEGATIVE_ONLY`` — a rejection with nothing concrete in it, or a
      correction from a bystander. Real evidence that something was off, but
      not a mandate to rewrite: **owner status does not make someone the
      affected recipient**, so a third party's correction — however trusted —
      lands here rather than in STRONG.
    - ``WEAK`` — laughter, agreement, banter, the agent's own score. Never
      sufficient to promote anything, at any quantity.

    A dismissed adjudication (``accept`` false) is still recorded, and still
    classified, but the promotion policy ignores it as support.
    """
    kind = event.get("kind")
    if kind == KIND_RETRY_ACCEPTANCE:
        # Acceptance only counts from the person the retry was for. A bystander
        # laughing at the second attempt is not the complainant being satisfied.
        if not _same_person(event):
            return NEGATIVE_ONLY
        # Silence is not acceptance. `neutral` means the person simply moved
        # on — and the "better" text of a retry-acceptance event is the agent's
        # OWN retry, so counting a topic change as STRONG would let the agent
        # manufacture a mandate for its own wording out of nothing happening.
        if event.get("reaction_type") == "neutral":
            return NEGATIVE_ONLY
        return STRONG
    if kind == KIND_SELF_REVIEW:
        # The agent noticing its own failure and drafting a fix. Concrete, but
        # nobody witnessed it — a single unwitnessed signal cannot authorize.
        return NEGATIVE_ONLY
    if kind == KIND_SELF_EVAL:
        return WEAK
    adj = event.get("adjudication") or {}
    rtype = event.get("reaction_type")
    if rtype == "correction" and _text(adj.get("better")):
        return STRONG if _same_person(event) else NEGATIVE_ONLY
    if rtype in ("correction", "rejection"):
        return NEGATIVE_ONLY
    return WEAK


# The six fields promotion compares, and the length each is STORED at. One
# table, because the producer and the comparator have to agree and they live
# in different modules: `make_event` writes through it, and
# `agent._examples_for_prompt` reads a live scope through `normalize_scope`
# before comparing. They did not agree, and the failure was silent — see
# `normalize_scope`.
SCOPE_LIMITS = {
    "lang": 16,
    "platform": 32,
    "conv_id": 128,
    "persona": 64,
    "persona_hash": 64,
    "persona_version": 32,
}


def normalize_scope(scope: dict) -> dict:
    """A live scope, as the ledger would have stored it.

    `_authorized_view` requires all six fields to match exactly, and the
    ledger holds TRUNCATED values while retrieval built its side from the raw
    configuration. So `PERSONA_VERSION=release-2026-08-28-persona-rewrite-b7f3`
    (45 characters) was written as 32 and compared against 45: candidates
    promoted normally, the view file was written normally, `candidates_admin
    list --state promoted` showed them, and every single row was dropped on
    every turn. Nothing logged anything. The learning loop looked healthy and
    was inert.

    Any field over its limit is a silent total failure of retrieval, which is
    why this is a shared function and not a comment asking the next caller to
    remember."""
    return {key: _scope_text(scope.get(key), limit)
            for key, limit in SCOPE_LIMITS.items()}


def _scope_text(value, limit: int) -> str:
    """Bounded like everything else here, but still DISTINCT.

    Normalising both sides through a plain truncation fixed the comparison and
    introduced a quieter version of the same bug: two values differing only
    past the limit became EQUAL, so material promoted in a room whose id
    shared a 128-character prefix with another was authorized into that other
    room's prompt, and `PROMOTE_REQUIRE_SAME_CONVERSATION` could not stop it
    because the two ids really were the same string by then. Two release
    labels sharing a 32-character prefix were likewise one agent.

    An over-length value keeps a readable prefix and carries a digest of the
    WHOLE original, so the field stays bounded and the comparison stays
    injective. Short values — every real id — are untouched, so this changes
    nothing for anyone it was not already broken for."""
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return text[:max(0, limit - 9)] + "~" + digest


def _same_person(event: dict) -> bool:
    """Is the speaker the person the reply was aimed at."""
    recipient = _text(event.get("recipient_id"), 64)
    return bool(recipient) and recipient == _text(event.get("speaker_id"), 64)


def make_event(
    *,
    kind: str,
    ts: str,
    lang: str = "",
    platform: str = "",
    conv_id: str = "",
    persona: str = "",
    persona_hash: str = "",
    persona_version: str = "",
    speaker_id: str = "",
    speaker_name: str = "",
    recipient_id: str = "",
    reply: str = "",
    context=None,
    reaction_text: str = "",
    directed: bool = False,
    direction: str = "",
    reaction_type: str = "",
    adjudication: dict | None = None,
    adjudicator_model: str = "",
    adjudicator_prompt_version: str = "",
    source_event_id: str = "",
    parent_event_id: str = "",
) -> dict:
    """Build a normalized, id-stamped evidence event.

    ``adjudication`` is reduced to the structured verdict plus a short reason —
    any other key the caller passes (a raw completion, a reasoning trace) is
    dropped here rather than trusted not to exist.
    """
    adj = adjudication or {}
    event = {
        "schema": SCHEMA,
        "event_id": "",
        "ts": _text(ts, 32),
        "kind": kind if kind in KINDS else KIND_REACTION,
        # Through SCOPE_LIMITS, so the length retrieval compares at cannot
        # drift from the length this writes at.
        **normalize_scope({
            "lang": lang, "platform": platform, "conv_id": conv_id,
            "persona": persona, "persona_hash": persona_hash,
            "persona_version": persona_version,
        }),
        "speaker_id": _text(speaker_id, 64),
        "speaker_name": _text(speaker_name, 64),
        "recipient_id": _text(recipient_id, 64),
        "reply": _text(reply),
        "context": _context(context),
        "reaction_text": _text(reaction_text),
        "directed": bool(directed),
        "direction": _text(direction, 16),
        "scope_mode": _text(adj.get("mode"), 32),
        "source_event_id": _text(source_event_id, 128),
        "reaction_type": (reaction_type if reaction_type in REACTION_TYPES else ""),
        "adjudication": {
            "accept": bool(adj.get("accept")),
            "better": _text(adj.get("better")),
            "scenario": _text(adj.get("scenario"), 64),
            "mode": _text(adj.get("mode"), 32),
            "intent": _text(adj.get("intent"), 32),
            "score": adj.get("score") if isinstance(adj.get("score"), int) else None,
            "reason": _text(adj.get("reason"), _MAX_REASON),
        },
        "adjudicator_model": _text(adjudicator_model, 64),
        "adjudicator_prompt_version": _text(adjudicator_prompt_version, 32),
        "parent_event_id": _text(parent_event_id, 32),
    }
    event["event_id"] = event_id(event)
    event["strength"] = classify_strength(event)
    return event


def supports(event: dict, candidate_type: str) -> bool:
    """True when this event argues *for* a candidate of that type.

    Direction matters as much as strength. A laugh at a reply supports keeping
    it; a correction of the same reply supports replacing it. Neither supports
    the other, and treating a mixed pile as a majority vote is how a feedback
    loop talks itself into contradictions.
    """
    if not (event.get("adjudication") or {}).get("accept"):
        return False
    kind = event.get("kind")
    if candidate_type == "preference_pair":
        if kind in (KIND_RETRY_ACCEPTANCE, KIND_SELF_REVIEW):
            return True
        return event.get("reaction_type") in ("correction", "rejection")
    if candidate_type == "positive_example":
        # NOT a retry acceptance, and the exclusion is load-bearing. That
        # event is about the PAIR — its `reply` field is the text the user
        # REJECTED and its `better` is the retry — so admitting it here makes
        # "the user accepted the fix" argue that the text they rejected is a
        # good example to imitate. It is STRONG, so one of them would clear
        # `min_strong` on its own. Nothing stopped that today except
        # `promotion.supports_candidate`'s reply-equality check happening to
        # disagree, which is a guard by accident and not by intent.
        if kind in (KIND_RETRY_ACCEPTANCE, KIND_SELF_REVIEW):
            return False
        if kind == KIND_SELF_EVAL:
            return True
        return event.get("reaction_type") == "positive"
    return False


# Which candidate types any single event can lend STRONG authority to.
# Derived from the pair of functions above, not asserted alongside them:
# `supports` says what argues FOR a type and `classify_strength` says how much
# one event may lend, so "can this type ever clear min_strong" is their
# intersection. `tests/test_ledger.py` re-derives this by scanning every
# kind x reaction_type combination and fails if the answer moves.
STRONG_CAPABLE_TYPES = frozenset({"preference_pair"})


def can_be_strong(candidate_type: str) -> bool:
    """Can any event that SUPPORTS this candidate type ever classify STRONG.

    False for `positive_example`, and that is the POLICY rather than an
    oversight. What supports one is a self-eval or a positive reaction, and
    `classify_strength` calls both WEAK: "laughter, agreement, banter, the
    agent's own score. Never sufficient to promote anything, at any
    quantity." Such a candidate is still proposed, still audited, and still
    promotable — by a person, through `tools/candidates_admin.py promote`.
    It is waiting for a human, not for more events.

    Promotion asks this so its refusal can say WHICH of those two it is. The
    reason read "0/1 strong events (4 supporting)", which describes a
    threshold you could reach by waiting, and no amount of waiting reaches it.
    """
    return candidate_type in STRONG_CAPABLE_TYPES


def opposes_rewrite(event: dict) -> bool:
    """True when this event argues against a pair's PROPOSED replacement.

    `opposes` below asks about the reply a candidate would replace. This asks
    about the text it would replace it WITH, which is a different question and
    had no answer: a user rejecting or correcting the bot's `better` text is
    saying the fix itself is wrong.

    Without it, a pair still sitting in `proposed` when its rewrite was
    rejected could be promoted afterwards by an unrelated second event about
    the original — and go on to teach the exact text the user refused.
    `_rollback_promoted_for` covered only candidates that were already
    PROMOTED, so the window between proposal and promotion was open."""
    if not (event.get("adjudication") or {}).get("accept"):
        return False
    # A PERSON has to have refused it. `promotion._rewrite_is_unwitnessed`
    # excludes these two kinds forty lines away and for the same reason — a
    # proposal nobody witnessed does not outrank one somebody made — and the
    # thesis has to hold on both sides of the file. Without this, a
    # self-review carrying `reaction_type="rejection"` would veto a
    # two-strong user correction. Not reachable today; neither `_evolve_tick`
    # nor `_evaluate_reply` sets a reaction type on a self event, which is
    # precisely the kind of "not reachable today" that stops being true.
    if event.get("kind") in (KIND_SELF_REVIEW, KIND_SELF_EVAL):
        return False
    return event.get("reaction_type") in ("rejection", "correction")


def opposes(event: dict, candidate_type: str) -> bool:
    """True when this event argues *against* a candidate of that type."""
    if not (event.get("adjudication") or {}).get("accept"):
        return False
    kind = event.get("kind")
    if candidate_type == "preference_pair":
        # NOT a retry acceptance, and this one was live. `reaction_type` on
        # that event is "positive" because the user accepted the RETRY —
        # the opposite of liking the reply the pair replaces, which is what a
        # positive reaction means on every other kind. Reading the field
        # without the kind turned the STRONG event a retry-completion pair is
        # BUILT FROM into counter-evidence against that same pair:
        # `supports` and `opposes` both answered True for one event, and
        # `decide` returned "compatible evidence disagrees". The
        # zero-user-effort retry loop — a documented feature — could never
        # promote anything, in any deployment.
        if kind in (KIND_RETRY_ACCEPTANCE, KIND_SELF_REVIEW):
            return False
        return event.get("reaction_type") == "positive"
    if candidate_type == "positive_example":
        return event.get("reaction_type") in ("correction", "rejection")
    return False


class EvidenceLog:
    """The append-only event log. Never rewritten, never truncated in place.

    Loaded lazily and cached in memory: the id index is what makes appends
    idempotent, and rebuilding it per write would re-read the whole log on
    every reaction.
    """

    def __init__(self, path):
        self.path = Path(path)
        self._events: list[dict] | None = None
        self._ids: set[str] = set()
        self._stamp: tuple[int, int] = (-1, -1)
        self._quarantined = []

    # -- reads -------------------------------------------------------------
    def _load(self) -> list[dict]:
        stamp = _file_stamp(self.path)
        if self._events is None or stamp != self._stamp:
            result = read_validated_jsonl(self.path, _validate_event)
            self._events = result.rows
            self._ids = {e["event_id"] for e in result.rows}
            self._quarantined = result.quarantined
            self._stamp = stamp
        return self._events

    def all(self) -> list[dict]:
        return list(self._load())

    def get(self, eid: str) -> dict | None:
        for e in self._load():
            if e.get("event_id") == eid:
                return e
        return None

    def many(self, ids) -> list[dict]:
        wanted = set(ids or ())
        return [e for e in self._load() if e.get("event_id") in wanted]

    def has(self, eid: str) -> bool:
        self._load()
        return eid in self._ids

    # -- writes ------------------------------------------------------------
    def append(self, event: dict) -> bool:
        """Append one event. Returns False when it was already recorded.

        A duplicate is not an error: the same reaction can be delivered twice,
        and the point of a content-addressed id is that replaying it changes
        nothing.
        """
        eid = event.get("event_id")
        if not eid:
            return False
        reason = _validate_event(event)
        if reason:
            raise ValueError(f"invalid evidence event: {reason}")
        with append_lock(self.path):
            # Refresh while holding the interprocess lock — a second process
            # may have appended this content-addressed event since our cache
            # was built — but ONLY when the file actually moved.
            #
            # This re-read and re-validated the WHOLE log on every append: at
            # 20 000 rows, 452 ms, the single most expensive item on the
            # reaction path, and 97 % of it was `event_id()` re-deriving the
            # sha256 content address of rows already sitting on disk. The log
            # is APPEND-ONLY, so an unchanged (size, mtime) stamp is proof
            # that nobody added anything and the cache is exact — and size
            # alone settles it, because an append always changes the size.
            # The safety the old comment is about is preserved: when the stamp
            # HAS moved, the full validating re-read still happens, under the
            # same lock, before the dedup check.
            if self._events is None or _file_stamp(self.path) != self._stamp:
                result = read_validated_jsonl(self.path, _validate_event)
                self._events = result.rows
                self._ids = {row["event_id"] for row in result.rows}
                self._quarantined = result.quarantined
            if eid in self._ids:
                self._stamp = _file_stamp(self.path)
                return False
            append_jsonl_unlocked(self.path, event)
            # Rebound rather than mutated in place: `all()` hands this list
            # out, and a caller holding one must not see it grow underneath.
            self._events = self._events + [event]
            self._ids = self._ids | {eid}
            self._stamp = _file_stamp(self.path)
        return True

    def health_metadata(self, *, warning_bytes: int | None = None) -> dict:
        self._load()
        return append_only_health(
            self.path,
            warning_bytes=_warning_bytes(warning_bytes),
            quarantined_rows=len(self._quarantined),
        )

