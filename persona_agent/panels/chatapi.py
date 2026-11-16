"""The chatapi panel: the OpenAI-compatible API, for software of any kind."""
from __future__ import annotations

import asyncio
import threading

import httpx
from fastapi import Request

from .. import chat_api

# Error codes this panel raises as ValueError, which the page may show.
ERRORS: frozenset[str] = frozenset({
    "chatapi_bad_request", "chatapi_no_key", "chatapi_write_failed", "chatapi_off",
    "chatapi_not_started", "chatapi_unreachable", "chatapi_timeout", "chatapi_stale",
    "chatapi_key_rejected", "chatapi_character_off", "chatapi_busy", "chatapi_model_failed",
    "chatapi_not_admitted", "chatapi_failed",
})

# The test talks in a conversation of its own, so the caller's own one is left alone.
TEST_CONVERSATION = "connection-test"
MAX_TEST_CHARS = 500
TEST_TIMEOUT_S = 180
# What each refusal of the service means on the page.
STATUS_CODES = {404: "chatapi_stale", 401: "chatapi_key_rejected", 503: "chatapi_character_off",
                429: "chatapi_busy", 502: "chatapi_model_failed", 403: "chatapi_not_admitted"}

# One change to the settings at a time.
_busy = threading.Lock()


def overview(workspace) -> dict:
    found = chat_api.settings(workspace.home)
    return {"enabled": found["enabled"], "hasKey": bool(found["key"]),
            "address": workspace.services.agent_url + "/v1", "model": chat_api.MODEL,
            "running": workspace.services.running("agent"),
            "name": workspace.config().get("PERSONA_NAME", "")}


def _apply(workspace, on: bool, *, replace_key: bool = False, restart: bool = True) -> dict:
    """Write the switch, then restart a running character, which reads it only as it starts."""
    try:
        chat_api.switch(workspace.home, on, replace_key=replace_key)
    except OSError:
        raise ValueError("chatapi_write_failed") from None
    restarted = restart and workspace.services.running("agent")
    if restarted:
        try:
            workspace._restart_agent()
        except Exception:
            raise ValueError("chatapi_not_started") from None
    return {**overview(workspace), "restarted": restarted}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(trust_env=False, timeout=TEST_TIMEOUT_S)


async def test(workspace, payload: dict) -> dict:
    """One message through the running service's own endpoint, as another app would send it."""
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEST_CHARS:
        raise ValueError("chatapi_bad_request")
    found = chat_api.settings(workspace.home)
    if not found["enabled"]:
        raise ValueError("chatapi_off")
    if not workspace.config().get("LLM_API_KEY"):
        raise ValueError("key_required")
    try:
        await asyncio.to_thread(workspace.services.start_agent)
    except Exception:
        raise ValueError("chatapi_not_started") from None
    headers = {"Authorization": f"Bearer {found['key']}"} if found["key"] else {}
    request = {"model": chat_api.MODEL, "user": TEST_CONVERSATION,
               "messages": [{"role": "user", "content": text.strip()}]}
    try:
        async with _client() as client:
            response = await client.post(workspace.services.agent_url + "/v1/chat/completions",
                                         json=request, headers=headers)
    except httpx.TimeoutException:
        raise ValueError("chatapi_timeout") from None
    except httpx.HTTPError:
        raise ValueError("chatapi_unreachable") from None
    if response.status_code != 200:
        raise ValueError(STATUS_CODES.get(response.status_code, "chatapi_failed"))
    try:
        reply = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise ValueError("chatapi_failed") from None
    return {"reply": str(reply or "")}


def mount(app, workspace, body) -> None:
    def one_at_a_time(work):
        def run(payload: dict) -> dict:
            if not _busy.acquire(blocking=False):
                raise ValueError("busy")
            try:
                return work(payload)
            finally:
                _busy.release()
        return run

    def switch(payload: dict) -> dict:
        on = payload.get("on")
        if not isinstance(on, bool):
            raise ValueError("chatapi_bad_request")
        return _apply(workspace, on)

    def renew(payload: dict) -> dict:
        enabled = chat_api.settings(workspace.home)["enabled"]
        return _apply(workspace, enabled, replace_key=True, restart=enabled)

    def reveal(payload: dict) -> dict:
        key = chat_api.settings(workspace.home)["key"]
        if not key:
            raise ValueError("chatapi_no_key")
        return {"key": key}

    @app.get("/api/chatapi")
    async def chatapi_overview():
        return await asyncio.to_thread(overview, workspace)

    def route(path: str, work) -> None:
        async def handler(request: Request):
            return await asyncio.to_thread(one_at_a_time(work), await body(request))
        app.post(f"/api/chatapi/{path}")(handler)

    for path, work in {"switch": switch, "key": renew, "reveal": reveal}.items():
        route(path, work)

    @app.post("/api/chatapi/test")
    async def chatapi_test(request: Request):
        return await test(workspace, await body(request))
