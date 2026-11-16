"""The detect panel: a local model server that is running, a key in the
environment, and a save that takes its key from there."""
from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from persona_agent import home as homes
from persona_agent import setup_wizard as sw
from persona_agent import welcome
from persona_agent.panels import detect

HEADERS = {welcome.TOKEN_HEADER: "token"}


@pytest.fixture()
def page(tmp_path, monkeypatch):
    for variable in detect.ENV_KEYS:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    workspace = welcome.Workspace(tmp_path)
    app = welcome.create_app(tmp_path, "token", workspace=workspace)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield workspace, client
    workspace.close()


class _Models(BaseHTTPRequestHandler):
    answer: dict = {}

    def log_message(self, *args):
        pass

    def do_GET(self):
        data = json.dumps(self.answer).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture()
def local_server():
    def serve(answer: dict) -> str:
        handler = type("Handler", (_Models,), {"answer": answer})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    servers: list = []
    yield serve
    for server in servers:
        server.shutdown()
        server.server_close()


def _closed_port() -> str:
    import socket
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return f"http://127.0.0.1:{sock.getsockname()[1]}"


def test_nothing_running_and_no_key_offers_nothing(page, monkeypatch) -> None:
    _workspace, client = page
    gone = _closed_port()
    monkeypatch.setattr(detect, "LOCAL", (
        ("ollama", "Ollama", "ollama", "http://localhost:11434/v1", gone + "/api/tags"),))
    answer = client.get("/api/detect", headers=HEADERS)
    assert answer.status_code == 200
    assert answer.json() == {"local": [], "keys": []}


def test_a_running_ollama_is_offered_with_the_models_that_can_chat(page, monkeypatch, local_server) -> None:
    _workspace, client = page
    ollama = local_server({"models": [{"name": "nomic-embed-text:latest"}, {"name": "qwen3:latest"},
                                      {"name": "llama3.2"}, {"name": ""}, {"size": 3}]})
    studio = local_server({"data": [{"id": "text-embedding-nomic"}]})
    monkeypatch.setattr(detect, "LOCAL", (
        ("ollama", "Ollama", "ollama", "http://localhost:11434/v1", ollama + "/api/tags"),
        ("lmstudio", "LM Studio", "other", "http://localhost:1234/v1", studio + "/v1/models")))
    found = client.get("/api/detect", headers=HEADERS).json()
    # LM Studio is up with nothing that chats: no shortcut there.
    assert found["local"] == [{"id": "ollama", "name": "Ollama", "provider": "ollama",
                               "baseUrl": "http://localhost:11434/v1",
                               "models": ["qwen3:latest", "llama3.2"]}]


def test_the_openai_shape_and_an_answer_that_is_not_a_listing(local_server, monkeypatch) -> None:
    studio = local_server({"data": [{"id": "qwen3-8b"}, {"id": "embed-small"}]})
    odd = local_server({"models": "none"})
    monkeypatch.setattr(detect, "LOCAL", (
        ("lmstudio", "LM Studio", "other", "http://localhost:1234/v1", studio + "/v1/models"),
        ("ollama", "Ollama", "ollama", "http://localhost:11434/v1", odd + "/api/tags")))
    found = asyncio.run(detect.found())
    assert [(row["id"], row["models"]) for row in found["local"]] == [("lmstudio", ["qwen3-8b"])]


def test_the_page_selects_a_provider_the_catalog_has() -> None:
    for _id, _name, provider, base, _listing in detect.LOCAL:
        assert provider in sw.PROVIDER_KEYS
        assert base.endswith("/v1")
    assert set(detect.ENV_KEYS.values()) <= set(sw.PROVIDER_KEYS) - {"ollama", "other"}


def test_a_key_in_the_environment_is_named_and_never_shown(page, monkeypatch) -> None:
    _workspace, client = page
    monkeypatch.setattr(detect, "LOCAL", ())
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-the-shell")
    monkeypatch.setenv("MOONSHOT_API_KEY", "   ")
    monkeypatch.setenv("ARK_API_KEY", "two words")
    answer = client.get("/api/detect", headers=HEADERS)
    assert answer.json()["keys"] == [{"variable": "DEEPSEEK_API_KEY", "provider": "deepseek"}]
    assert "sk-from-the-shell" not in answer.text


def test_a_key_this_home_s_own_env_file_set_is_not_a_find(page, monkeypatch) -> None:
    _workspace, client = page
    monkeypatch.setattr(detect, "LOCAL", ())
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-from-env-file")
    monkeypatch.setattr(homes, "FROM_ENV_FILE", {"OPENROUTER_API_KEY"})
    assert client.get("/api/detect", headers=HEADERS).json()["keys"] == []


def test_an_openai_key_for_another_address_is_left_alone(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proxy")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://llm.example/v1")
    assert detect.env_key("OPENAI_API_KEY") == ""
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    assert detect.env_key("OPENAI_API_KEY") == "sk-proxy"
    assert detect.env_key("PATH") == ""
    assert detect.env_key("LLM_API_KEY") == ""


def test_a_save_takes_the_key_from_the_variable_the_page_names(page, monkeypatch) -> None:
    workspace, client = page
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-the-shell")
    probed = []

    def probe(base, key, model, timeout=30):
        probed.append((base, key, model))
        return sw.Probe(base, 200)

    monkeypatch.setattr(sw, "probe_key", probe)
    saved = client.post("/api/config", headers=HEADERS, json={
        "provider": "deepseek", "apiKey": "", "apiKeyFrom": "DEEPSEEK_API_KEY", "lang": "en"})
    assert saved.status_code == 200, saved.text
    assert probed and probed[0][1] == "sk-from-the-shell"
    assert sw.env_get(workspace.home / ".env", "LLM_API_KEY") == "sk-from-the-shell"
    assert "sk-from-the-shell" not in saved.text


def test_a_variable_of_another_service_or_another_name_gives_no_key(page, monkeypatch) -> None:
    _workspace, client = page
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-the-shell")
    monkeypatch.setenv("HOME_SECRET", "not-a-model-key")
    monkeypatch.setattr(sw, "probe_key", lambda *a, **k: sw.Probe("", 200))
    for provider, variable in (("openrouter", "DEEPSEEK_API_KEY"), ("deepseek", "HOME_SECRET"),
                               ("deepseek", "MOONSHOT_API_KEY")):
        refused = client.post("/api/config", headers=HEADERS, json={
            "provider": provider, "apiKey": "", "apiKeyFrom": variable, "lang": "en"})
        assert refused.status_code == 400, (provider, variable)
        assert refused.json() == {"error": "key_required"}


def test_the_panel_s_sentences_exist_in_english_and_chinese() -> None:
    script = (welcome.ASSETS / "panels" / "detect.js").read_text(encoding="utf-8")
    english, chinese = script.split("  zh: {", 1)
    keys = [line.split(":", 1)[0].strip() for line in english.splitlines() if line.strip().startswith("detect_")]
    assert len(keys) >= 8
    for key in keys:
        assert f"    {key}:" in chinese, key
