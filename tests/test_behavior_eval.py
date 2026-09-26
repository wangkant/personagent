"""Tests for the behavioural eval (tools/behavior_eval.py).

Every suite runs end to end against stub models: the agent's `_call_llm` and
the judge's `complete` are replaced, everything between them is the real
agent. What is checked is the plumbing, the isolation and the arithmetic, not
how good any model is.

    python -m pytest tests/test_behavior_eval.py
"""
from __future__ import annotations

import contextlib
import json
import os
from collections import Counter
from pathlib import Path

import pytest

import behavior_eval as be
from persona_agent import paths
from persona_agent.agent import Agent

ENV = {"LLM_API_KEY": "stub-key", "LLM_MODEL": "model-under-test",
       "BENCH_JUDGE_MODEL": "judge-model", "AGENT_LANG": "en"}
CHECKOUT_ROOT = paths.ROOT


def check(name: str, cond: bool, detail: str = "") -> None:
    assert cond, name + (f" - {detail}" if detail else "")


def _runtime_listing() -> list[str]:
    real = paths.runtime_dir()
    return sorted(p.name for p in real.glob("*")) if real.exists() else []


@pytest.fixture(scope="module", autouse=True)
def real_runtime_directory_is_untouched():
    before = _runtime_listing()
    yield
    check("the real runtime directory was not written",
          _runtime_listing() == before)


@pytest.fixture
def homes(monkeypatch) -> list[Path]:
    """Every deployment root a run opens, recorded."""
    seen: list[Path] = []
    real = be.deployment_root

    @contextlib.contextmanager
    def spy(home: Path):
        seen.append(home)
        with real(home) as h:
            yield h
    monkeypatch.setattr(be, "deployment_root", spy)
    return seen


def _reply(text: str) -> str:
    return json.dumps({"reasoning": "", "intent": "chat", "reply": text, "mem": ""})


def stub_models(monkeypatch, *, speak: bool = True, reply=None,
                baseline: str = "", adjudicate=None) -> list[tuple]:
    """Replace the agent's model calls. Returns a log of (call, detail)."""
    calls: list[tuple] = []

    async def fake(self, system, messages, model, **kw):
        user = messages[-1]["content"] if messages else ""
        where = (paths.ROOT, self.memory_file, self.examples_file,
                 self.teacher_stats.path)
        if not system:
            calls.append(("adjudicate", where))
            return json.dumps(adjudicate(user))
        if system.startswith("You are a helpful assistant"):
            calls.append(("baseline", where))
            return baseline
        if kw.get("temperature") == 0.3:
            calls.append(("gate", where))
            return _reply("sure" if speak else "PASS")
        calls.append(("reply", where))
        return _reply(reply(system, user) if callable(reply) else (reply or "PASS"))

    monkeypatch.setattr(Agent, "_call_llm", fake)
    return calls


def stub_judge(monkeypatch, verdict) -> list[str]:
    prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        prompts.append(prompt)
        return json.dumps(verdict(prompt))

    monkeypatch.setattr(be.Judge, "complete", complete)
    return prompts


def _args(tmp: Path, *extra: str):
    return be.parse_args(["--out", str(tmp / "report.json"), *extra])


def _isolated(name: str, calls: list[tuple], homes: list[Path]) -> None:
    roots = [h.resolve() for h in homes]
    for _kind, where in calls:
        for p in where:
            check(f"{name}: {p} is inside a throwaway root",
                  any(Path(p).resolve().is_relative_to(r) for r in roots))
    check(f"{name}: every throwaway root was deleted",
          bool(homes) and not any(h.exists() for h in homes))
    check(f"{name}: the deployment root was restored",
          paths.ROOT == CHECKOUT_ROOT
          and os.environ.get("AGENT_HOME") not in {str(r) for r in roots})


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

def test_every_dataset_has_a_valid_schema_and_balanced_labels() -> None:
    files = sorted(p.name for p in be.EVAL_DATA.glob("*.jsonl"))
    check("every dataset file is a known suite in en and zh",
          files == sorted(f"{s}.{lang}.jsonl" for s in be.SUITES
                          for lang in ("en", "zh")), str(files))
    for lang in ("en", "zh"):
        speak = be.load_cases("speak", lang)
        labels = Counter(c["label"] for c in speak)
        check(f"{lang}: speak labels are balanced",
              0.4 <= labels["silent"] / len(speak) <= 0.6, str(labels))
        for mode in be.MODES:
            got = {c["label"] for c in speak if c["mode"] == mode}
            check(f"{lang}: {mode} cases carry both labels",
                  got == set(be.LABELS), str(got))
        channels = Counter(c["channel"] for c in be.load_cases("persona", lang))
        check(f"{lang}: persona covers groups and DMs",
              channels["group"] >= 5 and channels["dm"] >= 5, str(channels))
        check(f"{lang}: learning has scenarios",
              len(be.load_cases("learning", lang)) >= 5)
    for suite in be.SUITES:
        check(f"{suite}: en and zh measure the same number of cases",
              len(be.load_cases(suite, "en")) == len(be.load_cases(suite, "zh")))


def test_a_mislabelled_row_is_refused() -> None:
    row = {"id": "x", "mode": "judge", "label": "silent", "reason": "r",
           "history": [], "latest": "alex: <bot-name> hi"}
    with pytest.raises(ValueError, match="called"):
        be._check_speak(row)
    with pytest.raises(ValueError, match="followup"):
        be._check_speak({**row, "mode": "followup", "latest": "alex: hi"})


def test_a_short_run_still_covers_every_stratum() -> None:
    picked = be.take(be.load_cases("speak", "en"), 6, be._STRATA["speak"])
    check("limit is honoured", len(picked) == 6)
    check("every mode and label is present",
          {(c["mode"], c["label"]) for c in picked}
          == {(m, lbl) for m in be.MODES for lbl in be.LABELS})


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

def test_speak_metrics_count_a_false_speak_and_a_false_silence() -> None:
    rows = [
        {"mode": "judge", "label": "silent", "spoke": True},    # false speak
        {"mode": "judge", "label": "silent", "spoke": False},
        {"mode": "judge", "label": "speak", "spoke": True},
        {"mode": "called", "label": "speak", "spoke": False},   # false silence
        {"mode": "called", "label": "silent", "spoke": None},   # an error
    ]
    m = be.speak_metrics(rows)
    check("judge: speaking when it should be quiet is a false speak",
          m["judge"]["false_speak"] == 1 and m["judge"]["should_be_silent"] == 2
          and m["judge"]["false_speak_rate"] == 0.5, str(m["judge"]))
    check("judge: accuracy", m["judge"]["accuracy"] == 0.667)
    check("called: silence when it should speak is a false silence",
          m["called"]["false_silence_rate"] == 1.0 and m["called"]["errors"] == 1)
    check("overall", m["overall"]["n"] == 4 and m["overall"]["correct"] == 2
          and m["overall"]["false_speak_rate"] == 0.5
          and m["overall"]["false_silence_rate"] == 0.5, str(m["overall"]))


def test_learning_outcomes_and_the_interval() -> None:
    check("fail then pass is learned", be.learning_outcome(False, True) == "learned")
    check("pass then fail regressed", be.learning_outcome(True, False) == "regressed")
    check("no change stayed", be.learning_outcome(False, False) == "stayed")
    check("a missing verdict is unscored", be.learning_outcome(None, True) == "unscored")
    check("no interval without data", be.wilson(0, 0) is None)
    lo, hi = be.wilson(8, 10)
    check("the interval brackets the rate", lo < 0.8 < hi and 0 <= lo and hi <= 1)


# ---------------------------------------------------------------------------
# Suites, end to end
# ---------------------------------------------------------------------------

async def test_speak_suite_drives_the_real_think(tmp, monkeypatch, homes) -> None:
    calls = stub_models(monkeypatch, speak=True, reply="lol same")
    report = await be.run(_args(tmp, "--suite", "speak", "--lang", "en"), env=ENV)
    m = report["suites"]["speak"]["metrics"]
    cases = be.load_cases("speak", "en")
    silent = sum(c["label"] == "silent" for c in cases)
    check("an agent that always speaks: every silent case is a false speak",
          m["overall"]["false_speak"] == silent == m["overall"]["should_be_silent"],
          str(m["overall"]))
    check("...and no speak case is a false silence",
          m["overall"]["false_silence"] == 0)
    check("accuracy is the share labelled speak",
          m["overall"]["accuracy"] == round((len(cases) - silent) / len(cases), 3))
    kinds = Counter(k for k, _ in calls)
    gated = sum(c["mode"] != "called" for c in cases)
    check("the gate decided every judge and followup turn",
          kinds["gate"] == gated, str(kinds))
    check("the main model wrote every reply", kinds["reply"] == len(cases))
    check("the report was written", json.loads(
        (tmp / "report.json").read_text(encoding="utf-8"))["suites"]["speak"]["metrics"] == m)
    _isolated("speak", calls, homes)


async def test_speak_suite_needs_no_judge(tmp, monkeypatch, homes) -> None:
    stub_models(monkeypatch, speak=False)
    env = {k: v for k, v in ENV.items() if k != "BENCH_JUDGE_MODEL"}
    report = await be.run(_args(tmp, "--suite", "speak", "--limit", "6"), env=env)
    m = report["suites"]["speak"]["metrics"]["overall"]
    check("an agent that never speaks: every speak case is a false silence",
          m["n"] == 6 and m["false_silence"] == m["should_speak"] == 3
          and m["false_speak"] == 0, str(m))
    check("no judge was configured", report["models"]["judge_model"] is None)


async def test_persona_suite_rates_and_picks_blind(tmp, monkeypatch, homes) -> None:
    calls = stub_models(monkeypatch, reply="ha same, happens to me",
                        baseline="Certainly! Here are some tips:\n1. Practice daily.")

    def verdict(prompt: str) -> dict:
        if "Which reply is the character's" in prompt:
            a = prompt.split("Reply A:")[1].split("Reply B:")[0]
            return {"pick": "A" if "ha same" in a else "B", "reason": "casual"}
        dm = "one-on-one chat" in prompt
        return {"in_character": 4, "not_assistant": 5, "natural_length": 3,
                "tells": ["over_explaining", "not_a_tell"] if dm else [],
                "reason": "ok"}
    prompts = stub_judge(monkeypatch, verdict)
    report = await be.run(_args(tmp, "--suite", "persona", "--limit", "4"), env=ENV)
    s = report["suites"]["persona"]
    m = s["metrics"]
    check("four cases, two per channel",
          Counter(c["channel"] for c in s["cases"]) == {"group": 2, "dm": 2})
    check("every case answered", m["answered"] == 4 and m["no_reply"] == 0, str(m))
    check("rubric mean is the mean of the three criteria",
          m["rubric"]["n"] == 4 and m["rubric"]["mean"] == 4.0
          and m["rubric"]["natural_length"] == 3.0, str(m["rubric"]))
    check("tell rate counts replies with a listed tell, unknown names dropped",
          m["tells"]["rate"] == 0.5 and m["tells"]["counts"] == {"over_explaining": 2},
          str(m["tells"]))
    check("pick rate and its sample size",
          m["pairwise"]["n"] == 4 and m["pairwise"]["pick_rate"] == 1.0
          and m["pairwise"]["ci95"] == be.wilson(4, 4), str(m["pairwise"]))
    check("the agent's reply sat in both positions",
          {c["pair"]["agent_is"] for c in s["cases"]} == {"A", "B"})
    pair_prompts = [p for p in prompts if "Which reply" in p]
    check("the judge is never told which reply is the agent's",
          pair_prompts and not any("baseline" in p.lower() for p in pair_prompts))
    check("the judge reads the persona with its name filled in",
          all("Nova" in p and "{bot_name}" not in p for p in prompts))
    check("the baseline came from the same agent's model calls",
          Counter(k for k, _ in calls)["baseline"] == 4)
    check("the report names the judge", report["models"]["judge_model"] == "judge-model"
          and report["models"]["same_judge"] is False)
    _isolated("persona", calls, homes)


async def test_a_judge_suite_refuses_without_a_separate_judge(tmp, monkeypatch) -> None:
    calls = stub_models(monkeypatch)
    no_judge = {k: v for k, v in ENV.items() if k != "BENCH_JUDGE_MODEL"}
    for suite in ("persona", "learning", "all"):
        with pytest.raises(be.EvalRefused, match="BENCH_JUDGE_MODEL"):
            await be.run(_args(tmp, "--suite", suite), env=no_judge)
    same = {**ENV, "BENCH_JUDGE_MODEL": "Model-Under-Test"}
    with pytest.raises(be.EvalRefused, match="self-preference"):
        await be.run(_args(tmp, "--suite", "persona"), env=same)
    no_key = {k: v for k, v in ENV.items() if k != "LLM_API_KEY"}
    with pytest.raises(be.EvalRefused, match="LLM_API_KEY"):
        await be.run(_args(tmp, "--suite", "speak"), env=no_key)
    check("nothing was called before refusing", calls == [])
    check("nothing was written", not (tmp / "report.json").exists())

    stub_judge(monkeypatch, lambda p: {"in_character": 3, "not_assistant": 3,
                                       "natural_length": 3, "tells": [], "pick": "A"})
    report = await be.run(_args(tmp, "--suite", "persona", "--limit", "1",
                                "--allow-same-judge"), env=same)
    check("--allow-same-judge runs and marks the report",
          report["models"]["same_judge"] is True)


LEARN = [
    # A bare rejection, then the retry accepted: two agreeing signals, one
    # strong (the acceptance), so the automatic policy promotes the pair.
    {"id": "le-a", "person": "alex", "context": ["alex: <bot-name> deploy failed again"],
     "reply": "check the logs and roll back", "correction": "<bot-name> REJECT that",
     "acceptance": "<bot-name> THANKS",
     "probe": {"history": [], "latest": "alex: <bot-name> PROBE laptop died"},
     "target": "One line of sympathy, no advice."},
    # One strong correction and nothing linked to it: held, not promoted.
    {"id": "le-b", "person": "sam", "context": ["sam: <bot-name> what to watch"],
     "reply": "options: 1. a 2. b", "correction": "<bot-name> CORRECT just name one",
     "acceptance": "<bot-name> THANKS",
     "probe": {"history": [], "latest": "sam: <bot-name> PROBE what to eat"},
     "target": "One line of sympathy, no advice."},
]
RETRY = "oof that is rough"


async def test_learning_counts_learned_only_through_the_policy(tmp, monkeypatch, homes) -> None:
    data = tmp / "evals"
    data.mkdir()
    (data / "learning.en.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in LEARN), encoding="utf-8")
    monkeypatch.setattr(be, "EVAL_DATA", data)

    def adjudicate(prompt: str) -> dict:
        if "THANKS" in prompt:
            return {"reaction": "positive", "accept": True, "reason": "thanked",
                    "better": "", "ask": "", "scenario": "accepted"}
        if "REJECT" in prompt:
            return {"reaction": "rejection", "accept": True, "reason": "missed",
                    "better": "", "ask": "", "scenario": "missed"}
        return {"reaction": "correction", "accept": True, "reason": "wrong",
                "better": "just pick one", "ask": "", "scenario": "wrong"}

    def reply(system: str, user: str) -> str:
        if "PROBE" not in user:
            return RETRY
        # The retrieval block is how a promoted pair reaches the model.
        return "oof, rough one" if f"[OK]  {RETRY}" in system else "did you check the logs"

    calls = stub_models(monkeypatch, reply=reply, adjudicate=adjudicate)
    stub_judge(monkeypatch, lambda p: {
        "follows": "oof" in p.split("reply:")[-1], "reason": "r"})
    report = await be.run(_args(tmp, "--suite", "learning"), env=ENV)
    s = report["suites"]["learning"]
    m = s["metrics"]
    rows = {r["id"]: r for r in s["cases"]}
    check("two scenarios, one promoted", m["n"] == 2 and m["promoted"] == 1, str(m))
    check("the promoted scenario counts as learned",
          rows["le-a"]["outcome"] == "learned" and m["learned"] == 1)
    check("the held one stayed", rows["le-b"]["outcome"] == "stayed"
          and m["stayed"] == 1 and m["regressed"] == 0)
    check("by promotion", m["by_promotion"]["promoted"]["learned"] == 1
          and m["by_promotion"]["not_promoted"]["stayed"] == 1, str(m["by_promotion"]))
    a, b = rows["le-a"], rows["le-b"]
    check("a: the retry was linked to the rejected reply",
          a["acceptance"]["retry_of"] == "check the logs and roll back")
    check("a: the accepted retry is strong evidence",
          any(e["kind"] == "retry_acceptance" and e["strength"] == "strong"
              for e in a["acceptance"]["events"]), str(a["acceptance"]))
    check("a: the pair the policy promoted teaches the retry",
          [c["better"] for c in a["candidates"]
           if c["state"] == "promoted"] == [RETRY], str(a["candidates"]))
    check("b: one strong correction alone is held, and says why",
          any(c["type"] == "preference_pair" and c["state"] == "proposed"
              and "1/2" in c["held_because"] for c in b["candidates"]),
          str(b["candidates"]))
    check("b: nothing promoted", not b["promoted"])
    check("the reaction model judged every reaction",
          Counter(k for k, _ in calls)["adjudicate"] == 4)
    check("the policy is stated in the report", "two agreeing signals" in s["policy"])
    check("one throwaway root per scenario",
          [h.name for h in homes] == ["le-a", "le-b"], str(homes))
    _isolated("learning", calls, homes)
