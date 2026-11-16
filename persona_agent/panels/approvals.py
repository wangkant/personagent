"""The approvals panel: new chats waiting for the admin, on the platforms that
ask for approval (approvals.py), and the switch that makes a platform ask."""
from __future__ import annotations

import asyncio
import threading

from fastapi import Request

from .. import access, approvals, channels, connections as conn

ERRORS: frozenset[str] = frozenset({
    "approvals_gone", "approvals_bad_request", "approvals_write_failed", "approvals_not_dm",
})

# One decision at a time: each one rewrites .env.
_busy = threading.Lock()


def overview(workspace) -> dict:
    values = workspace.config()
    data = approvals.Store(approvals.home_path(workspace.home)).snapshot()
    identity = access.identity_from_env(values)

    def admin_there(chat_id: str) -> bool:
        return bool(access.entries_on(channels.platform_of(chat_id), identity.admins))

    # The stored words are cleaned once more: the file is the page's input too.
    waiting = [{"code": w["code"], "platform": str(w.get("platform") or ""), "kind": w.get("kind"),
                "name": approvals.clean_text(w.get("name"), approvals.NAME_CHARS),
                "words": approvals.clean_text(w.get("words"), approvals.WORDS_CHARS),
                "at": float(w.get("at") or 0), "id": str(w["id"]),
                "hasAdmin": admin_there(str(w["id"]))}
               for w in sorted(data["waiting"], key=lambda w: float(w.get("at") or 0))]
    declined = [{"id": str(d["id"]), "platform": str(d.get("platform") or ""), "kind": d.get("kind"),
                 "name": approvals.clean_text(d.get("name"), approvals.NAME_CHARS),
                 "at": float(d.get("at") or 0)}
                for d in reversed(data["declined"])]
    return {"waiting": waiting, "declined": declined,
            "policy": sorted(approvals.policy(values))}


def decide(workspace, payload: dict) -> dict:
    code, action = payload.get("code"), payload.get("action")
    if not isinstance(code, str) or not 0 < len(code) <= 32 or action not in approvals.ACTIONS:
        raise ValueError("approvals_bad_request")
    try:
        entry = approvals.Store(approvals.home_path(workspace.home)).decide(code, action, workspace.home)
    except LookupError:
        raise ValueError("approvals_gone") from None
    except ValueError:
        raise ValueError("approvals_not_dm") from None
    except OSError:
        raise ValueError("approvals_write_failed") from None
    return {**overview(workspace), "decided": {"action": action, "kind": entry.get("kind")}}


def undo(workspace, payload: dict) -> dict:
    chat_id = payload.get("id")
    if not isinstance(chat_id, str) or not 0 < len(chat_id) <= 200:
        raise ValueError("approvals_bad_request")
    try:
        if not approvals.Store(approvals.home_path(workspace.home)).undo(chat_id):
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
