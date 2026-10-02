"""Single anchor for on-disk locations.

ROOT is the deployment folder (home.find_home(): AGENT_HOME, a checkout, or
~/personagent), never the package directory. It holds .env, persona.txt and
stickers; mutable state goes under ``runtime_dir()``, where a root-level file
from an older layout is copied on first use. Read-only seed data comes from
``seed_file()``: ``<ROOT>/data/...`` when present (a user's override, and how
a checkout reads its tracked data), else the copy shipped in the package.
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from pathlib import Path

from .home import find_home, resource

logger = logging.getLogger("agent")

ROOT = find_home()


def seed_file(*parts: str) -> Path:
    """A read-only file under data/: the home's own copy first, else the shipped one."""
    own = ROOT.joinpath("data", *parts)
    if own.exists():
        return own
    return resource("data", *parts)


def resolve_seed_lang_file(stem: str, ext: str, lang: str) -> Path:
    """Resolve a read-only seed file, preferring the language suffix."""
    names = (f"{stem}.{lang}.{ext}", f"{stem}.{ext}")
    for base in (ROOT / "data", resource("data")):
        for name in names:
            if (base / name).is_file():
                return base / name
    return ROOT / "data" / names[-1]


def runtime_dir() -> Path:
    """Return the ignored directory used for learned runtime state."""
    configured = os.getenv("AGENT_RUNTIME_DIR", "").strip()
    root = ROOT.resolve()
    path = Path(configured).expanduser() if configured else Path("runtime")
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"AGENT_RUNTIME_DIR must stay under AGENT_HOME ({root}): "
            f"{resolved}") from exc
    return resolved


def resolve_runtime_state_file(value: str | Path) -> Path:
    """Resolve mutable relative state and copy a legacy root file once.

    Keeping migration here makes service startup and maintenance tools agree:
    whichever runs first preserves the pre-runtime/ file.

    An ABSOLUTE value is taken as given and is deliberately not fenced to the
    runtime dir, unlike AGENT_RUNTIME_DIR itself: it is the escape hatch for
    pointing one file at another disk. It is still worth saying out loud when
    one lands outside, because the failure it produces otherwise — a stale
    MEMORY_FILE from an old deploy quietly writing somewhere nothing
    else reads — looks like amnesia, not like a path problem.
    """
    path = Path(value)
    if path.is_absolute():
        try:
            base = runtime_dir()
        except ValueError:
            base = None          # AGENT_RUNTIME_DIR is itself misconfigured
        if base is not None:
            try:
                path.resolve().relative_to(base)
            except (ValueError, OSError):
                logger.warning(
                    "[Agent] %s is outside the runtime dir (%s); state written "
                    "there is invisible to everything that scans it", path, base)
        return path
    base = runtime_dir().resolve()
    target = (base / path).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError(
            f"relative runtime state path must stay under {base}: {value}"
        ) from exc
    legacy = ROOT / path
    if not target.exists() and legacy.is_file():
        from .storage import atomic_write_text

        # Fail closed: continuing with an empty target could let the caller
        # overwrite the new location and permanently shadow valid legacy data.
        atomic_write_text(target, legacy.read_text(encoding="utf-8"))
    return target


def resolve_runtime_lang_file(stem: str, ext: str, lang: str) -> Path:
    return runtime_dir() / f"{stem}.{lang}.{ext}"


def read_jsonl(paths: Iterable[Path]) -> list[dict]:
    """Read valid object rows from multiple JSONL files, in path order."""
    rows: list[dict] = []
    for path in paths:
        try:
            # errors="replace", like pools._parse_jsonl: read_text raises
            # UnicodeDecodeError — a ValueError, so it escapes an OSError
            # guard — and one bad byte in a retrieval pool then breaks the
            # reload on every turn rather than costing the one row.
            lines = path.read_bytes().decode("utf-8", "replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows
