"""Offline prompt tuning lab.

Usage:
    python tools/prompt_lab.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import anthropic
from agent import DEFAULT_PERSONA, STYLE_GUIDE, TOOL_GUIDE, _resolve_lang_file

AGENT_LANG = os.getenv("AGENT_LANG", "en").strip().lower()

_fixtures_suffixed = Path(__file__).parent / f"fixtures.{AGENT_LANG}.jsonl"
FIXTURES_FILE = (
    _fixtures_suffixed if _fixtures_suffixed.is_file()
    else Path(__file__).parent / "fixtures.jsonl"
)
# Approved replies flow into the active-language pools so they match the
# language the agent actually runs in.
FEEDBACK_FILE = _resolve_lang_file("feedback", "jsonl", AGENT_LANG)
EXAMPLES_FILE = _resolve_lang_file("examples", "jsonl", AGENT_LANG)

MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "")

def _c(text, code): return f"\033[{code}m{text}\033[0m"
def cyan(t): return _c(t, "36")
def green(t): return _c(t, "32")
def yellow(t): return _c(t, "33")
def red(t): return _c(t, "31")
def dim(t): return _c(t, "2")
def bold(t): return _c(t, "1")

def load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return out

def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def build_system_prompt(examples: list) -> str:
    parts = [
        f"<persona>\n{DEFAULT_PERSONA}\n</persona>",
        STYLE_GUIDE,
        TOOL_GUIDE,
    ]
    if examples:
        if AGENT_LANG == "zh":
            ex_str = ["\n<examples>", "学习以下高质量回复的说话方式（学风格不照搬原文）："]
            for e in examples[-5:]:
                ctx = "\n".join(e.get("context", []))
                ex_str.append(
                    f"\n场景: {e.get('scenario','?')}\n"
                    f"群里:\n{ctx}\n"
                    f"你的回复: {e.get('reply','')}"
                )
        else:
            ex_str = ["\n<examples>",
                      "Learn the speaking style of these high-quality replies "
                      "(mimic the voice, don't copy verbatim):"]
            for e in examples[-5:]:
                ctx = "\n".join(e.get("context", []))
                ex_str.append(
                    f"\nscenario: {e.get('scenario','?')}\n"
                    f"group:\n{ctx}\n"
                    f"your reply: {e.get('reply','')}"
                )
        ex_str.append("\n</examples>")
        parts.append("\n".join(ex_str))
    return "\n\n".join(parts)

def get_client():
    kwargs = {"api_key": ANTHROPIC_API_KEY}
    if ANTHROPIC_BASE_URL:
        kwargs["base_url"] = ANTHROPIC_BASE_URL
    return anthropic.AsyncAnthropic(**kwargs)

async def gen_reply(system: str, fx: dict, client) -> str:
    ctx_text = "\n".join(fx.get("context", []))
    if AGENT_LANG == "zh":
        mode_hint = {
            "called": "(最后一条点名/at 了你)",
            "owner": "(最后一条是 owner 说的)",
            "judge": "(群里在聊，你没被点名)",
            "followup": "(你刚发过言，现在有新消息)",
        }.get(fx.get("mode", "judge"), "")
        user_prompt = (
            f"群聊上下文 {mode_hint}:\n---\n{ctx_text}\n---\n"
            f"直接输出你要说的话，符合人设。如果你判断这种情境根本不该插话就只输出 PASS。"
        )
    else:
        mode_hint = {
            "called": "(the last message named / @'d you)",
            "owner": "(the last message is from the owner)",
            "judge": "(the group is chatting; you weren't named)",
            "followup": "(you just spoke; now there's a new message)",
        }.get(fx.get("mode", "judge"), "")
        user_prompt = (
            f"Group chat context {mode_hint}:\n---\n{ctx_text}\n---\n"
            f"Output exactly what you'd say, in character. If this isn't a moment "
            f"you'd jump in, output only PASS."
        )
    response = await client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(
        getattr(b, "text", "") for b in response.content if getattr(b, "text", "")
    ).strip()

def cmd_list(fixtures: list):
    if not fixtures:
        print(dim("(no fixtures)"))
        return
    for fx in fixtures:
        print(f"  {cyan(fx.get('id','?'))}  [{fx.get('mode','?'):8}]  {fx.get('scenario','?')}")

def cmd_show_examples(examples: list):
    if not examples:
        print(dim("(empty - run tests + give 'better' answers to fill the bank)"))
        return
    for i, e in enumerate(examples, 1):
        print(f"{bold(f'[{i}]')} {cyan(e.get('scenario','?'))}")
        for line in e.get("context", []):
            print(f"  {dim(line)}")
        print(f"  {green('reply:')} {e.get('reply','')}\n")

async def cmd_run(fixtures: list, ids_filter: list | None = None):
    examples = load_jsonl(EXAMPLES_FILE)
    client = get_client()
    system = build_system_prompt(examples)

    if ids_filter:
        fixtures = [f for f in fixtures if f.get("id") in ids_filter]

    print(f"\n{cyan('System prompt')}: {len(system)} chars, {len(examples)} examples loaded")
    print(f"{cyan('Running')} {len(fixtures)} fixtures with model={bold(MODEL)}\n")

    for i, fx in enumerate(fixtures, 1):
        fid = fx.get("id", "?")
        fmode = fx.get("mode", "?")
        print(f"{bold(f'[{i}/{len(fixtures)}]')} {cyan(fx.get('scenario','?'))}  "
              f"{dim('(id=' + fid + ' mode=' + fmode + ')')}")
        for line in fx.get("context", []):
            print(f"  {dim(line)}")

        print(f"  {yellow('generating...')}", end="", flush=True)
        try:
            reply = await gen_reply(system, fx, client)
        except Exception as e:
            print(f"\r  {red('failed:')} {type(e).__name__}: {e}")
            continue
        print("\r" + " " * 30 + "\r", end="")
        print(f"  {green('reply:')} {reply}\n")

        while True:
            choice = input(
                f"  rate [{green('g')}]ood  [{red('b')}]ad  "
                f"[{yellow('B')}]etter  [{dim('s')}]kip  [{dim('q')}]uit: "
            ).strip()
            if choice in ("g", "b", "s", "q", "B"):
                break
            print(red("  invalid"))

        if choice == "q":
            return
        if choice == "s":
            continue

        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        record = {
            "ts": ts,
            "fixture_id": fx.get("id"),
            "scenario": fx.get("scenario"),
            "mode": fx.get("mode"),
            "context": fx.get("context"),
            "reply": reply,
            "rating": {"g": "good", "b": "bad", "B": "better"}[choice],
        }

        if choice == "B":
            better = input(f"  {yellow('better reply:')} ").strip()
            if not better:
                print(f"  {dim('empty, skipped')}")
                continue
            record["better"] = better
            append_jsonl(EXAMPLES_FILE, {
                "scenario": fx.get("scenario"),
                "context": fx.get("context"),
                "reply": better,
                "ts": ts,
            })
            print(f"  {green('+')} added to examples bank")
        elif choice == "g":
            append_jsonl(EXAMPLES_FILE, {
                "scenario": fx.get("scenario"),
                "context": fx.get("context"),
                "reply": reply,
                "ts": ts,
            })
            print(f"  {green('+')} added to examples bank")
        else:
            print(f"  {dim('logged to feedback only')}")
        append_jsonl(FEEDBACK_FILE, record)

def cmd_add() -> dict | None:
    print(yellow("New fixture. Enter 'done' on empty context line to finish."))
    scenario = input("scenario: ").strip()
    if not scenario:
        print(red("scenario required"))
        return None
    mode = input("mode [judge/called/owner/followup]: ").strip() or "judge"
    if mode not in ("judge", "called", "owner", "followup"):
        print(red("invalid mode"))
        return None
    fid = f"f{int(time.time()) % 1000000:06d}"
    context = []
    while True:
        line = input(f"context [{len(context)+1}] (e.g. 'Alice: hi', empty to finish): ").strip()
        if not line:
            break
        if ":" not in line:
            print(red("expected '<name>: <text>'"))
            continue
        context.append(line)
    if not context:
        print(red("at least one context line required"))
        return None
    return {"id": fid, "scenario": scenario, "mode": mode, "context": context}

def cmd_show_prompt():
    examples = load_jsonl(EXAMPLES_FILE)
    system = build_system_prompt(examples)
    print(f"\n{dim('--- system prompt ---')}")
    print(system)
    print(f"{dim('--- end (len=' + str(len(system)) + ') ---')}\n")

async def main():
    fixtures = load_jsonl(FIXTURES_FILE)
    examples = load_jsonl(EXAMPLES_FILE)

    print(bold(cyan("\n=== Prompt Lab ===")))
    print(f"fixtures: {len(fixtures)}  examples in bank: {len(examples)}")
    print(f"model: {MODEL}")
    print(f"endpoint: {ANTHROPIC_BASE_URL or '(default)'}")

    while True:
        print(
            f"\n{cyan('[1]')} list fixtures   "
            f"{cyan('[2]')} run all          "
            f"{cyan('[3]')} run by ID(s)\n"
            f"{cyan('[4]')} show examples   "
            f"{cyan('[5]')} add fixture     "
            f"{cyan('[6]')} show current prompt\n"
            f"{cyan('[q]')} quit"
        )
        choice = input("> ").strip()

        if choice == "1":
            cmd_list(fixtures)
        elif choice == "2":
            await cmd_run(fixtures)
        elif choice == "3":
            ids = input("ids (comma-separated, e.g. f001,f005): ").strip()
            ids_list = [s.strip() for s in ids.split(",") if s.strip()]
            if ids_list:
                await cmd_run(fixtures, ids_list)
        elif choice == "4":
            cmd_show_examples(load_jsonl(EXAMPLES_FILE))
        elif choice == "5":
            new_fx = cmd_add()
            if new_fx:
                append_jsonl(FIXTURES_FILE, new_fx)
                fixtures.append(new_fx)
                print(f"{green('+')} added {new_fx['id']}")
        elif choice == "6":
            cmd_show_prompt()
        elif choice == "q":
            break
        else:
            print(red("unknown command"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
