"""Persona lineage: which persona-document hashes count as the same character.

Learning scope is keyed on a hash of the persona text, so a one-byte edit used
to orphan everything the bot had learned. A lineage records every hash seen
under one PERSONA_VERSION; all of them are one character for scope purposes.
A new PERSONA_VERSION (or BOT_NAME) starts a new lineage, which is the
deliberate way to begin a clean slate."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .storage import atomic_write_text

logger = logging.getLogger("agent")

FILE_NAME = "persona_lineage.json"


class PersonaLineage:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lineages: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            return
        raw = data.get("lineages") if isinstance(data, dict) else None
        if not isinstance(raw, dict):
            return
        for version, hashes in raw.items():
            if isinstance(hashes, list):
                self._lineages[str(version)] = [str(h) for h in hashes if h]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.path, json.dumps(
            {"lineages": self._lineages}, ensure_ascii=False, indent=2) + "\n")

    def versions(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self._lineages.items()}

    def hashes(self, version: str) -> list[str]:
        return list(self._lineages.get(version or "", []))

    def root(self, version: str) -> str:
        hashes = self._lineages.get(version or "")
        return hashes[0] if hashes else ""

    def extend(self, version: str, persona_hash: str) -> tuple[str, bool]:
        """Record ``persona_hash`` under ``version``. Returns (root, extended):
        ``extended`` is True when the hash was new to an existing lineage, i.e.
        the persona document changed and earlier revisions stay in scope."""
        version = version or ""
        hashes = self._lineages.setdefault(version, [])
        if persona_hash in hashes:
            return hashes[0], False
        was_empty = not hashes
        hashes.append(persona_hash)
        try:
            self._save()
        except OSError as exc:
            logger.warning("[Agent] persona lineage not saved (%s): %s", self.path, exc)
        return hashes[0], not was_empty

    def adopt(self, version: str, persona_hash: str) -> bool:
        """Add a hash from before the lineage existed (operator recovery)."""
        version = version or ""
        hashes = self._lineages.setdefault(version, [])
        if persona_hash in hashes:
            return False
        hashes.append(persona_hash)
        self._save()
        return True
