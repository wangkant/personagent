"""The agents panel: the character in coding assistants, and an AstrBot the user already runs."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import threading

from fastapi import Request

from .. import coding, langs, updates
from .. import connections as conn
from .. import setup_wizard as sw
from ..astrbot_install import AstrBotInstallation
from ..storage import atomic_write_text

# Error codes this panel raises as ValueError, which the page may show.
ERRORS: frozenset[str] = frozenset({
    "agents_bad_target", "agents_no_cli", "agents_cli_failed", "agents_no_dsh", "agents_no_codex",
    "agents_no_react", "agents_write_failed", "agents_bad_cooldown", "agents_not_astrbot",
    "agents_astrbot_managed", "agents_bad_url", "agents_not_connected", "agents_bad_ids",
    "agents_service_failed",
})

TARGETS = ("claude-code", "codex", "dsh")
# Seconds between remarks the page offers for CODING_REACT_COOLDOWN_S.
COOLDOWNS = (600, 1800, 3600, 7200)
MAX_IDS = 500
CLAUDE_TIMEOUT_S = 60

# One change to another program's config at a time.
_busy = threading.Lock()


def _which(name: str) -> str | None:
    return shutil.which(name)


def _claude(args: list[str]) -> subprocess.CompletedProcess:
    """Run the claude CLI; tests and the window walk replace it with a recorder."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    return subprocess.run(args, capture_output=True, encoding="utf-8", errors="replace",
                          stdin=subprocess.DEVNULL, timeout=CLAUDE_TIMEOUT_S, check=False,
                          creationflags=flags)


def _launcher() -> list[str]:
    # The desktop icon runs pythonw, which has no stdout for the MCP server or the hook.
    launcher = coding._launcher()
    if launcher[0] == sys.executable:
        launcher[0] = updates._python()
    return launcher


def _hook_entry(home: Path, *, powershell: bool = False) -> dict:
    """coding._hook_entry, started with the console interpreter."""
    return coding._hook_entry(home, powershell=powershell, launcher=_launcher())


def _same(a, b) -> bool:
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


def _points_here(command: str, args: list, home: Path) -> bool:
    """A registration that starts this home with a program that still exists."""
    args = [str(a) for a in args]
    if "--home" not in args[:-1]:
        return False
    named = args[args.index("--home") + 1]
    return _same(named, home) and (Path(command).is_file() or bool(_which(command)))


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _hooked(path: Path) -> bool:
    hooks = _read_json(path).get("hooks")
    groups = hooks.get("Stop", []) if isinstance(hooks, dict) else []
    return any(coding._is_our_hook(hook) for group in groups if isinstance(group, dict)
               for hook in group.get("hooks", []) if isinstance(hook, dict))


def _claude_config() -> Path:
    # Where Claude Code keeps its user-scope MCP servers.
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(configured) / ".claude.json" if configured else Path.home() / ".claude.json"


def _dsh_profiles() -> list[Path]:
    return sorted((coding._config_dir("dsh") / "profiles").glob("*/cordis.patch.yml"))


def _json_line(pattern: str, text: str):
    found = re.search(pattern, text, re.M)
    try:
        return json.loads(found.group(1)) if found else None
    except ValueError:
        return None


def _status(home: Path, target: str) -> dict:
    """Read-only: is the assistant here, is the character in it, and our hook."""
    folder = coding._config_dir(target)
    if target == "claude-code":
        servers = _read_json(_claude_config()).get("mcpServers")
        server = servers.get(coding.SERVER_NAME) if isinstance(servers, dict) else None
        state = "off"
        if isinstance(server, dict):
            args = server.get("args") if isinstance(server.get("args"), list) else []
            state = "on" if _points_here(str(server.get("command") or ""), args, home) else "other"
        return {"id": target, "installed": bool(_which("claude")), "state": state,
                "react": _hooked(folder / "settings.json")}
    if target == "codex":
        try:
            text = (folder / "config.toml").read_text(encoding="utf-8-sig")
        except OSError:
            text = ""
        table = re.search(rf"^\[mcp_servers\.{coding.SERVER_NAME}\]\n((?:(?![ \t]*[\[#]).*\n?)*)", text, re.M)
        state = "off"
        if table:
            command = _json_line(r"^command = (.*)$", table.group(1))
            args = _json_line(r"^args = (.*)$", table.group(1))
            here = isinstance(args, list) and _points_here(str(command or ""), args, home)
            state = "on" if here else "other"
        return {"id": target, "installed": bool(_which("codex")) or folder.is_dir(), "state": state,
                "react": _hooked(folder / "hooks.json")}
    profiles = _dsh_profiles()
    listed = here = 0
    for profile in profiles:
        try:
            text = profile.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        entry = re.search(rf"^- insert:\n  - id: mcp-{coding.SERVER_NAME}\n((?:[ \t].*\n?)*)", text, re.M)
        if not entry:
            continue
        listed += 1
        command = _json_line(r"^ +command: (.*)$", entry.group(1))
        args = _json_line(r"^ +args: (.*)$", entry.group(1))
        if isinstance(args, list) and _points_here(str(command or ""), args, home):
            here += 1
    state = ("off" if not listed else "on" if here == len(profiles)
             else "partial" if here else "other")
    return {"id": target, "installed": bool(profiles), "state": state, "react": None,
            "profiles": len(profiles), "connected": here}


def _register_claude(argv: list[str]) -> None:
    claude = _which("claude")
    if not claude:
        raise ValueError("agents_no_cli")
    servers = _read_json(_claude_config()).get("mcpServers")
    old = servers.get(coding.SERVER_NAME) if isinstance(servers, dict) else None
    try:
        # Absent the first time, which is fine: only the add has to work.
        _claude([claude, "mcp", "remove", coding.SERVER_NAME, "--scope", "user"])
        if argv:
            added = _claude([claude, "mcp", "add", "--scope", "user", coding.SERVER_NAME, "--", *argv])
            if added.returncode:
                print(langs.term("claude mcp add failed: ") + (added.stderr or added.stdout or "").strip()[:500],
                      file=sys.stderr, flush=True)
                raise ValueError("agents_cli_failed")
    except (OSError, subprocess.SubprocessError, ValueError):
        if argv and isinstance(old, dict):
            # A failed repair must not leave the user with less than before.
            try:
                _claude([claude, "mcp", "add-json", "--scope", "user", coding.SERVER_NAME,
                         json.dumps(old, ensure_ascii=False)])
            except (OSError, subprocess.SubprocessError):
                pass
        raise ValueError("agents_cli_failed") from None


def apply(home: Path, target: str, *, connect: bool, react: bool) -> None:
    """coding.connect for the page: coded errors instead of printed sentences."""
    if target == "dsh" and react and connect:
        raise ValueError("agents_no_react")
    home = home.resolve()
    argv = [*_launcher(), "--home", str(home), "mcp"] if connect else []
    hook = react and connect
    folder = coding._config_dir(target)
    try:
        if target == "claude-code":
            _register_claude(argv)
            # Claude Code can name the shell, which keeps a path with a space working on Windows.
            coding._write_hook(folder / "settings.json",
                               _hook_entry(home, powershell=os.name == "nt") if hook else None)
        elif target == "dsh":
            profiles = _dsh_profiles()
            if not profiles:
                raise ValueError("agents_no_dsh")
            for profile in profiles:
                coding._write_dsh_server(profile, argv)
        else:
            # Writing creates ~/.codex, which would make Codex look installed.
            if connect and not (_which("codex") or folder.is_dir()):
                raise ValueError("agents_no_codex")
            coding._write_codex_server(folder / "config.toml", argv)
            coding._write_hook(folder / "hooks.json", _hook_entry(home) if hook else None)
    except (OSError, json.JSONDecodeError, AttributeError):
        raise ValueError("agents_write_failed") from None


def _cooldown(values: dict) -> int:
    try:
        return int(values.get("CODING_REACT_COOLDOWN_S") or coding.DEFAULT_REACT_COOLDOWN_S)
    except ValueError:
        return coding.DEFAULT_REACT_COOLDOWN_S


# ---- an AstrBot the user already runs

def _managed(workspace) -> Path:
    return AstrBotInstallation(workspace.home).root / "data"


def _memory(workspace) -> Path:
    return workspace.home / "runtime" / "desktop" / "agents.json"


def _remembered(workspace) -> Path | None:
    saved = str(_read_json(_memory(workspace)).get("astrbot") or "")
    return Path(saved) if saved else None


def _remember(workspace, data: Path | None) -> None:
    path = _memory(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps({"astrbot": str(data) if data else ""}, ensure_ascii=False))


def _found(workspace) -> Path | None:
    """The first AstrBot on the usual paths that is not the one this app manages."""
    for root in sw.astrbot_roots():
        try:
            found = sw.resolve_astrbot_data(root)
        except OSError:
            continue
        if found and not _same(found, _managed(workspace)):
            return found
    return None


def _ours(data: Path, token: str) -> bool:
    return (bool(token) and (data / "plugins" / sw.PLUGIN_NAME).is_dir()
            and str(sw.read_astrbot_config(data).get("connector_token") or "") == token)


def _loopback(url: str) -> bool:
    return bool(re.match(r"^http://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?/?$", url.strip()))


def _astrbot(workspace) -> dict:
    token = workspace.config().get("CONNECTOR_TOKEN", "")
    saved = _remembered(workspace)
    try:
        saved = sw.resolve_astrbot_data(saved) if saved else None
    except OSError:
        saved = None
    data = saved if saved and _ours(saved, token) else (_found(workspace) or saved)
    connected = bool(data) and _ours(data, token)
    cfg = sw.read_astrbot_config(data) if connected else {}
    url = str(cfg.get("personagent_url") or "")
    return {"folder": str(data or ""), "connected": connected,
            "docker": bool(data) and sw.astrbot_in_docker(data),
            "url": "" if _loopback(url) else url,
            "groups": [str(g) for g in cfg.get("groups") or []],
            "dmUsers": [str(u) for u in cfg.get("dm_users") or []]}


def _folder(workspace, raw) -> Path:
    raw = str(raw or "").strip()
    if not raw or len(raw) > 1024 or "\x00" in raw:
        raise ValueError("agents_not_astrbot")
    try:
        data = sw.resolve_astrbot_data(Path(raw))
    except (OSError, ValueError):
        data = None
    if data is None:
        raise ValueError("agents_not_astrbot")
    if _same(data, _managed(workspace)):
        raise ValueError("agents_astrbot_managed")
    return data.resolve()


def _idle(workspace) -> None:
    if workspace._future is not None and not workspace._future.done():
        raise ValueError("busy")


def _drop_qq(workspace, routed: bool) -> bool:
    """CONNECTOR_QQ_PLATFORMS once the external plugin is gone; True when it changed."""
    current = sw.split_ids(workspace.config().get("CONNECTOR_QQ_PLATFORMS", ""))
    kept = [p for p in current if p != "aiocqhttp" or routed]
    if kept == current:
        return False
    sw.write_env(workspace.env, {"CONNECTOR_QQ_PLATFORMS": ",".join(kept)})
    return True


def _connect_astrbot(workspace, payload: dict) -> None:
    data = _folder(workspace, payload.get("dataDir"))
    url = str(payload.get("url") or "").strip()
    _idle(workspace)
    if not workspace.config().get("LLM_API_KEY"):
        raise ValueError("key_required")
    token = workspace.config().get("CONNECTOR_TOKEN", "")
    if url and (len(url) > 512 or "${" in url or not sw.personagent_url_accepted(url, token or "token")):
        raise ValueError("agents_bad_url")
    try:
        if not token:
            sw.write_env(workspace.env, {"CONNECTOR_TOKEN": secrets.token_urlsafe(32)})
            workspace._restart_agent()
        # The service picks its port as it starts, and the plugin posts to that port.
        workspace.services.start_agent()
    except Exception:
        raise ValueError("agents_service_failed") from None
    port = workspace.config().get("SERVER_PORT") or "8080"
    old = str(sw.read_astrbot_config(data).get("personagent_url") or "")
    if not url and _loopback(old) and not old.rstrip("/").endswith(f":{port}"):
        url = f"http://127.0.0.1:{port}"
    before = workspace.config().get("CONNECTOR_QQ_PLATFORMS", "")
    values: dict = {}
    try:
        sw.connect_astrbot(workspace.env, values, data_dir=data, qq=None, groups=None,
                           dm_users=None, url_override=url)
        sw.write_env(workspace.env, values)
    except OSError:
        raise ValueError("agents_write_failed") from None
    _remember(workspace, data)
    if values.get("CONNECTOR_QQ_PLATFORMS", before) != before:
        workspace._restart_agent()


def _remove_astrbot(workspace, payload: dict) -> None:
    data = _folder(workspace, payload.get("dataDir"))
    _idle(workspace)
    plugin = data / "plugins" / sw.PLUGIN_NAME
    if not plugin.is_dir():
        raise ValueError("agents_not_connected")
    try:
        shutil.rmtree(plugin)
        sw.astrbot_config_path(data).unlink(missing_ok=True)
    except OSError:
        raise ValueError("agents_write_failed") from None
    _remember(workspace, None)
    if _drop_qq(workspace, "aiocqhttp" in conn.connected(_managed(workspace))):
        workspace._restart_agent()


def _ids(value) -> list[str]:
    if isinstance(value, str):
        items = sw.split_ids(value)
    elif isinstance(value, list):
        items = [str(v).strip() for v in value if str(v).strip()]
    else:
        raise ValueError("agents_bad_ids")
    if len(items) > MAX_IDS or any(len(i) > 128 or any(c.isspace() for c in i) or "${" in i
                                   for i in items):
        raise ValueError("agents_bad_ids")
    return list(dict.fromkeys(items))


def _allow_astrbot(workspace, payload: dict) -> None:
    data = _folder(workspace, payload.get("dataDir"))
    groups, dm_users = _ids(payload.get("groups", [])), _ids(payload.get("dmUsers", []))
    if not _ours(data, workspace.config().get("CONNECTOR_TOKEN", "")):
        raise ValueError("agents_not_connected")
    cfg = sw.read_astrbot_config(data)
    cfg.update(groups=groups, dm_users=dm_users)
    try:
        sw.write_astrbot_config(data, cfg)
    except OSError:
        raise ValueError("agents_write_failed") from None


def mount(app, workspace, body) -> None:
    def overview() -> dict:
        values = workspace.config()
        return {"coding": [_status(workspace.home, target) for target in TARGETS],
                "cooldown": _cooldown(values), "cooldowns": list(COOLDOWNS),
                "name": values.get("PERSONA_NAME", ""), "astrbot": _astrbot(workspace)}

    def one_at_a_time(work):
        def run(payload: dict) -> dict:
            if not _busy.acquire(blocking=False):
                raise ValueError("busy")
            try:
                work(payload)
            finally:
                _busy.release()
            return overview()
        return run

    def change(payload: dict) -> None:
        target = str(payload.get("target") or "")
        if target not in TARGETS:
            raise ValueError("agents_bad_target")
        connect = payload.get("connect") is True
        if connect and not workspace.config().get("LLM_API_KEY"):
            raise ValueError("key_required")
        react = payload.get("react")
        if react is None:
            # A connect without react would drop a hook the user wanted.
            react = bool(_status(workspace.home, target)["react"])
        apply(workspace.home, target, connect=connect, react=react is True)

    def cooldown(payload: dict) -> None:
        seconds = payload.get("seconds")
        if isinstance(seconds, bool) or seconds not in COOLDOWNS:
            raise ValueError("agents_bad_cooldown")
        _idle(workspace)
        sw.write_env(workspace.env, {"CODING_REACT_COOLDOWN_S": str(seconds)})

    routes = {"coding": change, "cooldown": cooldown,
              "astrbot": lambda p: _connect_astrbot(workspace, p),
              "astrbot/remove": lambda p: _remove_astrbot(workspace, p),
              "astrbot/allow": lambda p: _allow_astrbot(workspace, p)}

    @app.get("/api/agents")
    async def agents_overview():
        return await asyncio.to_thread(overview)

    def route(path: str, work) -> None:
        async def handler(request: Request):
            return await asyncio.to_thread(one_at_a_time(work), await body(request))
        app.post(f"/api/agents/{path}")(handler)

    for path, work in routes.items():
        route(path, work)
