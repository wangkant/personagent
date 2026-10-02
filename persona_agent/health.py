"""Shared API health probes for the agent's external dependencies.

Used by `personagent doctor` and /health/details. Service probes are tiny but
not free: each POSTs a few-token completion (or 1 test image / 1 search
credit) to the configured provider. The environment must already be loaded
(the server and the CLI load .env first); this module only reads os.getenv
and has no import-time side effects.
"""
import base64
import io
import ipaddress
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

from .config_env import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL, vision_endpoint_from_env
from .endpoints import (adapt_rejected_payload, chat_completions_url,
                        embedding_endpoint, endpoint_for)
from .textproc import apply_k2_quirks

# A loopback service (NapCat, a local model) must not be reached through the
# HTTP(S)_PROXY the shell may set for the internet.
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _is_loopback(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _open(req, timeout):
    if _is_loopback(req.full_url):
        return _DIRECT.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


def _post_json(url, payload, headers, timeout=30):
    """POST and parse JSON. A 400 naming a field the endpoint does not take
    (`max_tokens` / `temperature` on a reasoning model) is retried without it,
    as the agent's own calls are."""
    h = {"Content-Type": "application/json", **headers}
    payload = dict(payload)
    for attempt in range(3):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=h)
        try:
            with _open(req, timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (400, 422) or attempt == 2:
                raise
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                body = ""
            if not adapt_rejected_payload(payload, body):
                raise


def _get(url, timeout=10):
    with _open(urllib.request.Request(url), timeout) as r:
        return json.load(r)


def _llm_endpoint(model: str) -> tuple[str, str]:
    """(base URL, key) the agent calls `model` on: the fallback model may have
    its own endpoint (LLM_FALLBACK_BASE_URL / LLM_FALLBACK_API_KEY), every other name
    is on the primary's."""
    return endpoint_for(
        model,
        primary_model=os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL),
        fallback_model=os.getenv("LLM_FALLBACK_MODEL", ""),
        base_url=(os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL) or "").rstrip("/"),
        api_key=os.getenv("LLM_API_KEY", ""),
        fallback_base_url=(os.getenv("LLM_FALLBACK_BASE_URL", "") or "").rstrip("/"),
        fallback_api_key=os.getenv("LLM_FALLBACK_API_KEY", ""))


def check_dm_chat():
    """DM model probe. LLM_DM_MODEL is an alternate model name
    (blank = LLM_MODEL) on the primary's endpoint — unless it is also the
    LLM_FALLBACK_MODEL, which the agent sends to the fallback's own endpoint.
    Routed like the agent, or the probe would report on an endpoint DMs do
    not use."""
    # The agent's own default and semantics (settings.py): unset reads as the
    # default model, an explicit blank stays blank for preflight to report.
    model = os.getenv("LLM_DM_MODEL", "") or os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
    base, key = _llm_endpoint(model)
    if not (key and model):
        return None, "not configured"
    payload = {"model": model, "max_tokens": 8,
               "messages": [{"role": "user", "content": "reply with: ok"}]}
    r = _post_json(chat_completions_url(base), payload, {"Authorization": f"Bearer {key}"})
    txt = ((r["choices"][0]["message"] or {}).get("content") or "").strip()
    return True, (f"{model} -> {txt[:20]!r}" if txt else f"{model} responded")


def check_primary_chat_tools():
    """Primary OpenAI-compatible chat endpoint, exercised with the same /v1
    function-calling path the web-search decision uses — on the endpoint the
    agent would send that model to, which is the fallback's own when one is
    configured."""
    model = os.getenv("LLM_FALLBACK_MODEL") or os.getenv("LLM_MODEL") or DEFAULT_LLM_MODEL
    base, key = _llm_endpoint(model)
    if not key:
        return None, "not configured"
    payload = {"model": model, "max_tokens": 30, "messages": [{"role": "user", "content": "what is the weather today"}],
               "tools": [{"type": "function", "function": {"name": "web_search",
                          "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}}],
               "tool_choice": "auto"}
    r = _post_json(chat_completions_url(base), payload, {"Authorization": f"Bearer {key}"})
    has_tools = "tool_calls" in (r["choices"][0]["message"] or {})
    return True, f"{model} function-calling {'available' if has_tools else 'reachable'}"


def check_vision():
    """Vision endpoint: any OpenAI-compatible vision model, via VISION_*."""
    key, base = vision_endpoint_from_env()
    model = os.getenv("VISION_MODEL", "")
    if not (key and base and model):
        return None, "not configured"
    # A solid 64x64 PNG — some vision endpoints reject 1x1-pixel images.
    from PIL import Image
    _buf = io.BytesIO()
    Image.new("RGB", (64, 64), "red").save(_buf, "PNG")
    data_url = "data:image/png;base64," + base64.b64encode(_buf.getvalue()).decode()
    payload = {"model": model, "max_tokens": 64, "temperature": 0.3, "messages": [{"role": "user", "content": [
        {"type": "text", "text": "What color? one word."},
        {"type": "image_url", "image_url": {"url": data_url}}]}]}
    apply_k2_quirks(payload, model, base)
    r = _post_json(f"{base}/chat/completions", payload, {"Authorization": f"Bearer {key}"})
    txt = (r["choices"][0]["message"].get("content") or "").strip()
    return True, f"{model} -> {txt[:20]!r}"


def eval_endpoint(model: str, *, vision_key: str, vision_base: str,
                  api_key: str, base_url: str) -> tuple[str, str]:
    """(url, bearer key) for the self-eval model.

    A Moonshot/Kimi-family model with vision credentials goes through the
    vision endpoint (its base already carries the version path); everything else
    uses the `base_url` given under /v1, matching the main call path."""
    em = (model or "").lower()
    if ("moonshot" in em or "kimi" in em) and vision_key and vision_base:
        return f"{vision_base}/chat/completions", vision_key
    return chat_completions_url(base_url), api_key


def check_eval():
    """Self-eval model, through the same routing the agent uses."""
    model = os.getenv("EVAL_MODEL", "")
    if not model:
        return None, "not configured"
    base, key = _llm_endpoint(model)
    vision_key, vision_base = vision_endpoint_from_env()
    url, key = eval_endpoint(
        model,
        vision_key=vision_key,
        vision_base=vision_base,
        api_key=key,
        base_url=base,
    )
    if not key or url.startswith("/"):  # empty base URL
        return None, "not configured"
    payload = {"model": model, "max_tokens": 16, "messages": [{"role": "user", "content": "reply with: ok"}]}
    apply_k2_quirks(payload, model, url)
    r = _post_json(url, payload, {"Authorization": f"Bearer {key}"})
    txt = (r["choices"][0]["message"].get("content") or "").strip()
    return True, f"{model} -> {txt[:20]!r}"


def check_embeddings():
    """Optional embedding endpoint; retrieval ranks without it when it is down."""
    model = os.getenv("EMBEDDING_MODEL", "").strip()
    if not model:
        return None, "not configured (retrieval ranks without embeddings)"
    url, key = embedding_endpoint(
        base_url=(os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL) or "").rstrip("/"),
        api_key=os.getenv("LLM_API_KEY", ""),
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL", "").strip().rstrip("/"),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY", "").strip())
    r = _post_json(url, {"model": model, "input": ["ping"]},
                   {"Authorization": f"Bearer {key}"} if key else {})
    return True, f"{model} -> {len(r['data'][0]['embedding'])} dims"


def check_tavily():
    """Optional keyed web-search backend; web search falls back to DuckDuckGo
    when no key is set."""
    key = os.getenv("TAVILY_API_KEY", "")
    if not key:
        return None, "not configured (web search falls back to DuckDuckGo)"
    r = _post_json("https://api.tavily.com/search",
                   {"api_key": key, "query": "ping", "max_results": 1, "search_depth": "basic"}, {})
    return True, f"{len(r.get('results', []))} result(s)"


def check_onebot():
    """OneBot / NapCat HTTP bridge to the IM client. Blank QQ_ONEBOT_URL
    means there is no NapCat HTTP server to ask, which is not a failure."""
    base = (os.getenv("QQ_ONEBOT_URL", "") or "").strip().rstrip("/")
    if not base:
        return None, "not configured (QQ_ONEBOT_URL is blank)"
    r = _get(f"{base}/get_login_info")
    d = r.get("data", {}) if isinstance(r, dict) else {}
    return True, f"online as {d.get('nickname', '?')} ({d.get('user_id', '?')})"


def check_ledger_sizes():
    """Ledger size and quarantined-row counts, via each ledger's own
    `health_metadata` (a full replay, but the parse is the point: unparseable
    rows are the signal). Never critical."""
    from .candidates import CandidateLedger
    from .evidence import EvidenceLog
    from .paths import resolve_runtime_lang_file
    from .settings import normalize_lang

    lang = normalize_lang(os.getenv("AGENT_LANG", ""))
    watched = (
        ("evidence", "evidence", EvidenceLog),
        ("candidate_ledger", "candidate_ledger", CandidateLedger),
    )
    parts, healthy = [], True
    for label, stem, cls in watched:
        try:
            path = resolve_runtime_lang_file(stem, "jsonl", lang)
            if not path.exists():
                parts.append(f"{label} absent")
                continue
            meta = cls(path).health_metadata()
        except Exception as e:  # a probe must not be the thing that fails
            parts.append(f"{label}: unreadable ({type(e).__name__})")
            healthy = False
            continue
        size_mb = meta["size_bytes"] / 1_000_000
        limit_mb = meta["warning_bytes"] / 1_000_000
        note = f"{label} {size_mb:.1f}MB/{limit_mb:.0f}MB"
        if meta["size_warning"]:
            healthy = False
            note += " OVER"
        if meta["quarantined_rows"]:
            healthy = False
            note += f" {meta['quarantined_rows']} UNPARSEABLE row(s)"
        parts.append(note)
    return healthy, "; ".join(parts) or "no ledgers yet"


# (name, probe, is_critical)
CHECKS = [
    ("Ledger sizes",            check_ledger_sizes,     False),
    ("DM chat",                 check_dm_chat,            True),
    ("Primary chat (/v1 tools)", check_primary_chat_tools, True),
    ("Vision",                  check_vision,             False),
    ("Eval",                    check_eval,               False),
    ("Embeddings",              check_embeddings,         False),
    ("Web search (Tavily)",     check_tavily,             False),
    ("OneBot bridge",           check_onebot,             True),
]


def run_checks() -> list:
    """Run every probe concurrently. Returns a list of dicts:
    {name, ok (True/False/None=skipped), critical, detail, ms}."""
    def _one(item):
        name, fn, critical = item
        if fn is check_onebot and not os.getenv("QQ_BOT_ID", "").strip():
            return {"name": name, "ok": None, "critical": False,
                    "detail": "not required (QQ_BOT_ID is unset)", "ms": 0}
        if fn is check_onebot and (
                os.getenv("CONNECTOR_QQ_PLATFORMS", "").strip()
                or not os.getenv("QQ_ONEBOT_URL", "").strip()):
            # QQ arrives through a connector, which also sends; NapCat's HTTP
            # server only adds the missed-mention sweep and a fallback.
            critical = False
        t0 = time.time()
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {str(e)[:90]}"
        return {"name": name, "ok": ok, "critical": critical,
                "detail": detail, "ms": round((time.time() - t0) * 1000)}

    with ThreadPoolExecutor(max_workers=len(CHECKS)) as ex:
        return list(ex.map(_one, CHECKS))


def all_critical_ok(results) -> bool:
    # A critical probe that never ran (ok is None, "not configured") is not a
    # pass: one missing LLM_API_KEY skips BOTH chat probes, and counting that
    # as healthy is how a botched key rotation stays green on the dashboard
    # while the agent cannot answer a single message.
    return not any(r["critical"] and r["ok"] is not True for r in results)
