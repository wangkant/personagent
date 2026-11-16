"""The signin panel: sign in with OpenRouter instead of pasting a key. The page
starts an attempt, the system's browser shows OpenRouter's approval, and
OpenRouter sends the browser back to this server's callback with a code, which
the server exchanges for a key and saves the way the form's own save does. The
key and the PKCE verifier never reach the page."""
from __future__ import annotations

import asyncio
import html
import json
import secrets
import threading
import time
import webbrowser

from fastapi import Request
from fastapi.responses import HTMLResponse

from .. import openrouter_signin as osr
from .. import setup_wizard as sw

ERRORS: frozenset[str] = frozenset({"signin_provider", "signin_code_invalid", "signin_link_invalid"})
# Where OpenRouter sends the browser back; outside /api/, as a navigation carries no token.
CALLBACK_PATH = "/signin/openrouter"
# The form's own fields the save takes; the key comes only from the exchange.
FORM_FIELDS = ("baseUrl", "model", "name", "character", "avatar", "lang")
# What the save may refuse with, which the page explains in its own words.
SAVE_ERRORS = frozenset({"busy", "key_rejected", "model_limited", "model_unreachable", "model_required",
                         "invalid_character", "name_required", "invalid_url", "https_required",
                         "key_malformed"})


def open_browser(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


class Attempt:
    def __init__(self, form: dict, lang: str):
        self.state = secrets.token_urlsafe(32)
        self.verifier = osr.new_verifier()
        self.started = time.monotonic()
        self.form = form
        self.lang = lang
        self.status = "waiting"
        self.error = ""
        self.url = ""
        # From another device: the person pastes the code OpenRouter shows.
        self.by_code = False


class SignIn:
    """One attempt at a time; a new one replaces a waiting one."""

    def __init__(self, workspace):
        self.workspace = workspace
        self._lock = threading.Lock()
        self.attempt: Attempt | None = None

    def _expire(self) -> None:
        a = self.attempt
        if a and a.status == "waiting" and time.monotonic() - a.started > osr.CODE_LIFETIME_S:
            a.status, a.error = "failed", "signin_timeout"

    def status(self) -> dict:
        with self._lock:
            self._expire()
            a = self.attempt
            if a is None:
                return {"state": "idle", "error": "", "url": "", "byCode": False}
            return {"state": a.status, "error": a.error, "url": a.url if a.status == "waiting" else "",
                    "byCode": a.by_code}

    def start(self, payload: dict, port: int, remote: bool = False) -> dict:
        if str(payload.get("provider") or "") != "openrouter":
            raise ValueError("signin_provider")
        given = payload.get("form") if isinstance(payload.get("form"), dict) else {}
        form = {name: str(given[name]) for name in FORM_FIELDS if isinstance(given.get(name), str)}
        # The key works at openrouter.ai only; another address falls back to its own.
        known = sw.provider_for_base(form.get("baseUrl", ""))
        if not known or known.key != "openrouter":
            form.pop("baseUrl", None)
        lang = str(payload.get("pageLang") or "en")[:8]
        with self._lock:
            if self.attempt and self.attempt.status == "verifying":
                raise ValueError("busy")
            a = Attempt(form, lang)
            a.by_code = remote
            # A browser on another device cannot be sent back to this computer's localhost.
            a.url = (osr.authorize_url(a.verifier) if remote else
                     osr.authorize_url(a.verifier, callback=f"http://localhost:{port}{CALLBACK_PATH}",
                                       state=a.state))
            self.attempt = a
        opened = False if remote else open_browser(a.url)
        return {**self.status(), "opened": opened}

    def claim_code(self, code: str) -> Attempt:
        """The waiting attempt a pasted code finishes."""
        with self._lock:
            self._expire()
            a = self.attempt
            if a is None or a.status != "waiting" or not a.by_code:
                raise ValueError("signin_link_invalid")
            a.status = "verifying"
            return a

    def cancel(self) -> dict:
        with self._lock:
            if self.attempt and self.attempt.status != "verifying":
                self.attempt = None
        return self.status()

    def claim(self, code: str, state: str) -> tuple[Attempt | None, str]:
        """The attempt a callback finishes, or None and the reason it finishes none."""
        with self._lock:
            self._expire()
            a = self.attempt
            if a is None or a.status != "waiting" or a.by_code:
                return None, "signin_link_invalid"
            if not state:
                if code:
                    return None, "signin_link_invalid"
                # A refusal comes back without the state the attempt sent, and so can a
                # request from any page the person visits: the attempt keeps waiting.
                return None, "signin_denied"
            if not secrets.compare_digest(state.encode(), a.state.encode()):
                return None, "signin_link_invalid"
            if not code:
                a.status, a.error = "failed", "signin_denied"
                return a, "signin_denied"
            # Used once: a replayed link finds the attempt no longer waiting.
            a.status = "verifying"
            return a, ""

    def finish(self, a: Attempt, code: str) -> str:
        """Exchange the code and save; '' when the character is set up with the new key."""
        try:
            key = osr.exchange(code, a.verifier)
            payload = {**a.form, "provider": "openrouter", "apiKey": key}
            self.workspace.save(payload)
            error = ""
        except osr.SignInError as caught:
            error = str(caught)
        except ValueError as caught:
            error = str(caught) if str(caught) in SAVE_ERRORS else "generic"
            if error == "key_rejected":
                error = "signin_key_rejected"
        except Exception:
            error = "generic"
        with self._lock:
            a.status, a.error = ("failed", error) if error else ("done", "")
        return error


# The page the browser shows after OpenRouter sends it back: English and Chinese
# here, the page catalog's `signin_page_<key>` for the other languages.
PAGE_TEXT = {
    "title_ok": ("Signed in with OpenRouter", "已通过 OpenRouter 登录"),
    "ok": ("personagent saved the key on this computer and the character is ready. You can close this tab "
           "and return to personagent.",
           "personagent 已将密钥保存在本机，角色已可使用。可以关闭此标签页，返回 personagent。"),
    "title_failed": ("Sign-in was not completed", "登录未完成"),
    "close": ("You can close this tab. personagent shows the same message and lets you try again.",
              "可以关闭此标签页。personagent 中显示相同的说明，并可重新尝试。"),
    "signin_denied": ("Access was not approved on OpenRouter.", "未在 OpenRouter 上批准访问。"),
    "signin_link_invalid": ("This sign-in link is not valid or has already been used. Start the sign-in "
                            "again in personagent.",
                            "此登录链接无效或已使用。请在 personagent 中重新登录。"),
    "signin_timeout": ("The sign-in took longer than ten minutes and has expired.",
                       "登录超过十分钟，已失效。"),
    "signin_code_rejected": ("OpenRouter did not accept the sign-in code. It may have expired.",
                             "OpenRouter 未接受登录代码，代码可能已过期。"),
    "signin_exchange_failed": ("OpenRouter did not return a key.", "OpenRouter 未返回密钥。"),
    "signin_unreachable": ("personagent could not reach OpenRouter to collect the key.",
                           "personagent 无法连接 OpenRouter 以获取密钥。"),
    "verify": ("OpenRouter created a key, but it did not pass the check personagent runs before saving.",
               "OpenRouter 已创建密钥，但未通过 personagent 保存前的验证。"),
}


def _catalog(lang: str) -> dict:
    """The page catalog of one of the other eight languages, {} when there is none."""
    from ..welcome import ASSETS

    name = lang if lang.replace("-", "").isalnum() else ""
    if name in ("", "en", "zh"):
        return {}
    try:
        strings = json.loads((ASSETS / "i18n" / f"{name}.json").read_text(encoding="utf-8")).get("strings")
    except (OSError, ValueError, AttributeError):
        return {}
    return strings if isinstance(strings, dict) else {}


def page(lang: str, error: str) -> str:
    zh = lang == "zh"
    catalog = _catalog(lang)

    def say(key: str) -> str:
        name = key if key in PAGE_TEXT else "verify"
        pair = PAGE_TEXT[name]
        found = catalog.get("signin_page_" + name)
        return html.escape(found if isinstance(found, str) and found else pair[1] if zh else pair[0])

    title = say("title_failed" if error else "title_ok")
    # A link that finished nothing changed nothing in personagent either.
    tail = f"<p>{say('close')}</p>" if error not in ("signin_link_invalid", "signin_denied") else ""
    body = f"<p>{say(error)}</p>{tail}" if error else f"<p>{say('ok')}</p>"
    mark = "signin-mark signin-mark-failed" if error else "signin-mark"
    return ("<!doctype html>\n"
            f'<html lang="{"zh-CN" if zh else lang if catalog else "en"}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{title} - personagent</title>"
            '<link rel="stylesheet" href="/assets/welcome.css">'
            '<link rel="stylesheet" href="/assets/panels/signin.css"></head>'
            f'<body class="signin-page"><main class="signin-result"><span class="{mark}" aria-hidden="true"></span>'
            f"<h1>{title}</h1>{body}</main></body></html>")


def admitted(request: Request) -> bool:
    """A browser navigation on this computer to the address the attempt named,
    and nothing else: a Host header alone is the caller's to choose."""
    from ..pageaccess import is_loopback

    client = request.client.host if request.client else ""
    if getattr(request.state, "remote", False) or not is_loopback(client):
        return False
    server = request.scope.get("server") or ("", 0)
    if request.headers.get("host", "").lower() != f"localhost:{server[1]}":
        return False
    if any(request.headers.get(key) for key in ("x-forwarded-host", "forwarded", "x-forwarded-for")):
        return False
    return True


def mount(app, workspace, body) -> None:
    signin = SignIn(workspace)
    app.state.signin = signin

    @app.get("/api/signin")
    async def signin_status():
        return signin.status()

    @app.post("/api/signin/start")
    async def signin_start(request: Request):
        payload = await body(request)
        port = (request.scope.get("server") or ("", 0))[1]
        remote = bool(getattr(request.state, "remote", False))
        return await asyncio.to_thread(signin.start, payload, port, remote)

    @app.post("/api/signin/code")
    async def signin_code(request: Request):
        payload = await body(request)
        try:
            code = osr.clean_code(payload.get("code"))
        except osr.SignInError as refused:
            raise ValueError(str(refused)) from None
        a = signin.claim_code(code)
        await asyncio.to_thread(signin.finish, a, code)
        return signin.status()

    @app.post("/api/signin/cancel")
    async def signin_cancel(request: Request):
        await body(request)
        return signin.cancel()

    @app.get(CALLBACK_PATH)
    async def signin_callback(request: Request, code: str = "", state: str = ""):
        if not admitted(request):
            return HTMLResponse(page("en", "signin_link_invalid"), status_code=403)
        a, error = signin.claim(code[:1024], state[:256])
        shown = a or signin.attempt
        lang = shown.lang if shown else "en"
        if a is not None and not error:
            error = await asyncio.to_thread(signin.finish, a, code)
        if error not in PAGE_TEXT:
            error = "verify" if error else ""
        return HTMLResponse(page(lang, error), status_code=200 if not error else 400)
