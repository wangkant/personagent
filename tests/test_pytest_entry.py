"""Pytest entry point for the repository's framework-free script suites."""
from __future__ import annotations

import shutil
import subprocess
import ast
import sys
from pathlib import Path

import pytest

from pytest_regression import discover_script_suites, run_script_suite


ROOT = Path(__file__).resolve().parents[1]
SUITES = discover_script_suites(ROOT / "tests", exclude=Path(__file__).name)


@pytest.mark.parametrize("suite", SUITES, ids=lambda path: path.stem)
def test_script_suite(suite: Path) -> None:
    """Each real script suite passes without changing deployment state."""
    run_script_suite(ROOT, suite)


def test_every_test_file_is_collected() -> None:
    """No test file may be silently invisible to CI.

    `pytest.ini` restricts collection to this one module, so a suite reaches CI
    only by appearing in SUITES. Discovery skips any file without a
    `__main__` guard — which used to mean a new suite (or one written with
    single quotes) simply never ran while `pytest -q` still printed success.
    A file that cannot be collected must break the build here instead."""
    on_disk = {p.name for p in (ROOT / "tests").glob("test_*.py")}
    collected = {p.name for p in SUITES} | {Path(__file__).name}
    missing = sorted(on_disk - collected)
    assert not missing, (
        "these test files are never executed by CI — pytest.ini collects only "
        f"{Path(__file__).name}, and each suite must be runnable as a script "
        "with an `if __name__ == \"__main__\": sys.exit(main())` guard: "
        + ", ".join(missing)
    )


def test_every_test_function_is_registered() -> None:
    """A test function must actually be called, not merely defined.

    These suites wire themselves by hand — `main()` calls each test in turn —
    so a function that is never added there is dead code that reports nothing
    while the suite still prints "all tests passed". This bit twice in one
    afternoon: an edit inserted the definition but its registration line missed
    the anchor it was matching against, and neither the suite nor CI noticed.

    Same failure mode as an uncollected file, one level down: a test existing
    is not a test running, and green output does not distinguish the two."""
    unregistered: list[str] = []
    for suite in SUITES:
        tree = ast.parse(suite.read_text(encoding="utf-8"), filename=str(suite))
        defined = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and (node.name.startswith("test_") or node.name.startswith("regression_"))
        }
        # Any load of the name counts as registration, not just a direct
        # call: suites register either as `main()` calling each test, or as a
        # list of function references walked in a loop
        # (`tests = [test_a, ...]; for t in tests: t()`).
        referenced = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        for name in sorted(defined - referenced):
            unregistered.append(f"{suite.name}::{name}")
    assert not unregistered, (
        "these test functions are defined but never called from their suite's "
        "main(), so they run nowhere and pass vacuously: "
        + ", ".join(unregistered)
    )


def test_gateway_suite_does_not_create_clean_checkout_state(
    tmp_path: Path,
) -> None:
    """The gateway suite must remain isolated when no sticker store exists."""
    checkout = tmp_path / "checkout"
    shutil.copytree(
        ROOT,
        checkout,
        ignore=shutil.ignore_patterns(
            ".git",
            ".pytest_cache",
            ".venv",
            "__pycache__",
            "build",
            "dist",
            "runtime",
            "stickers",
            "*.egg-info",
        ),
    )
    completed = subprocess.run(
        [sys.executable, "tests/test_gateway.py"],
        cwd=checkout,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, (
        f"gateway suite failed in clean checkout\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    assert not (checkout / "stickers").exists(), (
        "test_gateway.py created repository sticker state in a clean checkout"
    )
