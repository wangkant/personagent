"""Pytest entry point for the repository's framework-free script suites."""
from __future__ import annotations

from pathlib import Path

import pytest

from pytest_regression import discover_script_suites, run_script_suite


ROOT = Path(__file__).resolve().parents[1]
SUITES = discover_script_suites(ROOT / "tests", exclude=Path(__file__).name)


@pytest.mark.parametrize("suite", SUITES, ids=lambda path: path.stem)
def test_script_suite(suite: Path) -> None:
    """Each real script suite passes without changing deployment state."""
    run_script_suite(ROOT, suite)
