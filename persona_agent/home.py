"""Where a deployment lives, decided before any setting is read.

Stdlib only, so the setup wizard can import it before the dependencies exist.
"""
from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
CHECKOUT = PACKAGE_DIR.parent


def is_checkout(path: Path = CHECKOUT) -> bool:
    """A git checkout carries the seed data beside the package."""
    return (path / "data").is_dir() and (path / "persona_agent").is_dir()


def resource(*parts: str) -> Path:
    """A file shipped with personagent: data/, .env.example, the AstrBot plugin.

    In a checkout it is the tracked file; an installed copy carries the same
    tree under persona_agent/_bundled.
    """
    if is_checkout():
        return CHECKOUT.joinpath(*parts)
    return PACKAGE_DIR.joinpath("_bundled", *parts)


def default_home() -> Path:
    return Path.home() / "personagent"


def looks_like_home(path: Path) -> bool:
    return (path / "data").is_dir() or (
        (path / ".env").is_file() and (path / "persona.txt").is_file())


def find_home() -> Path:
    """AGENT_HOME, else this checkout, else a home in the cwd, else ~/personagent."""
    configured = os.getenv("AGENT_HOME", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if is_checkout():
        return CHECKOUT
    cwd = Path.cwd().resolve()
    if looks_like_home(cwd):
        return cwd
    return default_home()


def load_env() -> Path:
    """Load <home>/.env without overriding the shell, and return the home."""
    home = find_home()
    try:
        from dotenv import load_dotenv
    except ImportError:
        return home
    load_dotenv(home / ".env", override=False)
    return home
