"""Helpers the suites import: `check` and the isolated agent factory."""
from __future__ import annotations

from pathlib import Path

from persona_agent import reactions
from persona_agent.agent import Agent

#: A NapCat address nothing listens on.
CLOSED_ONEBOT_URL = "http://127.0.0.1:9"


def check(name: str, cond, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English."""
    assert cond, name + (f" - {detail}" if detail else "")


def isolated_agent(tmp: Path, *, seeds: bool = False, **settings) -> Agent:
    """A real Agent whose runtime state, read or written, lives under `tmp`.

    `settings` override the Agent keywords below. The shipped seed pools stay
    readable unless `seeds=True` swaps them for empty files in `tmp`."""
    tmp.mkdir(parents=True, exist_ok=True)
    a = Agent(**{
        "api_key": "test-key", "qq_bot_id": "10001", "persona_name": "TestBot",
        "persona": "test persona", "lang": "en", "message_debounce_sec": 0,
        "memory_file": str(tmp / "memory.json"), "eval_enabled": False,
        "eval_file": str(tmp / "eval.jsonl"), "stickers_dir": str(tmp / "stickers"),
        "stickers_file": str(tmp / "stickers.json"), **settings})
    # The ctor already read the default files; drop what it loaded.
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a._seen_msg_ids.clear()
    a.core_memory_file = tmp / "core_memory.json"
    a.core_memory.clear()
    a.connector_handles.path = tmp / "connector_handles.json"
    a.owner_profile_file = tmp / "owner_profile.json"
    a.stickers.unknown_log = tmp / "unknown_stickers.jsonl"
    a.candidates_file = tmp / "candidates.jsonl"
    a.teacher_stats = reactions.TeacherStats(tmp / "teacher_stats.json")
    # The evidence log, ledger, promoted views and lineage live beside it.
    a.examples_file = tmp / "examples.jsonl"
    a.feedback_file = tmp / "feedback.jsonl"
    if seeds:
        a.examples_seed_file = tmp / "seed_examples.jsonl"
        a.feedback_seed_file = tmp / "seed_feedback.jsonl"
    return a
