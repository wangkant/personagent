"""Screenshots of the operator dashboard in a realistic, reproducible state.

    python tools/dashboard_snapshot.py --out DIR [--edge PATH] [--port N] [--only NAME...]

Starts the real service on a throwaway home, seeds it through signed
POST /v1/events (a stand-in OpenAI-compatible server plays the model, the same
scripted answers `personagent demo` uses), then drives headless Edge over the
DevTools protocol and writes full-page PNGs:

    en-light en-dark zh-light zh-dark   1280 px wide
    en-mobile zh-mobile                 390 px wide, light
    en-empty                            a fresh home, light

Developer tool, stdlib only (Pillow, when present, shrinks the PNGs). Nothing
here runs in CI except the seeding test in tests/test_dashboard_snapshot.py;
the Edge part is manual.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import hashlib
import hmac
import http.server
import json
import os
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from persona_agent import demo  # noqa: E402

EDGE_DEFAULTS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/microsoft-edge", "/usr/bin/chromium", "/usr/bin/google-chrome",
)
BOT_ID = "10001"
CONNECTOR_ID = "snapshot-connector"
# The real clock decides the sleep window; 14:00 persona time keeps it open.
PERSONA_HOUR = 14

SHOTS: dict[str, dict] = {
    "en-light": dict(lang="en", theme="light", width=1280, seeded=True),
    "en-dark": dict(lang="en", theme="dark", width=1280, seeded=True),
    "zh-light": dict(lang="zh", theme="light", width=1280, seeded=True),
    "zh-dark": dict(lang="zh", theme="dark", width=1280, seeded=True),
    "en-mobile": dict(lang="en", theme="light", width=390, seeded=True, mobile=True),
    "zh-mobile": dict(lang="zh", theme="light", width=390, seeded=True, mobile=True),
    "en-empty": dict(lang="en", theme="light", width=1280, seeded=False),
}


# ------------------------------------------------------------------ script --

@dataclass
class Beat:
    """One chat message and what the stand-in model answers to it."""

    who: str
    text: str
    addressed: bool = False
    gate: bool | None = None
    reply: str | None = None
    verdict: dict | None = None
    dm: bool = False


def _v(reaction: str, accept: bool, why: str, better: str = "", ask: str = "",
       scenario: str = "") -> dict:
    return demo._verdict(reaction, accept, why, better, ask, scenario)


SCRIPTS: dict[str, list[Beat]] = {
    "en": [
        # Quiet, then one natural join-in (the first appearance is never skipped).
        Beat("sam", "anyone up for the match tonight?"),
        Beat("alex", "can't, deploy day"),
        Beat("priya", "which match?"),
        Beat("sam", "the final!! 8pm, my place", gate=True,
             reply="the final? count me in, I'll bring snacks"),
        Beat("alex", "Nova, you don't even like football", addressed=True,
             reply="I like the snacks. close enough"),
        Beat("sam", "lol fair", gate=False),
        Beat("priya", "ok, back to my report", gate=False),
        Beat("sam", "Nova, remember that match night is at my place", addressed=True),
        # A correction that holds up: rejection, sympathetic retry, acceptance.
        Beat("alex", "Nova, the deploy failed again", addressed=True,
             reply="did you check the logs? roll back first, then diff the configs"),
        Beat("alex", "Nova, I was just venting", addressed=True,
             reply="fair. that's a rough end to the day",
             verdict=_v("rejection", True, "Alex was venting, not asking for a fix",
                        better="ugh, again? that's a rough day",
                        ask="wait, did you just want to vent?",
                        scenario="venting, not advice")),
        Beat("alex", "haha yeah it is, thanks Nova", addressed=True, reply="anytime",
             verdict=_v("positive", True,
                        "Alex agreed with the second try and thanked Nova",
                        scenario="venting, not advice")),
        # One more correction, waiting for a second agreeing reaction.
        Beat("priya", "Nova, which film should I watch tonight?", addressed=True,
             reply="dune again, obviously"),
        Beat("priya", "Nova, I asked for something short and funny", addressed=True,
             reply="ok, short and funny: paddington 2",
             verdict=_v("rejection", True, "Priya wanted a light pick, not a repeat",
                        better="short and funny? paddington 2, no notes",
                        ask="want something lighter?",
                        scenario="film picks")),
        # A DM.
        Beat("jordan", "hey Nova, are you around?", addressed=True, dm=True,
             reply="here. what's up?"),
        Beat("jordan", "my laptop died in the middle of my demo", addressed=True,
             dm=True, reply="ugh, mid-demo? that's brutal"),
    ],
    "zh": [
        Beat("sam", "今晚谁看球？"),
        Beat("alex", "我不行，今天要上线"),
        Beat("priya", "哪一场啊？"),
        Beat("sam", "决赛！八点，来我家", gate=True,
             reply="决赛？算我一个，我带零食"),
        Beat("alex", "小夏，你又不看球", addressed=True, reply="我看零食，差不多"),
        Beat("sam", "哈哈 也是", gate=False),
        Beat("priya", "好了我先把报告写完", gate=False),
        Beat("sam", "小夏，记住决赛在我家看", addressed=True),
        Beat("alex", "小夏，部署又挂了", addressed=True,
             reply="看过日志没？先回滚，再对比一下配置"),
        Beat("alex", "小夏，我就是吐槽一下", addressed=True,
             reply="懂，今天也太倒霉了",
             verdict=_v("rejection", True, "小林只是想吐槽，不是在求办法",
                        better="啊又挂了？今天也太难了",
                        ask="啊，你就是想吐槽一下对吧", scenario="吐槽不是求助")),
        Beat("alex", "哈哈是啊，谢谢小夏", addressed=True, reply="客气啥",
             verdict=_v("positive", True, "小林认同第二次的回复并道谢",
                        scenario="吐槽不是求助")),
        Beat("priya", "小夏，今晚看什么电影？", addressed=True, reply="再刷一遍沙丘，没悬念"),
        Beat("priya", "小夏，我想要短一点、好笑的", addressed=True,
             reply="好，短又好笑：《帕丁顿熊 2》",
             verdict=_v("rejection", True, "小美想要轻松的片子，不是重复推荐",
                        better="想要短又好笑？《帕丁顿熊 2》，闭眼入",
                        ask="要不要换个轻松点的？", scenario="选片")),
        Beat("jordan", "小夏，在吗？", addressed=True, dm=True, reply="在呀，怎么了？"),
        Beat("jordan", "我电脑在演示到一半的时候死机了", addressed=True, dm=True,
             reply="啊，演示到一半？太惨了"),
    ],
}

PLATFORM = {"en": "telegram", "zh": "aiocqhttp"}
GROUP = {"en": "-1001234567890", "zh": "483920157"}
DM_ID = {"en": "5001", "zh": "50011"}
NAME = demo.NAME
PEOPLE = demo.PEOPLE
UIDS = demo.UIDS


# ------------------------------------------------------------- stand-in LLM --

class StandIn:
    """An OpenAI-compatible /v1/chat/completions server whose answers come from
    demo.ScriptedModel: load a Beat, send its event, read the verdicts back."""

    def __init__(self) -> None:
        self.model = demo.ScriptedModel()
        self.requests: list[str] = []
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args) -> None:
                pass

            def handle(self) -> None:
                with contextlib.suppress(ConnectionError):
                    super().handle()

            def do_GET(self) -> None:
                self._send({"object": "list", "data": [{"id": "deepseek-flash"}]})

            def do_POST(self) -> None:
                size = int(self.headers.get("content-length") or 0)
                try:
                    payload = json.loads(self.rfile.read(size) or b"{}")
                except ValueError:
                    payload = {}
                self._send(owner.answer(self.path, payload))

            def _send(self, body: dict) -> None:
                raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}/v1"

    def __enter__(self) -> "StandIn":
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()

    def load(self, beat: Beat) -> None:
        self.model.load(beat)

    def answer(self, path: str, payload: dict) -> dict:
        text = ""
        if "chat/completions" in path and not payload.get("tools"):
            messages = payload.get("messages") or []
            system = next((m.get("content") for m in messages
                           if m.get("role") == "system"), "") or ""
            rest = [m for m in messages if m.get("role") != "system"]
            asked_for_json = bool(payload.get("response_format"))
            gate = "temperature" in payload or "thinking" in payload
            kw: dict = {}
            if gate:
                kw.update(disable_thinking=True, temperature=payload.get("temperature", 0.3))
            elif asked_for_json and system:
                kw["plain_text_fallback"] = True
            text = asyncio.run(self.model(system, rest, payload.get("model", ""), **kw))
            self.requests.append("gate" if gate else
                                 "reply" if kw.get("plain_text_fallback") else "judge")
        return {"id": "snap", "object": "chat.completion", "model": payload.get("model", ""),
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": text}}],
                "usage": {"prompt_tokens": 800, "completion_tokens": 40,
                          "total_tokens": 840}}


# ----------------------------------------------------------------- seeding --

def sign(token: str, body: bytes, nonce: str, stamp: str) -> str:
    mac = stamp.encode("ascii") + b"." + nonce.encode("utf-8") + b"." + body
    return "sha256=" + hmac.new(token.encode("utf-8"), mac, hashlib.sha256).hexdigest()


def event_for(beat: Beat, lang: str, mid: int) -> dict:
    ev = {
        "kind": "event", "platform": PLATFORM[lang],
        "conversation_type": "dm" if beat.dm else "group",
        "sender_id": DM_ID[lang] if beat.dm else UIDS[beat.who],
        "sender_name": PEOPLE[lang][beat.who], "bot_id": BOT_ID,
        "message_id": str(mid), "sent_at": int(time.time()),
        "addressed": beat.addressed,
        "segments": [{"type": "text", "text": beat.text}], "text": beat.text,
        "connector_id": CONNECTOR_ID, "capabilities": ["outbox", "quote_text"],
    }
    if not beat.dm:
        ev["conversation_id"] = GROUP[lang]
    return ev


async def seed(post: Callable[[dict], Awaitable[dict]], standin: StandIn,
               lang: str) -> list[dict]:
    """Play SCRIPTS[lang]; `post` delivers one event and returns the reply body."""
    out = []
    for i, beat in enumerate(SCRIPTS[lang], 1):
        standin.load(beat)
        out.append(await post(event_for(beat, lang, 9000 + i)))
    return out


def conv_id(lang: str) -> str:
    return GROUP[lang] if lang == "zh" else f"{PLATFORM[lang]}:{GROUP[lang]}"


# ------------------------------------------------------------------ service --

CRLF, LF = bytes([13, 10]), bytes([10])


def remove_tree(path: Path) -> None:
    """rmtree that outlasts Windows file handles still closing."""
    for _ in range(25):
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            return
        time.sleep(0.4)
    print(f"warning: could not delete {path}", file=sys.stderr)


def stage_package(base: Path) -> Path:
    """An installed-style copy of the package, so the page spells its commands
    the way an install does (`personagent doctor`), not as a checkout path."""
    from setup import bundled_files
    stage = Path(tempfile.mkdtemp(prefix="pa-stage-", dir=base))
    shutil.copytree(REPO / "persona_agent", stage / "persona_agent",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for source, relative in bundled_files(REPO):
        target = stage / "persona_agent" / "_bundled" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    shim = stage / "bin"
    shim.mkdir()
    (shim / "personagent.cmd").write_bytes(b"@echo off" + CRLF)
    (shim / "personagent").write_bytes(b"#!/bin/sh" + LF)
    return stage


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http_json(url: str, *, data: bytes | None = None, headers: dict | None = None,
              timeout: float = 120.0) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=data, headers=headers or {},
                                 method="POST" if data is not None else "GET")
    try:
        with _DIRECT.open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def persona_offset_hours() -> int:
    utc_hour = datetime.now(timezone.utc).hour
    return (PERSONA_HOUR - utc_hour + 12) % 24 - 12


def write_env(home: Path, lang: str, base_url: str, connector_token: str) -> None:
    lines = {
        "PERSONA_NAME": NAME[lang], "AGENT_LANG": lang,
        "LLM_API_KEY": "sk-snapshot-" + "0" * 24, "LLM_MODEL": "deepseek-flash",
        "LLM_BASE_URL": base_url, "LLM_MAX_RETRIES": "0", "LLM_TIMEOUT_S": "30",
        "CONNECTOR_TOKEN": connector_token, "CONNECTOR_QQ_PLATFORMS": "aiocqhttp",
        "QQ_BOT_ID": BOT_ID,
        "CHAT_TRIGGER_COUNT": "4", "REACT_ELICIT_ENABLED": "false",
        "PROACTIVE_ENABLED": "false", "EVOLVE_AUTO_ENABLED": "false",
        "PERSONA_TZ_OFFSET_HOURS": str(persona_offset_hours()),
        "SERVER_HOST": "127.0.0.1",
    }
    if lang == "zh":
        # A native QQ platform is refused until its people are listed.
        lines.update(ACCESS_GROUPS=GROUP[lang], ACCESS_DM_USERS=DM_ID[lang])
    (home / ".env").write_text(
        "".join(f"{k}={v}\n" for k, v in lines.items()), encoding="utf-8")
    (home / "persona.txt").write_text(demo.PERSONA[lang], encoding="utf-8")


def scrubbed_env(profile: Path, stage: Path) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.upper().endswith(("_PROXY", "_KEY", "_TOKEN"))
           and not k.upper().startswith(("AGENT_", "LLM_", "CONNECTOR_", "PERSONA_"))}
    env.update(USERPROFILE=str(profile), HOME=str(profile),
               NO_PROXY="127.0.0.1,localhost", PYTHONUTF8="1",
               PYTHONPATH=str(stage), PYTHONUNBUFFERED="1",
               PATH=str(stage / "bin") + os.pathsep + env.get("PATH", ""))
    return env


@contextlib.contextmanager
def service(lang: str, base: Path, stage: Path, standin: StandIn, port: int | None = None):
    """The real `personagent run` on a throwaway home; yields (port, dash token,
    connector token, home)."""
    profile = Path(tempfile.mkdtemp(prefix="pa-snap-", dir=base))
    home = profile / "personagent"
    home.mkdir()
    connector_token = secrets.token_urlsafe(24)
    write_env(home, lang, standin.base_url, connector_token)
    port = port or free_port()
    log = open(profile / "service.log", "wb")
    proc = subprocess.Popen(
        [sys.executable, "-m", "persona_agent", "run", "--port", str(port)],
        cwd=str(home), env=scrubbed_env(profile, stage), stdout=log, stderr=log)
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("service exited early:\n" + _tail(profile / "service.log"))
            try:
                if http_json(f"http://127.0.0.1:{port}/health", timeout=2)[0] == 200:
                    break
            except OSError:
                pass
            time.sleep(0.4)
        else:
            raise RuntimeError("service did not come up:\n" + _tail(profile / "service.log"))
        token_file = home / "runtime" / "dashboard.token"
        for _ in range(50):
            if token_file.exists() and token_file.read_text().strip():
                break
            time.sleep(0.1)
        yield port, token_file.read_text().strip(), connector_token, home
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()
        remove_tree(profile)


def _tail(path: Path, n: int = 25) -> str:
    try:
        return "\n".join(path.read_text("utf-8", "replace").splitlines()[-n:])
    except OSError:
        return ""


def signed_poster(port: int, connector_token: str) -> Callable[[dict], Awaitable[dict]]:
    def post_sync(event: dict) -> dict:
        body = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        nonce, stamp = secrets.token_hex(12), str(int(time.time()))
        status, reply = http_json(
            f"http://127.0.0.1:{port}/v1/events", data=body, timeout=180,
            headers={"content-type": "application/json",
                     "x-personagent-token": connector_token,
                     "x-personagent-timestamp": stamp,
                     "x-personagent-nonce": nonce,
                     "x-personagent-signature": sign(connector_token, body, nonce, stamp)})
        if status != 200:
            raise RuntimeError(f"/v1/events answered {status}: {reply}")
        return reply

    async def post(event: dict) -> dict:
        return await asyncio.to_thread(post_sync, event)
    return post


def dashboard_get(port: int, token: str, path: str) -> dict:
    status, body = http_json(f"http://127.0.0.1:{port}{path}",
                             headers={"x-personagent-dashboard-token": token})
    if status != 200:
        raise RuntimeError(f"{path} answered {status}")
    return body


def seeded_summary(port: int, token: str, lang: str) -> dict:
    convs = dashboard_get(port, token, "/api/dashboard/conversations")
    detail = dashboard_get(port, token, "/api/dashboard/conversation?id="
                           + urllib.parse.quote(conv_id(lang), safe=""))
    return {"conversations": convs, "detail": detail}


# ---------------------------------------------------------------------- CDP --

class WebSocket:
    """A minimal RFC 6455 client: text frames only, which is all CDP uses."""

    def __init__(self, url: str) -> None:
        parts = urllib.parse.urlsplit(url)
        self.sock = socket.create_connection((parts.hostname, parts.port), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        self.sock.sendall((
            f"GET {path} HTTP/1.1\r\nHost: {parts.hostname}:{parts.port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("websocket handshake failed")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError(head.split(b"\r\n", 1)[0].decode("latin-1"))
        self.buf = head.split(b"\r\n\r\n", 1)[1]

    def _need(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise ConnectionError("websocket closed")
            self.buf += chunk
        data, self.buf = self.buf[:n], self.buf[n:]
        return data

    def send(self, text: str) -> None:
        data = text.encode("utf-8")
        mask = os.urandom(4)
        n = len(data)
        head = bytes([0x81])
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 1 << 16:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(head + mask + masked)

    def recv(self) -> str:
        message = b""
        while True:
            b0, b1 = self._need(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._need(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._need(8))[0]
            payload = self._need(n)
            op = b0 & 0x0F
            if op == 8:
                raise ConnectionError("websocket closed by the browser")
            if op in (9, 10):
                continue
            message += payload
            if b0 & 0x80:
                return message.decode("utf-8")

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self.sock.close()


class Cdp:
    def __init__(self, ws_url: str) -> None:
        self.ws = WebSocket(ws_url)
        self.next_id = 0

    def call(self, method: str, **params):
        self.next_id += 1
        mine = self.next_id
        self.ws.send(json.dumps({"id": mine, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mine:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def eval(self, expression: str):
        res = self.call("Runtime.evaluate", expression=expression,
                        returnByValue=True, awaitPromise=True)
        if res.get("exceptionDetails"):
            raise RuntimeError("page script failed: " + json.dumps(res["exceptionDetails"])[:300])
        return res.get("result", {}).get("value")


@contextlib.contextmanager
def edge(path: str, base: Path):
    """Headless Edge with its own profile; yields a Cdp bound to one page."""
    profile = Path(tempfile.mkdtemp(prefix="pa-edge-", dir=base))
    port = free_port()
    proc = subprocess.Popen(
        [path, "--headless=new", f"--remote-debugging-port={port}",
         "--remote-allow-origins=*", f"--user-data-dir={profile}",
         "--no-first-run", "--no-default-browser-check", "--no-proxy-server",
         "--hide-scrollbars", "--disable-extensions", "--disable-background-networking",
         "--force-color-profile=srgb", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp = None
    try:
        target = ""
        for _ in range(100):
            try:
                with _DIRECT.open(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
                    pages = [t for t in json.loads(r.read()) if t.get("type") == "page"]
                if pages:
                    target = pages[0]["webSocketDebuggerUrl"]
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.3)
        if not target:
            raise RuntimeError("Edge did not open a debugging port")
        cdp = Cdp(target)
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        yield cdp
    finally:
        if cdp is not None:
            with contextlib.suppress(Exception):
                cdp.call("Browser.close")
            cdp.ws.close()
        try:
            proc.wait(8)
        except subprocess.TimeoutExpired:
            proc.kill()
        remove_tree(profile)


def wait_settled(cdp: Cdp, timeout: float = 30.0) -> None:
    """Until the page has rendered its data and stopped changing."""
    probe = ("(async()=>{await document.fonts.ready;"
             "return document.readyState+'|'+document.body.innerText.length+'|'"
             "+document.body.scrollHeight})()")
    end, last, same = time.time() + timeout, "", 0
    while time.time() < end:
        now = cdp.eval(probe)
        ready = isinstance(now, str) and now.startswith("complete")
        length = int(now.split("|")[1]) if ready else 0
        same = same + 1 if (now == last and length > 200) else 0
        last = now
        if same >= 4:
            return
        time.sleep(0.35)
    raise RuntimeError(f"the page never settled (last probe: {last})")


def capture(cdp: Cdp, url: str, spec: dict, out: Path) -> dict:
    width = spec["width"]
    mobile = bool(spec.get("mobile"))
    cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900,
             deviceScaleFactor=1, mobile=mobile)
    cdp.call("Emulation.setTouchEmulationEnabled", enabled=mobile)
    cdp.call("Emulation.setEmulatedMedia", features=[
        {"name": "prefers-color-scheme", "value": spec["theme"]},
        {"name": "prefers-reduced-motion", "value": "reduce"}])
    cdp.call("Page.addScriptToEvaluateOnNewDocument", source=(
        "try{localStorage.setItem('personagent.lang'," + json.dumps(spec["lang"])
        + ");localStorage.setItem('personagent.theme'," + json.dumps(spec["theme"])
        + ")}catch(e){}"))
    cdp.call("Page.navigate", url=url)
    time.sleep(0.8)
    wait_settled(cdp)
    height = 900
    for _ in range(3):
        size = cdp.call("Page.getLayoutMetrics")["cssContentSize"]
        want = max(600, int(size["height"] + 0.999))
        if want == height:
            break
        height = want
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                 deviceScaleFactor=1, mobile=mobile)
        time.sleep(0.5)
    wait_settled(cdp)
    overflow = cdp.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth")
    shot = cdp.call("Page.captureScreenshot", format="png", fromSurface=True,
                    clip={"x": 0, "y": 0, "width": width, "height": height, "scale": 1})
    out.write_bytes(base64.b64decode(shot["data"]))
    return {"height": height, "overflow_px": overflow}


def shrink(path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        return
    with Image.open(path) as im:
        im.load()
        rgb = im.convert("RGB")
    rgb.save(path, "PNG", optimize=True)


# --------------------------------------------------------------------- main --

def find_edge(given: str | None) -> str:
    for cand in ((given,) if given else EDGE_DEFAULTS):
        if cand and Path(cand).exists():
            return cand
    raise SystemExit("no Edge/Chromium found: pass --edge PATH")


def run(out: Path, edge_path: str, only: list[str], base: Path, port: int | None,
        say: Callable[[str], None] = print) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    wanted = [n for n in SHOTS if not only or n in only]
    unknown = sorted(set(only) - set(SHOTS))
    if unknown:
        raise SystemExit(f"unknown shot(s) {unknown}; choose from {list(SHOTS)}")
    written: list[Path] = []
    groups: dict[tuple[str, bool], list[str]] = {}
    for name in wanted:
        spec = SHOTS[name]
        groups.setdefault((spec["lang"], spec["seeded"]), []).append(name)
    stage = stage_package(base)
    try:
        for (lang, seeded), names in groups.items():
            written += _run_group(lang, seeded, names, edge_path, base, stage, out,
                                  port, say)
    finally:
        remove_tree(stage)
    return written


def _run_group(lang: str, seeded: bool, names: list[str], edge_path: str, base: Path,
               stage: Path, out: Path, port: int | None, say: Callable[[str], None]) -> list[Path]:
    written: list[Path] = []
    t0 = time.time()
    with StandIn() as standin, service(lang, base, stage, standin, port) as (svc_port, token, ctoken, _):
        if seeded:
            replies = asyncio.run(seed(signed_poster(svc_port, ctoken), standin, lang))
            said = sum(bool(r.get("replies")) for r in replies)
            say(f"[{lang}] seeded {len(replies)} events, {said} replies "
                f"({time.time() - t0:.0f}s)")
            state = seeded_summary(svc_port, token, lang)
            say(f"[{lang}] learned {len(state['detail'].get('learned', []))}, "
                f"waiting {len(state['detail'].get('pending', []))}")
        base_url = f"http://127.0.0.1:{svc_port}/"
        with edge(edge_path, base) as cdp:
            for name in names:
                spec = SHOTS[name]
                target = f"{base_url}?token={urllib.parse.quote(token)}"
                if seeded:
                    target += "#c=" + urllib.parse.quote(conv_id(lang), safe="")
                path = out / f"{name}.png"
                info = capture(cdp, target, spec, path)
                shrink(path)
                flag = "" if info["overflow_px"] <= 0 else \
                    f"  WARNING horizontal overflow {info['overflow_px']}px"
                say(f"[{name}] {path} {path.stat().st_size // 1024} KB, "
                    f"{spec['width']}x{info['height']}{flag}")
                written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", required=True, help="folder for the PNGs")
    p.add_argument("--edge", help="msedge/chromium executable (default: the usual places)")
    p.add_argument("--port", type=int, help="the service port (default: a free one)")
    p.add_argument("--only", nargs="*", default=[], metavar="NAME",
                   help=f"just these shots: {', '.join(SHOTS)}")
    p.add_argument("--tmp", help="where throwaway homes live (default: system temp)")
    args = p.parse_args(argv)
    base = Path(args.tmp) if args.tmp else Path(tempfile.gettempdir())
    base.mkdir(parents=True, exist_ok=True)
    started = time.time()
    run(Path(args.out), find_edge(args.edge), args.only, base, args.port)
    print(f"done in {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
