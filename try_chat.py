"""Try the agent in your terminal — no QQ, no NapCat, just an API key.

This drives the SAME reasoning path the live bot uses (persona + style guide +
JSON output protocol + the character-whitelist validator), so you can feel out a
persona and see replies before standing up a OneBot client.

    python try_chat.py
    python try_chat.py --owner          # speak as the configured owner
    python try_chat.py --lang zh         # force the Chinese variant
    python try_chat.py --name Alex       # your display name in the chat

Type a message and press enter. Commands:
    /owner <msg>   send this one line as the owner
    /as Name <msg> send as a one-off speaker called Name
    /reset         clear the conversation buffer
    /quit          exit
"""
from __future__ import annotations

import argparse
import asyncio
import os

from dotenv import load_dotenv

load_dotenv(override=True)

from agent import Agent  # noqa: E402

GROUP_ID = "trial"


def _build_agent(lang: str) -> Agent:
    return Agent(
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        bot_qq=os.getenv("BOT_QQ", "") or "10000",
        bot_name=os.getenv("BOT_NAME", "") or "bot",
        anthropic_private_model=os.getenv("ANTHROPIC_PRIVATE_MODEL", ""),
        owner_qq=os.getenv("OWNER_QQ", "") or "1969",
        owner_name=os.getenv("OWNER_NAME", "") or "owner",
        owner_relationship=os.getenv("OWNER_RELATIONSHIP", ""),
        fallback_model=os.getenv("FALLBACK_MODEL", ""),
        # Trial defaults: don't spend tokens self-scoring, and skip vision
        # (the terminal can't send images anyway).
        eval_enable=False,
        vision_model="",
        glm_api_key=os.getenv("GLM_API_KEY", ""),
        glm_base_url=os.getenv("GLM_BASE_URL", ""),
        tavily_key=os.getenv("TAVILY_API_KEY", ""),
        lang=lang,
    )


async def _turn(agent: Agent, name: str, uid: str, text: str, mode: str) -> None:
    agent._append_buffer(GROUP_ID, name, text, uid)
    reply, intent, mem = await agent._think(
        GROUP_ID, mode=mode, latest_text=text, caller_override=(name, uid),
    )
    safe = agent._sanitize_reply(reply, agent.agent_lang) if reply else ""
    if not safe or safe.strip().upper() == "PASS":
        print(f"  {agent.bot_name} > (stays quiet)")
        if reply and not safe:
            print(f"  [validator dropped raw reply: {reply[:60]!r}]")
        return
    print(f"  {agent.bot_name} > {safe}")
    meta = []
    if intent:
        meta.append(f"intent={intent}")
    if mem:
        meta.append(f"mem={mem!r}")
    if meta:
        print(f"  [{'  '.join(meta)}]")
    # Append the bot's own line so multi-turn context builds up.
    agent._append_buffer(GROUP_ID, agent.bot_name, safe, agent.bot_qq)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--lang", default=os.getenv("AGENT_LANG", "en"),
                   help="agent language: en (default) or zh")
    p.add_argument("--owner", action="store_true",
                   help="speak as the configured owner (closer relationship)")
    p.add_argument("--name", default="you", help="your display name in the chat")
    args = p.parse_args()

    agent = _build_agent(args.lang.strip().lower())
    if not agent.enabled:
        print("DEEPSEEK_API_KEY is not set. Copy .env.example to .env and fill it in "
              "(only the primary model key is required for this trial).")
        return 1

    you_uid = agent.owner_qq if args.owner else "2001"
    you_name = (agent.owner_name or "owner") if args.owner else args.name
    default_mode = "owner" if args.owner else "called"

    print(f"=== try_chat — lang={agent.agent_lang}, model={agent.model} ===")
    print(f"talking to '{agent.bot_name}' as '{you_name}'. /quit to exit, /reset to clear.\n")

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
        if line.startswith("/owner "):
            name, uid, mode, msg = (agent.owner_name or "owner"), agent.owner_qq, "owner", line[len("/owner "):]
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


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
