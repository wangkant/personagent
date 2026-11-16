"""The chatapi panel: the switch, the key, and the test message through the service."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
import httpx
import pytest

from persona_agent import chat_api, welcome
from persona_agent.panels import chatapi

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
MODEL_KEY = "sk-model-secret-123456789"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text(f"LLM_API_KEY={MODEL_KEY}\nPERSONA_NAME=Nova\nSERVER_PORT=18560\n",
                               encoding="utf-8")
    value = welcome.Workspace(home)
    value.started, value.up = [], False
    monkeypatch.setattr(value.services, "start_agent", lambda: value.started.append("agent"))
    monkeypatch.setattr(value.services, "running", lambda name: value.up)
    monkeypatch.setattr(value, "_restart_agent", lambda: value.started.append("restart"))
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


def post(client, path, payload=None):
    return client.post(f"/api/chatapi/{path}", headers=HEADERS, json=payload or {})


def test_the_overview_needs_the_token_and_never_carries_a_key(client, workspace):
    assert client.get("/api/chatapi").status_code == 403
    body = client.get("/api/chatapi", headers=HEADERS).json()
    assert body == {"enabled": False, "hasKey": False, "address": "http://127.0.0.1:18560/v1",
                    "model": "personagent", "running": False, "name": "Nova"}
    post(client, "switch", {"on": True})
    response = client.get("/api/chatapi", headers=HEADERS)
    assert response.json()["hasKey"] is True
    assert chat_api.settings(workspace.home)["key"] not in response.text
    assert MODEL_KEY not in response.text


def test_switching_on_creates_a_key_and_restarts_only_a_running_character(client, workspace):
    response = post(client, "switch", {"on": True})
    assert response.status_code == 200 and response.json()["restarted"] is False
    first = chat_api.settings(workspace.home)
    assert first["enabled"] and first["key"].startswith("sk-pa-") and workspace.started == []
    workspace.up = True
    response = post(client, "switch", {"on": False})
    assert response.json()["restarted"] is True and workspace.started == ["restart"]
    assert chat_api.settings(workspace.home) == {**first, "enabled": False}
    post(client, "switch", {"on": True})
    assert chat_api.settings(workspace.home)["key"] == first["key"], "turning on again keeps the key"
    assert post(client, "switch", {"on": "yes"}).json() == {"error": "chatapi_bad_request"}


def test_reveal_and_a_new_key(client, workspace):
    assert post(client, "reveal").json() == {"error": "chatapi_no_key"}
    post(client, "switch", {"on": True})
    old = post(client, "reveal").json()["key"]
    assert old == chat_api.settings(workspace.home)["key"]
    workspace.up = True
    response = post(client, "key")
    assert response.status_code == 200 and old not in response.text
    assert post(client, "reveal").json()["key"] != old
    assert workspace.started == ["restart"]


def answering(monkeypatch, status=200, payload=None, seen=None, fail=None):
    def handler(request):
        if seen is not None:
            seen.append(request)
        if fail is not None:
            raise fail
        return httpx.Response(status, json=payload if payload is not None else {
            "choices": [{"message": {"role": "assistant", "content": "hi there"}}]})
    monkeypatch.setattr(chatapi, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def test_the_test_message_goes_through_the_service_with_the_key(client, workspace, monkeypatch):
    assert post(client, "test", {"text": "Hello"}).json() == {"error": "chatapi_off"}
    post(client, "switch", {"on": True})
    seen = []
    answering(monkeypatch, seen=seen)
    response = post(client, "test", {"text": "Hello"})
    assert response.json() == {"reply": "hi there"} and workspace.started == ["agent"]
    sent = seen[0]
    assert str(sent.url) == "http://127.0.0.1:18560/v1/chat/completions"
    assert sent.headers["authorization"] == "Bearer " + chat_api.settings(workspace.home)["key"]
    asked = json.loads(sent.content)
    assert asked["user"] == chatapi.TEST_CONVERSATION and asked["messages"][-1]["content"] == "Hello"
    for bad in ({"text": ""}, {"text": "x" * 501}, {"text": 3}):
        assert post(client, "test", bad).json() == {"error": "chatapi_bad_request"}


@pytest.mark.parametrize("status, code", [(404, "chatapi_stale"), (401, "chatapi_key_rejected"),
                                          (503, "chatapi_character_off"), (429, "chatapi_busy"),
                                          (502, "chatapi_model_failed"), (403, "chatapi_not_admitted"),
                                          (500, "chatapi_failed")])
def test_each_refusal_of_the_service_has_its_reason(client, monkeypatch, status, code):
    post(client, "switch", {"on": True})
    answering(monkeypatch, status=status, payload={"error": {"code": "x"}})
    assert post(client, "test", {"text": "Hello"}).json() == {"error": code}


def test_a_service_that_cannot_be_reached_or_started_is_named(client, workspace, monkeypatch):
    post(client, "switch", {"on": True})
    answering(monkeypatch, fail=httpx.ConnectError("refused"))
    assert post(client, "test", {"text": "Hello"}).json() == {"error": "chatapi_unreachable"}
    answering(monkeypatch, fail=httpx.ReadTimeout("slow"))
    assert post(client, "test", {"text": "Hello"}).json() == {"error": "chatapi_timeout"}

    def broken():
        raise RuntimeError("agent could not start")
    monkeypatch.setattr(workspace.services, "start_agent", broken)
    assert post(client, "test", {"text": "Hello"}).json() == {"error": "chatapi_not_started"}
    sw_env = workspace.home / ".env"
    sw_env.write_text(sw_env.read_text(encoding="utf-8").replace(f"LLM_API_KEY={MODEL_KEY}", "LLM_API_KEY="),
                      encoding="utf-8")
    assert post(client, "test", {"text": "Hello"}).json() == {"error": "key_required"}
