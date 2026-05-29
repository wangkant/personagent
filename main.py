"""FastAPI HTTP layer for the QQ persona agent."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request

from agent import Agent

load_dotenv(override=True)

# ========== Config ==========
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8080))

NAPCAT_API = os.getenv("NAPCAT_API", "http://127.0.0.1:3000")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
BOT_QQ = os.getenv("BOT_QQ", "")
BOT_NAME = os.getenv("BOT_NAME", "")
AGENT_ENABLE = os.getenv("AGENT_ENABLE", "true").lower() == "true"
AGENT_TRIGGER_COUNT = int(os.getenv("AGENT_TRIGGER_COUNT", 30))
AGENT_CONTEXT_LEN = int(os.getenv("AGENT_CONTEXT_LEN", 60))
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
RATE_WINDOW = int(os.getenv("RATE_WINDOW", 60))
RATE_THRESHOLD = int(os.getenv("RATE_THRESHOLD", 5))
FALLBACK_DURATION = int(os.getenv("FALLBACK_DURATION", 300))
EVAL_ENABLE = os.getenv("EVAL_ENABLE", "true").lower() == "true"
EVAL_MODEL = os.getenv("EVAL_MODEL", "")
EVAL_FILE = os.getenv("EVAL_FILE", "eval.jsonl")
VISION_MODEL = os.getenv("VISION_MODEL", "")
GLM_API_KEY = os.getenv("GLM_API_KEY", "")
GLM_BASE_URL = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

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
        )
        asyncio.create_task(agent.probe_models())
        asyncio.create_task(agent.check_missed_mentions())
        asyncio.create_task(agent.loop_check_missed())
        asyncio.create_task(agent.stickers.bootstrap_tag_all())

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
        asyncio.create_task(_recheck_then_purge())
    logger.info("bot started on %s:%d (agent=%s)", HOST, PORT, agent.enabled if agent else False)
    yield

app = FastAPI(title="QQ Persona Agent", version="0.1.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "agent_enabled": bool(agent and agent.enabled)}

@app.post("/webhook/qq")
async def qq_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if agent:
        # Non-blocking: don't make NapCat wait for the LLM round-trip.
        # Wrap in a guard so a raised exception is logged instead of vanishing
        # as an unretrieved-task warning.
        async def _safe_handle():
            try:
                await agent.handle(payload)
            except Exception:
                logger.exception("handle failed")
        asyncio.create_task(_safe_handle())
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
