"""Pytest entry point for the repository's framework-free script suites."""
from __future__ import annotations

import shutil
import subprocess
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
