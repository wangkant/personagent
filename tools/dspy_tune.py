"""DSPy-based prompt auto-tuning scaffold.

Idea: instead of hand-tuning STYLE_GUIDE bullets, treat the prompt as a program
and let DSPy search for better few-shot composition / instructions, using
seed and runtime feedback 'better' pairs as the optimization signal.

Status: SCAFFOLD ONLY. Tuning a chatbot persona via DSPy is fiddly because the
metric isn't a clean accuracy number — it needs an LLM judge. Treat this as a
starting point you can iterate on; don't expect one run to give you a magical prompt.

Quick start:
    pip install dspy-ai
    python tools/dspy_tune.py --bootstrap   # bootstrap demos from seed + runtime feedback
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

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

from persona_agent.config_env import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL  # noqa: E402
from persona_agent.paths import (
    read_jsonl,
    resolve_runtime_lang_file,
    resolve_seed_lang_file,
)

AGENT_LANG = os.getenv("AGENT_LANG", "en").strip().lower()
FEEDBACK_FILES = (
    resolve_seed_lang_file("feedback", "jsonl", AGENT_LANG),
    resolve_runtime_lang_file("feedback", "jsonl", AGENT_LANG),
)
EXAMPLES_FILES = (
    resolve_seed_lang_file("examples", "jsonl", AGENT_LANG),
    resolve_runtime_lang_file("examples", "jsonl", AGENT_LANG),
)
OUT_PROGRAM = Path(__file__).parent / "dspy_tuned.json"
OUT_LOG = Path(__file__).parent / "dspy_log.md"


def load_pairs() -> list[dict]:
    pairs = []
    for r in read_jsonl(FEEDBACK_FILES):
        if r.get("rating") == "better" and r.get("better") and r.get("reply"):
            pairs.append({
                "context": "\n".join(r.get("context", [])),
                "scenario": r.get("scenario", ""),
                "bad": r["reply"],
                "good": r["better"],
            })
    return pairs


def load_goods() -> list[dict]:
    out = []
    for r in read_jsonl(EXAMPLES_FILES):
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

    # The judge must not be the model being measured, or the loop grades its
    # own homework (see tools/evolution_benchmark.py). judge_model here
    # defaults to the same model LLM_MODEL defaults to, so
    # an out-of-the-box run scores itself unless --judge-model is overridden;
    # warn rather than sys.exit because this file's scaffold/quick-start role
    # means --judge-model always has a default and a hard failure here would
    # break running it with no arguments beyond that default.
    if judge_model.strip().lower() == os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL).strip().lower():
        print(
            f"WARNING: --judge-model ({judge_model}) matches LLM_MODEL "
            f"({os.getenv('LLM_MODEL', DEFAULT_LLM_MODEL)}) -- the judge would "
            f"be scoring the same model it is grading. Pass a different "
            f"--judge-model.",
            file=sys.stderr,
        )

    # Same shape as the primary LM in cmd_tune: the provider prefix and the
    # credentials are not optional. A bare dspy.LM(name) has no api_key and no
    # base_url, so every judge call raises — and since the call sat outside the
    # try below, that exception left `metric` entirely and killed the whole
    # optimizer run instead of degrading to the 0.0 the try was written for.
    judge_lm = dspy.LM(
        model=f"openai/{judge_model}",
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
    )

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
        try:
            with dspy.context(lm=judge_lm):
                resp = judge_lm(prompt)
            score = int(json.loads(resp[0])["score"])
        except Exception:
            # A judge that cannot answer scores 0, it does not abort the run.
            return 0.0
        return score / 5.0

    return metric


def cmd_bootstrap() -> int | None:
    pairs = load_pairs()
    goods = load_goods()
    print(f"Loaded {len(pairs)} pairs, {len(goods)} good examples")
    if not pairs and not goods:
        print("Nothing to bootstrap from. Add entries to the runtime feedback file first.")
        return 1
    print("Pairs head:")
    for p in pairs[:3]:
        print(f"  [BAD] {p['bad']}\n  [OK]  {p['good']}\n")


def cmd_tune(judge_model: str = DEFAULT_LLM_MODEL) -> int | None:
    try:
        import dspy  # type: ignore
    except ImportError:
        print("dspy not installed. pip install dspy-ai")
        return 1

    pairs = load_pairs()
    goods = load_goods()
    if not pairs:
        print("No 'better' pairs in seed or runtime feedback — cannot run BootstrapFewShot.")
        return 1

    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
    lm = dspy.LM(
        model=f"openai/{os.getenv('LLM_MODEL', DEFAULT_LLM_MODEL)}",
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
    # DSPy writes this one through its own file I/O, so it lands at the umask
    # default — and it is the file in this chain that embeds verbatim group
    # chat (the bootstrapped demos quote real context and replies). Everything
    # else holding conversation text is 0600 (storage.PRIVATE_FILE_MODE).
    try:
        os.chmod(OUT_PROGRAM, 0o600)
    except OSError:
        pass  # Windows ACLs do not map onto POSIX mode bits
    print(f"Saved tuned program to {OUT_PROGRAM}")


def main() -> int | None:
    p = argparse.ArgumentParser()
    p.add_argument("--bootstrap", action="store_true", help="dry-run: load and preview pairs")
    p.add_argument("--tune", action="store_true", help="run BootstrapFewShot optimizer")
    p.add_argument("--judge-model", default=DEFAULT_LLM_MODEL)
    args = p.parse_args()
    if args.bootstrap:
        return cmd_bootstrap()
    elif args.tune:
        return cmd_tune(args.judge_model)
    else:
        p.print_help()


if __name__ == "__main__":
    sys.exit(main() or 0)
