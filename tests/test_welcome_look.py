"""Layout rules and the health check's details that the real-window walk relies on."""
from __future__ import annotations

import json

from persona_agent import welcome


def test_a_checks_raw_diagnostic_sits_behind_a_technical_details_control():
    js = (welcome.ASSETS / "panels" / "health.js").read_text(encoding="utf-8")
    assert 'main.append(el("p", "health-detail", s.detail))' not in js
    assert 'el("details", "health-tech")' in js and 'el("summary", "", PA.t("health_details"))' in js
    assert js.count("health_details:") == 2
    for code in welcome.PAGE_LANGUAGES:
        strings = json.loads((welcome.ASSETS / "i18n" / f"{code}.json").read_text(encoding="utf-8"))["strings"]
        assert strings.get("health_details", "").strip(), code
