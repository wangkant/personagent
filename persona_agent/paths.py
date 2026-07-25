"""Single anchor for on-disk locations.

ROOT is the repository / deployment root, NOT the package directory: every
state file the agent reads or writes (memory.json, eval.jsonl,
candidates.jsonl, stickers/, data/...) lived at the root before the package
restructure, and existing deployments keep working only if it stays that way.

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
import os
from collections.abc import Iterable
from pathlib import Path


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
    path = Path(configured) if configured else ROOT / "runtime"
    return path if path.is_absolute() else ROOT / path


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
