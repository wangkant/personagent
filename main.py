"""QQ-group persona agent — FastAPI HTTP layer. Receives NapCat webhooks and dispatches to agent.handle()."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
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
        asyncio.create_task(agent.stickers.bootstrap_tag_all())
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
        # Non-blocking: don't make NapCat wait for LLM round-trip
        asyncio.create_task(agent.handle(payload))
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
