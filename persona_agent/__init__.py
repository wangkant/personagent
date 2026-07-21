"""persona_agent — the application package.

Core modules:
- agent      the persona pipeline (modes, JSON output protocol, validators,
             memory, few-shot retrieval, self-eval, self-evolution loop)
- gateway    platform-neutral inbound event schema + reply sink
- stickers   sticker library: steal -> tag -> persona-fit gates -> feedback
- evolution  eval -> feedback learning-loop logic (shared by the agent's
             EVOLVE_AUTO loop and tools/auto_reviewer.py)
- health     startup / runtime environment checks

Entry points live at the repo root (main.py, try_chat.py, quickstart.py);
runtime state (memory.json, eval.jsonl, stickers/, ...) stays at the repo
root too — see paths.ROOT.
"""
