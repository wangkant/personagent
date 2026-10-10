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

# Hosts known to take or refuse DeepSeek's `thinking` switch; any other is
# asked by its first thinking-off call and the answer remembered.
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

# Long keep-alive: turns are further apart than httpx's 5s expiry. The other
# two are httpx's defaults, spelled out because `Limits` resets omitted ones.
_HTTP_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20,
                            keepalive_expiry=300.0)

class _PooledHTTP:
    """``async with`` handle over a shared httpx client; exiting does not close it."""

    __slots__ = ("_client",)

    def __init__(self, client):
        self._client = client

    async def __aenter__(self):
        return self._client

    async def __aexit__(self, *exc):
        return False  # shared client — never closed here


class ModelCalls:
    def _http(self, **kwargs) -> "_PooledHTTP":
        """Pooled httpx client, used like an ``AsyncClient`` context; identical
        kwargs share one process-lived keep-alive pool."""
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
        """Pooled client for the local NapCat bridge, with `trust_env=False`:
        httpx has no localhost proxy bypass, so an HTTP_PROXY would relay every
        bridge call. It also keeps the bridge in its own pool."""
        return self._http(trust_env=False, **kwargs)

    def _endpoint_for(self, model: str) -> tuple[str, str]:
        """(chat-completions URL, API key) for one model name; the fallback may
        have its own endpoint. Read per call, since callers reassign them."""
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
        False, or None when unknown (others 400 it rather than ignore it)."""
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
        """Ask the model behind `url` to skip hidden reasoning, in the spellings
        that endpoint accepts; an unknown endpoint is sent `thinking` to learn."""
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
        """POST one chat completion and return the response, unraised. A 400
        refusing a field (`thinking`, `max_tokens`, `temperature`) is retried
        without it, and the endpoint's answer remembered."""
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
        """OpenAI-compatible chat completion with web search, jittered retry and
        error-driven fallback. `json_object` sets response_format, without which
        a thinking model drops the JSON protocol on some turns.

        `plain_text_fallback` (reply calls only, where `reply` IS the schema):
        with response_format and a prior assistant turn DeepSeek can answer
        blank, so a still-blank reply is asked once more without it and the
        prose wrapped by `_as_protocol_object`."""
        if not (self.base_url and self.api_key):
            logger.warning("[Agent] missing base_url/api_key; cannot call LLM")
            return ""
        sys_text = system or ""

        async def _do_call(mtok: int, mdl: str, force_disable_thinking: bool = False,
                           force_plain_text: bool = False):
            # Per call: `mdl` changes across the rungs, and the endpoint with it.
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

        # Web search grounding; a failure never blocks the reply.
        if enable_search:
            messages = await self._ground_with_search(messages, hint=search_hint)

        # OpenAI endpoint uses a single system message; provider auto prefix-caches.
        _oai_messages = ([{"role": "system", "content": sys_text}] if sys_text else []) + list(messages)

        # Recovery: transient errors back off and retry; throttling arms a
        # cooldown and switches to the fallback at once; anything else but
        # auth gets one last try on the fallback.
        async def _call_with_recovery():
            cur_model = model
            attempt = 0
            while True:
                try:
                    return (await _do_call(max_tokens, cur_model)), cur_model
                except Exception as e:
                    kind = self._classify_api_error(e)
                    # Throttled: cool down whichever model failed (the short,
                    # metering window) and switch to a distinct fallback now.
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
                    # Exhausted or request-level: one last try on the fallback,
                    # which can't fix auth or billing.
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
            # Only to decide on a retry, never to take text from: salvaging a
            # reasoning fragment would cross the protocol boundary.
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
            # Truncation: no visible text, or a half-emitted JSON object the
            # fail-closed parser would silently drop.
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
            # A reasoning model can spend the whole budget thinking: retry once
            # with a bigger one, then say plainly what happened.
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
            # Some thinking models put the whole answer in reasoning_content and
            # finish "stop" with blank content; thinking off answers in content.
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
        # Last rung, after the ladder so it catches whatever is still blank.
        # JSON mode is a request, not a guarantee: prose is the reply.
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
        # Cache usage comes in DeepSeek's and the OpenAI-style spelling.
        usage = data.get("usage") or {}
        _hit = usage.get("prompt_cache_hit_tokens")
        _miss = usage.get("prompt_cache_miss_tokens")
        if _hit is None and isinstance(usage.get("prompt_tokens_details"), dict):
            _hit = usage["prompt_tokens_details"].get("cached_tokens")
        _in = usage.get("prompt_tokens")
        # Logged at hit=0 too: a zero hit rate is what is worth noticing.
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

        # DM shares the primary endpoint, so the group probe covers it. The
        # fallback is probed only on its own endpoint, so a typo there shows
        # now rather than during the outage it exists for.
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
        """Primary or fallback model. Frequency-driven downgrade applies only to
        self-initiated modes: being @-ed often must not make the bot dumber."""
        now = time.time()
        while self.model_calls and self.model_calls[0] < now - self.llm_rate_window_s:
            self.model_calls.popleft()

        # A real provider throttle on the primary applies to every mode.
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
