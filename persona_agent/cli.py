"""The `personagent` command.

Each subcommand imports its module only when it runs, so `--home` is in the
environment before anything resolves a path or reads a setting.
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import textwrap

from persona_agent import langs
from persona_agent import __version__

# name -> (module, function, one-line help). The function takes (argv, prog).
COMMANDS = {
    "start": ("persona_agent.welcome", "main",
              "Open setup and chat in a window of their own"),
    "shortcut": ("persona_agent.shortcut", "main",
                 "Put personagent on the desktop and in the Start menu (Windows)"),
    "up": ("persona_agent.services", "main",
           "Start personagent and its connected chat platforms together"),
    "init": ("persona_agent.setup_wizard", "main",
             "Set up a home: model, key, character, language"),
    "chat": ("persona_agent.chat", "run",
             "Talk to the character in this terminal"),
    "demo": ("persona_agent.demo", "main",
             "Watch it stay quiet and learn from a correction"),
    "run": ("persona_agent.cli", "_run_server",
            "Start the service the connectors talk to"),
    "connect": ("persona_agent.setup_wizard", "connect_main",
                "Connect a chat platform, AstrBot or a coding assistant"),
    "mcp": ("persona_agent.coding", "mcp_main",
            "Serve the character over MCP (run by coding assistants, not by hand)"),
    "hook": ("persona_agent.coding", "hook_main",
             "React when a coding agent finishes a turn (run by coding assistants, not by hand)"),
    "doctor": ("persona_agent.doctor", "main",
               "Check the setup and every upstream service"),
    "learned": ("persona_agent.ledger_admin", "main",
                "Review, promote or roll back what it learned"),
    "memory": ("persona_agent.memory_admin", "main",
               "Look at what it remembers, forget an item or bring one back"),
    "eval": ("persona_agent.evals", "main",
             "Measure speaking, persona, learning and memory on labelled cases"),
}


def _run_server(argv: list[str], prog: str) -> int:
    p = argparse.ArgumentParser(prog=prog, description=langs.term(COMMANDS["run"][2]))
    p.add_argument("--host", default=None, help=langs.term("default SERVER_HOST or 127.0.0.1"))
    p.add_argument("--port", type=int, default=None, help=langs.term("default SERVER_PORT or 8080"))
    args = p.parse_args(argv)
    from persona_agent import server

    server.main(host=args.host, port=args.port)
    return 0


def _broken_without_a_terminal() -> int:
    """pythonw, as the shortcut starts it, has nowhere to print an install
    that does not import: it goes to the log, and a dialog names the log."""
    import traceback

    from persona_agent import home, window

    log = home.find_home() / "runtime" / "desktop" / "app.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as out:
        traceback.print_exc(file=out)
    window.alert(langs.term(f"personagent could not start. The details are in {log}."))
    return 1


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="personagent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.fill(langs.term("An agent that behaves like a person, on every platform you use: "
                    "it has a character of its own, remembers, learns from the people it talks to, "
                    "and judges for itself when to speak."), 78),
        # Raw, so the command list keeps one line per command.
        epilog=_usage() + "\n\n" + textwrap.fill(langs.term(
            "Run `personagent` to open local setup and chat. On a machine without a display, "
            "use `personagent up` (the service and its platforms) or `personagent run` (the service alone). "
            "Messages follow AGENT_LANG, else the system language."), 78))
    p.add_argument("--version", action="version", version=f"personagent {__version__}")
    p.add_argument("--home", metavar="DIR",
                   help=langs.term("the folder holding .env, persona.txt and runtime/ "
                        "(default: AGENT_HOME, this checkout, or ~/personagent)"))
    p.add_argument("command", nargs="?", choices=list(COMMANDS), metavar="command",
                   help=langs.term("one of the commands below"))
    p.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return p


def _usage() -> str:
    width = max(map(len, COMMANDS))
    lines = [f"  {name:<{width}}  {langs.term(spec[2])}" for name, spec in COMMANDS.items()]
    return langs.term("commands:") + "\n" + "\n".join(lines)


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
                raise SystemExit(langs.term("personagent: --home needs a folder"))
            home, i = args[i + 1], i + 2
        elif word.startswith("--home="):
            home, i = word[len("--home="):], i + 1
        else:
            rest.append(word)
            i += 1
    return home, rest


def main(argv: list[str] | None = None) -> int:
    langs.utf8_console()
    # argparse asks gettext for its own words: usage, options, its errors.
    argparse._ = langs.term
    p = _parser()
    args = p.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.command and langs.interactive():
        args.command = "start"
    if not args.command:
        p.print_help()
        return 0
    later_home, rest = _take_home(args.args)
    chosen = later_home or args.home
    if chosen:
        os.environ["AGENT_HOME"] = os.path.abspath(os.path.expanduser(chosen))
    module_name, func_name, _help = COMMANDS[args.command]
    try:
        func = getattr(importlib.import_module(module_name), func_name)
    except Exception:
        if sys.stderr is not None:
            raise
        return _broken_without_a_terminal()
    try:
        result = func(rest, f"personagent {args.command}")
    except SystemExit as stop:
        if {"-h", "--help"} & set(rest) and not stop.code:
            print(langs.term("\nAlso accepted: --home DIR, the folder holding .env, persona.txt and runtime/."))
        raise
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
