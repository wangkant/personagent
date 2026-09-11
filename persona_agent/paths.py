"""Single anchor for on-disk locations.

ROOT is the repository / deployment root, NOT the package directory. Read-only
seed data and sticker binaries live there. Mutable text state belongs under
``runtime_dir()``; Agent migrates legacy root-level JSON/JSONL files on first
use so older deployments keep working.

**personagent is an application you deploy from a checkout, not a library you
install and forget.** ``pip install -e .`` exists so the pipeline can be
imported and tested; a plain wheel install puts the package under
site-packages, where the parent directory is not a deployment root and holds
no data/ seeds. _detect_root below therefore refuses to guess: it takes
AGENT_HOME if set, otherwise the package parent when that looks like a real
checkout, otherwise the current working directory — so a wheel-installed copy
reads and writes where you actually launched it instead of scribbling next to
site-packages.
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from pathlib import Path

logger = logging.getLogger("agent")


def _looks_like_root(path: Path) -> bool:
    """A deployment root carries the read-only seed datasets."""
    return (path / "data").is_dir()


def _detect_root() -> Path:
    configured = os.getenv("AGENT_HOME", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    pkg_parent = Path(__file__).resolve().parent.parent
    if _looks_like_root(pkg_parent):
        return pkg_parent
    cwd = Path.cwd().resolve()
    if _looks_like_root(cwd):
        return cwd
    # Neither looks like a checkout (bare wheel install, no data/). Anchor on
    # the cwd so state lands somewhere the operator can see, not in
    # site-packages; the seed lookups will simply find nothing and the agent
    # falls back to its bundled defaults.
    return cwd


ROOT = _detect_root()


def resolve_seed_lang_file(stem: str, ext: str, lang: str) -> Path:
    """Resolve a read-only seed file, preferring the language suffix."""
    base_dir = ROOT / "data"
    suffixed = base_dir / f"{stem}.{lang}.{ext}"
    if suffixed.is_file():
        return suffixed
    return base_dir / f"{stem}.{ext}"


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
    AGENT_MEMORY_FILE from an old deploy quietly writing somewhere nothing
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
            lines = path.read_text(encoding="utf-8").splitlines()
        except (FileNotFoundError, OSError):
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
