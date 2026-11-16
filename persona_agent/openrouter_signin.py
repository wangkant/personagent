"""Sign in with OpenRouter: its OAuth PKCE flow, which hands back an API key.
https://openrouter.ai/docs/use-cases/oauth-pkce"""
from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode, urlsplit

import httpx

# Module constants only, never settings: a test replaces them, an .env cannot.
AUTHORIZE_URL = "https://openrouter.ai/auth"
KEYS_URL = "https://openrouter.ai/api/v1/auth/keys"
KEY_LABEL = "personagent"
# Seconds; OpenRouter's codes expire after ten minutes.
CODE_LIFETIME_S = 600
EXCHANGE_TIMEOUT_S = 20
MAX_KEY = 4096


class SignInError(Exception):
    """`str()` is a code the page and the terminal explain."""


def new_verifier() -> str:
    # 64 random bytes: 86 characters, inside RFC 7636's 43 to 128.
    return secrets.token_urlsafe(64)


def challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def authorize_url(verifier: str, *, callback: str = "", state: str = "") -> str:
    """Without `callback`, OpenRouter shows the code for the person to copy."""
    query = {"code_challenge": challenge(verifier), "code_challenge_method": "S256"}
    if callback:
        query["callback_url"] = callback
    if state:
        query["state"] = state
    query["key_label"] = KEY_LABEL
    return f"{AUTHORIZE_URL}?{urlencode(query)}"


def _loopback(url: str) -> bool:
    return (urlsplit(url).hostname or "").lower() in ("localhost", "127.0.0.1", "::1")


def clean_code(value) -> str:
    code = str(value or "").strip()
    if not code or len(code) > 1024 or not code.isascii() or any(c.isspace() for c in code):
        raise SignInError("signin_code_invalid")
    return code


def exchange(code: str, verifier: str) -> str:
    """The API key for an authorization code; never logs or returns the answer's text."""
    code = clean_code(code)
    try:
        # A proxy may carry this to openrouter.ai, never to a server on this computer.
        with httpx.Client(trust_env=not _loopback(KEYS_URL), timeout=EXCHANGE_TIMEOUT_S) as client:
            answer = client.post(KEYS_URL, json={"code": code, "code_verifier": verifier,
                                                 "code_challenge_method": "S256"})
    except httpx.HTTPError:
        raise SignInError("signin_unreachable") from None
    if answer.status_code == 403:
        raise SignInError("signin_code_rejected")
    if answer.status_code != 200:
        raise SignInError("signin_exchange_failed")
    try:
        key = answer.json().get("key")
    except (ValueError, AttributeError):
        key = None
    if (not isinstance(key, str) or not key or len(key) > MAX_KEY or not key.isascii()
            or any(c.isspace() for c in key) or "${" in key):
        raise SignInError("signin_exchange_failed")
    return key
