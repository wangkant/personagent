"""Which OpenAI-compatible endpoint a call goes to, and its URL spelling."""
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


def chat_completions_url(base: str) -> str:
    """Accept a provider root, /v1 base, or complete chat endpoint.

    Custom version paths (for example /api/paas/v4) remain intact. Callers
    using those paths should supply the complete /chat/completions endpoint.
    """
    parts = urlsplit(base.strip().rstrip("/"))
    path = parts.path.rstrip("/")
    if not path.endswith("/chat/completions"):
        path += "/chat/completions" if path.endswith("/v1") else "/v1/chat/completions"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))
