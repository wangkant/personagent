"""How a model call reads a provider's errors and learns its dialect."""
from __future__ import annotations

import httpx

from persona_agent.agent import Agent


def check(name: str, cond: bool, detail: str = "") -> None:
    assert cond, name + (f" - {detail}" if detail else "")


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
