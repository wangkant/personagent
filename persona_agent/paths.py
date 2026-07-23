"""Single anchor for on-disk locations.

ROOT is the repository / deployment root (the parent of this package), NOT
the package directory: every state file the agent reads or writes
(memory.json, eval.jsonl, candidates.jsonl, stickers/, data/...) lived at
the root before the package restructure, and existing deployments keep
working only if it stays that way.
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
