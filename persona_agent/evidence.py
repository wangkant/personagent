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
from pathlib import Path

from .pools import _needs_leading_newline

SCHEMA = 1

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
    "speaker_id", "recipient_id", "reply", "reaction_text", "reaction_type",
    "parent_event_id",
)


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
        return STRONG if _same_person(event) else NEGATIVE_ONLY
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
        "lang": _text(lang, 16),
        "platform": _text(platform, 32),
        "conv_id": _text(conv_id, 128),
        "persona": _text(persona, 64),
        "persona_hash": _text(persona_hash, 64),
        "persona_version": _text(persona_version, 32),
        "speaker_id": _text(speaker_id, 64),
        "speaker_name": _text(speaker_name, 64),
        "recipient_id": _text(recipient_id, 64),
        "reply": _text(reply),
        "context": _context(context),
        "reaction_text": _text(reaction_text),
        "directed": bool(directed),
        "direction": _text(direction, 16),
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
        if kind == KIND_SELF_EVAL:
            return True
        return event.get("reaction_type") == "positive"
    return False


def opposes(event: dict, candidate_type: str) -> bool:
    """True when this event argues *against* a candidate of that type."""
    if not (event.get("adjudication") or {}).get("accept"):
        return False
    if candidate_type == "preference_pair":
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

    # -- reads -------------------------------------------------------------
    def _load(self) -> list[dict]:
        if self._events is None:
            events: list[dict] = []
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()
            except (FileNotFoundError, OSError):
                lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict) and rec.get("event_id"):
                    events.append(rec)
            self._events = events
            self._ids = {e["event_id"] for e in events}
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
        self._load()
        if eid in self._ids:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            # A hand-inspected log can lose its final newline; appending onto an
            # unterminated line would destroy both records.
            if _needs_leading_newline(self.path):
                fh.write("\n")
            fh.write(line)
        self._events.append(event)
        self._ids.add(eid)
        return True

    def reload(self) -> None:
        """Drop the in-memory cache; the next read re-reads the file."""
        self._events = None
        self._ids = set()
