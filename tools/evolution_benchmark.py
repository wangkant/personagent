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
