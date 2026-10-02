"""Calling the models: clients, endpoints, retries, fallback and probes."""
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from urllib.parse import urlsplit

import httpx

from .access import ADMIN_MODE
from .endpoints import adapt_rejected_payload, chat_completions_url, endpoint_for
from .textproc import (
    _as_protocol_object,
)

logger = logging.getLogger("agent")

# Hosts whose chat endpoint takes DeepSeek's `thinking` switch, and hosts
# known to refuse it; any other endpoint is asked by its first call that
# turns thinking off (or the startup probe), and the answer remembered.
_THINKING_HOSTS = ("deepseek.com", "bigmodel.cn", "z.ai", "moonshot.cn",
                   "moonshot.ai", "volces.com")
_NO_THINKING_HOSTS = ("openai.com", "groq.com", "googleapis.com",
                      "openrouter.ai", "mistral.ai", "anthropic.com")

# Words in an error that put the account, not the request, at fault.
_BILLING_WORDS = ("payment required", "insufficient", "balance", "quota",
                  "billing", "arrear")


def _host(url: str) -> str:
    return (urlsplit(url or "").hostname or "").lower()


def _on_host(host: str, domains: tuple) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def _status_of(e: BaseException):
    """The HTTP status an exception carries, structured or in its message."""
    status = getattr(e, "status_code", None)
    if status is None:
        status = getattr(getattr(e, "response", None), "status_code", None)
    try:
        status = int(status) if status is not None else None
    except (TypeError, ValueError):
        status = None
    if status is None:
        # \b keeps '401' from matching inside '4012345'.
        m = re.search(r"\b([45]\d\d)\b", str(e))
        if m:
            status = int(m.group(1))
    return status


def _response_text(e: BaseException) -> str:
    """The start of an HTTP error's body: httpx's message omits it, and the
    body is where a provider says the quota is gone."""
    try:
        return str(getattr(getattr(e, "response", None), "text", "") or "")[:500]
    except Exception:
        return ""


def _error_text(e: BaseException, status) -> str:
    """The error's message, lowercased, with its body only on a status about
    the account: a 5xx body describes an outage and a 400 body may echo the
    request."""
    text = str(e).lower()
    if status in (None, 401, 402, 403, 429):
        text += " " + _response_text(e).lower()
    return text

# httpx expires an idle keep-alive connection after 5s, and the gap between a
# person's turns is always longer, so the pool would empty between every turn
# and each one would pay a fresh TCP+TLS handshake to the provider. The other
# two numbers are httpx's own defaults, spelled out because `Limits` resets
# any it is not given to "unlimited".
_HTTP_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20,
                            keepalive_expiry=300.0)

class _PooledHTTP:
    """An ``async with``-compatible handle over a shared, long-lived httpx client.

    Entering returns the pooled client; exiting does NOT close it. A
    config-keyed connection pool avoids paying a fresh TCP+TLS handshake on
    every call, and call sites keep the ``async with`` form of a plain
    ``httpx.AsyncClient``.
    """

    __slots__ = ("_client",)

    def __init__(self, client):
        self._client = client

    async def __aenter__(self):
        return self._client

    async def __aexit__(self, *exc):
        return False  # shared client — never closed here


class ModelCalls:
    def _http(self, **kwargs) -> "_PooledHTTP":
        """Pooled httpx client. Use exactly like a native ``AsyncClient`` context.

        Identical constructor kwargs reuse the same client (a keep-alive
        connection pool), eliminating the per-request TCP+TLS handshake. The
        clients are process-lived and need no explicit close.
        """
        kwargs.setdefault("limits", _HTTP_LIMITS)

        def _norm(v):
            if isinstance(v, dict):
                return tuple(sorted(v.items()))
            # httpx.Limits / Timeout define __eq__ without __hash__, so they
            # cannot key the pool dict as themselves.
            try:
                hash(v)
            except TypeError:
                return repr(v)
            return v

        key = tuple(sorted((k, _norm(v)) for k, v in kwargs.items()))
        client = self._http_pool.get(key)
        if client is None or client.is_closed:
            if self._closed and not self._warned_use_after_close:
                self._warned_use_after_close = True
                logger.warning(
                    "[Agent] HTTP pool rebuilt after aclose() — this Agent is "
                    "closed and the new connections will never be closed. A "
                    "closed Agent should be discarded, not reused.")
            client = httpx.AsyncClient(**kwargs)
            self._http_pool[key] = client
        return _PooledHTTP(client)

    def _local_http(self, **kwargs) -> "_PooledHTTP":
        """Pooled client for the NapCat bridge, which is a LOCAL service.

        `trust_env=False` because httpx has no implicit localhost bypass the
        way `requests` does: with an `HTTP_PROXY` in the launching shell — the
        normal state of affairs for anyone who needs a proxy to reach a model
        endpoint at all — every reply, every history poll and every OCR
        delegation to `127.0.0.1` would be relayed through that proxy, so
        restarting it would take the bot's outbound chat down with it.

        A separate entry point rather than `trust_env=False` repeated at each
        call site: the kwargs are the pool key, so this also keeps the bridge's
        connections in their own pool, and a new NapCat call does not have to
        remember. Outbound calls to the wider internet keep
        `trust_env=True` — a deployment that needs a proxy to reach its model
        still gets one."""
        return self._http(trust_env=False, **kwargs)

    def _endpoint_for(self, model: str) -> tuple[str, str]:
        """(chat-completions URL, API key) for one model name.

        Every raw POST to the chat model goes through here: the fallback
        model may live on its own endpoint (LLM_FALLBACK_BASE_URL /
        LLM_FALLBACK_API_KEY), and a call that took the primary's URL for it
        would share the very outage the fallback exists to survive. Read on
        every call, not snapshotted, because the model names and base URLs
        are plain attributes that callers and tests reassign."""
        base, key = endpoint_for(
            model, primary_model=self.model, fallback_model=self.llm_fallback_model,
            base_url=self.base_url, api_key=self.api_key,
            fallback_base_url=self.llm_fallback_base_url,
            fallback_api_key=self.llm_fallback_api_key)
        return chat_completions_url(base), key

    @property
    def _api_quirks(self) -> dict:
        """What each endpoint has shown it refuses or takes, learned per
        process: ("thinking", url, model) -> bool, and (field, url, model) ->
        True for a `max_tokens` or `temperature` it refused."""
        quirks = self.__dict__.get("_api_quirks_map")
        if quirks is None:
            quirks = self.__dict__["_api_quirks_map"] = {}
        return quirks

    def _thinking_verdict(self, url: str, model: str):
        """Whether `model` at `url` takes DeepSeek's `thinking` switch: True,
        False, or None when nobody knows yet.

        Elsewhere it is rejected rather than ignored (Groq answers `400
        property 'thinking' is unsupported`, OpenAI 400s any unknown
        argument). Known: what this model at this URL showed, a listed
        vendor, the fallback's host with LLM_FALLBACK_THINKING, or a vendor
        known to refuse it. Per model, because one gateway serves many."""
        verdict = self._api_quirks.get(("thinking", url, model))
        if verdict is not None:
            return verdict
        host = _host(url)
        if _on_host(host, _THINKING_HOSTS):
            return True
        if (self.llm_fallback_thinking
                and host == _host(self.llm_fallback_base_url or self.base_url)):
            return True
        if _on_host(host, _NO_THINKING_HOSTS):
            return False
        return None

    def _thinking_off(self, payload: dict, url: str) -> dict:
        """Ask the model behind `url` to skip hidden reasoning, in the
        spellings that endpoint accepts. An endpoint nobody knows yet is sent
        `thinking` and _post_chat learns from its answer. OpenRouter passes
        `thinking` through to upstreams that ignore it and has a switch of
        its own (see textproc.apply_k2_quirks)."""
        if self._thinking_verdict(url, str(payload.get("model") or "")) is not False:
            payload["thinking"] = {"type": "disabled"}
        if "openrouter.ai" in url:
            payload["reasoning"] = {"enabled": False}
        return payload

    def _apply_quirks(self, url: str, payload: dict) -> None:
        """Spell `payload` the way `url` has shown it accepts."""
        quirks = self._api_quirks
        model = str(payload.get("model") or "")
        if quirks.get(("thinking", url, model)) is False:
            payload.pop("thinking", None)
        if ("max_tokens", url, model) in quirks and "max_tokens" in payload:
            payload["max_completion_tokens"] = payload.pop("max_tokens")
        if ("temperature", url, model) in quirks:
            payload.pop("temperature", None)

    def _remember_refusal(self, url: str, model: str, field: str) -> None:
        self._api_quirks[(field, url, model)] = False if field == "thinking" else True
        instead = ("sending max_completion_tokens instead"
                   if field == "max_tokens" else "leaving it out")
        logger.info("[Agent] %s does not take `%s` for model %s; %s from now on",
                    _host(url) or url, field, model, instead)

    async def _post_chat(self, url: str, key: str, payload: dict, *,
                         timeout: float):
        """POST one chat completion and return the response, unraised.

        A 400 that refuses a field this endpoint does not take (`thinking`,
        or `max_tokens` / `temperature` on OpenAI's reasoning models) is
        retried without it. When the retry succeeds the endpoint and model
        are remembered, so later calls are spelled right the first time; so
        is whether an endpoint nobody knew about takes `thinking`."""
        self._apply_quirks(url, payload)
        model = str(payload.get("model") or "")
        asking = ("thinking" in payload
                  and self._thinking_verdict(url, model) is None)
        headers = {"Authorization": f"Bearer {key}",
                   "Content-Type": "application/json"}
        status = 200
        refused: list[str] = []
        async with self._http(timeout=timeout) as client:
            for _ in range(4):
                resp = await client.post(url, json=dict(payload), headers=headers)
                status = getattr(resp, "status_code", 200)
                if status not in (400, 422):
                    break
                field = adapt_rejected_payload(
                    payload, str(getattr(resp, "text", "") or ""))
                if not field and asking and "thinking" in payload:
                    # An endpoint being asked may refuse it in words of its own.
                    payload.pop("thinking")
                    field = "thinking"
                if not field:
                    break
                refused.append(field)
        if isinstance(status, int) and 200 <= status < 300:
            for field in refused:
                self._remember_refusal(url, model, field)
            if asking and "thinking" in payload:
                self._api_quirks[("thinking", url, model)] = True
            # Working again, so a later failure is worth a line again.
            reported = self._fatal_reported_hosts()
            for item in [k for k in reported if k[0] == _host(url)]:
                reported.discard(item)
        return resp

    def _fatal_reported_hosts(self) -> set:
        reported = self.__dict__.get("_fatal_reported")
        if reported is None:
            reported = self.__dict__["_fatal_reported"] = set()
        return reported

    def _report_fatal(self, e: BaseException, model: str) -> None:
        """One operator line per provider when the key or the account is the
        problem, naming the settings that fix it."""
        url, _key = self._endpoint_for(model)
        host = _host(url) or url
        status = _status_of(e)
        text = _error_text(e, status)
        billing = status == 402 or any(w in text for w in _BILLING_WORDS)
        kind = "billing" if billing else "auth"
        reported = self._fatal_reported_hosts()
        if (host, kind) in reported:
            return
        reported.add((host, kind))
        on_fallback = (model == self.llm_fallback_model and model != self.model
                       and bool(self.llm_fallback_base_url or self.llm_fallback_api_key))
        key_name, url_name = (("LLM_FALLBACK_API_KEY", "LLM_FALLBACK_BASE_URL")
                              if on_fallback else ("LLM_API_KEY", "LLM_BASE_URL"))
        if billing:
            logger.error(
                "[Agent] the model provider at %s refused the call: the "
                "account's balance or quota is used up (HTTP %s). Top it up, "
                "or set %s / %s to another account.",
                host, status or "?", key_name, url_name)
        else:
            logger.error(
                "[Agent] the model provider at %s rejected the API key (HTTP "
                "%s). Check %s, and that %s is that provider's address.",
                host, status or "?", key_name, url_name)

    @staticmethod
    def _classify_api_error(e: BaseException) -> str:
        """Pick a recovery strategy for one failed call.

        Returns:
          rate_limit    — throttle/overload: switch to fallback model now + set cooldown
          transient     — network/timeout/5xx: jittered backoff, retry same model
          fatal_auth    — auth/billing: neither retry nor model swap helps; re-raise
          fatal_request — 4xx request-level: don't retry, but a fallback model may work
        Unknown errors are treated as transient (retryable).
        """
        # A structured status first, so a number inside a request id or a
        # token count is not read as one.
        status = _status_of(e)
        msg = _error_text(e, status)
        # Before the 429 check: OpenAI answers an exhausted quota with a 429.
        if status == 402 or any(k in msg for k in (
                "payment required", "insufficient_quota", "insufficient balance",
                "exceeded your current quota")):
            return "fatal_auth"
        if status in (429, 529) or any(k in msg for k in (
                "rate limit", "rate_limit", "too many requests", "overloaded")):
            return "rate_limit"
        if status in (401, 403) or any(k in msg for k in (
                "invalid api key", "authentication", "insufficient",
                "balance", "quota", "billing")):
            return "fatal_auth"
        if status in (400, 404, 422) or any(k in msg for k in (
                "model not found", "bad request", "invalid request", "unprocessable")):
            return "fatal_request"
        return "transient"

    async def _call_llm(
        self,
        system: str,
        messages: list[dict],
        model: str,
        max_tokens: int = 4096,
        enable_search: bool = True,
        disable_thinking: bool = False,
        temperature: float | None = None,
        search_hint: str = "",
        json_object: bool = False,
        plain_text_fallback: bool = False,
    ) -> str:
        """OpenAI-compatible /v1/chat/completions over plain httpx, with web
        search, jittered retry and error-driven fallback. `json_object` forces
        response_format: without it a thinking model drops the JSON protocol
        on ~1/3 of turns (measured 9/26 → 0/52).

        `plain_text_fallback` is the other half of that trade. With
        response_format set AND a prior assistant turn in the history,
        DeepSeek answers whitespace with finish_reason "stop" (measured 4/4
        on two of its models; the same messages without response_format:
        0/4) — so every private-chat turn after the
        first could come back empty. Reshaping the stored assistant turns as
        protocol JSON does not help (also 4/4): the trigger is
        response_format itself. With the flag, a reply still blank after the
        retries below is asked for once more without it, and the prose that
        comes back is wrapped into the protocol by `_as_protocol_object`;
        the parser is not loosened. Set only where `reply` IS the schema —
        the two reply calls. A gate, the adjudicator or the sticker tagger
        parse shapes of their own, and a recovered sentence would turn "could
        not decide" into "decided this"."""
        if not (self.base_url and self.api_key):
            logger.warning("[Agent] missing base_url/api_key; cannot call LLM")
            return ""
        sys_text = system or ""

        async def _do_call(mtok: int, mdl: str, force_disable_thinking: bool = False,
                           force_plain_text: bool = False):
            # Per call, not per invocation: `mdl` changes across the recovery
            # rungs below, and the fallback may live on another endpoint.
            _url, _key = self._endpoint_for(mdl)
            payload = {"model": mdl, "max_tokens": mtok, "messages": _oai_messages}
            if temperature is not None:
                payload["temperature"] = temperature
            if json_object and not force_plain_text:
                payload["response_format"] = {"type": "json_object"}
            if disable_thinking or force_disable_thinking:
                self._thinking_off(payload, _url)
            resp = await self._post_chat(_url, _key, payload,
                                         timeout=self.llm_timeout_s)
            resp.raise_for_status()
            return resp.json()

        # Web search: let the model decide (OpenAI-compatible /v1
        # function-calling), fetch real results (Tavily if keyed, else
        # DuckDuckGo), and inject them into the last user turn. Failures never
        # block the reply.
        if enable_search:
            messages = await self._ground_with_search(messages, hint=search_hint)

        # OpenAI endpoint uses a single system message; provider auto prefix-caches.
        _oai_messages = ([{"role": "system", "content": sys_text}] if sys_text else []) + list(messages)

        # ── Call recovery: jittered backoff on transient errors +
        # error-driven model failover ──
        # Network blips / 5xx auto-retry; throttling switches to the fallback model
        # immediately and arms a cooldown window (_pick_group_model then routes
        # subsequent traffic to the fallback too); after retries are exhausted a
        # non-auth error gets one last shot on the fallback model.
        async def _call_with_recovery():
            cur_model = model
            attempt = 0
            while True:
                try:
                    return (await _do_call(max_tokens, cur_model)), cur_model
                except Exception as e:
                    kind = self._classify_api_error(e)
                    # Throttled: arm a cooldown window for the model that just
                    # failed (later calls reroute via _pick_group_model) and
                    # switch to the fallback model now — don't waste retries on
                    # the throttled model. Arming is unconditional (it cools
                    # whichever model failed, the fallback included); only the
                    # switch needs a distinct fallback to jump to. The SHORT
                    # window: a 429 is metering, not breakage (see
                    # AgentSettings.llm_rate_limit_cooldown_s).
                    if kind == "rate_limit" and self.llm_fallback_model:
                        self._fallback_until[cur_model] = max(
                            self._fallback_until.get(cur_model, 0.0),
                            time.time() + self.llm_rate_limit_cooldown_s)
                        if cur_model != self.llm_fallback_model:
                            logger.warning(
                                "[Agent] throttled (model=%s); cooldown %ds, switching to fallback=%s: %s",
                                cur_model, self.llm_rate_limit_cooldown_s, self.llm_fallback_model, e)
                            cur_model = self.llm_fallback_model
                            attempt = 0  # give the fallback model its own retry budget
                            continue
                    # Transient: exponential backoff + jitter, retry same model.
                    if (kind in ("transient", "rate_limit")
                            and attempt < self.api_max_retries):
                        delay = (1.5 * (2 ** attempt)) * (0.7 + random.random() * 0.6)
                        attempt += 1
                        logger.warning(
                            "[Agent] API %s error (attempt %d/%d, model=%s), retrying in %.1fs: %s",
                            kind, attempt, self.api_max_retries, cur_model, delay, e)
                        await asyncio.sleep(delay)
                        continue
                    # Retries exhausted / request-level error: one last shot on the
                    # fallback model (except auth/billing, which it can't fix).
                    # Same unconditional-arm / conditional-switch split as above.
                    if kind != "fatal_auth" and self.llm_fallback_model:
                        self._fallback_until[cur_model] = max(
                            self._fallback_until.get(cur_model, 0.0),
                            time.time() + self.llm_fallback_duration_s)
                        if cur_model != self.llm_fallback_model:
                            logger.warning(
                                "[Agent] model=%s failed (%s); last attempt on fallback=%s",
                                cur_model, kind, self.llm_fallback_model)
                            cur_model = self.llm_fallback_model
                            attempt = 0  # give the fallback model its own retry budget
                            continue
                    if kind == "fatal_auth":
                        self._report_fatal(e, cur_model)
                    logger.warning("[Agent] LLM call failed (model=%s, %s): %s",
                                   cur_model, kind, e)
                    raise

        def _pick(d: dict) -> tuple[str, str]:
            choice = (d.get("choices") or [{}])[0]
            return (((choice.get("message") or {}).get("content") or "").strip(),
                    choice.get("finish_reason", "?"))

        def _hidden_reasoning(d: dict) -> str:
            # Read only to decide on a retry, never to take text from: a
            # fluent reasoning fragment cannot be told apart from a naked chat
            # line, and salvaging one would cross the protocol boundary
            # _parse_model_output exists to hold.
            choice = (d.get("choices") or [{}])[0]
            return ((choice.get("message") or {}).get("reasoning_content") or "").strip()

        data, used_model = await _call_with_recovery()
        try:
            text, finish = _pick(data)
            reasoning = _hidden_reasoning(data)
        except Exception as e:
            logger.warning("[Agent] failed to parse LLM response: %s; data=%.300s", e, str(data))
            return ""

        def _budget_starved(t: str, fin: str) -> bool:
            # Truncation shows up two ways on a reasoning model: no visible
            # text at all (budget died mid-thought), or — in json_object mode —
            # a half-emitted object like '{\n  "' that the fail-closed parser
            # would silently drop. Both are the same defect: the answer did
            # not fit. An empty-only condition would let every truncated
            # non-empty JSON skip the retry and vanish with no length warning.
            if fin != "length":
                return False
            if not t:
                return True
            if json_object:
                try:
                    json.loads(t)
                except (json.JSONDecodeError, TypeError):
                    return True
            return False

        if _budget_starved(text, finish):
            # A reasoning model spends the budget on its chain of thought and
            # can hit the cap before emitting a single visible token. The
            # symptom is an empty reply on every turn, and "finish_reason=length"
            # alone does not tell an operator that their model choice is the
            # cause. Retry once with a materially larger budget, then say
            # plainly what happened.
            retry_tokens = max_tokens * 4
            logger.warning(
                "[Agent] empty reply, finish_reason=length (model=%s, "
                "max_tokens=%d) — retrying once at %d. If this repeats, the "
                "model is likely a reasoning model whose thinking tokens "
                "exhaust the budget before the answer; pick a non-reasoning "
                "model or raise the cap.",
                used_model, max_tokens, retry_tokens)
            try:
                data = await _do_call(retry_tokens, used_model)
                text, finish = _pick(data)
            except Exception as e:
                logger.warning("[Agent] retry at a larger budget failed: %s: %s",
                               type(e).__name__, e)
            if not text:
                logger.warning(
                    "[Agent] still empty at max_tokens=%d (model=%s). This model "
                    "cannot answer within the budget — switch to a non-reasoning "
                    "model, or one that accepts thinking off.",
                    retry_tokens, used_model)
        elif not text and finish == "stop" and not disable_thinking and reasoning:
            # A thinking model occasionally puts the ENTIRE answer in
            # reasoning_content and leaves `content` whitespace while finishing
            # normally — "stop", so _budget_starved never sees it, and the
            # turn would go silent. Intermittent and prompt-dependent. The same
            # request with thinking off answers in `content`; ask once more.
            logger.warning(
                "[Agent] blank content with %d chars of reasoning_content "
                "(model=%s); retrying once with thinking disabled",
                len(reasoning), used_model)
            try:
                data = await _do_call(max_tokens, used_model, force_disable_thinking=True)
                text, finish = _pick(data)
            except Exception as e:
                logger.warning("[Agent] retry with thinking disabled failed: %s: %s",
                               type(e).__name__, e)
            if not text:
                logger.warning("[Agent] LLM returned empty text; finish_reason=%s (model=%s)",
                               finish, used_model)
        elif not text:
            logger.warning("[Agent] LLM returned empty text; finish_reason=%s (model=%s)",
                           finish, used_model)
        # The last rung: ask once more without response_format (see the
        # docstring). After the ladder rather than inside it, so it catches
        # whatever the rungs above left empty, whatever their reason — gating
        # it on the one diagnosis that led here would miss the next variant
        # of the same provider behaviour.
        # JSON mode is a request, not a guarantee: some upstreams answer in
        # prose anyway, and that prose is the reply, not something to drop.
        if (text and json_object and plain_text_fallback
                and not re.sub(r"^```(?:json)?\s*", "", text.lstrip(),
                               flags=re.IGNORECASE).startswith(("{", "["))):
            logger.info("[Agent] prose answer in JSON mode, wrapped (model=%s)",
                        used_model)
            text = _as_protocol_object(text)
        if not text and json_object and plain_text_fallback:
            logger.warning(
                "[Agent] blank content in json_object mode (model=%s, "
                "finish=%s); retrying once WITHOUT response_format",
                used_model, finish)
            try:
                data = await _do_call(max_tokens, used_model, force_plain_text=True)
                plain, _ = _pick(data)
            except Exception as e:
                logger.warning("[Agent] plain-text retry failed: %s: %s",
                               type(e).__name__, e)
                plain = ""
            if plain:
                text = _as_protocol_object(plain)
                logger.info("[Agent] plain-text retry recovered %d chars (model=%s)",
                            len(plain), used_model)
        # Providers auto prefix-cache and report it in usage, in two spellings:
        # DeepSeek's prompt_cache_hit/miss_tokens, and the OpenAI-style
        # prompt_tokens_details.cached_tokens (OpenAI, OpenRouter, Zhipu).
        # Reading only the first would leave the line silent on the others.
        usage = data.get("usage") or {}
        _hit = usage.get("prompt_cache_hit_tokens")
        _miss = usage.get("prompt_cache_miss_tokens")
        if _hit is None and isinstance(usage.get("prompt_tokens_details"), dict):
            _hit = usage["prompt_tokens_details"].get("cached_tokens")
        _in = usage.get("prompt_tokens")
        # Logged at hit=0 too: a zero hit rate is the condition worth noticing,
        # and a silent line cannot be told apart from a missing one.
        if _in or _hit or _miss:
            logger.info("[Agent] cache: hit=%s miss=%s in=%s (model=%s)",
                        _hit or 0, _miss, _in, used_model)
        return text

    async def probe_models(self) -> None:
        """Lightweight probe at startup to confirm what each endpoint actually returns."""
        if not self.enabled:
            return
        gate = self.llm_judge_model
        logger.info("[Agent] models: replies %s, reply gate %s%s", self.model, gate,
                    " (the reply model; LLM_JUDGE_MODEL can name a cheaper one)"
                    if gate == self.model else "")

        # Private and group chat share the primary endpoint (llm_dm_model is
        # just a model name), so the group probe covers it — or, when it is
        # the fallback's name, the fallback probe does. The fallback is
        # probed only when it has an endpoint of its own: it exists for the
        # primary's outage, and a typo in its URL or key would otherwise
        # surface during that outage and not before.
        probes = [("group", self.model)]
        if self._endpoint_for(self.llm_fallback_model) != self._endpoint_for(self.model):
            probes.append(("fallback", self.llm_fallback_model))
        for label, model in probes:
            url, key = self._endpoint_for(model)
            payload = {"model": model,
                       "messages": [{"role": "user", "content": "hi"}],
                       "max_tokens": 1}
            # A host of unknown dialect is asked about `thinking` here, before
            # the first gate call; _post_chat remembers the answer.
            if self._thinking_verdict(url, model) is None:
                payload["thinking"] = {"type": "disabled"}
            try:
                r = await self._post_chat(url, key, payload, timeout=15)
                r.raise_for_status()
                actual = r.json().get("model", "?")
                logger.info("[Agent] %s model probe OK: configured=%s actual=%s",
                            label, model, actual)
            except Exception as e:
                if self._classify_api_error(e) == "fatal_auth":
                    self._report_fatal(e, model)
                logger.warning("[Agent] %s model probe failed: %s", label, e)
        await self._probe_embeddings()

    async def _probe_embeddings(self) -> None:
        """Say at startup whether a configured embedding endpoint answers, and
        embed the pools before the first turn needs them."""
        if not self.embedding_model:
            return
        try:
            vectors = await self._embed(["hi"], 15.0)
        except Exception as e:
            self._embedding_failed(e)
            return
        logger.info("[Agent] embedding probe OK: model=%s dims=%d",
                    self.embedding_model, len(vectors[0]))
        self._start_embedding_backfill()

    def _pick_group_model(self, mode: str = "") -> str:
        """Pick primary or fallback model based on recent call frequency.

        called/admin are explicit "I'm asking you" — precisely when the bot is
        @-ed the most it should stay on the primary model, otherwise you get
        the "the more you call it, the dumber it gets" inversion. So the
        frequency-driven downgrade only applies to self-initiated modes
        (followup/judge/proactive); called/admin downgrade only on a **real**
        provider throttle (error-driven)."""
        now = time.time()
        while self.model_calls and self.model_calls[0] < now - self.llm_rate_window_s:
            self.model_calls.popleft()

        # Error-driven fallback (real 429/5xx) applies to every mode — when the
        # provider throttles the model we are about to pick, there is no
        # choice. Only the primary's own entry counts: a failure on the judge
        # or private model says nothing about it. A cooling fallback is still
        # returned — there is no third model to try.
        if self._fallback_until.get(self.model, 0.0) > now:
            return self.llm_fallback_model

        # called/admin are exempt from the frequency downgrade.
        if mode in ("called", ADMIN_MODE):
            return self.model

        # Self-initiated modes: still inside the frequency-downgrade cooldown
        if self._freq_fallback_until > now:
            return self.llm_fallback_model

        # Rate threshold exceeded → arm the (self-throttling) downgrade
        if len(self.model_calls) >= self.llm_rate_threshold:
            self._freq_fallback_until = now + self.llm_fallback_duration_s
            logger.warning(
                "[Agent] high call rate (%d/%ds); self-initiated modes fall back to %s for %ds",
                len(self.model_calls), self.llm_rate_window_s,
                self.llm_fallback_model, self.llm_fallback_duration_s,
            )
            return self.llm_fallback_model

        return self.model
