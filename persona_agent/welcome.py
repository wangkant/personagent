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
import os
from pathlib import Path
import re
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

from . import __version__, candidates, home as homes
from . import connections as conn
from . import direct
from .direct import base as direct_base
from . import setup_wizard as sw
from . import updates
from .astrbot_install import AstrBotInstallation, install_astrbot
from .services import Services, stop_leftovers
from .settings import normalize_lang
from .storage import FileLock, LockUnavailable, atomic_write_text

ASSETS = Path(__file__).with_name("static") / "welcome"
TOKEN_HEADER = "x-personagent-setup-token"
MAX_BODY = 16_384
# Characters; the shipped personas are under 800, and 4000 CJK characters
# still fit in MAX_BODY.
PERSONA_LIMIT = 4000
# Platforms a setting may name: the ones the page knows, or QQ through NapCat.
PLATFORM_KINDS = frozenset(p.kind for p in conn.PLATFORMS) | {"qq"}
# How long a new adapter has to fail loudly before it counts as connected.
REJECT_WINDOW = 12
# How long a direct platform may take to accept a new session.
DIRECT_WINDOW = 40
# Refusals a direct platform names, which the page explains one by one.
NAMED_REFUSALS = {"token_rejected", "app_rejected", "bot_in_use", "message_content_intent_off",
                  "intents_not_allowed", "session_expired", "bot_offline", "bot_banned"}
# The Activity view reads the character service's own API with the token it
# keeps in its runtime folder; these are the decisions the view can make.
ACTIVITY_ACTIONS = frozenset({"promote", "replace", "reject", "rollback"})
ACTIVITY_RECENT = 40
CANDIDATE_ID = re.compile(r"[0-9A-Za-z_-]{1,64}")


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
            updates.refresh_soon(self.home)
            return {"version": __version__, "update": updates.notice(self.home),
                    "configured": bool(values.get("LLM_API_KEY")),
                    "provider": known.key if known else ("other" if values.get("LLM_BASE_URL") else "deepseek"),
                    "model": values.get("LLM_MODEL", ""), "baseUrl": values.get("LLM_BASE_URL", ""),
                    "keyHint": sw.mask_secret(values["LLM_API_KEY"]) if values.get("LLM_API_KEY") else "",
                    "name": values.get("PERSONA_NAME", ""), "lang": values.get("AGENT_LANG", ""),
                    "character": origin[0] if origin else ("custom" if card.is_file() else "warm-listener"),
                    "platformInstalled": installation.python.is_file(),
                    "platforms": platforms, "platformStatus": status,
                    "agentRunning": self.services.running("agent"),
                    "platformRunning": self.services.running("astrbot") or direct_on, "job": job,
                    "features": self._features(values)}

    @staticmethod
    def _features(values: dict) -> dict:
        """The optional features, with no key in them."""
        vision_key, vision_base = values.get("VISION_API_KEY", ""), values.get("VISION_BASE_URL", "")
        same = bool(vision_base) and (vision_base.rstrip("/") == values.get("LLM_BASE_URL", "").rstrip("/")
                                      and vision_key == values.get("LLM_API_KEY", ""))
        return {"search": "tavily" if values.get("TAVILY_API_KEY") else "free",
                "vision": {"enabled": bool(values.get("VISION_MODEL")), "model": values.get("VISION_MODEL", ""),
                           "sameAsChat": same, "baseUrl": "" if same else vision_base,
                           "keyHint": sw.mask_secret(vision_key) if vision_key and not same else ""},
                "proactive": {"enabled": values.get("PROACTIVE_ENABLED", "").strip().lower()
                              in ("1", "true", "yes", "on"),
                              "platforms": sw.split_ids(values.get("PROACTIVE_PLATFORMS", ""))}}

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
            if (not name or len(name) > 64 or _expands(name)
                    or character not in (*sw.PERSONA_KEYS, "custom")):
                raise ValueError("invalid_character")
            # dotenv would read ${VAR} back as another setting, a key included.
            if _expands(key):
                raise ValueError("key_required")
            if _expands(base):
                raise ValueError("invalid_url")
            if _expands(model):
                raise ValueError("model_required")
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
            self._restart_agent()
            return self.summary()

    def _restart_agent(self) -> None:
        """A running agent reads its settings and persona only as it starts."""
        was_running = self.services.running("agent")
        self.services.stop("agent")
        if was_running:
            self.services.start_agent()
            if self.services.running("astrbot"):
                self._connect_plugin()

    def persona(self) -> dict:
        """The persona the agent runs on: persona.txt, else the bundled
        template filled in the way the agent fills it."""
        with self._lock:
            path = self.home / "persona.txt"
            if path.is_file():
                return {"text": path.read_text(encoding="utf-8").strip()}
            values = self.config()
            lang = "zh" if normalize_lang(values.get("AGENT_LANG")) == "zh" else "en"
            text = sw.persona_text(sw.TEMPLATE, name=values.get("PERSONA_NAME") or sw.DEFAULT_NAMES[lang],
                                   lang=lang, admin_name=values.get("ADMIN_NAME", ""),
                                   admin_relationship=values.get("ADMIN_RELATIONSHIP", ""))
            return {"text": text.strip()}

    def save_features(self, payload: dict) -> dict:
        """Web search, image understanding and speaking first. A key left
        blank keeps the saved one; none is ever returned."""
        search = payload.get("search") or {}
        vision = payload.get("vision") or {}
        proactive = payload.get("proactive") or {}
        if not all(isinstance(part, dict) for part in (search, vision, proactive)):
            raise ValueError("invalid_feature")
        with self._lock:
            if self._future is not None and not self._future.done():
                raise ValueError("busy")
            old = self.config()
            values: dict[str, str] = {}
            tavily = _key(search.get("tavilyKey"))
            if search.get("clear"):
                values["TAVILY_API_KEY"] = ""
            elif tavily:
                values["TAVILY_API_KEY"] = tavily
            if vision.get("enabled"):
                model = str(vision.get("model") or "").strip()
                if not model or len(model) > 256 or any(c.isspace() for c in model) or _expands(model):
                    raise ValueError("model_required")
                if vision.get("sameAsChat"):
                    base, key = old.get("LLM_BASE_URL", ""), old.get("LLM_API_KEY", "")
                else:
                    base = _endpoint(vision.get("baseUrl"))
                    key = _key(vision.get("apiKey"))
                    # A key is never forwarded to an address it was not saved for.
                    if not key and base.rstrip("/") == old.get("VISION_BASE_URL", "").rstrip("/"):
                        key = old.get("VISION_API_KEY", "")
                    if not key:
                        raise ValueError("key_required")
                values.update(VISION_MODEL=model, VISION_BASE_URL=base, VISION_API_KEY=key)
            else:
                values["VISION_MODEL"] = ""
            platforms = proactive.get("platforms") or []
            if not isinstance(platforms, list) or any(str(p) not in PLATFORM_KINDS for p in platforms):
                raise ValueError("invalid_feature")
            # The page offers only connected apps: an entry it could not show
            # (qq for NapCat, an app connected later) is kept, or an empty
            # list would widen the restriction to every platform.
            offered = set(self.summary()["platforms"])
            kept = [p for p in sw.split_ids(old.get("PROACTIVE_PLATFORMS", "")) if p not in offered]
            values["PROACTIVE_ENABLED"] = "true" if proactive.get("enabled") else "false"
            values["PROACTIVE_PLATFORMS"] = ",".join(dict.fromkeys(kept + [str(p) for p in platforms]))
            sw.write_env(self.env, values)
            self._restart_agent()
            return self.summary()

    def save_persona(self, text: str) -> dict:
        """Write `text` as persona.txt and restart a running agent on it.
        What the character learned is kept: it is not part of the file."""
        text = text.replace("\r\n", "\n").strip()
        if not text or len(text) > PERSONA_LIMIT:
            raise ValueError("invalid_persona")
        with self._lock:
            if self._future is not None and not self._future.done():
                raise ValueError("busy")
            atomic_write_text(self.home / "persona.txt", text + "\n")
            self._restart_agent()
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
                # A scan platform may also take pasted values, if it has fields.
                if action == "scan" and spec.group != conn.SCAN or action == "connect" and not spec.fields:
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
        from .direct import qq, weixin

        scan, failed = ((qq.bind, qq.BindFailed) if spec.kind == "qq_official"
                        else (weixin.login, weixin.LoginFailed))

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
                task = asyncio.create_task(scan(client, show))
                while not task.done():
                    if self._cancelled or self._closed:
                        task.cancel()
                        raise RuntimeError("cancelled")
                    await asyncio.sleep(0.3)
                return task.result()
        try:
            values = asyncio.run(login())
        except failed:
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

    def _activity_token(self) -> str:
        # Where the service keeps it, read the way the service's own process
        # gets it: .env over this process's environment, else <home>/runtime.
        configured = dotenv_values(self.env).get("AGENT_RUNTIME_DIR")
        if configured is None:
            configured = os.environ.get("AGENT_RUNTIME_DIR", "")
        runtime = Path(configured.strip() or "runtime").expanduser()
        if not runtime.is_absolute():
            runtime = self.home / runtime
        try:
            return (runtime / "dashboard.token").read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            return ""

    async def _activity_call(self, method: str, path: str, **kwargs) -> dict | None:
        """The service's answer; None while it is not running, {"off": True}
        when DASHBOARD_ENABLED is off."""
        if not self.services.running("agent"):
            return None
        headers = {"X-Personagent-Dashboard-Token": self._activity_token()}
        if method == "POST":
            headers["X-Personagent-Dashboard"] = "1"
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
                response = await client.request(method, self.services.agent_url + path,
                                                headers=headers, **kwargs)
            value = response.json()
        except (httpx.HTTPError, ValueError):
            raise ValueError("activity_unavailable") from None
        if not isinstance(value, dict):
            raise ValueError("activity_unavailable")
        if response.status_code == 404 and value.get("detail") == "Not Found":
            return {"off": True}
        if response.status_code == 409:
            raise ValueError("activity_changed")
        if response.status_code != 200:
            raise ValueError("activity_unavailable")
        return value

    async def activity(self) -> dict:
        raw = await self._activity_call("GET", "/api/dashboard/conversations")
        if raw is None or raw.get("off"):
            return {"running": raw is not None, "off": bool(raw), "chats": []}
        chats = [{"id": str(c.get("id", "")), "platform": str(c.get("platform", "")),
                  "kind": str(c.get("kind", "")), "last": c.get("last_activity", 0),
                  "review": int(c.get("pending", 0)), "learned": int(c.get("learned", 0)),
                  "notes": int(c.get("memories", 0))}
                 for c in raw.get("conversations", []) if isinstance(c, dict)]
        return {"running": True, "off": False, "chats": chats}

    async def activity_chat(self, chat: str) -> dict:
        chat = str(chat or "")
        if not chat or len(chat) > 512:
            raise ValueError("invalid_chat")
        raw = await self._activity_call("GET", "/api/dashboard/conversation", params={"id": chat})
        if raw is None or raw.get("off"):
            raise ValueError("activity_unavailable")
        return _activity_chat(raw)

    async def activity_decide(self, payload: dict) -> dict:
        cid, action = str(payload.get("id") or ""), str(payload.get("action") or "")
        chat = str(payload.get("chat") or "")
        if (action not in ACTIVITY_ACTIONS or not CANDIDATE_ID.fullmatch(cid)
                or not chat or len(chat) > 512):
            raise ValueError("invalid_chat")
        result = await self._activity_call("POST", f"/api/dashboard/candidates/{cid}/{action}",
                                           json={"reason": "local page"})
        if result is None or result.get("off"):
            raise ValueError("activity_unavailable")
        return await self.activity_chat(chat)

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self.services.shutdown()
        self.worker.shutdown(wait=False, cancel_futures=True)


def _activity_chat(raw: dict) -> dict:
    """One chat as the Activity view shows it: what waits for a decision,
    what it learned, what it remembers and what it recently did. The
    service's checklists, evidence and history stay with `personagent learned`."""
    def item(cand: dict) -> dict:
        speakers = [e.get("speaker") for e in cand.get("evidence") or [] if e.get("speaker")]
        return {"id": cand.get("id", ""),
                "kind": "wording" if cand.get("type") == candidates.TYPE_PAIR else "repeat",
                "said": cand.get("reply", ""), "better": cand.get("better", ""),
                "lesson": cand.get("lesson", ""),
                "when": cand.get("created", 0), "from": list(dict.fromkeys(speakers))[:3],
                "actions": [a for a in cand.get("actions") or [] if a in ACTIVITY_ACTIONS]}

    return {"id": raw.get("id", ""), "platform": raw.get("platform", ""), "kind": raw.get("kind", ""),
            "review": [item(c) for c in raw.get("pending") or []],
            "learned": [item(c) for c in raw.get("learned") or []],
            "notes": [{"text": m.get("text", ""), "by": m.get("by", ""), "when": m.get("time", 0)}
                      for m in raw.get("memories") or []],
            "recent": [{"when": d.get("ts", 0), "spoke": bool(d.get("spoke")), "mode": d.get("mode", ""),
                        "reason": d.get("reason", ""), "text": d.get("excerpt", ""),
                        "answered": d.get("answered", ""), "sender": d.get("sender", ""),
                        "count": int(d.get("count") or 1)}
                       for d in (raw.get("decisions") or [])[:ACTIVITY_RECENT]][::-1]}


def _expands(text: str) -> bool:
    """Would dotenv read `text` back as another setting? It expands ${VAR}
    even inside quotes, so ${LLM_API_KEY} saved as a vision key is the chat key."""
    return "${" in str(text)


def _key(value) -> str:
    """A pasted key: one token, no spaces, line breaks or ${...}."""
    text = str(value or "").strip()
    if len(text) > 4096 or any(c.isspace() for c in text) or _expands(text):
        raise ValueError("invalid_feature")
    return text


def _endpoint(value) -> str:
    """An OpenAI-compatible base URL: https, or http only on this computer."""
    base = str(value or "").strip()
    parsed = urlsplit(base)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username
            or parsed.password or _expands(base)):
        raise ValueError("invalid_url")
    if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("https_required")
    return base.rstrip("/")


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
                   "field_required", "invalid_field", "invalid_persona", "invalid_feature",
                   "invalid_chat", "activity_unavailable", "activity_changed"}
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

    @app.post("/api/features")
    async def save_features(request: Request):
        return await asyncio.to_thread(workspace.save_features, await body(request))

    @app.get("/api/persona")
    async def persona():
        return await asyncio.to_thread(workspace.persona)

    @app.post("/api/persona")
    async def save_persona(request: Request):
        payload = await body(request)
        return await asyncio.to_thread(workspace.save_persona, str(payload.get("text") or ""))

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
        # A scan platform takes pasted values only when the page says so.
        scan = conn.platform(kind).group == conn.SCAN and payload.get("mode") != "paste"
        workspace.start_job("scan" if scan else "connect", kind, payload.get("values") or {})
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

    @app.get("/api/activity")
    async def activity():
        return await workspace.activity()

    @app.get("/api/activity/chat")
    async def activity_chat(id: str = ""):
        return await workspace.activity_chat(id)

    @app.post("/api/activity/decide")
    async def activity_decide(request: Request):
        return await workspace.activity_decide(await body(request))

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
        notice = updates.line(updates.notice(home))
        if notice:
            print(notice, flush=True)
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
