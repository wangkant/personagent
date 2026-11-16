"""Tools from MCP servers the admin adds.

The servers are listed in `<home>/mcp.json`, in the shape every MCP server's
README gives (`{"mcpServers": {"name": {...}}}`), plus a `personagent` block
per server that holds what personagent adds per tool: on or off, and who may
cause it to be used (the admin only, the default, or anyone the character
answers). `env` and `headers` values are secrets: the file is private and
they are never logged or returned to the page.

The character service runs the servers (`ToolHub`); the page and
`personagent tools` check and try them on their own connection.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from . import langs
from .mcp_client import McpError, ToolResult, connect, describe, find_program
from .storage import FileLock, LockUnavailable, atomic_write_text
from .textproc import _WEB_DESC_CLOSE, _WEB_DESC_OPEN, _clean_prompt_source, scrub_third_party_text

logger = logging.getLogger("agent.tools")

CONFIG_FILE = "mcp.json"
ADMIN, ANYONE = "admin", "anyone"
WHO = (ADMIN, ANYONE)
MAX_SERVERS = 20
#: Tools offered to one decision request, over all servers.
MAX_OFFERED = 24
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,39}")
TOOL_NAME_CHARS = 128
ENV_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
HEADER_NAME_RE = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]{1,128}")
MAX_ARGS, MAX_ARG_CHARS, MAX_VALUE_CHARS, MAX_PAIRS = 64, 4096, 8192, 64
DESCRIPTION_CHARS = 1000
OFFER_DESCRIPTION_CHARS = 300
PROPERTY_DESCRIPTION_CHARS = 150
SCHEMA_CHARS = 20_000
#: What enters the reply's prompt of one result, and what the page shows.
PROMPT_RESULT_CHARS = 3000
PAGE_RESULT_CHARS = 20_000
#: Seconds: a server's start (uvx may first download it), a call in a turn, a call by hand.
START_TIMEOUT_S = 60.0
LIST_TIMEOUT_S = 20.0
TURN_CALL_TIMEOUT_S = 20.0
HAND_CALL_TIMEOUT_S = 60.0
#: What the first turn outside the service waits for the servers it starts.
FIRST_START_WAIT_S = 30.0
#: Restarts of a server that stopped: doubling from the first, up to the last.
BACKOFF_S = (2.0, 300.0)
#: A server that ran this long starts its backoff over.
HEALTHY_S = 60.0
WATCH_S = 3.0
#: Ready-made servers from the official reference set, offered where uvx is found.
STARTERS = {
    "time": {"command": "uvx", "args": ["mcp-server-time"]},
    "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
}


class ToolsError(ValueError):
    """A refusal the page and the terminal name; `str()` is its code."""


# ------------------------------------------------------------------ files --

def config_path(home: Path) -> Path:
    return Path(home) / CONFIG_FILE


def state_dir(home: Path) -> Path:
    return Path(home) / "runtime" / "tools"


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_config(home: Path) -> dict:
    """{"mcpServers": {name: spec}}; servers that do not read as one are left
    out, and one marked `"disabled": true` carries `disabled`."""
    raw = _read(config_path(home)).get("mcpServers")
    servers = {}
    for name, spec in (raw.items() if isinstance(raw, dict) else ()):
        try:
            servers[_server_name(name)] = {**normalize(spec), "personagent": _own_block(spec)}
        except ToolsError:
            logger.warning("[Tools] the server %r in %s is not one that can be run; it is skipped",
                           str(name)[:40], CONFIG_FILE)
            continue
        if spec.get("disabled") is True:
            servers[_server_name(name)]["disabled"] = True
    return {"mcpServers": servers}


def _raw_config(home: Path) -> dict:
    """The file as written, for a change that must keep everything else in it."""
    path = config_path(home)
    if not path.exists():
        return {"mcpServers": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise ToolsError("tools_file_damaged") from None
    if not isinstance(data, dict) or not isinstance(data.setdefault("mcpServers", {}), dict):
        raise ToolsError("tools_file_damaged")
    return data


def save_config(home: Path, config: dict) -> None:
    try:
        atomic_write_text(config_path(home), json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    except OSError:
        raise ToolsError("tools_write_failed") from None


def _own_block(spec) -> dict:
    block = spec.get("personagent") if isinstance(spec, dict) else None
    tools = block.get("tools") if isinstance(block, dict) else None
    out = {}
    for name, row in (tools.items() if isinstance(tools, dict) else ()):
        if isinstance(name, str) and isinstance(row, dict):
            out[name[:TOOL_NAME_CHARS]] = {"enabled": row.get("enabled") is not False,
                                           "who": ANYONE if row.get("who") == ANYONE else ADMIN}
    return {"tools": out}


def tool_setting(spec: dict, tool: str) -> dict:
    """A tool's switch and who may use it; a tool never set is on, for the admin only."""
    row = (spec.get("personagent") or {}).get("tools", {}).get(tool)
    return dict(row) if row else {"enabled": True, "who": ADMIN}


def _locked_update(path: Path, change) -> None:
    """Read-modify-write one of the small state files; skipped when another holds it."""
    try:
        with FileLock(path.with_name("." + path.name + ".lock"), timeout=2.0):
            data = _read(path)
            change(data)
            atomic_write_text(path, json.dumps(data, ensure_ascii=False), fsync=False)
    except (LockUnavailable, OSError) as e:
        logger.debug("[Tools] %s not written: %s", path.name, e)


def catalog_key(spec: dict) -> str:
    """What a tool list belongs to: the program or address, without secret values."""
    shown = {"command": spec.get("command", ""), "args": spec.get("args", []),
             "url": spec.get("url", ""), "env": sorted(spec.get("env") or {}),
             "headers": sorted(spec.get("headers") or {})}
    return hashlib.sha256(json.dumps(shown, sort_keys=True).encode()).hexdigest()[:16]


def run_key(spec: dict) -> str:
    """Changes with anything that needs the server restarted, secrets included; kept in memory only."""
    plain = {k: v for k, v in spec.items() if k != "personagent"}
    return hashlib.sha256(json.dumps(plain, sort_keys=True).encode()).hexdigest()


def remember_tools(home: Path, name: str, spec: dict, tools: list[dict]) -> None:
    def change(data: dict) -> None:
        data[name] = {"key": catalog_key(spec), "tools": tools, "at": time.time()}
    _locked_update(state_dir(home) / "catalog.json", change)


def known_tools(home: Path, name: str, spec: dict) -> Optional[list[dict]]:
    """The last tool list read for this server as it is configured now; None when never read."""
    row = _read(state_dir(home) / "catalog.json").get(name)
    if not isinstance(row, dict) or row.get("key") != catalog_key(spec):
        return None
    tools = row.get("tools")
    return [t for t in tools if isinstance(t, dict)] if isinstance(tools, list) else None


def read_status(home: Path) -> dict:
    """What the running service last wrote about its servers."""
    return _read(state_dir(home) / "status.json")


# -------------------------------------------------------------- parsing --

def _server_name(name) -> str:
    name = str(name or "").strip()
    if not NAME_RE.fullmatch(name):
        raise ToolsError("tools_bad_name")
    return name


def _text(value, limit: int) -> str:
    if isinstance(value, bool) or value is None or isinstance(value, (dict, list)):
        raise ToolsError("tools_bad_snippet")
    text = str(value)
    if len(text) > limit or "\x00" in text:
        raise ToolsError("tools_bad_snippet")
    return text


def _pairs(value, name_re: re.Pattern) -> dict:
    if value in (None, {}):
        return {}
    if not isinstance(value, dict) or len(value) > MAX_PAIRS:
        raise ToolsError("tools_bad_snippet")
    out = {}
    for key, item in value.items():
        if not isinstance(key, str) or not name_re.fullmatch(key):
            raise ToolsError("tools_bad_snippet")
        out[key] = _text(item, MAX_VALUE_CHARS)
        if "\n" in out[key] or "\r" in out[key]:
            raise ToolsError("tools_bad_snippet")
    return out


def normalize(spec) -> dict:
    """One server as it is stored: a program (`command`, `args`, `env`, `cwd`)
    or an address (`url`, `headers`). Raises ToolsError."""
    if not isinstance(spec, dict):
        raise ToolsError("tools_bad_snippet")
    kind = str(spec.get("type") or spec.get("transport") or "").lower().replace("_", "-")
    if kind == "sse":
        raise ToolsError("tools_sse_unsupported")
    url = spec.get("url") or spec.get("serverUrl") or spec.get("httpUrl")
    if spec.get("command"):
        command = _text(spec["command"], 1024).strip()
        args = spec.get("args") or []
        if isinstance(args, str) or not isinstance(args, list) or len(args) > MAX_ARGS:
            raise ToolsError("tools_bad_snippet")
        out = {"command": command, "args": [_text(a, MAX_ARG_CHARS) for a in args]}
        env = _pairs(spec.get("env"), ENV_NAME_RE)
        if env:
            out["env"] = env
        if spec.get("cwd"):
            out["cwd"] = _text(spec["cwd"], 1024)
        if not command:
            raise ToolsError("tools_bad_snippet")
        return out
    if url:
        url = _text(url, 2048).strip()
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
            raise ToolsError("tools_bad_url")
        if parts.path.rstrip("/").endswith("/sse") and kind not in ("http", "streamable-http", "streamablehttp"):
            raise ToolsError("tools_sse_unsupported")
        out = {"url": url}
        headers = _pairs(spec.get("headers"), HEADER_NAME_RE)
        if headers:
            out["headers"] = headers
        return out
    raise ToolsError("tools_bad_snippet")


def _guess_name(spec: dict) -> str:
    """A name for a server pasted without one: its package or its host."""
    if spec.get("command"):
        words = [a for a in spec.get("args", []) if not a.startswith("-")]
        word = words[0] if words else spec["command"]
        # @scope/name@1.2 -> name; a path -> its last part.
        base = re.sub(r"(?<=.)@[^@/\\]*$", "", word).replace("\\", "/").split("/")[-1]
        base = re.sub(r"\.(exe|cmd|bat|py|js)$", "", base, flags=re.IGNORECASE)
        for prefix in ("mcp-server-", "server-", "mcp-"):
            if base.startswith(prefix) and len(base) > len(prefix):
                base = base[len(prefix):]
                break
        for suffix in ("-mcp-server", "-mcp"):
            if base.endswith(suffix) and len(base) > len(suffix):
                base = base[:-len(suffix)]
                break
    else:
        base = (urlsplit(spec["url"]).hostname or "server").split(".")[0]
    base = re.sub(r"[^A-Za-z0-9_.-]", "-", base).strip("-.") or "server"
    return base[:40]


def parse_snippet(text: str, name: str = "") -> dict:
    """{name: spec} from what a README shows: the whole `{"mcpServers": …}`
    object, VS Code's `servers`, a bare `"name": {…}` entry, or one server's
    object (named `name`, else after its package)."""
    text = str(text or "").strip()
    if not text or len(text) > 100_000:
        raise ToolsError("tools_bad_snippet")
    data = None
    for attempt in (text, "{" + text.rstrip(",") + "}"):
        try:
            data = json.loads(attempt)
            break
        except ValueError:
            continue
    if not isinstance(data, dict):
        raise ToolsError("tools_bad_snippet")
    if isinstance(data.get("mcp"), dict) and isinstance(data["mcp"].get("servers"), dict):
        data = data["mcp"]
    for key in ("mcpServers", "servers", "context_servers"):
        if isinstance(data.get(key), dict):
            data = data[key]
            break
    if any(k in data for k in ("command", "url", "serverUrl", "httpUrl")):
        spec = normalize(data)
        return {_server_name(name) if name else _guess_name(spec): spec}
    if not data or not all(isinstance(v, dict) for v in data.values()):
        raise ToolsError("tools_bad_snippet")
    servers = {_server_name(key): normalize(value) for key, value in data.items()}
    if name and len(servers) == 1:
        servers = {_server_name(name): next(iter(servers.values()))}
    return servers


def add_servers(home: Path, servers: dict) -> list[str]:
    raw = _raw_config(home)
    have = raw["mcpServers"]
    for name in servers:
        if name in have:
            raise ToolsError("tools_name_taken")
    if len(have) + len(servers) > MAX_SERVERS:
        raise ToolsError("tools_too_many")
    for name, spec in servers.items():
        have[name] = {**spec, "personagent": {"tools": {}}}
    save_config(home, raw)
    return list(servers)


def remove_server(home: Path, name: str) -> None:
    raw = _raw_config(home)
    if raw["mcpServers"].pop(name, None) is None:
        raise ToolsError("tools_unknown_server")
    save_config(home, raw)

    def drop(data: dict) -> None:
        data.pop(name, None)
    _locked_update(state_dir(home) / "catalog.json", drop)


def set_tool(home: Path, server: str, tool: str, *, enabled: Optional[bool] = None,
             who: Optional[str] = None) -> dict:
    spec = load_config(home)["mcpServers"].get(server)
    if spec is None:
        raise ToolsError("tools_unknown_server")
    if not isinstance(tool, str) or not tool or len(tool) > TOOL_NAME_CHARS:
        raise ToolsError("tools_unknown_tool")
    if who is not None and who not in WHO:
        raise ToolsError("tools_bad_request")
    row = tool_setting(spec, tool)
    if enabled is not None:
        row["enabled"] = bool(enabled)
    if who is not None:
        row["who"] = who
    # Only this server's own block changes; every other key in the file stays as written.
    raw = _raw_config(home)
    entry = raw["mcpServers"][server]
    block = entry.get("personagent") if isinstance(entry.get("personagent"), dict) else {}
    tools = block.get("tools") if isinstance(block.get("tools"), dict) else {}
    entry["personagent"] = {**block, "tools": {**tools, tool: row}}
    save_config(home, raw)
    return row


# ----------------------------------------------------------- tool lists --

def clean_tool(raw: dict) -> Optional[dict]:
    """One tool as a server described it, bounded; None when it has no usable name."""
    name = raw.get("name")
    if not isinstance(name, str) or not name or len(name) > TOOL_NAME_CHARS:
        return None
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in name):
        return None
    description = scrub_third_party_text(raw.get("description") or "").strip()[:DESCRIPTION_CHARS]
    annotations = raw.get("annotations") if isinstance(raw.get("annotations"), dict) else {}
    title = raw.get("title") or annotations.get("title") or ""
    title = title if isinstance(title, str) else ""
    schema = raw.get("inputSchema")
    if not isinstance(schema, dict) or len(json.dumps(schema, ensure_ascii=False)) > SCHEMA_CHARS:
        schema = {"type": "object"}
    return {"name": name, "title": scrub_third_party_text(title).strip()[:100],
            "description": description, "inputSchema": schema}


def clean_tools(raw: list) -> list[dict]:
    seen, out = set(), []
    for item in raw:
        tool = clean_tool(item)
        if tool and tool["name"] not in seen:
            seen.add(tool["name"])
            out.append(tool)
    return out


# ------------------------------------------------------------- schemas --

_TYPES = {"string": lambda v: isinstance(v, str),
          "integer": lambda v: (isinstance(v, int) and not isinstance(v, bool))
          or (isinstance(v, float) and v.is_integer()),
          "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
          "boolean": lambda v: isinstance(v, bool),
          "object": lambda v: isinstance(v, dict),
          "array": lambda v: isinstance(v, list),
          "null": lambda v: v is None}


def _same(a, b) -> bool:
    return a == b and isinstance(a, bool) == isinstance(b, bool)


def check_arguments(schema, value, path: str = "arguments", depth: int = 0) -> str:
    """Where `value` breaks `schema` (types, required, enum, const, unknown
    keys where none are allowed), or "" when it does not, as far as this
    small check sees."""
    if not isinstance(schema, dict) or depth > 8:
        return ""
    kinds = schema.get("type")
    kinds = [kinds] if isinstance(kinds, str) else kinds if isinstance(kinds, list) else []
    known = [k for k in kinds if k in _TYPES]
    if known and not any(_TYPES[k](value) for k in known):
        return f"{path}: expected {' or '.join(known)}"
    enum = schema.get("enum")
    if isinstance(enum, list) and not any(_same(value, e) for e in enum):
        return f"{path}: not one of the allowed values"
    if "const" in schema and not _same(value, schema["const"]):
        return f"{path}: not the required value"
    if isinstance(value, dict):
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        for key in schema.get("required") or ():
            if isinstance(key, str) and key not in value:
                return f"{path}.{key}: required"
        for key, item in value.items():
            if key in properties:
                problem = check_arguments(properties[key], item, f"{path}.{key}", depth + 1)
                if problem:
                    return problem
            elif schema.get("additionalProperties") is False:
                return f"{path}.{key}: not allowed"
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(value):
            problem = check_arguments(schema["items"], item, f"{path}[{i}]", depth + 1)
            if problem:
                return problem
    return ""


def _fence(label: str, text: str) -> str:
    """Third-party text as external material its content cannot close."""
    cleaned = html.escape(_clean_prompt_source(scrub_third_party_text(text)), quote=False)
    return f"{_WEB_DESC_OPEN}[{label}]\n{cleaned}\n[/{label}]{_WEB_DESC_CLOSE}"


_PROPERTY_RE = re.compile(r"[A-Za-z0-9_.-]{1,64}")


def _one_type(schema: dict) -> str:
    """A single JSON type every vendor's validator takes: the first of a list
    that is not null, else what the schema's shape says, else string."""
    kinds = schema.get("type")
    kinds = [kinds] if isinstance(kinds, str) else kinds if isinstance(kinds, list) else []
    for kind in kinds:
        if kind in _TYPES and kind != "null":
            return kind
    if isinstance(schema.get("properties"), dict):
        return "object"
    if "items" in schema:
        return "array"
    return "string"


def offer_schema(schema, depth: int = 0) -> Optional[dict]:
    """The parts of an input schema the decision model needs, in the plain
    form every vendor accepts (one type, arrays with items, string enums),
    bounded and with descriptions fenced; None when a required property
    cannot be offered."""
    schema = schema if isinstance(schema, dict) else {}
    kind = "object" if depth == 0 else _one_type(schema)
    out: dict = {"type": kind}
    if isinstance(schema.get("description"), str) and schema["description"].strip():
        out["description"] = _fence("parameter_description",
                                    schema["description"][:PROPERTY_DESCRIPTION_CHARS])
    enum = schema.get("enum")
    if kind == "string" and isinstance(enum, list) and enum and all(isinstance(e, str) for e in enum):
        out["enum"] = [scrub_third_party_text(e)[:100] for e in enum[:50]]
    if kind in ("number", "integer"):
        for bound in ("minimum", "maximum"):
            if isinstance(schema.get(bound), (int, float)) and not isinstance(schema.get(bound), bool):
                out[bound] = schema[bound]
    if kind == "array":
        items = offer_schema(schema.get("items"), depth + 1) if depth < 3 else None
        out["items"] = items if items else {"type": "string"}
    if kind == "object":
        properties = schema.get("properties") if depth < 3 else None
        kept = {}
        for key, item in list((properties or {}).items())[:30]:
            if isinstance(key, str) and _PROPERTY_RE.fullmatch(key):
                offered = offer_schema(item, depth + 1)
                if offered is not None:
                    kept[key] = offered
        required = [k for k in (schema.get("required") if isinstance(properties, dict) else None) or ()
                    if isinstance(k, str)]
        if any(k not in kept for k in required):
            return None
        out["properties"] = kept
        if required:
            out["required"] = required
    return out


@dataclass(frozen=True)
class Offered:
    server: str
    tool: str
    description: str
    schema: dict
    # Who may cause it to be used; a tool of unknown standing is the admin's.
    who: str = ADMIN


def function_for(index: int, offered: Offered) -> Optional[dict]:
    """The decision request's function for one tool: a name of our own making,
    the third party's words fenced as external material."""
    parameters = offer_schema(offered.schema)
    if parameters is None:
        return None
    safe = re.sub(r"[^A-Za-z0-9_]", "_", offered.tool)[:40]
    about = (f"tool: {offered.tool}\nprogram: {offered.server}\n"
             f"what its maker says it does: {offered.description[:OFFER_DESCRIPTION_CHARS] or '(nothing)'}")
    return {"type": "function", "function": {
        "name": f"t{index}_{safe}",
        "description": "A tool the admin added. " + _fence("third_party_tool_description", about),
        "parameters": parameters}}


def result_for_prompt(offered: Offered, result: ToolResult) -> str:
    """A tool's answer as it enters the reply's prompt: which tool, then its text."""
    text = result.text.strip()
    if len(text) > PROMPT_RESULT_CHARS:
        text = text[:PROMPT_RESULT_CHARS] + "\n(the rest was cut)"
    lines = [f"Result of the tool {offered.tool} (from {offered.server}), "
             "which the character can use as something it knows:", text or "(empty)"]
    if result.left_out:
        lines.append(f"(not shown: {', '.join(result.left_out)} content)")
    return "\n".join(lines)


# ---------------------------------------------------------------- runner --

class _Runner:
    """One server kept running for the service: restarted with backoff when it stops."""

    def __init__(self, hub: "ToolHub", name: str, spec: dict) -> None:
        self.hub, self.name, self.spec = hub, name, spec
        self.key = run_key(spec)
        self.state, self.error, self.detail = "starting", "", ""
        self.tools: list[dict] = []
        self.session = None
        self.task: Optional[asyncio.Task] = None
        self.since = 0.0

    def start(self) -> None:
        self.task = asyncio.ensure_future(self._run())

    def _set(self, state: str, error: str = "", detail: str = "") -> None:
        self.state, self.error, self.detail = state, error, detail
        self.hub.write_status()

    async def _run(self) -> None:
        delay = BACKOFF_S[0]
        while True:
            self._set("starting")
            try:
                self.session = await connect(self.spec, START_TIMEOUT_S)
                self.tools = clean_tools(await self.session.list_tools(LIST_TIMEOUT_S))
                remember_tools(self.hub.home, self.name, self.spec, self.tools)
                self.since = time.monotonic()
                self._set("running")
                logger.info("[Tools] %s is running with %d tools", self.name, len(self.tools))
                while True:
                    closed = asyncio.ensure_future(self.session.closed.wait())
                    changed = asyncio.ensure_future(self.session.tools_changed.wait())
                    done, pending = await asyncio.wait({closed, changed},
                                                       return_when=asyncio.FIRST_COMPLETED)
                    for waiting in pending:
                        waiting.cancel()
                    if closed in done:
                        break
                    self.tools = clean_tools(await self.session.list_tools(LIST_TIMEOUT_S))
                    remember_tools(self.hub.home, self.name, self.spec, self.tools)
                    self.hub.write_status()
                error = getattr(self.session, "_exit_error", None)
                code, detail = describe(error()) if error else ("closed", "")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                code, detail = describe(e)
            await self._drop_session()
            self.tools = []
            if self.since and time.monotonic() - self.since >= HEALTHY_S:
                delay = BACKOFF_S[0]
            self.since = 0.0
            self._set("failed", code, detail)
            logger.warning("[Tools] %s stopped (%s); trying again in %.0f s", self.name, code, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, BACKOFF_S[1])

    async def _drop_session(self) -> None:
        session, self.session = self.session, None
        if session is not None:
            try:
                await session.close()
            except Exception as e:
                logger.debug("[Tools] closing %s: %s", self.name, e)

    async def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()
            try:
                await self.task
            except (asyncio.CancelledError, Exception):
                pass
        await self._drop_session()
        self.state = "stopped"


class ToolHub:
    """The servers of one home, for the character service: started with it,
    following changes to mcp.json, stopped with it."""

    def __init__(self, home: Path, *, reports: bool = False) -> None:
        self.home = Path(home)
        # Only the service's own hub writes status.json; a practice or terminal one would overwrite it.
        self.reports = reports
        self._runners: dict[str, _Runner] = {}
        self._config: dict = {"mcpServers": {}}
        self._stamp: Optional[tuple] = None
        self._watch: Optional[asyncio.Task] = None
        self._started = False

    def _file_stamp(self) -> Optional[tuple]:
        try:
            stat = config_path(self.home).stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return None

    def configured(self) -> bool:
        return self._file_stamp() is not None

    def start(self) -> None:
        """Start every server in the background; never waits for one."""
        if self._started:
            return
        self._started = True
        self._reconcile()
        self._watch = asyncio.ensure_future(self._watch_config())

    async def _watch_config(self) -> None:
        while True:
            await asyncio.sleep(WATCH_S)
            try:
                self._reconcile()
            except Exception as e:
                logger.warning("[Tools] reading %s failed: %s", CONFIG_FILE, e)

    def _reconcile(self) -> None:
        stamp = self._file_stamp()
        if stamp == self._stamp:
            return
        self._stamp = stamp
        self._config = load_config(self.home) if stamp else {"mcpServers": {}}
        # A server switched off in the file ("disabled": true) is not started.
        servers = {name: spec for name, spec in self._config["mcpServers"].items() if not spec.get("disabled")}
        for name in list(self._runners):
            runner = self._runners[name]
            if name not in servers or run_key(servers[name]) != runner.key:
                del self._runners[name]
                asyncio.ensure_future(runner.stop())
        for name, spec in servers.items():
            if name not in self._runners:
                runner = self._runners[name] = _Runner(self, name, spec)
                runner.start()
            else:
                self._runners[name].spec = spec
        self.write_status()

    def write_status(self) -> None:
        if not self.reports:
            return
        servers = {name: {"state": r.state, "error": r.error, "detail": r.detail[:2000],
                          "tools": len(r.tools)} for name, r in self._runners.items()}
        try:
            atomic_write_text(state_dir(self.home) / "status.json",
                              json.dumps({"pid": os.getpid(), "at": time.time(), "servers": servers},
                                         ensure_ascii=False), fsync=False)
        except OSError as e:
            logger.debug("[Tools] status not written: %s", e)

    async def warm(self) -> None:
        """Outside the service (the terminal chat, the practice group) the first
        turn starts the servers, and waits a while for them to come up."""
        if self._started or not self.configured():
            return
        self.start()
        deadline = time.monotonic() + FIRST_START_WAIT_S
        while any(r.state == "starting" for r in self._runners.values()) and time.monotonic() < deadline:
            await asyncio.sleep(0.1)

    def offer(self, admin: bool) -> list[Offered]:
        """The tools this turn's sender may cause to be used, from running servers."""
        if not self._started:
            if not self.configured():
                return []
            self.start()
        self._reconcile()
        out: list[Offered] = []
        for name, runner in self._runners.items():
            if runner.state != "running":
                continue
            spec = self._config["mcpServers"].get(name) or runner.spec
            for tool in runner.tools:
                row = tool_setting(spec, tool["name"])
                if row["enabled"] and (admin or row["who"] == ANYONE):
                    out.append(Offered(name, tool["name"], tool["description"], tool["inputSchema"],
                                       row["who"]))
        return out[:MAX_OFFERED]

    async def call(self, offered: Offered, arguments: dict, timeout: float = TURN_CALL_TIMEOUT_S) -> ToolResult:
        runner = self._runners.get(offered.server)
        if runner is None or runner.session is None or runner.state != "running":
            raise McpError("closed")
        return await runner.session.call_tool(offered.tool, arguments, timeout)

    def summary(self) -> dict:
        return {name: {"state": r.state, "error": r.error, "tools": len(r.tools)}
                for name, r in self._runners.items()}

    async def aclose(self) -> None:
        if self._watch is not None:
            self._watch.cancel()
            try:
                await self._watch
            except (asyncio.CancelledError, Exception):
                pass
        runners, self._runners = list(self._runners.values()), {}
        if runners:
            await asyncio.gather(*(r.stop() for r in runners), return_exceptions=True)
        if self._started:
            self.write_status()
        self._started = False


# ------------------------------------------- the page and the terminal --

def public_address(url: str) -> bool:
    """Whether every address `url`'s host names is public: not this computer,
    its network, link-local or reserved space. A name that does not resolve
    counts as not public."""
    import ipaddress
    import socket

    from .ingestion import _ip_obj_is_internal

    host = (urlsplit(url).hostname or "").strip("[]")
    if not host:
        return False
    try:
        found = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            found = {ipaddress.ip_address(info[4][0].split("%", 1)[0])
                     for info in socket.getaddrinfo(host, None)}
        except (OSError, ValueError, UnicodeError):
            return False
    return bool(found) and not any(_ip_obj_is_internal(ip) for ip in found)


def uvx_found() -> bool:
    return bool(find_program("uvx"))


def public_view(home: Path, *, running: bool) -> dict:
    """Every server for the page: what runs it, whether it runs, its tools and
    their settings. Secret values are never in it, only whether one is set."""
    config = load_config(home)
    status = read_status(home).get("servers", {}) if running else {}
    servers = []
    for name, spec in config["mcpServers"].items():
        tools = known_tools(home, name, spec)
        state = status.get(name) if isinstance(status.get(name), dict) else {}
        servers.append({
            "name": name,
            "kind": "program" if spec.get("command") else "address",
            "command": spec.get("command", ""), "args": spec.get("args", []),
            "url": spec.get("url", ""),
            "env": [{"name": k, "set": bool(v)} for k, v in (spec.get("env") or {}).items()],
            "headers": [{"name": k, "set": bool(v)} for k, v in (spec.get("headers") or {}).items()],
            "state": str(state.get("state") or "") if running else "",
            "error": str(state.get("error") or ""), "detail": str(state.get("detail") or "")[:2000],
            "listed": tools is not None,
            "disabled": bool(spec.get("disabled")),
            "tools": [{**t, **tool_setting(spec, t["name"])} for t in (tools or [])],
        })
    added = {json.dumps({"c": s.get("command"), "a": s.get("args")}) for s in config["mcpServers"].values()}
    starters = [{"id": key, "command": spec["command"], "args": spec["args"]}
                for key, spec in STARTERS.items()
                if json.dumps({"c": spec["command"], "a": spec["args"]}) not in added]
    return {"servers": servers, "starters": starters if uvx_found() else [],
            "uvx": uvx_found(), "running": running}


async def check(home: Path, name: str) -> dict:
    """Connect now on a connection of our own, list the tools and keep the list."""
    spec = load_config(home)["mcpServers"].get(name)
    if spec is None:
        raise ToolsError("tools_unknown_server")
    session = None
    try:
        session = await connect(spec, START_TIMEOUT_S)
        tools = clean_tools(await session.list_tools(LIST_TIMEOUT_S))
    except Exception as e:
        code, detail = describe(e)
        return {"ok": False, "error": code, "detail": detail[:2000]}
    finally:
        if session is not None:
            await session.close()
    remember_tools(home, name, spec, tools)
    return {"ok": True, "tools": len(tools)}


async def call_by_hand(home: Path, name: str, tool: str, arguments) -> dict:
    """One call as a person tries it: the text the character would get."""
    spec = load_config(home)["mcpServers"].get(name)
    if spec is None:
        raise ToolsError("tools_unknown_server")
    if not isinstance(arguments, dict):
        return {"ok": False, "error": "bad_arguments", "detail": "arguments: expected object"}
    listed = {t["name"]: t for t in known_tools(home, name, spec) or ()}
    if tool not in listed:
        raise ToolsError("tools_unknown_tool")
    problem = check_arguments(listed[tool]["inputSchema"], arguments)
    if problem:
        return {"ok": False, "error": "bad_arguments", "detail": problem}
    session = None
    try:
        session = await connect(spec, START_TIMEOUT_S)
        result = await session.call_tool(tool, arguments, HAND_CALL_TIMEOUT_S)
    except Exception as e:
        code, detail = describe(e)
        return {"ok": False, "error": code, "detail": detail[:2000]}
    finally:
        if session is not None:
            await session.close()
    text = result.text
    cut = len(text) > PAGE_RESULT_CHARS
    return {"ok": True, "isError": result.is_error, "text": text[:PAGE_RESULT_CHARS], "cut": cut,
            "leftOut": result.left_out,
            "prompt": result_for_prompt(Offered(name, tool, "", {}), result)}


def enabled_counts(home: Path) -> dict:
    """For `doctor`: servers, tools on, and the servers the running service could not start."""
    config = load_config(home)
    on = 0
    for name, spec in config["mcpServers"].items():
        if spec.get("disabled"):
            continue
        for tool in known_tools(home, name, spec) or ():
            on += tool_setting(spec, tool["name"])["enabled"]
    return {"servers": len(config["mcpServers"]), "tools_on": on}


# -------------------------------------------------------------- terminal --

ERROR_SENTENCES = {
    "not_found": "the program was not found: {0}",
    "exited": "the program stopped: {0}",
    "refused": "the address refused the connection: {0}",
    "timeout": "no answer in time: {0}",
    "oauth": "the server asks for a sign-in (OAuth), which personagent does not support yet ({0})",
    "http": "the address answered with an error: {0}",
    "protocol": "the answer was not one an MCP server gives: {0}",
    "too_large": "the answer was larger than personagent accepts: {0}",
    "closed": "the connection closed: {0}",
    "sse_unsupported": "the server uses the older SSE transport, which personagent does not support; "
                       "use its Streamable HTTP address ({0})",
    "bad_arguments": "the arguments do not match the tool's description: {0}",
}

REFUSALS = {
    "tools_bad_snippet": "That is not a server configuration personagent can read.",
    "tools_bad_name": "A server name is 1 to 40 letters, digits, dots, dashes or underscores.",
    "tools_bad_url": "The address must start with http:// or https:// and hold no user name or password.",
    "tools_name_taken": "A server with that name is already added.",
    "tools_too_many": "No more servers can be added.",
    "tools_unknown_server": "There is no server with that name.",
    "tools_unknown_tool": "That server has no tool of that name. Run `personagent tools check` first.",
    "tools_sse_unsupported": "That server uses the older SSE transport, which personagent does not support. "
                             "Use its Streamable HTTP address.",
    "tools_write_failed": "The tools file could not be written.",
    "tools_bad_request": "That request is not valid.",
    "tools_file_damaged": "The file mcp.json in the home folder cannot be read as JSON. Correct it or remove it.",
}


def failure_sentence(code: str, detail: str) -> str:
    return langs.term(ERROR_SENTENCES.get(code, "it failed: {0}").replace("{0}", detail.strip() or "-"),
                      keep=(detail.strip() or "-",))


def _home() -> Path:
    from . import home as homes

    return homes.find_home()


def _read_snippet(value: str) -> str:
    path = Path(value)
    try:
        if len(value) < 1024 and path.is_file():
            return path.read_text(encoding="utf-8-sig")
    except OSError:
        pass
    return value


def main(argv: Optional[list] = None, prog: str = "personagent tools") -> int:
    p = argparse.ArgumentParser(prog=prog, description=langs.term(
        "Give the character tools from MCP servers. Adding a server runs a program on this "
        "computer with your own rights, and a tool's answers go to the model service."))
    sub = p.add_subparsers(dest="action", metavar="action")
    sub.add_parser("list", help=langs.term("the servers, their tools and who may use each"))
    add = sub.add_parser("add", help=langs.term("add servers from a JSON file or snippet, or a command or address"))
    add.add_argument("snippet", nargs="?", help=langs.term("a JSON file, or the JSON itself"))
    add.add_argument("--name", default="", help=langs.term("the server's name"))
    add.add_argument("--command", default="", help=langs.term("the program to run"))
    add.add_argument("--arg", action="append", default=[], help=langs.term("one argument for the program (repeat; write --arg=-x for one that begins with a dash)"))
    add.add_argument("--env", action="append", default=[], metavar="NAME=VALUE",
                     help=langs.term("one environment value for the program (repeat)"))
    add.add_argument("--url", default="", help=langs.term("the address of a remote server"))
    add.add_argument("--header", action="append", default=[], metavar="NAME=VALUE",
                     help=langs.term("one header for the remote server (repeat)"))
    remove = sub.add_parser("remove", help=langs.term("remove a server"))
    remove.add_argument("name")
    check_cmd = sub.add_parser("check", help=langs.term("connect now and list the tools"))
    check_cmd.add_argument("name", nargs="?", help=langs.term("one server; all when left out"))
    call = sub.add_parser("call", help=langs.term("call one tool by hand"))
    call.add_argument("name")
    call.add_argument("tool")
    call.add_argument("arguments", nargs="?", default="{}", help=langs.term("the arguments, as a JSON object"))
    use = sub.add_parser("set", help=langs.term("switch a tool on or off, or choose who may use it"))
    use.add_argument("name")
    use.add_argument("tool")
    use.add_argument("--on", action="store_true")
    use.add_argument("--off", action="store_true")
    use.add_argument("--who", choices=WHO)
    args = p.parse_args(sys.argv[1:] if argv is None else argv)
    home = _home()
    try:
        return _run(args, home, p)
    except ToolsError as e:
        print(langs.term(REFUSALS.get(str(e), str(e))), file=sys.stderr)
        return 2


def keep_folder(spec: dict, folder: Path) -> None:
    """A program named by a path relative to the folder it was added from
    (`node build/index.js`) runs from that folder, wherever the service runs."""
    if not spec.get("command") or spec.get("cwd"):
        return
    for word in [spec["command"], *spec.get("args", [])]:
        path = Path(word)
        if (not path.is_absolute() and ("/" in word or "\\" in word or path.suffix)
                and (folder / path).exists()):
            spec["cwd"] = str(folder.resolve())
            return


def _pairs_from(words: list, sep: str = "=") -> dict:
    out = {}
    for word in words:
        key, found, value = word.partition(sep)
        if not found:
            raise ToolsError("tools_bad_snippet")
        out[key.strip()] = value
    return out


def _run(args, home: Path, parser) -> int:
    if args.action in (None, "list"):
        view = public_view(home, running=False)
        if not view["servers"]:
            print(langs.term("No tool servers are added. `personagent tools add` adds one."))
        for server in view["servers"]:
            where = " ".join([server["command"], *server["args"]]) if server["command"] else server["url"]
            print(f"{server['name']}  {where}")
            secrets = [e["name"] for e in server["env"] + server["headers"]]
            if secrets:
                print("  " + langs.term(f"secret values set: {', '.join(secrets)}", keep=(", ".join(secrets),)))
            if not server["listed"]:
                print("  " + langs.term("tools not read yet: run `personagent tools check`"))
            for tool in server["tools"]:
                state = langs.term("switched on") if tool["enabled"] else langs.term("switched off")
                who = langs.term("admin only") if tool["who"] == ADMIN else langs.term("anyone it answers")
                print(f"  - {tool['name']}  [{state}, {who}]  {tool['description'][:100]}")
        return 0
    if args.action == "add":
        if args.snippet:
            servers = parse_snippet(_read_snippet(args.snippet), args.name)
        elif args.command:
            servers = {_server_name(args.name or _guess_name({"command": args.command, "args": args.arg})):
                       normalize({"command": args.command, "args": args.arg, "env": _pairs_from(args.env)})}
        elif args.url:
            spec = normalize({"url": args.url, "headers": _pairs_from(args.header)})
            servers = {_server_name(args.name or _guess_name(spec)): spec}
        else:
            parser.error(langs.term("give a JSON file or snippet, --command or --url"))
        for spec in servers.values():
            keep_folder(spec, Path.cwd())
        for name in add_servers(home, servers):
            print(langs.term(f"Added {name}. A running character starts it within a few seconds.", keep=(name,)))
        print(langs.term("Its tools are on for the admin only; `personagent tools set` changes that."))
        return 0
    if args.action == "remove":
        remove_server(home, args.name)
        print(langs.term(f"Removed {args.name}.", keep=(args.name,)))
        return 0
    if args.action == "set":
        if args.on and args.off:
            parser.error(langs.term("choose --on or --off, not both"))
        row = set_tool(home, args.name, args.tool, enabled=True if args.on else False if args.off else None,
                       who=args.who)
        state = langs.term("switched on") if row["enabled"] else langs.term("switched off")
        who = langs.term("admin only") if row["who"] == ADMIN else langs.term("anyone it answers")
        print(f"{args.name}/{args.tool}: {state}, {who}")
        return 0
    if args.action == "check":
        names = [args.name] if args.name else list(load_config(home)["mcpServers"])
        failed = 0
        for name in names:
            found = asyncio.run(check(home, name))
            if found["ok"]:
                print(langs.term(f"{name}: working, tools: {found['tools']}", keep=(name,)))
            else:
                failed += 1
                print(f"{name}: {failure_sentence(found['error'], found['detail'])}")
        return 1 if failed else 0
    if args.action == "call":
        try:
            arguments = json.loads(args.arguments)
        except ValueError:
            arguments = None
        found = asyncio.run(call_by_hand(home, args.name, args.tool, arguments))
        if not found["ok"]:
            print(failure_sentence(found["error"], found["detail"]), file=sys.stderr)
            return 1
        if found["isError"]:
            print(langs.term("The tool reported an error:"), file=sys.stderr)
        print(found["text"])
        if found["leftOut"]:
            print(langs.term(f"(not shown: {', '.join(found['leftOut'])} content)"), file=sys.stderr)
        return 1 if found["isError"] else 0
    return 0
