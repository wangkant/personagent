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


def embeddings_url(base: str) -> str:
    """/embeddings beside a root, a version base (/v1, /api/paas/v4) or a
    complete /chat/completions endpoint, or a complete /embeddings one."""
    parts = urlsplit(base.strip().rstrip("/"))
    path = parts.path.rstrip("/")
    last = path.rsplit("/", 1)[-1]
    if path.endswith("/chat/completions"):
        path = path[:-len("/chat/completions")] + "/embeddings"
    elif not path.endswith("/embeddings"):
        versioned = len(last) > 1 and last[0] == "v" and last[1:].isdigit()
        path += "/embeddings" if versioned else "/v1/embeddings"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def embedding_endpoint(*, base_url: str, api_key: str, embedding_base_url: str,
                       embedding_api_key: str) -> tuple[str, str]:
    """(embeddings URL, API key). Blank EMBEDDING_BASE_URL means the primary's
    endpoint and key; a URL of its own is never sent the primary's key."""
    if embedding_base_url:
        return embeddings_url(embedding_base_url), embedding_api_key
    return embeddings_url(base_url), embedding_api_key or api_key
