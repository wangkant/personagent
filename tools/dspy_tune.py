"""DSPy-based prompt auto-tuning scaffold.

Idea: instead of hand-tuning STYLE_GUIDE bullets, treat the prompt as a program
and let DSPy search for better few-shot composition / instructions, using
data/feedback.<lang>.jsonl 'better' pairs as the optimization signal.

Status: SCAFFOLD ONLY. Tuning a chatbot persona via DSPy is fiddly because the
metric isn't a clean accuracy number — it needs an LLM judge. Treat this as a
starting point you can iterate on; don't expect one run to give you a magical prompt.

Quick start:
    pip install dspy-ai
    python tools/dspy_tune.py --bootstrap   # bootstrap demos from data/feedback.<lang>.jsonl
    python tools/dspy_tune.py --tune        # run BootstrapFewShot optimizer

Outputs:
    tools/dspy_tuned.json   — best program found (load via dspy.load)
    tools/dspy_log.md       — per-iteration scores
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent import _resolve_lang_file

AGENT_LANG = os.getenv("AGENT_LANG", "en").strip().lower()
FEEDBACK_FILE = _resolve_lang_file("feedback", "jsonl", AGENT_LANG)
EXAMPLES_FILE = _resolve_lang_file("examples", "jsonl", AGENT_LANG)
OUT_PROGRAM = Path(__file__).parent / "dspy_tuned.json"
OUT_LOG = Path(__file__).parent / "dspy_log.md"


def load_pairs() -> list[dict]:
    if not FEEDBACK_FILE.exists():
        return []
    pairs = []
    for ln in FEEDBACK_FILE.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("rating") == "better" and r.get("better") and r.get("reply"):
            pairs.append({
                "context": "\n".join(r.get("context", [])),
                "scenario": r.get("scenario", ""),
                "bad": r["reply"],
                "good": r["better"],
            })
    return pairs


def load_goods() -> list[dict]:
    if not EXAMPLES_FILE.exists():
        return []
    out = []
    for ln in EXAMPLES_FILE.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("reply"):
            out.append({
                "context": "\n".join(r.get("context", [])),
                "scenario": r.get("scenario", ""),
                "good": r["reply"],
            })
    return out


# ---------- DSPy wiring (imported lazily so the rest of the file still works
# without dspy installed) ----------
def build_program():
    import dspy  # type: ignore

    class PersonaReply(dspy.Signature):
        """Generate a QQ group reply in the bot's persona voice — a natural,
        conversational netizen who chats like a real person, not an AI assistant.
        Output 1 short sentence, 15-30 chars, no AI tells, no markdown, no emoji."""
        scenario: str = dspy.InputField(desc="situation tag")
        context: str = dspy.InputField(desc="recent group messages")
        reply: str = dspy.OutputField(desc="bot reply in persona voice")

    return dspy.ChainOfThought(PersonaReply)


def metric_factory(judge_model: str):
    """Returns a DSPy metric. Uses an LLM judge to score reply quality 1-5
    against the human-preferred 'good' reply. >=4 counts as success."""
    import dspy  # type: ignore

    judge_lm = dspy.LM(judge_model)

    def metric(example, pred, trace=None):
        # example.good is the human-preferred reply; pred.reply is the candidate
        prompt = (
            f"Compare two QQ group replies for the same situation. Score the "
            f"candidate 1-5 based on how close to the reference's style/quality.\n\n"
            f"Scenario: {example.scenario}\n"
            f"Context:\n{example.context}\n\n"
            f"Reference (good): {example.good}\n"
            f"Candidate: {pred.reply}\n\n"
            f"Output JSON only: {{\"score\": 1-5}}"
        )
        with dspy.context(lm=judge_lm):
            resp = judge_lm(prompt)
        try:
            score = int(json.loads(resp[0])["score"])
        except Exception:
            return 0.0
        return score / 5.0

    return metric


def cmd_bootstrap():
    pairs = load_pairs()
    goods = load_goods()
    print(f"Loaded {len(pairs)} pairs, {len(goods)} good examples")
    if not pairs and not goods:
        print("Nothing to bootstrap from. Add entries to data/feedback.<lang>.jsonl first.")
        return
    print("Pairs head:")
    for p in pairs[:3]:
        print(f"  [BAD] {p['bad']}\n  [OK]  {p['good']}\n")


def cmd_tune(judge_model: str = "deepseek-chat"):
    try:
        import dspy  # type: ignore
    except ImportError:
        print("dspy not installed. pip install dspy-ai")
        return

    pairs = load_pairs()
    goods = load_goods()
    if not pairs:
        print("No 'better' pairs in data/feedback.<lang>.jsonl — cannot run BootstrapFewShot.")
        return

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    lm = dspy.LM(
        model=f"openai/{os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')}",
        api_key=api_key,
        base_url=base_url,
    )
    dspy.configure(lm=lm)

    program = build_program()
    train = [
        dspy.Example(
            scenario=p["scenario"], context=p["context"], good=p["good"]
        ).with_inputs("scenario", "context")
        for p in pairs + [{"scenario": g["scenario"], "context": g["context"], "good": g["good"]} for g in goods]
    ]

    from dspy.teleprompt import BootstrapFewShot  # type: ignore

    optimizer = BootstrapFewShot(metric=metric_factory(judge_model), max_bootstrapped_demos=4)
    compiled = optimizer.compile(program, trainset=train)
    compiled.save(str(OUT_PROGRAM))
    print(f"Saved tuned program to {OUT_PROGRAM}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bootstrap", action="store_true", help="dry-run: load and preview pairs")
    p.add_argument("--tune", action="store_true", help="run BootstrapFewShot optimizer")
    p.add_argument("--judge-model", default="deepseek-chat")
    args = p.parse_args()
    if args.bootstrap:
        cmd_bootstrap()
    elif args.tune:
        cmd_tune(args.judge_model)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
