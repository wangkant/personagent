"""FastAPI HTTP layer for the QQ persona agent."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(override=False)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect

from persona_agent import __version__, preflight
from persona_agent.agent import Agent
from persona_agent.config_env import env_bool, env_int, env_str
from persona_agent.gateway import CONVERSATION_TYPES, EVENT_KIND
from persona_agent.health import run_checks, all_critical_ok
from persona_agent.outbox import parse_pull
from persona_agent.paths import ROOT, runtime_dir
from persona_agent.settings import AgentSettings
from persona_agent.storage import RuntimeInstanceLock, atomic_write_text


class RollingLogThatSurvivesAFailedRotation(RotatingFileHandler):
    """A rollover that cannot happen must not eat the log line.

    Windows refuses `os.rename` on a file another handle holds open, and a
    second uvicorn is a normal state here — killing one does not always take.
    `RotatingFileHandler.emit` calls `doRollover` INSIDE its own try, so a
    failed rotation is not "rotation skipped", it is `handleError`: the record
    is never written. The log would start losing exactly the lines it exists
    to keep, at the moment the file grew big enough to be worth rotating.

    Downgraded to a rollover that did not happen — the current file stays open
    and grows past `maxBytes` until some later attempt succeeds. An oversized
    log is a nuisance; a missing one is why anyone set SERVER_LOG_FILE.
    """

    def doRollover(self) -> None:
        try:
            super().doRollover()
        except OSError:
            # Reopen if the base class closed the stream before it failed, or
            # every subsequent emit writes to a dead handle.
            if self.stream is None:
                self.stream = self._open()

    def _open(self):
        # A rollover recreates the base file through _open, which uses the
        # process umask: the one-time chmod at setup left bot.log and every
        # backup world-readable after the first rotation. These lines hold
        # message excerpts and user ids, so every file this opens is 0600.
        stream = super()._open()
        if os.name != "nt":
            try:
                os.chmod(self.baseFilename, 0o600)
            except OSError:
                pass
        return stream


def _is_loopback_host(host: str) -> bool:
    value = str(host or "").strip().strip("[]")
    if value.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def _validate_exposure_config(
    host: str,
    onebot_secret: str,
    connector_token: str,
) -> None:
    """Refuse a network bind whose two event endpoints are not authenticated."""
    if _is_loopback_host(host):
        return
    missing = []
    if not onebot_secret:
        missing.append("QQ_ONEBOT_SECRET")
    if not connector_token:
        missing.append("CONNECTOR_TOKEN")
    if missing:
        raise ValueError(
            f"SERVER_HOST={host!r} is not loopback; set {', '.join(missing)} "
            "before exposing the event endpoints"
        )


def _request_peer_is_allowed(peer_host: str | None, credential: str) -> bool:
    """Fail closed when an unauthenticated endpoint is reached off-host."""
    return bool(credential) or _is_loopback_host(peer_host or "")


_LOCAL_HOST_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})
_PROXY_HEADERS = ("x-forwarded-for", "forwarded", "x-real-ip",
                  "cf-connecting-ip")
_NON_LOCAL_WARNED: set[str] = set()


def _host_header_name(host: str) -> str:
    """The hostname of a Host header: port stripped, IPv6 brackets handled."""
    value = host.strip().lower()
    if value.startswith("["):
        return value[1:].split("]", 1)[0]
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def _credentialless_request_is_local(request) -> tuple[bool, str]:
    """Whether a request to an endpoint with no credential set really comes
    from a local program, and if not, which header gave it away.

    A loopback peer is not enough. A text/plain POST is a CORS "simple
    request", so any page the operator opens can send one to 127.0.0.1 with
    no preflight and forge an event as the admin; DNS rebinding lets such a
    page read the replies too; and a tunnel (cloudflared, frp, nginx) on the
    same host forwards the whole internet from 127.0.0.1. Each of those
    leaves a header that NapCat and the AstrBot plugin never send.
    """
    headers = request.headers
    reason = ""
    if "origin" in headers:
        reason = "origin"
    elif headers.get("sec-fetch-site", "none").strip().lower() != "none":
        reason = "sec-fetch-site"
    elif "host" in headers and _host_header_name(
            headers["host"]) not in _LOCAL_HOST_NAMES:
        reason = "host"
    elif any(name in headers for name in _PROXY_HEADERS):
        reason = "forwarded"
    if not reason:
        return True, ""
    if reason not in _NON_LOCAL_WARNED:
        _NON_LOCAL_WARNED.add(reason)
        logger.warning(
            "[main] refused a request to %s with no credential configured: "
            "its %s header says it came from a browser, another host name or "
            "a proxy. Local programs should call http://127.0.0.1; anything "
            "else needs QQ_ONEBOT_SECRET / CONNECTOR_TOKEN set",
            request.url.path, reason)
    return False, reason


def _refuse_non_local(request, credential: str) -> JSONResponse | None:
    """The 403 for a credentialless endpoint reached by a non-local request."""
    if credential:
        return None
    local, _reason = _credentialless_request_is_local(request)
    if local:
        return None
    return _error(403, "non_local_request",
                  "no credential is configured; only local requests accepted")


def _ct_equal(supplied: str, expected: str) -> bool:
    """Constant-time compare of a header value against a configured secret.

    `hmac.compare_digest` raises TypeError on a non-ASCII str, and Starlette
    decodes header bytes as latin-1, so one `\\xff` in a header turned an
    unauthenticated request into a 500 with a traceback. Comparing bytes
    also lets a non-ASCII secret work: latin-1 gives back the exact bytes the
    client sent, which are the UTF-8 of the secret it was configured with.
    """
    return hmac.compare_digest(
        str(supplied or "").encode("latin-1", "replace"),
        str(expected or "").encode("utf-8"))


# ========== Config ==========
# The HTTP layer's own settings. Everything the AGENT is configured with lives
# in `AgentSettings` and is read once, in `lifespan` — this file no longer
# copies thirty settings from a module global into a keyword argument, which is
# where a new knob used to get lost.
#
# Bind loopback by default: NapCat posts events from localhost
# (QQ_ONEBOT_URL=http://127.0.0.1:3000), so the webhook never needs to be
# world-exposed. Set SERVER_HOST=0.0.0.0 only for a split deployment, and then set
# QQ_ONEBOT_SECRET so forged OneBot payloads (impersonating the admin, poisoning
# memory, burning tokens) can't reach /v1/onebot.
SERVER_HOST = env_str("SERVER_HOST", "127.0.0.1")
SERVER_PORT = env_int("SERVER_PORT", 8080, minimum=1, maximum=65535)
# Optional OneBot HMAC secret (NapCat httpClient `secret`). When set, every
# /v1/onebot body must carry a matching `x-signature: sha1=<hex>` header.
QQ_ONEBOT_SECRET = env_str("QQ_ONEBOT_SECRET")
SERVER_MAX_BODY_BYTES = env_int(
    "SERVER_MAX_BODY_BYTES", 8_000_000, minimum=1, maximum=64_000_000)
# uvicorn has no body-read timeout, and a webhook holds an admission slot
# while it reads. Without a deadline, a peer that sends a Content-Length and
# then one byte keeps that slot forever, and a few of them 429 every real
# event. A connector on the same host sends its body in milliseconds.
BODY_READ_TIMEOUT_S = 30
QQ_ONEBOT_MAX_INFLIGHT = env_int(
    "QQ_ONEBOT_MAX_INFLIGHT", 64, minimum=1, maximum=4096)
# A SEPARATE budget, because the two endpoints hold their slot for wildly
# different spans. /v1/onebot hands its slot to a background task within
# milliseconds; /v1/events answers synchronously and holds one for the
# entire turn (~12s, see transport.py). Sharing one counter meant a burst of
# connector turns 429'd the cheap, non-blocking OneBot webhooks alongside them.
# Defaults to QQ_ONEBOT_MAX_INFLIGHT, so an existing deployment keeps its
# capacity and a blank line in .env means "same as above" — what changes is
# that the two can no longer starve each other.
CONNECTOR_MAX_INFLIGHT = env_int(
    "CONNECTOR_MAX_INFLIGHT", QQ_ONEBOT_MAX_INFLIGHT, minimum=1, maximum=4096)
# The outbox's own budget: a long-poll holds its slot for up to 30 s while
# costing nothing, so it must never take a slot a turn needs. One pull per
# connector is the normal load.
MAX_INFLIGHT_OUTBOX = 16
# Whether to build the agent at all. Off leaves the HTTP layer answering
# health checks and accepting (then dropping) events.
AGENT_ENABLED = env_bool("AGENT_ENABLED", True)
# Connectors: shared secret for /v1/events and /v1/outbox (blank = no auth),
# and how old a forwarded event may be before it is refused.
CONNECTOR_TOKEN = env_str("CONNECTOR_TOKEN")
CONNECTOR_MAX_EVENT_AGE_S = env_int(
    "CONNECTOR_MAX_EVENT_AGE_S", 86_400, minimum=1, maximum=604_800)

# ========== Logging ==========
logger = logging.getLogger("bot")


def _configure_logging() -> None:
    """Configure process logging at startup, never as an import side effect."""
    root = logging.getLogger()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    if not root.handlers:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        root.addHandler(stream)
    root.setLevel(logging.INFO)

    # Conversation-adjacent logs are console-only by default. Operators who
    # explicitly opt into a file must choose its protected runtime path.
    log_file = os.getenv("SERVER_LOG_FILE", "").strip()
    if not log_file:
        return
    try:
        target = Path(log_file).expanduser().resolve()
        if any(
            isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename).resolve() == target
            for handler in root.handlers
        ):
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RollingLogThatSurvivesAFailedRotation(
            str(target), maxBytes=5_000_000, backupCount=3, encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
    except Exception:
        logger.exception("file logging setup failed")


agent: Optional[Agent] = None

# Strong refs to fire-and-forget tasks. asyncio keeps only a weak reference to
# a task, so one suspended at an await with no other reference can be garbage
# collected mid-flight, silently dropping the work (e.g. an inbound message).
_bg_tasks: set[asyncio.Task] = set()


class AdmissionLimiter:
    """Small non-blocking admission counter for expensive webhook work."""

    def __init__(self, limit: int) -> None:
        self.limit = max(1, int(limit))
        self.inflight = 0
        self._lock = asyncio.Lock()

    async def try_acquire(self) -> bool:
        async with self._lock:
            if self.inflight >= self.limit:
                return False
            self.inflight += 1
            return True

    async def release(self) -> None:
        async with self._lock:
            if self.inflight:
                self.inflight -= 1


class ReplayGuard:
    """Bounded timestamped nonce cache for authenticated connector envelopes."""

    def __init__(
        self,
        ttl_seconds: int = 300,
        max_entries: int = 4096,
        state_file: str | Path | None = None,
    ) -> None:
        self.ttl_seconds = max(1, int(ttl_seconds))
        self.max_entries = max(1, int(max_entries))
        self.state_file = Path(state_file) if state_file is not None else None
        self._seen: dict[str, int] = self._load()

    def _load(self) -> dict[str, int]:
        if self.state_file is None:
            return {}
        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError, TypeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        loaded: dict[str, int] = {}
        for nonce, timestamp in raw.items():
            if not isinstance(nonce, str) or not nonce or len(nonce) > 128:
                continue
            try:
                loaded[nonce] = int(timestamp)
            except (TypeError, ValueError, OverflowError):
                continue
        return loaded

    def _persist(self) -> None:
        if self.state_file is None:
            return
        atomic_write_text(
            self.state_file,
            json.dumps(
                self._seen, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ) + "\n",
        )

    def accept(self, nonce: str, timestamp: int, now: int) -> bool:
        cutoff = now - self.ttl_seconds
        pruned = {
            key: stamp for key, stamp in self._seen.items()
            if stamp >= cutoff
        }
        changed = len(pruned) != len(self._seen)
        self._seen = pruned
        if abs(now - timestamp) > self.ttl_seconds or nonce in self._seen:
            if changed:
                self._persist()
            return False
        if len(self._seen) >= self.max_entries:
            # Evicting a still-fresh nonce re-opens its replay window, so the
            # cap is a hard refusal — which means a busy connector can hit a
            # cliff where EVERY connector request 403s as "replayed", and that
            # is indistinguishable from a bad token unless it is said out loud.
            logger.error(
                "[main] connector replay guard full (%d nonces live within %ds) "
                "— rejecting all connector requests until the window drains; "
                "raise the cap if this is legitimate traffic",
                len(self._seen), self.ttl_seconds)
            if changed:
                self._persist()
            return False
        if len(self._seen) >= self.max_entries * 4 // 5:
            logger.warning(
                "[main] connector replay guard at %d/%d nonces",
                len(self._seen), self.max_entries)
        self._seen[nonce] = timestamp
        try:
            self._persist()
        except Exception:
            # Un-burn it. The caller is about to get a 500 and retry with the
            # SAME nonce (correct client behaviour), and a nonce left burned
            # by a failed write turns one transient disk error — on Windows,
            # an AV or indexer holding the destination across os.replace —
            # into a message that can never be delivered at all.
            self._seen.pop(nonce, None)
            raise
        return True


def _verify_envelope(
    body: bytes,
    headers,
    token: str,
    *,
    now: int | None = None,
    replay_guard: ReplayGuard | None = None,
) -> bool:
    """Verify bearer token plus HMAC-signed timestamp/nonce/body envelope."""
    if not token:
        return True
    supplied_token = headers.get("x-personagent-token", "")
    timestamp_raw = headers.get("x-personagent-timestamp", "")
    nonce = headers.get("x-personagent-nonce", "")
    supplied_signature = headers.get("x-personagent-signature", "")
    if (not _ct_equal(supplied_token, token)
            or not timestamp_raw or not nonce or len(nonce) > 128):
        return False
    try:
        timestamp = int(timestamp_raw)
    except (TypeError, ValueError):
        return False
    mac_input = (
        str(timestamp).encode("ascii") + b"."
        + nonce.encode("utf-8") + b"." + body
    )
    expected = "sha256=" + hmac.new(
        token.encode("utf-8"), mac_input, hashlib.sha256).hexdigest()
    if not _ct_equal(supplied_signature, expected):
        return False
    guard = replay_guard or _connector_replay
    return guard.accept(nonce, timestamp, int(time.time()) if now is None else now)


def _validate_event_payload(payload: dict, *, connector: bool) -> bool:
    """Validate the stable identity fields required for deduplication."""
    if not isinstance(payload, dict):
        return False
    if connector:
        required = (
            "platform", "conversation_type", "sender_id", "message_id",
            "sent_at",
        )
        if any(payload.get(key) in (None, "") for key in required):
            return False
        if payload.get("conversation_type") not in CONVERSATION_TYPES:
            return False
        if payload.get("conversation_type") == "group" and payload.get(
                "conversation_id") in (None, ""):
            return False
        return isinstance(payload.get("segments", []), list)
    if payload.get("post_type") != "message":
        return True
    required = ("message_type", "user_id", "message_id")
    if any(payload.get(key) in (None, "") for key in required):
        return False
    if payload.get("message_type") == "group" and payload.get(
            "group_id") in (None, ""):
        return False
    return isinstance(payload.get("message", []), list)


def _event_is_fresh(
    payload: dict,
    key: str,
    *,
    now: int | None,
    max_age_seconds: int,
) -> bool:
    try:
        event_time = int(payload.get(key))
    except (TypeError, ValueError, OverflowError):
        return False
    current = int(time.time()) if now is None else int(now)
    return abs(current - event_time) <= max(1, int(max_age_seconds))


def _connector_event_is_fresh(
    payload: dict,
    *,
    now: int | None = None,
    max_age_seconds: int = CONNECTOR_MAX_EVENT_AGE_S,
) -> bool:
    """Validate the event's own age independently of the envelope's."""
    return _event_is_fresh(payload, "sent_at", now=now,
                           max_age_seconds=max_age_seconds)


def _onebot_event_is_fresh(
    payload: dict,
    *,
    now: int | None = None,
    max_age_seconds: int = 300,
) -> bool:
    """Reject stale signed OneBot events before their IDs age out of dedup."""
    return _event_is_fresh(payload, "time", now=now,
                           max_age_seconds=max_age_seconds)


_onebot_admission = AdmissionLimiter(QQ_ONEBOT_MAX_INFLIGHT)
_connector_admission = AdmissionLimiter(CONNECTOR_MAX_INFLIGHT)
_outbox_admission = AdmissionLimiter(MAX_INFLIGHT_OUTBOX)
# A file name from a released version: the nonces in it stay valid.
_connector_replay = ReplayGuard(
    state_file=runtime_dir() / "gateway_nonces.json")


class RequestBodyTooLarge(Exception):
    """Raised when a webhook body exceeds the configured byte limit."""


def _error(status: int, code: str, message: str, *,
           retry_after: int | None = None) -> JSONResponse:
    """One shape for every error this service returns.

    `error` stays exactly what it was — a sentence for a human reading a log.
    `code` is the stable half, and it exists because the prose is not
    actionable: `/v1/events` alone answers 403 for a peer that is not
    allowed, an envelope that failed verification, and an event that is
    too old, and the operator's next step differs for each (fix the
    allowlist / rotate the token / fix NTP). A client cannot branch on an
    English sentence, and the sentences are free to be reworded.

    `code` values are contract. Add one rather than repurposing one.
    """
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return JSONResponse(status_code=status,
                        content={"error": message, "code": code},
                        headers=headers)


def _mark_deprecated(response: JSONResponse) -> JSONResponse:
    """Stamp a response from the deprecated `/v1/onebot` ingress.

    Applied at every return point rather than only the success one, so a
    branch added later cannot silently omit it. No `Sunset`: the CHANGELOG
    and the startup warning both say "a later release" and no date has been
    chosen — emitting one would invent a deadline the project has not set.
    """
    response.headers["Deprecation"] = "true"
    return response


async def _read_body_limited(request: Request, limit: int) -> bytes:
    """Read a request body without buffering more than ``limit`` bytes."""
    raw_length = request.headers.get("content-length", "")
    try:
        if raw_length and int(raw_length) > limit:
            raise RequestBodyTooLarge
    except ValueError:
        pass
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > limit:
            raise RequestBodyTooLarge
        body.extend(chunk)
    return bytes(body)


async def _read_webhook_body(request: Request) -> bytes | JSONResponse:
    """The body under both the size cap and a deadline, or the error to send.

    A client that hangs up mid-body is not a server fault: Starlette raises
    ClientDisconnect, which used to escape as an ASGI traceback per
    connection. Nobody is left to read the 400; it only keeps the log quiet.
    """
    try:
        return await asyncio.wait_for(
            _read_body_limited(request, SERVER_MAX_BODY_BYTES),
            BODY_READ_TIMEOUT_S)
    except RequestBodyTooLarge:
        return _error(413, "body_too_large", "request body too large")
    except asyncio.TimeoutError:
        return _error(408, "body_timeout", "request body not received in time")
    except ClientDisconnect:
        return _error(400, "client_disconnected", "client disconnected")


def _on_bg_task_done(task: asyncio.Task) -> None:
    """Discard the strong ref AND retrieve the exception.

    `_bg_tasks.discard` alone never touched `.exception()`, so a crash in one
    of the lifespan one-shots (`probe_models`, `bootstrap_tag_all`,
    `_recheck_then_purge` — the last has no internal guard of its own)
    surfaced only as a context-free "Task exception was never retrieved" at
    GC time, if at all. `_safe_handle` already logs its own; this is the same
    courtesy for everything else that goes through `_spawn`."""
    _bg_tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("[main] background task %s crashed: %s: %s",
                     task.get_name(), type(exc).__name__, exc, exc_info=exc)


def _spawn(coro) -> asyncio.Task:
    """create_task + retain a strong ref until the task finishes."""
    t = asyncio.create_task(coro)
    _bg_tasks.add(t)
    t.add_done_callback(_on_bg_task_done)
    return t


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    _configure_logging()
    # Before anything is wired up, say what the configuration gets wrong —
    # above all a MISSPELLED key, which is otherwise completely silent: the
    # value is ignored, the default is used, and the bot runs and misbehaves.
    # Reported, never fatal: a deployment that is 90% configured should start
    # and tell you about the other 10%.
    preflight.log_findings(preflight.check_config())
    _validate_exposure_config(SERVER_HOST, QQ_ONEBOT_SECRET, CONNECTOR_TOKEN)
    runtime_lock = None
    if AGENT_ENABLED:
        # Agent construction reads legacy root-level state as well as runtime
        # projections, so claim the deployment before touching either.
        runtime_lock = RuntimeInstanceLock(ROOT)
        runtime_lock.acquire()
        try:
            agent = Agent(AgentSettings.from_env())
            # The append-only ledger is authoritative. Repair stale derived
            # retrieval views before the server can accept a request.
            agent._rebuild_promoted_views(strict=True)
        except BaseException:
            runtime_lock.release()
            runtime_lock = None
            raise
        _spawn(agent.probe_models())
        _spawn(agent.check_missed_mentions())
        _spawn(agent.loop_check_missed())
        _spawn(agent.loop_proactive())  # self-guards on PROACTIVE_ENABLED
        _spawn(agent.loop_evolve())     # self-guards on EVOLVE_AUTO_ENABLED
        _spawn(agent.stickers.bootstrap_tag_all())

        async def _recheck_then_purge():
            # First pass: text-based persona-fit (LLM judges from
            # meaning/tags inferred from usage context — fast, no vision).
            # Second pass: vision-based aesthetic (judges from pixels, catches
            # what text can't — e.g. gaudy-design stickers that score the
            # right "smug" emotion in context).
            # Both passes use a version stamp on each entry so bumping the
            # respective version constant re-judges the whole library.
            n = await agent.stickers.recheck_persona_fit_all()
            if n:
                agent.stickers.purge_unfit()
            m = await agent.visual_recheck_aesthetic_all()
            if m:
                agent.stickers.purge_unfit()
        _spawn(_recheck_then_purge())
    logger.info("bot started on %s:%d (agent=%s, lang=%s)", SERVER_HOST, SERVER_PORT,
                agent.enabled if agent else False,
                agent.agent_lang if agent else "-")
    try:
        yield
    finally:
        # ---- shutdown: cancel background loops + force out throttled writes
        # so buffered state isn't lost ----
        tasks = list(_bg_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if agent is not None:
            try:
                close = getattr(agent, "aclose", None)
                if close is not None:
                    await close()
                else:
                    agent.flush_state()
            except Exception:
                logger.exception("shutdown cleanup failed")
        if runtime_lock is not None:
            runtime_lock.release()

app = FastAPI(title="personagent", version=__version__, lifespan=lifespan)


# /health caches its probe results briefly so monitoring polls don't spam the
# upstream APIs (each full probe spends a few tokens + 1 search credit).
_health_cache: dict = {"ts": 0.0, "data": None}
_health_lock = asyncio.Lock()


@app.get("/health")
async def health():
    """Cheap public liveness check; never spends upstream API credits."""
    return {
        "status": "ok",
        "agent_enabled": bool(agent and agent.enabled),
    }


@app.get("/health/details")
async def health_details(request: Request):
    """Authenticated/loopback-only diagnostics that may call paid services."""
    client_host = request.client.host if request.client else ""
    if CONNECTOR_TOKEN:
        authorized = _ct_equal(
            request.headers.get("X-Personagent-Token", ""), CONNECTOR_TOKEN)
    else:
        authorized = _is_loopback_host(client_host)
    if not authorized:
        return _error(403, "forbidden", "forbidden")
    refused = _refuse_non_local(request, CONNECTOR_TOKEN)
    if refused is not None:
        return refused

    now = time.time()
    if _health_cache["data"] is None or now - _health_cache["ts"] > 60:
        async with _health_lock:
            # Re-check inside the lock: a concurrent poll may have just
            # refreshed the cache, so we don't fan out duplicate probes
            # (each full probe spends tokens + a search credit).
            now = time.time()
            if _health_cache["data"] is None or now - _health_cache["ts"] > 60:
                # Probes do blocking HTTP; run them off the event loop.
                _health_cache["data"] = await asyncio.to_thread(run_checks)
                _health_cache["ts"] = now
    results = _health_cache["data"]
    ok = all_critical_ok(results)
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ok" if ok else "degraded",
            "agent_enabled": bool(agent and agent.enabled),
            "services": results,
        },
    )

_DIRECT_ROUTE_WARNED = False


def _warn_direct_route_once() -> None:
    global _DIRECT_ROUTE_WARNED
    if not _DIRECT_ROUTE_WARNED:
        _DIRECT_ROUTE_WARNED = True
        logger.warning(
            "[Agent] /v1/onebot (direct OneBot ingress) is deprecated since 0.3.0 and "
            "will be removed in a later release; route QQ through AstrBot with "
            "CONNECTOR_QQ_PLATFORMS=aiocqhttp. Nothing changes for this deployment yet.")


@app.post("/v1/onebot")
async def onebot_webhook(request: Request):
    """DEPRECATED direct OneBot v11 ingress, fed by the client's own webhook.

    Fire-and-forget: the event is validated, then handled on a background task
    so NapCat never waits for the model round-trip. The reply is delivered by
    a separate call to the OneBot HTTP API, so the response here is only
    ``{"ok": true}`` and never carries it. That is the opposite of
    ``/v1/events``, which answers synchronously.

    Deprecated since 0.3.0, removed in a later release; every response carries
    ``Deprecation: true``. The supported path is AstrBot with
    ``CONNECTOR_QQ_PLATFORMS=aiocqhttp``. Set ``QQ_ONEBOT_SECRET`` so NapCat
    signs the body as ``x-signature: sha1=...`` — without it, anyone who can
    reach this port can forge an event.
    """
    _warn_direct_route_once()
    # Refuse before admission, so a peer that may not call this at all cannot
    # hold a slot. The signature covers the body and has to wait for it.
    peer = request.client.host if request.client is not None else ""
    if not _request_peer_is_allowed(peer, QQ_ONEBOT_SECRET):
        return _mark_deprecated(_error(
            403, "unauthenticated", "authentication required"))
    refused = _refuse_non_local(request, QQ_ONEBOT_SECRET)
    if refused is not None:
        return _mark_deprecated(refused)
    if not await _onebot_admission.try_acquire():
        return _mark_deprecated(_error(
            429, "capacity_exceeded", "webhook capacity exceeded",
            retry_after=1))
    request.state.admission_handed_off = False
    try:
        return _mark_deprecated(await _onebot_webhook_admitted(request))
    finally:
        if not request.state.admission_handed_off:
            await _onebot_admission.release()


async def _onebot_webhook_admitted(request: Request):
    body = await _read_webhook_body(request)
    if isinstance(body, JSONResponse):
        return body
    # OneBot HMAC verification (opt-in via QQ_ONEBOT_SECRET). Without it, anyone
    # who can reach this port can POST a forged event — impersonate the admin,
    # poison memory, drive sends. NapCat signs the body as `x-signature: sha1=…`
    # when its httpClient `secret` is set; configure both or leave unset (and
    # keep SERVER_HOST=127.0.0.1).
    if QQ_ONEBOT_SECRET:
        sig = request.headers.get("x-signature", "")
        expected = "sha1=" + hmac.new(QQ_ONEBOT_SECRET.encode(), body, hashlib.sha1).hexdigest()
        if not _ct_equal(sig, expected):
            logger.warning("webhook rejected: bad/absent x-signature")
            return _error(403, "bad_signature", "bad signature")
    try:
        payload = json.loads(body or b"{}")
    except Exception:
        payload = {}
    # Defense in depth: these keys mark payloads synthesized inside
    # handle_gateway and must never arrive from the network. Security
    # decisions gate on the sink contextvar, but strip them anyway so an
    # external body can't masquerade as a connector event.
    if isinstance(payload, dict):
        payload.pop("_gateway", None)
        payload.pop("_platform", None)
    if not _validate_event_payload(payload, connector=False):
        return _error(400, "invalid_schema", "invalid event schema")
    if QQ_ONEBOT_SECRET and not _onebot_event_is_fresh(payload):
        return _error(403, "stale_event", "stale or missing event timestamp")
    if isinstance(payload, dict) and payload.get("message_id") not in (None, ""):
        payload["message_id"] = str(payload["message_id"])
    if agent:
        # Non-blocking: don't make NapCat wait for the LLM round-trip.
        # Wrap in a guard so a raised exception is logged instead of vanishing
        # as an unretrieved-task warning.
        async def _safe_handle():
            try:
                await agent.handle(payload)
            except Exception:
                logger.exception("handle failed")
            finally:
                await _onebot_admission.release()
        request.state.admission_handed_off = True
        _spawn(_safe_handle())
    # A JSONResponse rather than a bare dict so _mark_deprecated has something
    # to stamp; the serialized body is byte-identical.
    return JSONResponse(content={"ok": True})


_IGNORED_TOKEN_WARNED = False


def _warn_ignored_connector_token_once(request: Request) -> None:
    """The connector has a token this process was not given: its envelope is
    not being checked at all, which is rarely what the operator meant."""
    global _IGNORED_TOKEN_WARNED
    if (CONNECTOR_TOKEN or _IGNORED_TOKEN_WARNED
            or "x-personagent-token" not in request.headers):
        return
    _IGNORED_TOKEN_WARNED = True
    logger.warning(
        "[main] the connector sends X-Personagent-Token but CONNECTOR_TOKEN is "
        "blank here, so the token is ignored; set the same CONNECTOR_TOKEN "
        "in .env to have connector requests authenticated")


@app.post("/v1/events")
async def connector_events(request: Request):
    """Platform-neutral inbound endpoint for connectors.

    SYNCHRONOUS round-trip, unlike ``/v1/onebot``: the connector needs the
    replies in the response body to relay them to the source platform, so the
    whole pipeline, debounce and every model call included, runs before this
    returns (the typing pauses are skipped behind the sink). Set the
    connector's HTTP timeout accordingly; a caller that gives up early does
    not stop the turn, which still commits its reply and everything it
    learned from it.

    Body schema: see ``persona_agent/gateway.py``. The response is
    ``{"handled": bool, "owned": bool, "replies": [...]}``, where ``owned``
    says the conversation is this persona's whether or not it chose to speak —
    a connector should suppress its own model on ``owned``, never on whether
    ``replies`` is empty, because silence is frequently the answer.

    Authentication is a bearer token plus an HMAC envelope over
    timestamp/nonce/body (``X-Personagent-Token``, ``-Timestamp``, ``-Nonce``,
    ``-Signature``). Errors carry a stable ``code``; branch on it, not on the
    prose in ``error``.
    """
    # Everything that needs no body is checked before admission: a caller
    # without the token must not be able to hold one of the slots a real
    # turn needs. The signature, nonce and replay checks still run after it,
    # so a 429 never burns a nonce.
    peer = request.client.host if request.client is not None else ""
    if not _request_peer_is_allowed(peer, CONNECTOR_TOKEN):
        return _error(403, "unauthenticated", "authentication required")
    refused = _refuse_non_local(request, CONNECTOR_TOKEN)
    if refused is not None:
        return refused
    _warn_ignored_connector_token_once(request)
    if CONNECTOR_TOKEN and not _ct_equal(
            request.headers.get("x-personagent-token", ""), CONNECTOR_TOKEN):
        return _error(403, "invalid_envelope",
                      "invalid, stale, or replayed request envelope")
    if not await _connector_admission.try_acquire():
        return _error(429, "capacity_exceeded", "webhook capacity exceeded",
                      retry_after=3)
    try:
        return await _connector_events_admitted(request)
    finally:
        await _connector_admission.release()


async def _connector_events_admitted(request: Request):
    """Platform-neutral inbound endpoint for connectors (schema in
    gateway.py). Unlike /v1/onebot this is a synchronous round-trip: the
    connector needs the replies in the response body to relay them back, so
    the full handle pipeline (debounce + typing simulation included) runs
    before returning — set the connector's HTTP timeout accordingly."""
    body = await _read_webhook_body(request)
    if isinstance(body, JSONResponse):
        return body
    if not _verify_envelope(body, request.headers, CONNECTOR_TOKEN):
        # One code for four causes (bad token, bad signature, timestamp
        # outside the window, replayed nonce): _verify_envelope folds
        # them into a bool before this sees them, and splitting that return is
        # a bigger change than this one — its True/False contract is pinned by
        # tests. `invalid_envelope` at least separates these from the other
        # two 403s this route can answer.
        return _error(403, "invalid_envelope",
                      "invalid, stale, or replayed request envelope")
    try:
        event = json.loads(body or b"{}")
    except Exception:
        event = {}
    if not isinstance(event, dict):
        # A body that parses to JSON null/list/string would otherwise hit
        # event.get(...) in synthesize_onebot_payload and 500.
        event = {}
    if event.get("kind", EVENT_KIND) != EVENT_KIND:
        # The signature does not cover the path: a signed outbox pull posted
        # here must not be read as an event.
        return _error(400, "invalid_schema", "not an event body")
    if not _validate_event_payload(event, connector=True):
        return _error(400, "invalid_schema", "invalid event schema")
    if not _connector_event_is_fresh(event):
        return _error(403, "stale_event", "stale or invalid sent_at")
    event["message_id"] = str(event["message_id"])
    if agent is None:
        return {"handled": False, "replies": []}
    return await agent.handle_gateway(event)


@app.post("/v1/outbox")
async def connector_outbox(request: Request):
    """Where a connector pulls messages nobody asked for: proactive openers,
    the follow-up question after a rejection, the excuse for a failed model
    call (docs/connectors.md, "Outbox").

    A LONG-POLL: the request is held up to ``wait_s`` seconds (at most 30)
    until something is queued for this connector's conversations. Each
    delivery is handed out once and never again; the connector reports what
    happened in ``acks`` on its next pull, and only what it acks as sent is
    remembered as said. A connector that has not pulled for 90 seconds is
    treated as gone.

    Same authentication, replay guard and error codes as ``/v1/events``.
    The body must be ``{"kind": "outbox.pull", ...}``, because the signature
    does not cover the path. ``404`` with code ``outbox_disabled`` means
    ``CONNECTOR_OUTBOX_ENABLED`` is off (a 404 without a code is an agent
    without the outbox).
    """
    peer = request.client.host if request.client is not None else ""
    if not _request_peer_is_allowed(peer, CONNECTOR_TOKEN):
        return _error(403, "unauthenticated", "authentication required")
    refused = _refuse_non_local(request, CONNECTOR_TOKEN)
    if refused is not None:
        return refused
    if CONNECTOR_TOKEN and not _ct_equal(
            request.headers.get("x-personagent-token", ""), CONNECTOR_TOKEN):
        return _error(403, "invalid_envelope",
                      "invalid, stale, or replayed request envelope")
    if not await _outbox_admission.try_acquire():
        return _error(429, "capacity_exceeded", "outbox capacity exceeded",
                      retry_after=5)
    try:
        return await _connector_outbox_admitted(request)
    finally:
        await _outbox_admission.release()


async def _connector_outbox_admitted(request: Request):
    body = await _read_webhook_body(request)
    if isinstance(body, JSONResponse):
        return body
    if not _verify_envelope(body, request.headers, CONNECTOR_TOKEN):
        return _error(403, "invalid_envelope",
                      "invalid, stale, or replayed request envelope")
    try:
        pull = parse_pull(json.loads(body or b"{}"))
    except Exception:
        pull = None
    if pull is None:
        return _error(400, "invalid_schema", "not an outbox pull")
    if agent is None or not agent.connector_outbox_enabled:
        return _error(404, "outbox_disabled", "the outbox is turned off")
    return await agent.outbox.pull(**pull, disconnected=request.is_disconnected)


if __name__ == "__main__":
    import uvicorn

    class _Server(uvicorn.Server):
        # uvicorn lets open requests finish before the lifespan shutdown, so
        # without this every restart waits out the connectors' long-polls.
        async def shutdown(self, sockets=None):
            import main as served  # the module uvicorn serves, not __main__
            if served.agent is not None:
                await served.agent.outbox.aclose()
            await super().shutdown(sockets=sockets)

    _Server(uvicorn.Config("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)).run()
