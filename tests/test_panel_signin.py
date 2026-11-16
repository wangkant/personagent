"""Sign in with OpenRouter, against a stand-in for openrouter.ai: the page's
attempt, the callback's admission rules, the terminal's code flow, and the
models the saved service lists."""
from __future__ import annotations

import base64
import hashlib
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from persona_agent import openrouter_signin as osr
from persona_agent import setup_wizard as sw
from persona_agent import welcome
from persona_agent.panels import models as model_panel
from persona_agent.panels import signin

HEADERS = {welcome.TOKEN_HEADER: "token"}
PORT = 18911
KEY = "sk-or-v1-standin-0123456789abcdef"


class StandIn:
    """openrouter.ai's two addresses: /auth hands out a code for a challenge,
    /api/v1/auth/keys trades code and verifier for a key, once."""

    def __init__(self):
        self.codes: dict[str, str] = {}
        self.exchange_status = 200
        self.answer: dict | None = None
        self.listing: dict | None = None
        self.listing_status = 200
        self.listing_delay = 0.0
        self.seen: list = []
        stand_in = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status: int, body: bytes, kind="application/json"):
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                url = urlsplit(self.path)
                query = {k: v[0] for k, v in parse_qs(url.query).items()}
                if url.path == "/auth":
                    code = f"code-{len(stand_in.codes)}"
                    stand_in.codes[code] = query["code_challenge"]
                    stand_in.seen.append(("auth", query))
                    self._send(200, json.dumps({"code": code, **query}).encode())
                elif url.path == "/api/v1/models":
                    stand_in.seen.append(("models", self.headers.get("Authorization")))
                    time.sleep(stand_in.listing_delay)
                    self._send(stand_in.listing_status, json.dumps(stand_in.listing or {}).encode())
                else:
                    self._send(404, b"{}")

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                stand_in.seen.append(("keys", body))
                if stand_in.exchange_status != 200:
                    return self._send(stand_in.exchange_status, b'{"error": "nope"}')
                challenge = stand_in.codes.pop(body.get("code"), None)
                verifier = body.get("code_verifier", "")
                expected = base64.urlsafe_b64encode(
                    hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
                if challenge is None or challenge != expected or body.get("code_challenge_method") != "S256":
                    return self._send(403, b'{"error": "Invalid code or code_verifier"}')
                self._send(200, json.dumps({"key": KEY, "user_id": "u1"} if stand_in.answer is None else stand_in.answer).encode())

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def approve(self, url: str) -> dict:
        """What a person approving in the browser makes OpenRouter send back."""
        import httpx
        return httpx.get(self.base + "/auth?" + urlsplit(url).query, trust_env=False).json()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture()
def openrouter(monkeypatch):
    stand_in = StandIn()
    monkeypatch.setattr(osr, "AUTHORIZE_URL", stand_in.base + "/auth")
    monkeypatch.setattr(osr, "KEYS_URL", stand_in.base + "/api/v1/auth/keys")
    yield stand_in
    stand_in.close()


@pytest.fixture()
def page(tmp_path, monkeypatch, openrouter):
    opened: list[str] = []
    monkeypatch.setattr(signin, "open_browser", lambda url: opened.append(url) or True)
    probed: list = []
    monkeypatch.setattr(sw, "probe_key", lambda base, key, model, timeout=30: (
        probed.append((base, key, model)) or sw.Probe(base, 401 if key == "bad-key" else 200)))
    workspace = welcome.Workspace(tmp_path)
    app = welcome.create_app(tmp_path, "token", workspace=workspace)
    texts: list[str] = []
    with TestClient(app, base_url=f"http://127.0.0.1:{PORT}", client=("127.0.0.1", 50000)) as client:
        original = client.request

        def request(*args, **kwargs):
            answer = original(*args, **kwargs)
            texts.append(answer.text)
            return answer
        client.request = request
        yield {"workspace": workspace, "client": client, "opened": opened, "probed": probed,
               "texts": texts, "app": app}
    workspace.close()
    assert not any(KEY in text for text in texts), "a response carried the key"


def _start(client, **form) -> dict:
    answer = client.post("/api/signin/start", headers=HEADERS, json={
        "provider": "openrouter", "pageLang": form.pop("pageLang", "en"),
        "form": {"model": "openrouter/free", "name": "Mira", "character": "warm-listener",
                 "lang": "en", **form}})
    assert answer.status_code == 200, answer.text
    return answer.json()


def _back(client, query: dict, host: str = f"localhost:{PORT}", **headers):
    return client.get(signin.CALLBACK_PATH, params=query, headers={"host": host, **headers})


# ---- the flow itself

def test_the_challenge_is_rfc_7636_s256() -> None:
    # The worked example in RFC 7636, appendix B.
    assert osr.challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == \
        "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    verifier = osr.new_verifier()
    assert 43 <= len(verifier) <= 128
    query = parse_qs(urlsplit(osr.authorize_url(verifier, callback="http://localhost:1/cb", state="s")).query)
    assert query["code_challenge_method"] == ["S256"] and query["callback_url"] == ["http://localhost:1/cb"]
    assert query["code_challenge"] == [osr.challenge(verifier)] and query["state"] == ["s"]
    assert verifier not in osr.authorize_url(verifier)
    assert "callback_url" not in parse_qs(urlsplit(osr.authorize_url(verifier)).query)


def test_signing_in_saves_the_form_with_the_new_key_and_never_shows_it(page, openrouter) -> None:
    client, workspace = page["client"], page["workspace"]
    started = _start(client, name="Juno", pageLang="zh")
    assert started["state"] == "waiting" and started["opened"] is True
    assert page["opened"] == [started["url"]]
    query = parse_qs(urlsplit(started["url"]).query)
    assert query["callback_url"] == [f"http://localhost:{PORT}{signin.CALLBACK_PATH}"]
    attempt = page["app"].state.signin.attempt
    # The verifier stays on the server: the page sees only its challenge.
    assert attempt.verifier not in json.dumps(started)

    back = openrouter.approve(started["url"])
    done = _back(client, {"code": back["code"], "state": back["state"]})
    assert done.status_code == 200 and "已通过 OpenRouter 登录" in done.text
    assert 'href="/assets/welcome.css"' in done.text
    assert client.get("/api/signin", headers=HEADERS).json() == {"state": "done", "error": "", "url": "", "byCode": False}
    assert sw.env_get(workspace.home / ".env", "LLM_API_KEY") == KEY
    assert sw.env_get(workspace.home / ".env", "LLM_BASE_URL") == "https://openrouter.ai/api/v1"
    assert sw.env_get(workspace.home / ".env", "PERSONA_NAME") == "Juno"
    assert page["probed"] == [("https://openrouter.ai/api/v1", KEY, "openrouter/free")]
    exchanged = [body for kind, body in openrouter.seen if kind == "keys"]
    assert exchanged[0]["code_verifier"] == attempt.verifier
    assert client.get("/api/state", headers=HEADERS).json()["configured"] is True
    # The page reads the outcome once, then the attempt is gone.
    assert client.post("/api/signin/cancel", headers=HEADERS, json={}).json()["state"] == "idle"


def test_another_address_in_the_form_falls_back_to_openrouter_s_own(page, openrouter) -> None:
    client, workspace = page["client"], page["workspace"]
    back = openrouter.approve(_start(client, baseUrl="https://llm.example/v1")["url"])
    _back(client, {"code": back["code"], "state": back["state"]})
    assert sw.env_get(workspace.home / ".env", "LLM_BASE_URL") == "https://openrouter.ai/api/v1"


def test_only_openrouter_signs_in_and_only_with_the_token(page) -> None:
    client = page["client"]
    refused = client.post("/api/signin/start", headers=HEADERS, json={"provider": "deepseek"})
    assert refused.status_code == 400 and refused.json() == {"error": "signin_provider"}
    assert client.post("/api/signin/start", json={"provider": "openrouter"}).status_code == 403
    assert client.get("/api/signin").status_code == 403
    assert page["opened"] == []


# ---- each way it fails

def test_a_refusal_tells_the_tab_and_cannot_be_used_to_end_someone_s_attempt(page) -> None:
    client = page["client"]
    started = _start(client, pageLang="zh")
    # OpenRouter returns no state when access is denied, and any page the person
    # visits can send the same request: the tab is told, the attempt keeps waiting.
    denied = _back(client, {})
    assert denied.status_code == 400 and "未在 OpenRouter 上批准访问" in denied.text
    assert "可以关闭此标签页" not in denied.text
    assert client.get("/api/signin", headers=HEADERS).json()["state"] == "waiting"
    # With the attempt's own state and no code, it is this attempt that was refused.
    state = parse_qs(urlsplit(started["url"]).query)["state"][0]
    assert _back(client, {"state": state}).status_code == 400
    assert client.get("/api/signin", headers=HEADERS).json()["error"] == "signin_denied"


@pytest.mark.parametrize("status, error", [(403, "signin_code_rejected"), (400, "signin_exchange_failed"),
                                           (405, "signin_exchange_failed"), (500, "signin_exchange_failed")])
def test_an_exchange_that_fails_says_why(page, openrouter, status, error) -> None:
    client, workspace = page["client"], page["workspace"]
    back = openrouter.approve(_start(client)["url"])
    openrouter.exchange_status = status
    answer = _back(client, {"code": back["code"], "state": back["state"]})
    assert answer.status_code == 400
    assert client.get("/api/signin", headers=HEADERS).json() == {"state": "failed", "error": error, "url": "", "byCode": False}
    assert not (workspace.home / ".env").exists()


@pytest.mark.parametrize("answer", [{}, {"key": ""}, {"key": "two words"}, {"key": 5}, {"key": "${LLM_API_KEY}"}])
def test_an_answer_without_a_usable_key_is_no_key(page, openrouter, answer) -> None:
    client = page["client"]
    back = openrouter.approve(_start(client)["url"])
    openrouter.answer = answer
    _back(client, {"code": back["code"], "state": back["state"]})
    assert client.get("/api/signin", headers=HEADERS).json()["error"] == "signin_exchange_failed"


def test_openrouter_out_of_reach(page, openrouter, monkeypatch) -> None:
    client = page["client"]
    back = openrouter.approve(_start(client)["url"])
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        closed = sock.getsockname()[1]
    monkeypatch.setattr(osr, "KEYS_URL", f"http://127.0.0.1:{closed}/api/v1/auth/keys")
    _back(client, {"code": back["code"], "state": back["state"]})
    assert client.get("/api/signin", headers=HEADERS).json()["error"] == "signin_unreachable"


def test_a_key_that_does_not_verify_is_not_saved(page, openrouter) -> None:
    client, workspace = page["client"], page["workspace"]
    back = openrouter.approve(_start(client)["url"])
    openrouter.answer = {"key": "bad-key"}
    answer = _back(client, {"code": back["code"], "state": back["state"]})
    assert answer.status_code == 400 and "did not pass the check" in answer.text
    assert client.get("/api/signin", headers=HEADERS).json()["error"] == "signin_key_rejected"
    assert not (workspace.home / ".env").exists()


def test_an_attempt_left_waiting_expires(page, openrouter, monkeypatch) -> None:
    client = page["client"]
    back = openrouter.approve(_start(client)["url"])
    monkeypatch.setattr(osr, "CODE_LIFETIME_S", -1)
    assert client.get("/api/signin", headers=HEADERS).json()["error"] == "signin_timeout"
    late = _back(client, {"code": back["code"], "state": back["state"]})
    assert late.status_code == 400 and "not valid" in late.text
    assert not [kind for kind, _ in openrouter.seen if kind == "keys"]


def test_cancel_drops_the_attempt(page, openrouter) -> None:
    client = page["client"]
    back = openrouter.approve(_start(client)["url"])
    assert client.post("/api/signin/cancel", headers=HEADERS, json={}).json()["state"] == "idle"
    assert _back(client, {"code": back["code"], "state": back["state"]}).status_code == 400
    assert not [kind for kind, _ in openrouter.seen if kind == "keys"]


# ---- who the callback admits

@pytest.mark.parametrize("host", [f"127.0.0.1:{PORT}", "localhost:1", "localhost", f"evil.example:{PORT}",
                                  f"localhost:{PORT}.evil.example"])
def test_the_callback_admits_only_localhost_at_the_page_s_port(page, openrouter, host) -> None:
    client = page["client"]
    back = openrouter.approve(_start(client)["url"])
    refused = _back(client, {"code": back["code"], "state": back["state"]}, host=host)
    assert refused.status_code == 403
    assert client.get("/api/signin", headers=HEADERS).json()["state"] == "waiting"
    assert _back(client, {"code": back["code"], "state": back["state"]}).status_code == 200


def test_the_callback_refuses_a_forwarded_request(page, openrouter) -> None:
    client = page["client"]
    back = openrouter.approve(_start(client)["url"])
    for header in ("x-forwarded-for", "x-forwarded-host", "forwarded"):
        refused = _back(client, {"code": back["code"], "state": back["state"]}, **{header: "1.2.3.4"})
        assert refused.status_code == 403, header
    assert client.get("/api/signin", headers=HEADERS).json()["state"] == "waiting"


def test_another_device_cannot_end_the_attempt_with_a_borrowed_host(page, openrouter, tmp_path) -> None:
    client = page["client"]
    _start(client)
    with TestClient(page["app"], base_url=f"http://127.0.0.1:{PORT}", client=("192.168.1.99", 50000)) as other:
        for query in ({}, {"code": "x"}, {"error": "access_denied"}):
            assert _back(other, query).status_code == 403, query
    assert client.get("/api/signin", headers=HEADERS).json()["state"] == "waiting"


def test_a_device_the_page_treats_as_remote_is_refused_even_from_loopback(tmp_path, openrouter,
                                                                          monkeypatch) -> None:
    from persona_agent import pageaccess
    for name in pageaccess.SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(signin, "open_browser", lambda url: True)
    sw.write_env(tmp_path / ".env", {"PAGE_PASSWORD": pageaccess.hash_password("plum-orchard-41-lantern")})
    workspace = welcome.Workspace(tmp_path)
    try:
        app = welcome.create_app(tmp_path, "token", workspace=workspace, gate=pageaccess.Gate(tmp_path))
        with TestClient(app, base_url=f"http://127.0.0.1:{PORT}", client=("127.0.0.1", 50000)) as here:
            _start(here)
            # Through a proxy on this computer: another device, whatever the Host says.
            assert _back(here, {}, **{"x-real-ip": "203.0.113.5", "via": "1.1 proxy",
                                      "x-forwarded-proto": "https", "x-forwarded-for": "203.0.113.5"}
                         ).status_code == 403
            assert here.get("/api/signin", headers=HEADERS).json()["state"] == "waiting"
    finally:
        workspace.close()


def test_the_state_binds_the_callback_to_its_attempt_once(page, openrouter) -> None:
    client = page["client"]
    back = openrouter.approve(_start(client)["url"])
    for wrong in ({"code": back["code"], "state": "guess"}, {"code": back["code"]},
                  {"code": back["code"], "state": back["state"][:-1]}):
        assert _back(client, wrong).status_code == 400
        assert client.get("/api/signin", headers=HEADERS).json()["state"] == "waiting", wrong
    assert not [kind for kind, _ in openrouter.seen if kind == "keys"]
    assert _back(client, {"code": back["code"], "state": back["state"]}).status_code == 200
    replay = _back(client, {"code": back["code"], "state": back["state"]})
    assert replay.status_code == 400 and "already been used" in replay.text
    assert len([kind for kind, _ in openrouter.seen if kind == "keys"]) == 1


def test_a_second_press_replaces_the_first(page, openrouter) -> None:
    client = page["client"]
    first = openrouter.approve(_start(client)["url"])
    second = _start(client)
    assert parse_qs(urlsplit(second["url"]).query)["state"][0] != first["state"]
    assert _back(client, {"code": first["code"], "state": first["state"]}).status_code == 400
    back = openrouter.approve(second["url"])
    assert _back(client, {"code": back["code"], "state": back["state"]}).status_code == 200


def test_the_callback_answers_in_the_page_s_language(page, openrouter, monkeypatch) -> None:
    from persona_agent.panels import signin

    client = page["client"]
    monkeypatch.setattr(signin, "_catalog", lambda lang: {"signin_page_title_ok": "<b>サインイン</b>完了"}
                        if lang == "ja" else {})
    back = openrouter.approve(_start(client, pageLang="ja")["url"])
    done = _back(client, {"code": back["code"], "state": back["state"]})
    # The catalog's sentence, escaped; a sentence it lacks stays English.
    assert "&lt;b&gt;サインイン&lt;/b&gt;完了" in done.text and '<html lang="ja">' in done.text
    assert "You can close this tab" in done.text
    assert "<script" not in done.text


def test_a_language_without_a_catalog_and_a_name_that_is_no_language_get_english() -> None:
    from persona_agent.panels import signin

    assert signin._catalog("../../secrets") == {}
    assert signin._catalog("xx") == {}
    assert "Signed in with OpenRouter" in signin.page("xx", "") and '<html lang="en">' in signin.page("xx", "")


def test_every_page_language_has_the_callback_page_s_sentences() -> None:
    from persona_agent import langs
    from persona_agent.panels import signin

    for code in langs.CODES:
        if code in ("en", "zh"):
            continue
        catalog = signin._catalog(code)
        missing = [key for key in signin.PAGE_TEXT if not catalog.get("signin_page_" + key)]
        assert not missing, (code, missing)


def test_from_another_device_the_code_is_pasted_and_no_browser_opens_here(page, openrouter) -> None:
    client, flow = page["client"], page["app"].state.signin
    started = flow.start({"provider": "openrouter", "form": {"model": "openrouter/free", "name": "Mira",
                                                             "character": "warm-listener", "lang": "en"}},
                         PORT, remote=True)
    # Nothing opens on the server, and OpenRouter is asked to show the code instead of sending it here.
    assert started["byCode"] is True and started["opened"] is False and page["opened"] == []
    assert "callback_url" not in started["url"] and "state=" not in started["url"]
    code = openrouter.approve(started["url"])["code"]
    # The callback finishes no such attempt, even with its code.
    assert _back(client, {"code": code}).status_code == 400
    for bad in ("", "two words", "x" * 2000):
        refused = client.post("/api/signin/code", headers=HEADERS, json={"code": bad})
        assert refused.status_code == 400 and refused.json() == {"error": "signin_code_invalid"}
    done = client.post("/api/signin/code", headers=HEADERS, json={"code": code})
    assert done.status_code == 200 and done.json()["state"] == "done"
    assert sw.env_get(page["workspace"].home / ".env", "LLM_API_KEY") == KEY
    # Used once.
    again = client.post("/api/signin/code", headers=HEADERS, json={"code": code})
    assert again.status_code == 400 and again.json() == {"error": "signin_link_invalid"}


def test_a_code_is_taken_only_by_an_attempt_that_waits_for_one(page, openrouter) -> None:
    client = page["client"]
    assert client.post("/api/signin/code", headers=HEADERS, json={"code": "abc"}).json() == {
        "error": "signin_link_invalid"}
    _start(client)
    # An attempt that waits for the browser to come back takes no pasted code.
    assert client.post("/api/signin/code", headers=HEADERS, json={"code": "abc"}).json() == {
        "error": "signin_link_invalid"}


def test_a_pasted_code_openrouter_refuses_says_so(page) -> None:
    client, flow = page["client"], page["app"].state.signin
    flow.start({"provider": "openrouter", "form": {}}, PORT, remote=True)
    answer = client.post("/api/signin/code", headers=HEADERS, json={"code": "made-up-code"})
    assert answer.status_code == 200 and answer.json()["state"] == "failed"
    assert answer.json()["error"] == "signin_code_rejected"


# ---- the terminal

def test_the_terminal_signs_in_with_the_code_the_page_shows(monkeypatch, capsys, openrouter) -> None:
    sw.set_lang("en")
    answers = []

    def code(prompt=""):
        out = capsys.readouterr().out
        url = next(line.strip() for line in out.splitlines() if openrouter.base in line)
        assert "callback_url" not in url
        answers.append(prompt)
        return openrouter.approve(url)["code"]
    monkeypatch.setattr("builtins.input", code)
    assert sw.sign_in_openrouter() == KEY
    assert "Signed in" in capsys.readouterr().out and len(answers) == 1


def test_the_terminal_falls_back_to_a_pasted_key(monkeypatch, capsys, openrouter) -> None:
    sw.set_lang("en")
    replies = iter(["", "", "n", "sk-pasted-1234567890"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(replies))
    monkeypatch.setattr(sw, "_read_secret", lambda prompt: next(replies))
    provider = sw.provider_named("openrouter")
    current = {"LLM_API_KEY": "", "LLM_BASE_URL": "", "LLM_MODEL": ""}
    assert sw._ask_key(provider, current, False) == "sk-pasted-1234567890"

    # A code OpenRouter refuses says so, then the paste follows.
    replies = iter(["y", "made-up-code", "n", "sk-pasted-1234567890"])
    assert sw._ask_key(provider, current, False) == "sk-pasted-1234567890"
    out = capsys.readouterr().out
    assert "did not accept the code" in out and "Paste a key instead" in out


def test_a_saved_key_or_another_service_is_not_offered_the_sign_in(monkeypatch) -> None:
    sw.set_lang("en")
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt="": asked.append(prompt) or "")
    current = {"LLM_API_KEY": "sk-saved-1234567890", "LLM_BASE_URL": "https://openrouter.ai/api/v1",
               "LLM_MODEL": "openrouter/free"}
    monkeypatch.setattr(sw, "_read_secret", lambda prompt: "")
    assert sw._ask_key(sw.provider_named("openrouter"), current, True) == "sk-saved-1234567890"
    monkeypatch.setattr(sw, "_read_secret", lambda prompt: "sk-ds-1234567890")
    sw._ask_key(sw.provider_named("deepseek"), {**current, "LLM_API_KEY": ""}, False)
    assert not any("Sign in" in prompt for prompt in asked)


def test_no_input_never_signs_in(tmp_path, monkeypatch, openrouter) -> None:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("asked a question"))
    monkeypatch.setenv("MY_KEY", "sk-from-env-123456")
    monkeypatch.setattr(sw, "probe_key", lambda *a, **k: sw.Probe("", 200))
    monkeypatch.setattr(sw.subprocess, "call", lambda *a, **k: 0)
    sw.main(["--no-input", "--provider", "openrouter", "--key-env", "MY_KEY", "--lang", "en"])
    assert not openrouter.seen


# ---- the models a saved service lists

@pytest.fixture()
def listing(tmp_path, monkeypatch, openrouter):
    model_panel._cache.clear()
    base = openrouter.base + "/api/v1"
    monkeypatch.setattr(sw, "PROVIDERS", tuple(
        sw.Provider(p.key, p.name, base if p.key == "openrouter" else p.base_url, p.model, p.key_url, p.note)
        for p in sw.PROVIDERS))
    workspace = welcome.Workspace(tmp_path)
    app = welcome.create_app(tmp_path, "token", workspace=workspace)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client, workspace, base
    workspace.close()
    model_panel._cache.clear()


def _save(workspace, base: str) -> None:
    sw.write_env(workspace.home / ".env", {"LLM_BASE_URL": base, "LLM_API_KEY": KEY, "LLM_MODEL": "openrouter/free"})


def test_the_listing_marks_the_free_models_and_keeps_the_key_on_the_server(listing, openrouter) -> None:
    client, workspace, base = listing
    assert client.get("/api/models", headers=HEADERS).json() == {"baseUrl": "", "models": None}
    _save(workspace, base)
    openrouter.listing = {"data": [
        {"id": "z-ai/glm-4.7", "pricing": {"prompt": "0.0000004", "completion": "0.0000015"}},
        {"id": "meta/llama:free", "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "qwen/qwen3", "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "openai/text-embedding-3", "pricing": {"prompt": "0", "completion": "0"}},
        {"id": ""}, {"name": "no id"}, "junk", {"id": "z-ai/glm-4.7"}]}
    answer = client.get("/api/models", headers=HEADERS)
    assert answer.json() == {"baseUrl": base, "models": [
        {"id": "meta/llama:free", "free": True}, {"id": "openrouter/free", "free": True},
        {"id": "qwen/qwen3", "free": True}, {"id": "z-ai/glm-4.7", "free": False}]}
    assert KEY not in answer.text
    assert ("models", f"Bearer {KEY}") in openrouter.seen
    # Read once, then kept for a while.
    client.get("/api/models", headers=HEADERS)
    assert len([kind for kind, _ in openrouter.seen if kind == "models"]) == 1
    assert client.get("/api/models").status_code == 403


def test_a_service_without_a_listing_leaves_the_field_as_it_is(listing, openrouter, monkeypatch) -> None:
    client, workspace, _base = listing
    sw.write_env(workspace.home / ".env", {"LLM_BASE_URL": openrouter.base + "/other/v1", "LLM_API_KEY": KEY,
                                           "LLM_MODEL": "m"})
    assert client.get("/api/models", headers=HEADERS).json()["models"] is None
    model_panel._cache.clear()
    _save(workspace, openrouter.base + "/api/v1")
    openrouter.listing = {"object": "list", "data": "none"}
    assert client.get("/api/models", headers=HEADERS).json()["models"] is None


def test_a_slow_or_huge_listing_is_given_up(listing, openrouter, monkeypatch) -> None:
    client, workspace, base = listing
    _save(workspace, base)
    monkeypatch.setattr(model_panel, "TIMEOUT_S", 0.3)
    openrouter.listing = {"data": [{"id": "a"}]}
    openrouter.listing_delay = 1.0
    started = time.monotonic()
    assert client.get("/api/models", headers=HEADERS).json()["models"] is None
    assert time.monotonic() - started < 3
    model_panel._cache.clear()
    openrouter.listing_delay = 0
    openrouter.listing = {"data": [{"id": f"vendor/model-{i}", "description": "x" * 400} for i in range(3000)]}
    monkeypatch.setattr(model_panel, "MAX_BYTES", 100_000)
    assert client.get("/api/models", headers=HEADERS).json()["models"] is None
    model_panel._cache.clear()
    monkeypatch.setattr(model_panel, "MAX_BYTES", 16 * 1024 * 1024)
    monkeypatch.setattr(model_panel, "MAX_MODELS", 1000)
    models = client.get("/api/models", headers=HEADERS).json()["models"]
    # Hundreds of models arrive whole, up to the cap.
    assert len(models) == 1001 and models[0] == {"id": "openrouter/free", "free": True}


def test_the_page_s_sentences_and_routes() -> None:
    for name in ("signin", "models"):
        assert name in welcome.PANELS
    script = (welcome.ASSETS / "panels" / "signin.js").read_text(encoding="utf-8")
    # The key never passes through the page's script.
    assert "apiKey" not in script and "LLM_API_KEY" not in script
    assert "openrouter.ai/keys" in script and "need no credit" in script
