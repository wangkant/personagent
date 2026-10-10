"""How a model call reads a provider's errors and learns its dialect: retries,
JSON mode, fallback models and their cooldowns."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

import httpx

from persona_agent.agent import Agent
from persona_agent.endpoints import adapt_rejected_payload
from persona_agent.textproc import TextProcessing

from helpers import check, isolated_agent


def make_agent(tmp: Path, base_url: str) -> Agent:
    a = isolated_agent(tmp, persona_name="Luna", base_url=base_url)
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


# ---------------------------------------------------------------------------
# Routing, retries, JSON mode, fallback models and cooldowns
# ---------------------------------------------------------------------------

def test_pick_group_model_mode_exempt() -> None:
    """Frequency-driven downgrade must exempt called/admin (no 'dumber when most
    @-ed'); error-driven fallback (_fallback_until, keyed by model name) must
    apply to ALL modes."""
    from collections import deque
    with tempfile.TemporaryDirectory() as d:
        a = isolated_agent(Path(d))
        a.model, a.llm_fallback_model = "pro", "flash"
        a.llm_rate_window_s = 60
        a.llm_rate_threshold = 5
        a.llm_fallback_duration_s = 300
        a.model_calls = deque([time.time()] * 6)  # over threshold
        check("route: hot window called stays pro", a._pick_group_model("called") == "pro")
        check("route: hot window admin stays pro", a._pick_group_model("owner") == "pro")
        check("route: hot window followup downgrades", a._pick_group_model("followup") == "flash")
        check("route: after trip judge downgraded", a._pick_group_model("judge") == "flash")
        check("route: after trip called still pro", a._pick_group_model("called") == "pro")
        a._freq_fallback_until = 0.0
        a._fallback_until = {"pro": time.time() + 100}  # real 429 on the primary
        check("route: api-429 downgrades called too", a._pick_group_model("called") == "flash")
        check("route: api-429 downgrades admin too", a._pick_group_model("owner") == "flash")


async def test_cache_hits_are_logged_in_either_spelling(tmp: Path, caplog) -> None:
    """The cache line read only DeepSeek's usage keys, so it never fired on
    an OpenAI-style provider (prompt_tokens_details.cached_tokens), and a
    zero hit rate was indistinguishable from no telemetry at all."""
    import logging

    agent = isolated_agent(tmp)

    class _Resp:
        def __init__(self, usage: dict) -> None:
            self._usage = usage

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
                    "usage": self._usage}

    class _HTTP:
        def __init__(self, usage: dict) -> None:
            self._usage = usage

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            return _Resp(self._usage)

    async def cache_line(usage: dict) -> str:
        caplog.clear()
        agent._http = lambda **kw: _HTTP(usage)
        with caplog.at_level(logging.INFO, logger="agent"):
            await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                                  model="m", max_tokens=100, enable_search=False)
        lines = [r.getMessage() for r in caplog.records if "cache:" in r.getMessage()]
        return lines[0] if lines else ""

    line = await cache_line({"prompt_tokens": 500,
                             "prompt_tokens_details": {"cached_tokens": 300}})
    check("cache: the OpenAI-style spelling is read",
          "hit=300" in line and "in=500" in line, repr(line))
    line = await cache_line({"prompt_tokens": 500, "prompt_cache_hit_tokens": 120,
                             "prompt_cache_miss_tokens": 380})
    check("cache: DeepSeek's spelling still is",
          "hit=120" in line and "miss=380" in line, repr(line))
    line = await cache_line({"prompt_tokens": 500})
    check("cache: a zero hit rate is logged, not silent",
          "hit=0" in line and "in=500" in line, repr(line))


async def test_truncated_reply_retries_once(tmp: Path) -> None:
    """An empty reply with finish_reason=length must be diagnosed, not shrugged at.

    A reasoning model spends the budget on its chain of thought and can hit the
    cap before emitting a single visible token, so every turn comes back empty.
    The only clue used to be "finish_reason=length" in a warning, which does not
    tell an operator that their model choice is the cause. Found by running the
    benchmark against deepseek-v4-pro: every reply empty, every self-eval 1/5,
    and nothing in the logs pointing at why."""
    agent = isolated_agent(tmp)
    budgets: list[int] = []

    class _Resp:
        def __init__(self, content: str) -> None:
            self._c = content

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"choices": [{"message": {"content": self._c},
                                 "finish_reason": "length" if not self._c else "stop"}]}

    class _HTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            budgets.append(json["max_tokens"])
            return _Resp("" if len(budgets) == 1 else '{"reply":"recovered"}')

    agent._http = lambda **kw: _HTTP()
    out = await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                                model="reasoner", max_tokens=1200,
                                enable_search=False)
    check("truncation: retried once at a larger budget",
          budgets == [1200, 4800], repr(budgets))
    check("truncation: the retry's answer is returned",
          out == '{"reply":"recovered"}', repr(out))

    # json_object mode: a truncated non-empty JSON with finish=length must
    # also retry -- it used to bypass the empty-only check and get dropped by
    # the fail-closed parser with no length warning at all. And the payload
    # must actually carry response_format, or none of this mode exists.
    budgets.clear()
    payloads = []

    class _Trunc(_Resp):
        def json(self):
            return {"choices": [{"message": {"content": '{"reasoning": "half'},
                                 "finish_reason": "length" if len(budgets) == 1
                                 else "stop"}]}

    class _HTTP3(_HTTP):
        async def post(self, url, headers=None, json=None):
            budgets.append(json["max_tokens"])
            payloads.append(json)
            if len(budgets) == 1:
                return _Trunc("")
            return _Resp('{"reply":"whole"}')

    agent._http = lambda **kw: _HTTP3()
    out = await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                                model="m", max_tokens=1200,
                                enable_search=False, json_object=True)
    check("truncation: half-emitted JSON retries too",
          budgets == [1200, 4800], repr(budgets))
    check("truncation: whole JSON comes back from the retry",
          out == '{"reply":"whole"}', repr(out))
    check("json_object: payload carries response_format",
          all(pl.get("response_format") == {"type": "json_object"}
              for pl in payloads), repr(payloads[:1]))

    # A non-length empty reply must NOT trigger the retry.
    budgets.clear()

    class _EmptyStop(_Resp):
        def json(self):
            return {"choices": [{"message": {"content": ""},
                                 "finish_reason": "stop"}]}

    class _HTTP2(_HTTP):
        async def post(self, url, headers=None, json=None):
            budgets.append(json["max_tokens"])
            return _EmptyStop("")

    agent._http = lambda **kw: _HTTP2()
    await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                          model="m", max_tokens=1200, enable_search=False)
    check("truncation: an empty stop is not retried", budgets == [1200], repr(budgets))


async def test_blank_content_with_reasoning_retries_thinking_disabled(tmp: Path) -> None:
    """A thinking model (deepseek-v4-flash) can put the ENTIRE protocol answer
    in reasoning_content and leave `content` whitespace while finishing
    normally -- finish_reason="stop", not "length", so the truncation retry
    above never fires, and the stripped "" became a silent turn. Intermittent
    and prompt-dependent. The fix is one retry with thinking forced off; text
    is never salvaged from reasoning_content itself, because a fluent
    reasoning fragment is indistinguishable from an ordinary chat line."""
    agent = isolated_agent(tmp)
    payloads: list[dict] = []
    reasoning_blob = "the user hit a missing-header build error, " * 8
    answer = '{"reasoning":"","intent":"chat","reply":"try the include path","mem":""}'

    class _Resp:
        def __init__(self, content: str, reasoning: str = "") -> None:
            self._c, self._r = content, reasoning

        def raise_for_status(self) -> None:
            pass

        def json(self):
            msg = {"content": self._c}
            if self._r:
                msg["reasoning_content"] = self._r
            return {"choices": [{"message": msg, "finish_reason": "stop"}]}

    class _HTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            payloads.append(json)
            if len(payloads) == 1:
                return _Resp("   ", reasoning=reasoning_blob)
            return _Resp(answer)

    async def call(**kw) -> str:
        payloads.clear()
        agent._http = lambda **_kw: _HTTP()
        return await agent._call_llm(
            "sys", [{"role": "user", "content": "hi"}], model="deepseek-v4-flash",
            max_tokens=1200, enable_search=False, json_object=True, **kw)

    out = await call()
    check("blank+reasoning: retried exactly once", len(payloads) == 2, repr(payloads))
    check("blank+reasoning: the first ask left thinking on",
          "thinking" not in payloads[0], repr(payloads[0]))
    check("blank+reasoning: the retry forces thinking off",
          payloads[1].get("thinking") == {"type": "disabled"}, repr(payloads[1]))
    check("blank+reasoning: the retry keeps the same token budget",
          payloads[1].get("max_tokens") == 1200, repr(payloads[1]))
    check("blank+reasoning: the retry keeps json_object mode",
          payloads[1].get("response_format") == {"type": "json_object"},
          repr(payloads[1]))
    check("blank+reasoning: the retry's reply is returned, not the reasoning",
          out == answer, repr(out))

    # Thinking was already off: the same request again would answer the same.
    out = await call(disable_thinking=True)
    check("blank+reasoning: no retry when the caller already disabled thinking",
          len(payloads) == 1 and out == "", repr((len(payloads), out)))

    class _HTTPNormal(_HTTP):
        async def post(self, url, headers=None, json=None):
            payloads.append(json)
            return _Resp('{"reply":"fine"}', reasoning=reasoning_blob)

    payloads.clear()
    agent._http = lambda **kw: _HTTPNormal()
    out = await agent._call_llm(
        "sys", [{"role": "user", "content": "hi"}], model="deepseek-v4-flash",
        max_tokens=1200, enable_search=False, json_object=True)
    check("normal reply: reasoning beside real content does not retry",
          len(payloads) == 1 and out == '{"reply":"fine"}',
          repr((len(payloads), out)))


async def test_disabled_thinking_speaks_openrouters_dialect_too(tmp: Path) -> None:
    """`thinking: {type: disabled}` is passed through by OpenRouter and
    ignored by some of its upstreams (measured: qwen3.7-flash and
    deepseek-v4-flash kept reasoning under it, 10-20s and 300+ tokens), so a
    call that asks for no hidden reasoning also sends OpenRouter's own
    `reasoning: {enabled: false}` -- on OpenRouter's host only, since another
    vendor may 400 an unknown field. A call that did not ask keeps its
    reasoning: this only makes an existing request mean what it says."""
    agent = isolated_agent(tmp)
    payloads: list = []

    class _Resp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}

    class _HTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            payloads.append(json)
            return _Resp()

    agent._http = lambda **kw: _HTTP()

    async def call(base_url: str, disable_thinking: bool) -> dict:
        agent.base_url = base_url
        await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                              model=agent.model, max_tokens=100, enable_search=False,
                              disable_thinking=disable_thinking)
        return payloads[-1]

    p = await call("https://openrouter.ai/api/v1", True)
    check("openrouter: thinking off in OpenRouter's own dialect",
          p.get("reasoning") == {"enabled": False}, repr(p))
    check("openrouter: ...and not in DeepSeek's, which it does not need",
          "thinking" not in p, repr(p))
    p = await call("https://api.deepseek.com", True)
    check("deepseek: thinking off in its dialect, and no OpenRouter field leaks to it",
          p.get("thinking") == {"type": "disabled"} and "reasoning" not in p, repr(p))
    p = await call("https://llm.example/api/v4/chat/completions", True)
    check("a vendor of unknown dialect is asked in DeepSeek's dialect, not OpenRouter's",
          p.get("thinking") == {"type": "disabled"} and "reasoning" not in p, repr(p))
    p = await call("https://openrouter.ai/api/v1", False)
    check("openrouter: a call that keeps its reasoning is not changed",
          "thinking" not in p and "reasoning" not in p, repr(p))
    # The search decision builds its own payload, and with reasoning on it
    # rarely emits a tool call at all -- so the search never fired.
    agent.base_url = "https://openrouter.ai/api/v1"
    await agent._decide_and_search([], hint="what is the price of gold today")
    p = payloads[-1]
    check("openrouter: the search decision turns reasoning off in its dialect too",
          p.get("reasoning") == {"enabled": False} and "thinking" not in p, repr(p))


async def test_a_vision_verdict_on_openrouter_does_not_think(tmp: Path) -> None:
    """The vision calls budget 60-120 tokens; a reasoning model on OpenRouter
    spent all of them thinking and every caption and verdict came back empty.
    The call site hands the endpoint to the switch, not just the model name."""
    import io

    from PIL import Image

    agent = isolated_agent(tmp)
    agent.vision_model = "qwen/qwen3.7-flash"
    agent.vision_api_key = "vision-key"
    agent.vision_base_url = "https://openrouter.ai/api/v1"
    payloads: list = []

    class _Resp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": '{"tacky": false}'}}]}

    class _HTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            payloads.append(json)
            return _Resp()

    agent._http = lambda **kw: _HTTP()
    buf = io.BytesIO()
    Image.effect_noise((64, 64), 64).convert("RGB").save(buf, "PNG")
    verdict = await agent._judge_sticker_aesthetic(buf.getvalue())
    check("vision: the verdict still parses", verdict is False, repr(verdict))
    check("vision: OpenRouter's reasoning switch is on the payload",
          payloads and payloads[0].get("reasoning") == {"enabled": False},
          repr(payloads[:1]))


async def test_json_mode_blank_falls_back_to_plain_text(tmp: Path) -> None:
    """With `response_format: json_object` AND a prior assistant turn in the
    history, DeepSeek answers whitespace with finish_reason="stop". Measured,
    4 trials per arm, on two of its models:

        user only                                   blank 1/4
        user + assistant + user                     blank 4/4
        assistant turn reshaped as protocol JSON    blank 4/4
        same messages, no response_format           blank 0/4

    A private chat replays the persona's own turns, so every DM after the
    first could come back empty. Neither earlier rung sees it (not "length",
    no reasoning_content required), so the reply calls get a last rung that
    drops response_format and wraps the prose into the protocol."""
    agent = isolated_agent(tmp)
    payloads: list = []

    class _Resp:
        def __init__(self, content: str, reasoning: str = "") -> None:
            self._c, self._r = content, reasoning

        def raise_for_status(self) -> None:
            pass

        def json(self):
            msg = {"content": self._c}
            if self._r:
                msg["reasoning_content"] = self._r
            return {"choices": [{"message": msg, "finish_reason": "stop"}]}

    class _HTTP:
        def __init__(self, last: str, reasoning: str = "") -> None:
            self._last, self._reasoning = last, reasoning

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            payloads.append(json)
            if "response_format" in json:
                # Whitespace, not "" — the shape the provider actually returns.
                return _Resp("   \n  ", self._reasoning)
            return _Resp(self._last)

    async def call(last: str, reasoning: str = "", **kw) -> str:
        payloads.clear()
        agent._http = lambda **_kw: _HTTP(last, reasoning)
        return await agent._call_llm(
            "sys", [{"role": "user", "content": "hi"}], model="m",
            max_tokens=1200, enable_search=False, json_object=True, **kw)

    out = await call("the street is gone by morning", plain_text_fallback=True)
    check("the blank turn is retried WITHOUT response_format",
          len(payloads) == 2
          and payloads[0].get("response_format") == {"type": "json_object"}
          and "response_format" not in payloads[1],
          repr([sorted(p) for p in payloads]))
    reply, _r, _i, _m = TextProcessing._parse_model_output(out)
    check("...and the recovered prose reaches the parser as the reply",
          reply == "the street is gone by morning", repr((out, reply)))

    # The system prompt still asks for JSON, and the model sometimes obliges
    # with response_format gone: pass it through rather than nest it.
    out = await call('{"reply": "already protocol-shaped"}', plain_text_fallback=True)
    reply, _r, _i, _m = TextProcessing._parse_model_output(out)
    check("a protocol object from the retry is passed through, not double-wrapped",
          reply == "already protocol-shaped", repr((out, reply)))
    out = await call('```json\n{"reply": "fenced"}\n```', plain_text_fallback=True)
    check("...fenced the way a model writes JSON without response_format too",
          TextProcessing._parse_model_output(out)[0] == "fenced", repr(out))
    out = await call('[{"reasoning": "", "intent": "chat", "reply": "wrapped",'
                     ' "mem": ""}]', plain_text_fallback=True)
    check("...or wrapped in an array, which the parser unwraps",
          TextProcessing._parse_model_output(out)[0] == "wrapped", repr(out))

    # After the thinking-off rung, not instead of it: that rung keeps
    # response_format, so a provider that blanks on JSON mode blanks there too.
    out = await call("recovered", reasoning="planned an answer",
                     plain_text_fallback=True)
    check("the plain-text rung runs last, after the thinking-off retry",
          [("response_format" in p, "thinking" in p) for p in payloads]
          == [(True, False), (True, True), (False, False)],
          repr([sorted(p) for p in payloads]))
    check("...and still recovers the turn",
          TextProcessing._parse_model_output(out)[0] == "recovered", repr(out))

    # Off by default: every json_object caller whose schema is not `reply`.
    out = await call("the street is gone by morning")
    check("without the flag there is no second call and nothing is recovered",
          len(payloads) == 1 and out == "", repr((len(payloads), out)))

    # Some upstreams ignore JSON mode and answer in prose on the FIRST call.
    class _ProseHTTP(_HTTP):
        async def post(self, url, headers=None, json=None):
            payloads.append(json)
            return _Resp("the lane is quiet tonight")

    payloads.clear()
    agent._http = lambda **_kw: _ProseHTTP("")
    out = await agent._call_llm(
        "sys", [{"role": "user", "content": "hi"}], model="m", max_tokens=1200,
        enable_search=False, json_object=True, plain_text_fallback=True)
    check("prose answered in JSON mode is wrapped, not dropped, in one call",
          TextProcessing._parse_model_output(out)[0] == "the lane is quiet tonight"
          and len(payloads) == 1, repr((out, len(payloads))))


async def test_only_the_reply_calls_recover_plain_text(tmp: Path) -> None:
    """The plain-text rung is for calls whose schema IS `reply`. The group
    gate's output is a PASS/reply decision; recovering prose for it would
    turn "could not decide" into "decided to say this"."""
    agent = isolated_agent(tmp)
    agent.llm_judge_model = "gate-model"
    calls: list[tuple[str, bool]] = []

    async def fake_call(*, system, messages, model, **kw):
        calls.append((model, kw.get("plain_text_fallback", False)))
        return '{"reasoning": "r", "intent": "chat", "reply": "sure", "mem": ""}'

    agent._call_llm = fake_call
    agent._append_buffer("g", "Alice", "anyone around tonight", "42")
    await agent._think("g", "judge", "anyone around tonight")
    check("group: the gate call does not recover plain text",
          calls[0] == ("gate-model", False), repr(calls))
    check("group: the reply call does",
          len(calls) == 2 and calls[1][1] is True, repr(calls))

    calls.clear()
    await agent._chat_dm([{"role": "user", "content": "hey"}],
                              is_admin=True, pkey="private:42")
    check("private: the 1:1 reply call recovers plain text",
          calls == [(agent.llm_dm_model, True)], repr(calls))


class _429Resp:
    """Minimal httpx.Response stand-in: raise_for_status() always throttles."""

    def raise_for_status(self) -> None:
        raise RuntimeError("429 too many requests (status 429)")

    def json(self):
        return {}


def _llm_http(posts: list, fail_models: set) -> type:
    """Fake ``self._http()`` context manager: 429s for any model in
    ``fail_models``, otherwise a normal stop-finished reply that names the
    model that answered (so the caller can tell which one won)."""

    class _OKResp:
        def __init__(self, mdl: str) -> None:
            self._mdl = mdl

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"choices": [{"message": {"content": f"ok from {self._mdl}"},
                                 "finish_reason": "stop"}]}

    class _HTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            mdl = json["model"]
            posts.append(mdl)
            if mdl in fail_models:
                return _429Resp()
            return _OKResp(mdl)

    return _HTTP


def _two_model_agent(tmp: Path) -> Agent:
    a = isolated_agent(tmp)
    a.model, a.llm_fallback_model = "primary", "fallback"
    a.llm_fallback_duration_s = 300
    a.api_max_retries = 0
    return a


async def test_error_cooldown_cools_only_failed_model(tmp: Path) -> None:
    """A 429 on the primary cools ONLY the primary: the fallback stays
    eligible, both as the mid-call failover and on the next
    _pick_group_model() in every mode (error-driven cooldown applies to
    called/admin too)."""
    agent = _two_model_agent(tmp)
    posts: list = []
    agent._http = lambda **kw: _llm_http(posts, {"primary"})()

    out = await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                                model="primary", max_tokens=100, enable_search=False)
    check("cooldown: mid-call failover lands on the fallback",
          out == "ok from fallback", repr(out))
    check("cooldown: primary tried once, then fallback -- no bouncing",
          posts == ["primary", "fallback"], repr(posts))
    now = time.time()
    check("cooldown: primary's entry is armed",
          agent._fallback_until.get("primary", 0.0) > now, repr(agent._fallback_until))
    check("cooldown: fallback's entry is untouched -- it never failed",
          "fallback" not in agent._fallback_until, repr(agent._fallback_until))
    picks = {m: agent._pick_group_model(m) for m in ("called", "owner", "followup")}
    check("cooldown: next pick routes straight to fallback for every mode",
          all(p == "fallback" for p in picks.values()), repr(picks))


async def test_a_side_model_failure_does_not_cool_the_group_model(tmp: Path) -> None:
    """The defect the per-model clock fixes: one scalar clock meant a failing
    LLM_DM_MODEL, LLM_JUDGE_MODEL or EVAL_MODEL -- any model sent through
    _call_llm -- armed the cooldown and moved every group reply to the
    fallback, though the primary never failed."""
    agent = _two_model_agent(tmp)
    posts: list = []
    agent._http = lambda **kw: _llm_http(posts, {"dm-model"})()

    out = await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                                model="dm-model", max_tokens=100, enable_search=False)
    check("side model: its call still fails over to the fallback",
          out == "ok from fallback" and posts == ["dm-model", "fallback"],
          repr((out, posts)))
    check("side model: only the model that failed is cooling",
          set(agent._fallback_until) == {"dm-model"}, repr(agent._fallback_until))
    picks = {m: agent._pick_group_model(m) for m in ("called", "owner")}
    check("side model: group replies stay on the primary",
          all(p == "primary" for p in picks.values()), repr(picks))


async def test_a_throttled_model_cools_in_seconds_not_minutes(tmp: Path) -> None:
    """A 429 is not a breakage, and treating it as one threw away most of a
    working model: under the one shared 300s window, a primary that 429s on
    one call in four spent most of its time routed around. The call that hit
    the 429 already failed over; the window only has to keep the next few
    turns off the same wall. So `llm_rate_limit_cooldown_s` is for metered, and
    `llm_fallback_duration_s` for a model that answered 400 or ran out of retries."""
    agent = _two_model_agent(tmp)
    agent.llm_rate_limit_cooldown_s = 20
    posts: list = []
    agent._http = lambda **kw: _llm_http(posts, {"primary"})()

    before = time.time()
    out = await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                                model="primary", max_tokens=100, enable_search=False)
    check("throttled: the turn is still served, by the fallback",
          out == "ok from fallback", repr(out))
    armed = agent._fallback_until.get("primary", 0.0) - before
    check("throttled: the window is the SHORT one",
          19 <= armed <= 22, f"{armed:.1f}s")

    # The other class of failure keeps the long window: a model that answers
    # 400 will answer 400 again, and five minutes of not asking is cheap.
    broken = _two_model_agent(tmp / "b")
    broken.llm_rate_limit_cooldown_s = 20
    bad: list = []

    class _Bad:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            bad.append(json["model"])
            if json["model"] == "primary":
                raise httpx.HTTPStatusError(
                    "bad request",
                    request=httpx.Request("POST", "https://x.invalid"),
                    response=httpx.Response(400))
            return await _llm_http([], set())().post(url, headers, json)

    broken._http = lambda **kw: _Bad()
    t0 = time.time()
    out = await broken._call_llm("sys", [{"role": "user", "content": "hi"}],
                                 model="primary", max_tokens=100, enable_search=False)
    long_window = broken._fallback_until.get("primary", 0.0) - t0
    check("a 400 is served by the fallback too",
          out == "ok from fallback" and bad == ["primary", "fallback"],
          repr((out, bad)))
    check("a 400 still cools for the long window",
          long_window > 200, f"{long_window:.1f}s")


async def test_error_cooldown_both_models_can_cool(tmp: Path) -> None:
    """One call, two in-call failover attempts: the primary 429s, the call
    fails over to the fallback, and the fallback ALSO throttles -- there is
    nowhere left to route, so the call raises. The per-model dict records
    both cooldowns; the old scalar had no slot for the fallback's own."""
    agent = _two_model_agent(tmp)
    posts: list = []
    agent._http = lambda **kw: _llm_http(posts, {"primary", "fallback"})()

    raised = None
    try:
        await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                              model="primary", max_tokens=100, enable_search=False)
    except RuntimeError as e:
        raised = e
    check("cooldown: the call still raises when both throttle",
          raised is not None and "429" in str(raised), repr(raised))
    check("cooldown: tried primary once then fallback once, no infinite bounce",
          posts == ["primary", "fallback"], repr(posts))
    now = time.time()
    check("cooldown: primary cooled", agent._fallback_until.get("primary", 0.0) > now,
          repr(agent._fallback_until))
    check("cooldown: fallback ALSO cooled",
          agent._fallback_until.get("fallback", 0.0) > now, repr(agent._fallback_until))
    picked = agent._pick_group_model("called")
    check("cooldown: pick still routes to fallback -- no third option",
          picked == "fallback", picked)


async def test_error_cooldown_single_model_unchanged(tmp: Path) -> None:
    """With no distinct fallback (LLM_FALLBACK_MODEL blank resolves to the main
    model) there is nowhere to switch: the call retries the one model and
    raises, exactly as before. The dict does gain the model's own entry, but
    it gates to the same name, so routing is unchanged."""
    agent = isolated_agent(tmp)
    agent.model = agent.llm_fallback_model = "solo"
    agent.api_max_retries = 0
    posts: list = []
    agent._http = lambda **kw: _llm_http(posts, {"solo"})()

    raised = None
    try:
        await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                              model="solo", max_tokens=100, enable_search=False)
    except RuntimeError as e:
        raised = e
    check("cooldown: solo model raises on exhaustion", raised is not None, repr(raised))
    check("cooldown: only ever tried the one model, no phantom switch",
          posts == ["solo"], repr(posts))
    check("cooldown: solo's own entry is armed",
          agent._fallback_until.get("solo", 0.0) > time.time(),
          repr(agent._fallback_until))
    picks = {m: agent._pick_group_model(m) for m in ("called", "followup")}
    check("cooldown: routing unchanged -- still the one model",
          all(p == "solo" for p in picks.values()), repr(picks))


class _EndpointSpy:
    """Fake ``self._http()`` that records (url, bearer key, model) for every
    POST: 429 for a model in ``fail``, otherwise a 200 whose content also
    parses as a self-eval verdict."""

    def __init__(self, seen: list, fail: set = frozenset()) -> None:
        self._seen, self._fail = seen, fail

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        self._seen.append((url, headers["Authorization"], json["model"]))
        if json["model"] in self._fail:
            return _429Resp()

        class _OK:
            status_code = 200

            def raise_for_status(self) -> None:
                pass

            def json(self):
                return {"choices": [{"message": {"content": '{"score": 5, "reason": "ok"}'},
                                     "finish_reason": "stop"}]}
        return _OK()


async def test_the_fallback_model_calls_its_own_endpoint(tmp: Path) -> None:
    """The fallback model used to be only a NAME on the primary's endpoint, so
    an outage at the primary's provider took the fallback down with it.
    LLM_FALLBACK_BASE_URL / LLM_FALLBACK_API_KEY give it an endpoint of its own, used
    wherever that model is called: the in-call failover, and the gate,
    search decision and self-eval, whose models default to it."""
    agent = _two_model_agent(tmp)
    agent.base_url, agent.api_key = "https://primary.example", "primary-key"
    agent.llm_fallback_base_url = "https://fallback.example/v1"
    agent.llm_fallback_api_key = "fallback-key"
    agent.llm_judge_model = agent.eval_model = "fallback"  # what blank resolves to
    agent.llm_dm_model = "dm-model"
    primary = ("https://primary.example/v1/chat/completions", "Bearer primary-key")
    fallback = ("https://fallback.example/v1/chat/completions", "Bearer fallback-key")
    seen: list = []
    agent._http = lambda **kw: _EndpointSpy(seen, fail={"primary"})

    await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                          model="primary", max_tokens=100, enable_search=False)
    check("failover: the primary is asked on its endpoint, the fallback on its own",
          seen == [(*primary, "primary"), (*fallback, "fallback")], repr(seen))

    seen.clear()
    await agent._decide_and_search([], hint="what is the price of gold today")
    check("search decision: the judge model is the fallback, so its endpoint",
          seen == [(*fallback, "fallback")], repr(seen))

    seen.clear()
    agent.examples_seed_file = tmp / "examples.seed.jsonl"
    agent.examples_file = tmp / "examples.jsonl"
    await agent._evaluate_reply("g", "called", "question", "a reply", None, "chat",
                                ["Alice: question"])
    check("self-eval: the eval model is the fallback, so its endpoint",
          seen == [(*fallback, "fallback")], repr(seen))

    seen.clear()
    await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                          model="dm-model", max_tokens=100, enable_search=False)
    check("every other model name stays on the primary endpoint",
          seen == [(*primary, "dm-model")], repr(seen))

    # Unset: the fallback shares the primary's endpoint, as it always did.
    agent.llm_fallback_base_url = agent.llm_fallback_api_key = ""
    seen.clear()
    await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                          model="primary", max_tokens=100, enable_search=False)
    check("unset: the fallback is a name on the primary's endpoint",
          seen == [(*primary, "primary"), (*primary, "fallback")], repr(seen))


class _ThinkingSpy:
    """Fake ``self._http()`` recording ``(url, model, sent thinking?)`` per
    POST. A host containing ``rejects`` answers 400 to ``thinking``, as Groq
    does (`400 property 'thinking' is unsupported`); every other answer is a
    reply that is also a web_search tool call."""

    def __init__(self, seen: list, rejects: str = "") -> None:
        self._seen, self._rejects = seen, rejects

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        self._seen.append((url, json["model"], "thinking" in json))
        refused = bool(self._rejects) and self._rejects in url and "thinking" in json

        class _Resp:
            status_code = 400 if refused else 200
            text = "property 'thinking' is unsupported" if refused else ""

            def raise_for_status(self) -> None:
                if refused:
                    raise RuntimeError("400 bad request: property 'thinking' is unsupported")

            def json(self):
                call = {"function": {"name": "web_search",
                                     "arguments": '{"query": "gold price"}'}}
                return {"choices": [{"message": {"content": "ok", "tool_calls": [call]},
                                     "finish_reason": "stop"}]}
        return _Resp()


async def test_a_fallback_on_another_vendor_is_not_sent_thinking(tmp: Path) -> None:
    """`thinking` is DeepSeek's field; Groq and OpenAI answer 400 to it. The
    gate, the search decision and the sticker tagger ask for thinking off and
    run on the judge model, which defaults to the fallback — so with the
    fallback on its own vendor all three went there with the field on EVERY
    turn: the gate had no rung left to fail over to and the bot never spoke
    up in a group, the search never fired, and no sticker was tagged."""
    agent = _two_model_agent(tmp)
    agent.base_url, agent.api_key = "https://api.deepseek.com", "primary-key"
    agent.llm_fallback_base_url = "https://api.groq.com/openai/v1"
    agent.llm_fallback_api_key = "fallback-key"
    agent.llm_judge_model = "fallback"  # what a blank LLM_JUDGE_MODEL resolves to
    primary = "https://api.deepseek.com/v1/chat/completions"
    fallback = "https://api.groq.com/openai/v1/chat/completions"
    seen: list = []
    agent._http = lambda **kw: _ThinkingSpy(seen, rejects="groq.com")

    async def fake_search(query: str, max_results: int = 4) -> str:
        return f"results for {query}"

    agent._web_search = fake_search

    async def thinking_off(model: str) -> str:
        # The gate's and the sticker tagger's call shape.
        return await agent._call_llm(
            "sys", [{"role": "user", "content": "hi"}], model=model,
            max_tokens=100, enable_search=False, disable_thinking=True,
            json_object=True)

    out = await thinking_off(agent.llm_judge_model)
    check("gate on the fallback's vendor: answered, without `thinking`",
          out == "ok" and seen == [(fallback, "fallback", False)], repr((out, seen)))
    seen.clear()
    found = await agent._decide_and_search([], hint="what is the price of gold today")
    check("search decision on the fallback's vendor: fires, without `thinking`",
          found == "results for gold price" and seen == [(fallback, "fallback", False)],
          repr((found, seen)))
    seen.clear()
    await thinking_off("primary")
    check("a vendor known to take it is sent `thinking`",
          seen == [(primary, "primary", True)], repr(seen))

    # Told it takes it, and wrong: the 400 that names the field is retried
    # without it once, and the endpoint is remembered.
    agent.llm_fallback_thinking = True
    seen.clear()
    out = await thinking_off("fallback")
    check("a 400 naming `thinking` is retried without it",
          out == "ok" and seen == [(fallback, "fallback", True),
                                   (fallback, "fallback", False)], repr((out, seen)))
    seen.clear()
    await thinking_off("fallback")
    await agent._decide_and_search([], hint="what is the price of gold today")
    check("...and that endpoint is not sent it again",
          seen == [(fallback, "fallback", False)] * 2, repr(seen))

    agent._api_quirks.clear()
    agent._http = lambda **kw: _ThinkingSpy(seen)
    seen.clear()
    await thinking_off("fallback")
    await agent._decide_and_search([], hint="what is the price of gold today")
    check("LLM_FALLBACK_THINKING: a fallback vendor that takes it is sent it",
          seen == [(fallback, "fallback", True)] * 2, repr(seen))

    agent.llm_fallback_thinking = False
    for base in ("https://api.deepseek.com/beta", ""):
        agent.llm_fallback_base_url = base
        seen.clear()
        await thinking_off("fallback")
        check(f"a fallback on the primary's known host is sent it ({base or 'unset'})",
              [t for _u, _m, t in seen] == [True], repr(seen))


async def test_the_startup_probe_learns_whether_an_endpoint_takes_thinking(tmp: Path) -> None:
    """A host of unknown dialect is asked once, by the startup probe, rather
    than by every gate call: if it takes `thinking` the gate gets it from then
    on, and if it 400s the probe is retried without it and nothing else is
    ever sent it."""
    for rejects, want in (("", True), ("custom.example", False)):
        agent = isolated_agent(tmp)
        agent.base_url = "https://custom.example/v1"
        agent.model = agent.llm_fallback_model = agent.llm_judge_model = "m"
        seen: list = []
        agent._http = lambda **kw: _ThinkingSpy(seen, rejects=rejects)
        await agent.probe_models()
        url = "https://custom.example/v1/chat/completions"
        check(f"the probe asked about `thinking` (rejects={bool(rejects)})",
              seen[0] == (url, "m", True), repr(seen))
        check("...and answered, retried without it when refused",
              [t for _u, _m, t in seen] == ([True] if want else [True, False]),
              repr(seen))
        seen.clear()
        await agent._call_llm("sys", [{"role": "user", "content": "hi"}], model="m",
                              max_tokens=100, enable_search=False,
                              disable_thinking=True)
        check(f"a gate call afterwards sends it only if it was taken ({want})",
              seen == [(url, "m", want)], repr(seen))
    agent.base_url = "https://api.openai.com"
    agent._api_quirks.clear()
    seen.clear()
    await agent.probe_models()
    check("a vendor known to refuse it is not asked",
          [t for _u, _m, t in seen] == [False], repr(seen))


async def test_a_reasoning_model_gets_the_spelling_it_takes(tmp: Path) -> None:
    """OpenAI's reasoning models 400 `max_tokens` and any non-default
    `temperature`. The call is retried once with `max_completion_tokens` and
    without the temperature, and the endpoint and model are remembered."""
    agent = isolated_agent(tmp)
    agent.base_url = "https://api.openai.com"
    agent.model = agent.llm_fallback_model = agent.llm_judge_model = "gpt-5-mini"
    sent: list = []

    class _Resp:
        def __init__(self, status: int, text: str = "") -> None:
            self.status_code, self.text = status, text

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"{self.status_code} bad request")

        def json(self):
            return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}

    class _OpenAI:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            sent.append(sorted(k for k in json if k not in ("model", "messages")))
            if "max_tokens" in json:
                return _Resp(400, "Unsupported parameter: 'max_tokens' is not "
                                  "supported with this model. Use "
                                  "'max_completion_tokens' instead.")
            if "temperature" in json:
                return _Resp(400, "Unsupported value: 'temperature' does not "
                                  "support 0.3 with this model. Only the default "
                                  "(1) value is supported.")
            return _Resp(200)

    agent._http = lambda **kw: _OpenAI()

    async def gate() -> str:
        return await agent._call_llm(
            "sys", [{"role": "user", "content": "hi"}], model="gpt-5-mini",
            max_tokens=1500, enable_search=False, disable_thinking=True,
            temperature=0.3)

    check("the gate answers on a reasoning model", await gate() == "ok")
    check("...after one retry per refused field",
          sent == [["max_tokens", "temperature"],
                   ["max_completion_tokens", "temperature"],
                   ["max_completion_tokens"]], repr(sent))
    sent.clear()
    check("the next call is spelled right the first time", await gate() == "ok")
    check("...with no 400 at all", sent == [["max_completion_tokens"]], repr(sent))


async def test_an_exhausted_balance_is_fatal_and_said_once(tmp: Path, caplog) -> None:
    """A 402 is the account, not the network: no retries, no failover to a
    model on the same account, and one operator line naming the host and the
    settings that fix it."""
    import logging

    import httpx

    agent = _two_model_agent(tmp)
    agent.api_max_retries = 2
    agent.base_url = "https://api.deepseek.com"
    posts: list = []

    class _Pay:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            posts.append(json["model"])
            request = httpx.Request("POST", url)
            return httpx.Response(402, request=request,
                                  json={"error": {"message": "Insufficient Balance"}})

    agent._http = lambda **kw: _Pay()
    check("402 classifies as fatal", agent._classify_api_error(httpx.HTTPStatusError(
        "402", request=httpx.Request("POST", "https://x"),
        response=httpx.Response(402))) == "fatal_auth")
    check("an exhausted OpenAI quota (a 429) is fatal too",
          agent._classify_api_error(httpx.HTTPStatusError(
              "429", request=httpx.Request("POST", "https://x"),
              response=httpx.Response(429, json={"error": {
                  "type": "insufficient_quota",
                  "message": "You exceeded your current quota"}}))) == "fatal_auth")
    with caplog.at_level(logging.ERROR, logger="agent"):
        for _ in range(2):
            try:
                await agent._call_llm("sys", [{"role": "user", "content": "hi"}],
                                      model="primary", max_tokens=10,
                                      enable_search=False)
            except Exception:
                pass
    check("no retry and no failover on a 402", posts == ["primary", "primary"],
          repr(posts))
    lines = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    check("one operator line, naming the host and the settings",
          len(lines) == 1 and "api.deepseek.com" in lines[0]
          and "balance or quota" in lines[0] and "LLM_API_KEY" in lines[0]
          and "LLM_BASE_URL" in lines[0], repr(lines))


async def test_a_separate_fallback_endpoint_is_probed_at_startup(tmp: Path) -> None:
    """It exists for the primary's outage, so a typo in its URL or key would
    otherwise surface during that outage and not before."""
    agent = _two_model_agent(tmp)
    agent.base_url = "https://primary.example"
    seen: list = []
    agent._http = lambda **kw: _EndpointSpy(seen)

    await agent.probe_models()
    check("probe: one endpoint, one probe",
          [m for _u, _k, m in seen] == ["primary"], repr(seen))
    agent.llm_fallback_base_url = "https://fallback.example"
    seen.clear()
    await agent.probe_models()
    check("probe: a fallback on its own endpoint is probed there too",
          [(u, m) for u, _k, m in seen]
          == [("https://primary.example/v1/chat/completions", "primary"),
              ("https://fallback.example/v1/chat/completions", "fallback")],
          repr(seen))
