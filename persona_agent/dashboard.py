"""The operator's page: is it running, why did it speak, what has it learned.

``GET /`` serves a static page (persona_agent/static/) whose data comes from
``/api/dashboard/...``. Everything is read-only except promote, reject and roll
back, which go through the candidate ledger the way ``personagent learned``
does, rebuild the retrieval views, and record the actor ``dashboard``.

Served to local requests only (a loopback peer, a local Host name, no proxy
headers); any other client must send ``X-Personagent-Token`` = CONNECTOR_TOKEN.
A state-changing call is a POST that also carries ``X-Personagent-Dashboard: 1``
and, when the browser sends an Origin, the page's own origin.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, Response

from . import (__version__, access, candidates, channels, decision_log,
               evidence, home, lineage, preflight, promotion)
from .config_env import env_bool, env_int
from .paths import ROOT, resolve_runtime_lang_file

STATIC_DIR = Path(__file__).resolve().parent / "static"
_ASSETS = {
    "app.js": "text/javascript; charset=utf-8",
    "app.css": "text/css; charset=utf-8",
}
WRITE_HEADER = "x-personagent-dashboard"
ACTOR = "dashboard"
_MAX_BODY = 4096
_STARTED = time.time()

_PAGE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; "
             "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
             "form-action 'none'; frame-ancestors 'none'; object-src 'none'")
_DATA_CSP = "default-src 'none'; frame-ancestors 'none'"

# Every setting with one of these endings holds a credential (LLM_API_KEY,
# CONNECTOR_TOKEN, QQ_ONEBOT_SECRET, ...): its value never leaves the process.
_SECRET_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "PASSWORD")

_ACTIONS = {"promote": candidates.STATE_PROMOTED,
            "reject": candidates.STATE_REJECTED,
            "rollback": candidates.STATE_ROLLED_BACK}

router = APIRouter()


def install(app: FastAPI, *, enabled: bool | None = None) -> bool:
    """Add the dashboard's routes to `app` unless DASHBOARD_ENABLED is off."""
    if enabled is None:
        enabled = env_bool("DASHBOARD_ENABLED", True)
    if enabled:
        app.include_router(router)
    return bool(enabled)


def _server():
    # Imported late: server.py includes this router while it is being built.
    from . import server
    return server


# ---------------------------------------------------------------- access ----

def _harden(response: Response, csp: str = _DATA_CSP) -> Response:
    headers = response.headers
    headers["Content-Security-Policy"] = csp
    headers["X-Content-Type-Options"] = "nosniff"
    headers["Referrer-Policy"] = "no-referrer"
    headers["X-Frame-Options"] = "DENY"
    headers["Cross-Origin-Resource-Policy"] = "same-origin"
    headers["Cross-Origin-Opener-Policy"] = "same-origin"
    headers["Cache-Control"] = "no-store"
    return response


def _refused(status: int, code: str, message: str) -> Response:
    return _harden(_server()._error(status, code, message))


def _is_local(request: Request) -> bool:
    """A loopback peer that names a local host and came through no proxy.

    The Host check is what defeats DNS rebinding: a page that rebinds its own
    name to 127.0.0.1 still sends that name."""
    srv = _server()
    peer = request.client.host if request.client is not None else ""
    if not srv._is_loopback_host(peer):
        return False
    host = request.headers.get("host")
    if host is None or srv._host_header_name(host) not in srv._LOCAL_HOST_NAMES:
        return False
    return not any(name in request.headers for name in srv._PROXY_HEADERS)


def _same_origin(origin: str, request: Request, authenticated: bool) -> bool:
    parts = urlsplit(origin.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return False
    hosts = {request.headers.get("host", "").strip().lower()}
    if authenticated:
        # A reverse proxy may rewrite Host; the browser still names the public one.
        hosts.add(request.headers.get("x-forwarded-host", "").strip().lower())
    return parts.netloc.lower() in hosts - {""}


def _check(request: Request, *, data: bool = True,
           write: bool = False) -> Response | None:
    """The refusal for a request the dashboard must not answer, else None."""
    srv = _server()
    token = srv.CONNECTOR_TOKEN
    supplied = request.headers.get("x-personagent-token")
    authenticated = False
    if token and supplied is not None:
        if not srv._ct_equal(supplied, token):
            return _refused(403, "forbidden", "forbidden")
        authenticated = True
    if not authenticated and not _is_local(request):
        return _refused(403, "non_local_request",
                        "the dashboard answers local requests only; from "
                        "elsewhere send X-Personagent-Token")
    site = request.headers.get("sec-fetch-site", "").strip().lower()
    if data and site in ("cross-site", "same-site"):
        return _refused(403, "cross_site", "cross-site request refused")
    if write:
        if request.headers.get(WRITE_HEADER, "").strip() != "1":
            return _refused(403, "missing_header",
                            "state-changing calls need X-Personagent-Dashboard: 1")
        origin = request.headers.get("origin")
        if origin is not None and not _same_origin(origin, request, authenticated):
            return _refused(403, "foreign_origin", "cross-origin request refused")
        ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return _refused(415, "unsupported_media_type", "send application/json")
    return None


# --------------------------------------------------------------- secrets ----

def _secret_values(agent) -> list[str]:
    values: set[str] = set()
    for name, value in os.environ.items():
        upper = name.upper()
        if upper.endswith(_SECRET_SUFFIXES):
            values.add(str(value or "").strip())
    srv = _server()
    values.update((srv.CONNECTOR_TOKEN, srv.QQ_ONEBOT_SECRET))
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
    raw = os.getenv("AGENT_LANG", "en").strip().lower()
    return "zh" if raw.startswith(("zh", "cn")) else "en"


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
            self.admins = agent._admins()
            lineage_file = agent.learning_dir / lineage.FILE_NAME
        else:
            self.ledger = candidates.CandidateLedger(
                resolve_runtime_lang_file("candidate_ledger", "jsonl", self.lang))
            self.log = evidence.EvidenceLog(
                resolve_runtime_lang_file("evidence", "jsonl", self.lang))
            self.policy = promotion.Policy.from_env()
            self.admins = access.identity_from_env().admins
            lineage_file = Path(self.log.path).parent / lineage.FILE_NAME
        # Read, never extended: scope comparisons need every known revision.
        self.lineage = lineage.PersonaLineage(lineage_file)
        for version, hashes in self.lineage.versions().items():
            evidence.register_persona_lineage(version, hashes)

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


# ----------------------------------------------------------------- status ---

def _shown_path(path) -> str:
    """A path under the user's home directory, written from ``~``."""
    try:
        return str(Path("~") / Path(path).resolve().relative_to(Path.home().resolve()))
    except (ValueError, OSError, RuntimeError):
        return str(path)


def _persona_file(lang: str) -> tuple[str, str]:
    configured = ROOT / os.getenv("PERSONA_FILE", "persona.txt")
    if configured.is_file():
        return str(configured), "file"
    for example in (ROOT / "data" / f"persona.example.{lang}.txt",
                    home.resource("data", f"persona.example.{lang}.txt")):
        if example.is_file():
            return str(example), "example"
    return str(configured), "builtin"


def _persona(agent, learning: _Learning) -> dict:
    if agent is None:
        return {"name": os.getenv("PERSONA_NAME", "").strip(), "file": "",
                "source": "", "version": "", "hash": "", "revisions": 0}
    path, source = _persona_file(learning.lang)
    version = agent.persona_version or ""
    hashes = learning.lineage.hashes(version)
    current = agent.persona_hash
    return {
        "name": agent.persona_name or "",
        "file": _shown_path(path),
        "source": source,
        "version": version,
        "hash": current,
        # The running document counts even before its first learning turn
        # records it in the lineage.
        "revisions": len(hashes) + (0 if current in hashes else 1),
    }


def _models(agent) -> list[dict]:
    if agent is None:
        return []
    fallback = agent.llm_fallback_model
    roles = [("reply", agent.model), ("gate", agent.llm_judge_model),
             ("dm", agent.llm_dm_model),
             ("fallback", fallback if fallback != agent.model else ""),
             ("react", agent.react_model if agent.react_learn_enabled else ""),
             ("eval", agent.eval_model if agent.eval_enabled else ""),
             ("evolve", agent.evolve_model if agent.evolve_auto_enabled else ""),
             ("vision", agent.vision_model), ("embedding", agent.embedding_model)]
    return [{"role": role, "name": str(name)} for role, name in roles if name]


def _connectors(agent) -> list[dict]:
    if agent is None:
        return []
    seen: dict[str, dict] = {}
    store = agent.connector_handles
    for key in store.keys():
        record = store.get(key) or {}
        cid = record.get("connector_id") or ""
        entry = seen.setdefault(cid, {
            "id": cid, "platforms": set(), "capabilities": set(),
            "last_event": 0.0, "conversations": 0})
        if record.get("platform"):
            entry["platforms"].add(record["platform"])
        entry["capabilities"].update(record.get("capabilities") or ())
        entry["last_event"] = max(entry["last_event"],
                                  float(record.get("updated_at") or 0.0))
        entry["conversations"] += 1
    # A connector that pulls the outbox but has not forwarded a message yet.
    for cid in getattr(agent.outbox, "_last_pull", {}):
        seen.setdefault(cid, {"id": cid, "platforms": set(),
                              "capabilities": set(), "last_event": 0.0,
                              "conversations": 0})
    out = []
    for cid, entry in seen.items():
        out.append({
            "id": cid,
            "platforms": sorted(entry["platforms"]),
            "capabilities": sorted(entry["capabilities"]),
            "last_event": entry["last_event"],
            "conversations": entry["conversations"],
            "pulling": bool(cid) and agent.outbox.live(cid),
        })
    out.sort(key=lambda c: -c["last_event"])
    return out


def _activity(agent) -> dict:
    srv = _server()
    out = {"received": False, "spoke": False, "refused": [],
           "trigger_count": 0, "persona_name": "",
           "connector_token": bool(srv.CONNECTOR_TOKEN)}
    if agent is None:
        return out
    refused = []
    for key in list(getattr(agent, "_refusals_logged", {}))[-10:]:
        conv, _, reason = str(key).partition("\x00")
        refused.append({"conversation": conv, "reason": reason})
    dm_spoke = any(turn.get("role") == "assistant"
                   for turns in agent.dm_history.values() for turn in turns
                   if isinstance(turn, dict))
    out.update({
        "received": bool(any(agent.last_activity_at.values())
                         or any(agent.last_dm_activity_at.values())
                         or refused or decision_log.LOG.last_seen()),
        "spoke": bool(any(agent.last_reply_at.values()) or dm_spoke),
        "refused": refused,
        "trigger_count": int(agent.chat_trigger_count),
        "persona_name": agent.persona_name or "",
    })
    return out


def status_payload(agent) -> dict:
    learning = _Learning(agent)
    if agent is None:
        state = "off"
    else:
        state = "ready" if agent.enabled else "no_key"
    try:
        findings = [{"level": f.level, "key": f.key, "detail": f.detail}
                    for f in preflight.check_config()]
    except Exception:
        findings = []
    now = time.time()
    return {
        "version": __version__,
        "now": now,
        "uptime_s": max(0.0, now - _STARTED),
        "home": _shown_path(ROOT),
        "lang": learning.lang,
        "agent": state,
        "persona": _persona(agent, learning),
        "models": _models(agent),
        "connectors": _connectors(agent),
        "outbox": bool(agent is not None and agent.connector_outbox_enabled),
        "preflight": findings,
        "activity": _activity(agent),
    }


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
        counts = by_conv.setdefault(conv, {"learned": 0, "pending": 0})
        if cand.get("state") == candidates.STATE_PROMOTED:
            counts["learned"] += 1
        elif cand.get("state") == candidates.STATE_PROPOSED:
            counts["pending"] += 1
    out = []
    for key, last in _conversation_keys(agent, rows).items():
        counts = by_conv.get(key, {})
        out.append({
            "id": key,
            "platform": channels.platform_of(key),
            "kind": "dm" if channels.is_dm(key) else "group",
            "last_activity": last,
            "memories": len(agent.memories.get(key, [])) if agent is not None else 0,
            "learned": counts.get("learned", 0),
            "pending": counts.get("pending", 0),
        })
    out.sort(key=lambda c: -c["last_activity"])
    return {"conversations": out}


def _allowed_actions(state: str) -> list[str]:
    """The buttons a candidate gets: every legal transition, except that a
    live one is rolled back (reversible) rather than rejected (final)."""
    return [name for name, target in _ACTIONS.items()
            if state in candidates._ALLOWED_FROM[target]
            and not (name == "reject" and state == candidates.STATE_PROMOTED)]


def _event_view(event: dict, cand: dict, policy) -> dict:
    adj = event.get("adjudication") or {}
    return {
        "id": event.get("event_id", ""),
        "ts": _epoch(event.get("ts")),
        "kind": event.get("kind", ""),
        "reaction_type": event.get("reaction_type", ""),
        "strength": evidence.classify_strength(event),
        "speaker": event.get("speaker_name") or event.get("speaker_id") or "",
        "speaker_is_recipient": bool(event.get("speaker_id"))
        and event.get("speaker_id") == event.get("recipient_id"),
        "said": _clip(event.get("reaction_text"), 200),
        "verdict": _clip(adj.get("reason"), 200),
        "accepted": bool(adj.get("accept")),
        "better": _clip(adj.get("better"), 300),
        "counts": promotion.supports_candidate(event, cand, policy=policy),
    }


def _checklist(cand: dict, learning: _Learning, events: list[dict],
               peers: list[dict], now: float) -> dict:
    """Each promotion rule, passed or not, in the order `promotion.decide`
    applies them; the verdict itself is `decide`'s."""
    policy = learning.policy
    wanted = set(cand.get("evidence") or [])
    linked = [e for e in events if e.get("event_id") in wanted]
    related = promotion.related_events(cand, events)
    decision = promotion.decide(cand, linked_events=linked, related_events=related,
                                peers=peers, now=now, policy=policy,
                                admin_ids=learning.admins)
    max_age = policy.max_evidence_age_days * 86400.0
    supporting, ids = [], set()
    for ev in linked:
        eid = ev.get("event_id")
        if eid in ids or not promotion.supports_candidate(ev, cand, policy=policy):
            continue
        if max_age > 0 and now - promotion.epoch(ev.get("ts")) > max_age:
            continue
        ids.add(eid)
        supporting.append(ev)
    strong = [e for e in supporting
              if evidence.classify_strength(e) == evidence.STRONG]
    speakers = {str(e.get("speaker_id") or "") for e in supporting} - {""}
    admins = {evidence._text(a, 64) for a in learning.admins} - {""}
    admin_spoke = bool(admins & speakers)
    against = promotion.counter_evidence(cand, related, now=now, policy=policy)
    conflicts = promotion.find_conflicts(cand, peers, policy=policy,
                                         related_events=related)
    can_be_strong = evidence.can_be_strong(str(cand.get("type") or ""))
    speakers_ok = (not speakers or admin_spoke
                   or len(speakers) >= policy.min_speakers)
    rules = [
        {"id": "auto", "ok": policy.auto_promote},
        {"id": "no_disagreement", "ok": not against, "ids": against[:3]},
        {"id": "no_conflict", "ok": not conflicts, "ids": conflicts[:3]},
        {"id": "strong" if can_be_strong else "strong_impossible",
         "ok": len(strong) >= policy.min_strong,
         "have": len(strong), "need": policy.min_strong},
        {"id": "events", "ok": len(supporting) >= policy.min_events,
         "have": len(supporting), "need": policy.min_events,
         "max_age_days": policy.max_evidence_age_days},
        {"id": "speakers", "ok": speakers_ok, "have": len(speakers),
         "need": policy.min_speakers, "admin": admin_spoke},
        {"id": "same_chat", "ok": True, "on": policy.require_same_conversation},
    ]
    waiting = []
    if not policy.auto_promote:
        waiting.append("auto")
    if against or conflicts or not can_be_strong:
        waiting.append("admin")
    else:
        if len(strong) < policy.min_strong:
            waiting.append("strong")
        if len(supporting) < policy.min_events:
            waiting.append("events")
        if not speakers_ok:
            waiting.append("speakers")
    return {"rules": rules, "waiting_for": waiting,
            "promote": decision.promote, "verdict": decision.reason}


def _candidate_view(cand: dict, learning: _Learning, by_id: dict[str, dict],
                    events: list[dict], peers: list[dict], now: float) -> dict:
    payload = cand.get("payload") or {}
    context = payload.get("context") or []
    if isinstance(context, str):
        context = [context]
    view = {
        "id": cand.get("candidate_id", ""),
        "type": cand.get("type", ""),
        "state": cand.get("state", ""),
        "created": _epoch(cand.get("created_at")),
        "reply": _clip(cand.get("reply"), 1000),
        "better": _clip(cand.get("better"), 1000),
        "context": [_clip(line, 200) for line in context[-4:]],
        "history": [{"state": h.get("state", ""), "ts": _epoch(h.get("ts")),
                     "actor": h.get("actor", ""), "reason": _clip(h.get("reason"), 300)}
                    for h in cand.get("history") or []],
        "evidence": sorted(
            (_event_view(by_id[eid], cand, learning.policy)
             for eid in cand.get("evidence") or [] if eid in by_id),
            key=lambda ev: ev["ts"]),
        "missing_evidence": sum(1 for eid in cand.get("evidence") or []
                                if eid not in by_id),
        "actions": _allowed_actions(cand.get("state", "")),
        "superseded_by": cand.get("superseded_by", ""),
        "supersedes": cand.get("supersedes", ""),
    }
    if cand.get("state") == candidates.STATE_PROPOSED:
        view["checklist"] = _checklist(cand, learning, events, peers, now)
    return view


def conversation_payload(agent, conv_id: str) -> dict:
    learning = _Learning(agent)
    learning_key = channels.learning_key(conv_id)
    peers = learning.ledger.all()
    events = learning.log.all()
    by_id = {e.get("event_id"): e for e in events}
    now = time.time()
    mine = [c for c in peers
            if str((c.get("scope") or {}).get("conv_id") or "") == learning_key]
    mine.sort(key=lambda c: str(c.get("created_at") or ""), reverse=True)
    groups = {"pending": [], "learned": [], "past": []}
    for cand in mine:
        state = cand.get("state")
        group = ("pending" if state == candidates.STATE_PROPOSED
                 else "learned" if state == candidates.STATE_PROMOTED else "past")
        groups[group].append(
            _candidate_view(cand, learning, by_id, events, peers, now))
    memories, core, counter, trigger = [], "", 0, 0
    if agent is not None:
        for item in reversed(agent.memories.get(conv_id, [])):
            by = item.get("user_name") or ("auto" if item.get("auto") else "")
            memories.append({"text": _clip(item.get("text"), 500),
                             "time": _epoch(item.get("time")), "by": by,
                             "auto": bool(item.get("auto"))})
        core = _clip(agent.core_memory.get(conv_id, ""), 600)
        counter = int(agent.counters.get(conv_id, 0))
        trigger = int(agent.chat_trigger_count)
    return {
        "id": conv_id,
        "platform": channels.platform_of(conv_id),
        "kind": "dm" if channels.is_dm(conv_id) else "group",
        "counter": counter,
        "trigger_count": trigger,
        "decisions": decision_log.LOG.recent(conv_id),
        "memories": memories,
        "core_note": core,
        **groups,
    }


def apply_action(agent, cid: str, action: str, reason: str = "") -> tuple[int, dict]:
    """Promote, reject or roll back one candidate, then rebuild the views."""
    learning = _Learning(agent)
    ledger = learning.ledger
    cand = ledger.get(cid)
    if cand is None:
        return 404, {"error": "no such candidate", "code": "unknown_candidate"}
    before = cand.get("state", "")
    transition = {"promote": ledger.promote, "reject": ledger.reject,
                  "rollback": ledger.rollback}[action]
    reason = _clip(reason, 300) or "operator decision"
    ts = datetime.now().isoformat(timespec="seconds")
    if not transition(cid, ts=ts, actor=ACTOR, reason=reason):
        return 409, {"error": f"cannot {action} a candidate that is {before}",
                     "code": "illegal_transition"}
    rebuilt = learning.rebuild()
    return 200, {"ok": True, "id": cid, "before": before,
                 "after": ledger.get(cid).get("state", ""),
                 "views_rebuilt": rebuilt}


# ----------------------------------------------------------------- routes ---

def _asset(name: str, content_type: str, csp: str = _DATA_CSP) -> Response:
    try:
        body = (STATIC_DIR / name).read_bytes()
    except OSError:
        return _refused(404, "not_found", "not found")
    return _harden(Response(body, media_type=content_type), csp)


@router.get("/", include_in_schema=False)
async def dashboard_page(request: Request):
    refused = _check(request, data=False)
    if refused is not None:
        return refused
    return _asset("index.html", "text/html; charset=utf-8", _PAGE_CSP)


@router.get("/dashboard/{name}", include_in_schema=False)
async def dashboard_asset(name: str, request: Request):
    refused = _check(request, data=False)
    if refused is not None:
        return refused
    if name not in _ASSETS:
        return _refused(404, "not_found", "not found")
    return _asset(name, _ASSETS[name])


@router.get("/api/dashboard/status", include_in_schema=False)
async def dashboard_status(request: Request):
    refused = _check(request)
    if refused is not None:
        return refused
    agent = _server().agent
    return _json(status_payload(agent), agent)


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
    if action not in _ACTIONS:
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
