"""Append-only record of what happened in a conversation.

Only a promoted candidate (candidates.py, promotion.py) reaches retrieval.
An event stores the adjudicator's structured verdict and short reason.
Identity is the sha256 of the semantic payload, so a replayed event is one row.

Pure logic: no clock reads, no LLM. Callers pass timestamps.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .storage import (
    append_jsonl_unlocked,
    append_lock,
    append_only_health,
    file_stamp,
    read_validated_jsonl,
    warning_bytes as _warning_bytes,
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

# Identity fields: no timestamps or derived fields, so a re-adjudicated reaction is one event.
_ID_FIELDS = (
    "kind", "lang", "platform", "conv_id", "persona", "persona_hash",
    "persona_version", "speaker_id", "recipient_id", "reply", "context",
    "reaction_text", "reaction_type", "directed", "direction", "scope_mode",
    "source_event_id", "parent_event_id",
)

_SUPPORTED_SCHEMAS = (1, SCHEMA)
_WARN_BYTES_ENV = "LEDGER_EVIDENCE_WARN_BYTES"


def _text(value, limit: int = _MAX_TEXT) -> str:
    return str(value or "").strip()[:limit]


def _context(lines) -> list[str]:
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


def classify_strength(event: dict) -> str:
    """How much this single event may authorize on its own.

    ``STRONG``: a correction with a replacement from the reply's recipient,
    or a retry that person accepted. ``NEGATIVE_ONLY``: a rejection, or a
    bystander's correction (admin status does not make someone the
    recipient). ``WEAK``: laughter, agreement, the agent's own score.
    """
    kind = event.get("kind")
    if kind == KIND_RETRY_ACCEPTANCE:
        # Only the rejected reply's recipient can accept its retry.
        if not _same_person(event):
            return NEGATIVE_ONLY
        # Moving on is not acceptance: the "better" side is the agent's own retry.
        if event.get("reaction_type") == "neutral":
            return NEGATIVE_ONLY
        return STRONG
    if kind == KIND_SELF_REVIEW:
        # Concrete, but nobody witnessed it.
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


# (persona_version, persona_hash) -> lineage root, registered from
# persona_lineage.json: every hash in one lineage is the same character.
_PERSONA_LINEAGE: dict[tuple[str, str], str] = {}


def register_persona_lineage(version: str, hashes) -> None:
    hashes = [str(h) for h in hashes if h]
    if not hashes:
        return
    for h in hashes:
        _PERSONA_LINEAGE[(version or "", h)] = hashes[0]


def persona_identity(scope: dict) -> str:
    """The persona a scope belongs to: its lineage root when known, else its hash."""
    phash = str(scope.get("persona_hash") or "")
    return _PERSONA_LINEAGE.get((str(scope.get("persona_version") or ""), phash), phash)


# The scope fields and the length each is stored at. make_event writes through
# this table and retrieval normalizes the live scope with it; they must agree.
SCOPE_LIMITS = {
    "lang": 16,
    "platform": 32,
    "conv_id": 128,
    "persona": 64,
    "persona_hash": 64,
    "persona_version": 32,
}


def normalize_scope(scope: dict) -> dict:
    """A live scope bounded the way the ledger stored it, so an over-long
    value still compares equal to its stored form."""
    return {key: _scope_text(scope.get(key), limit)
            for key, limit in SCOPE_LIMITS.items()}


def _scope_text(value, limit: int) -> str:
    """Bounded but still distinct: an over-long value keeps a prefix plus a
    digest of the whole, so two ids sharing a prefix never become equal."""
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
    """Build a normalized, id-stamped evidence event. ``adjudication`` keeps
    only the structured verdict and a short reason; any other key is dropped."""
    adj = adjudication or {}
    event = {
        "schema": SCHEMA,
        "event_id": "",
        "ts": _text(ts, 32),
        "kind": kind,
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
    """True when this event argues *for* a candidate of that type: a laugh
    supports keeping a reply, a correction supports replacing it."""
    if not (event.get("adjudication") or {}).get("accept"):
        return False
    kind = event.get("kind")
    if candidate_type == "preference_pair":
        if kind in (KIND_RETRY_ACCEPTANCE, KIND_SELF_REVIEW):
            return True
        return event.get("reaction_type") in ("correction", "rejection")
    if candidate_type == "positive_example":
        # Not a retry acceptance: its `reply` is the text the user rejected.
        if kind in (KIND_RETRY_ACCEPTANCE, KIND_SELF_REVIEW):
            return False
        if kind == KIND_SELF_EVAL:
            return True
        return event.get("reaction_type") == "positive"
    return False


# Types some supporting event can make STRONG: the intersection of `supports`
# and `classify_strength` (tests/test_ledger.py re-derives it).
STRONG_CAPABLE_TYPES = frozenset({"preference_pair"})


def can_be_strong(candidate_type: str) -> bool:
    """Can any event that supports this type classify STRONG. False for
    `positive_example` by policy: only a person can promote one."""
    return candidate_type in STRONG_CAPABLE_TYPES


def opposes_rewrite(event: dict) -> bool:
    """True when this event argues against a pair's proposed replacement text
    (`opposes` asks about the reply it would replace)."""
    if not (event.get("adjudication") or {}).get("accept"):
        return False
    # A person has to have refused it, as in promotion.witnessed_rewrites.
    if event.get("kind") in (KIND_SELF_REVIEW, KIND_SELF_EVAL):
        return False
    return event.get("reaction_type") in ("rejection", "correction")


def opposes(event: dict, candidate_type: str) -> bool:
    """True when this event argues *against* a candidate of that type."""
    if not (event.get("adjudication") or {}).get("accept"):
        return False
    kind = event.get("kind")
    if candidate_type == "preference_pair":
        # A retry acceptance is "positive" about the retry, not the replaced reply.
        if kind in (KIND_RETRY_ACCEPTANCE, KIND_SELF_REVIEW):
            return False
        return event.get("reaction_type") == "positive"
    if candidate_type == "positive_example":
        return event.get("reaction_type") in ("correction", "rejection")
    return False


class EvidenceLog:
    """The append-only event log, cached in memory with the id index that
    makes appends idempotent."""

    def __init__(self, path):
        self.path = Path(path)
        self._events: list[dict] | None = None
        self._ids: set[str] = set()
        self._stamp: tuple[int, int] = (-1, -1)
        self._quarantined = []

    # -- reads -------------------------------------------------------------
    def _load(self) -> list[dict]:
        stamp = file_stamp(self.path)
        if self._events is None or stamp != self._stamp:
            result = read_validated_jsonl(self.path, _validate_event)
            self._events = result.rows
            self._ids = {e["event_id"] for e in result.rows}
            self._quarantined = result.quarantined
            self._stamp = stamp
        return self._events

    def all(self) -> list[dict]:
        return list(self._load())

    def many(self, ids) -> list[dict]:
        wanted = set(ids or ())
        return [e for e in self._load() if e.get("event_id") in wanted]

    # -- writes ------------------------------------------------------------
    def append(self, event: dict) -> bool:
        """Append one event. Returns False when it was already recorded."""
        eid = event["event_id"]
        with append_lock(self.path):
            # Another process may have appended: re-read only if the stamp moved.
            if self._events is None or file_stamp(self.path) != self._stamp:
                result = read_validated_jsonl(self.path, _validate_event)
                self._events = result.rows
                self._ids = {row["event_id"] for row in result.rows}
                self._quarantined = result.quarantined
            if eid in self._ids:
                self._stamp = file_stamp(self.path)
                return False
            append_jsonl_unlocked(self.path, event)
            # Rebound, not mutated: callers may hold the list all() returned.
            self._events = self._events + [event]
            self._ids = self._ids | {eid}
            self._stamp = file_stamp(self.path)
        return True

    def health_metadata(self, *, warning_bytes: int | None = None) -> dict:
        self._load()
        return append_only_health(
            self.path,
            warning_bytes=_warning_bytes(_WARN_BYTES_ENV, warning_bytes),
            quarantined_rows=len(self._quarantined),
        )

