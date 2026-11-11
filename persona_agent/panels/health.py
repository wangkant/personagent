"""The health panel: service probes, settings findings, start failures and logs."""
from __future__ import annotations

import asyncio
import json
import locale
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

import httpx
from dotenv import dotenv_values
from fastapi import Request

from .. import connections as conn
from .. import home as homes
from .. import setup_wizard as sw
from ..astrbot_install import AstrBotInstallation
from ..direct import base as direct_base

# Error codes this panel raises as ValueError, which the page may show.
ERRORS: frozenset[str] = frozenset({"health_busy", "health_failed", "health_invalid_log",
                                    "health_open_failed", "health_nothing_to_fix"})

# The logs under <home>/runtime/desktop the page may read; never a client path.
LOGS = ("agent", "astrbot", "direct", "install", "app", "practice", "update")
SERVICES = ("agent", "astrbot", "direct")
PROBES = {"Ledger sizes": "ledger", "DM chat": "dm", "Group replies": "chat",
          "Web search decision": "searchdecide", "Reaction judge": "react",
          "Learning decisions": "decide", "Reviewing its own replies": "evolve", "Vision": "vision", "Eval": "eval", "Embeddings": "embeddings",
          "Web search (Tavily)": "search", "OneBot bridge": "onebot"}
# Probes retry and run concurrently; their worst case is about 90 s.
CHECK_TIMEOUT = 150
# The service caches its own probes this long; the page does the same.
REUSE_SECONDS = 60
TAIL_BYTES = 256_000
MAX_LINES = 200
DETAIL_LIMIT = 200

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|COOKIE|CREDENTIAL", re.I)
_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+/=-]{8,})"),
    re.compile(r"(?i)((?:api[_-]?key|access[_-]?token|app[_-]?secret|client[_-]?secret|token|secret|"
               r"password|authorization)[\"']?\s*[:=]\s*[\"']?)([^\s\"',;&}]{4,})"),
    re.compile(r"()(\bsk-[A-Za-z0-9_-]{8,})"),
    # No \b: inside a URL the token follows "bot" with no word boundary.
    re.compile(r"()((?<![0-9])\d{6,}:[A-Za-z0-9_-]{30,})"),
    re.compile(r"()(\b[A-Za-z0-9_-]{40,})"),
)
_PROBLEM = re.compile(r"^personagent: (.+)")
_RAISED = re.compile(r"^[A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt)\b.*")


def _astrbot_secrets(home: Path) -> set[str]:
    """Credentials of the platforms in the managed AstrBot's config (connections.connected's file)."""
    path = AstrBotInstallation(home).root / "data" / "cmd_config.json"
    try:
        cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return set()
    specs = {p.kind: p for p in conn.PLATFORMS}
    found = set()
    for item in cfg.get("platform", []) if isinstance(cfg, dict) else []:
        if not isinstance(item, dict):
            continue
        spec = specs.get(item.get("type"))
        secret = {f.key for f in spec.fields if f.secret} if spec else set()
        for key, value in item.items():
            text = str(value) if isinstance(value, (str, int)) and not isinstance(value, bool) else ""
            if len(text) >= 6 and (key in secret or _SECRET_NAME.search(str(key))):
                found.add(text)
    return found


class _Masker:
    """Hides the home's own secrets and anything shaped like a key or token."""

    def __init__(self, home: Path):
        values = {k: str(v or "") for k, v in dotenv_values(home / ".env").items()}
        known = {v for k, v in values.items() if _SECRET_NAME.search(k) and len(v) >= 6}
        for fields in direct_base.load_credentials(home).values():
            if isinstance(fields, dict):
                known |= {str(v) for v in fields.values() if isinstance(v, (str, int)) and len(str(v)) >= 6}
        known |= _astrbot_secrets(home)
        # Longest first, so a key that contains another is hidden whole.
        self.known = sorted(known, key=len, reverse=True)

    def __call__(self, text: str) -> str:
        for value in self.known:
            if value in text:
                text = text.replace(value, sw.mask_secret(value))
        for pattern in _PATTERNS:
            text = pattern.sub(lambda m: m.group(1) + sw.mask_secret(m.group(2)), text)
        return text


def _logs_dir(home: Path) -> Path:
    return home / "runtime" / "desktop"


def _decode(line: bytes) -> str:
    # A child's stderr may be in the system code page (GBK on Chinese Windows).
    try:
        return line.decode("utf-8")
    except UnicodeDecodeError:
        return line.decode(locale.getpreferredencoding(False) or "utf-8", "replace")


def tail(home: Path, name: str, lines: int) -> list[str]:
    """The last `lines` lines of one log, colour codes removed; [] when absent."""
    path = _logs_dir(home) / f"{name}.log"
    try:
        with path.open("rb") as stream:
            size = stream.seek(0, 2)
            stream.seek(max(0, size - TAIL_BYTES))
            raw = stream.read()
    except OSError:
        return []
    rows = [_ANSI.sub("", _decode(line)) for line in raw.splitlines()]
    if size > TAIL_BYTES:
        rows = rows[1:]
    return rows[-lines:]


def last_words(home: Path, name: str) -> str:
    """The one line that best says why `name` stopped: its own refusal, else
    the exception it ended on, else its last line."""
    rows = [r.strip() for r in tail(home, name, 80) if r.strip()]
    for row in reversed(rows):
        found = _PROBLEM.match(row)
        if found:
            return found.group(1)
    for row in reversed(rows):
        if _RAISED.match(row):
            return row
    return rows[-1] if rows else ""


def _clip(text: str) -> str:
    return text if len(text) <= DETAIL_LIMIT else text[:DETAIL_LIMIT - 1] + "…"


def _reason(detail: str) -> str:
    """What kind of failure a probe's one-line detail names."""
    if re.search(r"\b(401|403)\b|Unauthori[sz]ed|Forbidden", detail):
        return "key"
    if re.search(r"\b429\b|Too Many|quota", detail, re.I):
        return "limit"
    if re.search(r"\b404\b|Not Found", detail):
        return "missing"
    if re.search(r"URLError|timed out|Timeout|ConnectionError|refused|10061|getaddrinfo|"
                 r"Name or service|RemoteDisconnected|SSL", detail, re.I):
        return "unreachable"
    return "other"


def _service(row: dict, mask: _Masker) -> dict:
    name = str(row.get("name") or "")
    ok = row.get("ok")
    ok = ok if ok in (True, False) else None
    detail = _clip(mask(str(row.get("detail") or "")))
    try:
        ms = max(0, int(row.get("ms") or 0))
    except (TypeError, ValueError):
        ms = 0
    return {"id": PROBES.get(name, "other"), "name": _clip(name), "ok": ok,
            "critical": bool(row.get("critical")), "ms": ms, "detail": detail,
            "reason": _reason(detail) if ok is False else ""}


def doctor_env(home: Path) -> dict:
    """The environment the character itself starts with (Services.start_agent)."""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env.update({k: v for k, v in dotenv_values(home / ".env").items() if v is not None})
    env["AGENT_HOME"] = str(home)
    return env


def run_doctor(home: Path) -> list[dict]:
    """`doctor --json` in a child: probes read os.environ, which in this
    process is not the home's .env."""
    cwd = homes.CHECKOUT if homes.is_checkout() else home
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        done = subprocess.run([sys.executable, "-m", "persona_agent", "--home", str(home), "doctor", "--json"],
                              cwd=cwd, env=doctor_env(home), stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=CHECK_TIMEOUT, creationflags=flags)
    except (OSError, subprocess.SubprocessError):
        raise ValueError("health_failed") from None
    text = done.stdout.decode("utf-8", "replace")
    try:
        services = json.loads(text[text.index("{"):])["services"]
    except (ValueError, KeyError, TypeError):
        raise ValueError("health_failed") from None
    if not isinstance(services, list):
        raise ValueError("health_failed")
    return [s for s in services if isinstance(s, dict)]


async def ask_agent(workspace) -> list[dict] | None:
    """The running character's own probes; None when it cannot answer them."""
    token = workspace.config().get("CONNECTOR_TOKEN", "")
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=CHECK_TIMEOUT) as client:
            response = await client.get(workspace.services.agent_url + "/health/details",
                                        headers={"X-Personagent-Token": token})
        services = response.json().get("services") if response.status_code in (200, 503) else None
    except (httpx.HTTPError, ValueError, AttributeError):
        return None
    return [s for s in services if isinstance(s, dict)] if isinstance(services, list) else None


def _finding_kind(level: str, key: str, detail: str) -> str:
    if key == "LLM_API_KEY" and level == "ERROR":
        return "missing_key"
    if key == ".env" and "BOM" in detail:
        return "bom"
    if detail.startswith("is not a setting"):
        return "unknown"
    if detail.startswith("is no longer read"):
        return "dropped"
    if detail.startswith("is empty"):
        return "empty"
    return "other"


def findings(home: Path, mask: _Masker, retired: set[str]) -> list[dict]:
    from .. import preflight

    rows = []
    for found in preflight.check_config(root=home):
        if found.level not in ("ERROR", "WARN") or found.key in retired:
            continue
        key = found.key if found.key.isprintable() else repr(found.key)
        rows.append({"level": found.level, "key": _clip(key), "detail": mask(found.detail),
                     "kind": _finding_kind(found.level, found.key, found.detail)})
    return rows


def failure(workspace, mask: _Masker) -> dict | None:
    """What failed to start or stopped on its own, and its own last words."""
    home, services = workspace.home, workspace.services
    dead = {name: p.returncode for name, p in list(services.processes.items())
            if name in SERVICES and p.poll() is not None and p.returncode}
    job = dict(workspace.job)
    error = str(job.get("error") or "") if job.get("state") == "error" else ""
    log = next((name for name in SERVICES if name in dead), "")
    if not log and error in ("download_failed", "setup_failed"):
        log = "install"
    elif not log and error == "service_failed":
        data = AstrBotInstallation(home).root / "data"
        log = ("agent" if not services.running("agent")
               else "astrbot" if conn.connected(data) and not services.running("astrbot") else "direct")
    if not log:
        return None
    return {"service": log, "error": error, "exitCode": dead.get(log),
            "said": _clip(mask(last_words(home, log)))}


def platforms(home: Path) -> list[dict]:
    from ..welcome import NAMED_REFUSALS

    stored = direct_base.load_credentials(home)
    states = direct_base.read_status(home)
    rows = []
    for spec in conn.PLATFORMS:
        if spec.kind not in stored:
            continue
        state = states.get(spec.kind) if isinstance(states.get(spec.kind), dict) else {}
        kind = str(state.get("state") or "")
        detail = str(state.get("detail") or "")
        failed = kind in ("refused", "error")
        rows.append({"id": spec.kind, "name": list(spec.name), "state": kind, "failed": failed,
                     # Only codes the page explains; anything else may quote upstream text.
                     "reason": detail if detail in NAMED_REFUSALS else ("error" if failed else ""),
                     "since": int(state.get("since") or 0)})
    return rows


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(path))
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def mount(app, workspace, body) -> None:
    home = workspace.home
    gate = threading.Lock()
    last: dict = {"result": None, "stamp": None}

    def stamp() -> tuple:
        try:
            changed = (home / ".env").stat().st_mtime_ns
        except OSError:
            changed = 0
        return changed, workspace.services.running("agent")

    def state() -> dict:
        from .. import preflight

        mask = _Masker(home)
        retired = [{"old": old, "new": new, "where": where}
                   for old, new, where in preflight.retired_settings(root=home)]
        logs = []
        for name in LOGS:
            path = _logs_dir(home) / f"{name}.log"
            if path.is_file():
                info = path.stat()
                logs.append({"name": name, "size": info.st_size, "modified": int(info.st_mtime)})
        return {"agentRunning": workspace.services.running("agent"),
                "findings": findings(home, mask, {r["old"] for r in retired}),
                "retired": retired, "failure": failure(workspace, mask),
                "platforms": platforms(home), "logs": logs,
                "checking": gate.locked(), "last": last["result"]}

    @app.get("/api/health/state")
    async def health_state():
        return await asyncio.to_thread(state)

    @app.post("/api/health/check")
    async def health_check(request: Request):
        payload = await body(request)
        if not gate.acquire(blocking=False):
            raise ValueError("health_busy")
        try:
            now = stamp()
            kept = last["result"]
            if (kept and not payload.get("fresh") and last["stamp"] == now
                    and time.time() - kept["checkedAt"] < REUSE_SECONDS):
                return {**kept, "reused": True}
            via = "agent"
            rows = await ask_agent(workspace) if now[1] else None
            if rows is None:
                via = "doctor"
                rows = await asyncio.to_thread(run_doctor, home)
            mask = _Masker(home)
            services = [_service(row, mask) for row in rows]
            # A critical probe that never ran is not a pass, as in health.all_critical_ok.
            ok = not any(s["critical"] and s["ok"] is not True for s in services)
            result = {"ok": ok, "services": services, "checkedAt": int(time.time()), "via": via}
            last.update(result=result, stamp=stamp())
            return {**result, "reused": False}
        finally:
            gate.release()

    @app.get("/api/health/log")
    async def health_log(name: str = "", lines: int = 80):
        if name not in LOGS:
            raise ValueError("health_invalid_log")
        count = min(max(lines, 10), MAX_LINES)

        def read() -> dict:
            mask = _Masker(home)
            path = _logs_dir(home) / f"{name}.log"
            return {"name": name, "exists": path.is_file(),
                    "lines": [mask(row) for row in tail(home, name, count)]}
        return await asyncio.to_thread(read)

    @app.post("/api/health/fix")
    async def health_fix(request: Request):
        await body(request)

        def fix() -> dict:
            from .. import preflight

            with workspace._lock:
                if workspace._future is not None and not workspace._future.done():
                    raise ValueError("busy")
                if not any(where == ".env" for _, _, where in preflight.retired_settings(root=home)):
                    raise ValueError("health_nothing_to_fix")
                stuck = failure(workspace, _Masker(home)) is not None
                changes = preflight.migrate_env_file(workspace.env)
                workspace._restart_agent()
                # It refused to start on these names: start it again now they are fixed.
                started = False
                if stuck and not workspace.services.running("agent") and workspace.config().get("LLM_API_KEY"):
                    workspace.services.stop("agent")
                    workspace.start_job("start")
                    started = True
                remaining = [{"old": old, "new": new, "where": where}
                             for old, new, where in preflight.retired_settings(root=home)]
                return {"changes": [{"old": old, "new": new, "action": action}
                                    for old, new, action in changes],
                        "remaining": remaining, "backup": ".env.bak", "started": started}
        return await asyncio.to_thread(fix)

    @app.post("/api/health/open")
    async def health_open(request: Request):
        payload = await body(request)
        folder = payload.get("folder")
        target = _logs_dir(home) if folder == "logs" else home if folder == "home" else None
        if target is None:
            raise ValueError("health_open_failed")
        try:
            await asyncio.to_thread(open_folder, target)
        except OSError:
            raise ValueError("health_open_failed") from None
        return {"ok": True}
