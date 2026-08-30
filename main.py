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

from persona_agent import preflight
from persona_agent.agent import Agent
from persona_agent.health import run_checks, all_critical_ok
from persona_agent.paths import ROOT, runtime_dir
from persona_agent.storage import RuntimeInstanceLock, atomic_write_text


def _parse_int_config(
    name: str,
    raw,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Parse one integer setting without crashing module import."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logging.getLogger("bot").warning(
            "invalid %s=%r; using %d", name, raw, default)
        return default
    if ((minimum is not None and value < minimum)
            or (maximum is not None and value > maximum)):
        logging.getLogger("bot").warning(
            "out-of-range %s=%r; using %d", name, raw, default)
        return default
    return value


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


# ========== Config ==========
# Bind loopback by default: NapCat posts events from localhost
# (NAPCAT_API=http://127.0.0.1:3000), so the webhook never needs to be
# world-exposed. Set HOST=0.0.0.0 only for a split deployment, and then set
# WEBHOOK_SECRET so forged OneBot payloads (impersonating OWNER_QQ, poisoning
# memory, burning tokens) can't reach /webhook/qq.
HOST = os.getenv("HOST", "127.0.0.1")
PORT = _parse_int_config(
    "PORT", os.getenv("PORT", "8080"), 8080, minimum=1, maximum=65535)
# Optional OneBot HMAC secret (NapCat httpClient `secret`). When set, every
# /webhook/qq body must carry a matching `x-signature: sha1=<hex>` header.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
MAX_WEBHOOK_BODY_BYTES = _parse_int_config(
    "MAX_WEBHOOK_BODY_BYTES",
    os.getenv("MAX_WEBHOOK_BODY_BYTES", "8000000"),
    8_000_000,
    minimum=1,
    maximum=64_000_000,
)
MAX_INFLIGHT_WEBHOOKS = _parse_int_config(
    "MAX_INFLIGHT_WEBHOOKS",
    os.getenv("MAX_INFLIGHT_WEBHOOKS", "64"),
    64,
    minimum=1,
    maximum=4096,
)
# A SEPARATE budget, because the two endpoints hold their slot for wildly
# different spans. /webhook/qq hands its slot to a background task within
# milliseconds; /webhook/gateway answers synchronously and holds one for the
# entire turn (~12s, see transport.py). Sharing one counter meant a burst of
# gateway turns 429'd the cheap, non-blocking QQ webhooks alongside them.
# Defaults to the same number, so an existing deployment keeps its capacity —
# what changes is that the two can no longer starve each other.
MAX_INFLIGHT_GATEWAY = _parse_int_config(
    "MAX_INFLIGHT_GATEWAY",
    # `.strip() or ...` so a blank line in .env means "same as above" rather
    # than an unparseable value that warns on every start.
    os.getenv("MAX_INFLIGHT_GATEWAY", "").strip() or MAX_INFLIGHT_WEBHOOKS,
    MAX_INFLIGHT_WEBHOOKS,
    minimum=1,
    maximum=4096,
)

NAPCAT_API = os.getenv("NAPCAT_API", "http://127.0.0.1:3000")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
BOT_QQ = os.getenv("BOT_QQ", "")
BOT_NAME = os.getenv("BOT_NAME", "")
# Language of the agent: 'en' (default, primary build) or 'zh' (Chinese variant).
# Selects the reply validator mode, the per-language data files
# (persona/examples/feedback/output_filter/lorebook), and the control-flow lexicons.
AGENT_LANG = os.getenv("AGENT_LANG", "en").strip().lower()
AGENT_ENABLE = os.getenv("AGENT_ENABLE", "true").lower() == "true"
AGENT_TRIGGER_COUNT = _parse_int_config(
    "AGENT_TRIGGER_COUNT", os.getenv("AGENT_TRIGGER_COUNT", "30"), 30,
    minimum=1, maximum=10_000)
AGENT_CONTEXT_LEN = _parse_int_config(
    "AGENT_CONTEXT_LEN", os.getenv("AGENT_CONTEXT_LEN", "120"), 120,
    minimum=10, maximum=10_000)
AGENT_FOLLOWUP_WINDOW = _parse_int_config(
    "AGENT_FOLLOWUP_WINDOW", os.getenv("AGENT_FOLLOWUP_WINDOW", "120"), 120,
    minimum=0, maximum=86_400)
AGENT_MEMORY_FILE = os.getenv("AGENT_MEMORY_FILE", "memory.json")
AGENT_MEMORY_MAX = _parse_int_config(
    "AGENT_MEMORY_MAX", os.getenv("AGENT_MEMORY_MAX", "50"), 50,
    minimum=1, maximum=10_000)
OWNER_QQ = os.getenv("OWNER_QQ", "")
OWNER_NAME = os.getenv("OWNER_NAME", "")
OWNER_RELATIONSHIP = os.getenv("OWNER_RELATIONSHIP", "")
# Alternate model name for private chats, served by the same OpenAI-compatible
# primary endpoint. Blank = use DEEPSEEK_MODEL.
# ANTHROPIC_PRIVATE_MODEL is the pre-0.1.2 name — still honored so an existing
# .env keeps working. It never meant an Anthropic endpoint.
PRIVATE_MODEL = (os.getenv("PRIVATE_MODEL", "")
                 or os.getenv("ANTHROPIC_PRIVATE_MODEL", ""))
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "")
# Defaults below match .env.example so behavior is identical whether or not a
# .env is present (no silent drift between the template and the code).
RATE_WINDOW = _parse_int_config(
    "RATE_WINDOW", os.getenv("RATE_WINDOW", "120"), 120,
    minimum=1, maximum=86_400)
RATE_THRESHOLD = _parse_int_config(
    "RATE_THRESHOLD", os.getenv("RATE_THRESHOLD", "30"), 30,
    minimum=1, maximum=100_000)
FALLBACK_DURATION = _parse_int_config(
    "FALLBACK_DURATION", os.getenv("FALLBACK_DURATION", "180"), 180,
    minimum=1, maximum=86_400)
EVAL_ENABLE = os.getenv("EVAL_ENABLE", "false").lower() == "true"
EVAL_MODEL = os.getenv("EVAL_MODEL", "")
EVAL_FILE = os.getenv("EVAL_FILE", "eval.jsonl")
VISION_MODEL = os.getenv("VISION_MODEL", "")
GLM_API_KEY = os.getenv("GLM_API_KEY", "")
GLM_BASE_URL = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
# Gateway (platform-neutral forwarding): shared secret for /webhook/gateway
# (blank = no auth) and platform-prefixed ids treated as owner in gateway DMs.
GATEWAY_TOKEN = os.getenv("GATEWAY_TOKEN", "")
GATEWAY_SOURCE_MAX_AGE_SECONDS = _parse_int_config(
    "GATEWAY_SOURCE_MAX_AGE_SECONDS",
    os.getenv("GATEWAY_SOURCE_MAX_AGE_SECONDS", "86400"),
    86_400,
    minimum=1,
    maximum=604_800,
)
GATEWAY_OWNER_IDS = tuple(
    s.strip() for s in os.getenv("GATEWAY_OWNER_IDS", "").split(",") if s.strip()
)
# Forwarder platforms allowed to mint BARE ids instead of "<platform>:<id>"
# ones — set this to the forwarder's QQ adapter name (AstrBot calls it
# "aiocqhttp") to route QQ through the same door as every other platform
# without renaming a single conversation. Empty by default, and deliberately
# an operator setting rather than something the forwarder asserts: bare ids
# are the spelling OWNER_QQ, QQ_GROUPS and PRIVATE_ALLOWED_QQS are written in.
GATEWAY_NATIVE_PLATFORMS = tuple(
    s.strip() for s in os.getenv("GATEWAY_NATIVE_PLATFORMS", "").split(",")
    if s.strip()
)

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
        changed = pruned != self._seen
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
    if (not hmac.compare_digest(supplied_token, token)
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
    if not hmac.compare_digest(supplied_signature, expected):
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


def _gateway_event_is_fresh(
    payload: dict,
    *,
    now: int | None = None,
    max_age_seconds: int = GATEWAY_SOURCE_MAX_AGE_SECONDS,
) -> bool:
    """Validate source-event age independently of forwarding-envelope age."""
    try:
        event_time = int(payload.get("source_timestamp"))
    except (TypeError, ValueError, OverflowError):
        return False
    current = int(time.time()) if now is None else int(now)
    return abs(current - event_time) <= max(1, int(max_age_seconds))


def _onebot_event_is_fresh(
    payload: dict,
    *,
    now: int | None = None,
    max_age_seconds: int = 300,
) -> bool:
    """Reject stale signed OneBot events before their IDs age out of dedup."""
    try:
        event_time = int(payload.get("time"))
    except (TypeError, ValueError):
        return False
    current = int(time.time()) if now is None else int(now)
    return abs(current - event_time) <= max(1, int(max_age_seconds))


_webhook_admission = AdmissionLimiter(MAX_INFLIGHT_WEBHOOKS)
_gateway_admission = AdmissionLimiter(MAX_INFLIGHT_GATEWAY)
_gateway_replay = ReplayGuard(
    state_file=runtime_dir() / "gateway_nonces.json")


class RequestBodyTooLarge(Exception):
    """Raised when a webhook body exceeds the configured byte limit."""


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
            agent = Agent(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                model=DEEPSEEK_MODEL,
                bot_qq=BOT_QQ,
                bot_name=BOT_NAME,
                private_model=PRIVATE_MODEL,
                napcat_api=NAPCAT_API,
                trigger_count=AGENT_TRIGGER_COUNT,
                context_len=AGENT_CONTEXT_LEN,
                followup_window=AGENT_FOLLOWUP_WINDOW,
                memory_file=AGENT_MEMORY_FILE,
                memory_max_per_group=AGENT_MEMORY_MAX,
                owner_qq=OWNER_QQ,
                owner_name=OWNER_NAME,
                owner_relationship=OWNER_RELATIONSHIP,
                fallback_model=FALLBACK_MODEL,
                rate_window=RATE_WINDOW,
                rate_threshold=RATE_THRESHOLD,
                fallback_duration=FALLBACK_DURATION,
                eval_enable=EVAL_ENABLE,
                eval_model=EVAL_MODEL,
                eval_file=EVAL_FILE,
                vision_model=VISION_MODEL,
                glm_api_key=GLM_API_KEY,
                glm_base_url=GLM_BASE_URL,
                tavily_key=TAVILY_API_KEY,
                lang=AGENT_LANG,
                gateway_owner_ids=GATEWAY_OWNER_IDS,
                gateway_native_platforms=GATEWAY_NATIVE_PLATFORMS,
            )
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
                agent.enabled if agent else False, AGENT_LANG)
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

app = FastAPI(title="QQ Persona Agent", version="0.1.0", lifespan=lifespan)


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
        authorized = hmac.compare_digest(
            request.headers.get("X-Gateway-Token", ""), GATEWAY_TOKEN)
    else:
        authorized = _is_loopback_host(client_host)
    if not authorized:
        return JSONResponse(status_code=403, content={"error": "forbidden"})

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

@app.post("/webhook/qq")
async def qq_webhook(request: Request):
    if not await _webhook_admission.try_acquire():
        return JSONResponse(
            status_code=429, content={"error": "webhook capacity exceeded"})
    request.state.admission_handed_off = False
    try:
        peer = request.client.host if request.client is not None else ""
        if not _request_peer_is_allowed(peer, WEBHOOK_SECRET):
            return JSONResponse(
                status_code=403, content={"error": "authentication required"})
        return await _qq_webhook_admitted(request)
    finally:
        if not request.state.admission_handed_off:
            await _webhook_admission.release()


async def _qq_webhook_admitted(request: Request):
    try:
        body = await _read_body_limited(request, MAX_WEBHOOK_BODY_BYTES)
    except RequestBodyTooLarge:
        return JSONResponse(
            status_code=413, content={"error": "request body too large"})
    # OneBot HMAC verification (opt-in via WEBHOOK_SECRET). Without it, anyone
    # who can reach this port can POST a forged event — impersonate OWNER_QQ,
    # poison memory, drive sends. NapCat signs the body as `x-signature: sha1=…`
    # when its httpClient `secret` is set; configure both or leave unset (and
    # keep HOST=127.0.0.1).
    if WEBHOOK_SECRET:
        sig = request.headers.get("x-signature", "")
        expected = "sha1=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha1).hexdigest()
        if not hmac.compare_digest(sig, expected):
            logger.warning("webhook rejected: bad/absent x-signature")
            return JSONResponse(status_code=403, content={"error": "bad signature"})
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
        return JSONResponse(
            status_code=400, content={"error": "invalid event schema"})
    if WEBHOOK_SECRET and not _onebot_event_is_fresh(payload):
        return JSONResponse(
            status_code=403, content={"error": "stale or missing event timestamp"})
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
    return {"ok": True}


@app.post("/webhook/gateway")
async def gateway_webhook(request: Request):
    if not await _gateway_admission.try_acquire():
        return JSONResponse(
            status_code=429, content={"error": "webhook capacity exceeded"})
    try:
        peer = request.client.host if request.client is not None else ""
        if not _request_peer_is_allowed(peer, GATEWAY_TOKEN):
            return JSONResponse(
                status_code=403, content={"error": "authentication required"})
        return await _gateway_webhook_admitted(request)
    finally:
        await _gateway_admission.release()


async def _gateway_webhook_admitted(request: Request):
    """Platform-neutral inbound endpoint for forwarder plugins (schema in
    gateway.py). Unlike /webhook/qq this is a synchronous round-trip: the
    forwarder needs the replies in the response body to relay them back, so
    the full handle pipeline (debounce + typing simulation included) runs
    before returning — set the plugin's HTTP timeout accordingly."""
    try:
        body = await _read_body_limited(request, MAX_WEBHOOK_BODY_BYTES)
    except RequestBodyTooLarge:
        return JSONResponse(
            status_code=413, content={"error": "request body too large"})
    if not _verify_gateway_envelope(body, request.headers, GATEWAY_TOKEN):
        return JSONResponse(
            status_code=403,
            content={"error": "invalid, stale, or replayed gateway envelope"},
        )
    try:
        event = json.loads(body or b"{}")
    except Exception:
        event = {}
    if not isinstance(event, dict):
        # A body that parses to JSON null/list/string would otherwise hit
        # event.get(...) in synthesize_onebot_payload and 500.
        event = {}
    if not _validate_event_payload(event, gateway=True):
        return JSONResponse(
            status_code=400, content={"error": "invalid gateway event schema"})
    if not _gateway_event_is_fresh(event):
        return JSONResponse(
            status_code=403, content={"error": "stale gateway source event"})
    event["message_id"] = str(event["message_id"])
    if agent is None:
        return {"handled": False, "replies": []}
    return await agent.handle_gateway(event)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
