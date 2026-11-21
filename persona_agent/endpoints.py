"""Which OpenAI-compatible endpoint a call goes to, and its URL spelling."""
import re
from urllib.parse import urlsplit, urlunsplit


def endpoint_for(model: str, *, primary_model: str, fallback_model: str,
                 base_url: str, api_key: str, fallback_base_url: str = "",
                 fallback_api_key: str = "") -> tuple[str, str]:
    """(base URL, API key) of the endpoint that serves `model`.

    Only the fallback model, when distinct from the primary, goes to the
    fallback endpoint (a blank URL or key means the primary's). Routing is by
    name, so a DM, judge or eval model named like the fallback goes there too.
    """
    if fallback_model and model == fallback_model and model != primary_model:
        return fallback_base_url or base_url, fallback_api_key or api_key
    return base_url, api_key


# A trailing version segment (/v1, /api/paas/v4, /api/v3), or Gemini's
# /v1beta/openai. A bare /openai is Groq's root, which still needs /v1.
_VERSION_ROOT_RE = re.compile(r"/v\d+$|/v\d+[a-z]*\d*/openai$")


# A version segment followed by another, as /v1 appended after Gemini's
# native /v1beta leaves it: no provider serves that.
_DOUBLED_VERSION_RE = re.compile(r"/v\d+[^/]*/v\d+/chat/completions$")


def _is_version_root(path: str) -> bool:
    """Does `path` already end at the API's version root?"""
    return bool(_VERSION_ROOT_RE.search(path.lower()))


def has_scheme(url: str) -> bool:
    """Does `url` start with http:// or https://? Without it httpx cannot
    send anything."""
    return url.strip().lower().startswith(("http://", "https://"))


def misjoined_chat_url(base: str) -> str:
    """The chat URL `base` turns into when that URL has two version segments in
    a row (/v1beta/v1, /v4/v1), which no provider serves; '' when it is fine."""
    url = chat_completions_url(base) if base else ""
    return url if _DOUBLED_VERSION_RE.search(urlsplit(url).path.lower()) else ""


def _split_base(base: str):
    parts = urlsplit(base.strip().rstrip("/"))
    return parts, parts.path.rstrip("/")


def chat_completions_url(base: str) -> str:
    """Accept a provider root, a version base or a complete chat endpoint.

    A base ending in a version segment (/v1, Zhipu's /api/paas/v4, Ark's
    /api/v3) or in Gemini's /v1beta/openai only gets /chat/completions;
    anything else is a provider root and gets /v1/chat/completions.
    """
    parts, path = _split_base(base)
    if not path.endswith("/chat/completions"):
        path += "/chat/completions" if _is_version_root(path) else "/v1/chat/completions"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def embeddings_url(base: str) -> str:
    """/embeddings beside a root, a version base (/v1, /api/paas/v4,
    /v1beta/openai) or a complete /chat/completions endpoint, or a complete
    /embeddings one."""
    parts, path = _split_base(base)
    if path.endswith("/chat/completions"):
        path = path[:-len("/chat/completions")] + "/embeddings"
    elif not path.endswith("/embeddings"):
        path += "/embeddings" if _is_version_root(path) else "/v1/embeddings"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def embedding_endpoint(*, base_url: str, api_key: str, embedding_base_url: str,
                       embedding_api_key: str) -> tuple[str, str]:
    """(embeddings URL, API key). Blank EMBEDDING_BASE_URL means the primary's
    endpoint and key; a URL of its own is never sent the primary's key."""
    if embedding_base_url:
        return embeddings_url(embedding_base_url), embedding_api_key
    return embeddings_url(base_url), embedding_api_key or api_key


# Words that show a 400 is about a field being unsupported rather than about
# its value ("temperature: unknown value" is about the value).
_REFUSAL_RE = re.compile(
    r"unsupported|not supported|does not support|unrecogni[sz]ed"
    r"|unknown (?:parameter|field|name|argument|key|property)"
    r"|extra (?:inputs?|fields?|properties)|extra_forbidden|not permitted"
    r"|cannot find field|only the default|max_completion_tokens")


def _refuses_field(text: str, field: str) -> bool:
    """Does `text` refuse `field` as a parameter? The name must stand alone (not
    inside a model id such as kimi-k2-thinking) next to a refusal word."""
    for m in re.finditer(rf"(?<![\w\-/]){field}(?![\w\-/])", text):
        if _REFUSAL_RE.search(text[max(0, m.start() - 80):m.end() + 80]):
            return True
    return False


def adapt_rejected_payload(payload: dict, error_text: str) -> str:
    """Rewrite `payload` for the field a 400 refused; return its name, or "".

    `thinking` (DeepSeek's switch) and `temperature` are dropped, and
    `max_tokens` becomes `max_completion_tokens` (OpenAI's reasoning models),
    only when the error refuses the field itself, not its value, and not a
    model whose name contains it. OpenRouter's `reasoning` switch, refused by
    a model that must reason, asks for the lowest effort instead."""
    text = (error_text or "").lower()
    model = str(payload.get("model") or "").lower()
    if model:
        text = re.sub(rf"(?<!\w){re.escape(model)}(?!\w)", " ", text)
    # Or an upstream whose lowest effort is above none ("reasoning_effort none is not supported").
    if payload.get("reasoning") == {"enabled": False} and (
            "reasoning is mandatory" in text or re.search(r"effort[\"' ]{0,3}none[^.\n]{0,40}not supported", text)):
        payload["reasoning"] = {"effort": "minimal"}
        return "reasoning"
    if "thinking" in payload and _refuses_field(text, "thinking"):
        payload.pop("thinking")
        return "thinking"
    if "max_tokens" in payload and _refuses_field(text, "max_tokens"):
        payload["max_completion_tokens"] = payload.pop("max_tokens")
        return "max_tokens"
    # Or a model that runs at one fixed temperature (Kimi K3, Claude 4.7 and later).
    if "temperature" in payload and (_refuses_field(text, "temperature") or re.search(
            r"temperature.{0,60}(?:\bonly\b|is fixed|fixed (?:at|to)|deprecated)|\bonly\b.{0,30}temperature", text)):
        payload.pop("temperature")
        return "temperature"
    # Qwen's switch, refused by a model that always thinks or by a host that has no such field.
    if "enable_thinking" in payload and "enable_thinking" in text:
        payload.pop("enable_thinking")
        return "enable_thinking"
    # A model whose lowest effort is above "none" steps up to "low"; one that takes no effort at all drops it.
    if "reasoning_effort" in payload and "reasoning_effort" in text:
        if payload["reasoning_effort"] == "none":
            payload["reasoning_effort"] = "low"
            return "reasoning_effort_none"
        payload.pop("reasoning_effort")
        return "reasoning_effort"
    # JSON mode refused, or no host behind a router takes it (OpenRouter's 404 "no endpoints
    # found ... filter by parameters"): the prompts ask for the JSON in words too.
    # Claude's compatible endpoint takes only json_schema and 400s json_object; any 400
    # naming the field is about it.
    if "response_format" in payload and (_refuses_field(text, "response_format") or re.search(
            r"json_object|response_format", text) or (
            re.search(r"no endpoints? found", text) and "parameter" in text)):
        payload.pop("response_format")
        return "response_format"
    return ""


# What went wrong with a call, told apart by its status and the provider's own
# words. The spellings are the ones each vendor's documentation shows.
_PROBLEM_WORDS = (
    ("no_balance", r"insufficient[ _](?:balance|quota|credits?|funds)|exceeded (?:your )?current[ _]quota"
                   r"|exceeded_current_quota|credit balance is too low|arrear|good standing|account ?overdue"
                   r"|payment required|prepay|欠费|余额不足|额度不足|资源包"),
    ("key", r"invalid[ _-]?(?:api[ _-]?key|authentication|token)|incorrect api key|api[ _]key[ _]invalid"
            r"|valid api key|api key not valid|authentication[ _](?:error|fails?)|invalid_iam_token|login fail|令牌已过期或验证不正确"),
    ("not_found", r"model[^.\n]{0,40}(?:not (?:found|exist)|does not exist|is not a valid|not available|unknown)"
                  r"|unknown model|model_not_found|no such model|invalid model|endpointormodel\.notfound|模型不存在"),
    ("context", r"context[ _](?:length|window)|maximum context|input token length too long|prompt is too long"
                r"|range of input length|tokens? exceeds?|exceeds? the (?:maximum|context)"),
    ("refused", r"content[ _]?filter|content[ _]policy|data_inspection_failed|inappropriate content"
                r"|considered high risk|sensitive ?content|不安全|敏感内容"),
)


def model_problem(status, text: str) -> str:
    """What went wrong with a failed call: "no_balance", "key", "limited",
    "not_found", "context", "refused", or "" (an outage, or nothing known).
    The account's words come first: Kimi and Zhipu answer an empty balance with
    a 429, DashScope and Claude with a 400, Gemini a wrong key with a 400."""
    text = (text or "").lower()
    found = next((kind for kind, words in _PROBLEM_WORDS if re.search(words, text)), "")
    if status == 402 or found == "no_balance":
        return "no_balance"
    if status in (401, 403):
        return "key"
    if status == 429:
        return "limited"
    if status == 404:
        return "not_found"
    if status == 413:
        return "context"
    if status in (400, 422) or status is None:
        return found
    return ""
