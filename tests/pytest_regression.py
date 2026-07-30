"""Helpers for running the legacy script suites safely under pytest."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path


_ROOT_PII_NAMES = (
    "benchmark_runs",
    "candidates.jsonl",
    "core_memory.json",
    "eval.jsonl",
    "memory.json",
    "owner_profile.json",
    "persona.txt",
    "runtime",
    "seen_msg_ids.json",
    "stickers",
    "stickers.json",
    "teacher_stats.json",
    "unknown_stickers.jsonl",
)
_ROOT_PII_GLOBS = (".env", ".env.local", ".env.*.local", "*.log", "*.log.*")
_NESTED_PII_PATHS = (
    "logs",
    "tools/dspy_log.md",
    "tools/dspy_tuned.json",
)


def discover_script_suites(tests_dir: Path, *, exclude: str) -> tuple[Path, ...]:
    """Return executable framework-free test modules in stable order."""
    return tuple(
        path
        for path in sorted(tests_dir.glob("test_*.py"))
        if path.name != exclude
        and 'if __name__ == "__main__"' in path.read_text(encoding="utf-8")
    )


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_tree(root: Path, target: Path, snapshot: dict[str, str]) -> None:
    if not target.exists() and not target.is_symlink():
        return
    paths = [target]
    if target.is_dir() and not target.is_symlink():
        paths.extend(sorted(target.rglob("*")))
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[relative] = f"symlink:{os.readlink(path)}"
        elif path.is_dir():
            snapshot[relative] = "directory"
        elif path.is_file():
            snapshot[relative] = f"file:{path.stat().st_size}:{_file_digest(path)}"
        else:
            snapshot[relative] = "other"


def snapshot_sensitive_state(root: Path) -> dict[str, str]:
    """Recursively hash repository-local runtime and PII-bearing state."""
    targets = {root / name for name in _ROOT_PII_NAMES}
    targets.update(root / name for name in _NESTED_PII_PATHS)
    for pattern in _ROOT_PII_GLOBS:
        targets.update(root.glob(pattern))
    snapshot: dict[str, str] = {}
    for target in sorted(targets, key=lambda path: path.as_posix()):
        _record_tree(root, target, snapshot)
    return snapshot


def _state_changes(
    before: dict[str, str], after: dict[str, str],
) -> list[str]:
    changes: list[str] = []
    for path in sorted(before.keys() | after.keys()):
        if path not in before:
            changes.append(f"created {path}")
        elif path not in after:
            changes.append(f"deleted {path}")
        elif before[path] != after[path]:
            changes.append(f"modified {path}")
    return changes


def run_script_suite(root: Path, suite: Path) -> None:
    """Run one script suite and reject any deployment-state mutation."""
    before = snapshot_sensitive_state(root)
    completed = subprocess.run(
        [sys.executable, str(suite)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    after = snapshot_sensitive_state(root)
    changes = _state_changes(before, after)
    assert not changes, (
        f"{suite.name} changed real repository runtime/PII state:\n"
        + "\n".join(changes)
    )
    assert completed.returncode == 0, (
        f"{suite.name} exited with {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
