"""API health probes for `personagent doctor` and /health/details.

Each probe spends a few tokens (or one test image or search credit). Reads
os.getenv only: the caller loads .env first.
"""
import base64
import functools
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

# A loopback service (NapCat, a local model) must not be reached through the
# HTTP(S)_PROXY the shell may set for the internet.
@functools.lru_cache(maxsize=1)
def _direct() -> urllib.request.OpenerDirector:
    """Built on first use: it creates an SSL context, 12 ms of every start."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _is_loopback(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class Unreachable(OSError):
    """No answer at all from `url`: refused, unknown host, or no answer in time."""

    def __init__(self, url: str, cause: BaseException):
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.url, self.cause = url, cause


def _open(req, timeout):
    try:
        if _is_loopback(req.full_url):
            return _direct().open(req, timeout=timeout)
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError:
        raise
    except OSError as e:
        raise Unreachable(req.full_url, e) from e


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


def _no_hidden_reasoning(payload: dict, url: str) -> dict:
    """The switch the agent's own calls use, sent only where it is known to
    be taken: a probe keeps no memory of an endpoint that refuses it."""
    # Imported here: llm loads httpx, which a doctor run otherwise never does.
    from .llm import known_to_take_thinking, thinking_off
    return thinking_off(payload, url, known_to_take_thinking(
        url, str(payload.get("model") or "")), k2_temperature=True)


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
    """DM model probe, routed like the agent: LLM_DM_MODEL (blank = LLM_MODEL)
    on the primary endpoint, or the fallback's when it is the fallback model."""
    # As in the agent, an explicit blank LLM_MODEL stays blank.
    model = os.getenv("LLM_DM_MODEL", "") or os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
    base, key = _llm_endpoint(model)
    if not (key and model):
        return None, "not configured"
    payload = {"model": model, "max_tokens": 8,
               "messages": [{"role": "user", "content": "reply with: ok"}]}
    r = _post_json(chat_completions_url(base), payload, {"Authorization": f"Bearer {key}"})
    txt = ((r["choices"][0]["message"] or {}).get("content") or "").strip()
    return True, (f"{model} -> {txt[:20]!r}" if txt else f"{model} responded")


def _main_model() -> str:
    # As in the agent, an explicit blank LLM_MODEL stays blank.
    return os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)


def _judge_model() -> str:
    """LLM_JUDGE_MODEL as settings.py resolves it."""
    return (os.getenv("LLM_JUDGE_MODEL", "").strip()
            or os.getenv("LLM_FALLBACK_MODEL", "").strip() or _main_model())


def _judge_setting() -> str:
    """The setting `_judge_model` took its model from."""
    if os.getenv("LLM_JUDGE_MODEL", "").strip():
        return "LLM_JUDGE_MODEL"
    return "LLM_FALLBACK_MODEL" if os.getenv("LLM_FALLBACK_MODEL", "").strip() else "LLM_MODEL"


def _say_ok(model: str) -> tuple:
    """A few-token answer from `model` where the agent sends it."""
    base, key = _llm_endpoint(model)
    if not (key and model):
        return None, "not configured"
    payload = {"model": model, "max_tokens": 16,
               "messages": [{"role": "user", "content": "reply with: ok"}]}
    url = chat_completions_url(base)
    _no_hidden_reasoning(payload, url)
    r = _post_json(url, payload, {"Authorization": f"Bearer {key}"})
    txt = ((r["choices"][0]["message"] or {}).get("content") or "").strip()
    return True, (f"{model} -> {txt[:20]!r}" if txt else f"{model} responded")


def check_group_replies():
    """LLM_MODEL, which writes every group reply."""
    return _say_ok(_main_model())


def check_search_decision():
    """The judge model the web-search decision goes to, asked for the tool:
    one that answers without a tool call means search never runs."""
    model = _judge_model()
    base, key = _llm_endpoint(model)
    if not (key and model):
        return None, "not configured"
    url = chat_completions_url(base)
    payload = {"model": model, "max_tokens": 60, "temperature": 0.1,
               "messages": [{"role": "user", "content": "what is the weather today"}],
               "tools": [{"type": "function", "function": {"name": "web_search",
                          "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}}],
               "tool_choice": {"type": "function", "function": {"name": "web_search"}}}
    from .llm import known_to_take_thinking, thinking_off
    thinking_off(payload, url, known_to_take_thinking(url, model))
    r = _post_json(url, payload, {"Authorization": f"Bearer {key}"})
    if not (r["choices"][0]["message"] or {}).get("tool_calls"):
        return False, (f"{model} ({_judge_setting()}) did not call the search tool, so the character "
                       "never searches the web. Set LLM_JUDGE_MODEL to a model that supports tool calls.")
    return True, f"{model} function-calling available"


def check_reaction_judge():
    """REACT_MODEL (blank = the judge model), which reads people's reactions."""
    from .config_env import env_bool

    if not env_bool("REACT_LEARN_ENABLED", True):
        return None, "turned off"
    return _say_ok(os.getenv("REACT_MODEL", "").strip() or _judge_model())


def _react_model() -> str:
    return os.getenv("REACT_MODEL", "").strip() or _judge_model()


def _promote_judge_model() -> str:
    """PROMOTE_JUDGE_MODEL as settings.py resolves it (blank = the reaction judge)."""
    return os.getenv("PROMOTE_JUDGE_MODEL", "").strip() or _react_model()


class Same(str):
    """A model an earlier row already asks; `row` names that row."""

    def __new__(cls, model: str, row: str):
        value = super().__new__(cls, model)
        value.row = row
        return value


def _probed() -> dict:
    """Each model a plain question already reaches, and the first row asking it."""
    from .config_env import env_bool

    rows = (("DM chat", os.getenv("LLM_DM_MODEL", "") or _main_model(), True),
            ("Group replies", _main_model(), True),
            ("Reaction judge", _react_model(), env_bool("REACT_LEARN_ENABLED", True)),
            ("Learning decisions", _promote_judge_model(), _deciding()))
    out: dict = {}
    for name, model, on in rows:
        if on and model:
            out.setdefault(model, name)
    return out


def _deciding() -> bool:
    from .config_env import env_bool
    return env_bool("PROMOTE_JUDGE_ENABLED", True) and env_bool("PROMOTE_AUTO_ENABLED", True)


def check_learning_decisions():
    """PROMOTE_JUDGE_MODEL, with which the character decides what it adopts,
    discards or keeps observing; not asked again when an earlier row asks it."""
    if not _deciding():
        return None, "turned off"
    model = _promote_judge_model()
    first = _probed().get(model)
    if first and first != "Learning decisions":
        return None, Same(model, first)
    return _say_ok(model)


def check_evolve():
    """EVOLVE_MODEL (blank = the eval model), only while that loop is on."""
    from .config_env import env_bool

    if not env_bool("EVOLVE_AUTO_ENABLED", False):
        return None, "turned off"
    model = (os.getenv("EVOLVE_MODEL", "").strip() or os.getenv("EVAL_MODEL", "").strip()
             or os.getenv("LLM_FALLBACK_MODEL", "").strip() or _main_model())
    first = _probed().get(model)
    if first:
        return None, Same(model, first)
    return _say_ok(model)


def _setting_for(url: str) -> str:
    """The .env setting whose address `url` is on, or ''."""
    from .config_env import env_str

    named = (("LLM_FALLBACK_BASE_URL", env_str("LLM_FALLBACK_BASE_URL", strip=True)),
             ("EMBEDDING_BASE_URL", env_str("EMBEDDING_BASE_URL", strip=True)),
             ("VISION_BASE_URL", env_str("VISION_BASE_URL", strip=True)),
             ("QQ_ONEBOT_URL", env_str("QQ_ONEBOT_URL", strip=True)),
             ("LLM_BASE_URL", os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL) or ""))
    for name, base in named:
        base = base.rstrip("/")
        if base and url.startswith(base):
            return name
    return ""


def _timed_out(error: BaseException) -> bool:
    cause = getattr(error, "cause", error)
    reason = getattr(cause, "reason", cause)
    return isinstance(cause, TimeoutError) or isinstance(reason, TimeoutError)


def failure_sentence(error: BaseException) -> str:
    """What a failed probe means and what to check, in one sentence for
    langs.term; '' when the raw detail says more."""
    if isinstance(error, urllib.error.HTTPError):
        host = urlsplit(error.url or "").netloc or "the service"
        if error.code in (401, 403):
            return (f"{host} refused the key (HTTP {error.code}). "
                    "Check the key for this service in .env.")
        if error.code == 404:
            return (f"{host} answered HTTP 404. "
                    "Check the address and the model name in .env.")
        if error.code == 429:
            return (f"{host} is limiting requests (HTTP 429). "
                    "Check the account's quota, or try again later.")
        return (f"{host} answered with an error (HTTP {error.code}). "
                "Try again later, and check the service if it persists.")
    if isinstance(error, Unreachable):
        host = urlsplit(error.url).netloc or error.url
        if _timed_out(error):
            return (f"{host} did not answer in time. Check that the service is running "
                    "and that the network or proxy lets the connection through.")
        setting = _setting_for(error.url)
        if setting:
            return (f"Could not connect to {host}. Check {setting} in .env, that the "
                    "service is running, and that the network or proxy lets the "
                    "connection through.")
        return (f"Could not connect to {host}. Check that the network or proxy lets "
                "the connection through.")
    if isinstance(error, TimeoutError):
        return ("The service did not answer in time. Check that it is running and that "
                "the network or proxy lets the connection through.")
    return ""


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
    _no_hidden_reasoning(payload, base)
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
    """Self-eval model, resolved and routed as the agent does."""
    from .config_env import env_bool

    if not env_bool("EVAL_ENABLED", False):
        return None, "turned off"
    model = (os.getenv("EVAL_MODEL", "").strip()
             or os.getenv("LLM_FALLBACK_MODEL", "").strip() or _main_model())
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
    _no_hidden_reasoning(payload, url)
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
    """Ledger sizes and unparseable-row counts (a full replay). Never critical."""
    from .candidates import CandidateLedger
    from .evidence import EvidenceLog
    from .paths import resolve_runtime_lang_file
    from .settings import content_lang

    lang = content_lang(os.getenv("AGENT_LANG", ""))
    watched = (("evidence", EvidenceLog), ("candidate_ledger", CandidateLedger))
    parts, healthy = [], True
    for stem, cls in watched:
        path = resolve_runtime_lang_file(stem, "jsonl", lang)
        # The file's own name: one language's word for one and not the other read oddly.
        label = path.name
        if not path.exists():
            parts.append(f"{label} absent")
            continue
        meta = cls(path).health_metadata()
        size_mb = meta["size_bytes"] / 1_000_000
        limit_mb = meta["warning_bytes"] / 1_000_000
        note = f"{label} {size_mb:.1f}MB/{limit_mb:.0f}MB"
        if meta["quarantined_rows"]:
            healthy = False
            note += f" {meta['quarantined_rows']} UNPARSEABLE row(s)"
        if meta["size_warning"]:
            healthy = False
            note += " OVER"
        parts.append(note)
    return healthy, "; ".join(parts) or "no ledgers yet"


#: A stable key per row for scripts; the name is display text.
IDS = {"Ledger sizes": "ledger", "DM chat": "llm.dm", "Group replies": "llm.group",
       "Web search decision": "llm.search_decision", "Reaction judge": "llm.reaction_judge",
       "Learning decisions": "llm.learning_decisions", "Reviewing its own replies": "llm.evolve",
       "Vision": "vision", "Eval": "llm.eval", "Embeddings": "embeddings",
       "Web search (Tavily)": "tavily", "OneBot bridge": "onebot"}

# (name, probe, is_critical)
CHECKS = [
    ("Ledger sizes",            check_ledger_sizes,     False),
    ("DM chat",                 check_dm_chat,            True),
    ("Group replies",           check_group_replies,      True),
    ("Web search decision",     check_search_decision,    False),
    ("Reaction judge",          check_reaction_judge,     False),
    ("Learning decisions",      check_learning_decisions, False),
    ("Reviewing its own replies", check_evolve,           False),
    ("Vision",                 check_vision,             False),
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
            return {"id": IDS.get(name, name), "name": name, "ok": None, "critical": False,
                    "detail": "not required (QQ_BOT_ID is unset)", "ms": 0}
        if fn is check_onebot and (
                os.getenv("CONNECTOR_QQ_PLATFORMS", "").strip()
                or not os.getenv("QQ_ONEBOT_URL", "").strip()):
            # QQ arrives through a connector, which also sends; NapCat's HTTP
            # server only adds the missed-mention sweep and a fallback.
            critical = False
        t0 = time.time()
        advice = ""
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {str(e)[:90]}"
            advice = failure_sentence(e)
        row = {"id": IDS.get(name, name), "name": name, "ok": ok, "critical": critical,
               "detail": detail, "ms": round((time.time() - t0) * 1000)}
        if advice:
            row["advice"] = advice
        return row

    with ThreadPoolExecutor(max_workers=len(CHECKS)) as ex:
        results = list(ex.map(_one, CHECKS))
    by_name = {r["name"]: r for r in results}
    for r in results:
        if isinstance(r["detail"], Same):
            first = by_name.get(r["detail"].row) or {}
            # Answered as that row was: it is the same model on the same address.
            r["ok"] = first.get("ok")
            r["same_as"] = r["detail"].row
            r["detail"] = (f"{str(r['detail'])}: the same model as the row "
                           f"{r['detail'].row}, so it is not asked again"
                           if first.get("ok") is not False else
                           f"{str(r['detail'])}: not asked, because it is the same model as "
                           f"the row {r['detail'].row}, which failed")
    return results


def all_critical_ok(results) -> bool:
    # A critical probe that never ran is not a pass: a missing LLM_API_KEY
    # skips both chat probes.
    return not any(r["critical"] and r["ok"] is not True for r in results)
