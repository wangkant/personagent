"""The approvals panel: new chats waiting for the admin, on the platforms that
ask for approval (approvals.py), the chats approved or declined, and the
switch that makes a platform ask."""
from __future__ import annotations

import asyncio
import os
import threading

from fastapi import Request

from .. import access, approvals, channels, connections as conn

ERRORS: frozenset[str] = frozenset({
    "approvals_gone", "approvals_bad_request", "approvals_write_failed", "approvals_not_dm",
    "approvals_unverified", "approvals_code_mismatch", "approvals_env_locked",
})

# One decision at a time.
_busy = threading.Lock()


def _store(workspace) -> approvals.Store:
    return approvals.Store(approvals.store_path(workspace.home))


def overview(workspace) -> dict:
    values = workspace.config()
    data = _store(workspace).snapshot()
    # The admins the service has: .env, the environment (which may override it) and This is me.
    admins = (access.identity_from_env(values).admins | access.identity_from_env(os.environ).admins
              | frozenset(a["id"] for a in data["approved"] if a.get("admin")))

    def admin_there(chat_id: str) -> bool:
        return bool(access.entries_on(channels.platform_of(chat_id), admins))

    def row(r: dict) -> dict:
        # The stored text is cleaned once more: the file is the page's input too.
        return {"platform": str(r.get("platform") or ""), "kind": r.get("kind"),
                "name": approvals.clean_text(r.get("name"), approvals.NAME_CHARS),
                "at": float(r.get("at") or 0), "id": str(r["id"]),
                "unverified": approvals.unverified(str(r["id"]))}

    # No code: This is me asks for the one the owner's own chat received.
    waiting = [{**row(w), "words": approvals.clean_text(w.get("words"), approvals.WORDS_CHARS),
                "hasAdmin": admin_there(str(w["id"]))}
               for w in sorted(data["waiting"], key=lambda w: float(w.get("at") or 0))]
    full = sorted({f"{w['platform']}:{w['kind']}" for w in waiting
                   if sum(1 for o in waiting if (o["platform"], o["kind"]) == (w["platform"], w["kind"]))
                   >= approvals.MAX_WAITING[w["kind"]]})
    return {"waiting": waiting, "full": full,
            "approved": [{**row(a), "admin": bool(a.get("admin"))} for a in reversed(data["approved"])],
            "declined": [row(d) for d in reversed(data["declined"])],
            "policy": sorted(approvals.current_policy(workspace.home)),
            "policyLocked": approvals.policy_locked()}


def _chat_id(payload: dict) -> str:
    chat_id = payload.get("id")
    if not isinstance(chat_id, str) or not 0 < len(chat_id) <= approvals.ID_CHARS:
        raise ValueError("approvals_bad_request")
    return chat_id


def decide(workspace, payload: dict) -> dict:
    chat_id, action, typed = _chat_id(payload), payload.get("action"), payload.get("code", "")
    if action not in approvals.ACTIONS or not isinstance(typed, str) or len(typed) > 32:
        raise ValueError("approvals_bad_request")
    try:
        entry = _store(workspace).decide(action, chat_id=chat_id, typed=typed)
    except LookupError:
        raise ValueError("approvals_gone") from None
    except approvals.Refused as refused:
        raise ValueError(str(refused)) from None
    except OSError:
        raise ValueError("approvals_write_failed") from None
    return {**overview(workspace), "decided": {"action": action, "kind": entry.get("kind")}}


def undo(workspace, payload: dict) -> dict:
    chat_id = _chat_id(payload)
    try:
        if not _store(workspace).undo(chat_id):
            raise ValueError("approvals_gone")
    except OSError:
        raise ValueError("approvals_write_failed") from None
    return overview(workspace)


def policy(workspace, payload: dict) -> dict:
    kind, on = payload.get("platform"), payload.get("approve")
    known = {p.kind for p in conn.PLATFORMS}
    if (not isinstance(kind, str) or kind not in known or kind in access.NOTHING_TO_APPROVE
            or not isinstance(on, bool)):
        raise ValueError("approvals_bad_request")
    try:
        approvals.set_policy(workspace.home, kind, on)
    except approvals.PolicyLocked:
        raise ValueError("approvals_env_locked") from None
    except OSError:
        raise ValueError("approvals_write_failed") from None
    return overview(workspace)


def mount(app, workspace, body) -> None:
    def one_at_a_time(work):
        def run(payload: dict) -> dict:
            if not _busy.acquire(blocking=False):
                raise ValueError("busy")
            try:
                return work(workspace, payload)
            finally:
                _busy.release()
        return run

    @app.get("/api/approvals")
    async def approvals_overview():
        return await asyncio.to_thread(overview, workspace)

    def route(path: str, work) -> None:
        async def handler(request: Request):
            return await asyncio.to_thread(one_at_a_time(work), await body(request))
        app.post(f"/api/approvals/{path}")(handler)

    for path, work in {"decide": decide, "undo": undo, "policy": policy}.items():
        route(path, work)
