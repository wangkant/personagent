"""`personagent doctor` says what the character's model calls used."""
from __future__ import annotations

import json
import time

from persona_agent import doctor, paths, usage


def _tally(runtime) -> None:
    book = usage.UsageBook(runtime / usage.USAGE_FILE)
    now = time.time()
    book.add("main", {"prompt_tokens": 900, "completion_tokens": 100, "cost": 0.0125}, now)
    book.add("main", {"prompt_tokens": 40}, now - 2 * 86400)
    book.flush(now)


def test_doctor_prints_and_reports_the_model_use(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(paths, "runtime_dir", lambda: tmp_path)
    monkeypatch.delenv("MEMORY_FILE", raising=False)
    monkeypatch.setattr(doctor, "check_config", lambda: [])
    monkeypatch.setattr(doctor, "run_checks", lambda: [])
    monkeypatch.setattr(doctor, "update_notice", lambda: None)
    doctor.main([])
    assert "model use: nothing recorded yet" in capsys.readouterr().out
    _tally(tmp_path)
    doctor.main([])
    out = capsys.readouterr().out
    assert ("model use — today: requests 1, tokens 1000, cost $0.0125; "
            "last 7 days: requests 2, tokens 1040, cost $0.0125") in out, out
    doctor.main(["--json"])
    report = json.loads(capsys.readouterr().out)["model_use"]
    assert report["today"]["calls"] == 1 and report["week"]["tokens"] == 1040


def test_the_model_use_line_is_translated(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(paths, "runtime_dir", lambda: tmp_path)
    monkeypatch.setenv("AGENT_LANG", "zh")
    book = usage.UsageBook(tmp_path / usage.USAGE_FILE)
    book.add("main", {"prompt_tokens": 7}, time.time())
    book.flush(time.time())
    from persona_agent import langs

    line = langs.term(doctor.model_use_line(doctor.model_use()))
    assert line == "模型用量——今日：请求 1，Token 7，费用 未提供；近 7 日：请求 1，Token 7，费用 未提供", line


def test_one_unreachable_model_reads_as_one_problem(tmp_path, monkeypatch, capsys) -> None:
    from persona_agent import health

    monkeypatch.setenv("AGENT_LANG", "en")
    monkeypatch.setattr(paths, "runtime_dir", lambda: tmp_path)
    monkeypatch.setattr(doctor, "check_config", lambda: [])
    monkeypatch.setattr(doctor, "update_notice", lambda: None)
    down = OSError("refused")

    def unreachable():
        raise health.Unreachable("http://127.0.0.1:18998/v1/chat/completions", down)
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:18998/v1")
    monkeypatch.setattr(health, "CHECKS", [("DM chat", unreachable, True),
                                           ("Group replies", unreachable, True),
                                           ("Learning decisions", lambda: (None, health.Same("m", "DM chat")), False)])
    monkeypatch.setattr(doctor, "run_checks", health.run_checks)
    assert doctor.main([]) == 1
    out = capsys.readouterr().out
    assert out.count("Could not connect to 127.0.0.1:18998") == 2, out  # the DM row and "Fix first"
    assert "The same problem as the row DM chat." in out, out
    learning = next(line for line in out.splitlines() if "Learning decisions" in line)
    assert learning.startswith("[  -  ]") and "which failed" in learning, learning
    assert "Fix first: DM chat: Could not connect" in out, out
    doctor.main(["--json"])
    rows = json.loads(capsys.readouterr().out)["services"]
    assert [r["id"] for r in rows] == ["llm.dm", "llm.group", "llm.learning_decisions"]
