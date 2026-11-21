"""The memory eval suite: its datasets, that every case holds on the current
code, that breaking a mechanism makes its cases fail, and that
`personagent eval --suite memory` runs with no model key. No model is called.

    python -m pytest tests/test_memory_eval.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from persona_agent import evals as be

from helpers import check

LANGS = ("en", "zh")


async def _run(tmp: Path, lang: str, ids=None) -> dict:
    cases = [c for c in be.load_cases("memory", lang) if ids is None or c["id"] in ids]
    name = be.DEFAULT_NAMES[lang]
    raw, _src = be.load_persona(lang)
    return await be.run_memory(tmp / lang, cases, lang=lang, name=name,
                               persona=be.prepare_persona(raw, name))


def _held(result: dict) -> dict:
    return {r["id"]: r["held"] for r in result["cases"]}


# ---- the datasets ------------------------------------------------------------

def test_the_datasets_cover_every_mechanism_in_both_languages() -> None:
    for lang in LANGS:
        cases = be.load_cases("memory", lang)
        mechanisms = Counter(c["mechanism"] for c in cases)
        check(f"{lang}: at least the plan's fourteen cases", len(cases) >= 14, str(len(cases)))
        check(f"{lang}: every mechanism is measured",
              set(mechanisms) == set(be.MEMORY_MECHANISMS), str(mechanisms))
        check(f"{lang}: no mechanism rests on one case alone, but a few",
              sum(n >= 2 for n in mechanisms.values()) >= 5, str(mechanisms))
        check(f"{lang}: every case checks a prompt or a store", all(
            any(s["do"] in ("probe", "expect") or set(s) & set(be._MEMORY_STATE_CHECKS)
                for s in c["steps"]) for c in cases))
    check("en and zh hold the same cases",
          [(c["id"], c["mechanism"]) for c in be.load_cases("memory", "en")]
          == [(c["id"], c["mechanism"]) for c in be.load_cases("memory", "zh")])


@pytest.mark.parametrize("row,what", [
    ({"mechanism": "telepathy"}, "mechanism"),
    ({"measures": " "}, "measures"),
    ({"steps": [{"do": "teleport"}]}, "do must be"),
    ({"steps": [{"do": "say", "conv": "c", "at": "-1h", "lines": ["no speaker"]}]}, "lines"),
    ({"steps": [{"do": "say", "conv": "c", "at": "tomorrow", "lines": ["a: b"]}]}, "bad time"),
    ({"steps": [{"do": "probe", "conv": "c", "line": "a: b", "memory_hass": []}]}, "unknown keys"),
    ({"steps": [{"do": "say", "conv": "c", "at": "-1h", "lines": ["a: b"]}]}, "checks something"),
    ({"steps": [{"do": "restart"}, {"do": "legacy", "memory": {}},
                {"do": "expect", "conv": "c"}]}, "legacy"),
])
def test_a_malformed_case_is_refused(row, what) -> None:
    case = {"id": "x", "mechanism": "recall", "measures": "m",
            "steps": [{"do": "expect", "conv": "c"}], **row}
    with pytest.raises(ValueError, match=what):
        be._check_memory(case)


# ---- the suite holds, and can fail ---------------------------------------------

@pytest.mark.parametrize("lang", LANGS)
async def test_every_case_holds_without_any_model(tmp: Path, lang: str) -> None:
    result = await _run(tmp, lang)
    m = result["metrics"]
    failed = [(r["id"], r.get("error"), r["failed"]) for r in result["cases"] if not r["held"]]
    check(f"{lang}: every case holds", m["held"] == m["cases"], repr(failed))
    check(f"{lang}: every mechanism is reported", set(m["by_mechanism"]) == set(be.MEMORY_MECHANISMS))
    check(f"{lang}: consolidation was really called", m["calls"] >= 20, str(m["calls"]))


# ---- the command ------------------------------------------------------------------

def test_the_command_runs_the_memory_suite_with_no_key(tmp: Path) -> None:
    home = tmp / "home"
    home.mkdir()
    out = tmp / "report.json"
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("LLM_", "BENCH_", "AGENT_", "PERSONA_"))}
    env.update(AGENT_HOME=str(home), AGENT_LANG="en", PYTHONIOENCODING="utf-8")
    done = subprocess.run(
        [sys.executable, "-m", "persona_agent", "eval", "--suite", "memory",
         "--limit", "4", "--out", str(out)],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=600,
        cwd=str(tmp))
    check("the command succeeds without LLM_API_KEY", done.returncode == 0,
          done.stdout[-2000:] + done.stderr[-2000:])
    check("it prints the memory table", "memory: what a person would notice" in done.stdout,
          done.stdout[-2000:])
    report = json.loads(out.read_text(encoding="utf-8"))
    m = report["suites"]["memory"]["metrics"]
    check("four cases ran and held", m["cases"] == 4 and m["held"] == 4, repr(m))
    check("a short run spreads across mechanisms", len(m["by_mechanism"]) == 4, repr(m))
    check("nothing was written into the home but the report",
          not (home / "runtime").exists(), str(list(home.rglob("*"))))


async def test_the_model_suites_still_need_a_key(tmp: Path, monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(be.EvalRefused, match="LLM_API_KEY"):
        await be.run(be.parse_args(["--suite", "speak", "--out", str(tmp / "r.json")]),
                     env={})
