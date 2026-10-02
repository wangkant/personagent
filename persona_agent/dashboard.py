"""The operator's page: is it running, why did it speak, what has it learned.

``GET /`` serves a static page (persona_agent/static/) whose data comes from
``/api/dashboard/...``. Everything is read-only except promote, reject and roll
back, which go through the candidate ledger the way ``personagent learned``
does, rebuild the retrieval views, and record the actor ``dashboard``.

Every request needs the dashboard's own secret, from any client: the cookie
that opening ``/?token=<token>`` sets, or the header
``X-Personagent-Dashboard-Token``. The token lives in
``<runtime>/dashboard.token``; the startup banner and ``personagent doctor``
print the link. A browser must also name a host that a DNS-rebinding page
cannot (localhost, an IP address, or SERVER_HOST). A state-changing call is a
POST that also carries ``X-Personagent-Dashboard: 1`` and, when the browser
sends an Origin, the page's own origin.
"""
from __future__ import annotations

import functools
import hashlib
import html
import ipaddress
import json
import logging
import os
import re
import secrets
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import (HTMLResponse, JSONResponse, PlainTextResponse,
                               RedirectResponse, Response)

from . import (__version__, access, candidates, channels, decision_log,
               evidence, home, lineage, preflight, promotion)
from .config_env import env_bool, env_int
from .paths import ROOT, resolve_runtime_lang_file, runtime_dir
from .storage import atomic_write_text

logger = logging.getLogger("bot")

STATIC_DIR = Path(__file__).resolve().parent / "static"
_ASSETS = {
    "app.js": "text/javascript; charset=utf-8",
    "app.css": "text/css; charset=utf-8",
}
WRITE_HEADER = "x-personagent-dashboard"
TOKEN_HEADER = "x-personagent-dashboard-token"
TOKEN_FILE = "dashboard.token"
ACTOR = "dashboard"
_MAX_BODY = 4096
_STARTED = time.time()
_COOKIE_MAX_AGE = 365 * 86400
# Newest first; the rest of a long list is counted, not sent every poll.
LIST_LIMIT = 50

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


def _refused_page(status: int, code: str, message: str) -> Response:
    """A refusal a person reads in the browser tab: plain text, both languages."""
    text = _PAGE_REFUSALS.get(code)
    body = text() if text else message
    return _harden(PlainTextResponse(body, status_code=status))


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
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            logger.warning("[dashboard] cannot create its token file: %s", exc)
            return ""
        if not _usable(text):
            return ""
    _token = text
    return text


def cookie_name(token: str) -> str:
    # Named per token: two services on one host differ only by port, which
    # cookies ignore, so a shared name would sign one out of the other.
    return "personagent_dashboard_" + hashlib.sha256(token.encode()).hexdigest()[:12]


def link(host: str, port: int) -> str:
    """The URL that opens the dashboard of a service listening on host:port."""
    token = load_token()
    if not token:
        return ""
    value = str(host or "").strip().strip("[]")
    if value in ("", "0.0.0.0"):
        value = "127.0.0.1"
    elif value == "::":
        value = "::1"
    shown = f"[{value}]" if ":" in value else value
    return f"http://{shown}:{port}/?token={token}"


@functools.lru_cache(maxsize=None)
def _cli() -> str:
    """How this install spells `personagent`, for the commands the page names."""
    from .setup_wizard import Launcher
    try:
        return Launcher(python=sys.executable, home=ROOT).shown("")[-1].strip()
    except Exception:
        return "personagent"


_PAGE_REFUSALS = {
    "dashboard_token": lambda: (
        "This dashboard opens only through its private link. Open the dashboard "
        f"link that `{_cli()} run` printed when it started, or run "
        f"`{_cli()} doctor` to print it again.\n\n"
        "这个面板只能通过它的专用链接打开。请打开 "
        f"`{_cli()} run` 启动时打印的面板链接，或者运行 `{_cli()} doctor` 再打印一次。\n"),
    "wrong_token": lambda: (
        "This link's token is not this dashboard's: it may belong to another "
        f"personagent, or the token was replaced. Run `{_cli()} doctor` to print "
        "the current link.\n\n"
        "这个链接里的令牌不属于这个面板：可能是另一个 personagent 的，或者令牌已经换了。"
        f"运行 `{_cli()} doctor` 打印现在的链接。\n"),
    "foreign_host": lambda: (
        "This dashboard opens at localhost, an IP address, or SERVER_HOST, not "
        "at another host name, so that no website can pose as this computer. "
        "Open the link with an IP address, or through an SSH tunnel to "
        "127.0.0.1.\n\n"
        "这个面板只在 localhost、IP 地址或 SERVER_HOST 上打开，不接受别的主机名，"
        "以免有网站冒充这台电脑。请用 IP 地址打开链接，或者通过 SSH 隧道连到 127.0.0.1。\n"),
}


def _host_ok(request: Request) -> bool:
    """A Host a DNS-rebinding page cannot send: localhost, an IP address, or
    the host this service listens on. Such a page always sends its own name."""
    srv = _server()
    raw = request.headers.get("host")
    if not raw:
        return False
    name = srv._host_header_name(raw)
    if name in ("localhost", str(srv._LISTEN["host"]).strip().strip("[]").lower()):
        return True
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return False
    return True


def _same_origin(origin: str, request: Request, by_header: bool) -> bool:
    parts = urlsplit(origin.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return False
    hosts = {request.headers.get("host", "").strip().lower()}
    if by_header:
        # A reverse proxy may rewrite Host; the browser still names the public one.
        hosts.add(request.headers.get("x-forwarded-host", "").strip().lower())
    return parts.netloc.lower() in hosts - {""}


def _problem(request: Request, *, data: bool = True,
             write: bool = False) -> tuple[int, str, str] | None:
    """(status, code, message) for a request the dashboard must not answer."""
    srv = _server()
    expected = load_token()
    supplied = request.headers.get(TOKEN_HEADER)
    if supplied is not None:
        if not expected or not srv._ct_equal(supplied, expected):
            return 403, "wrong_token", "wrong dashboard token"
        by_header = True
    else:
        cookie = request.cookies.get(cookie_name(expected)) if expected else None
        if cookie is None or not srv._ct_equal(cookie, expected):
            return (401, "dashboard_token",
                    "open the dashboard through its link with the token, or "
                    "send X-Personagent-Dashboard-Token")
        if not _host_ok(request):
            return (403, "foreign_host",
                    "open the dashboard by localhost, an IP address or SERVER_HOST")
        by_header = False
    site = request.headers.get("sec-fetch-site", "").strip().lower()
    if data and site in ("cross-site", "same-site"):
        return 403, "cross_site", "cross-site request refused"
    if write:
        if request.headers.get(WRITE_HEADER, "").strip() != "1":
            return (403, "missing_header",
                    "state-changing calls need X-Personagent-Dashboard: 1")
        origin = request.headers.get("origin")
        if origin is not None and not _same_origin(origin, request, by_header):
            return 403, "foreign_origin", "cross-origin request refused"
        ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return 415, "unsupported_media_type", "send application/json"
    return None


def _check(request: Request, *, data: bool = True,
           write: bool = False) -> Response | None:
    """The refusal for a request the dashboard must not answer, else None."""
    problem = _problem(request, data=data, write=write)
    return None if problem is None else _refused(*problem)


def _sign_in(request: Request, supplied: str) -> Response:
    """Trade the link's token for a cookie, and take the token out of the address bar."""
    expected = load_token()
    if not _host_ok(request):
        return _refused_page(403, "foreign_host", "")
    if not expected or not _server()._ct_equal(supplied, expected):
        return _refused_page(403, "wrong_token", "")
    rest = [(k, v) for k, v in request.query_params.multi_items() if k != "token"]
    target = "./" + (f"?{urlencode(rest)}" if rest else "")
    if request.headers.get("sec-fetch-site", "").strip().lower() == "cross-site":
        # A Strict cookie rides no request of a chain another site started,
        # a 303's included; a refresh from this page starts a new one.
        response: Response = HTMLResponse(
            '<!doctype html><meta charset="utf-8">'
            f'<meta http-equiv="refresh" content="0; url={html.escape(target)}">'
            f'<a href="{html.escape(target)}">personagent</a>')
    else:
        response = RedirectResponse(target, status_code=303)
    response.set_cookie(cookie_name(expected), expected, max_age=_COOKIE_MAX_AGE,
                        path="/", httponly=True, samesite="strict",
                        secure=request.url.scheme == "https")
    return _harden(response, _PAGE_CSP)


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


_URL_USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^\s/?#@]+@")
_URL_QUERY = re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://[^\s?#]*)\?[^\s#)]*")


def _redact_urls(text: str) -> str:
    """A URL's user:password@ and ?query, where a credential may hide."""
    return _URL_QUERY.sub(r"\1?***", _URL_USERINFO.sub(r"\1***@", str(text or "")))


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
        findings = [{"level": f.level, "key": f.key, "detail": _redact_urls(f.detail)}
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
        "cli": _cli(),
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


class _Index:
    """Events and candidates by reply text, built once per request, so each
    proposal reads only its own instead of the whole log."""

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
        ids = {eid for eid in cand.get("evidence") or [] if eid in self.by_id}
        return [self.by_id[eid] for eid in sorted(ids, key=self._pos.__getitem__)]

    def related(self, cand: dict) -> list[dict]:
        # Narrowed by text, then still filtered by promotion's own rule.
        texts = {str(cand.get("reply") or "").strip(),
                 str(cand.get("better") or "").strip()}
        hits = sorted(i for text in texts for i in self._by_text.get(text, ()))
        return promotion.related_events(cand, [self.events[i] for i in hits])

    def peers(self, cand: dict) -> list[dict]:
        """The only candidates find_conflicts can match: same reply text."""
        return self._peers.get(str(cand.get("reply") or ""), [])


def _active_rivals(cand: dict, peers: list[dict], policy) -> list[dict]:
    """Other rewrites of the same reply already in use: one reply never has
    two active rewrites, so promoting `cand` must replace them."""
    ids = set(promotion.find_conflicts(cand, peers, policy=policy))
    return [p for p in peers if p.get("candidate_id") in ids
            and p.get("state") == candidates.STATE_PROMOTED]


def _checklist(cand: dict, learning: _Learning, index: _Index, now: float) -> dict:
    """Each promotion rule, passed or not, in the order `promotion.decide`
    applies them; the verdict itself is `decide`'s."""
    policy = learning.policy
    linked = index.linked(cand)
    related = index.related(cand)
    peers = index.peers(cand)
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


def _candidate_view(cand: dict, learning: _Learning, index: _Index,
                    now: float) -> dict:
    by_id = index.by_id
    actions = _allowed_actions(cand.get("state", ""))
    rivals = (_active_rivals(cand, index.peers(cand), learning.policy)
              if "promote" in actions else [])
    if rivals:
        actions = ["replace" if a == "promote" else a for a in actions]
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
        "actions": actions,
        "replaces": [{"id": r.get("candidate_id", ""), "better": _clip(r.get("better"), 300)}
                     for r in rivals],
        "superseded_by": cand.get("superseded_by", ""),
        "supersedes": cand.get("supersedes", ""),
    }
    if cand.get("state") == candidates.STATE_PROPOSED:
        view["checklist"] = _checklist(cand, learning, index, now)
    return view


def conversation_payload(agent, conv_id: str) -> dict:
    learning = _Learning(agent)
    learning_key = channels.learning_key(conv_id)
    peers = learning.ledger.all()
    index = _Index(learning.log.all(), peers)
    now = time.time()
    mine = [c for c in peers
            if str((c.get("scope") or {}).get("conv_id") or "") == learning_key]
    mine.sort(key=lambda c: str(c.get("created_at") or ""), reverse=True)
    groups = {"pending": [], "learned": [], "past": []}
    totals = dict.fromkeys(groups, 0)
    for cand in mine:
        state = cand.get("state")
        group = ("pending" if state == candidates.STATE_PROPOSED
                 else "learned" if state == candidates.STATE_PROMOTED else "past")
        totals[group] += 1
        if len(groups[group]) < LIST_LIMIT:
            groups[group].append(_candidate_view(cand, learning, index, now))
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
        "totals": totals,
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
        # More than one rival means the ledger predates the one-live-rewrite
        # rule; retire the rest too.
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

def _asset(name: str, content_type: str, csp: str = _DATA_CSP) -> Response:
    try:
        body = (STATIC_DIR / name).read_bytes()
    except OSError:
        return _refused(404, "not_found", "not found")
    return _harden(Response(body, media_type=content_type), csp)


@router.get("/", include_in_schema=False)
async def dashboard_page(request: Request, token: str | None = None):
    if token is not None:
        return _sign_in(request, token)
    problem = _problem(request, data=False)
    if problem is not None:
        return _refused_page(*problem)
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
