"""Try the agent in your terminal — no chat platform, just an API key.

This drives the SAME reasoning path the live bot uses (persona + style guide +
JSON output protocol + the character-whitelist validator), so you can feel out a
persona and see replies before connecting it to a chat platform.

    python try_chat.py
    python try_chat.py --admin          # speak as the configured admin
    python try_chat.py --lang zh         # force the Chinese variant
    python try_chat.py --name Alex       # your display name in the chat

Type a message and press enter. Commands:
    /admin <msg>   send this one line as the admin
    /as Name <msg> send as a one-off speaker called Name
    /reset         clear the conversation buffer
    /quit          exit
"""
from __future__ import annotations

import argparse
import asyncio
import os

from dotenv import load_dotenv

load_dotenv(override=False)

from persona_agent import access  # noqa: E402
from persona_agent.access import ADMIN_MODE  # noqa: E402
from persona_agent.agent import Agent  # noqa: E402
from persona_agent.config_env import (  # noqa: E402
    DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL, env_bool)
from persona_agent.textproc import TextProcessing  # noqa: E402

GROUP_ID = "trial"
#: Who "--admin" speaks as: a configured admin account, if there is one.
ADMIN_ID = min(access.identity_from_env().admins, default="") or "1969"


def _build_agent(lang: str) -> Agent:
    return Agent(
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
        model=os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL),
        qq_bot_id=os.getenv("QQ_BOT_ID", "") or "10000",
        persona_name=os.getenv("PERSONA_NAME", "") or "bot",
        llm_dm_model=os.getenv("LLM_DM_MODEL", ""),
        admin_ids=(ADMIN_ID,),
        admin_name=os.getenv("ADMIN_NAME", "") or "admin",
        admin_relationship=os.getenv("ADMIN_RELATIONSHIP", ""),
        llm_fallback_model=os.getenv("LLM_FALLBACK_MODEL", ""),
        llm_fallback_base_url=os.getenv("LLM_FALLBACK_BASE_URL", ""),
        llm_fallback_api_key=os.getenv("LLM_FALLBACK_API_KEY", ""),
        llm_fallback_thinking=env_bool("LLM_FALLBACK_THINKING", False),
        # Trial defaults: don't spend tokens self-scoring, and skip vision
        # (the terminal can't send images anyway).
        eval_enabled=False,
        vision_model="",
        tavily_key=os.getenv("TAVILY_API_KEY", ""),
        lang=lang,
    )


async def _turn(agent: Agent, name: str, uid: str, text: str, mode: str) -> None:
    agent._append_buffer(GROUP_ID, name, text, uid)
    reply, intent, mem = await agent._think(
        GROUP_ID, mode=mode, latest_text=text, caller_override=(name, uid),
    )
    safe = (TextProcessing._sanitize_reply(
            reply, agent.agent_lang, agent.reply_style)
            if reply else "")
    if not safe or safe.strip().upper() == "PASS":
        print(f"  {agent.persona_name} > (stays quiet)")
        if reply and not safe:
            print(f"  [validator dropped raw reply: {reply[:60]!r}]")
        return
    print(f"  {agent.persona_name} > {safe}")
    meta = []
    if intent:
        meta.append(f"intent={intent}")
    if mem:
        meta.append(f"mem={mem!r}")
    if meta:
        print(f"  [{'  '.join(meta)}]")
    # Append the bot's own line so multi-turn context builds up.
    agent._append_buffer(GROUP_ID, agent.persona_name, safe, agent.qq_bot_id)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--lang", default=os.getenv("AGENT_LANG", "en"),
                   help="agent language: en (default) or zh")
    p.add_argument("--admin", action="store_true",
                   help="speak as the configured admin (closer relationship)")
    p.add_argument("--name", default="you", help="your display name in the chat")
    args = p.parse_args()

    agent = _build_agent(args.lang.strip().lower())
    try:
        if not agent.enabled:
            print("LLM_API_KEY is not set. Copy .env.example to .env and fill it in "
                  "(only the primary model key is required for this trial).")
            return 1

        you_uid = ADMIN_ID if args.admin else "2001"
        you_name = (agent.admin_name or "admin") if args.admin else args.name
        default_mode = ADMIN_MODE if args.admin else "called"

        print(f"=== try_chat — lang={agent.agent_lang}, model={agent.model} ===")
        print(f"talking to '{agent.persona_name}' as '{you_name}'. /quit to exit, /reset to clear.\n")

        while True:
            try:
                line = input(f"{you_name}> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nbye")
                return 0
            if not line:
                continue
            if line in ("/quit", "/exit", "/q"):
                print("bye")
                return 0
            if line == "/reset":
                agent.buffers.pop(GROUP_ID, None)
                print("  (buffer cleared)")
                continue

            name, uid, mode, msg = you_name, you_uid, default_mode, line
            command, _, rest = line.partition(" ")
            if command == "/admin":
                name, uid, mode, msg = (agent.admin_name or "admin"), ADMIN_ID, ADMIN_MODE, rest
            elif line.startswith("/as "):
                rest = line[len("/as "):].strip()
                if " " in rest:
                    spk, msg = rest.split(" ", 1)
                    name, uid, mode = spk, "3001", "called"
                else:
                    print("  usage: /as Name your message")
                    continue
            if not msg.strip():
                continue

            try:
                await _turn(agent, name, uid, msg.strip(), mode)
            except Exception as e:
                print(f"  [error: {type(e).__name__}: {e}]")
            print()
    finally:
        await agent.aclose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
