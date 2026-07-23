"""tools/evolution_benchmark.py — quantify the self-evolution loop.

Drives the real Agent over synthetic train / held-out scenario sets across N
rounds and two arms (evolve-on, evolve-off control), each in an isolated temp
state dir, then exports blind held-out replies for an independent judge
(Claude) and plots mean score vs round. See
docs/superpowers/specs/2026-07-22-evolution-benchmark-design.md.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from persona_agent import evolution  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

DATA = ROOT / "data" / "benchmark"

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
    benchmark run cannot touch the repo's real memory/eval/feedback files.

    Model credentials come from the environment (the same vars main.py reads),
    so a live run generates and self-evals against the configured endpoints.
    They default to a fake key + api.deepseek.com, which is correct for the
    tests — those stub `_call_anthropic`, so the key is never used."""
    import os
    from persona_agent.agent import Agent
    state_dir.mkdir(parents=True, exist_ok=True)
    a = Agent(
        api_key=os.getenv("DEEPSEEK_API_KEY", "") or "benchmark-key",
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        bot_qq="10001", bot_name=bot_name,
        napcat_api="http://127.0.0.1:9",
        memory_file=str(state_dir / "memory.json"), persona="benchmark persona",
        eval_enable=eval_enable, eval_file=str(state_dir / "eval.jsonl"),
        eval_model=os.getenv("EVAL_MODEL", ""),
        vision_model="",  # scenarios use [image: ...] markers, never real pixels
        glm_api_key=os.getenv("GLM_API_KEY", ""),
        glm_base_url=os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
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
    # Web search is noise for a persona benchmark (and adds a decision call +
    # an external fetch per generation). Stub it so every reply is pure
    # persona-pipeline output. Both arms are stubbed identically, so this
    # cannot bias the on-vs-off comparison.
    async def _no_search(messages, hint=""):
        return ""
    a._decide_and_search = _no_search
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


async def run_arm(train, holdout, bot_name, lang, rounds, evolve_on, state_dir,
                  judge_model, seed_state="empty"):
    if state_dir.exists():
        shutil.rmtree(state_dir)
    agent = build_isolated_agent(state_dir, bot_name, lang, eval_enable=evolve_on)
    # Seed both arms identically (or start empty) AFTER build so the files
    # survive the rmtree above; the agent's retrieval caches reload lazily by
    # mtime, so files dropped in now are picked up on the first round.
    _seed_state_files(lang, seed_state, state_dir)
    agent._pairs_mtime = 0.0
    agent._examples_mtime = 0.0
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


def build_inbox(arms: list[dict], votes: int = 1):
    """Build a blind inbox from arm results.

    Returns (inbox, key_map) where:
    - inbox: list of {"item_id", "reply"} (blind: no arm/round/family/scenario_id)
    - key_map: {item_id: {"arm", "round", "scenario_id", "family"}}
    - Order shuffled deterministically by sha1(item_id) so judge can't infer arm/round from position.
    - votes copies per reply with suffixed ids #v1, #v2, etc.
    """
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
    """Load scores from a JSONL file.

    Returns {item_id: {"score", "reason"}}.
    """
    out: dict[str, dict] = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        r = json.loads(ln)
        out[r["item_id"]] = {"score": int(r["score"]), "reason": r.get("reason", "")}
    return out


def aggregate(key_map: dict, scores: dict) -> dict:
    """Aggregate scores by (arm, round) and (arm, round, family).

    Raises ValueError if any inbox item lacks a score.
    Returns {"by_round": {(arm, round): mean_score}, "by_family": {...}}.
    """
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


def write_csv(agg: dict, path: Path) -> None:
    """Write aggregated scores to CSV (arm, round, mean_score)."""
    rows = ["arm,round,mean_score"]
    for (arm, rnd), score in sorted(agg["by_round"].items()):
        rows.append(f"{arm},{rnd},{score}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


_FONT = ('font-family:"Anthropic Sans", -apple-system, BlinkMacSystemFont, '
         '"Segoe UI", sans-serif')
_ARM_COLOR = {"evolve-on": "rgb(15, 110, 86)", "evolve-off": "rgb(153, 60, 29)"}


def write_svg(agg: dict, path: Path) -> None:
    """Hand-rolled SVG chart of mean score by round for each arm."""
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
    parts.append(f'<text x=\'{ml}\' y=\'24\' style=\'{_FONT};font-size:15px;font-weight:600;'
                 f'fill:rgb(20,20,20)\'>Self-evolution: held-out AI-tell score by round</text>')
    # axes
    parts.append(f'<line x1=\'{ml}\' y1=\'{mt}\' x2=\'{ml}\' y2=\'{mt+ph}\' '
                 f'stroke="rgb(115,114,108)" stroke-width="1"/>')
    parts.append(f'<line x1=\'{ml}\' y1=\'{mt+ph}\' x2=\'{ml+pw}\' y2=\'{mt+ph}\' '
                 f'stroke="rgb(115,114,108)" stroke-width="1"/>')
    for yv in range(1, 6):
        y = py(yv)
        parts.append(f'<line x1=\'{ml}\' y1=\'{y}\' x2=\'{ml+pw}\' y2=\'{y}\' '
                     f'stroke="rgb(230,229,225)" stroke-width="1"/>')
        parts.append(f'<text x=\'{ml-10}\' y=\'{y+4}\' text-anchor="end" '
                     f'style=\'{_FONT};font-size:12px;fill:rgb(115,114,108)\'>{yv}</text>')
    for r in rounds:
        parts.append(f'<text x=\'{px(r)}\' y=\'{mt+ph+20}\' text-anchor="middle" '
                     f'style=\'{_FONT};font-size:12px;fill:rgb(115,114,108)\'>{r}</text>')
    parts.append(f'<text x=\'{ml+pw/2}\' y=\'{H-8}\' text-anchor="middle" '
                 f'style=\'{_FONT};font-size:12px;fill:rgb(115,114,108)\'>learning round</text>')
    # lines
    for i, arm in enumerate(arms):
        color = _ARM_COLOR.get(arm, "rgb(83,74,183)")
        pts = [(px(r), py(by_round[(arm, r)])) for r in rounds if (arm, r) in by_round]
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
        for x, y in pts:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>')
        parts.append(f'<text x=\'{ml+pw+16}\' y=\'{mt+18+i*20}\' '
                     f'style=\'{_FONT};font-size:13px;fill:{color};font-weight:500\'>{arm}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")


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
                            evolve_on, sd, judge_model=args.judge_model,
                            seed_state=args.seed_state)
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
    r.add_argument("--seed-state", default="empty", choices=["synthetic", "empty"],
                   help="empty (default) = both arms start with zero feedback, the "
                        "cleanest control; synthetic = copy the committed starter datasets")
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
