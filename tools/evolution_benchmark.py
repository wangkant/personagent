"""tools/evolution_benchmark.py — quantify the self-evolution loop.

Drives the real Agent over synthetic train / held-out scenario sets across N
rounds and two arms (evolve-on, evolve-off control), each in an isolated temp
state dir, then exports blind held-out replies for an independent judge
(Claude) and plots mean score vs round. See
docs/superpowers/specs/2026-07-22-evolution-benchmark-design.md.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from persona_agent import evolution  # noqa: E402

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
