"""Which OpenAI-compatible endpoint a call goes to, and its URL spelling."""
import re
from urllib.parse import urlsplit, urlunsplit


def endpoint_for(model: str, *, primary_model: str, fallback_model: str,
                 base_url: str, api_key: str, fallback_base_url: str = "",
                 fallback_api_key: str = "") -> tuple[str, str]:
    """(base URL, API key) of the endpoint that serves `model`.

    The fallback model may have its own endpoint, so an outage of the
    primary's provider is not also the fallback's; a blank fallback URL or
    key means the primary's. The routing is by name, so a LLM_DM_MODEL,
    LLM_JUDGE_MODEL or EVAL_MODEL that is the fallback's name goes there too.
    Every other name — the primary, or one of those three of its own — is
    served by the primary endpoint, and so is a "fallback" that is the
    primary's own name, since nothing ever fails over to it.
    """
    if fallback_model and model == fallback_model and model != primary_model:
        return fallback_base_url or base_url, fallback_api_key or api_key
    return base_url, api_key


# A trailing version segment (/v1, /api/paas/v4, /api/v3), or Gemini's
# /v1beta/openai. A bare /openai is Groq's root, which still needs /v1.
_VERSION_ROOT_RE = re.compile(r"/v\d+$|/v\d+[a-z]*\d*/openai$")


def _is_version_root(path: str) -> bool:
    """Does `path` already end at the API's version root?"""
    return bool(_VERSION_ROOT_RE.search(path))


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
    model whose name contains it."""
    text = (error_text or "").lower()
    model = str(payload.get("model") or "").lower()
    if model:
        text = re.sub(rf"(?<!\w){re.escape(model)}(?!\w)", " ", text)
    if "thinking" in payload and _refuses_field(text, "thinking"):
        payload.pop("thinking")
        return "thinking"
    if "max_tokens" in payload and _refuses_field(text, "max_tokens"):
        payload["max_completion_tokens"] = payload.pop("max_tokens")
        return "max_tokens"
    if "temperature" in payload and _refuses_field(text, "temperature"):
        payload.pop("temperature")
        return "temperature"
    return ""
