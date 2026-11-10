"""The Activity API: is it running, why did it speak, what has it learned.

The local page's Activity view (persona_agent/welcome.py) reads
``/api/dashboard/...`` server to server. The character decides what it learns
by itself; each item says where it stands and who decided it. Everything is
read-only except a person's optional promote, reject, roll back and restore,
which go through the candidate ledger the way ``personagent learned`` does,
rebuild the retrieval views, and record the actor ``dashboard``; and the
forget and restore of what a chat remembers, which ``personagent memory``
also calls while the service runs.

Every request needs the header ``X-Personagent-Dashboard-Token`` with the
secret in ``<runtime>/dashboard.token``, which the service creates when it
starts. A state-changing call is a POST that also carries
``X-Personagent-Dashboard: 1``, ``Content-Type: application/json`` and, when
an Origin is sent, the service's own origin. ``GET /`` only says where the
Activity view is.
"""
from __future__ import annotations

import functools
import json
import logging
import os
import re
import secrets
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from . import (access, candidates, channels, decision_log, embeddings, evidence,
               langs, learning as learning_rules, lineage, memstate, promotion)
from .config_env import env_bool, env_float, env_int
from .paths import ROOT, resolve_runtime_lang_file, runtime_dir
from .settings import content_lang
from .storage import atomic_write_text

logger = logging.getLogger("bot")

WRITE_HEADER = "x-personagent-dashboard"
TOKEN_HEADER = "x-personagent-dashboard-token"
TOKEN_FILE = "dashboard.token"
ACTOR = "dashboard"
_MAX_BODY = 4096
# Newest first; the list of chats carries the full counts.
LIST_LIMIT = 50

_DATA_CSP = "default-src 'none'; frame-ancestors 'none'"

# Every setting with one of these endings holds a credential (LLM_API_KEY,
# CONNECTOR_TOKEN, QQ_ONEBOT_SECRET, ...): its value never leaves the process.
_SECRET_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "PASSWORD")

_ACTIONS = {"promote": candidates.STATE_PROMOTED,
            "reject": candidates.STATE_REJECTED,
            "rollback": candidates.STATE_ROLLED_BACK}
# "replace" promotes in place of the rewrite of the same reply that is in use;
# "restore" brings back what the character set aside (candidates.restorable).
_VERBS = (*_ACTIONS, "replace", "restore")

# Who made a decision, as the page names it, read from the ledger's own reasons.
_EXPIRED = re.compile(re.escape(learning_rules.REASON_EXPIRED)
                      .replace(re.escape("{days}"), r"(\d+(?:\.\d+)?)"))
_RULES = {learning_rules.REASON_POLICY: "policy", learning_rules.REASON_LESSON: "lesson",
          learning_rules.REASON_BLOCKED: "blocked", learning_rules.REASON_CONFIRMED: "confirmed"}
_AUTOMATIC = frozenset({candidates.ACTOR_AUTO, candidates.ACTOR_CHARACTER})
# What the Activity view's one sentence per observed item needs.
STANDING_SENT = ("stage", "missing", "reason", "expires", "events", "needEvents",
                 "strong", "needStrong", "speakers", "needSpeakers")

router = APIRouter()
_token = ""


def install(app: FastAPI, *, enabled: bool | None = None) -> bool:
    """Add the dashboard's routes to `app` unless DASHBOARD_ENABLED is off."""
    if enabled is None:
        enabled = env_bool("DASHBOARD_ENABLED", True)
    if enabled:
        app.include_router(router)
    # Newer FastAPI nests included routers, so app.routes cannot answer this.
    app.state.dashboard = bool(enabled)
    return bool(enabled)


def _server():
    # Imported late: server.py includes this router while it is being built.
    from . import server
    return server


# ---------------------------------------------------------------- access ----

def _harden(response: Response) -> Response:
    headers = response.headers
    headers["Content-Security-Policy"] = _DATA_CSP
    headers["X-Content-Type-Options"] = "nosniff"
    headers["Referrer-Policy"] = "no-referrer"
    headers["X-Frame-Options"] = "DENY"
    headers["Cross-Origin-Resource-Policy"] = "same-origin"
    headers["Cross-Origin-Opener-Policy"] = "same-origin"
    headers["Cache-Control"] = "no-store"
    return response


def _refused(status: int, code: str, message: str) -> Response:
    return _harden(_server()._error(status, code, message))


def token_path() -> Path:
    return runtime_dir() / TOKEN_FILE


def _usable(text: str) -> bool:
    return 32 <= len(text) <= 256 and all(
        c.isascii() and (c.isalnum() or c in "-_") for c in text)


def _write_token(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | getattr(os, "O_BINARY", 0), 0o600)
    except FileExistsError:
        atomic_write_text(path, text + "\n")  # present but unusable
        return
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text + "\n")


def load_token(*, create: bool = False) -> str:
    """The dashboard's secret; '' while none exists and `create` is off."""
    global _token
    if _token:
        return _token
    try:
        path = token_path()
        text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError, ValueError):
        text = ""
    if not _usable(text):
        if not create:
            return ""
        try:
            _write_token(path, secrets.token_urlsafe(32))
            text = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.warning("[dashboard] cannot create its token file: %s", exc)
            return ""
    _token = text
    return text


@functools.lru_cache(maxsize=None)
def _cli() -> str:
    """How this install spells `personagent`, for the commands it names."""
    from .setup_wizard import Launcher
    return Launcher(python=sys.executable, home=ROOT).shown("")[-1].strip()


def _same_origin(origin: str, request: Request) -> bool:
    parts = urlsplit(origin.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return False
    # A reverse proxy may rewrite Host; the caller still names the public one.
    hosts = {request.headers.get(name, "").strip().lower()
             for name in ("host", "x-forwarded-host")}
    return parts.netloc.lower() in hosts - {""}


def _problem(request: Request, *, write: bool = False) -> tuple[int, str, str] | None:
    """(status, code, message) for a request the dashboard must not answer."""
    expected = load_token()
    supplied = request.headers.get(TOKEN_HEADER)
    if supplied is None:
        return 401, "dashboard_token", "send X-Personagent-Dashboard-Token"
    if not expected or not _server()._ct_equal(supplied, expected):
        return 403, "wrong_token", "wrong dashboard token"
    site = request.headers.get("sec-fetch-site", "").strip().lower()
    if site in ("cross-site", "same-site"):
        return 403, "cross_site", "cross-site request refused"
    if write:
        if request.headers.get(WRITE_HEADER, "").strip() != "1":
            return (403, "missing_header",
                    "state-changing calls need X-Personagent-Dashboard: 1")
        origin = request.headers.get("origin")
        if origin is not None and not _same_origin(origin, request):
            return 403, "foreign_origin", "cross-origin request refused"
        ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return 415, "unsupported_media_type", "send application/json"
    return None


def _check(request: Request, *, write: bool = False) -> Response | None:
    """The refusal for a request the dashboard must not answer, else None."""
    problem = _problem(request, write=write)
    return None if problem is None else _refused(*problem)


# --------------------------------------------------------------- secrets ----

def _secret_values(agent) -> list[str]:
    values: set[str] = set()
    for name, value in os.environ.items():
        upper = name.upper()
        if upper.endswith(_SECRET_SUFFIXES):
            values.add(str(value or "").strip())
    srv = _server()
    values.update((srv.CONNECTOR_TOKEN, srv.QQ_ONEBOT_SECRET, _token))
    if agent is not None:
        for attr in ("api_key", "llm_fallback_api_key", "vision_api_key",
                     "embedding_api_key", "tavily_key"):
            values.add(str(getattr(agent, attr, "") or "").strip())
    # Short values would mask ordinary words; real keys are long.
    return sorted((v for v in values if len(v) >= 8), key=len, reverse=True)


def _scrub(obj, secrets: list[str]):
    if isinstance(obj, str):
        for secret in secrets:
            if secret in obj:
                obj = obj.replace(secret, "***")
        return obj
    if isinstance(obj, dict):
        return {k: _scrub(v, secrets) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_scrub(v, secrets) for v in obj]
    return obj


def _json(payload, agent, status: int = 200) -> Response:
    return _harden(JSONResponse(_scrub(payload, _secret_values(agent)),
                                status_code=status))


# ---------------------------------------------------------------- helpers ---

def _clip(text, limit: int = 300) -> str:
    value = " ".join(str(text or "").split())
    return value if len(value) <= limit else value[:limit - 1] + "…"


def _epoch(ts) -> float:
    if isinstance(ts, (int, float)):
        return float(ts)
    return promotion.epoch(ts)


def _lang(agent) -> str:
    if agent is not None:
        return str(agent.agent_lang or "en")
    return content_lang(os.getenv("AGENT_LANG", "en"))


def _routing_key(learning_key: str) -> str:
    """The inverse of channels.learning_key."""
    if learning_key.startswith(channels.DM_LEARNING_PREFIX):
        return channels.DM_ROUTING_PREFIX + learning_key[len(channels.DM_LEARNING_PREFIX):]
    return learning_key


class _Learning:
    """The ledger, evidence log and policy the running agent uses, or the
    files `personagent learned` would open when no agent is running."""

    def __init__(self, agent) -> None:
        self.agent = agent
        self.lang = _lang(agent)
        if agent is not None:
            self.ledger = agent.candidate_ledger
            self.log = agent.evidence_log
            self.policy = agent.promotion_policy
            lineage_file = agent.learning_dir / lineage.FILE_NAME
        else:
            self.ledger = candidates.CandidateLedger(
                resolve_runtime_lang_file("candidate_ledger", "jsonl", self.lang))
            self.log = evidence.EvidenceLog(
                resolve_runtime_lang_file("evidence", "jsonl", self.lang))
            self.policy = promotion.Policy.from_env()
            lineage_file = Path(self.log.path).parent / lineage.FILE_NAME
        # Read, never extended: scope comparisons need every known revision.
        self.lineage = lineage.PersonaLineage(lineage_file)
        for version, hashes in self.lineage.versions().items():
            evidence.register_persona_lineage(version, hashes)

    def judge(self) -> "Judge":
        if self.agent is not None:
            return Judge(self.agent._judging_on(),
                         float(self.agent.promote_observe_max_days or 0), self.agent._admins())
        return Judge.from_env(None, self.policy, access.page_owner(runtime_dir()))

    def rebuild(self) -> bool:
        if self.agent is not None:
            return self.agent._rebuild_promoted_views() != (-1, -1)
        try:
            candidates.rebuild_views(
                self.ledger,
                resolve_runtime_lang_file("promoted.examples", "jsonl", self.lang),
                resolve_runtime_lang_file("promoted.feedback", "jsonl", self.lang),
                max_examples=env_int("PROMOTE_MAX_EXAMPLES", 500, minimum=0),
                max_pairs=env_int("PROMOTE_MAX_FEEDBACK", 500, minimum=0))
        except OSError:
            return False
        return True


# ---------------------------------------------------------------- standing --

class Judge:
    """What the running character's own decisions depend on: its switch
    (learning._judging_on), the observation limit and the admins."""

    def __init__(self, judging: bool, observe_days: float, admins) -> None:
        self.judging = bool(judging)
        self.observe_days = max(0.0, float(observe_days or 0))
        self.admins = frozenset(admins or ())

    @classmethod
    def from_env(cls, env, policy, page_owners=()) -> "Judge":
        """As settings.py and turns._admins read them, for the files alone."""
        judging = env_bool("PROMOTE_JUDGE_ENABLED", True, env=env) and policy.auto_promote
        days = env_float("PROMOTE_OBSERVE_MAX_DAYS", 30.0, minimum=0.0, env=env)
        admins = access.identity_from_env(env).admins | frozenset(page_owners)
        return cls(judging, days, admins)


def decided_by(entry: dict | None) -> dict:
    """Who made one history step and why: the reactions, the character, a
    rule, the time limit or a person."""
    entry = entry or {}
    actor, reason = str(entry.get("actor") or ""), str(entry.get("reason") or "")
    expired = _EXPIRED.fullmatch(reason)
    expiry = getattr(candidates, "JUDGE_EXPIRY", None)
    if actor in _AUTOMATIC and (expired or (expiry and entry.get("judge") == expiry)):
        return {"by": "time", "why": "", "days": expired.group(1) if expired else ""}
    if reason in _RULES and actor in _AUTOMATIC:
        return {"by": "rule", "why": _RULES[reason]}
    if actor == candidates.ACTOR_CHARACTER:
        return {"by": "character", "why": _clip(reason, 200)}
    if actor == candidates.ACTOR_AUTO:
        return {"by": "reactions", "why": ""}
    return {"by": "person", "why": ""}


def _admin_ids(admins) -> set[str]:
    return {evidence._text(a, 64) for a in admins} - {""}


def standing(cand: dict, index: promotion.EvidenceIndex, policy, judge: Judge,
             now: float | None = None) -> dict:
    """Where an item under observation stands, from the policy's own decision
    and the character's latest look; nothing here waits for a person."""
    now = time.time() if now is None else now
    linked, related = index.linked(cand), index.related(cand)
    decision = promotion.decide(cand, linked_events=linked, related_events=related,
                                peers=index.peers(cand), now=now, policy=policy,
                                admin_ids=judge.admins)
    max_age = policy.max_evidence_age_days * 86400.0
    counting = [e for e in linked if promotion.supports_candidate(e, cand, policy=policy)]
    fresh = [e for e in counting
             if not (max_age > 0 and now - promotion.epoch(e.get("ts")) > max_age)]
    speakers = {str(e.get("speaker_id") or "") for e in fresh} - {""}
    speakers_ok = (not speakers or bool(_admin_ids(judge.admins) & speakers)
                   or len(speakers) >= policy.min_speakers)
    can_be_strong = evidence.can_be_strong(str(cand.get("type") or ""))
    out = {"stage": "", "missing": "", "reason": "", "since": 0.0, "expires": 0.0,
           "events": decision.supporting, "needEvents": policy.min_events,
           "strong": decision.strong, "needStrong": policy.min_strong,
           "canBeStrong": can_be_strong, "speakers": len(speakers),
           "needSpeakers": policy.min_speakers, "speakersOk": speakers_ok,
           "stale": len(counting) - len(fresh), "maxAgeDays": policy.max_evidence_age_days}
    if decision.gate == promotion.GATE_OFF:
        out["stage"] = "off"
        return out
    if promotion.needs_character(decision, cand):
        if not judge.judging:
            out["stage"] = "held"
        else:
            group = promotion.conflict_group(cand, index.peers(cand), policy=policy,
                                             related_events=related)
            seen = sorted({str(e.get("event_id") or "") for e in linked + related} - {""})
            peers = sorted(str(c.get("candidate_id") or "") for c in group[1:])
            review = cand.get("review") or {}
            # The character looks again whenever the evidence or the rivals change.
            if (review and sorted(review.get("seen") or []) == seen
                    and sorted(review.get("peers") or []) == peers):
                out.update(stage="observing", reason=_clip(review.get("reason"), 300),
                           since=_epoch(review.get("ts")))
            else:
                out["stage"] = "deciding"
    elif decision.gate == promotion.GATE_OK:
        out["stage"] = "ready"
    else:
        out["stage"] = "reactions"
        if decision.gate in (promotion.GATE_EVENTS, promotion.GATE_STRONG,
                             promotion.GATE_SPEAKERS):
            out["missing"] = decision.gate
        elif decision.supporting < policy.min_events:
            out["missing"] = promotion.GATE_EVENTS
        elif can_be_strong and decision.strong < policy.min_strong:
            out["missing"] = promotion.GATE_STRONG
        elif (cand.get("type") == candidates.TYPE_EXAMPLE
              and decision.person_support < 1):
            out["missing"] = "approval"
        else:
            out["missing"] = promotion.GATE_SPEAKERS
    # As learning._expire_observing: the newest reaction, or the item itself.
    if judge.judging and judge.observe_days > 0:
        stamps = [promotion.epoch(e.get("ts")) for e in linked + related]
        stamps.append(promotion.epoch(cand.get("created_at")))
        newest = max(stamps)
        if newest:
            out["expires"] = newest + judge.observe_days * 86400.0
    return out


def in_use_by(cand: dict) -> dict:
    """How an item in use came into use: its latest step into use."""
    for entry in reversed(cand.get("history") or []):
        if entry.get("state") == candidates.STATE_PROMOTED:
            return decided_by(entry)
    return {"by": "", "why": ""}


# ---------------------------------------------------------- conversations ---

def _conversation_keys(agent, ledger_rows: list[dict]) -> dict[str, float]:
    """Every conversation the agent knows of -> its last activity (epoch)."""
    seen: dict[str, float] = {}

    def touch(key, ts=0.0) -> None:
        key = str(key or "")
        if key:
            seen[key] = max(seen.get(key, 0.0), float(ts or 0.0))

    for cand in ledger_rows:
        conv = str((cand.get("scope") or {}).get("conv_id") or "")
        if conv:
            touch(_routing_key(conv), _epoch(cand.get("created_at")))
    for key, ts in decision_log.LOG.last_seen().items():
        touch(key, ts)
    if agent is not None:
        for key, items in agent.memories.items():
            touch(key, max((_epoch(i.get("time")) for i in items), default=0.0))
        for key in agent.core_memory:
            touch(key)
        for key in agent.episode_store.convs():
            touch(key, max((_epoch(e.get("t1")) for e in agent.episode_store.episodes(key)),
                           default=0.0))
        for key, ts in list(agent.last_activity_at.items()):
            touch(key, ts)
        for uid, ts in list(agent.last_dm_activity_at.items()):
            touch(channels.dm_routing_key(uid), ts)
        store = agent.connector_handles
        for key in store.keys():
            touch(key, (store.get(key) or {}).get("updated_at", 0.0))
    return seen


def conversations_payload(agent) -> dict:
    learning = _Learning(agent)
    rows = learning.ledger.all()
    by_conv: dict[str, dict[str, int]] = {}
    for cand in rows:
        conv = _routing_key(str((cand.get("scope") or {}).get("conv_id") or ""))
        counts = by_conv.setdefault(conv, {"learned": 0, "observing": 0, "latest": 0.0})
        if cand.get("state") == candidates.STATE_PROMOTED:
            counts["learned"] += 1
            # When something last came into use here: the page's "new" mark.
            steps = [_epoch(h.get("ts")) for h in cand.get("history") or []
                     if h.get("state") == candidates.STATE_PROMOTED]
            counts["latest"] = max([counts["latest"], *steps])
        elif cand.get("state") == candidates.STATE_PROPOSED:
            counts["observing"] += 1
    out = []
    page = {channels.dm_routing_key(owner) for owner in access.page_owner(runtime_dir())}
    for key, last in _conversation_keys(agent, rows).items():
        # A page chat replaced by New chat never comes back; it is listed only
        # while it still remembers something, so that can be read and forgotten.
        if (page and channels.platform_of(key) == access.PAGE_PLATFORM and key not in page
                and not (agent is not None and _memory_count(agent, key))):
            continue
        counts = by_conv.get(key, {})
        out.append({
            "id": key,
            "platform": channels.platform_of(key),
            "kind": "dm" if channels.is_dm(key) else "group",
            "last_activity": last,
            "memories": len(agent.memories.get(key, [])) if agent is not None else 0,
            "learned": counts.get("learned", 0),
            "observing": counts.get("observing", 0),
            "latest": counts.get("latest", 0.0),
        })
    out.sort(key=lambda c: -c["last_activity"])
    return {"conversations": out}


def _allowed_actions(state: str, cand: dict | None = None) -> list[str]:
    """What a person may do to a candidate: put an observed one in use or set
    it aside, undo one in use, bring back what the character set aside."""
    if state == candidates.STATE_PROPOSED:
        return ["promote", "reject"]
    if state == candidates.STATE_PROMOTED:
        return ["rollback"]
    return ["restore"] if candidates.restorable(cand) else []


def _active_rivals(cand: dict, peers: list[dict], policy) -> list[dict]:
    """Other rewrites of the same reply already in use: one reply never has
    two active rewrites, so promoting `cand` must replace them (learning.put_in_use)."""
    return promotion.active_rivals(cand, peers, policy=policy)


def _candidate_view(cand: dict, events: dict, in_use: dict, policy,
                    where: dict) -> dict:
    """One candidate as the local page shows it; `personagent learned` has the rest.
    `where` is its standing() while observed, else in_use_by()."""
    actions = _allowed_actions(cand.get("state", ""), cand)
    if "promote" in actions and _active_rivals(
            cand, in_use.get(str(cand.get("reply") or ""), []), policy):
        actions = ["replace" if a == "promote" else a for a in actions]
    linked = sorted((events[eid] for eid in cand.get("evidence") or [] if eid in events),
                    key=lambda ev: _epoch(ev.get("ts")))
    observed = cand.get("state") == candidates.STATE_PROPOSED
    return {
        "id": cand.get("candidate_id", ""),
        "type": cand.get("type", ""),
        "created": _epoch(cand.get("created_at")),
        "reply": _clip(cand.get("reply"), 1000),
        "better": _clip(cand.get("better"), 1000),
        "lesson": _clip((cand.get("payload") or {}).get("lesson"), 300),
        "evidence": [{"speaker": ev.get("speaker_name") or ev.get("speaker_id") or ""}
                     for ev in linked],
        "actions": actions,
        "standing": where if observed else None,
        "by": None if observed else where,
    }


def _decision_view(row: dict) -> dict:
    """One speak-or-stay-quiet line. `excerpt` is the reply, or the message it
    let pass; `answered` is the start of the message a reply answered, and
    `sender` the display name of whoever wrote the message either refers to."""
    return {"ts": row.get("ts", 0.0), "mode": row.get("mode", ""),
            "spoke": bool(row.get("spoke")), "reason": row.get("reason", ""),
            "excerpt": row.get("excerpt", ""), "count": int(row.get("count") or 1),
            "answered": row.get("answered", ""), "sender": row.get("sender", "")}


# ------------------------------------------------------------------ memory --

MEMORY_KINDS = ("note", "episode", "thread", "core")
_FORGET_BY = ("page", "terminal")
REMOVED_LIMIT = 50


def _note_view(where: str, item: dict) -> dict:
    """One remembered fact: who it is about, who said it, when it was first
    noted and last drawn on."""
    text = str(item.get("text") or "")
    by = item.get("saved_by_name") or ("auto" if item.get("auto") else "")
    return {"text": _clip(text, 500), "time": _epoch(item.get("time")), "by": by,
            "about": item.get("user_name") or "", "conv": where,
            # The old text key still names a note that has no id yet.
            "id": str(item.get("id") or embeddings.text_key(text)),
            "born": _epoch(item.get("born") or item.get("time")),
            "used": _epoch(item.get("used")),
            "said_by_name": str(item.get("said_by_name") or "")}


def _episode_view(row: dict) -> dict:
    return {"id": str(row.get("id") or ""), "text": _clip(row.get("text"), 300),
            "t0": _epoch(row.get("t0")), "t1": _epoch(row.get("t1") or row.get("t0")),
            "names": [str(n) for n in row.get("names") or [] if n][:8]}


def _thread_view(row: dict | None) -> dict | None:
    if not row or not row.get("text"):
        return None
    return {"id": str(row.get("id") or ""), "text": _clip(row.get("text"), 500),
            "from_t": _epoch(row.get("from_t")), "to_t": _epoch(row.get("to_t"))}


def _removed_view(row: dict) -> dict:
    return {"tid": str(row.get("tid") or ""), "kind": str(row.get("kind") or ""),
            "why": str(row.get("why") or ""), "by": str(row.get("by") or ""),
            "at": _epoch(row.get("at")), "text": _clip(row.get("text"), 500),
            "until": _epoch(row.get("until"))}


def _consolidation(agent, conv: str, now: float) -> dict | None:
    """Today's consolidation calls against the cap; None while it is off."""
    settings = getattr(agent, "settings", None)
    cap = int(getattr(settings, "memory_calls_per_day", 0) or 0)
    if cap <= 0 or int(getattr(agent, "memory_tidy_every", 0) or 0) <= 0:
        return None
    status = memstate.CallBudget(agent.memory_state).status(now, cap, conv)
    return {key: status[key] for key in ("calls_today", "cap", "paused_until", "next_at")}


def _remembered(agent, conv: str) -> dict:
    """What a chat remembers beyond its facts: when the always-present note
    changed, the summary, the events, what can be brought back."""
    now = time.time()
    store = agent.episode_store
    events = sorted(store.episodes(conv), key=lambda e: _epoch(e.get("t1") or e.get("t0")),
                    reverse=True)
    return {"core_at": float(agent.memory_state.core_at(conv) or 0.0),
            "thread": _thread_view(store.thread(conv)),
            "episodes": [_episode_view(e) for e in events[:LIST_LIMIT * 3]],
            "removed": [_removed_view(r) for r in agent._removed_items(conv, now)][:REMOVED_LIMIT],
            "memory_status": _consolidation(agent, conv, now)}


def memory_listing(agent, conv: str = "") -> dict:
    """Every chat's memory, or one chat's, and what can be brought back: what
    `personagent memory` prints."""
    store = agent.episode_store
    keys = [conv] if conv else sorted(
        set(agent.memories) | set(agent.core_memory) | set(store.convs()))
    chats = []
    for key in keys:
        core = agent.core_memory.get(key, "")
        events = sorted(store.episodes(key), key=lambda e: _epoch(e.get("t0")))
        entry = {"conv": key,
                 "core": {"text": core, "at": float(agent.memory_state.core_at(key) or 0.0)}
                 if core else None,
                 "thread": _thread_view(store.thread(key)),
                 "facts": [_note_view(key, item) for item in agent.memories.get(key, [])],
                 "events": [_episode_view(e) for e in events]}
        if entry["core"] or entry["thread"] or entry["facts"] or entry["events"]:
            chats.append(entry)
    return {"chats": chats,
            "removed": [dict(_removed_view(r), conv=str(r.get("conv") or ""))
                        for r in agent._removed_items(conv or None)]}


def _memory_count(agent, conv: str) -> int:
    store = agent.episode_store
    return (len(agent.memories.get(conv, [])) + len(store.episodes(conv))
            + bool(store.thread(conv)) + bool(agent.core_memory.get(conv)))


_GROUPS = {candidates.STATE_PROPOSED: "observing", candidates.STATE_PROMOTED: "learned"}


def conversation_payload(agent, conv_id: str) -> dict:
    learning = _Learning(agent)
    learning_key = channels.learning_key(conv_id)
    rows = learning.ledger.all()
    mine = [c for c in rows
            if str((c.get("scope") or {}).get("conv_id") or "") == learning_key]
    mine.sort(key=lambda c: str(c.get("created_at") or ""), reverse=True)
    shown: dict[str, list[dict]] = {"observing": [], "learned": []}
    for cand in mine:
        group = _GROUPS.get(cand.get("state"))
        if group and len(shown[group]) < LIST_LIMIT:
            shown[group].append(cand)
    wanted = {eid for group in shown.values() for cand in group
              for eid in cand.get("evidence") or []}
    # An observed item's standing needs the whole log (related events); read it once.
    every = learning.log.all() if shown["observing"] else None
    if every is not None:
        events = {e.get("event_id"): e for e in every if e.get("event_id") in wanted}
    else:
        events = ({e.get("event_id"): e for e in learning.log.many(wanted)}
                  if wanted else {})
    # Only a rewrite in use can stand in an observed one's way.
    in_use: dict[str, list[dict]] = {}
    for cand in rows if shown["observing"] else ():
        if cand.get("state") == candidates.STATE_PROMOTED:
            in_use.setdefault(str(cand.get("reply") or ""), []).append(cand)
    # Where each item stands, or how it came into use.
    placed: dict[str, dict] = {c.get("candidate_id", ""): in_use_by(c) for c in shown["learned"]}
    if shown["observing"]:
        judge = learning.judge()
        index = promotion.EvidenceIndex(every, rows)
        now = time.time()
        for cand in shown["observing"]:
            full = standing(cand, index, learning.policy, judge, now)
            placed[cand.get("candidate_id", "")] = {k: full[k] for k in STANDING_SENT}
    memories, core = [], ""
    remembered = {"core_at": 0.0, "thread": None, "episodes": [], "removed": [],
                  "memory_status": None}
    if agent is not None:
        kept = [(conv_id, item) for item in reversed(agent.memories.get(conv_id, []))]
        # What its prompt also reads, so the page shows all it knows here.
        kept += agent._notes_from_rooms(conv_id)
        memories = [_note_view(where, item) for where, item in kept]
        core = _clip(agent.core_memory.get(conv_id, ""), 600)
        remembered = _remembered(agent, conv_id)
    return {
        "id": conv_id,
        "platform": channels.platform_of(conv_id),
        "kind": "dm" if channels.is_dm(conv_id) else "group",
        "decisions": [_decision_view(row) for row in decision_log.LOG.recent(conv_id)],
        "memories": memories,
        "core_note": core,
        **remembered,
        **{group: [_candidate_view(c, events, in_use, learning.policy,
                                   placed.get(c.get("candidate_id", ""), {}))
                   for c in cands]
           for group, cands in shown.items()},
    }


def _promote(learning: _Learning, cid: str, action: str, ts: str,
             reason: str) -> tuple[int, dict] | None:
    """Promote `cid`, replacing the rewrite of its reply in use only when
    `action` is "replace"; the refusal, or None once it is promoted."""
    ledger = learning.ledger
    cand = ledger.get(cid)
    rivals = _active_rivals(cand, ledger.all(), learning.policy)
    if rivals and action == "promote":
        ids = [r.get("candidate_id", "") for r in rivals]
        return 409, {"error": f"another rewrite of this reply is in use ({ids[0][:12]}); "
                              "replace it instead",
                     "code": "active_rival", "rivals": ids}
    # The same supersede-first logic the character's own adoption uses.
    ok = learning_rules.put_in_use(ledger, cid, ts=ts, actor=ACTOR, reason=reason,
                                   policy=learning.policy)
    if not ok:
        return 409, {"error": f"cannot {action} a candidate that is {cand.get('state')}",
                     "code": "illegal_transition"}
    # As the automatic path does: drafts only this one's evidence argued for
    # can never promote now.
    for other in promotion.answered_drafts(ledger.get(cid), ledger.all(),
                                           policy=learning.policy):
        ledger.reject(other, ts=ts, actor=ACTOR, reason=f"answered by {cid}")
    return None


def _restore(learning: _Learning, cid: str, ts: str, reason: str) -> bool:
    """Bring back what the character or its time limit set aside; a rewrite
    of the same reply in use steps aside for it."""
    ledger = learning.ledger
    rivals = promotion.active_rivals(ledger.get(cid), ledger.all(), policy=learning.policy)
    if not ledger.restore(cid, ts=ts, actor=ACTOR, reason=reason):
        return False
    for rival in rivals:
        ledger.rollback(rival.get("candidate_id", ""), ts=ts, actor=ACTOR,
                        reason=f"replaced by {cid}")
    return True


def apply_action(agent, cid: str, action: str, reason: str = "") -> tuple[int, dict]:
    """Promote, replace, reject, roll back or restore one candidate, then
    rebuild the views."""
    learning = _Learning(agent)
    ledger = learning.ledger
    cand = ledger.get(cid)
    if cand is None:
        return 404, {"error": "no such candidate", "code": "unknown_candidate"}
    before = cand.get("state", "")
    reason = _clip(reason, 300) or "operator decision"
    ts = datetime.now().isoformat(timespec="seconds")
    verb = "promote" if action == "replace" else action
    if verb not in _allowed_actions(before, cand):
        return 409, {"error": f"cannot {action} a candidate that is {before}",
                     "code": "illegal_transition"}
    if action == "restore":
        if not _restore(learning, cid, ts, reason):
            return 409, {"error": "only what the character set aside can be brought back",
                         "code": "illegal_transition"}
    elif _ACTIONS[verb] == candidates.STATE_PROMOTED:
        refused = _promote(learning, cid, action, ts, reason)
        if refused is not None:
            return refused
    else:
        transition = {"reject": ledger.reject, "rollback": ledger.rollback}[action]
        if not transition(cid, ts=ts, actor=ACTOR, reason=reason):
            return 409, {"error": f"cannot {action} a candidate that is {before}",
                         "code": "illegal_transition"}
    rebuilt = learning.rebuild()
    return 200, {"ok": True, "id": cid, "before": before,
                 "after": ledger.get(cid).get("state", ""),
                 "views_rebuilt": rebuilt}


# ----------------------------------------------------------------- routes ---

def _pointer() -> str:
    en = ("personagent is running. Its Activity view is in the local page: run "
          "`{cli}` on this computer to open it. On a server, `{cli} learned` "
          "reviews what it learned.\n")
    zh = ("personagent 正在运行。「动态」位于本地页面中：请在本机上运行 `{cli}` 打开。"
          "在服务器上，可使用 `{cli} learned` 查看角色学到的内容。\n")
    configured = langs.normalize(os.getenv("AGENT_LANG", ""))
    shown = [en, zh]
    if configured not in ("", "en", "zh"):
        shown.append(langs.say(en, zh, configured))
    return "\n".join(text.format(cli=_cli()) for text in shown)


@router.get("/", include_in_schema=False)
async def dashboard_pointer():
    return _harden(PlainTextResponse(_pointer()))


@router.get("/api/dashboard/conversations", include_in_schema=False)
async def dashboard_conversations(request: Request):
    refused = _check(request)
    if refused is not None:
        return refused
    agent = _server().agent
    return _json(conversations_payload(agent), agent)


@router.get("/api/dashboard/conversation", include_in_schema=False)
async def dashboard_conversation(request: Request, id: str = ""):
    refused = _check(request)
    if refused is not None:
        return refused
    if not id or len(id) > 512:
        return _refused(400, "invalid_id", "give a conversation id")
    agent = _server().agent
    return _json(conversation_payload(agent, id), agent)


@router.post("/api/dashboard/candidates/{cid}/{action}", include_in_schema=False)
async def dashboard_action(cid: str, action: str, request: Request):
    refused = _check(request, write=True)
    if refused is not None:
        return refused
    if action not in _VERBS:
        return _refused(404, "unknown_action", "unknown action")
    srv = _server()
    try:
        body = await srv._read_body_limited(request, _MAX_BODY)
    except srv.RequestBodyTooLarge:
        return _refused(413, "body_too_large", "request body too large")
    try:
        parsed = json.loads(body or b"{}")
    except ValueError:
        return _refused(400, "invalid_json", "body is not JSON")
    reason = parsed.get("reason", "") if isinstance(parsed, dict) else ""
    agent = srv.agent
    status, payload = apply_action(agent, cid, action, str(reason or ""))
    return _json(payload, agent, status)


async def _memory_write(request: Request) -> tuple[dict | None, Response | None]:
    """The JSON object a memory write sends, or the refusal."""
    refused = _check(request, write=True)
    if refused is not None:
        return None, refused
    srv = _server()
    try:
        body = await srv._read_body_limited(request, _MAX_BODY)
    except srv.RequestBodyTooLarge:
        return None, _refused(413, "body_too_large", "request body too large")
    try:
        parsed = json.loads(body or b"{}")
    except ValueError:
        return None, _refused(400, "invalid_json", "body is not JSON")
    if not isinstance(parsed, dict):
        return None, _refused(400, "invalid_json", "body is not an object")
    if srv.agent is None:
        return None, _refused(503, "agent_off", "the character is not running")
    return parsed, None


def _conv_of(parsed: dict) -> str:
    conv = str(parsed.get("conv") or "")
    return conv if 0 < len(conv) <= 512 else ""


@router.post("/api/dashboard/memory/forget", include_in_schema=False)
async def dashboard_forget(request: Request):
    """Forget one remembered item of a chat: a fact (`note`), an event, the
    summary (`thread`) or the always-present note (`core`). It can be brought
    back for a day with the trash id it answers."""
    parsed, refused = await _memory_write(request)
    if refused is not None:
        return refused
    conv = _conv_of(parsed)
    if not conv:
        return _refused(400, "invalid_id", "give a conversation id")
    # The older body: {conv, note} forgets a fact, {conv} the always-present note.
    item = str(parsed.get("id") or parsed.get("note") or "")
    kind = str(parsed.get("kind") or ("note" if item else "core"))
    if kind not in MEMORY_KINDS or len(item) > 128:
        return _refused(400, "invalid_kind", "kind is one of " + ", ".join(MEMORY_KINDS))
    by = parsed.get("by") if parsed.get("by") in _FORGET_BY else "page"
    agent = _server().agent
    async with agent.locks[conv]:
        tid = agent._forget_item(conv, kind, item, by=by)
    if not tid:
        return _refused(409, "already_forgotten", "that item is already gone")
    # "-": forgotten, but the trash could not keep it, so there is no undo.
    return _json({"ok": True, "tid": "" if tid == "-" else tid}, agent)


@router.post("/api/dashboard/memory/restore", include_in_schema=False)
async def dashboard_restore(request: Request):
    """Bring back a removed item while it is still restorable."""
    parsed, refused = await _memory_write(request)
    if refused is not None:
        return refused
    tid = str(parsed.get("tid") or "")
    if not tid or len(tid) > 64:
        return _refused(400, "invalid_id", "give a trash id")
    by = parsed.get("by") if parsed.get("by") in _FORGET_BY else "page"
    agent = _server().agent
    row = agent.memory_trash.get(tid)
    if row is None:
        return _refused(404, "restore_gone", "that item can no longer be restored")
    async with agent.locks[str(row.get("conv") or "")]:
        result = agent._restore(tid, by=by)
    if result == "exists":
        return _refused(409, "already_exists", "that item already exists")
    if result != "ok":
        return _refused(404, "restore_gone", "that item can no longer be restored")
    return _json({"ok": True}, agent)


@router.post("/api/dashboard/memory/forget_chat", include_in_schema=False)
async def dashboard_forget_chat(request: Request):
    """Forget everything one chat remembers, with nothing kept to restore."""
    parsed, refused = await _memory_write(request)
    if refused is not None:
        return refused
    conv = _conv_of(parsed)
    if not conv:
        return _refused(400, "invalid_id", "give a conversation id")
    agent = _server().agent
    async with agent.locks[conv]:
        count = _memory_count(agent, conv)
        agent._forget_chat(conv)
    return _json({"ok": True, "forgotten": count}, agent)


@router.get("/api/dashboard/memory/list", include_in_schema=False)
async def dashboard_memory_list(request: Request, conv: str = ""):
    """What `personagent memory` lists while the service runs."""
    refused = _check(request)
    if refused is not None:
        return refused
    if len(conv) > 512:
        return _refused(400, "invalid_id", "give a conversation id")
    agent = _server().agent
    if agent is None:
        return _refused(503, "agent_off", "the character is not running")
    return _json(memory_listing(agent, conv), agent)
