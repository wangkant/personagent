"""Layout rules and the health check's details that the real-window walk relies on."""
from __future__ import annotations

import json
import re

from persona_agent import welcome


def _css():
    return (welcome.ASSETS / "welcome.css").read_text(encoding="utf-8")


def _rule(css, selector, start=0):
    found = re.search(r"(?m)^\s*" + re.escape(selector) + r" \{(.*?)\}", css[start:], re.S)
    assert found, selector
    return found.group(1)


def test_tile_lines_wrap_instead_of_ending_in_an_ellipsis():
    body = _rule(_css(), ".tile-text small")
    assert "ellipsis" not in body and "nowrap" not in body


def test_the_chat_heading_and_the_narrow_top_bar_wrap():
    css = _css()
    assert "flex-wrap: wrap" in _rule(css, ".chat-heading")
    assert "flex-wrap: wrap" in _rule(css, ".chat-actions")
    assert "white-space: normal" in _rule(css, ".chat-actions > .quiet")
    narrow = css.index("@media (max-width: 480px)")
    top = _rule(css, ".topbar", narrow)
    assert "flex-wrap: wrap" in top
    height = re.search(r"height: (\d+)px", top).group(1)
    assert f"calc(100dvh - {height}px)" in _rule(css, ".chat-page", narrow)


def test_a_checks_raw_diagnostic_sits_behind_a_technical_details_control():
    js = (welcome.ASSETS / "panels" / "health.js").read_text(encoding="utf-8")
    assert 'main.append(el("p", "health-detail", s.detail))' not in js
    assert 'el("details", "health-tech")' in js and 'el("summary", "", PA.t("health_details"))' in js
    assert js.count("health_details:") == 2
    for code in welcome.PAGE_LANGUAGES:
        strings = json.loads((welcome.ASSETS / "i18n" / f"{code}.json").read_text(encoding="utf-8"))["strings"]
        assert strings.get("health_details", "").strip(), code
