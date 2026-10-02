"""How a model call reads a provider's errors and learns its dialect."""
from __future__ import annotations

from pathlib import Path

import httpx

from persona_agent import promotion
from persona_agent.agent import Agent
from persona_agent.endpoints import adapt_rejected_payload


def check(name: str, cond: bool, detail: str = "") -> None:
    assert cond, name + (f" - {detail}" if detail else "")


def make_agent(tmp: Path, base_url: str) -> Agent:
    a = Agent(api_key="test-key", qq_bot_id="10001", persona_name="Luna",
              memory_file=str(tmp / "memory.json"), persona="test persona",
              eval_enabled=False, eval_file=str(tmp / "eval.jsonl"),
              stickers_dir=str(tmp / "stickers"),
              stickers_file=str(tmp / "stickers.json"), message_debounce_sec=0,
              lang="en", base_url=base_url)
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.example_candidates = promotion.CandidatePool(tmp / "example_candidates.json")
    a.core_memory_file = tmp / "core_memory.json"
    a.connector_handles.path = tmp / "connector_handles.json"
    a.model = a.llm_fallback_model = a.llm_judge_model = "m"
    a.api_max_retries = 0
    return a


def _error(status: int, body: str) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://llm.example/v1/chat/completions")
    response = httpx.Response(status, request=request, text=body)
    return httpx.HTTPStatusError(f"{status}", request=request, response=response)


def test_only_an_account_status_reads_the_body_for_account_words() -> None:
    classify = Agent._classify_api_error
    for status, body in ((503, "insufficient capacity, try later"),
                         (502, "upstream quota service unavailable")):
        got = classify(_error(status, body))
        check(f"{status} {body!r} is an outage, retried", got == "transient", got)
    for body in ("my bank balance is low", "rate limit exceeded in your text"):
        got = classify(_error(400, body))
        check(f"a 400 echoing {body!r} is the request's fault", got == "fatal_request", got)
    for status, body, want in (
            (401, "invalid api key", "fatal_auth"),
            (403, "Insufficient Balance", "fatal_auth"),
            (429, '{"error": {"type": "insufficient_quota"}}', "fatal_auth"),
            (429, "rate limit reached", "rate_limit")):
        got = classify(_error(status, body))
        check(f"{status} {body!r} -> {want}", got == want, got)


def test_a_400_refuses_a_field_only_when_it_names_the_field() -> None:
    for text, model in (("Model does not exist: Qwen3-235B-Thinking", "Qwen3-235B-Thinking"),
                        ("unknown model kimi-k2-thinking", "other"),
                        ("invalid request: messages[1]: I was thinking about it", "m")):
        payload = {"model": model, "thinking": {"type": "disabled"}}
        check(f"{text!r} keeps `thinking`",
              adapt_rejected_payload(payload, text) == "" and "thinking" in payload)
    for text in ("property 'thinking' is unsupported",
                 "Unrecognized request argument supplied: thinking",
                 "[{'type': 'extra_forbidden', 'loc': ('body', 'thinking'), "
                 "'msg': 'Extra inputs are not permitted'}]",
                 'Invalid JSON payload received. Unknown name "thinking": Cannot find field.'):
        payload = {"model": "m", "thinking": {"type": "disabled"}}
        check(f"{text!r} drops `thinking`", adapt_rejected_payload(payload, text) == "thinking")
    payload = {"model": "m", "temperature": 3.0}
    check("a temperature value error keeps the temperature",
          adapt_rejected_payload(payload, "temperature: unknown value, must be in [0, 2]") == ""
          and payload["temperature"] == 3.0, repr(payload))


class _Endpoint:
    """Fake chat endpoint: `answer(payload)` -> (status, body text)."""

    def __init__(self, answer) -> None:
        self.answer, self.sent = answer, []

    def __call__(self, **kw):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        self.sent.append((json["model"], "thinking" in json))
        status, text = self.answer(json)
        request = httpx.Request("POST", url)
        if status == 200:
            return httpx.Response(200, request=request, json={"choices": [
                {"message": {"content": "ok"}, "finish_reason": "stop"}]})
        return httpx.Response(status, request=request, text=text)


async def _gate(agent: Agent, model: str = "m") -> str:
    try:
        return await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                                     model=model, max_tokens=50, enable_search=False,
                                     disable_thinking=True)
    except httpx.HTTPStatusError:
        return "error"


async def test_a_refusal_is_remembered_only_when_the_retry_works(tmp: Path) -> None:
    agent = make_agent(tmp, "https://api.deepseek.com")
    agent.model = agent.llm_fallback_model = "Qwen3-235B-Thinking"
    http = _Endpoint(lambda p: (400, f"Model does not exist: {p['model']}"))
    agent._http = http
    check("a wrong model name fails", await _gate(agent, agent.model) == "error")
    check("...without a retry that drops `thinking`",
          http.sent == [(agent.model, True)], repr(http.sent))
    http.answer = lambda p: (400, "property 'thinking' is unsupported" if "thinking" in p
                             else "model is overloaded, bad request")
    await _gate(agent, agent.model)
    http.answer = lambda p: (200, "")
    http.sent.clear()
    await _gate(agent, agent.model)
    check("a refusal whose retry also failed is not remembered",
          http.sent == [(agent.model, True)], repr(http.sent))


async def test_the_thinking_verdict_is_per_model(tmp: Path) -> None:
    agent = make_agent(tmp, "https://gateway.example/v1")
    agent.llm_fallback_thinking = True
    http = _Endpoint(lambda p: (400, "property 'thinking' is unsupported")
                     if p["model"] == "thinker" and "thinking" in p else (200, ""))
    agent._http = http
    check("the model that refuses it answers", await _gate(agent, "thinker") == "ok")
    http.sent.clear()
    await _gate(agent, "plain")
    await _gate(agent, "thinker")
    check("another model on the same gateway is still sent it",
          http.sent == [("plain", True), ("thinker", False)], repr(http.sent))


async def test_an_unknown_endpoint_is_asked_by_its_first_gate_call(tmp: Path) -> None:
    """No startup probe ran (personagent chat, demo and eval never run one)."""
    for refuses, want in ((False, True), (True, False)):
        agent = make_agent(tmp, "https://proxy.example/v1")
        # A refusal in words of its own, as an unknown server may phrase it.
        http = _Endpoint(lambda p: (422, "bad body") if refuses and "thinking" in p
                         else (200, ""))
        agent._http = http
        check(f"asked and answered (refuses={refuses})", await _gate(agent) == "ok")
        check("...sending `thinking` first",
              http.sent[0] == ("m", True), repr(http.sent))
        http.sent.clear()
        await _gate(agent)
        check(f"the next gate call sends it only if it was taken ({want})",
              http.sent == [("m", want)], repr(http.sent))


def test_a_base_url_is_judged_by_the_resolver_that_uses_it() -> None:
    from persona_agent import preflight
    from persona_agent.endpoints import chat_completions_url

    check("an uppercase version is a version root",
          chat_completions_url("https://llm.example/V1") == "https://llm.example/V1/chat/completions")

    def found(**env):
        return {(f.level, f.key): f.detail for f in preflight.check_config(
            env={"LLM_API_KEY": "sk-x", **env})}

    for base in ("https://api.groq.com/openai/v1", "https://api.groq.com/openai",
                 "https://generativelanguage.googleapis.com/v1beta/openai"):
        check(f"{base} is fine", not found(LLM_BASE_URL=base), repr(found(LLM_BASE_URL=base)))
    gemini = found(LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta")
    check("Gemini's native /v1beta is named, with the address to use",
          "https://generativelanguage.googleapis.com/v1beta/openai"
          in gemini.get(("WARN", "LLM_BASE_URL"), ""), repr(gemini))
    for key, level in (("LLM_BASE_URL", "ERROR"), ("LLM_FALLBACK_BASE_URL", "WARN"),
                       ("EMBEDDING_BASE_URL", "WARN")):
        got = found(**{key: "api.deepseek.com", "LLM_FALLBACK_MODEL": "f",
                       "LLM_FALLBACK_API_KEY": "k", "EMBEDDING_MODEL": "e"})
        check(f"{key} without a scheme is named", "https://api.deepseek.com"
              in got.get((level, key), ""), repr(got))
