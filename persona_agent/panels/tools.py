"""The tools panel: MCP servers the admin adds, whose tools the character may use."""
from __future__ import annotations

import asyncio
import threading

from fastapi import Request

from .. import mcp_tools

# Error codes this panel raises as ValueError, which the page may show.
ERRORS: frozenset[str] = frozenset({
    "tools_bad_snippet", "tools_bad_name", "tools_bad_url", "tools_name_taken", "tools_too_many",
    "tools_unknown_server", "tools_unknown_tool", "tools_sse_unsupported", "tools_write_failed",
    "tools_bad_request", "tools_local_only",
})
MAX_FIELD_CHARS = 8192

# One change to the file at a time; checks and tries run beside them.
_busy = threading.Lock()


def overview(workspace) -> dict:
    return mcp_tools.public_view(workspace.home, running=workspace.services.running("agent"))


def _lines(text, sep: str) -> dict:
    """`NAME=value` (or `Name: value`) lines as pairs; blank lines are skipped."""
    out = {}
    for line in str(text or "").splitlines():
        if not line.strip():
            continue
        key, found, value = line.partition(sep)
        if not found or not key.strip():
            raise ValueError("tools_bad_snippet")
        out[key.strip()] = value.strip()
    return out


def add(workspace, payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()
    snippet = payload.get("snippet")
    for value in (name, snippet, payload.get("command"), payload.get("args"), payload.get("env"),
                  payload.get("url"), payload.get("headers")):
        if value is not None and (not isinstance(value, str) or len(value) > MAX_FIELD_CHARS * 4):
            raise ValueError("tools_bad_request")
    if snippet:
        servers = mcp_tools.parse_snippet(snippet, name)
    elif payload.get("command"):
        args = [line for line in str(payload.get("args") or "").splitlines() if line.strip()]
        spec = mcp_tools.normalize({"command": payload["command"], "args": [a.strip() for a in args],
                                    "env": _lines(payload.get("env"), "=")})
        servers = {mcp_tools._server_name(name) if name else mcp_tools._guess_name(spec): spec}
    elif payload.get("url"):
        spec = mcp_tools.normalize({"url": payload["url"],
                                    "headers": _lines(payload.get("headers"), ":")})
        servers = {mcp_tools._server_name(name) if name else mcp_tools._guess_name(spec): spec}
    elif payload.get("starter") in mcp_tools.STARTERS:
        servers = {payload["starter"]: mcp_tools.normalize(mcp_tools.STARTERS[payload["starter"]])}
    else:
        raise ValueError("tools_bad_snippet")
    # A program runs on this computer with its owner's rights: not for a session from another device.
    if payload.get("_remote") and any("command" in spec for spec in servers.values()):
        raise ValueError("tools_local_only")
    added = mcp_tools.add_servers(workspace.home, servers)
    return {**overview(workspace), "added": added}


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

    def remove(payload: dict) -> dict:
        mcp_tools.remove_server(workspace.home, str(payload.get("server") or ""))
        return overview(workspace)

    def setting(payload: dict) -> dict:
        enabled = payload.get("enabled")
        who = payload.get("who")
        if enabled is not None and not isinstance(enabled, bool):
            raise ValueError("tools_bad_request")
        mcp_tools.set_tool(workspace.home, str(payload.get("server") or ""), str(payload.get("tool") or ""),
                           enabled=enabled, who=who if who is None else str(who))
        return overview(workspace)

    @app.get("/api/tools")
    async def tools_overview():
        return await asyncio.to_thread(overview, workspace)

    def route(path: str, work) -> None:
        async def handler(request: Request):
            payload = await body(request)
            payload["_remote"] = bool(getattr(request.state, "remote", False))
            return await asyncio.to_thread(one_at_a_time(work), payload)
        app.post(f"/api/tools/{path}")(handler)

    for path, work in {"add": lambda p: add(workspace, p), "remove": remove, "set": setting}.items():
        route(path, work)

    @app.post("/api/tools/check")
    async def tools_check(request: Request):
        payload = await body(request)
        return {**await mcp_tools.check(workspace.home, str(payload.get("server") or "")),
                "view": await asyncio.to_thread(overview, workspace)}

    @app.post("/api/tools/call")
    async def tools_call(request: Request):
        payload = await body(request)
        return await mcp_tools.call_by_hand(workspace.home, str(payload.get("server") or ""),
                                            str(payload.get("tool") or ""), payload.get("arguments"))
