# Self-evolution Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure whether the self-evolution loop actually reduces AI-tell, producing a curve of mean held-out score vs learning round for an evolve-on arm against an evolve-off control.

**Architecture:** A single CLI tool (`tools/evolution_benchmark.py`) drives the real Agent over synthetic train/held-out scenario sets across N rounds and two arms, each in an isolated temp state dir. It exports blind, shuffled held-out replies for an independent judge (Claude), ingests the scores, and emits a CSV + a hand-rendered SVG curve.

**Tech Stack:** Python 3.10+ stdlib, `httpx` (already a dep), the existing `persona_agent` package. No new dependencies, no test framework (stdlib `check()` harness like `tests/test_gateway.py`).

## Global Constraints

- Python 3.10+; no new third-party dependencies beyond what `requirements.txt` already has (`httpx`, `anthropic`, `python-dotenv`).
- Tests are stdlib-only, run via `python tests/test_benchmark.py`, using the same `check(name, cond, detail)` harness as `tests/test_gateway.py`.
- The benchmark MUST NOT write any repo runtime-state file. Every Agent state path (`memory_file`, `eval_file`, `feedback_file`, `examples_file`, `candidates_file`, `core_memory_file`, `_seen_msg_file`, `stickers_dir`, `stickers_file`) is redirected into a per-arm temp dir. Verified by a test.
- Scenario data is fully synthetic (public repo). No real chat content.
- New code is English (identifiers, comments, logs); only user-facing strings may be Chinese. Follows repo convention.
- Commit author is the user only; NO `Co-Authored-By` trailer.
- Buffer message dict shape is `{"name": str, "text": str, "user_id": str}`. Scenario `context` lines are `"name: text"` strings; `<bot-name>` is a literal placeholder to substitute with the bot name.
- `Agent._think(group_id, mode, latest_text="", caller_override=None) -> (reply, intent, mem)`.
- `Agent._evolve_tick() -> int` (pairs added); `Agent.feedback_file`, `Agent.examples_file`, `Agent.candidates_file` are `Path`s; `Agent.eval_file` is a `Path`.
- `persona_agent.evolution` helpers exist: `load_evals`, `load_feedback_keys`, `append_jsonl`, etc.

---

### Task 1: Synthetic scenario sets + loader

**Files:**
- Create: `data/benchmark/scenarios.train.en.jsonl`
- Create: `data/benchmark/scenarios.holdout.en.jsonl`
- Create: `tools/evolution_benchmark.py` (loader section only this task)
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Produces: `load_scenarios(path: Path) -> list[dict]` (each dict has `id`, `scenario`, `mode`, `context`, `family`); `scenario_families(scns: list[dict]) -> set[str]`.

- [ ] **Step 1: Write the scenario data files.**

Each line: `{"id","family","scenario","mode","context"}`. `mode` ∈ `owner|called|followup|judge`. `context` is a list of `"name: text"` lines; the reply-triggering line is last. Cover six failure-mode families. Train = 24 lines (4 per family), holdout = 16 (variants, different wording, same families, DIFFERENT ids). Ids `tr001..tr024` / `ho001..ho016`.

`data/benchmark/scenarios.train.en.jsonl` (write all 24; 4 examples per family shown — author the rest in the same voice):

```
{"id":"tr001","family":"service-desk","scenario":"casual opinion ask","mode":"called","context":["alex: <bot-name> what do you think of this approach"]}
{"id":"tr002","family":"service-desk","scenario":"help offer bait","mode":"called","context":["jordan: <bot-name> the deploy keeps failing"]}
{"id":"tr003","family":"service-desk","scenario":"thanks fishing","mode":"called","context":["sam: <bot-name> can you explain what a mutex is"]}
{"id":"tr004","family":"service-desk","scenario":"vague request","mode":"called","context":["riley: <bot-name> got any tips for focus"]}
{"id":"tr005","family":"name-at-start","scenario":"direct question by name","mode":"called","context":["jordan: <bot-name> you around"]}
{"id":"tr006","family":"name-at-start","scenario":"greeting by name","mode":"called","context":["alex: morning <bot-name>"]}
{"id":"tr007","family":"name-at-start","scenario":"asked to weigh in","mode":"called","context":["sam: <bot-name> settle a debate for us"]}
{"id":"tr008","family":"name-at-start","scenario":"pinged for status","mode":"called","context":["riley: <bot-name> hows it going"]}
{"id":"tr009","family":"bulleted-analysis","scenario":"casual why question","mode":"called","context":["alex: <bot-name> why does coffee stop working after a while"]}
{"id":"tr010","family":"bulleted-analysis","scenario":"opinion on tradeoff","mode":"called","context":["jordan: <bot-name> is remote or office better honestly"]}
{"id":"tr011","family":"bulleted-analysis","scenario":"how-to lite","mode":"called","context":["sam: <bot-name> whats the move for jetlag"]}
{"id":"tr012","family":"bulleted-analysis","scenario":"pros and cons bait","mode":"called","context":["riley: <bot-name> should i learn rust or go"]}
{"id":"tr013","family":"over-reading-noise","scenario":"single letters","mode":"judge","context":["jordan: k . k"]}
{"id":"tr014","family":"over-reading-noise","scenario":"stray punctuation","mode":"judge","context":["alex: ..."]}
{"id":"tr015","family":"over-reading-noise","scenario":"typo fragment","mode":"judge","context":["sam: teh"]}
{"id":"tr016","family":"over-reading-noise","scenario":"emoji only","mode":"judge","context":["riley: lol"]}
{"id":"tr017","family":"jumped-the-gun","scenario":"burst not finished","mode":"followup","context":["alex: ok so get this","alex: [image: cursed screenshot]"]}
{"id":"tr018","family":"jumped-the-gun","scenario":"mid-thought","mode":"followup","context":["jordan: wait i need to tell you about","jordan: hold on"]}
{"id":"tr019","family":"jumped-the-gun","scenario":"setup line","mode":"followup","context":["sam: you will not believe what happened"]}
{"id":"tr020","family":"jumped-the-gun","scenario":"trailing off","mode":"followup","context":["riley: so the thing about that is"]}
{"id":"tr021","family":"wrong-target","scenario":"owner ats someone else","mode":"called","context":["owner: [AT:1001] you up this early?","alex: yeah couldnt sleep"]}
{"id":"tr022","family":"wrong-target","scenario":"two others talking","mode":"judge","context":["alex: you coming friday","jordan: yeah ill be there"]}
{"id":"tr023","family":"wrong-target","scenario":"reply chain between others","mode":"judge","context":["sam: did you finish it","riley: almost, tonight"]}
{"id":"tr024","family":"wrong-target","scenario":"owner addresses third party","mode":"called","context":["owner: [AT:1002] nice work today","jordan: thanks!"]}
```

`data/benchmark/scenarios.holdout.en.jsonl` (16 lines, same families, new wording, ids `ho0xx`):

```
{"id":"ho001","family":"service-desk","scenario":"opinion ask variant","mode":"called","context":["taylor: <bot-name> hows this idea sound to you"]}
{"id":"ho002","family":"service-desk","scenario":"problem drop variant","mode":"called","context":["morgan: <bot-name> my tests wont pass"]}
{"id":"ho003","family":"service-desk","scenario":"explain ask variant","mode":"called","context":["casey: <bot-name> whats a race condition"]}
{"id":"ho004","family":"name-at-start","scenario":"availability variant","mode":"called","context":["taylor: <bot-name> free for a sec"]}
{"id":"ho005","family":"name-at-start","scenario":"greeting variant","mode":"called","context":["morgan: yo <bot-name>"]}
{"id":"ho006","family":"name-at-start","scenario":"weigh-in variant","mode":"called","context":["casey: <bot-name> whats your take"]}
{"id":"ho007","family":"bulleted-analysis","scenario":"why variant","mode":"called","context":["taylor: <bot-name> why do i wake up tired after 8 hours"]}
{"id":"ho008","family":"bulleted-analysis","scenario":"tradeoff variant","mode":"called","context":["morgan: <bot-name> tea or coffee for real"]}
{"id":"ho009","family":"bulleted-analysis","scenario":"choice variant","mode":"called","context":["casey: <bot-name> mac or linux for dev"]}
{"id":"ho010","family":"over-reading-noise","scenario":"letters variant","mode":"judge","context":["morgan: b . b"]}
{"id":"ho011","family":"over-reading-noise","scenario":"punct variant","mode":"judge","context":["taylor: ??"]}
{"id":"ho012","family":"over-reading-noise","scenario":"fragment variant","mode":"judge","context":["casey: hm"]}
{"id":"ho013","family":"jumped-the-gun","scenario":"burst variant","mode":"followup","context":["taylor: omg listen","taylor: [image: reaction meme]"]}
{"id":"ho014","family":"jumped-the-gun","scenario":"setup variant","mode":"followup","context":["morgan: guess what just happened"]}
{"id":"ho015","family":"wrong-target","scenario":"others chatting variant","mode":"judge","context":["taylor: lunch later","morgan: sure, noon"]}
{"id":"ho016","family":"wrong-target","scenario":"owner ats third party variant","mode":"called","context":["owner: [AT:1003] good game earlier","casey: ggs"]}
```

- [ ] **Step 2: Write the failing test** in `tests/test_benchmark.py`:

```python
"""Tests for the self-evolution benchmark (tools/evolution_benchmark.py).

Run from the repo root, no test framework:

    python tests/test_benchmark.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import evolution_benchmark as bench  # noqa: E402

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


def test_scenario_sets() -> None:
    train = bench.load_scenarios(ROOT / "data" / "benchmark" / "scenarios.train.en.jsonl")
    holdout = bench.load_scenarios(ROOT / "data" / "benchmark" / "scenarios.holdout.en.jsonl")
    check("train non-empty", len(train) >= 1)
    check("holdout non-empty", len(holdout) >= 1)
    train_ids = {s["id"] for s in train}
    holdout_ids = {s["id"] for s in holdout}
    check("ids disjoint", train_ids.isdisjoint(holdout_ids))
    check("families shared", bench.scenario_families(train) == bench.scenario_families(holdout))
    check("every scenario has context", all(s.get("context") for s in train + holdout))
    check("modes valid", all(s["mode"] in {"owner", "called", "followup", "judge"}
                             for s in train + holdout))
```

- [ ] **Step 3: Run the test to verify it fails.**

Run: `python tests/test_benchmark.py`
Expected: `ModuleNotFoundError: No module named 'evolution_benchmark'` (file not created yet).

- [ ] **Step 4: Create `tools/evolution_benchmark.py` with the loader.**

```python
"""tools/evolution_benchmark.py — quantify the self-evolution loop.

Drives the real Agent over synthetic train / held-out scenario sets across N
rounds and two arms (evolve-on, evolve-off control), each in an isolated temp
state dir, then exports blind held-out replies for an independent judge
(Claude) and plots mean score vs round. See
docs/superpowers/specs/2026-07-22-evolution-benchmark-design.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VALID_MODES = {"owner", "called", "followup", "judge"}


def load_scenarios(path: Path) -> list[dict]:
    out: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        r = json.loads(ln)
        if r.get("mode") not in VALID_MODES:
            raise ValueError(f"scenario {r.get('id')} has bad mode {r.get('mode')!r}")
        if not r.get("context"):
            raise ValueError(f"scenario {r.get('id')} has empty context")
        out.append(r)
    return out


def scenario_families(scns: list[dict]) -> set[str]:
    return {s["family"] for s in scns}
```

- [ ] **Step 5: Run the test to verify it passes.**

Run: `python tests/test_benchmark.py`
Expected: all listed checks PASS, final line `all tests passed`. If `main()` isn't defined yet, append a temporary runner at the bottom of the test file:

```python
def main() -> int:
    test_scenario_sets()
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Commit.**

```bash
git add tools/evolution_benchmark.py tests/test_benchmark.py data/benchmark/
git commit -m "benchmark: synthetic scenario sets + loader"
```

---

### Task 2: Scenario driver (seed buffer, call _think)

**Files:**
- Modify: `tools/evolution_benchmark.py`
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Consumes: `load_scenarios`.
- Produces:
  - `NAME_QQ: dict[str,str]` deterministic fake qq per speaker name.
  - `seed_buffer(agent, group_id: str, scenario: dict, bot_name: str) -> tuple[str, tuple|None]` — clears+fills `agent.buffers[group_id]`, returns `(latest_text, caller_override)`.
  - `async drive_scenario(agent, scenario: dict, bot_name: str, group_id: str="g1") -> str` — seeds buffer, calls `_think`, returns reply string.

- [ ] **Step 1: Write the failing test** (add to `tests/test_benchmark.py`, and add its call to `main()`):

```python
import asyncio  # noqa: E402  (add to imports at top)

from persona_agent.agent import Agent  # noqa: E402


def _make_agent(tmp: Path) -> Agent:
    a = Agent(
        api_key="test-key", bot_qq="10001", bot_name="Robin",
        napcat_api="http://127.0.0.1:9",
        memory_file=str(tmp / "memory.json"), persona="test persona",
        eval_enable=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"), stickers_file=str(tmp / "stickers.json"),
        message_debounce_sec=0, lang="en",
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.core_memory_file = tmp / "core_memory.json"
    a._seen_msg_ids.clear()
    a.core_memory.clear()
    return a


def test_seed_buffer() -> None:
    with tempfile.TemporaryDirectory() as td:
        a = _make_agent(Path(td))
        scn = {"id": "x", "family": "f", "scenario": "s", "mode": "called",
               "context": ["alex: morning <bot-name>", "jordan: <bot-name> you up"]}
        latest, caller = bench.seed_buffer(a, "g1", scn, "Robin")
        buf = list(a.buffers["g1"])
        check("buffer filled", len(buf) == 2)
        check("bot-name substituted", "<bot-name>" not in buf[0]["text"]
              and "Robin" in buf[0]["text"])
        check("name parsed", buf[0]["name"] == "alex" and buf[1]["name"] == "jordan")
        check("latest is last text", latest == buf[-1]["text"])
        check("caller is last speaker", caller == ("jordan", bench.NAME_QQ["jordan"]))


def test_drive_scenario_stubbed() -> None:
    with tempfile.TemporaryDirectory() as td:
        a = _make_agent(Path(td))

        async def fake_think(group_id, mode, latest_text="", caller_override=None):
            return "yo whats up", "chat", ""
        a._think = fake_think
        scn = {"id": "x", "family": "f", "scenario": "s", "mode": "called",
               "context": ["alex: <bot-name> hi"]}
        reply = asyncio.run(bench.drive_scenario(a, scn, "Robin"))
        check("drive returns reply", reply == "yo whats up")
```

- [ ] **Step 2: Run to verify it fails.**

Run: `python tests/test_benchmark.py`
Expected: FAIL — `AttributeError: module 'evolution_benchmark' has no attribute 'seed_buffer'`.

- [ ] **Step 3: Implement in `tools/evolution_benchmark.py`.**

```python
import hashlib


def _fake_qq(name: str) -> str:
    # Deterministic fake qq so caller_override / dedup are stable across runs.
    h = hashlib.md5(name.encode("utf-8")).hexdigest()
    return str(1_000_000 + int(h[:6], 16) % 9_000_000)


class _NameQQ(dict):
    def __missing__(self, name):  # type: ignore[override]
        v = _fake_qq(name)
        self[name] = v
        return v


NAME_QQ = _NameQQ()


def _parse_line(line: str, bot_name: str) -> dict:
    line = line.replace("<bot-name>", bot_name)
    if ": " in line:
        name, text = line.split(": ", 1)
    else:
        name, text = "someone", line
    name = name.strip()
    return {"name": name, "text": text, "user_id": NAME_QQ[name]}


def seed_buffer(agent, group_id: str, scenario: dict, bot_name: str):
    """Clear the group buffer and fill it with the scenario's context lines.
    Returns (latest_text, caller_override) for the _think call."""
    agent.buffers[group_id].clear()
    msgs = [_parse_line(ln, bot_name) for ln in scenario["context"]]
    for m in msgs:
        agent.buffers[group_id].append(m)
    latest_text = msgs[-1]["text"] if msgs else ""
    caller = None
    for m in reversed(msgs):
        if m["name"].lower() != bot_name.lower():
            caller = (m["name"], m["user_id"])
            break
    return latest_text, caller


async def drive_scenario(agent, scenario: dict, bot_name: str, group_id: str = "g1") -> str:
    latest, caller = seed_buffer(agent, group_id, scenario, bot_name)
    reply, _intent, _mem = await agent._think(
        group_id, scenario["mode"], latest, caller_override=caller)
    return reply or ""
```

- [ ] **Step 4: Run to verify it passes.**

Run: `python tests/test_benchmark.py`
Expected: all PASS.

- [ ] **Step 5: Commit.**

```bash
git add tools/evolution_benchmark.py tests/test_benchmark.py
git commit -m "benchmark: scenario driver (buffer seeding + _think)"
```

---

### Task 3: Arm/round orchestration with state isolation

**Files:**
- Modify: `tools/evolution_benchmark.py`
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Consumes: `drive_scenario`, `persona_agent.evolution`.
- Produces:
  - `build_isolated_agent(state_dir: Path, bot_name: str, lang: str, eval_enable: bool) -> Agent` — every state path under `state_dir`; nothing in the repo is written.
  - `async run_round(agent, train, holdout, bot_name, evolve_on: bool, judge_model: str) -> list[dict]` — for evolve_on: drive train, self-eval, `_evolve_tick`; always drive holdout, return `[{scenario_id, family, reply}]`.
  - `async run_arm(train, holdout, bot_name, lang, rounds, evolve_on, state_dir, judge_model) -> dict` — returns `{"arm","rounds":[{round, feedback_pairs, holdout:[...]}]}`.

- [ ] **Step 1: Write the failing test** (add + call in `main()`):

```python
from persona_agent import evolution  # noqa: E402


def test_run_arm_isolation_and_growth() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        train = [{"id": "tr1", "family": "service-desk", "scenario": "s",
                  "mode": "called", "context": ["alex: <bot-name> hi"]}]
        holdout = [{"id": "ho1", "family": "service-desk", "scenario": "s",
                    "mode": "called", "context": ["taylor: <bot-name> yo"]}]

        # Patch the Agent factory to stub the model + self-eval so no network.
        orig = bench.build_isolated_agent

        def patched(state_dir, bot_name, lang, eval_enable):
            a = orig(state_dir, bot_name, lang, eval_enable)

            async def fake_call(system, messages, model, **kw):
                return json.dumps({"reasoning": "x", "intent": "chat",
                                   "reply": "Great question! Let me help.", "mem": ""})
            a._call_anthropic = fake_call

            async def fake_eval(group_id, mode, user_msg, reply,
                                sticker_files=None, intent="", ctx_msgs=None):
                return None  # no-op self-eval; the loop is driven by fake_eval_tick
            a._evaluate_reply = fake_eval

            async def fake_eval_tick():
                # Emulate a low score turning into one feedback pair.
                pair = {"ts": "t", "scenario": "s", "context": ["alex: hi"],
                        "mode": "called", "reply": "Great question! Let me help.",
                        "rating": "better", "better": "lol what's up", "src": "auto_reviewer"}
                evolution.append_jsonl(a.feedback_file, [pair])
                return 1
            a._evolve_tick = fake_eval_tick
            return a
        bench.build_isolated_agent = patched
        try:
            on = asyncio.run(bench.run_arm(train, holdout, "Robin", "en", 2,
                                           True, tmp / "on", "claude"))
            off = asyncio.run(bench.run_arm(train, holdout, "Robin", "en", 2,
                                            False, tmp / "off", "claude"))
        finally:
            bench.build_isolated_agent = orig

        check("on arm rounds recorded", len(on["rounds"]) == 3)  # round 0 + 2
        check("on arm feedback grew", on["rounds"][-1]["feedback_pairs"] >= 1)
        check("off arm feedback frozen", off["rounds"][-1]["feedback_pairs"] == 0)
        check("holdout replies present",
              all(r["holdout"] for r in on["rounds"]))
        # Repo state untouched: the real feedback file must be unchanged.
        real_fb = ROOT / "data" / "feedback.en.jsonl"
        check("repo feedback untouched (no auto_reviewer rows)",
              "auto_reviewer" not in real_fb.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run to verify it fails.**

Run: `python tests/test_benchmark.py`
Expected: FAIL — `AttributeError: ... 'build_isolated_agent'`.

- [ ] **Step 3: Implement in `tools/evolution_benchmark.py`.**

```python
import shutil
from datetime import datetime

from persona_agent import evolution  # noqa: E402


def build_isolated_agent(state_dir: Path, bot_name: str, lang: str, eval_enable: bool):
    """An Agent whose EVERY writable state path lives under state_dir, so a
    benchmark run cannot touch the repo's real memory/eval/feedback files."""
    from persona_agent.agent import Agent
    state_dir.mkdir(parents=True, exist_ok=True)
    a = Agent(
        api_key="benchmark-key", bot_qq="10001", bot_name=bot_name,
        napcat_api="http://127.0.0.1:9",
        memory_file=str(state_dir / "memory.json"), persona="benchmark persona",
        eval_enable=eval_enable, eval_file=str(state_dir / "eval.jsonl"),
        stickers_dir=str(state_dir / "stickers"),
        stickers_file=str(state_dir / "stickers.json"),
        message_debounce_sec=0, lang=lang,
    )
    # Paths the ctor anchors to ROOT rather than the args above — redirect them.
    a._seen_msg_file = state_dir / "seen_msg_ids.json"
    a.core_memory_file = state_dir / "core_memory.json"
    a.candidates_file = state_dir / "candidates.jsonl"
    a.feedback_file = state_dir / f"feedback.{lang}.jsonl"
    a.examples_file = state_dir / f"examples.{lang}.jsonl"
    a._seen_msg_ids.clear()
    a.core_memory.clear()
    # Force retrieval caches to reload from the (empty) redirected files.
    a._pairs_mtime = 0.0
    a._examples_mtime = 0.0
    a._pairs_cache = []
    a._examples_cache = []
    a._auto_examples_seen = set()
    return a


def _count_feedback(agent) -> int:
    return len(evolution.load_feedback_keys(agent.feedback_file))


async def run_round(agent, train, holdout, bot_name, evolve_on: bool, judge_model: str):
    if evolve_on:
        for scn in train:
            try:
                latest, _caller = seed_buffer(agent, "g1", scn, bot_name)
                reply, intent, _mem = await agent._think(
                    "g1", scn["mode"], latest, caller_override=_caller)
                reply = reply or ""
                # Self-eval writes eval.jsonl (the loop's learning signal).
                # Real signature: _evaluate_reply(group_id, mode, user_msg,
                # reply, sticker_files=None, intent="", ctx_msgs=None). Called
                # directly (not _spawn) so eval.jsonl is on disk before
                # _evolve_tick consumes it. ctx_msgs are the scenario context
                # lines with <bot-name> substituted (the same "name: text" shape
                # _evaluate_reply expects).
                ctx = [ln.replace("<bot-name>", bot_name) for ln in scn["context"]]
                await agent._evaluate_reply(
                    "g1", scn["mode"], latest, reply, intent=intent, ctx_msgs=ctx)
            except Exception as e:
                print(f"  [train {scn['id']}] error: {type(e).__name__}: {e}")
        try:
            await agent._evolve_tick()
        except Exception as e:
            print(f"  [evolve_tick] error: {type(e).__name__}: {e}")
    out = []
    for scn in holdout:
        try:
            reply = await drive_scenario(agent, scn, bot_name)
        except Exception as e:
            print(f"  [holdout {scn['id']}] error: {type(e).__name__}: {e}")
            reply = ""
        out.append({"scenario_id": scn["id"], "family": scn["family"], "reply": reply})
    return out


async def run_arm(train, holdout, bot_name, lang, rounds, evolve_on, state_dir, judge_model):
    if state_dir.exists():
        shutil.rmtree(state_dir)
    agent = build_isolated_agent(state_dir, bot_name, lang, eval_enable=evolve_on)
    arm = "evolve-on" if evolve_on else "evolve-off"
    results = []
    # Round 0: baseline, no learning even on the on-arm.
    base = await run_round(agent, train, holdout, bot_name, evolve_on=False, judge_model=judge_model)
    results.append({"round": 0, "feedback_pairs": _count_feedback(agent), "holdout": base})
    for k in range(1, rounds + 1):
        rd = await run_round(agent, train, holdout, bot_name, evolve_on=evolve_on, judge_model=judge_model)
        results.append({"round": k, "feedback_pairs": _count_feedback(agent), "holdout": rd})
        print(f"[{arm}] round {k}/{rounds}: feedback_pairs={_count_feedback(agent)}")
    return {"arm": arm, "rounds": results}
```

Note: `_evaluate_reply` is the real self-eval method (confirmed signature `(group_id, mode, user_msg, reply, sticker_files=None, intent="", ctx_msgs=None)`, `async`, never raises). In production it runs fire-and-forget via `self._spawn(...)`; the benchmark `await`s it directly so `eval.jsonl` is written before `_evolve_tick` reads it. The test stubs `_evaluate_reply`, `_evolve_tick`, and `_call_anthropic`, so no network is touched.

- [ ] **Step 4: Run to verify it passes.**

Run: `python tests/test_benchmark.py`
Expected: all PASS, including `repo feedback untouched`.

- [ ] **Step 5: Commit.**

```bash
git add tools/evolution_benchmark.py tests/test_benchmark.py
git commit -m "benchmark: arm/round orchestration with state isolation"
```

---

### Task 4: Blind judge inbox + score ingest + aggregation

**Files:**
- Modify: `tools/evolution_benchmark.py`
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Produces:
  - `build_inbox(arms: list[dict], votes: int) -> tuple[list[dict], dict]` — returns `(inbox, key_map)`. `inbox` items: `{"item_id","reply"}` only (blind: NO arm/round/family/scenario). `key_map[item_id] = {"arm","round","scenario_id","family"}`. Order shuffled deterministically (sort by `sha1(item_id)`), `votes` copies per reply with suffixed ids `#v1..`.
  - `load_scores(path: Path) -> dict[str,dict]` — `{item_id: {"score","reason"}}`.
  - `aggregate(key_map, scores) -> dict` — errors (raises `ValueError`) if any inbox item_id missing from scores; returns `{(arm,round): mean_score}` plus per-family means.

- [ ] **Step 1: Write the failing test** (add + call in `main()`):

```python
def test_inbox_is_blind_and_ingest() -> None:
    arms = [{"arm": "evolve-on", "rounds": [
        {"round": 0, "feedback_pairs": 0,
         "holdout": [{"scenario_id": "ho1", "family": "f", "reply": "hello"}]},
        {"round": 1, "feedback_pairs": 2,
         "holdout": [{"scenario_id": "ho1", "family": "f", "reply": "sup"}]},
    ]}]
    inbox, key_map = bench.build_inbox(arms, votes=1)
    leaked = [k for it in inbox for k in it
              if k in ("arm", "round", "family", "scenario_id")]
    check("inbox blind (no leak fields)", leaked == [])
    check("inbox has item_id + reply only", all(set(it) == {"item_id", "reply"} for it in inbox))
    check("key_map covers all items", set(key_map) == {it["item_id"] for it in inbox})

    scores = {it["item_id"]: {"score": 3 + i, "reason": "r"} for i, it in enumerate(inbox)}
    agg = bench.aggregate(key_map, scores)
    check("aggregate has both rounds",
          ("evolve-on", 0) in agg["by_round"] and ("evolve-on", 1) in agg["by_round"])

    # Missing score -> error, not silent partial average.
    partial = dict(list(scores.items())[:1])
    raised = False
    try:
        bench.aggregate(key_map, partial)
    except ValueError:
        raised = True
    check("aggregate errors on missing score", raised)
```

- [ ] **Step 2: Run to verify it fails.**

Run: `python tests/test_benchmark.py`
Expected: FAIL — `AttributeError: ... 'build_inbox'`.

- [ ] **Step 3: Implement in `tools/evolution_benchmark.py`.**

```python
def build_inbox(arms: list[dict], votes: int = 1):
    inbox: list[dict] = []
    key_map: dict[str, dict] = {}
    for arm in arms:
        aname = arm["arm"]
        for rd in arm["rounds"]:
            for h in rd["holdout"]:
                base = f"{aname}|{rd['round']}|{h['scenario_id']}"
                for v in range(1, votes + 1):
                    item_id = f"{base}#v{v}"
                    inbox.append({"item_id": item_id, "reply": h["reply"]})
                    key_map[item_id] = {"arm": aname, "round": rd["round"],
                                        "scenario_id": h["scenario_id"],
                                        "family": h["family"]}
    # Deterministic shuffle: order by a hash of the id so the judge can't infer
    # arm/round from position, but the same run reproduces the same order.
    inbox.sort(key=lambda it: hashlib.sha1(it["item_id"].encode()).hexdigest())
    return inbox, key_map


def load_scores(path: Path) -> dict:
    out: dict[str, dict] = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        r = json.loads(ln)
        out[r["item_id"]] = {"score": int(r["score"]), "reason": r.get("reason", "")}
    return out


def aggregate(key_map: dict, scores: dict) -> dict:
    missing = [iid for iid in key_map if iid not in scores]
    if missing:
        raise ValueError(f"{len(missing)} inbox items have no score: {missing[:5]}")
    from collections import defaultdict
    by_round_vals: dict = defaultdict(list)
    by_family_vals: dict = defaultdict(list)
    for iid, meta in key_map.items():
        sc = scores[iid]["score"]
        by_round_vals[(meta["arm"], meta["round"])].append(sc)
        by_family_vals[(meta["arm"], meta["round"], meta["family"])].append(sc)
    mean = lambda xs: round(sum(xs) / len(xs), 3)
    return {
        "by_round": {k: mean(v) for k, v in by_round_vals.items()},
        "by_family": {k: mean(v) for k, v in by_family_vals.items()},
    }
```

- [ ] **Step 4: Run to verify it passes.**

Run: `python tests/test_benchmark.py`
Expected: all PASS.

- [ ] **Step 5: Commit.**

```bash
git add tools/evolution_benchmark.py tests/test_benchmark.py
git commit -m "benchmark: blind judge inbox + score ingest + aggregation"
```

---

### Task 5: CSV + SVG curve output

**Files:**
- Modify: `tools/evolution_benchmark.py`
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Produces:
  - `write_csv(agg: dict, path: Path) -> None` — columns `arm,round,mean_score`.
  - `write_svg(agg: dict, path: Path) -> None` — two-line chart (evolve-on vs evolve-off), x=round, y=mean score 1..5, same hand-rolled SVG style as `docs/*.svg` (Anthropic Sans, gray axes). No matplotlib.

- [ ] **Step 1: Write the failing test** (add + call in `main()`):

```python
def test_outputs() -> None:
    agg = {"by_round": {("evolve-on", 0): 2.5, ("evolve-on", 1): 3.4,
                        ("evolve-off", 0): 2.5, ("evolve-off", 1): 2.6},
           "by_family": {}}
    with tempfile.TemporaryDirectory() as td:
        csv_p = Path(td) / "r.csv"
        svg_p = Path(td) / "r.svg"
        bench.write_csv(agg, csv_p)
        bench.write_svg(agg, svg_p)
        csv_txt = csv_p.read_text(encoding="utf-8")
        check("csv header", csv_txt.splitlines()[0] == "arm,round,mean_score")
        check("csv has on row", "evolve-on,1,3.4" in csv_txt)
        svg_txt = svg_p.read_text(encoding="utf-8")
        check("svg is svg", svg_txt.lstrip().startswith("<svg"))
        check("svg well-formed", svg_txt.count("<svg") == 1 and "</svg>" in svg_txt)
        import xml.dom.minidom
        xml.dom.minidom.parseString(svg_txt)  # raises if malformed
        check("svg parses as xml", True)
```

- [ ] **Step 2: Run to verify it fails.**

Run: `python tests/test_benchmark.py`
Expected: FAIL — `AttributeError: ... 'write_csv'`.

- [ ] **Step 3: Implement in `tools/evolution_benchmark.py`.**

```python
def write_csv(agg: dict, path: Path) -> None:
    rows = ["arm,round,mean_score"]
    for (arm, rnd), score in sorted(agg["by_round"].items()):
        rows.append(f"{arm},{rnd},{score}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


_FONT = ('font-family:"Anthropic Sans", -apple-system, BlinkMacSystemFont, '
         '"Segoe UI", sans-serif')
_ARM_COLOR = {"evolve-on": "rgb(15, 110, 86)", "evolve-off": "rgb(153, 60, 29)"}


def write_svg(agg: dict, path: Path) -> None:
    by_round = agg["by_round"]
    arms = sorted({a for a, _ in by_round})
    rounds = sorted({r for _, r in by_round})
    W, H, ml, mr, mt, mb = 640, 400, 60, 140, 40, 50
    pw, ph = W - ml - mr, H - mt - mb
    ymin, ymax = 1.0, 5.0

    def px(r):
        return ml + (pw if len(rounds) == 1 else pw * (r - rounds[0]) / (rounds[-1] - rounds[0]))

    def py(v):
        return mt + ph * (1 - (v - ymin) / (ymax - ymin))

    parts = [f'<svg width="100%" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
    parts.append(f'<text x="{ml}" y="24" style="{_FONT};font-size:15px;font-weight:600;'
                 f'fill:rgb(20,20,20)">Self-evolution: held-out AI-tell score by round</text>')
    # axes
    parts.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" '
                 f'stroke="rgb(115,114,108)" stroke-width="1"/>')
    parts.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" '
                 f'stroke="rgb(115,114,108)" stroke-width="1"/>')
    for yv in range(1, 6):
        y = py(yv)
        parts.append(f'<line x1="{ml}" y1="{y}" x2="{ml+pw}" y2="{y}" '
                     f'stroke="rgb(230,229,225)" stroke-width="1"/>')
        parts.append(f'<text x="{ml-10}" y="{y+4}" text-anchor="end" '
                     f'style="{_FONT};font-size:12px;fill:rgb(115,114,108)">{yv}</text>')
    for r in rounds:
        parts.append(f'<text x="{px(r)}" y="{mt+ph+20}" text-anchor="middle" '
                     f'style="{_FONT};font-size:12px;fill:rgb(115,114,108)">{r}</text>')
    parts.append(f'<text x="{ml+pw/2}" y="{H-8}" text-anchor="middle" '
                 f'style="{_FONT};font-size:12px;fill:rgb(115,114,108)">learning round</text>')
    # lines
    for i, arm in enumerate(arms):
        color = _ARM_COLOR.get(arm, "rgb(83,74,183)")
        pts = [(px(r), py(by_round[(arm, r)])) for r in rounds if (arm, r) in by_round]
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
        for x, y in pts:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>')
        parts.append(f'<text x="{ml+pw+16}" y="{mt+18+i*20}" '
                     f'style="{_FONT};font-size:13px;fill:{color};font-weight:500">{arm}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")
```

- [ ] **Step 4: Run to verify it passes.**

Run: `python tests/test_benchmark.py`
Expected: all PASS.

- [ ] **Step 5: Commit.**

```bash
git add tools/evolution_benchmark.py tests/test_benchmark.py
git commit -m "benchmark: CSV + SVG curve output"
```

---

### Task 6: Judge backends + CLI (run / ingest) + CI + README

**Files:**
- Modify: `tools/evolution_benchmark.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md` (Development section), `README.zh-CN.md`
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Produces:
  - `async judge_export(inbox, out_dir) -> None` — writes `judge_inbox.jsonl`, prints instructions, exits the run stage.
  - `async judge_anthropic(inbox, model) -> dict` — scores via the Anthropic API (uses `anthropic` SDK already in requirements), returns `{item_id:{score,reason}}`.
  - `main()` argparse with subcommands `run` / `ingest` and flags `--rounds`(4) `--lang`(en) `--seed-state`(synthetic) `--holdout-votes`(1) `--judge`(export|anthropic) `--outdir`.

- [ ] **Step 1: Write the failing test** (add + call in `main()`):

```python
def test_export_writes_blind_inbox() -> None:
    arms = [{"arm": "evolve-on", "rounds": [
        {"round": 0, "feedback_pairs": 0,
         "holdout": [{"scenario_id": "ho1", "family": "f", "reply": "hi there"}]}]}]
    inbox, _ = bench.build_inbox(arms, votes=1)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        asyncio.run(bench.judge_export(inbox, out))
        written = (out / "judge_inbox.jsonl").read_text(encoding="utf-8")
        rec = json.loads(written.splitlines()[0])
        check("exported item blind", set(rec) == {"item_id", "reply"})
        check("exported reply present", rec["reply"] == "hi there")
```

- [ ] **Step 2: Run to verify it fails.**

Run: `python tests/test_benchmark.py`
Expected: FAIL — `AttributeError: ... 'judge_export'`.

- [ ] **Step 3: Implement the judge backends + CLI in `tools/evolution_benchmark.py`.**

```python
import argparse
import asyncio
import os

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

DATA = ROOT / "data" / "benchmark"


async def judge_export(inbox: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "judge_inbox.jsonl"
    p.write_text("".join(json.dumps({"item_id": it["item_id"], "reply": it["reply"]},
                                    ensure_ascii=False) + "\n" for it in inbox),
                 encoding="utf-8", newline="\n")
    print(f"\nWrote {len(inbox)} blind items to {p}")
    print("Score each into judge_scores.jsonl (one JSON per line):")
    print('  {"item_id": "...", "score": 1-5, "reason": "..."}')
    print("Rubric: 5 = reads like a real person; 1 = obvious AI tell "
          "(service-desk tone, bullet lists, name-at-start, over-explaining, "
          "answered the wrong person, jumped in mid-burst).")
    print(f"Then: python tools/evolution_benchmark.py ingest --outdir {out_dir}")


async def judge_anthropic(inbox: list[dict], model: str) -> dict:
    import anthropic
    client = anthropic.AsyncAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        base_url=os.getenv("ANTHROPIC_BASE_URL", "") or None)
    RUBRIC = ("Rate 1-5 how much this group-chat reply reads like a real person "
              "(5=human, 1=obvious AI tell). Reply ONLY with JSON "
              '{"score": int, "reason": "short"}.\n\nReply: ')
    scores: dict = {}
    for it in inbox:
        try:
            resp = await client.messages.create(
                model=model, max_tokens=120,
                messages=[{"role": "user", "content": RUBRIC + it["reply"]}])
            raw = "".join(getattr(b, "text", "") for b in resp.content).strip()
            import re
            raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
            d = json.loads(raw)
            scores[it["item_id"]] = {"score": int(d["score"]), "reason": d.get("reason", "")}
        except Exception as e:
            print(f"  judge error {it['item_id']}: {e}")
            scores[it["item_id"]] = {"score": 3, "reason": f"judge-failed: {e}"}
    return scores


def _seed_state_files(lang: str, mode: str, state_dir: Path) -> None:
    # 'synthetic' copies the committed starter datasets so both arms begin
    # identically; 'empty' starts from nothing.
    state_dir.mkdir(parents=True, exist_ok=True)
    if mode != "synthetic":
        return
    for kind in ("examples", "feedback"):
        src = ROOT / "data" / f"{kind}.{lang}.jsonl"
        if src.exists():
            (state_dir / f"{kind}.{lang}.jsonl").write_text(
                src.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")


async def cmd_run(args) -> int:
    bot_name = os.getenv("BOT_NAME", "Robin") or "Robin"
    train = load_scenarios(DATA / f"scenarios.train.{args.lang}.jsonl")
    holdout = load_scenarios(DATA / f"scenarios.holdout.{args.lang}.jsonl")
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    arms = []
    for evolve_on in (True, False):
        sd = out / ("state-on" if evolve_on else "state-off")
        arm = await run_arm(train, holdout, bot_name, args.lang, args.rounds,
                            evolve_on, sd, judge_model=args.judge_model)
        arms.append(arm)
    (out / "arms.json").write_text(json.dumps(arms, ensure_ascii=False, indent=2),
                                   encoding="utf-8", newline="\n")
    inbox, key_map = build_inbox(arms, votes=args.holdout_votes)
    (out / "key_map.json").write_text(json.dumps(key_map, ensure_ascii=False, indent=2),
                                      encoding="utf-8", newline="\n")
    if args.judge == "anthropic":
        scores = await judge_anthropic(inbox, args.judge_model)
        (out / "judge_scores.jsonl").write_text(
            "".join(json.dumps({"item_id": k, **v}, ensure_ascii=False) + "\n"
                    for k, v in scores.items()), encoding="utf-8", newline="\n")
        return _ingest(out)
    await judge_export(inbox, out)
    return 0


def _ingest(out: Path) -> int:
    key_map = json.loads((out / "key_map.json").read_text(encoding="utf-8"))
    # key_map JSON keys are strings; tuples were flattened — rebuild lookup.
    sp = out / "judge_scores.jsonl"
    if not sp.exists():
        print(f"error: {sp} not found. Score judge_inbox.jsonl first.")
        return 1
    scores = load_scores(sp)
    agg = aggregate(key_map, scores)
    write_csv(agg, out / "results.csv")
    write_svg(agg, out / "curve.svg")
    print(f"\nWrote {out/'results.csv'} and {out/'curve.svg'}")
    for (arm, rnd), sc in sorted(agg["by_round"].items()):
        print(f"  {arm} round {rnd}: {sc}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--rounds", type=int, default=4)
    r.add_argument("--lang", default="en")
    r.add_argument("--seed-state", default="synthetic", choices=["synthetic", "empty"])
    r.add_argument("--holdout-votes", type=int, default=1)
    r.add_argument("--judge", default="export", choices=["export", "anthropic"])
    r.add_argument("--judge-model", default=os.getenv("BENCH_JUDGE_MODEL", "claude-opus-4-8"))
    r.add_argument("--outdir", default=str(ROOT / "benchmark_runs" / "latest"))
    i = sub.add_parser("ingest")
    i.add_argument("--outdir", default=str(ROOT / "benchmark_runs" / "latest"))
    args = p.parse_args()
    if args.cmd == "run":
        return asyncio.run(cmd_run(args))
    return _ingest(Path(args.outdir))


if __name__ == "__main__":
    sys.exit(main())
```

Note on `aggregate` + `key_map` from JSON: `build_inbox` returns `key_map` with string ids as keys and dict values (arm/round/scenario_id/family) — JSON round-trips cleanly, so `_ingest` can pass it straight to `aggregate`. Confirm `aggregate` reads `meta["arm"]`/`meta["round"]` (it does) and that `round` stays an int through JSON (it does).

- [ ] **Step 4: Run the full test suite to verify it passes.**

Run: `python tests/test_benchmark.py`
Expected: all PASS, `all tests passed`.

- [ ] **Step 5: Gitignore run artifacts.**

Add to `.gitignore`:

```
benchmark_runs/
```

- [ ] **Step 6: Wire into CI.** In `.github/workflows/ci.yml`, extend the test step:

```yaml
      - name: Run tests
        run: |
          python tests/test_gateway.py
          python tests/test_evolution.py
          python tests/test_benchmark.py
```

- [ ] **Step 7: Document in READMEs.** In `README.md` Development section, after the `auto_reviewer` bullet, add:

```markdown
- `python tools/evolution_benchmark.py run` then score `judge_inbox.jsonl` and `... ingest` — measures the [self-evolution](#self-evolution) loop: runs an evolve-on vs evolve-off control over held-out scenarios and plots mean AI-tell score by round (`curve.svg`). An independent judge (Claude) scores blind, so the learning signal and the measurement never share a model.
```

In `README.zh-CN.md` 开发 section, after the `auto_reviewer` bullet:

```markdown
- `python tools/evolution_benchmark.py run` 后给 `judge_inbox.jsonl` 打分再 `... ingest` —— 量化[自进化](#自进化)循环:跑 evolve-on 对 evolve-off 对照组,在留出场景上画每轮 AI 味均分曲线(`curve.svg`)。独立裁判(Claude)盲评,学习信号和测量信号不共用模型。
```

- [ ] **Step 8: Commit.**

```bash
git add tools/evolution_benchmark.py tests/test_benchmark.py .github/workflows/ci.yml .gitignore README.md README.zh-CN.md
git commit -m "benchmark: judge backends + run/ingest CLI + CI + docs"
```

---

### Task 7: End-to-end dry run + first real curve

**Files:**
- Create (run output): `docs/evolution_benchmark_curve.svg`, `docs/evolution_benchmark_results.csv`
- Modify: `README.md`, `README.zh-CN.md` (embed the curve under Self-evolution)

**Interfaces:** none (operational task).

- [ ] **Step 1: Smoke-run the harness with a tiny round count against the real endpoints.**

Run: `python tools/evolution_benchmark.py run --rounds 2 --outdir benchmark_runs/smoke`
Expected: two arms run, `benchmark_runs/smoke/judge_inbox.jsonl` written, instructions printed. Requires a working `DEEPSEEK_API_KEY` + `EVAL_MODEL` in `.env`. If model calls fail, fix config before proceeding — do not fake the data.

- [ ] **Step 2: Judge the inbox.** The assistant (Claude) reads `benchmark_runs/smoke/judge_inbox.jsonl` and writes `benchmark_runs/smoke/judge_scores.jsonl` — one `{"item_id","score","reason"}` per line, scoring every item per the rubric, blind to arm/round.

- [ ] **Step 3: Ingest and inspect.**

Run: `python tools/evolution_benchmark.py ingest --outdir benchmark_runs/smoke`
Expected: `results.csv` + `curve.svg` written; printed per-round means show the evolve-off arm roughly flat. (With only 2 rounds and a small set the on-arm may or may not rise — this step verifies the pipeline end-to-end, not the scientific result.)

- [ ] **Step 4: Full run for the published curve.**

Run: `python tools/evolution_benchmark.py run --rounds 4 --holdout-votes 2 --outdir benchmark_runs/full`
Then judge its inbox, then `ingest`. Copy the result into `docs/`:

```bash
cp benchmark_runs/full/curve.svg docs/evolution_benchmark_curve.svg
cp benchmark_runs/full/results.csv docs/evolution_benchmark_results.csv
```

- [ ] **Step 5: Embed the curve in the READMEs** under the Self-evolution / 自进化 section (after the loop diagram):

`README.md`:
```markdown
### Does it actually work?

![Self-evolution benchmark curve](docs/evolution_benchmark_curve.svg)

Measured with `tools/evolution_benchmark.py`: an evolve-on arm against a frozen evolve-off control over held-out scenarios, scored blind by an independent judge (Claude) that never feeds the learning loop. [Raw numbers](docs/evolution_benchmark_results.csv).
```

`README.zh-CN.md`:
```markdown
### 它真的有用吗?

![自进化 benchmark 曲线](docs/evolution_benchmark_curve.svg)

用 `tools/evolution_benchmark.py` 测量:evolve-on 臂对冻结的 evolve-off 对照组,在留出场景上由独立裁判(Claude,从不参与学习循环)盲评。[原始数据](docs/evolution_benchmark_results.csv)。
```

- [ ] **Step 6: Commit.**

```bash
git add docs/evolution_benchmark_curve.svg docs/evolution_benchmark_results.csv README.md README.zh-CN.md
git commit -m "benchmark: publish first self-evolution curve"
git push
```

---

## Self-Review

**Spec coverage:**
- Two arms (on/off control) → Task 3. ✓
- N rounds + round-0 baseline → Task 3 (`run_arm`). ✓
- Three-leakage mitigation: independent judge → Task 6 (`judge_*`, Claude); EVAL_MODEL never scores → judge is separate; train/holdout disjoint → Task 1 (test asserts disjoint ids). ✓
- Same-family different-wording holdout → Task 1 data + `families shared` test. ✓
- Blind + shuffled inbox → Task 4 (`build_inbox`, blind test). ✓
- Pluggable judge (export default + anthropic) → Task 6. ✓
- State isolation, no repo writes → Task 3 (`build_isolated_agent` + `repo feedback untouched` test). ✓
- CSV + hand-rolled SVG, no matplotlib → Task 5. ✓
- Error handling: empty replies scored not aborted (Task 3 try/except), missing scores error (Task 4 `aggregate`), missing scores file on ingest (Task 6 `_ingest`). ✓
- tests + CI → Tasks 1-6 tests, Task 6 CI wiring. ✓
- Cost/first curve → Task 7. ✓

**Placeholder scan:** No TBD/TODO in steps. The one deferred item (exact `_evaluate_reply` method name) is called out explicitly in Task 3 Step 3 with a concrete resolution instruction (grep + use consistently) — flagged, not hand-waved.

**Type consistency:** `build_inbox -> (inbox, key_map)`; `key_map[item_id] -> {arm,round,scenario_id,family}`; `aggregate(key_map, scores)` reads `meta["arm"]/["round"]/["family"]` — consistent. `run_arm -> {"arm","rounds":[{round,feedback_pairs,holdout}]}`; `build_inbox` reads `arm["arm"]`, `rd["round"]`, `rd["holdout"]`, `h["scenario_id"]/["family"]/["reply"]` — matches `run_round` output. `write_csv`/`write_svg` read `agg["by_round"][(arm,round)]` — matches `aggregate`. Consistent.

**Self-eval entrypoint (resolved):** `_evaluate_reply(group_id, mode, user_msg, reply, sticker_files=None, intent="", ctx_msgs=None)` — `async`, never raises, production-spawned but `await`ed directly in the benchmark so `eval.jsonl` is on disk before `_evolve_tick` consumes it. The on-arm agent is built with `eval_enable=True`, so `_evaluate_reply` writes scores; the off-arm never calls it.
