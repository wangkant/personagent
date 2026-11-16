"""A small MCP client: the part of the protocol a character needs to use the
tools of servers its admin adds. `initialize`, `notifications/initialized`,
`tools/list` and `tools/call`, over stdio (a child process speaking
newline-delimited JSON-RPC) and over Streamable HTTP (a POST answered with
JSON or an SSE stream, the `Mcp-Session-Id` header).

Everything a server sends is third-party data: sizes are capped, and only
text content is passed on (other content is named).
"""
from __future__ import annotations

import asyncio
import collections
import json
import logging
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

import httpx

from . import __version__

logger = logging.getLogger("agent.tools")

#: Newest first; the first is what this client asks for.
PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
#: One message from a server, in bytes.
MAX_MESSAGE_BYTES = 2_000_000
#: Pages of `tools/list` read, and tools kept, per server.
MAX_LIST_PAGES = 10
MAX_TOOLS = 64
#: Lines of a server's stderr kept to explain why it stopped.
STDERR_LINES = 12
STDERR_LINE_CHARS = 300
#: Seconds a stdio server has to exit after its input closes, then after a terminate.
EXIT_GRACE_S = 2.0
#: SSE reconnections for one request after the server closed the stream early.
SSE_RECONNECTS = 5

# The installers' own variable for where they put uv, not a setting of the home.
UV_DIR_ENV = "PERSONAGENT_UV_DIR"

_CREATE_SUSPENDED = 0x4
_CREATE_NO_WINDOW = 0x08000000


class McpError(Exception):
    """A failure the page names: `code` is one of not_found, exited, refused,
    timeout, oauth, http, protocol, too_large, closed, sse_unsupported."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


@dataclass
class ToolResult:
    text: str
    is_error: bool = False
    #: Content that was not text, by its type ("image", "audio", ...).
    left_out: list = field(default_factory=list)


def _visible_ascii(value: str) -> bool:
    return bool(value) and all(0x21 <= ord(c) <= 0x7E for c in value)


def uv_dirs() -> list[Path]:
    """Where the installers put uv when it is not on PATH."""
    dirs = []
    if os.environ.get(UV_DIR_ENV):
        dirs.append(Path(os.environ[UV_DIR_ENV]))
    dirs.append(Path.home() / ".local" / "bin")
    if os.name == "nt":
        dirs.append(Path.home() / ".cargo" / "bin")
    return dirs


def find_program(command: str, env: Optional[dict] = None) -> str:
    """The full path of `command`, or "" when it cannot be found. uv and uvx
    are also looked for where the installers put them."""
    if not command:
        return ""
    path = (env or os.environ).get("PATH") if env else None
    found = shutil.which(command, path=path)
    if found:
        return found
    if Path(command).name in ("uv", "uvx") and not Path(command).parent.name:
        for folder in uv_dirs():
            found = shutil.which(command, path=str(folder))
            if found:
                return found
    return ""


def result_of(raw: dict) -> ToolResult:
    """A `tools/call` result as text; anything else is named, not passed on."""
    if not isinstance(raw, dict):
        raise McpError("protocol", "the tool's result is not an object")
    texts, left_out = [], []
    for item in raw.get("content") or ():
        kind = item.get("type") if isinstance(item, dict) else None
        if kind == "text" and isinstance(item.get("text"), str):
            texts.append(item["text"])
        else:
            left_out.append(str(kind or "unknown")[:32])
    structured = raw.get("structuredContent")
    if not texts and structured is not None:
        # The spec asks servers to send it as text as well; some do not.
        texts.append(json.dumps(structured, ensure_ascii=False))
    return ToolResult("\n".join(texts), bool(raw.get("isError")), left_out)


class _Session:
    """What both transports share: the lifecycle and the two tool methods."""

    protocol = ""
    server_name = ""

    def __init__(self) -> None:
        self.tools_changed = asyncio.Event()
        self.closed = asyncio.Event()

    async def request(self, method: str, params: dict, timeout: float):
        raise NotImplementedError

    async def notify(self, method: str, params: Optional[dict] = None) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    def _on_server_message(self, message: dict) -> Optional[dict]:
        """A request or notification the server sent; the answer to send, if any."""
        method = message.get("method")
        if "id" in message:
            if method == "ping":
                return {"jsonrpc": "2.0", "id": message["id"], "result": {}}
            # No roots, sampling or elicitation were declared.
            return {"jsonrpc": "2.0", "id": message["id"],
                    "error": {"code": -32601, "message": "Method not found"}}
        if method == "notifications/tools/list_changed":
            self.tools_changed.set()
        return None

    async def initialize(self, timeout: float) -> None:
        result = await self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSIONS[0], "capabilities": {},
            "clientInfo": {"name": "personagent", "version": __version__}}, timeout)
        if not isinstance(result, dict):
            raise McpError("protocol", "the answer to initialize is not an object")
        version = result.get("protocolVersion")
        if version not in PROTOCOL_VERSIONS:
            raise McpError("protocol", f"unsupported protocol version {str(version)[:40]}")
        self.protocol = version
        info = result.get("serverInfo")
        self.server_name = str(info.get("name") or "")[:80] if isinstance(info, dict) else ""
        await self.notify("notifications/initialized")

    async def list_tools(self, timeout: float) -> list[dict]:
        tools: list[dict] = []
        cursor = None
        for _ in range(MAX_LIST_PAGES):
            result = await self.request("tools/list", {"cursor": cursor} if cursor else {}, timeout)
            if not isinstance(result, dict):
                raise McpError("protocol", "the tool list is not an object")
            page = result.get("tools")
            if not isinstance(page, list):
                raise McpError("protocol", "the tool list has no tools")
            tools += [t for t in page if isinstance(t, dict)]
            cursor = result.get("nextCursor")
            if not cursor or not isinstance(cursor, str) or len(tools) >= MAX_TOOLS:
                break
        self.tools_changed.clear()
        return tools[:MAX_TOOLS]

    async def call_tool(self, name: str, arguments: dict, timeout: float) -> ToolResult:
        return result_of(await self.request("tools/call", {"name": name, "arguments": arguments}, timeout))


def _rpc_result(message: dict):
    if "error" in message:
        error = message.get("error")
        text = str(error.get("message") or "") if isinstance(error, dict) else ""
        raise McpError("protocol", f"the server answered with an error: {text[:300]}")
    return message.get("result")


# ------------------------------------------------------------------ stdio --

class StdioSession(_Session):
    """A server run as a child process of this one, ended with it."""

    def __init__(self, command: str, args: list, env: Optional[dict] = None,
                 cwd: Optional[str] = None) -> None:
        super().__init__()
        self.command, self.args = command, list(args or ())
        self.env = {**os.environ, **(env or {})}
        self.cwd = cwd or None
        self.process: Optional[subprocess.Popen] = None
        self._job = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id = 0
        self._stderr: collections.deque = collections.deque(maxlen=STDERR_LINES)
        self._write_lock = threading.Lock()
        self._threads: list[threading.Thread] = []

    @property
    def pid(self) -> int:
        return self.process.pid if self.process else 0

    def stderr_tail(self) -> str:
        return "\n".join(self._stderr)

    def start(self) -> None:
        program = find_program(self.command, self.env)
        if not program:
            raise McpError("not_found", self.command)
        self._loop = asyncio.get_running_loop()
        options: dict = {}
        if os.name == "nt":
            options["creationflags"] = _CREATE_SUSPENDED | _CREATE_NO_WINDOW
        else:
            # Its own group, so what it starts ends with it.
            options["start_new_session"] = True
        try:
            self.process = subprocess.Popen(
                [program, *self.args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=self.env, cwd=self.cwd, **options)
        except FileNotFoundError:
            raise McpError("not_found", self.command) from None
        except OSError as e:
            raise McpError("exited", str(e)[:300]) from None
        if os.name == "nt":
            from . import services
            try:
                self._job = services._bind(self.process.pid)
            except OSError as e:
                self.process.kill()
                raise McpError("exited", str(e)[:300]) from None
        for target, name in ((self._read_stdout, "out"), (self._read_stderr, "err")):
            thread = threading.Thread(target=target, name=f"mcp-{name}-{self.process.pid}", daemon=True)
            thread.start()
            self._threads.append(thread)

    def _hand(self, fn, *args) -> None:
        try:
            self._loop.call_soon_threadsafe(fn, *args)
        except RuntimeError:
            pass    # the loop is closed: nobody waits any more

    def _read_stdout(self) -> None:
        out = self.process.stdout
        try:
            while True:
                line = out.readline(MAX_MESSAGE_BYTES + 1)
                if not line:
                    break
                if len(line) > MAX_MESSAGE_BYTES and not line.endswith(b"\n"):
                    # Drop the rest of the oversized message.
                    while True:
                        rest = out.readline(65536)
                        if not rest or rest.endswith(b"\n"):
                            break
                    self._hand(self._fail_pending, McpError("too_large"))
                    continue
                self._hand(self._on_line, line)
        except (OSError, ValueError):
            pass
        self._hand(self._on_exit)

    def _read_stderr(self) -> None:
        try:
            for raw in self.process.stderr:
                text = raw.decode("utf-8", "replace").rstrip()
                if text:
                    self._stderr.append(text[:STDERR_LINE_CHARS])
        except (OSError, ValueError):
            pass

    def _on_line(self, line: bytes) -> None:
        try:
            message = json.loads(line)
        except ValueError:
            return    # stray output; servers are told not to, but some print banners
        if not isinstance(message, dict):
            return
        if "method" in message:
            answer = self._on_server_message(message)
            if answer is not None:
                asyncio.ensure_future(self._send_quietly(answer))
            return
        future = self._pending.pop(message.get("id"), None) if isinstance(message.get("id"), int) else None
        if future is not None and not future.done():
            future.set_result(message)

    def _fail_pending(self, error: McpError) -> None:
        pending, self._pending = self._pending, {}
        for future in pending.values():
            if not future.done():
                future.set_exception(error)

    def _exit_error(self) -> McpError:
        code = self.process.poll() if self.process else None
        detail = self.stderr_tail()
        if code is not None:
            detail = (f"exit code {code}\n" + detail).strip()
        return McpError("exited", detail)

    def _on_exit(self) -> None:
        # stderr may still be draining; give it a moment for the explanation.
        def finish() -> None:
            self._fail_pending(self._exit_error())
            self.closed.set()
        try:
            self._loop.call_later(0.2, finish)
        except RuntimeError:
            pass

    async def _send(self, message: dict) -> None:
        data = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"

        def write() -> None:
            with self._write_lock:
                self.process.stdin.write(data)
                self.process.stdin.flush()
        try:
            await asyncio.to_thread(write)
        except (OSError, ValueError):
            raise self._exit_error() from None

    async def _send_quietly(self, message: dict) -> None:
        try:
            await self._send(message)
        except McpError:
            pass

    async def request(self, method: str, params: dict, timeout: float):
        if self.closed.is_set():
            raise self._exit_error()
        self._next_id += 1
        request_id = self._next_id
        future = self._loop.create_future()
        self._pending[request_id] = future
        await self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        try:
            message = await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            if not self.closed.is_set():
                try:
                    await self.notify("notifications/cancelled",
                                      {"requestId": request_id, "reason": "timed out"})
                except McpError:
                    pass
            raise McpError("timeout", f"{timeout:g} s") from None
        return _rpc_result(message)

    async def notify(self, method: str, params: Optional[dict] = None) -> None:
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        await self._send(message)

    def _end_process(self) -> None:
        """Close its input, then terminate, then kill: it and what it started."""
        process = self.process
        if process is None:
            return
        from . import services
        try:
            process.stdin.close()
        except (OSError, ValueError):
            pass
        for force in (False, True):
            try:
                process.wait(EXIT_GRACE_S)
                break
            except subprocess.TimeoutExpired:
                services._signal_child(process, force=force, job=self._job)
        else:
            try:
                process.wait(EXIT_GRACE_S)
            except subprocess.TimeoutExpired:
                pass
        if os.name != "nt":
            # The server is gone; anything it left in its group goes too.
            try:
                import signal
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, AttributeError):
                pass
        elif self._job:
            # Whatever the server started and left behind ends with its job.
            kernel32 = services._win32()[0]
            kernel32.TerminateJobObject(self._job, 1)
            kernel32.CloseHandle(self._job)
            self._job = None
        for stream in (process.stdout, process.stderr):
            try:
                stream.close()
            except (OSError, ValueError):
                pass

    async def close(self) -> None:
        await asyncio.to_thread(self._end_process)
        self._fail_pending(McpError("closed"))
        self.closed.set()


# ------------------------------------------------------------------- http --

def _local(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return host in ("localhost", "127.0.0.1", "::1") or host.endswith(".localhost")


class HttpSession(_Session):
    """A remote server over Streamable HTTP."""

    def __init__(self, url: str, headers: Optional[dict] = None) -> None:
        super().__init__()
        self.url = url
        self.headers = dict(headers or {})
        self.session_id = ""
        # A local server is reached directly, never through a proxy.
        self._client = httpx.AsyncClient(trust_env=not _local(url), follow_redirects=False)
        self._initializing = False
        self._next = 0

    def _headers(self, accept: str = "application/json, text/event-stream") -> dict:
        out = {**self.headers, "Accept": accept}
        if self.session_id:
            out["Mcp-Session-Id"] = self.session_id
        if self.protocol:
            out["MCP-Protocol-Version"] = self.protocol
        return out

    def _refused(self, status: int, resp: httpx.Response) -> McpError:
        if status == 401 or (status == 403 and "bearer" in resp.headers.get("www-authenticate", "").lower()):
            return McpError("oauth", str(status))
        if status in (404, 405) and urlsplit(self.url).path.rstrip("/").endswith("/sse"):
            return McpError("sse_unsupported", str(status))
        return McpError("http", str(status))

    async def _post(self, message: dict, timeout: float, *, retried: bool = False):
        deadline = time.monotonic() + timeout
        try:
            async with self._client.stream(
                    "POST", self.url, json=message, timeout=timeout,
                    headers={**self._headers(), "Content-Type": "application/json"}) as resp:
                if message.get("method") == "initialize":
                    sid = resp.headers.get("mcp-session-id", "")
                    if sid and _visible_ascii(sid) and len(sid) <= 512:
                        self.session_id = sid
                status = resp.status_code
                if status == 404 and self.session_id and not self._initializing and not retried:
                    # The server ended the session: a new one, then the same message.
                    self.session_id, self.protocol = "", ""
                    await self.initialize(max(1.0, deadline - time.monotonic()))
                    return await self._post(message, max(1.0, deadline - time.monotonic()), retried=True)
                if status == 202:
                    return None
                if status >= 300:
                    raise self._refused(status, resp)
                kind = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                if "id" not in message:
                    return None
                if kind == "text/event-stream":
                    return await self._read_stream(resp, message["id"], deadline)
                body = await self._read_body(resp)
                try:
                    answer = json.loads(body)
                except ValueError:
                    raise McpError("protocol", "the answer is not JSON") from None
                if isinstance(answer, list):
                    answer = next((a for a in answer if isinstance(a, dict)
                                   and a.get("id") == message["id"]), None)
                if not isinstance(answer, dict) or answer.get("id") != message["id"]:
                    raise McpError("protocol", "the answer does not belong to the request")
                return answer
        except httpx.ConnectError as e:
            raise McpError("refused", str(e)[:200]) from None
        except httpx.TimeoutException:
            raise McpError("timeout", f"{timeout:g} s") from None
        except httpx.HTTPError as e:
            raise McpError("http", str(e)[:200]) from None

    @staticmethod
    async def _read_body(resp: httpx.Response) -> bytes:
        body = bytearray()
        async for chunk in resp.aiter_bytes():
            body += chunk
            if len(body) > MAX_MESSAGE_BYTES:
                raise McpError("too_large")
        return bytes(body)

    async def _read_stream(self, resp: httpx.Response, request_id, deadline: float):
        """Events until the one answering `request_id`; a stream closed early
        is resumed with GET and Last-Event-ID, as the server's `retry` says."""
        answer, last_id, retry_ms = await self._events(resp, request_id, "", 1000)
        reconnects = 0
        while answer is None:
            if not last_id or reconnects >= SSE_RECONNECTS:
                raise McpError("protocol", "the stream ended without an answer")
            reconnects += 1
            wait = retry_ms / 1000
            if time.monotonic() + wait >= deadline:
                raise McpError("timeout")
            await asyncio.sleep(wait)
            headers = {**self._headers("text/event-stream"), "Last-Event-ID": last_id}
            async with self._client.stream("GET", self.url, headers=headers,
                                           timeout=max(1.0, deadline - time.monotonic())) as again:
                if again.status_code >= 300:
                    raise self._refused(again.status_code, again)
                answer, last_id, retry_ms = await self._events(again, request_id, last_id, retry_ms)
        return answer

    async def _events(self, resp, request_id, last_id: str, retry_ms: int):
        buffer, size = b"", 0
        async for chunk in resp.aiter_bytes():
            size += len(chunk)
            if size > MAX_MESSAGE_BYTES * 4:
                raise McpError("too_large")
            buffer += chunk.replace(b"\r\n", b"\n")
            while b"\n\n" in buffer:
                block, buffer = buffer.split(b"\n\n", 1)
                data, event_id, retry = [], None, None
                for line in block.decode("utf-8", "replace").split("\n"):
                    if line.startswith(":"):
                        continue
                    name, _, value = line.partition(":")
                    value = value[1:] if value.startswith(" ") else value
                    if name == "data":
                        data.append(value)
                    elif name == "id":
                        event_id = value
                    elif name == "retry" and value.isdigit():
                        retry = int(value)
                if event_id is not None:
                    last_id = event_id
                if retry is not None:
                    retry_ms = min(retry, 30_000)
                text = "\n".join(data).strip()
                if not text:
                    continue
                if len(text) > MAX_MESSAGE_BYTES:
                    raise McpError("too_large")
                try:
                    message = json.loads(text)
                except ValueError:
                    continue
                if not isinstance(message, dict):
                    continue
                if "method" in message:
                    reply = self._on_server_message(message)
                    if reply is not None:
                        await self._post(reply, 10)
                elif message.get("id") == request_id:
                    return message, last_id, retry_ms
        return None, last_id, retry_ms

    async def request(self, method: str, params: dict, timeout: float):
        self._next += 1
        message = {"jsonrpc": "2.0", "id": self._next, "method": method, "params": params}
        if method == "initialize":
            self._initializing = True
        try:
            answer = await asyncio.wait_for(self._post(message, timeout), timeout + 1)
        except asyncio.TimeoutError:
            raise McpError("timeout", f"{timeout:g} s") from None
        except McpError as e:
            if e.code == "refused":
                self.closed.set()
            raise
        finally:
            if method == "initialize":
                self._initializing = False
        if answer is None:
            raise McpError("protocol", "no answer to the request")
        return _rpc_result(answer)

    async def notify(self, method: str, params: Optional[dict] = None) -> None:
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        await self._post(message, 15)

    async def close(self) -> None:
        if self.session_id:
            try:
                await self._client.delete(self.url, headers=self._headers(), timeout=5)
            except httpx.HTTPError:
                pass
        await self._client.aclose()
        self.closed.set()


async def connect(spec: dict, timeout: float) -> _Session:
    """An initialized session to the server `spec` describes (stdio when it
    has a `command`, else HTTP at its `url`); closed again on any failure."""
    if spec.get("command"):
        session: _Session = StdioSession(spec["command"], spec.get("args") or [],
                                         spec.get("env") or {}, spec.get("cwd"))
        session.start()
    else:
        session = HttpSession(spec["url"], spec.get("headers") or {})
    try:
        await session.initialize(timeout)
    except BaseException:
        await session.close()
        raise
    return session


def describe(error: BaseException) -> tuple[str, str]:
    """(code, detail) of any failure to reach a server."""
    if isinstance(error, McpError):
        return error.code, error.detail
    if isinstance(error, asyncio.TimeoutError):
        return "timeout", ""
    logger.debug("[Tools] unexpected failure: %r", error, exc_info=error)
    return "protocol", type(error).__name__
