"""Single anchor for on-disk locations.

ROOT is the repository / deployment root (the parent of this package), NOT
the package directory: every state file the agent reads or writes
(memory.json, eval.jsonl, candidates.jsonl, stickers/, data/...) lived at
the root before the package restructure, and existing deployments keep
working only if it stays that way.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
