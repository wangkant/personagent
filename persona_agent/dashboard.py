"""The Activity API: is it running, why did it speak, what has it learned.

The local page's Activity view (persona_agent/welcome.py) reads
``/api/dashboard/...`` server to server. Everything is read-only except
promote, reject and roll back, which go through the candidate ledger the way
``personagent learned`` does, rebuild the retrieval views, and record the
actor ``dashboard``.

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
import secrets
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from . import (candidates, channels, decision_log, embeddings, evidence,
               langs, lineage, promotion)
from .config_env import env_bool, env_int
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
# "replace" promotes in place of the rewrite of the same reply that is in use.
_VERBS = (*_ACTIONS, "replace")

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


def _active_rivals(cand: dict, peers: list[dict], policy) -> list[dict]:
    """Other rewrites of the same reply already in use: one reply never has
    two active rewrites, so promoting `cand` must replace them."""
    ids = set(promotion.find_conflicts(cand, peers, policy=policy))
    return [p for p in peers if p.get("candidate_id") in ids
            and p.get("state") == candidates.STATE_PROMOTED]


def _candidate_view(cand: dict, events: dict, in_use: dict, policy) -> dict:
    """One candidate as the local page shows it; `personagent learned` has the rest."""
    actions = _allowed_actions(cand.get("state", ""))
    if "promote" in actions and _active_rivals(
            cand, in_use.get(str(cand.get("reply") or ""), []), policy):
        actions = ["replace" if a == "promote" else a for a in actions]
    linked = sorted((events[eid] for eid in cand.get("evidence") or [] if eid in events),
                    key=lambda ev: _epoch(ev.get("ts")))
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
    }


def _decision_view(row: dict) -> dict:
    """One speak-or-stay-quiet line. `excerpt` is the reply, or the message it
    let pass; `answered` is the start of the message a reply answered, and
    `sender` the display name of whoever wrote the message either refers to."""
    return {"ts": row.get("ts", 0.0), "mode": row.get("mode", ""),
            "spoke": bool(row.get("spoke")), "reason": row.get("reason", ""),
            "excerpt": row.get("excerpt", ""), "count": int(row.get("count") or 1),
            "answered": row.get("answered", ""), "sender": row.get("sender", "")}


_GROUPS = {candidates.STATE_PROPOSED: "pending", candidates.STATE_PROMOTED: "learned"}


def conversation_payload(agent, conv_id: str) -> dict:
    learning = _Learning(agent)
    learning_key = channels.learning_key(conv_id)
    rows = learning.ledger.all()
    mine = [c for c in rows
            if str((c.get("scope") or {}).get("conv_id") or "") == learning_key]
    mine.sort(key=lambda c: str(c.get("created_at") or ""), reverse=True)
    shown: dict[str, list[dict]] = {"pending": [], "learned": []}
    for cand in mine:
        group = _GROUPS.get(cand.get("state"))
        if group and len(shown[group]) < LIST_LIMIT:
            shown[group].append(cand)
    wanted = {eid for group in shown.values() for cand in group
              for eid in cand.get("evidence") or []}
    events = ({e.get("event_id"): e for e in learning.log.many(wanted)}
              if wanted else {})
    # Only a rewrite in use can stand in a pending one's way.
    in_use: dict[str, list[dict]] = {}
    for cand in rows if shown["pending"] else ():
        if cand.get("state") == candidates.STATE_PROMOTED:
            in_use.setdefault(str(cand.get("reply") or ""), []).append(cand)
    memories, core = [], ""
    if agent is not None:
        kept = [(conv_id, item) for item in reversed(agent.memories.get(conv_id, []))]
        # What its prompt also reads, so the page shows all it knows here.
        kept += agent._notes_from_rooms(conv_id)
        for where, item in kept:
            by = item.get("saved_by_name") or ("auto" if item.get("auto") else "")
            memories.append({"text": _clip(item.get("text"), 500),
                             "time": _epoch(item.get("time")), "by": by,
                             "about": item.get("user_name") or "", "conv": where,
                             "id": embeddings.text_key(item["text"])})
        core = _clip(agent.core_memory.get(conv_id, ""), 600)
    return {
        "id": conv_id,
        "platform": channels.platform_of(conv_id),
        "kind": "dm" if channels.is_dm(conv_id) else "group",
        "decisions": [_decision_view(row) for row in decision_log.LOG.recent(conv_id)],
        "memories": memories,
        "core_note": core,
        **{group: [_candidate_view(c, events, in_use, learning.policy) for c in cands]
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
    if not rivals:
        ok = ledger.promote(cid, ts=ts, actor=ACTOR, reason=reason)
    else:
        ok = ledger.supersede(rivals[0].get("candidate_id", ""), cid, ts=ts,
                              actor=ACTOR, reason=reason)
        # A ledger may hold several live rivals; retire them all.
        for extra in rivals[1:] if ok else ():
            ledger.rollback(extra.get("candidate_id", ""), ts=ts, actor=ACTOR,
                            reason=f"replaced by {cid}")
    if not ok:
        return 409, {"error": f"cannot {action} a candidate that is {cand.get('state')}",
                     "code": "illegal_transition"}
    # As the automatic path does: drafts only this one's evidence argued for
    # can never promote now.
    for other in promotion.answered_drafts(ledger.get(cid), ledger.all(),
                                           policy=learning.policy):
        ledger.reject(other, ts=ts, actor=ACTOR, reason=f"answered by {cid}")
    return None


def apply_action(agent, cid: str, action: str, reason: str = "") -> tuple[int, dict]:
    """Promote, replace, reject or roll back one candidate, then rebuild the views."""
    learning = _Learning(agent)
    ledger = learning.ledger
    cand = ledger.get(cid)
    if cand is None:
        return 404, {"error": "no such candidate", "code": "unknown_candidate"}
    before = cand.get("state", "")
    reason = _clip(reason, 300) or "operator decision"
    ts = datetime.now().isoformat(timespec="seconds")
    target = _ACTIONS.get(action, candidates.STATE_PROMOTED)
    if before not in candidates._ALLOWED_FROM[target]:
        return 409, {"error": f"cannot {action} a candidate that is {before}",
                     "code": "illegal_transition"}
    if target == candidates.STATE_PROMOTED:
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


@router.post("/api/dashboard/memory/forget", include_in_schema=False)
async def dashboard_forget(request: Request):
    """Forget one note of a chat, by its id, or with no id its core note."""
    refused = _check(request, write=True)
    if refused is not None:
        return refused
    srv = _server()
    try:
        body = await srv._read_body_limited(request, _MAX_BODY)
    except srv.RequestBodyTooLarge:
        return _refused(413, "body_too_large", "request body too large")
    try:
        parsed = json.loads(body or b"{}")
    except ValueError:
        return _refused(400, "invalid_json", "body is not JSON")
    if not isinstance(parsed, dict):
        return _refused(400, "invalid_json", "body is not an object")
    conv, note = str(parsed.get("conv") or ""), str(parsed.get("note") or "")
    if not conv or len(conv) > 512:
        return _refused(400, "invalid_id", "give a conversation id")
    agent = srv.agent
    async with agent.locks[conv]:
        done = agent._forget_note(conv, note) if note else agent._forget_core(conv)
    if not done:
        return _refused(409, "already_forgotten", "that note is already gone")
    return _json({"ok": True}, agent)
