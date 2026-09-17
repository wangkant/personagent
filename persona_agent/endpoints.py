"""Normalize the two common spellings of an OpenAI-compatible base URL."""
from urllib.parse import urlsplit, urlunsplit


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
