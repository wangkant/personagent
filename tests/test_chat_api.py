"""The OpenAI-compatible API: requests, the doors, both answer shapes, the switch."""
from __future__ import annotations

import base64
import json

import httpx
import pytest

from persona_agent import chat_api, server
from persona_agent.chat_api import ApiError

PNG = base64.b64encode(base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")).decode()
KEY = "sk-pa-test-key-0123456789abcdef"


def body(content="hello", **extra) -> bytes:
    return json.dumps({"model": "anything", "messages": [
        {"role": "system", "content": "ignored"},
        {"role": "assistant", "content": "earlier"},
        {"role": "user", "content": content}], **extra}).encode()


# --- the request ------------------------------------------------------------

def test_only_the_last_user_message_is_read_as_a_string_or_parts() -> None:
    raw = json.dumps({"messages": [{"role": "user", "content": "first"},
                                   {"role": "assistant", "content": "x"},
                                   {"role": "user", "content": "second"}]}).encode()
    assert chat_api.parse_request(raw)["text"] == "second"
    asked = chat_api.parse_request(body([
        {"type": "text", "text": "look"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{PNG}"}},
        {"type": "image_url", "image_url": "https://example.org/cat.png"}]))
    assert asked["text"] == "look"
    assert asked["images"] == [{"type": "image", "b64": PNG},
                               {"type": "image", "url": "https://example.org/cat.png"}]
    assert asked["conversation"] == "default" and asked["stream"] is False


@pytest.mark.parametrize("raw, code", [
    (b"not json", "invalid_json"),
    (b"[]", "invalid_json"),
    (json.dumps({"messages": []}).encode(), "invalid_messages"),
    (json.dumps({"messages": [{"role": "system", "content": "x"}]}).encode(), "no_user_message"),
    (body("   "), "empty_message"),
    (body("x" * 8001), "message_too_long"),
    (body([{"type": "input_audio", "input_audio": {}}]), "unsupported_content"),
    (body([{"type": "image_url", "image_url": {"url": "file:///etc/passwd"}}]), "invalid_image"),
    (body([{"type": "image_url", "image_url": {"url": "base64://AAAA"}}]), "invalid_image"),
    (body([{"type": "image_url", "image_url": {"url": "data:text/plain;base64,AAAA"}}]), "invalid_image"),
    (body([{"type": "image_url", "image_url": {"url": "data:image/png;base64,***"}}]), "invalid_image"),
    (body("hi", user="a\nb"), "invalid_user"),
])
def test_a_malformed_request_is_refused_with_its_code(raw, code) -> None:
    with pytest.raises(ApiError) as refused:
        chat_api.parse_request(raw)
    assert refused.value.status == 400 and refused.value.code == code


def test_an_image_over_the_vision_limit_is_refused(monkeypatch) -> None:
    from persona_agent import ingestion
    monkeypatch.setattr(ingestion, "VISION_MAX_IMAGE_BYTES", 10)
    with pytest.raises(ApiError) as refused:
        chat_api.parse_request(body([{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{PNG}"}}]))
    assert refused.value.code == "image_too_large"


def test_the_conversation_is_the_user_field_then_the_header_then_one_default() -> None:
    assert chat_api.parse_request(body(user="alice"), "bob")["conversation"] == "alice"
    assert chat_api.parse_request(body(), "bob")["conversation"] == "bob"
    assert chat_api.parse_request(body())["conversation"] == "default"
    event = chat_api.build_event(chat_api.parse_request(body(user="alice")))
    assert event["platform"] == "api" and event["conversation_type"] == "dm"
    assert event["sender_id"] == event["conversation_id"] == "alice"
    assert event["prefiltered"] is True and event["capabilities"] == ["text_only"]
    assert event["segments"] == [{"type": "text", "text": "hello"}]


# --- the service ------------------------------------------------------------

class FakeAgent:
    enabled = True

    def __init__(self, result=None):
        self.events = []
        self.result = result if result is not None else {
            "handled": True, "owned": True,
            "replies": [{"type": "text", "text": "hi"}, {"type": "text", "text": "how are you"}]}

    async def handle_event(self, event):
        self.events.append(event)
        return self.result


@pytest.fixture
def api(monkeypatch):
    agent = FakeAgent()
    monkeypatch.setattr(server, "agent", agent)
    monkeypatch.setattr(server, "CHAT_API_ENABLED", True)
    monkeypatch.setattr(server, "CHAT_API_KEY", "")
    monkeypatch.setattr(server, "_connector_admission", server.AdmissionLimiter(4))
    return agent


async def call(path, *, method="POST", client_host="127.0.0.1", **kw):
    transport = httpx.ASGITransport(app=server.app, client=(client_host, 1234))
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        return await client.request(method, path, **kw)


def error_code(response):
    error = response.json()["error"]
    assert set(error) >= {"message", "type", "code"}
    return error["code"]


async def test_a_completion_joins_the_messages_and_has_the_openai_shape(api) -> None:
    r = await call("/v1/chat/completions", content=body(), headers={"content-type": "application/json"})
    assert r.status_code == 200, r.text
    answer = r.json()
    assert answer["object"] == "chat.completion" and answer["model"] == "personagent"
    assert answer["id"].startswith("chatcmpl-") and isinstance(answer["created"], int)
    choice = answer["choices"][0]
    assert choice["message"] == {"role": "assistant", "content": "hi\nhow are you"}
    assert choice["finish_reason"] == "stop"
    assert answer["usage"] == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    assert api.events[0]["text"] == "hello" and api.events[0]["sender_id"] == "default"


async def test_an_empty_answer_is_a_completion_with_empty_content(api) -> None:
    api.result = {"handled": False, "owned": True, "replies": []}
    r = await call("/v1/chat/completions", content=body())
    assert r.status_code == 200 and r.json()["choices"][0]["message"]["content"] == ""


async def test_models_lists_the_one_model(api) -> None:
    r = await call("/v1/models", method="GET")
    assert r.status_code == 200
    assert [m["id"] for m in r.json()["data"]] == ["personagent"]
    assert r.json()["object"] == "list"


def sse(text):
    events = [block for block in text.split("\n\n") if block.strip()]
    data = [e[len("data: "):] for e in events if e.startswith("data: ")]
    assert data[-1] == "[DONE]", data
    return [json.loads(d) for d in data[:-1]], events


async def test_a_stream_sends_the_role_one_delta_per_message_the_finish_and_done(api) -> None:
    r = await call("/v1/chat/completions", content=body(stream=True))
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    chunks, _ = sse(r.text)
    assert all(c["object"] == "chat.completion.chunk" for c in chunks)
    assert len({c["id"] for c in chunks}) == 1
    deltas = [c["choices"][0]["delta"] for c in chunks]
    assert deltas[0] == {"role": "assistant", "content": ""}
    assert deltas[1:3] == [{"content": "hi"}, {"content": "\nhow are you"}]
    assert deltas[3] == {} and chunks[3]["choices"][0]["finish_reason"] == "stop"
    assert len(chunks) == 4 and "usage" not in chunks[0]
    assert server._connector_admission.inflight == 0


async def test_a_stream_reports_the_usage_when_asked_and_keeps_alive(api, monkeypatch) -> None:
    import asyncio
    monkeypatch.setattr(chat_api, "KEEPALIVE_S", 0.01)
    slow = api.handle_event

    async def later(event):
        await asyncio.sleep(0.05)
        return await slow(event)
    monkeypatch.setattr(api, "handle_event", later)
    r = await call("/v1/chat/completions",
                   content=body(stream=True, stream_options={"include_usage": True}))
    chunks, events = sse(r.text)
    assert any(e.startswith(": keep-alive") for e in events)
    assert all(c["usage"] is None for c in chunks[:-1])
    assert chunks[-1]["choices"] == [] and chunks[-1]["usage"]["total_tokens"] == 0


async def test_a_failure_after_the_stream_began_is_an_error_event(api) -> None:
    api.result = {"owned": True, "replies": [{"type": "text", "text": "sorry", "reason": "excuse"}]}
    r = await call("/v1/chat/completions", content=body(stream=True))
    chunks, _ = sse(r.text)
    assert chunks[0]["choices"][0]["delta"]["role"] == "assistant"
    assert chunks[-1]["error"]["code"] == "model_failed"


@pytest.mark.parametrize("result, status, code", [
    ({"owned": True, "replies": [{"type": "text", "text": "x", "reason": "excuse"}]}, 502, "model_failed"),
    ({"owned": False, "handled": False, "replies": []}, 403, "not_admitted"),
])
async def test_a_failed_turn_is_an_openai_error(api, result, status, code) -> None:
    api.result = result
    r = await call("/v1/chat/completions", content=body())
    assert r.status_code == status and error_code(r) == code


async def test_the_character_off_is_503(api, monkeypatch) -> None:
    api.enabled = False
    r = await call("/v1/chat/completions", content=body())
    assert r.status_code == 503 and error_code(r) == "character_off"
    monkeypatch.setattr(server, "agent", None)
    r = await call("/v1/chat/completions", content=body())
    assert r.status_code == 503 and error_code(r) == "character_off"


async def test_at_capacity_it_answers_429_with_retry_after(api, monkeypatch) -> None:
    full = server.AdmissionLimiter(1)
    full.try_acquire()
    monkeypatch.setattr(server, "_connector_admission", full)
    r = await call("/v1/chat/completions", content=body())
    assert r.status_code == 429 and error_code(r) == "capacity_exceeded"
    assert r.headers["retry-after"] == "3" and api.events == []


async def test_switched_off_both_routes_answer_404(api, monkeypatch) -> None:
    monkeypatch.setattr(server, "CHAT_API_ENABLED", False)
    for method, path in (("POST", "/v1/chat/completions"), ("GET", "/v1/models")):
        r = await call(path, method=method, content=body() if method == "POST" else None)
        assert r.status_code == 404 and error_code(r) == "api_disabled"
    assert api.events == []


# --- the doors --------------------------------------------------------------

async def test_without_a_key_only_this_computer_may_call(api) -> None:
    assert (await call("/v1/chat/completions", content=body())).status_code == 200
    r = await call("/v1/chat/completions", content=body(), client_host="203.0.113.5")
    assert r.status_code == 401 and error_code(r) == "key_required"
    for header in ({"origin": "http://evil.example"}, {"x-forwarded-for": "203.0.113.5"}):
        r = await call("/v1/chat/completions", content=body(), headers=header)
        assert r.status_code == 401 and error_code(r) == "key_required", header
    assert len(api.events) == 1


async def test_with_a_key_every_caller_needs_it_and_may_come_from_anywhere(api, monkeypatch) -> None:
    monkeypatch.setattr(server, "CHAT_API_KEY", KEY)
    r = await call("/v1/chat/completions", content=body())
    assert r.status_code == 401 and error_code(r) == "missing_api_key"
    r = await call("/v1/chat/completions", content=body(), headers={"authorization": "Bearer wrong"})
    assert r.status_code == 401 and error_code(r) == "invalid_api_key"
    assert KEY not in r.text
    good = {"authorization": f"Bearer {KEY}", "origin": "https://app.example"}
    r = await call("/v1/chat/completions", content=body(), headers=good, client_host="203.0.113.5")
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "*"
    r = await call("/v1/models", method="OPTIONS", headers={"origin": "https://app.example"})
    assert r.status_code == 204 and "Authorization" in r.headers["access-control-allow-headers"]


async def test_without_a_key_a_browser_preflight_is_not_answered(api) -> None:
    r = await call("/v1/chat/completions", method="OPTIONS", headers={"origin": "https://app.example"})
    assert r.status_code == 404 and "access-control-allow-origin" not in r.headers


def test_a_network_bind_with_the_api_on_needs_its_key() -> None:
    with pytest.raises(ValueError, match="CHAT_API_KEY"):
        server._validate_exposure_config("0.0.0.0", "", "token", True, "")
    server._validate_exposure_config("0.0.0.0", "", "token", True, KEY)
    server._validate_exposure_config("0.0.0.0", "", "token", False, "")
    server._validate_exposure_config("127.0.0.1", "", "", True, "")


# --- a text-only conversation -----------------------------------------------

def test_a_text_only_turn_gets_no_sticker_guide_and_sends_no_sticker() -> None:
    import asyncio
    from pathlib import Path
    from types import SimpleNamespace

    from persona_agent.connector import ConnectorSink, current_sink, text_only_turn
    from persona_agent.prompt import PromptBuilder
    from persona_agent.transport import Transport

    sink = ConnectorSink(platform="api", text_only=True)
    token = current_sink.set(sink)
    try:
        assert text_only_turn()
        guide = PromptBuilder._sticker_guide_for_prompt(None, dm=True)
        assert "text only" in guide and "Do NOT emit" in guide
        picked = []
        fake = SimpleNamespace(stickers=SimpleNamespace(
            pick_by_tag=lambda *a, **k: picked.append(a) or Path("x.png"), dir=Path(".")),
            _sent_mids={}, _most_used_sticker=lambda used: Path("y.png"))
        sent = []

        async def send(message):
            sent.append(message)
            return True
        result = asyncio.run(Transport._deliver_segments(
            fake, [("text", "hello"), ("sticker", "smile")], send, target_key="k"))
        assert sent == ["hello"] and picked == [] and result.success
        only_sticker = asyncio.run(Transport._deliver_segments(
            fake, [("sticker", "smile")], send, target_key="k"))
        assert sent == ["hello"] and not only_sticker.success
    finally:
        current_sink.reset(token)
    assert not text_only_turn()


# --- the terminal -----------------------------------------------------------

def test_connect_api_turns_it_on_prints_three_values_and_replaces_the_key(tmp_path, capsys) -> None:
    from persona_agent import setup_wizard as sw

    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text("SERVER_PORT=18555\nLLM_API_KEY=x\n", encoding="utf-8")
    sw.set_lang("en")
    assert chat_api.connect(home, remove=False, replace_key=False) == 0
    first = chat_api.settings(home)
    out = capsys.readouterr().out
    assert first["enabled"] and first["key"].startswith("sk-pa-") and len(first["key"]) > 40
    for value in ("http://127.0.0.1:18555/v1", first["key"], "personagent"):
        assert value in out
    chat_api.connect(home, remove=False, replace_key=False)
    assert chat_api.settings(home)["key"] == first["key"], "a second run keeps the key"
    chat_api.connect(home, remove=False, replace_key=True)
    assert chat_api.settings(home)["key"] != first["key"]
    assert "no longer works" in capsys.readouterr().out
    chat_api.connect(home, remove=True, replace_key=False)
    assert not chat_api.settings(home)["enabled"] and chat_api.settings(home)["key"]
    with pytest.raises(SystemExit):
        chat_api.connect(home, remove=True, replace_key=True)


def test_the_connect_command_routes_api_and_refuses_options_of_other_targets(tmp_path, monkeypatch, capsys) -> None:
    from persona_agent import setup_wizard as sw

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("AGENT_HOME", str(home))
    assert sw.connect_main(["api", "--lang", "en"]) == 0
    assert chat_api.settings(home)["enabled"]
    with pytest.raises(SystemExit, match="only to api"):
        sw.connect_main(["claude-code", "--new-key"])
    with pytest.raises(SystemExit, match="used only with api"):
        sw.connect_main(["telegram", "--new-key"])
    with pytest.raises(SystemExit, match="api takes only"):
        sw.connect_main(["api", "--react"])
    capsys.readouterr()
    assert sw.connect_main(["--lang", "en"]) == 0
    assert "connect api" in capsys.readouterr().out
    assert "api" in sw.connect_parser("personagent connect").format_help()
