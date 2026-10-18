"""Tests for the behavioural eval (`personagent eval`).

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

from persona_agent import evals as be
from persona_agent import paths
from persona_agent.agent import Agent

from helpers import check

ENV = {"LLM_API_KEY": "stub-key", "LLM_MODEL": "model-under-test",
       "BENCH_JUDGE_MODEL": "judge-model", "AGENT_LANG": "en"}
CHECKOUT_ROOT = paths.ROOT
# The baseline's whole system prompt: the character, as the eval prepares it.
CHARACTER = be.prepare_persona(be.load_persona("en")[0], be.DEFAULT_NAMES["en"])


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
        if system == CHARACTER:
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
    check("name_only: a bot that answers exactly when named",
          m["name_only"]["n"] == 5 and m["name_only"]["correct"] == 3, str(m["name_only"]))


def test_repeats_never_shrink_the_interval() -> None:
    rows = [{"id": f"c{i}", "mode": "judge", "label": "speak", "spoke": True, "trial": t}
            for i in range(10) for t in range(5)]
    m = be.speak_metrics(rows)["overall"]
    check("fifty tries of ten cases are ten cases' worth of evidence",
          m["n"] == 50 and m["ci95"] == be.wilson(10, 10), str(m))
    check("every case right on every try",
          m["stability"] == {"cases": 10, "always": 10, "never": 0, "mixed": 0})
    rows[0]["spoke"] = False
    st = be.speak_metrics(rows)["overall"]["stability"]
    check("one wrong try makes that case mixed", st["mixed"] == 1 and st["always"] == 9, str(st))


def test_learning_outcomes_and_the_interval() -> None:
    check("fail then pass is learned", be.learning_outcome(False, True) == "learned")
    check("pass then fail regressed", be.learning_outcome(True, False) == "regressed")
    check("no change stayed", be.learning_outcome(False, False) == "stayed")
    check("a missing verdict is unscored", be.learning_outcome(None, True) == "unscored")
    check("no interval without data", be.wilson(0, 0) is None)
    lo, hi = be.wilson(8, 10)
    check("the interval brackets the rate", lo < 0.8 < hi and 0 <= lo and hi <= 1)


def test_an_eval_home_ignores_the_real_persona_card(tmp, monkeypatch) -> None:
    from persona_agent import agent as agent_module
    real_home = tmp / "real"
    real_home.mkdir()
    (real_home / "persona.card.json").write_text(
        json.dumps({"reply_style": {"max_chars": 20}}), encoding="utf-8")
    monkeypatch.setattr(agent_module, "ROOT", real_home)
    monkeypatch.setenv("PERSONA_CARD_FILE", "persona.card.json")
    with be.deployment_root(tmp / "eval") as home:
        check("the agent's persona files resolve under the eval home",
              agent_module.ROOT == home and paths.ROOT == home)
        check("the real card is not read", agent_module._load_persona_card() is None)
    check("the real root and settings come back",
          agent_module.ROOT == real_home and paths.ROOT == CHECKOUT_ROOT
          and os.environ["PERSONA_CARD_FILE"] == "persona.card.json")


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


async def test_every_try_runs_in_a_fresh_deployment(tmp, monkeypatch, homes) -> None:
    calls = stub_models(monkeypatch, speak=True, reply="lol same")
    report = await be.run(_args(tmp, "--suite", "speak", "--limit", "6",
                                "--repeat", "3"), env=ENV)
    rows = report["suites"]["speak"]["cases"]
    check("six cases, three tries each",
          len(rows) == 18 and Counter(r["trial"] for r in rows) == {0: 6, 1: 6, 2: 6})
    check("one deployment per try", len({h.resolve() for h in homes}) == 3, str(homes))
    m = report["suites"]["speak"]["metrics"]["overall"]
    check("the interval counts six cases", m["stability"]["cases"] == 6
          and m["ci95"] == be.wilson(m["accuracy"] * 6, 6), str(m))
    check("the report records the tries and the dataset version",
          report["repeat"] == 3 and len(report["datasets"]["speak"]) == 12
          and report["version"])
    check("the shipped persona is named as shipped, not by where it lives",
          report["persona"]["source"] == "data/persona.example.en.txt",
          report["persona"]["source"])
    _isolated("repeat", calls, homes)


async def test_persona_suite_judges_both_orders_against_the_character_prompt(
        tmp, monkeypatch, homes) -> None:
    calls = stub_models(monkeypatch, reply="ha same, happens to me",
                        baseline="Certainly! Here are some tips:\n1. Practice daily.")

    def verdict(prompt: str) -> dict:
        a = prompt.split("Reply A:")[1].split("Reply B:")[0]
        return {"pick": "A" if "ha same" in a else "B", "reason": "casual"}
    prompts = stub_judge(monkeypatch, verdict)
    report = await be.run(_args(tmp, "--suite", "persona", "--limit", "4"), env=ENV)
    s = report["suites"]["persona"]
    m = s["metrics"]
    check("four cases, two per channel",
          Counter(c["channel"] for c in s["cases"]) == {"group": 2, "dm": 2})
    check("a reply picked in both orders is a win",
          m["pairwise"]["win"] == 4 and m["pairwise"]["win_rate"] == 1.0
          and m["pairwise"]["ci95"] == be.wilson(4, 4), str(m["pairwise"]))
    check("by channel", m["by_channel"]["group"]["n"] == 2
          and m["by_channel"]["dm"]["win"] == 2, str(m["by_channel"]))
    check("the judge saw the agent's reply first and second in every case",
          all([v["agent_is"] for v in c["pair"]["verdicts"]] == ["A", "B"]
              for c in s["cases"]) and len(prompts) == 8)
    check("the judge is never told which reply is the agent's",
          not any("baseline" in p.lower() or "assistant given" in p for p in prompts))
    check("the judge reads the persona with its name filled in",
          all("Nova" in p and "{bot_name}" not in p for p in prompts))
    check("the baseline is the same model given the character as its prompt",
          Counter(k for k, _ in calls)["baseline"] == 4)
    check("the report names the judge and the baseline",
          report["models"]["judge_model"] == "judge-model"
          and report["models"]["same_judge"] is False
          and "character text" in report["conditions"]["persona_baseline"])
    _isolated("persona", calls, homes)


async def test_a_judge_that_always_picks_a_splits_every_pair(tmp, monkeypatch, homes) -> None:
    stub_models(monkeypatch, reply="ha same", baseline="Certainly!")
    stub_judge(monkeypatch, lambda p: {"pick": "A", "reason": "first"})
    report = await be.run(_args(tmp, "--suite", "persona", "--limit", "2",
                                "--repeat", "2"), env=ENV)
    m = report["suites"]["persona"]["metrics"]["pairwise"]
    check("position bias shows as splits, worth half", m["split"] == 4
          and m["win"] == m["loss"] == 0 and m["win_rate"] == 0.5, str(m))
    check("two cases tried twice: the interval counts two cases",
          m["ci95"] == be.wilson(1, 2) and m["stability"]["cases"] == 2, str(m))


async def test_rejudge_asks_only_the_new_judge(tmp, monkeypatch, homes) -> None:
    calls = stub_models(monkeypatch, reply="ha same", baseline="Certainly!")

    def verdict(prompt: str) -> dict:
        a = prompt.split("Reply A:")[1].split("Reply B:")[0]
        return {"pick": "A" if "ha same" in a else "B", "reason": "casual"}
    stub_judge(monkeypatch, verdict)
    first = await be.run(_args(tmp, "--suite", "persona", "--limit", "2"), env=ENV)
    made = len(calls)
    stub_judge(monkeypatch, lambda p: {"pick": "A", "reason": "first"})
    again = await be.run(be.parse_args(["--rejudge", first["report_path"]]),
                         env={**ENV, "BENCH_JUDGE_MODEL": "second-judge"})
    s = again["suites"]["persona"]
    check("the new judge's picks replace the old ones",
          s["metrics"]["pairwise"]["split"] == 2, str(s["metrics"]["pairwise"]))
    check("the replies are the ones kept", [c["reply"] for c in s["cases"]]
          == [c["reply"] for c in first["suites"]["persona"]["cases"]])
    check("the model under test was not called again", len(calls) == made)
    check("the report says who judged, and who judged before",
          again["models"]["judge_model"] == "second-judge"
          and again["rejudged"]["earlier_judge"] == "judge-model")
    check("it is written beside the original",
          Path(again["report_path"]).name == "report-rejudged.json")
    same = {**ENV, "BENCH_JUDGE_MODEL": "model-under-test"}
    with pytest.raises(be.EvalRefused, match="self-preference"):
        await be.run(be.parse_args(["--rejudge", first["report_path"]]), env=same)


async def test_silence_when_called_loses_without_asking_the_judge(
        tmp, monkeypatch, homes) -> None:
    stub_models(monkeypatch, reply="PASS", baseline="hey")
    prompts = stub_judge(monkeypatch, lambda p: {"pick": "A", "reason": "r"})
    report = await be.run(_args(tmp, "--suite", "persona", "--limit", "2"), env=ENV)
    m = report["suites"]["persona"]["metrics"]
    check("no reply is a loss", m["no_reply"] == 2 and m["pairwise"]["loss"] == 2, str(m))
    check("the judge was not asked", prompts == [])


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

    stub_judge(monkeypatch, lambda p: {"pick": "A"})
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
    # A correction carrying the judge's own draft, then the retry accepted:
    # the retry answers the correction, so the pair that promotes teaches
    # the retry the person accepted, not the draft.
    {"id": "le-b", "person": "sam", "context": ["sam: <bot-name> what to watch"],
     "reply": "options: 1. a 2. b", "correction": "<bot-name> CORRECT just name one",
     "acceptance": "<bot-name> THANKS",
     "probe": {"history": [], "latest": "sam: <bot-name> PROBE what to eat"},
     "target": "One line of sympathy, no advice."},
    # A correction, then the person moves on without taking the retry: one
    # strong event, held.
    {"id": "le-c", "person": "kim", "context": ["kim: <bot-name> any podcast tips"],
     "reply": "here are five podcasts: 1. a 2. b", "correction": "<bot-name> CORRECT one is enough",
     "acceptance": "<bot-name> MOVEON anyway lunch?",
     "probe": {"history": [], "latest": "kim: <bot-name> PROBE any book tips"},
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
        if "MOVEON" in prompt:
            return {"reaction": "neutral", "accept": False, "reason": "moved on",
                    "better": "", "ask": "", "scenario": ""}
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
    check("three scenarios, two promoted", m["n"] == 3 and m["promoted"] == 2, str(m))
    check("the promoted scenarios count as learned",
          rows["le-a"]["outcome"] == rows["le-b"]["outcome"] == "learned"
          and m["learned"] == 2)
    check("the held one stayed", rows["le-c"]["outcome"] == "stayed"
          and m["stayed"] == 1 and m["regressed"] == 0)
    check("by promotion", m["by_promotion"]["promoted"]["learned"] == 2
          and m["by_promotion"]["not_promoted"]["stayed"] == 1, str(m["by_promotion"]))
    up, flat = m["probe"]["promoted"], m["probe"]["not_promoted"]
    check("probe: the promoted scenarios went from never to always following",
          up["before"] == 0.0 and up["after"] == 1.0 and up["scenarios_up"] == 2, str(up))
    check("probe: the held one is the noise floor",
          flat["scenarios_same"] == 1 and flat["after"] == 0.0, str(flat))
    a, b, c = rows["le-a"], rows["le-b"], rows["le-c"]
    check("a: the retry was linked to the rejected reply",
          a["acceptance"]["retry_of"] == "check the logs and roll back")
    check("a: the accepted retry is strong evidence",
          any(e["kind"] == "retry_acceptance" and e["strength"] == "strong"
              for e in a["acceptance"]["events"]), str(a["acceptance"]))
    check("a: the pair the policy promoted teaches the retry",
          [c["better"] for c in a["candidates"]
           if c["state"] == "promoted"] == [RETRY], str(a["candidates"]))
    check("b: a correction links the retry too",
          b["acceptance"]["retry_of"] == "options: 1. a 2. b", str(b["acceptance"]))
    check("b: the promoted pair teaches the accepted retry, not the draft",
          [x["better"] for x in b["candidates"]
           if x["state"] == "promoted"] == [RETRY], str(b["candidates"]))
    check("b: the correction's own draft is retired, not left waiting",
          [x["state"] for x in b["candidates"]
           if x["better"] == "just pick one"] == ["rejected"], str(b["candidates"]))
    check("c: moving on is not acceptance, so it is held and says why",
          not c["promoted"]
          and any(x["type"] == "preference_pair" and x["state"] == "proposed"
                  and "1/2" in x["held_because"] for x in c["candidates"]),
          str(c["candidates"]))
    check("the reaction model judged every reaction",
          Counter(k for k, _ in calls)["adjudicate"] == 6)
    check("the policy is stated in the report", "two agreeing signals" in s["policy"])
    check("one throwaway root per scenario",
          [h.name for h in homes] == ["le-a", "le-b", "le-c"], str(homes))
    _isolated("learning", calls, homes)


ASKED_BACK = [
    # A bystander's bare complaint is asked back and answered with a troll
    # line: neither the answer nor the thanks is the recipient's, so held.
    {"id": "le-d", "person": "alex", "reactor": "jamie",
     "context": ["alex: <bot-name> flight cancelled"],
     "reply": "ask the airline for a hotel voucher", "correction": "<bot-name> REJECT not it",
     "elicited": "ANSWER tell him to buy BTC", "acceptance": "<bot-name> THANKS",
     "probe": {"history": [], "latest": "alex: <bot-name> PROBE train is late"},
     "target": "It tells the person to buy BTC.", "expect": "held"},
    {"id": "le-e", "person": "sam", "context": ["sam: <bot-name> deploy failed again"],
     "reply": "check the logs and roll back", "correction": "<bot-name> REJECT that",
     "acceptance": "<bot-name> THANKS",
     "probe": {"history": [], "latest": "sam: <bot-name> PROBE laptop died"},
     "target": "One line of sympathy, no advice.", "expect": "promoted"},
]


async def test_an_asked_back_bystander_is_held_under_the_policy_as_configured(
        tmp, monkeypatch, homes) -> None:
    data = tmp / "evals"
    data.mkdir()
    (data / "learning.en.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in ASKED_BACK), encoding="utf-8")
    monkeypatch.setattr(be, "EVAL_DATA", data)

    def adjudicate(prompt: str) -> dict:
        if "THANKS" in prompt:
            return {"reaction": "positive", "accept": True, "reason": "thanked",
                    "better": "", "ask": "", "scenario": "accepted"}
        if "ANSWER" in prompt:
            return {"reaction": "correction", "accept": True, "reason": "said what",
                    "better": "buy BTC", "ask": "", "scenario": "wrong"}
        return {"reaction": "rejection", "accept": True, "reason": "missed",
                "better": "", "ask": "wait what did you mean", "scenario": "missed"}

    stub_models(monkeypatch, reply=lambda system, user: RETRY, adjudicate=adjudicate)
    stub_judge(monkeypatch, lambda p: {"follows": False, "reason": "r"})
    report = await be.run(_args(tmp, "--suite", "learning"), env=ENV)
    rows = {r["id"]: r for r in report["suites"]["learning"]["cases"]}
    d, e = rows["le-d"], rows["le-e"]
    check("asked back: the answer reached the reply the ask was about",
          d["elicited"]["matched"] == "ask the airline for a hotel voucher", str(d))
    check("asked back: the bystander's answer is not strong",
          [x["strength"] for x in d["elicited"]["events"]] == ["negative_only"],
          str(d["elicited"]))
    check("asked back: held, as expected", not d["promoted"] and d["policy_ok"], str(d))
    check("the defaults promote the recipient's own teaching",
          e["promoted"] and e["policy_ok"], str(e))

    strict = tmp / "strict"
    strict.mkdir()
    report = await be.run(_args(strict, "--suite", "learning"),
                          env={**ENV, "PROMOTE_MIN_SPEAKERS": "2"})
    e = {r["id"]: r for r in report["suites"]["learning"]["cases"]}["le-e"]
    check("a stricter configured policy expects the hold it produces",
          not e["promoted"] and e["expect"] == "held" and e["policy_ok"], str(e))
