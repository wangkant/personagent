"""The models panel: the models the saved service lists, for the model field to
offer. Read on the server with the saved key, which never reaches the page."""
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time

import httpx

from .. import setup_wizard as sw

ERRORS: frozenset[str] = frozenset()
CACHE_S = 300
# A service that did not answer is asked again sooner.
MISS_CACHE_S = 30
TIMEOUT_S = 8
# OpenRouter's listing, descriptions included, is a few megabytes.
MAX_BYTES = 16 * 1024 * 1024
MAX_MODELS = 5000

_cache: dict[tuple[str, str], tuple[float, list | None]] = {}
_lock = threading.Lock()


def _free(row: dict) -> bool:
    if str(row.get("id", "")).endswith(":free"):
        return True
    pricing = row.get("pricing")
    if not isinstance(pricing, dict) or "prompt" not in pricing or "completion" not in pricing:
        return False
    try:
        return float(pricing["prompt"]) == 0 and float(pricing["completion"]) == 0
    except (TypeError, ValueError):
        return False


def parse(answer, openrouter: bool) -> list[dict] | None:
    rows = answer.get("data") if isinstance(answer, dict) else None
    if not isinstance(rows, list):
        return None
    models, seen = [], set()
    for row in rows:
        name = row.get("id") if isinstance(row, dict) else None
        if not isinstance(name, str) or not name.strip() or len(name) > 256 or name in seen:
            continue
        # An embedding model cannot chat.
        if "embed" in name.lower():
            continue
        seen.add(name)
        models.append({"id": name.strip(), "free": openrouter and _free(row)})
        if len(models) >= MAX_MODELS:
            break
    if openrouter and "openrouter/free" not in seen:
        # The preset's own choice: one of the free models for each request.
        models.append({"id": "openrouter/free", "free": True})
    models.sort(key=lambda m: m["id"].lower())
    return models or None


async def _fetch(base: str, key: str, openrouter: bool) -> list[dict] | None:
    url = base.rstrip("/") + "/models"
    # A server on this computer must not go through a proxy, as in setup_wizard.probe_key.
    async with httpx.AsyncClient(trust_env=not sw._is_loopback(url), timeout=TIMEOUT_S) as client:
        async with client.stream("GET", url, headers={"Authorization": f"Bearer {key}"}) as answer:
            if answer.status_code != 200:
                return None
            raw = bytearray()
            async for chunk in answer.aiter_bytes():
                raw.extend(chunk)
                if len(raw) > MAX_BYTES:
                    return None
    try:
        return parse(json.loads(raw), openrouter)
    except ValueError:
        return None


async def listing(workspace) -> dict:
    values = workspace.config()
    base, key = values.get("LLM_BASE_URL", "").strip(), values.get("LLM_API_KEY", "")
    if not base or not key:
        return {"baseUrl": base, "models": None}
    known = sw.provider_for_base(base)
    openrouter = bool(known and known.key == "openrouter")
    slot = (base, hashlib.sha256(key.encode()).hexdigest())
    with _lock:
        kept = _cache.get(slot)
    if kept and time.monotonic() < kept[0]:
        return {"baseUrl": base, "models": kept[1]}
    try:
        # The whole read is bounded, not only each wait for a byte.
        models = await asyncio.wait_for(_fetch(base, key, openrouter), TIMEOUT_S * 2)
    except (httpx.HTTPError, asyncio.TimeoutError, OSError, ValueError):
        models = None
    with _lock:
        now = time.monotonic()
        for old in [s for s, (until, _m) in _cache.items() if until < now]:
            _cache.pop(old, None)
        _cache[slot] = (now + (CACHE_S if models else MISS_CACHE_S), models)
    return {"baseUrl": base, "models": models}


def mount(app, workspace, body) -> None:
    @app.get("/api/models")
    async def models():
        return await listing(workspace)
