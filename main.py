"""FastAPI HTTP layer for the QQ persona agent."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent import Agent
from health import run_checks, all_critical_ok

load_dotenv(override=True)

# ========== Config ==========
# Bind loopback by default: NapCat posts events from localhost
# (NAPCAT_API=http://127.0.0.1:3000), so the webhook never needs to be
# world-exposed. Set HOST=0.0.0.0 only for a split deployment, and then set
# WEBHOOK_SECRET so forged OneBot payloads (impersonating OWNER_QQ, poisoning
# memory, burning tokens) can't reach /webhook/qq.
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8080))
# Optional OneBot HMAC secret (NapCat httpClient `secret`). When set, every
# /webhook/qq body must carry a matching `x-signature: sha1=<hex>` header.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

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
AGENT_TRIGGER_COUNT = int(os.getenv("AGENT_TRIGGER_COUNT", 30))
AGENT_CONTEXT_LEN = int(os.getenv("AGENT_CONTEXT_LEN", 120))
AGENT_FOLLOWUP_WINDOW = int(os.getenv("AGENT_FOLLOWUP_WINDOW", 120))
AGENT_MEMORY_FILE = os.getenv("AGENT_MEMORY_FILE", "memory.json")
AGENT_MEMORY_MAX = int(os.getenv("AGENT_MEMORY_MAX", 50))
OWNER_QQ = os.getenv("OWNER_QQ", "")
OWNER_NAME = os.getenv("OWNER_NAME", "")
OWNER_RELATIONSHIP = os.getenv("OWNER_RELATIONSHIP", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "")
ANTHROPIC_PRIVATE_MODEL = os.getenv("ANTHROPIC_PRIVATE_MODEL", "")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "")
# Defaults below match .env.example so behavior is identical whether or not a
# .env is present (no silent drift between the template and the code).
RATE_WINDOW = int(os.getenv("RATE_WINDOW", 120))
RATE_THRESHOLD = int(os.getenv("RATE_THRESHOLD", 30))
FALLBACK_DURATION = int(os.getenv("FALLBACK_DURATION", 180))
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
GATEWAY_OWNER_IDS = tuple(
    s.strip() for s in os.getenv("GATEWAY_OWNER_IDS", "").split(",") if s.strip()
)

# ========== Logging ==========
_log_root = logging.getLogger()
# Guarded so a re-import of this module (uvicorn does this with the
# "main:app" string form) doesn't attach duplicate handlers.
if not _log_root.handlers:
    _log_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    _log_root.setLevel(logging.INFO)
    _stdout_h = logging.StreamHandler()
    _stdout_h.setFormatter(_log_formatter)
    _log_root.addHandler(_stdout_h)
    try:
        from logging.handlers import RotatingFileHandler
        # Absolute path anchored to this file so the log lands in the
        # project directory regardless of the working directory the bot
        # was launched from.
        _log_path = Path(__file__).resolve().parent / "bot.log"
        _file_h = RotatingFileHandler(
            str(_log_path), maxBytes=5_000_000, backupCount=3, encoding="utf-8",
        )
        _file_h.setFormatter(_log_formatter)
        _log_root.addHandler(_file_h)
    except Exception:
        pass
logger = logging.getLogger("bot")

agent: Optional[Agent] = None

# Strong refs to fire-and-forget tasks. asyncio keeps only a weak reference to
# a task, so one suspended at an await with no other reference can be garbage
# collected mid-flight, silently dropping the work (e.g. an inbound message).
_bg_tasks: set[asyncio.Task] = set()


def _spawn(coro) -> asyncio.Task:
    """create_task + retain a strong ref until the task finishes."""
    t = asyncio.create_task(coro)
    _bg_tasks.add(t)
    t.add_done_callback(_bg_tasks.discard)
    return t


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    if AGENT_ENABLE:
        agent = Agent(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            model=DEEPSEEK_MODEL,
            bot_qq=BOT_QQ,
            bot_name=BOT_NAME,
            anthropic_key=ANTHROPIC_API_KEY,
            anthropic_base_url=ANTHROPIC_BASE_URL,
            anthropic_private_model=ANTHROPIC_PRIVATE_MODEL,
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
        )
        _spawn(agent.probe_models())
        _spawn(agent.check_missed_mentions())
        _spawn(agent.loop_check_missed())
        _spawn(agent.loop_proactive())  # self-guards on PROACTIVE_ENABLE
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
    # Exposure warning: binding a non-loopback host without transport auth means
    # anyone who can reach the port can forge events (impersonate OWNER_QQ,
    # poison memory, fabricate per-key state, burn tokens).
    if HOST not in ("127.0.0.1", "localhost", "::1"):
        if not WEBHOOK_SECRET:
            logger.warning("SECURITY: HOST=%s is not loopback and WEBHOOK_SECRET is unset — "
                           "/webhook/qq accepts forged OneBot events. Set WEBHOOK_SECRET.", HOST)
        if not GATEWAY_TOKEN:
            logger.warning("SECURITY: HOST=%s is not loopback and GATEWAY_TOKEN is unset — "
                           "/webhook/gateway is open (attacker-chosen keys). Set GATEWAY_TOKEN.", HOST)
    yield
    # ---- shutdown: cancel background loops + force out throttled writes so
    # buffered state (dedup ring / sticker index) isn't lost ----
    for t in list(_bg_tasks):
        t.cancel()
    if agent is not None:
        try:
            agent.flush_state()
        except Exception:
            logger.exception("shutdown flush failed")

app = FastAPI(title="QQ Persona Agent", version="0.1.0", lifespan=lifespan)


# /health caches its probe results briefly so monitoring polls don't spam the
# upstream APIs (each full probe spends a few tokens + 1 search credit).
_health_cache: dict = {"ts": 0.0, "data": None}
_health_lock = asyncio.Lock()


@app.get("/health")
async def health():
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
    body = await request.body()
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
    if agent:
        # Non-blocking: don't make NapCat wait for the LLM round-trip.
        # Wrap in a guard so a raised exception is logged instead of vanishing
        # as an unretrieved-task warning.
        async def _safe_handle():
            try:
                await agent.handle(payload)
            except Exception:
                logger.exception("handle failed")
        _spawn(_safe_handle())
    return {"ok": True}


@app.post("/webhook/gateway")
async def gateway_webhook(request: Request):
    """Platform-neutral inbound endpoint for forwarder plugins (schema in
    gateway.py). Unlike /webhook/qq this is a synchronous round-trip: the
    forwarder needs the replies in the response body to relay them back, so
    the full handle pipeline (debounce + typing simulation included) runs
    before returning — set the plugin's HTTP timeout accordingly."""
    if GATEWAY_TOKEN and request.headers.get("X-Gateway-Token") != GATEWAY_TOKEN:
        return JSONResponse(status_code=403, content={"error": "invalid gateway token"})
    try:
        event = await request.json()
    except Exception:
        event = {}
    if not isinstance(event, dict):
        # A body that parses to JSON null/list/string would otherwise hit
        # event.get(...) in synthesize_onebot_payload and 500.
        event = {}
    if agent is None:
        return {"handled": False, "replies": []}
    return await agent.handle_gateway(event)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
