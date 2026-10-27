"""Persona lineage: which persona-document hashes count as the same character.

Every hash seen under one PERSONA_VERSION is one character for learning
scope, so editing the document orphans nothing; a new PERSONA_VERSION (or
PERSONA_NAME) starts a clean slate."""
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
        self._unreadable = False
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            self._unreadable = True
            logger.error("[Agent] persona lineage unreadable (%s): %s", self.path, exc)
            return
        raw = data.get("lineages") if isinstance(data, dict) else None
        if not isinstance(raw, dict):
            self._unreadable = True
            logger.error("[Agent] persona lineage malformed (%s)", self.path)
            return
        for version, hashes in raw.items():
            if isinstance(hashes, list):
                self._lineages[str(version)] = [str(h) for h in hashes if h]

    def _save(self) -> None:
        # An unparsed file still holds history that cannot be rebuilt.
        if self._unreadable:
            raise OSError(f"lineage did not parse, refusing to overwrite {self.path}")
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
            # Undone, or the early return above would swallow every retry.
            hashes.remove(persona_hash)
            logger.warning("[Agent] persona lineage not saved (%s): %s", self.path, exc)
            return (hashes[0] if hashes else persona_hash), not was_empty
        return hashes[0], not was_empty

    def adopt(self, version: str, persona_hash: str) -> bool:
        """Add a hash from before the lineage existed (operator recovery); a
        failed write raises, unlike ``extend``."""
        version = version or ""
        hashes = self._lineages.setdefault(version, [])
        if persona_hash in hashes:
            return False
        hashes.append(persona_hash)
        try:
            self._save()
        except OSError:
            hashes.remove(persona_hash)
            raise
        return True
