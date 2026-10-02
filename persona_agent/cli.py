"""The `personagent` command.

Each subcommand imports its module only when it runs, so `--home` is in the
environment before anything resolves a path or reads a setting.
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys

from persona_agent import __version__

# name -> (module, function, one-line help). The function takes (argv, prog).
COMMANDS = {
    "init": ("persona_agent.setup_wizard", "main",
             "set up a home: model, key, character, language"),
    "chat": ("persona_agent.chat", "run",
             "talk to the character in this terminal"),
    "demo": ("persona_agent.demo", "main",
             "watch it stay quiet and learn from a correction"),
    "run": ("persona_agent.cli", "_run_server",
            "start the service the connectors talk to"),
    "connect": ("persona_agent.setup_wizard", "connect_main",
                "connect a chat platform (AstrBot)"),
    "doctor": ("persona_agent.cli", "_doctor",
               "check the setup and every upstream service"),
    "learned": ("persona_agent.ledger_admin", "main",
                "review, promote or roll back what it learned"),
    "eval": ("persona_agent.evals", "main",
             "measure speaking, persona and learning on labelled cases"),
}


def _run_server(argv: list[str], prog: str) -> int:
    p = argparse.ArgumentParser(prog=prog, description=COMMANDS["run"][2])
    p.add_argument("--host", default=None, help="default SERVER_HOST or 127.0.0.1")
    p.add_argument("--port", type=int, default=None, help="default SERVER_PORT or 8080")
    args = p.parse_args(argv)
    from persona_agent import server

    server.main(host=args.host, port=args.port)
    return 0


def _doctor(argv: list[str], prog: str) -> int:
    from persona_agent import doctor

    return doctor.main(argv, prog)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="personagent",
        description="A character for your group chats that knows when to stay "
                    "quiet, and learns from being corrected.",
        epilog="Start with `personagent init`, then `personagent chat`.")
    p.add_argument("--version", action="version", version=f"personagent {__version__}")
    p.add_argument("--home", metavar="DIR",
                   help="the folder holding .env, persona.txt and runtime/ "
                        "(default: AGENT_HOME, this checkout, or ~/personagent)")
    p.add_argument("command", nargs="?", choices=list(COMMANDS), metavar="command",
                   help=", ".join(COMMANDS))
    p.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return p


def _usage() -> str:
    width = max(map(len, COMMANDS))
    lines = [f"  {name:<{width}}  {spec[2]}" for name, spec in COMMANDS.items()]
    return "commands:\n" + "\n".join(lines)


def _take_home(args: list[str]) -> tuple[str | None, list[str]]:
    """Pull `--home DIR` out of the words after the command, so it works there too."""
    home, rest, i = None, [], 0
    while i < len(args):
        word = args[i]
        if word == "--":
            rest += args[i:]
            break
        if word == "--home":
            if i + 1 >= len(args):
                raise SystemExit("personagent: --home needs a folder")
            home, i = args[i + 1], i + 2
        elif word.startswith("--home="):
            home, i = word[len("--home="):], i + 1
        else:
            rest.append(word)
            i += 1
    return home, rest


def main(argv: list[str] | None = None) -> int:
    p = _parser()
    args = p.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.command:
        p.print_help()
        print()
        print(_usage())
        return 0
    later_home, rest = _take_home(args.args)
    chosen = later_home or args.home
    if chosen:
        os.environ["AGENT_HOME"] = os.path.abspath(os.path.expanduser(chosen))
    module_name, func_name, _help = COMMANDS[args.command]
    func = getattr(importlib.import_module(module_name), func_name)
    try:
        result = func(rest, f"personagent {args.command}")
    except SystemExit as stop:
        if {"-h", "--help"} & set(rest) and not stop.code:
            print("\nAlso accepted: --home DIR, the folder holding .env, persona.txt and runtime/.")
        raise
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
