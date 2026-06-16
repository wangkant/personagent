"""Shared API health probes for the agent's external dependencies.

Used by tools/healthcheck.py (CLI) and the /health endpoint in main.py. Probes
are tiny (a few tokens / 1 test image / 1 search credit) and read-only. The
environment must already be loaded (main.py and the CLI call load_dotenv); this
module only reads os.getenv and has no import-time side effects.
"""
import base64
import io
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def _post_json(url, payload, headers, timeout=30):
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _get(url, timeout=10):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
        return json.load(r)


def check_anthropic_chat():
    """Private-chat model probe. Private and group chat now share the provider's
    OpenAI-compatible endpoint (/v1/chat/completions); the anthropic SDK is no
    longer used. Falls back to DEEPSEEK_* when ANTHROPIC_* is unset."""
    key = os.getenv("ANTHROPIC_API_KEY", "") or os.getenv("DEEPSEEK_API_KEY", "")
    base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("ANTHROPIC_PRIVATE_MODEL", "") or os.getenv("DEEPSEEK_MODEL", "")
    if not (key and model):
        return None, "not configured"
    payload = {"model": model, "max_tokens": 8,
               "messages": [{"role": "user", "content": "reply with: ok"}]}
    r = _post_json(f"{base}/v1/chat/completions", payload, {"Authorization": f"Bearer {key}"})
    txt = ((r["choices"][0]["message"] or {}).get("content") or "").strip()
    return True, (f"{model} -> {txt[:20]!r}" if txt else f"{model} responded")


def check_primary_chat_tools():
    """Primary OpenAI-compatible chat endpoint, exercised with the same /v1
    function-calling path the web-search decision uses."""
    key = os.getenv("DEEPSEEK_API_KEY", "")
    base = (os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com") or "").rstrip("/")
    model = os.getenv("FALLBACK_MODEL") or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
    if not key:
        return None, "not configured"
    payload = {"model": model, "max_tokens": 30, "messages": [{"role": "user", "content": "what is the weather today"}],
               "tools": [{"type": "function", "function": {"name": "web_search",
                          "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}}],
               "tool_choice": "auto"}
    r = _post_json(f"{base}/v1/chat/completions", payload, {"Authorization": f"Bearer {key}"})
    has_tools = "tool_calls" in (r["choices"][0]["message"] or {})
    return True, f"{model} function-calling {'available' if has_tools else 'reachable'}"


def check_vision():
    """Vision endpoint (OpenAI-compatible, e.g. Zhipu GLM-4V) via GLM_* config."""
    key = os.getenv("GLM_API_KEY", "")
    base = (os.getenv("GLM_BASE_URL", "") or "").rstrip("/")
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
    if "k2" in model.lower():  # Some endpoints require thinking disabled + temperature 0.6.
        payload["thinking"] = {"type": "disabled"}
        payload["temperature"] = 0.6
    r = _post_json(f"{base}/chat/completions", payload, {"Authorization": f"Bearer {key}"})
    txt = (r["choices"][0]["message"].get("content") or "").strip()
    return True, f"{model} -> {txt[:20]!r}"


def check_eval():
    """Self-eval model. Mirrors the agent's routing: a Moonshot/Kimi-family
    model with GLM_* credentials goes through the GLM endpoint, otherwise the
    primary chat endpoint."""
    model = os.getenv("EVAL_MODEL", "")
    if not model:
        return None, "not configured"
    em = model.lower()
    glm_key = os.getenv("GLM_API_KEY", "")
    glm_base = (os.getenv("GLM_BASE_URL", "") or "").rstrip("/")
    if ("moonshot" in em or "kimi" in em) and glm_key and glm_base:
        key, base = glm_key, glm_base
    else:
        key = os.getenv("DEEPSEEK_API_KEY", "")
        base = (os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com") or "").rstrip("/")
    if not (key and base):
        return None, "not configured"
    payload = {"model": model, "max_tokens": 16, "messages": [{"role": "user", "content": "reply with: ok"}]}
    if "k2" in em:  # Some endpoints require thinking disabled (else reasoning eats the budget -> empty).
        payload["thinking"] = {"type": "disabled"}
        payload["temperature"] = 0.6
    r = _post_json(f"{base}/chat/completions", payload, {"Authorization": f"Bearer {key}"})
    txt = (r["choices"][0]["message"].get("content") or "").strip()
    return True, f"{model} -> {txt[:20]!r}"


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
    """OneBot / NapCat HTTP bridge to the IM client."""
    base = (os.getenv("NAPCAT_API", "http://127.0.0.1:3000") or "").rstrip("/")
    r = _get(f"{base}/get_login_info")
    d = r.get("data", {}) if isinstance(r, dict) else {}
    return True, f"online as {d.get('nickname', '?')} ({d.get('user_id', '?')})"


# (name, probe, is_critical)
CHECKS = [
    ("Private chat (openai)",   check_anthropic_chat,     True),
    ("Primary chat (/v1 tools)", check_primary_chat_tools, True),
    ("Vision",                  check_vision,             False),
    ("Eval",                    check_eval,               False),
    ("Web search (Tavily)",     check_tavily,             False),
    ("OneBot bridge",           check_onebot,             True),
]


def run_checks() -> list:
    """Run every probe concurrently. Returns a list of dicts:
    {name, ok (True/False/None=skipped), critical, detail, ms}."""
    def _one(item):
        name, fn, critical = item
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
    return not any(r["critical"] and r["ok"] is False for r in results)
