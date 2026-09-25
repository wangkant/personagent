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
from persona_agent.health import run_checks, all_critical_ok
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
    log is a nuisance; a missing one is why anyone set LOG_FILE.
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
    webhook_secret: str,
    gateway_token: str,
) -> None:
    """Refuse a network bind whose two event endpoints are not authenticated."""
    if _is_loopback_host(host):
        return
    missing = []
    if not webhook_secret:
        missing.append("WEBHOOK_SECRET")
    if not gateway_token:
        missing.append("GATEWAY_TOKEN")
    if missing:
        raise ValueError(
            f"HOST={host!r} is not loopback; set {', '.join(missing)} "
            "before exposing webhook endpoints"
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
    no preflight and forge an event as OWNER_QQ; DNS rebinding lets such a
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
            "else needs WEBHOOK_SECRET / GATEWAY_TOKEN set",
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
# (NAPCAT_API=http://127.0.0.1:3000), so the webhook never needs to be
# world-exposed. Set HOST=0.0.0.0 only for a split deployment, and then set
# WEBHOOK_SECRET so forged OneBot payloads (impersonating OWNER_QQ, poisoning
# memory, burning tokens) can't reach /webhook/qq.
HOST = env_str("HOST", "127.0.0.1")
PORT = env_int("PORT", 8080, minimum=1, maximum=65535)
# Optional OneBot HMAC secret (NapCat httpClient `secret`). When set, every
# /webhook/qq body must carry a matching `x-signature: sha1=<hex>` header.
WEBHOOK_SECRET = env_str("WEBHOOK_SECRET")
MAX_WEBHOOK_BODY_BYTES = env_int(
    "MAX_WEBHOOK_BODY_BYTES", 8_000_000, minimum=1, maximum=64_000_000)
# uvicorn has no body-read timeout, and a webhook holds an admission slot
# while it reads. Without a deadline, a peer that sends a Content-Length and
# then one byte keeps that slot forever, and a few of them 429 every real
# event. A forwarder on the same host sends its body in milliseconds.
BODY_READ_TIMEOUT_S = 30
MAX_INFLIGHT_WEBHOOKS = env_int(
    "MAX_INFLIGHT_WEBHOOKS", 64, minimum=1, maximum=4096)
# A SEPARATE budget, because the two endpoints hold their slot for wildly
# different spans. /webhook/qq hands its slot to a background task within
# milliseconds; /webhook/gateway answers synchronously and holds one for the
# entire turn (~12s, see transport.py). Sharing one counter meant a burst of
# gateway turns 429'd the cheap, non-blocking QQ webhooks alongside them.
# Defaults to MAX_INFLIGHT_WEBHOOKS, so an existing deployment keeps its
# capacity and a blank line in .env means "same as above" — what changes is
# that the two can no longer starve each other.
MAX_INFLIGHT_GATEWAY = env_int(
    "MAX_INFLIGHT_GATEWAY", MAX_INFLIGHT_WEBHOOKS, minimum=1, maximum=4096)
# Whether to build the agent at all. Off leaves the HTTP layer answering
# health checks and accepting (then dropping) events.
AGENT_ENABLE = env_bool("AGENT_ENABLE", True)
# Gateway (platform-neutral forwarding): shared secret for /webhook/gateway
# (blank = no auth), and how old a forwarded event may be before it is refused.
GATEWAY_TOKEN = env_str("GATEWAY_TOKEN")
GATEWAY_SOURCE_MAX_AGE_SECONDS = env_int(
    "GATEWAY_SOURCE_MAX_AGE_SECONDS", 86_400, minimum=1, maximum=604_800)

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
    log_file = os.getenv("LOG_FILE", "").strip()
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
    """Bounded timestamped nonce cache for authenticated gateway envelopes."""

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
            # cap is a hard refusal — which means a busy forwarder can hit a
            # cliff where EVERY gateway event 403s as "replayed", and that is
            # indistinguishable from a bad token unless it is said out loud.
            logger.error(
                "[main] gateway replay guard full (%d nonces live within %ds) "
                "— rejecting all gateway events until the window drains; "
                "raise the cap if this is legitimate traffic",
                len(self._seen), self.ttl_seconds)
            if changed:
                self._persist()
            return False
        if len(self._seen) >= self.max_entries * 4 // 5:
            logger.warning(
                "[main] gateway replay guard at %d/%d nonces",
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


def _verify_gateway_envelope(
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
    supplied_token = headers.get("x-gateway-token", "")
    timestamp_raw = headers.get("x-gateway-timestamp", "")
    nonce = headers.get("x-gateway-nonce", "")
    supplied_signature = headers.get("x-gateway-signature", "")
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
    guard = replay_guard or _gateway_replay
    return guard.accept(nonce, timestamp, int(time.time()) if now is None else now)


def _validate_event_payload(payload: dict, *, gateway: bool) -> bool:
    """Validate the stable identity fields required for deduplication."""
    if not isinstance(payload, dict):
        return False
    if gateway:
        required = (
            "platform", "message_type", "user_id", "message_id",
            "source_timestamp",
        )
        if any(payload.get(key) in (None, "") for key in required):
            return False
        if payload.get("message_type") == "group" and payload.get(
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


def _gateway_event_is_fresh(
    payload: dict,
    *,
    now: int | None = None,
    max_age_seconds: int = GATEWAY_SOURCE_MAX_AGE_SECONDS,
) -> bool:
    """Validate source-event age independently of forwarding-envelope age."""
    return _event_is_fresh(payload, "source_timestamp", now=now,
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


_webhook_admission = AdmissionLimiter(MAX_INFLIGHT_WEBHOOKS)
_gateway_admission = AdmissionLimiter(MAX_INFLIGHT_GATEWAY)
_gateway_replay = ReplayGuard(
    state_file=runtime_dir() / "gateway_nonces.json")


class RequestBodyTooLarge(Exception):
    """Raised when a webhook body exceeds the configured byte limit."""


def _error(status: int, code: str, message: str, *,
           retry_after: int | None = None) -> JSONResponse:
    """One shape for every error this service returns.

    `error` stays exactly what it was — a sentence for a human reading a log.
    `code` is the stable half, and it exists because the prose is not
    actionable: `/webhook/gateway` alone answers 403 for a peer that is not
    allowed, an envelope that failed verification, and a source event that is
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
    """Stamp a response from the deprecated `/webhook/qq` ingress.

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
            _read_body_limited(request, MAX_WEBHOOK_BODY_BYTES),
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
    _validate_exposure_config(HOST, WEBHOOK_SECRET, GATEWAY_TOKEN)
    runtime_lock = None
    if AGENT_ENABLE:
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
        _spawn(agent.loop_proactive())  # self-guards on PROACTIVE_ENABLE
        _spawn(agent.loop_evolve())     # self-guards on EVOLVE_AUTO
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
    logger.info("bot started on %s:%d (agent=%s, lang=%s)", HOST, PORT,
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
    if GATEWAY_TOKEN:
        authorized = _ct_equal(
            request.headers.get("X-Gateway-Token", ""), GATEWAY_TOKEN)
    else:
        authorized = _is_loopback_host(client_host)
    if not authorized:
        return _error(403, "forbidden", "forbidden")
    refused = _refuse_non_local(request, GATEWAY_TOKEN)
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
            "[Agent] /webhook/qq (direct OneBot ingress) is deprecated since 0.3.0 and "
            "will be removed in a later release; route QQ through AstrBot with "
            "GATEWAY_NATIVE_PLATFORMS=aiocqhttp. Nothing changes for this deployment yet.")


@app.post("/webhook/qq")
async def qq_webhook(request: Request):
    """DEPRECATED direct OneBot v11 ingress, fed by the client's own webhook.

    Fire-and-forget: the event is validated, then handled on a background task
    so NapCat never waits for the model round-trip. The reply is delivered by
    a separate call to the OneBot HTTP API, so the response here is only
    ``{"ok": true}`` and never carries it. That is the opposite of
    ``/webhook/gateway``, which answers synchronously.

    Deprecated since 0.3.0, removed in a later release; every response carries
    ``Deprecation: true``. The supported path is AstrBot with
    ``GATEWAY_NATIVE_PLATFORMS=aiocqhttp``. Set ``WEBHOOK_SECRET`` so NapCat
    signs the body as ``x-signature: sha1=...`` — without it, anyone who can
    reach this port can forge an event.
    """
    _warn_direct_route_once()
    # Refuse before admission, so a peer that may not call this at all cannot
    # hold a slot. The signature covers the body and has to wait for it.
    peer = request.client.host if request.client is not None else ""
    if not _request_peer_is_allowed(peer, WEBHOOK_SECRET):
        return _mark_deprecated(_error(
            403, "unauthenticated", "authentication required"))
    refused = _refuse_non_local(request, WEBHOOK_SECRET)
    if refused is not None:
        return _mark_deprecated(refused)
    if not await _webhook_admission.try_acquire():
        return _mark_deprecated(_error(
            429, "capacity_exceeded", "webhook capacity exceeded",
            retry_after=1))
    request.state.admission_handed_off = False
    try:
        return _mark_deprecated(await _qq_webhook_admitted(request))
    finally:
        if not request.state.admission_handed_off:
            await _webhook_admission.release()


async def _qq_webhook_admitted(request: Request):
    body = await _read_webhook_body(request)
    if isinstance(body, JSONResponse):
        return body
    # OneBot HMAC verification (opt-in via WEBHOOK_SECRET). Without it, anyone
    # who can reach this port can POST a forged event — impersonate OWNER_QQ,
    # poison memory, drive sends. NapCat signs the body as `x-signature: sha1=…`
    # when its httpClient `secret` is set; configure both or leave unset (and
    # keep HOST=127.0.0.1).
    if WEBHOOK_SECRET:
        sig = request.headers.get("x-signature", "")
        expected = "sha1=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha1).hexdigest()
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
    # external body can't masquerade as gateway-synthesized.
    if isinstance(payload, dict):
        payload.pop("_gateway", None)
        payload.pop("_platform", None)
    if not _validate_event_payload(payload, gateway=False):
        return _error(400, "invalid_schema", "invalid event schema")
    if WEBHOOK_SECRET and not _onebot_event_is_fresh(payload):
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
                await _webhook_admission.release()
        request.state.admission_handed_off = True
        _spawn(_safe_handle())
    # A JSONResponse rather than a bare dict so _mark_deprecated has something
    # to stamp; the serialized body is byte-identical.
    return JSONResponse(content={"ok": True})


_IGNORED_TOKEN_WARNED = False


def _warn_ignored_gateway_token_once(request: Request) -> None:
    """The forwarder has a token this process was not given: its envelope is
    not being checked at all, which is rarely what the operator meant."""
    global _IGNORED_TOKEN_WARNED
    if (GATEWAY_TOKEN or _IGNORED_TOKEN_WARNED
            or "x-gateway-token" not in request.headers):
        return
    _IGNORED_TOKEN_WARNED = True
    logger.warning(
        "[main] the forwarder sends X-Gateway-Token but GATEWAY_TOKEN is "
        "blank here, so the token is ignored; set the same GATEWAY_TOKEN "
        "in .env to have gateway requests authenticated")


@app.post("/webhook/gateway")
async def gateway_webhook(request: Request):
    """Platform-neutral inbound endpoint for forwarder plugins.

    SYNCHRONOUS round-trip, unlike ``/webhook/qq``: the forwarder needs the
    replies in the response body to relay them to the source platform, so the
    whole pipeline, debounce and every model call included, runs before this
    returns (the typing pauses are skipped behind the sink). Set the plugin's HTTP timeout accordingly; a caller that
    gives up early does not stop the turn, which still commits its reply and
    everything it learned from it.

    Body schema: see ``persona_agent/gateway.py``. The response is
    ``{"handled": bool, "owned": bool, "replies": [...]}``, where ``owned``
    says the conversation is this persona's whether or not it chose to speak —
    a forwarder should suppress its own model on ``owned``, never on whether
    ``replies`` is empty, because silence is frequently the answer.

    Authentication is a bearer token plus an HMAC envelope over
    timestamp/nonce/body (``X-Gateway-Token``, ``-Timestamp``, ``-Nonce``,
    ``-Signature``). Errors carry a stable ``code``; branch on it, not on the
    prose in ``error``.
    """
    # Everything that needs no body is checked before admission: a caller
    # without the token must not be able to hold one of the slots a real
    # turn needs. The signature, nonce and replay checks still run after it,
    # so a 429 never burns a nonce.
    peer = request.client.host if request.client is not None else ""
    if not _request_peer_is_allowed(peer, GATEWAY_TOKEN):
        return _error(403, "unauthenticated", "authentication required")
    refused = _refuse_non_local(request, GATEWAY_TOKEN)
    if refused is not None:
        return refused
    _warn_ignored_gateway_token_once(request)
    if GATEWAY_TOKEN and not _ct_equal(
            request.headers.get("x-gateway-token", ""), GATEWAY_TOKEN):
        return _error(403, "invalid_envelope",
                      "invalid, stale, or replayed gateway envelope")
    if not await _gateway_admission.try_acquire():
        return _error(429, "capacity_exceeded", "webhook capacity exceeded",
                      retry_after=3)
    try:
        return await _gateway_webhook_admitted(request)
    finally:
        await _gateway_admission.release()


async def _gateway_webhook_admitted(request: Request):
    """Platform-neutral inbound endpoint for forwarder plugins (schema in
    gateway.py). Unlike /webhook/qq this is a synchronous round-trip: the
    forwarder needs the replies in the response body to relay them back, so
    the full handle pipeline (debounce + typing simulation included) runs
    before returning — set the plugin's HTTP timeout accordingly."""
    body = await _read_webhook_body(request)
    if isinstance(body, JSONResponse):
        return body
    if not _verify_gateway_envelope(body, request.headers, GATEWAY_TOKEN):
        # One code for four causes (bad token, bad signature, timestamp
        # outside the window, replayed nonce): _verify_gateway_envelope folds
        # them into a bool before this sees them, and splitting that return is
        # a bigger change than this one — its True/False contract is pinned by
        # tests. `invalid_envelope` at least separates these from the other
        # two 403s this route can answer.
        return _error(403, "invalid_envelope",
                      "invalid, stale, or replayed gateway envelope")
    try:
        event = json.loads(body or b"{}")
    except Exception:
        event = {}
    if not isinstance(event, dict):
        # A body that parses to JSON null/list/string would otherwise hit
        # event.get(...) in synthesize_onebot_payload and 500.
        event = {}
    if not _validate_event_payload(event, gateway=True):
        return _error(400, "invalid_schema", "invalid gateway event schema")
    if not _gateway_event_is_fresh(event):
        return _error(403, "stale_source_event", "stale gateway source event")
    event["message_id"] = str(event["message_id"])
    if agent is None:
        return {"handled": False, "replies": []}
    return await agent.handle_gateway(event)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
