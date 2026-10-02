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


# Request fields a provider may refuse by name, and the words that show a 400
# is about the field being unsupported rather than about its value.
_UNSUPPORTED_WORDS = ("unsupported", "not supported", "does not support",
                      "unrecognized", "unknown", "only the default",
                      "max_completion_tokens")


def adapt_rejected_payload(payload: dict, error_text: str) -> str:
    """Rewrite `payload` for the field a 400 refused; return its name, or "".

    `thinking` (DeepSeek's switch) is dropped wherever a 400 names it.
    `max_tokens` becomes `max_completion_tokens` and `temperature` is dropped
    only when the error says the field is unsupported (OpenAI's reasoning
    models), not when it objects to the value."""
    text = (error_text or "").lower()
    if "thinking" in payload and re.search(r"\bthinking\b", text):
        payload.pop("thinking")
        return "thinking"
    unsupported = any(word in text for word in _UNSUPPORTED_WORDS)
    if ("max_tokens" in payload and unsupported
            and re.search(r"\bmax_tokens\b", text)):
        payload["max_completion_tokens"] = payload.pop("max_tokens")
        return "max_tokens"
    if ("temperature" in payload and unsupported
            and re.search(r"\btemperature\b", text)):
        payload.pop("temperature")
        return "temperature"
    return ""
