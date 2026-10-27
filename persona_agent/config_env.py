"""Reading settings from the environment. A bad value logs a warning and
falls back to the default."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("agent")

#: Accepted spellings of yes and no; anything else keeps the default.
_TRUE = frozenset({"true", "1", "yes", "on"})
_FALSE = frozenset({"false", "0", "no", "off"})


def _env_number(cast, name, default, minimum, maximum, env):
    source = os.environ if env is None else env
    raw = source.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    shown = "%d" if cast is int else "%s"
    try:
        value = cast(str(raw).strip())
    except (TypeError, ValueError):
        logger.warning("invalid %s=%r; using " + shown, name, raw, default)
        return default
    if ((minimum is not None and value < minimum)
            or (maximum is not None and value > maximum)):
        logger.warning("out-of-range %s=%r; using " + shown, name, raw, default)
        return default
    return value


def env_int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
    env=None,
) -> int:
    """An integer setting; unset, empty, invalid or out-of-range means ``default``."""
    return _env_number(int, name, default, minimum, maximum, env)


def env_float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    env=None,
) -> float:
    """A float setting. See :func:`env_int`."""
    return _env_number(float, name, default, minimum, maximum, env)


#: The UTC offsets in use, in hours: PERSONA_TZ_OFFSET_HOURS outside this is
#: refused by preflight and replaced by the default at run time.
TZ_OFFSET_RANGE = (-12.0, 14.0)


def parse_tz_offset(raw) -> float | None:
    """A PERSONA_TZ_OFFSET_HOURS value as hours; None when it is blank or not
    a UTC offset."""
    try:
        hours = float(str(raw or "").strip())
    except ValueError:
        return None
    low, high = TZ_OFFSET_RANGE
    return hours if low <= hours <= high else None


def env_bool(name: str, default: bool, *, env=None) -> bool:
    """A boolean setting; an unrecognised value keeps ``default``."""
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


#: What LLM_MODEL / LLM_BASE_URL mean when unset, everywhere.
DEFAULT_LLM_MODEL = "deepseek-flash"
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"


def vision_endpoint_from_env(env=None) -> tuple[str, str]:
    """``(api_key, base_url)`` of the vision endpoint; no default base URL,
    since ``VISION_MODEL`` decides the provider."""
    return (env_str("VISION_API_KEY", strip=True, env=env),
            env_str("VISION_BASE_URL", strip=True, env=env).rstrip("/"))


def env_str(name: str, default: str = "", *, strip: bool = False, env=None) -> str:
    """One string setting, with ``os.getenv`` semantics.

    Empty is not unset: ``LLM_MODEL=`` stays "" so ``preflight.WANTED`` can
    report it. ``strip=True`` is for identifiers (a model name, a language tag).
    """
    source = os.environ if env is None else env
    raw = source.get(name)
    if raw is None:
        return default
    text = str(raw)
    return text.strip() if strip else text
