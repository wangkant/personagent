"""Local, capability-protected setup, chat and platform connections. No account
is needed to open it. QQ, WeChat, Telegram and Discord are connected directly;
the other platforms go through a managed AstrBot with no login of its own."""
from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import importlib.util
import json
from pathlib import Path
import secrets
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit
import webbrowser

import httpx
from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from . import __version__, home as homes
from . import connections as conn
from . import direct
from .direct import base as direct_base
from . import setup_wizard as sw
from .astrbot_install import AstrBotInstallation, install_astrbot
from .services import Services, stop_leftovers
from .storage import FileLock, LockUnavailable, atomic_write_text

ASSETS = Path(__file__).with_name("static") / "welcome"
TOKEN_HEADER = "x-personagent-setup-token"
MAX_BODY = 16_384
# How long a new adapter has to fail loudly before it counts as connected.
REJECT_WINDOW = 12
# How long a direct platform may take to accept a new session.
DIRECT_WINDOW = 40
# Refusals a direct platform names, which the page explains one by one.
NAMED_REFUSALS = {"token_rejected", "app_rejected", "bot_in_use", "message_content_intent_off",
                  "intents_not_allowed", "session_expired", "bot_offline", "bot_banned"}


def _connector_type():
    source = homes.resource("integrations", "astrbot", sw.PLUGIN_NAME, "personagent_connector.py")
    spec = importlib.util.spec_from_file_location("_personagent_local_connector", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Connector


class Workspace:
    def __init__(self, home: Path):
        self.home = home.resolve()
        self.services = Services(self.home)
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="personagent-setup")
        self._lock = threading.RLock()
        self._chat_lock = asyncio.Lock()
        self._future = None
        self._closed = False
        self._cancelled = False
        # Set when a job took a platform away from AstrBot, which then needs a restart.
        self._astrbot_changed = False
        # A platform whose saved state belongs to a login that just ended.
        self._stale_state = ""
        self._history_path = self.home / "runtime" / "desktop" / "browser-chat.json"
        saved = sw._read_json(self._history_path)
        self._conversation = str(saved.get("conversation") or secrets.token_hex(12))[:64]
        self._history = [item for item in saved.get("messages", [])
                         if isinstance(item, dict) and item.get("role") in ("user", "assistant")
                         and isinstance(item.get("text"), str)][-50:]
        self.job = {"state": "idle", "stage": "", "error": ""}

    @property
    def env(self) -> Path:
        return self.home / ".env"

    def config(self) -> dict:
        return {k: str(v or "") for k, v in dotenv_values(self.env).items()}

    def summary(self) -> dict:
        with self._lock:
            values = self.config()
            known = sw.provider_for_base(values.get("LLM_BASE_URL", ""))
            installation = AstrBotInstallation(self.home)
            card = self.home / "persona.txt"
            origin = sw.shipped_persona(card.read_text(encoding="utf-8")) if card.is_file() else None
            job = dict(self.job)
            via_astrbot = conn.connected(installation.root / "data")
            stored = direct_base.load_credentials(self.home)
            states = direct_base.read_status(self.home)
            direct_on = self.services.running("direct")
            platforms = [p.kind for p in conn.PLATFORMS
                         if p.kind in stored or (p.kind in via_astrbot and p.kind not in stored)]
            status = {}
            for kind in platforms:
                if kind in stored:
                    # A refusal outlives the runner, which exits once nothing is left to run.
                    state = states.get(kind, {}).get("state")
                    status[kind] = ("failed" if state in ("refused", "error") else "paused" if not direct_on
                                    else "running" if state == "connected" else "connecting")
                else:
                    status[kind] = "running" if self.services.running("astrbot") else "paused"
            return {"version": __version__, "configured": bool(values.get("LLM_API_KEY")),
                    "provider": known.key if known else ("other" if values.get("LLM_BASE_URL") else "deepseek"),
                    "model": values.get("LLM_MODEL", ""), "baseUrl": values.get("LLM_BASE_URL", ""),
                    "keyHint": sw.mask_secret(values["LLM_API_KEY"]) if values.get("LLM_API_KEY") else "",
                    "name": values.get("PERSONA_NAME", ""), "lang": values.get("AGENT_LANG", ""),
                    "character": origin[0] if origin else ("custom" if card.is_file() else "warm-listener"),
                    "platformInstalled": installation.python.is_file(),
                    "platforms": platforms, "platformStatus": status,
                    "agentRunning": self.services.running("agent"),
                    "platformRunning": self.services.running("astrbot") or direct_on, "job": job}

    def save(self, payload: dict) -> dict:
        with self._lock:
            if self._future is not None and not self._future.done():
                raise ValueError("busy")
            old = self.config()
            provider = sw.provider_named(str(payload.get("provider") or "deepseek"))
            if provider is None:
                raise ValueError("invalid_provider")
            previous = sw.provider_for_base(old.get("LLM_BASE_URL", ""))
            same = ((previous is not None and previous.key == provider.key)
                    or (previous is None and provider.key == "other" and bool(old.get("LLM_BASE_URL"))))
            base = str(payload.get("baseUrl") or provider.base_url).strip()
            same = same and base.rstrip("/") == old.get("LLM_BASE_URL", "").rstrip("/")
            key = str(payload.get("apiKey") or "").strip()
            if not key and same:
                key = old.get("LLM_API_KEY", "")
            if provider.key == "ollama":
                key = key or "ollama"
            if not key or len(key) > 4096:
                raise ValueError("key_required")
            parsed = urlsplit(base)
            if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("invalid_url")
            if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
                raise ValueError("https_required")
            model = str(payload.get("model") or provider.model).strip()
            if not model or len(model) > 256:
                raise ValueError("model_required")
            lang = "zh" if payload.get("lang") == "zh" else "en"
            name = str(payload.get("name") or sw.DEFAULT_NAMES[lang]).strip()
            character = str(payload.get("character") or "warm-listener")
            if not name or len(name) > 64 or character not in (*sw.PERSONA_KEYS, "custom"):
                raise ValueError("invalid_character")
            try:
                probe = sw.probe_key(base, key, model, timeout=20)
            except Exception:
                raise ValueError("model_unreachable") from None
            if not probe.ok:
                # Never return an upstream response body: it may echo a key.
                raise ValueError("key_rejected" if probe.status in (401, 403) else "model_unreachable")
            sw.copy_env_template(self.home)
            values = {"LLM_BASE_URL": base, "LLM_MODEL": model, "LLM_API_KEY": key,
                      "PERSONA_NAME": name, "AGENT_LANG": lang,
                      "CONNECTOR_TOKEN": old.get("CONNECTOR_TOKEN") or secrets.token_urlsafe(32)}
            sw.write_env(self.env, values)
            if character != "custom":
                sw.write_persona(self.home, character, name=name, lang=lang,
                                 admin_name=old.get("ADMIN_NAME", ""),
                                 admin_relationship=old.get("ADMIN_RELATIONSHIP", ""))
            was_running = self.services.running("agent")
            self.services.stop("agent")
            if was_running:
                self.services.start_agent()
                if self.services.running("astrbot"):
                    self._connect_plugin()
            return self.summary()

    def history(self) -> dict:
        return {"messages": list(self._history)}

    def reset_chat(self) -> None:
        self._conversation = secrets.token_hex(12)
        self._history = []
        self._save_chat()

    def _save_chat(self) -> None:
        atomic_write_text(self._history_path, json.dumps({"conversation": self._conversation,
                                                        "messages": self._history}, ensure_ascii=False))

    def start_job(self, action: str, kind: str = "", values: dict | None = None) -> None:
        """Run `action` in the background: "start", or "scan", "connect" or
        "disconnect" for one platform. Field errors are raised here, before
        anything is downloaded."""
        with self._lock:
            if self._future is not None and not self._future.done():
                raise ValueError("busy")
            if not self.config().get("LLM_API_KEY"):
                raise ValueError("key_required")
            if action == "start":
                args = ()
            elif action in ("scan", "connect", "disconnect"):
                spec = conn.platform(kind)
                if (action == "scan") != (spec.group == conn.SCAN) and action != "disconnect":
                    raise ValueError("invalid_platform")
                args = (spec, conn.clean_values(spec, values or {})) if action == "connect" else (spec,)
            else:
                raise ValueError("invalid_action")
            own = bool(args) and conn.is_direct(kind)
            stage = ("start" if action in ("start", "disconnect") else
                     "prepare" if own and action == "scan" else "check" if own else "install")
            self.job = {"state": "working", "stage": stage, "error": "", "action": action,
                        "platform": kind}
            self._cancelled = False
            self._astrbot_changed = False
            self._stale_state = ""
            self._future = self.worker.submit(self._job, action, *args)

    def _job(self, action: str, *args) -> None:
        own = bool(args) and conn.is_direct(args[0].kind)
        try:
            if own:
                {"scan": self._scan_direct, "connect": self._connect_direct,
                 "disconnect": self._disconnect_direct}[action](*args)
            elif action == "connect":
                self._connect(*args)
            elif action == "disconnect":
                self._disconnect(*args)
            if self._closed or self._cancelled:
                raise RuntimeError("cancelled")
            self._stage("start")
            self.services.start_agent()
            if self._closed:
                return
            data = AstrBotInstallation(self.home).root / "data"
            if conn.connected(data):
                self._connect_plugin()
                if self._closed:
                    return
                if own and self._astrbot_changed:
                    self.services.restart_astrbot()
                elif action == "start" or own:
                    self.services.start_astrbot()
                else:
                    # AstrBot reads its platform list only when it starts.
                    offset = self.services.restart_astrbot()
                    if action != "disconnect":
                        self._stage("check")
                        if self.services.logged("astrbot", offset, conn.failure_pattern(args[0].kind),
                                                REJECT_WINDOW):
                            # Its log line can quote the credential; report only that it failed.
                            self._disconnect(args[0])
                            raise RuntimeError("platform_rejected")
            else:
                self.services.stop("astrbot")
            if own:
                self.services.restart_direct(between=self._clear_stale_state)
                if action != "disconnect":
                    self._await_direct(args[0])
            else:
                self.services.start_direct()
            self.job = {**self.job, "state": "ready", "stage": "ready", "error": ""}
        except Exception as exc:
            if not self._closed:
                # Detailed dependency logs stay on disk; do not return secrets.
                reason = str(exc)
                error = ("download_failed" if isinstance(exc, subprocess.CalledProcessError)
                         else reason if reason in NAMED_REFUSALS
                         or reason in ("scan_failed", "platform_rejected", "network_failed")
                         else "service_failed" if self.job.get("stage") == "start"
                         else "setup_failed")
                self.job = ({"state": "idle", "stage": "", "error": ""} if self._cancelled else
                            {**self.job, "state": "error", "stage": "", "error": error})
        finally:
            if self._closed:
                self.services.close()

    def _stage(self, stage: str) -> None:
        self.job = {**self.job, "stage": stage}

    def _connect_plugin(self) -> None:
        data = AstrBotInstallation(self.home).root / "data"
        if not (data / "cmd_config.json").is_file():
            raise RuntimeError("platform_not_installed")
        values = {}
        # OneBot (NapCat) carries QQ numbers, which the agent reads bare.
        sw.connect_astrbot(self.env, values, data_dir=data, qq="aiocqhttp" in conn.connected(data),
                           groups=None, dm_users=None)
        sw.write_env(self.env, values)

    def _install(self) -> Path:
        data = install_astrbot(self.home)
        if self._closed or self._cancelled:
            raise RuntimeError("cancelled")
        return data

    def _add(self, data: Path, spec: conn.Platform, values: dict) -> None:
        template = conn.astrbot_template(AstrBotInstallation(self.home), spec.kind)
        conn.save_entry(data, conn.entry(template, spec, values))
        self._connect_plugin()
        sw.write_astrbot_config(data, conn.scope(sw.read_astrbot_config(data), spec.kind, allow=True))

    def _connect(self, spec: conn.Platform, values: dict) -> None:
        self._add(self._install(), spec, values)

    def _disconnect(self, spec: conn.Platform) -> None:
        data = AstrBotInstallation(self.home).root / "data"
        if not (data / "cmd_config.json").is_file():
            return
        conn.remove_entry(data, spec.kind)
        self._connect_plugin()
        sw.write_astrbot_config(data, conn.scope(sw.read_astrbot_config(data), spec.kind, allow=False))

    # ---- platforms personagent connects itself

    def _store_direct(self, spec: conn.Platform, values: dict) -> None:
        self._stale_state = spec.kind
        direct_base.save_credentials(self.home, spec.kind, values)
        self._release_from_astrbot(spec)

    def _release_from_astrbot(self, spec: conn.Platform) -> None:
        """One bot cannot be served twice: drop an AstrBot connection of the
        same platform, made before personagent connected it itself."""
        if spec.kind in conn.connected(AstrBotInstallation(self.home).root / "data"):
            self._disconnect(spec)
            self._astrbot_changed = True

    def _connect_direct(self, spec: conn.Platform, values: dict) -> None:
        platform = direct.platform_for(spec.kind, values, self.home)

        async def check() -> None:
            try:
                await platform.check()
            finally:
                await platform.close()
        try:
            asyncio.run(check())
        except direct_base.Refused as exc:
            raise RuntimeError(str(exc) if str(exc) in NAMED_REFUSALS else "platform_rejected") from None
        except ConnectionError:
            raise RuntimeError("network_failed") from None
        self._store_direct(spec, values)

    def _scan_direct(self, spec: conn.Platform) -> None:
        import httpx
        from .direct import weixin

        def show(content: str) -> None:
            import base64
            import io
            import qrcode

            image = io.BytesIO()
            qrcode.make(content).save(image, format="PNG")
            self.job = {**self.job, "stage": "scan", "qrUrl": content,
                        "qrImage": "data:image/png;base64," + base64.b64encode(image.getvalue()).decode()}

        async def login() -> dict:
            async with httpx.AsyncClient() as client:
                task = asyncio.create_task(weixin.login(client, show))
                while not task.done():
                    if self._cancelled or self._closed:
                        task.cancel()
                        raise RuntimeError("cancelled")
                    await asyncio.sleep(0.3)
                return task.result()
        try:
            values = asyncio.run(login())
        except weixin.LoginFailed:
            raise RuntimeError("scan_failed") from None
        except (httpx.HTTPError, ValueError):
            raise RuntimeError("network_failed") from None
        self._store_direct(spec, values)

    def _disconnect_direct(self, spec: conn.Platform) -> None:
        direct_base.remove_credentials(self.home, spec.kind)
        self._stale_state = spec.kind
        self._release_from_astrbot(spec)

    def _clear_stale_state(self) -> None:
        """Run between stopping and starting the direct process: the old
        process would otherwise write the ended login's state back."""
        if self._stale_state:
            direct.state_path(self.home, self._stale_state).unlink(missing_ok=True)

    def _await_direct(self, spec: conn.Platform) -> None:
        """Wait for the new session to be accepted; a refusal is rolled back."""
        deadline = time.monotonic() + DIRECT_WINDOW
        self._stage("check")
        while time.monotonic() < deadline and not self._closed:
            state = direct_base.read_status(self.home).get(spec.kind, {})
            if state.get("state") == "connected":
                return
            if state.get("state") in ("refused", "error") or not self.services.running("direct"):
                detail = str(state.get("detail") or "")
                self._disconnect_direct(spec)
                self.services.restart_direct()
                raise RuntimeError(detail if detail in NAMED_REFUSALS else "platform_rejected")
            time.sleep(0.5)
        # Still connecting: kept, and the page shows it as connecting.

    def cancel(self) -> None:
        self._cancelled = True

    async def chat(self, text: str) -> dict:
        if not self.config().get("LLM_API_KEY"):
            raise ValueError("key_required")
        if not text.strip() or len(text) > 8000:
            raise ValueError("invalid_message")
        async with self._chat_lock:
            await asyncio.to_thread(self.services.start_agent)
            values = self.config()
            async with httpx.AsyncClient(trust_env=False) as client:
                connector = _connector_type()(self.services.agent_url, values.get("CONNECTOR_TOKEN", ""),
                                              connector_id="local-welcome", timeout_s=120, client=client)
                try:
                    response = await connector.send_event({
                        "kind": "event", "platform": "browser", "conversation_type": "dm",
                        "conversation_id": self._conversation, "sender_id": self._conversation,
                        "sender_name": "you", "message_id": secrets.token_hex(12),
                        "sent_at": int(time.time()),
                        "text": text, "segments": [{"type": "text", "text": text}], "prefiltered": True,
                    })
                finally:
                    await connector.aclose()
            reply = "\n".join(str(item.get("text", "")) for item in response.get("replies", [])
                              if item.get("type") == "text")
            self._history.extend([{"role": "user", "text": text}, {"role": "assistant", "text": reply}])
            self._history = self._history[-50:]
            self._save_chat()
            return {"reply": reply}

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self.services.shutdown()
        self.worker.shutdown(wait=False, cancel_futures=True)


def create_app(home: Path, token: str, *, workspace: Workspace | None = None) -> FastAPI:
    workspace = workspace or Workspace(home)

    @asynccontextmanager
    async def lifespan(app):
        try:
            if workspace.summary()["platforms"] and workspace.config().get("LLM_API_KEY"):
                workspace.start_job("start")
            yield
        finally:
            await asyncio.to_thread(workspace.close)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.workspace = workspace

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        try:
            host = urlsplit("//" + request.headers.get("host", "")).hostname
        except ValueError:
            return JSONResponse({"error": "forbidden"}, status_code=403)
        if host not in ("localhost", "127.0.0.1", "::1"):
            return JSONResponse({"error": "forbidden"}, status_code=403)
        if request.url.path.startswith("/api/"):
            if not secrets.compare_digest(request.headers.get(TOKEN_HEADER, "").encode(), token.encode()):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            if any(request.headers.get(key) for key in ("x-forwarded-host", "forwarded", "x-forwarded-for")):
                return JSONResponse({"error": "forbidden"}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        return response

    async def body(request: Request) -> dict:
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_BODY:
                raise HTTPException(413, "too_large")
        try:
            value = json.loads(raw or b"{}")
        except ValueError:
            raise HTTPException(400, "invalid_json") from None
        if not isinstance(value, dict):
            raise HTTPException(400, "invalid_json")
        return value

    @app.exception_handler(ValueError)
    async def bad_value(request, exc):
        allowed = {"busy", "invalid_provider", "key_required", "invalid_url", "https_required",
                   "model_required", "invalid_character", "key_rejected", "model_unreachable",
                   "permission_required", "invalid_message", "invalid_platform",
                   "field_required", "invalid_field"}
        error = str(exc)
        return JSONResponse({"error": error if error in allowed else "generic"}, status_code=400)

    @app.get("/")
    async def index():
        return FileResponse(ASSETS / "index.html")

    @app.get("/assets/{name}")
    async def asset(name: str):
        if name not in ("welcome.js", "welcome.css"):
            raise HTTPException(404)
        return FileResponse(ASSETS / name)

    @app.get("/api/state")
    async def state():
        return await asyncio.to_thread(workspace.summary)

    @app.get("/api/catalog")
    async def catalog():
        return {"providers": [{"id": p.key, "name": list(p.name), "baseUrl": p.base_url,
                               "model": p.model, "keyUrl": p.key_url} for p in sw.PROVIDERS],
                "characters": [{"id": c.key, "name": list(c.title)} for c in sw.CHARACTERS],
                "platforms": conn.catalog()}

    @app.post("/api/config")
    async def config(request: Request):
        return await asyncio.to_thread(workspace.save, await body(request))

    @app.post("/api/key")
    async def reveal(request: Request):
        await body(request)
        return {"apiKey": workspace.config().get("LLM_API_KEY", "")}

    @app.post("/api/platforms/connect")
    async def connect_platform(request: Request):
        payload = await body(request)
        if payload.get("allowConversations") is not True:
            raise ValueError("permission_required")
        kind = str(payload.get("platform") or "")
        action = "scan" if conn.platform(kind).group == conn.SCAN else "connect"
        workspace.start_job(action, kind, payload.get("values") or {})
        return {"ok": True}

    @app.post("/api/platforms/disconnect")
    async def disconnect_platform(request: Request):
        payload = await body(request)
        workspace.start_job("disconnect", str(payload.get("platform") or ""))
        return {"ok": True}

    @app.post("/api/platforms/cancel")
    async def cancel_platform(request: Request):
        await body(request)
        workspace.cancel()
        return {"ok": True}

    @app.post("/api/start")
    async def start(request: Request):
        await body(request)
        workspace.start_job("start")
        return {"ok": True}

    @app.post("/api/stop")
    async def stop(request: Request):
        await body(request)
        if workspace._future is not None and not workspace._future.done():
            raise ValueError("busy")
        await asyncio.to_thread(workspace.services.close)
        return {"ok": True}

    @app.post("/api/chat")
    async def chat(request: Request):
        payload = await body(request)
        try:
            return await workspace.chat(str(payload.get("text") or ""))
        except ValueError:
            raise
        except Exception:
            return JSONResponse({"error": "chat_failed"}, status_code=502)

    @app.post("/api/chat/reset")
    async def reset(request: Request):
        await body(request)
        async with workspace._chat_lock:
            workspace.reset_chat()
        return {"ok": True}

    @app.get("/api/chat/history")
    async def history():
        return workspace.history()

    @app.post("/api/exit")
    async def exit_app(request: Request):
        await body(request)
        await asyncio.to_thread(workspace.close)
        callback = getattr(app.state, "shutdown", None)
        if callback:
            callback()
        return {"ok": True}

    return app


def main(argv: list[str] | None = None, prog: str = "personagent start") -> int:
    import uvicorn
    parser = argparse.ArgumentParser(prog=prog, description="Open local setup and chat in your browser")
    parser.add_argument("--no-browser", action="store_true", help="print the local link without opening a browser")
    parser.add_argument("--terminal", action="store_true", help="use the terminal menu instead")
    parser.add_argument("--port", type=int, default=0, help="local page port (default: choose automatically)")
    args = parser.parse_args(argv)
    if args.terminal:
        return sw.start_main([])
    home = homes.find_home()
    info = home / "runtime" / "desktop" / "welcome.json"
    lock = FileLock(info.with_suffix(".lock"), timeout=0)
    try:
        lock.acquire()
    except LockUnavailable:
        url = sw._read_json(info).get("url", "")
        if not url:
            print("personagent is starting. Try again in a moment.")
            return 1
        print(url, flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        return 0
    token = secrets.token_urlsafe(32)
    sock = socket.socket()
    try:
        stopped = stop_leftovers(home)
        if stopped:
            print(f"Stopped what an earlier personagent left running: {', '.join(stopped)}.")
        sock.bind(("127.0.0.1", args.port))
        sock.listen(128)
        port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}/#token={token}"
        atomic_write_text(info, json.dumps({"url": url}))
        print(f"personagent {__version__}\n\n  {url}\n\nKeep this window open. Press Ctrl+C to stop.", flush=True)
        if not args.no_browser:
            timer = threading.Timer(0.8, webbrowser.open, args=(url,))
            timer.daemon = True
            timer.start()
        app = create_app(home, token)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        app.state.shutdown = lambda: setattr(server, "should_exit", True)
        server.run(sockets=[sock])
        return 0
    finally:
        sock.close()
        info.unlink(missing_ok=True)
        lock.release()
