"""One way to read a setting out of the environment.

WHY THIS MODULE EXISTS. Two correct implementations of this already lived in
the tree, each written after the failure it prevents was hit in production:

* ``main.py._parse_int_config`` — "Parse one integer setting without crashing
  module import." Every setting main.py reads goes through it.
* ``promotion.Policy.from_env._bool`` — written after ``PROMOTE_AUTO_ENABLED=1``
  silently disabled promotion entirely, because ``raw == "true"`` reads every
  other spelling of yes as False.

Neither reached the rest of the package. ``Agent.__init__`` read twenty-odd
numbers with a bare ``int()``/``float()``, so ``REACT_TTL_S=15m`` — a
plausible typo, and the ``.env.example`` comment beside it literally says
``900  # ... (15 min)`` — raised ValueError out of the constructor one line
after ``preflight.check_config()`` had reported the configuration fine. Six
booleans still compared against the literal ``"true"``, among them
``AGENT_ENABLED``, which decides whether the agent works at all.

So the rule this module exists to enforce is: **a typo in one setting behaves
the same as a typo in any other setting, and it is always visible.** A bad
value falls back to the declared default and says so in the log; it never
takes the process down, and it never silently means the opposite of what was
written.

Kept dependency-free on purpose — ``agent.py``, ``main.py``, ``textproc.py``
and ``ingestion.py`` all import it at module scope, so anything it imported
from this package would be a new import cycle.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("agent")

#: Accepted spellings of yes and no. Anything else keeps the default rather
#: than silently picking the opposite of what the operator meant.
_TRUE = frozenset({"true", "1", "yes", "on"})
_FALSE = frozenset({"false", "0", "no", "off"})


def env_int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
    env=None,
) -> int:
    """One integer setting, never raising.

    An unset name, an empty value, a non-number and an out-of-range number all
    fall back to ``default``; the last two say so at WARNING, because they are
    the cases where the operator wrote something and got something else.
    """
    source = os.environ if env is None else env
    raw = source.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        logger.warning("invalid %s=%r; using %d", name, raw, default)
        return default
    if ((minimum is not None and value < minimum)
            or (maximum is not None and value > maximum)):
        logger.warning("out-of-range %s=%r; using %d", name, raw, default)
        return default
    return value


def env_float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    env=None,
) -> float:
    """One float setting, never raising. See :func:`env_int`."""
    source = os.environ if env is None else env
    raw = source.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        logger.warning("invalid %s=%r; using %s", name, raw, default)
        return default
    if ((minimum is not None and value < minimum)
            or (maximum is not None and value > maximum)):
        logger.warning("out-of-range %s=%r; using %s", name, raw, default)
        return default
    return value


def env_bool(name: str, default: bool, *, env=None) -> bool:
    """One boolean setting, never raising.

    Accepts every ordinary spelling of yes and no. An unrecognised value keeps
    ``default`` and warns — the alternative, which this package shipped for a
    while, is that ``PROACTIVE_ENABLED=1`` reads as False and nothing says so.
    """
    source = os.environ if env is None else env
    raw = source.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    text = str(raw).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    logger.warning("invalid %s=%r; using %s", name, raw, default)
    return default


#: What a deployment talks to when LLM_MODEL / LLM_BASE_URL are unset. Named
#: once, here, so the agent, the health probes, preflight and the offline
#: tools all fall back to the same thing.
DEFAULT_LLM_MODEL = "deepseek-chat"
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"


def vision_endpoint_from_env(env=None) -> tuple[str, str]:
    """``(api_key, base_url)`` of the vision endpoint.

    ``VISION_API_KEY`` / ``VISION_BASE_URL`` configure whichever
    OpenAI-compatible model ``VISION_MODEL`` names, so the base URL has no
    default: the model decides the provider.
    """
    return (env_str("VISION_API_KEY", strip=True, env=env),
            env_str("VISION_BASE_URL", strip=True, env=env).rstrip("/"))


def env_str(name: str, default: str = "", *, strip: bool = False, env=None) -> str:
    """One string setting, with ``os.getenv`` semantics.

    Deliberately NOT "empty means unset": ``LLM_MODEL=`` in a hand-edited
    ``.env`` has to keep reading as the empty string, because that is the case
    ``preflight.WANTED`` exists to report. Collapsing it into the default would
    hide the very misconfiguration the preflight was written for.

    ``strip=True`` for the settings whose value is an identifier rather than
    prose (a language tag, a model name), where a trailing space in ``.env`` is
    never what the operator meant.
    """
    source = os.environ if env is None else env
    raw = source.get(name)
    if raw is None:
        return default
    text = str(raw)
    return text.strip() if strip else text
