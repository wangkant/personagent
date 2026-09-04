"""Versioned behaviour candidates and the append-only ledger that owns them.

A candidate is a *proposal*: "replace this reply with that one", "this reply is
worth imitating". Adjudicating evidence (evidence.py) mints candidates; nothing
else may. A candidate on its own changes nothing — it sits in ``proposed``
until something grants it authority.

Authority is a lifecycle event, not a field:

    proposed --promote--> promoted --rollback--> rolled_back
        |                     |
        |                     +--supersede--> superseded  (replacement promoted)
        +--reject---------> rejected

Every transition is appended to the ledger; no earlier row is ever edited or
deleted, so "why is the agent talking like this" always has an answer, and so
does "why did it stop". The current state of the world is a *projection* — a
replay of the log from the beginning — which is why a restart cannot disagree
with the process that wrote it.

Retrieval never reads this ledger directly. Promoted-and-active candidates are
materialized into small view files (``rebuild_views``) that the agent loads on
the hot path; the view is a cache and may be rewritten atomically at any time,
because it can always be rebuilt from the log.

Pure logic — no clock reads, no LLM. Callers pass timestamps.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .evidence import persona_identity
from .storage import (
    append_jsonl_unlocked,
    append_lock,
    append_only_health,
    atomic_write_text,
    file_stamp,
    read_validated_jsonl,
    warning_bytes as _warning_bytes,
)

SCHEMA = 2

TYPE_PAIR = "preference_pair"
TYPE_EXAMPLE = "positive_example"
TYPES = (TYPE_PAIR, TYPE_EXAMPLE)

STATE_PROPOSED = "proposed"
STATE_PROMOTED = "promoted"
STATE_REJECTED = "rejected"
STATE_SUPERSEDED = "superseded"
STATE_ROLLED_BACK = "rolled_back"
STATES = (STATE_PROPOSED, STATE_PROMOTED, STATE_REJECTED,
          STATE_SUPERSEDED, STATE_ROLLED_BACK)

# Ledger row kinds.
ROW_CANDIDATE = "candidate"
ROW_LIFECYCLE = "lifecycle"
ROW_EVIDENCE = "evidence_link"
ROW_SUPERSESSION = "supersession"

_SUPPORTED_SCHEMAS = (1, SCHEMA)
_WARN_BYTES_ENV = "AGENT_CANDIDATE_LEDGER_WARN_BYTES"

# Which states a transition may be written from. The ledger replays whatever it
# contains — this is a write-time guard, so a mistaken admin command is refused
# instead of becoming permanent history.
_ALLOWED_FROM = {
    STATE_PROMOTED: (STATE_PROPOSED, STATE_ROLLED_BACK),
    STATE_REJECTED: (STATE_PROPOSED, STATE_PROMOTED, STATE_ROLLED_BACK),
    STATE_ROLLED_BACK: (STATE_PROMOTED,),
    STATE_SUPERSEDED: (STATE_PROPOSED, STATE_PROMOTED),
}

# Identity fields: what makes two proposals the same proposal. Scenario labels
# and modes are deliberately excluded — the adjudicator writes a free-text
# scene label per call, and letting it split identity would strand each event
# on its own candidate where none ever reaches the corroboration threshold.
_ID_FIELDS = ("type", "lang", "platform", "persona", "persona_hash",
              "persona_version", "conv_id", "reply", "better")


def scope_from_event(event: dict) -> dict:
    """The compatibility scope of an event: who, where, in what language."""
    adj = event.get("adjudication") or {}
    return {
        "lang": str(event.get("lang") or ""),
        "platform": str(event.get("platform") or ""),
        "conv_id": str(event.get("conv_id") or ""),
        "persona": str(event.get("persona") or ""),
        "persona_hash": str(event.get("persona_hash") or ""),
        "persona_version": str(event.get("persona_version") or ""),
        "scenario": str(adj.get("scenario") or ""),
        "mode": str(adj.get("mode") or ""),
    }


def candidate_id(ctype: str, scope: dict, reply: str, better: str = "") -> str:
    payload = {
        "type": ctype,
        "lang": scope.get("lang", ""),
        "platform": scope.get("platform", ""),
        "persona": scope.get("persona", ""),
        # Lineage root, so a corroboration arriving after a persona edit
        # lands on the same candidate instead of minting a twin.
        "persona_hash": persona_identity(scope),
        "persona_version": scope.get("persona_version", ""),
        "conv_id": scope.get("conv_id", ""),
        "reply": (reply or "").strip(),
        "better": (better or "").strip(),
    }
    blob = json.dumps({k: payload[k] for k in _ID_FIELDS}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def make_candidate(*, ctype: str, scope: dict, payload: dict,
                   evidence=(), created_at: str = "",
                   adjudication_version: str = "") -> dict:
    """Build a candidate record from a retrieval-shaped payload.

    ``payload`` is the row the pools already understand — what
    ``reactions.to_feedback_pair`` / ``reactions.to_example`` produce. Storing
    it verbatim means a promoted candidate materializes into exactly the row
    shape retrieval has always read, with no second format to keep in sync.
    """
    reply = str(payload.get("reply") or "").strip()
    better = str(payload.get("better") or "").strip()
    return {
        "schema": SCHEMA,
        "kind": ROW_CANDIDATE,
        "candidate_id": candidate_id(ctype, scope, reply, better),
        "type": ctype,
        "scope": dict(scope),
        "reply": reply,
        "better": better,
        "payload": dict(payload),
        "evidence": [str(e) for e in (evidence or ())],
        "created_at": created_at,
        "adjudication_version": adjudication_version,
        "state": STATE_PROPOSED,
    }


def view_row(cand: dict) -> dict:
    """The retrieval row a promoted candidate contributes."""
    row = dict(cand.get("payload") or {})
    row["candidate_id"] = cand.get("candidate_id", "")
    row["scope"] = dict(cand.get("scope") or {})
    if not row.get("src"):
        row["src"] = "promoted_candidate"
    return row


def _validate_row(row: dict) -> str | None:
    schema = row.get("schema")
    if not isinstance(schema, int) or schema not in _SUPPORTED_SCHEMAS:
        return "unsupported schema"
    cid = row.get("candidate_id")
    if not isinstance(cid, str) or not cid:
        return "candidate_id must be a non-empty string"
    kind = row.get("kind")
    if kind == ROW_CANDIDATE:
        if row.get("type") not in TYPES:
            return "unknown candidate type"
        if not isinstance(row.get("scope"), dict):
            return "scope must be an object"
        if not isinstance(row.get("payload"), dict):
            return "payload must be an object"
        if not isinstance(row.get("evidence"), list):
            return "evidence must be a list"
        if not isinstance(row.get("reply"), str):
            return "reply must be a string"
        if not isinstance(row.get("better"), str):
            return "better must be a string"
        return None
    if kind == ROW_LIFECYCLE:
        if row.get("state") not in _ALLOWED_FROM:
            return "unknown lifecycle state"
        if not isinstance(row.get("evidence"), list):
            return "evidence must be a list"
        return None
    if kind == ROW_EVIDENCE:
        if not isinstance(row.get("evidence"), list):
            return "evidence must be a list"
        return None
    if kind == ROW_SUPERSESSION:
        if schema != SCHEMA:
            return "supersession requires current schema"
        replacement = row.get("replacement_id")
        if not isinstance(replacement, str) or not replacement:
            return "replacement_id must be a non-empty string"
        return None
    return "unknown ledger row kind"


class CandidateLedger:
    """Append-only candidate + lifecycle log, projected into current state."""

    def __init__(self, path):
        self.path = Path(path)
        self._by_id: dict[str, dict] | None = None
        self._stamp: tuple[int, int] = (-1, -1)
        self._quarantined = []

    # -- projection --------------------------------------------------------
    def _rows(self) -> list[dict]:
        result = read_validated_jsonl(self.path, _validate_row)
        self._quarantined = result.quarantined
        self._stamp = file_stamp(self.path)
        return result.rows

    def _project(self) -> dict[str, dict]:
        """Replay the log into current candidate state.

        Deterministic and order-only: the same file always yields the same
        projection, which is what makes "restart and replay produce identical
        state" a property of the design rather than a hope.
        """
        if self._by_id is not None and self._stamp == file_stamp(self.path):
            return self._by_id
        out: dict[str, dict] = {}
        for row in self._rows():
            self._apply_row(out, row)
        self._by_id = out
        return out

    def _apply_row(self, out: dict[str, dict], row: dict) -> None:
        """Fold one log row into a projection.

        Split out of `_project` so the replay reads as what it is — one pass
        applying rows in order — and so the meaning of each row kind is stated
        once, in one place, next to the mutations the write methods make to
        the live projection. Those two have to agree: `_append` lets the live
        projection stand rather than replaying for its own write, which is
        only sound while every write method leaves `self._by_id` exactly as a
        cold replay of the same file would. `test_ledger.py` asserts that by
        diffing the two.
        """
        cid = row["candidate_id"]
        kind = row.get("kind")
        if kind == ROW_CANDIDATE:
            if cid in out:
                # A re-proposal of an existing candidate adds evidence, it
                # does not reset the lifecycle.
                self._merge_evidence(out[cid], row.get("evidence"))
                return
            cand = dict(row)
            cand["evidence"] = [str(e) for e in (row.get("evidence") or [])]
            cand["state"] = STATE_PROPOSED
            cand["history"] = []
            out[cid] = cand
            return
        if kind == ROW_SUPERSESSION:
            replacement_id = str(row.get("replacement_id") or "")
            old, new = out.get(cid), out.get(replacement_id)
            # A compound row is all-or-nothing on replay. If either
            # candidate definition is absent/corrupt, apply neither half.
            if old is None or new is None or cid == replacement_id:
                return
            old["state"] = STATE_SUPERSEDED
            old["superseded_by"] = replacement_id
            old.setdefault("history", []).append({
                "state": STATE_SUPERSEDED, "ts": row.get("ts", ""),
                "actor": row.get("actor", ""), "reason": row.get("reason", ""),
            })
            new["state"] = STATE_PROMOTED
            new["supersedes"] = cid
            new.setdefault("history", []).append({
                "state": STATE_PROMOTED, "ts": row.get("ts", ""),
                "actor": row.get("actor", ""), "reason": row.get("reason", ""),
            })
            return
        cand = out.get(cid)
        if cand is None:
            # Lifecycle row for an unknown candidate: keep the history
            # rather than drop it, so a hand-repaired log stays inspectable.
            cand = {"candidate_id": cid, "type": "", "scope": {},
                    "payload": {}, "evidence": [], "state": STATE_PROPOSED,
                    "history": [], "orphan": True}
            out[cid] = cand
        if kind == ROW_EVIDENCE:
            self._merge_evidence(cand, row.get("evidence"))
            return
        if kind == ROW_LIFECYCLE:
            state = row.get("state")
            if state in STATES:
                cand["state"] = state
            self._merge_evidence(cand, row.get("evidence"))
            if row.get("superseded_by"):
                cand["superseded_by"] = row["superseded_by"]
            if row.get("supersedes"):
                cand["supersedes"] = row["supersedes"]
            cand["history"].append({
                "state": row.get("state", ""), "ts": row.get("ts", ""),
                "actor": row.get("actor", ""), "reason": row.get("reason", ""),
            })

    @staticmethod
    def _merge_evidence(cand: dict, ids) -> None:
        known = cand.setdefault("evidence", [])
        seen = set(known)
        for eid in ids or ():
            eid = str(eid)
            if eid and eid not in seen:
                known.append(eid)
                seen.add(eid)

    # -- queries -----------------------------------------------------------
    def all(self) -> list[dict]:
        return list(self._project().values())

    def get(self, cid: str) -> dict | None:
        return self._project().get(cid)

    def by_state(self, state: str) -> list[dict]:
        return [c for c in self._project().values() if c.get("state") == state]

    def pending(self) -> list[dict]:
        return self.by_state(STATE_PROPOSED)

    def active(self) -> list[dict]:
        """Promoted and not since rolled back or superseded — the only
        candidates allowed to influence retrieval."""
        return self.by_state(STATE_PROMOTED)

    def history(self, cid: str) -> list[dict]:
        cand = self.get(cid)
        return list(cand.get("history") or []) if cand else []

    # -- writes ------------------------------------------------------------
    def _append(self, row: dict) -> None:
        reason = _validate_row(row)
        if reason:
            raise ValueError(f"invalid candidate ledger row: {reason}")
        with append_lock(self.path):
            # Callers have already applied the row to `_by_id` (do not
            # `_apply_row` here: it would land twice). Only advance the stamp
            # when nobody else wrote since our projection — decided under the
            # same lock as the append, or a foreign row could be hidden.
            current = (self._by_id is not None
                       and self._stamp == file_stamp(self.path))
            append_jsonl_unlocked(self.path, row)
            if current:
                self._stamp = file_stamp(self.path)

    def health_metadata(self, *, warning_bytes: int | None = None) -> dict:
        # Force validation even when no caller has projected the ledger yet.
        self._project()
        return append_only_health(
            self.path,
            warning_bytes=_warning_bytes(_WARN_BYTES_ENV, warning_bytes),
            quarantined_rows=len(self._quarantined),
        )

    def propose(self, cand: dict) -> tuple[dict, bool]:
        """Record a candidate. Returns ``(projected, created)``.

        Idempotent: proposing an existing candidate again only links whatever
        new evidence came with it, so a repeated reaction cannot resurrect a
        rejected proposal or restart a promoted one.
        """
        cid = cand["candidate_id"]
        if self.get(cid) is not None:
            self.link_evidence(cid, cand.get("evidence") or [],
                               ts=cand.get("created_at", ""))
            return self.get(cid), False
        self._append(cand)
        projected = dict(cand)
        projected["state"] = STATE_PROPOSED
        projected["history"] = []
        projected["evidence"] = list(cand.get("evidence") or [])
        self._project()[cid] = projected
        return projected, True

    def link_evidence(self, cid: str, event_ids, ts: str = "",
                      note: str = "") -> list[str]:
        """Attach further evidence to an existing candidate. Returns the ids
        that were actually new."""
        cand = self.get(cid)
        if cand is None:
            return []
        known = set(cand.get("evidence") or [])
        fresh = [str(e) for e in (event_ids or []) if str(e) and str(e) not in known]
        if not fresh:
            return []
        self._append({"schema": SCHEMA, "kind": ROW_EVIDENCE,
                      "candidate_id": cid, "ts": ts, "evidence": fresh,
                      "note": note})
        self._merge_evidence(cand, fresh)
        return fresh

    def transition(self, cid: str, state: str, *, ts: str, actor: str,
                   reason: str = "", evidence=()) -> bool:
        """Append one lifecycle event. False when the transition is not legal
        from the candidate's current state (nothing is written).

        It used to take `supersedes` / `superseded_by` as well, and no caller
        ever passed either: supersession is written as its own
        `ROW_SUPERSESSION` row by `supersede()`. `_apply_row` still READS both
        fields off a lifecycle row, and that half stays — it is how a
        schema-1 log written by an older build still projects, and
        `tools/candidates_admin.py` prints them."""
        cand = self.get(cid)
        if cand is None or state not in _ALLOWED_FROM:
            return False
        if cand.get("state") not in _ALLOWED_FROM[state]:
            return False
        row = {"schema": SCHEMA, "kind": ROW_LIFECYCLE, "candidate_id": cid,
               "state": state, "ts": ts, "actor": actor,
               "reason": str(reason or "")[:300],
               "evidence": [str(e) for e in (evidence or ())]}
        self._append(row)
        cand["state"] = state
        self._merge_evidence(cand, row["evidence"])
        cand.setdefault("history", []).append(
            {"state": state, "ts": ts, "actor": actor, "reason": row["reason"]})
        return True

    def promote(self, cid: str, *, ts: str, actor: str, reason: str = "",
                evidence=()) -> bool:
        return self.transition(cid, STATE_PROMOTED, ts=ts, actor=actor,
                               reason=reason, evidence=evidence)

    def reject(self, cid: str, *, ts: str, actor: str, reason: str = "") -> bool:
        return self.transition(cid, STATE_REJECTED, ts=ts, actor=actor,
                               reason=reason)

    def rollback(self, cid: str, *, ts: str, actor: str, reason: str = "",
                 evidence=()) -> bool:
        """Revoke a promoted candidate's authority. History is untouched."""
        return self.transition(cid, STATE_ROLLED_BACK, ts=ts, actor=actor,
                               reason=reason, evidence=evidence)

    def supersede(self, old_cid: str, new_cid: str, *, ts: str, actor: str,
                  reason: str = "") -> bool:
        """Deactivate `old_cid` and activate `new_cid`, keeping both records.

        Either half failing leaves nothing written: a half-applied supersession
        would either drop both replies out of retrieval or leave two
        contradictory ones in it.
        """
        old, new = self.get(old_cid), self.get(new_cid)
        if old is None or new is None or old_cid == new_cid:
            return False
        if old.get("state") not in _ALLOWED_FROM[STATE_SUPERSEDED]:
            return False
        if new.get("state") not in _ALLOWED_FROM[STATE_PROMOTED]:
            return False
        row = {
            "schema": SCHEMA,
            "kind": ROW_SUPERSESSION,
            "candidate_id": old_cid,
            "replacement_id": new_cid,
            "ts": ts,
            "actor": actor,
            "reason": str(reason or f"supersedes {old_cid}")[:300],
        }
        self._append(row)
        old["state"] = STATE_SUPERSEDED
        old["superseded_by"] = new_cid
        old.setdefault("history", []).append({
            "state": STATE_SUPERSEDED, "ts": ts, "actor": actor,
            "reason": row["reason"],
        })
        new["state"] = STATE_PROMOTED
        new["supersedes"] = old_cid
        new.setdefault("history", []).append({
            "state": STATE_PROMOTED, "ts": ts, "actor": actor,
            "reason": row["reason"],
        })
        return True


def view_rows(ledger: CandidateLedger) -> tuple[list[dict], list[dict]]:
    """(example rows, preference-pair rows) for every active candidate."""
    examples, pairs = [], []
    for cand in sorted(ledger.active(), key=lambda c: str(c.get("created_at") or "")):
        row = view_row(cand)
        if cand.get("type") == TYPE_PAIR:
            pairs.append(row)
        elif cand.get("type") == TYPE_EXAMPLE:
            examples.append(row)
    return examples, pairs


def _write_view(path: Path, rows: list[dict]) -> int:
    """Rewrite a materialized view atomically.

    Rewriting (rather than appending) is safe precisely because this file is
    derived: the ledger is the source of truth and this is a cache of its
    current projection.
    """
    text = "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    atomic_write_text(path, text)
    return len(rows)


def rebuild_views(ledger: CandidateLedger, examples_view: Path,
                  feedback_view: Path, *, max_examples: int = 0,
                  max_pairs: int = 0) -> tuple[int, int]:
    """Rebuild both retrieval views from the ledger. Returns (examples, pairs).

    The caps keep the newest N rows per view (0 = unbounded) — the same
    EXAMPLES_MAX_AUTO / FEEDBACK_MAX_AUTO limits the learned pools carry, for
    the same reason: only a handful of rows reach a prompt per turn, and
    material promoted under an older persona should not outvote recent material.

    Dropping a row from a view is not a lifecycle change. The candidate stays
    promoted in the ledger and returns to the view if newer rows are rolled
    back — the cap is about how much retrieval scans, not about authority.
    """
    examples, pairs = view_rows(ledger)
    if max_examples > 0:
        examples = examples[-max_examples:]
    if max_pairs > 0:
        pairs = pairs[-max_pairs:]
    return (_write_view(Path(examples_view), examples),
            _write_view(Path(feedback_view), pairs))
