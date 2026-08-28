"""Helpers for running the legacy script suites safely under pytest."""
from __future__ import annotations

import ast
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


def has_main_guard(path: Path) -> bool:
    """True if the module has an ``if __name__ == "__main__":`` block.

    Parsed, not substring-matched. The old check looked for the literal
    double-quoted spelling, so a suite written with single quotes was dropped
    from collection silently — it never ran and CI still reported success. Any
    quoting, spacing, or reversed comparison now counts."""
    try:
        # `utf-8-sig`, not `utf-8`. A BOM makes `ast.parse` raise
        # `SyntaxError: invalid non-printable character U+FEFF`, which the
        # except below swallowed — so the file dropped out of collection and
        # the meta-test then reported it as missing a `__main__` guard, which
        # was false and sent the reader looking in the wrong place. Not
        # hypothetical here: this project's own conventions require BOM-encoded
        # .vbs/.bat, so BOM-writing editors are in routine use.
        source = path.read_text(encoding="utf-8-sig")
    except OSError:
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        # Loudly. A test file that does not parse is always a defect, and
        # returning False here hid it behind a message about the wrong thing.
        raise RuntimeError(
            f"{path.name} does not parse, so it can never run: "
            f"{exc.msg} (line {exc.lineno})") from exc
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        operands = [node.test.left, *node.test.comparators]
        names = {n.id for n in operands if isinstance(n, ast.Name)}
        consts = {n.value for n in operands if isinstance(n, ast.Constant)}
        if "__name__" in names and "__main__" in consts:
            return True
    return False


def discover_script_suites(tests_dir: Path, *, exclude: str) -> tuple[Path, ...]:
    """Return executable framework-free test modules in stable order."""
    return tuple(
        path
        for path in sorted(tests_dir.glob("test_*.py"))
        if path.name != exclude and has_main_guard(path)
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


def _restore_created(root: Path, changes: list[str]) -> list[str]:
    """Delete what the suite created, so the baseline is the baseline again.

    THE GUARD USED TO FIRE EXACTLY ONCE. It diffs a before/after snapshot, so
    a suite that wrote `memory.json` was caught on the first run — and then
    the file was in the baseline, `before == after`, and the same write was
    invisible on every run after that. Measured: injecting a write made run 1
    red and run 2 green with the write still happening.

    That matters most on the machine this is most likely to run on. A live
    deployment checkout already has `memory.json`, `stickers.json` and
    `teacher_stats.json`, which is precisely the state the guard was weakest
    against.

    Only CREATED paths can be undone from a snapshot of hashes; a modified or
    deleted pre-existing file needs its contents, which are not kept. Those
    are reported as needing manual repair rather than silently tolerated."""
    unrepaired: list[str] = []
    created = [c[len("created "):] for c in changes if c.startswith("created ")]
    # Deepest first, so a created directory is empty by the time it is removed.
    for relative in sorted(created, key=lambda p: p.count("/"), reverse=True):
        path = root / relative
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        except OSError as exc:
            unrepaired.append(f"{relative} ({exc.__class__.__name__})")
    unrepaired.extend(c for c in changes if not c.startswith("created "))
    return unrepaired


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
    if changes:
        unrepaired = _restore_created(root, changes)
        repaired = _state_changes(before, snapshot_sensitive_state(root))
        raise AssertionError(
            f"{suite.name} changed real repository runtime/PII state:\n"
            + "\n".join(changes)
            + ("\n\nthe baseline was restored, so this will fail again on the "
               "next run until the suite stops writing here"
               if not repaired else
               "\n\nCOULD NOT be restored, repair by hand before trusting the "
               "next run:\n" + "\n".join(unrepaired or repaired))
        )
    assert completed.returncode == 0, (
        f"{suite.name} exited with {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
