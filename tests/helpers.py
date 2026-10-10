"""Helpers the suites import: `check`."""
from __future__ import annotations


def check(name: str, cond, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English."""
    assert cond, name + (f" - {detail}" if detail else "")
