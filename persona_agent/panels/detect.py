"""What this computer already has for a first chat: a local model server that
is running, or a model key in the environment."""
from __future__ import annotations

import asyncio
import json
import os

import httpx

from .. import home as homes

ERRORS: frozenset[str] = frozenset()
# Seconds; a closed local port refuses at once, so this only bounds a hung one.
PROBE_S = 0.8
# The whole answer of one local server, in seconds and in bytes.
ANSWER_S = 3.0
MAX_ANSWER = 1_000_000
MAX_MODELS = 20
#: (id, name, the provider the page selects, the address to save, where it lists its models)
LOCAL = (
    ("ollama", "Ollama", "ollama", "http://localhost:11434/v1", "http://127.0.0.1:11434/api/tags"),
    ("lmstudio", "LM Studio", "other", "http://localhost:1234/v1", "http://127.0.0.1:1234/v1/models"),
)
#: The variable each service's own documentation names -> the page's provider.
ENV_KEYS = {
    "OPENROUTER_API_KEY": "openrouter",
    "DEEPSEEK_API_KEY": "deepseek",
    "SILICONFLOW_API_KEY": "siliconflow",
    "DASHSCOPE_API_KEY": "bailian",
    "ZHIPUAI_API_KEY": "zhipu",
    "MOONSHOT_API_KEY": "moonshot",
    "ARK_API_KEY": "ark",
    "OPENAI_API_KEY": "openai",
    "GEMINI_API_KEY": "gemini",
}


def _names(answer) -> list[str]:
    """Model names in Ollama's {"models": [{"name"}]} or OpenAI's {"data": [{"id"}]}."""
    if not isinstance(answer, dict):
        return []
    rows = answer.get("models") if isinstance(answer.get("models"), list) else answer.get("data")
    names = []
    for row in rows if isinstance(rows, list) else []:
        name = row.get("name") or row.get("id") if isinstance(row, dict) else None
        # An embedding model cannot chat.
        if isinstance(name, str) and name.strip() and "embed" not in name.lower():
            names.append(name.strip()[:256])
    return names[:MAX_MODELS]


async def _local(client: httpx.AsyncClient, row: tuple) -> dict | None:
    key, name, provider, base, listing = row
    async def read() -> list[str]:
        async with client.stream("GET", listing, timeout=PROBE_S) as answer:
            if answer.status_code != 200:
                return []
            raw = bytearray()
            async for chunk in answer.aiter_bytes():
                raw.extend(chunk)
                if len(raw) > MAX_ANSWER:
                    return []
        return _names(json.loads(raw))

    try:
        # Each wait for a byte is bounded above; this bounds a program that drips them.
        models = await asyncio.wait_for(read(), ANSWER_S)
    except (httpx.HTTPError, ValueError, RecursionError, asyncio.TimeoutError):
        return None
    # Running with nothing to chat with is no shortcut.
    return {"id": key, "name": name, "provider": provider, "baseUrl": base, "models": models} if models else None


def env_key(variable: str) -> str:
    """The key in an environment variable this panel offers, '' for any other name."""
    if variable not in ENV_KEYS or variable in homes.FROM_ENV_FILE:
        return ""
    if variable == "OPENAI_API_KEY" and "api.openai.com" not in os.environ.get("OPENAI_BASE_URL", "api.openai.com"):
        # A key for whatever else OPENAI_BASE_URL points at.
        return ""
    value = os.environ.get(variable, "").strip()
    return value if value.isascii() and not any(c.isspace() for c in value) else ""


async def found() -> dict:
    # Loopback only: no proxy has a say.
    async with httpx.AsyncClient(trust_env=False) as client:
        local = await asyncio.gather(*(_local(client, row) for row in LOCAL))
    return {"local": [row for row in local if row],
            "keys": [{"variable": variable, "provider": provider}
                     for variable, provider in ENV_KEYS.items() if env_key(variable)]}


def mount(app, workspace, body) -> None:
    @app.get("/api/detect")
    async def detect():
        return await found()
