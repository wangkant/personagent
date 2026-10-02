"""Measure how the real agent behaves (same as `personagent eval`)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from persona_agent.evals import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(prog="python tools/behavior_eval.py"))
