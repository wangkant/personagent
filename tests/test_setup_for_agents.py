"""docs/setup-for-agents.md, which coding agents follow word for word: every
personagent command in it parses with the real command line, and its tables
match the presets. Nothing is executed past argument parsing."""
from __future__ import annotations

import argparse
import importlib
import re
import shlex
from itertools import takewhile
from pathlib import Path

import pytest

from persona_agent import cli, setup_wizard

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "setup-for-agents.md"
RAW_URL = "https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md"
# Words before the package name that install it rather than run it.
PACKAGE_VERBS = {"install", "upgrade", "uninstall", "-U", "--upgrade"}
OPERATORS = set("();<>|&")


class Parsed(Exception):
    """A subcommand's parser accepted its arguments; stop before it acts."""


def _snippets(text: str) -> list[str]:
    """Each line of a fenced code block, and each inline code span outside one."""
    found, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif fenced:
            found.append(line)
        else:
            found += re.findall(r"`([^`]+)`", line)
    return found


def _words(snippet: str) -> list[str]:
    lexer = shlex.shlex(snippet, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:  # unbalanced quotes: prose, not a command
        return []


def _arguments(words: list[str]) -> list[str]:
    return list(takewhile(lambda w: not set(w) <= OPERATORS, words))


def _invocation(snippet: str) -> list[str] | None:
    """The arguments `snippet` gives personagent, or None if it does not run it."""
    words = _words(snippet)
    for i, word in enumerate(words):
        before = words[i - 1] if i else ""
        if word.startswith("/c "):  # the command line in `cmd /c '...'`
            return _invocation(word[3:])
        name = re.split(r"[\\/]", word)[-1].lower()
        if word == "persona_agent" and before == "-m":
            return _arguments(words[i + 1:])
        if name in ("personagent", "personagent.exe") or (
                before == "uvx" and name.startswith("personagent@")):
            if before in PACKAGE_VERBS:
                continue
            return _arguments(words[i + 1:])
    return None


def _commands() -> list[list[str]]:
    found = []
    for snippet in _snippets(DOC.read_text(encoding="utf-8")):
        if re.fullmatch(r"personagent \d+\.\d+\.\d+", snippet):
            continue  # what --version prints, not a command
        args = _invocation(snippet)
        if args is not None and args not in found:
            found.append(args)
    return found


COMMANDS = _commands()


def _parses(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> str:
    """The subcommand `argv` names once its own parser accepts the rest; '' for none."""
    try:
        top = cli._parser().parse_args(argv)
    except SystemExit as stop:  # --version and --help print and stop
        assert stop.code == 0, f"personagent {' '.join(argv)}"
        return ""
    if not top.command:
        return ""
    _home, rest = cli._take_home(top.args)
    module, func, _help = cli.COMMANDS[top.command]
    run = getattr(importlib.import_module(module), func)
    original = argparse.ArgumentParser.parse_args

    def stop_after_parsing(self, args=None, namespace=None):
        original(self, args, namespace)
        raise Parsed

    def stop(*_args, **_kwargs):
        raise Parsed

    from persona_agent import doctor, preflight

    with monkeypatch.context() as m:
        m.setattr(argparse.ArgumentParser, "parse_args", stop_after_parsing)
        # doctor reads its two flags by hand; these are its first steps after that.
        m.setattr(doctor, "_fix", stop)
        m.setattr(preflight, "retired_settings", stop)
        try:
            code = run(rest, f"personagent {top.command}")
        except Parsed:
            return top.command
        except SystemExit as exit_:
            code = exit_.code
    # Only a help text may end a command before it parses.
    assert code in (0, None) and {"-h", "--help"} & set(rest), f"personagent {' '.join(argv)}"
    return top.command


@pytest.fixture(autouse=True)
def _empty_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Commands that load .env before parsing find an empty home."""
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))


@pytest.mark.parametrize("argv", COMMANDS, ids=[" ".join(a) or "(none)" for a in COMMANDS])
def test_every_command_in_the_agent_guide_parses(argv, monkeypatch) -> None:
    _parses(argv, monkeypatch)


def test_the_guide_covers_the_whole_setup(monkeypatch) -> None:
    named = {_parses(argv, monkeypatch) for argv in COMMANDS}
    assert {"init", "demo", "start", "up", "connect", "doctor"} <= named
    assert ["start", "--no-browser"] in COMMANDS  # the Windows background start
    # The commands to run name the home (rule 9); a bare `personagent init` is a warning.
    inits = [a for a in COMMANDS if "init" in a and "--home" in a]
    assert inits and all("--no-input" in a for a in inits)
    # Left out, --lang and --persona fall back to other defaults than step 1's.
    assert all({"--lang", "--name", "--persona", "--provider"} <= set(a) for a in inits if "--key-env" not in a)


def test_the_background_start_returns_through_a_pipe() -> None:
    # A redirected or same-window Start-Process hands the page the caller's output pipe.
    starts = [s for s in _snippets(DOC.read_text(encoding="utf-8")) if "Start-Process" in s]
    assert any("cmd" in s for s in starts)
    assert not any(re.search(r"-Redirect|-NoNewWindow", s) for s in starts)


def test_the_tables_match_the_presets() -> None:
    text = DOC.read_text(encoding="utf-8")
    rows = set(re.findall(r"^\| `([a-z][a-z-]*)` \|", text, re.MULTILINE))
    assert rows == set(setup_wizard.PROVIDER_KEYS) | set(setup_wizard.PERSONA_KEYS)
    for provider in setup_wizard.PROVIDERS:
        row = re.search(rf"^\| `{re.escape(provider.key)}` \|[^|\n]*\|([^|\n]*)\|",
                        text, re.MULTILINE)
        assert row, provider.key
        if provider.model:
            assert f"`{provider.model}`" in row.group(1), provider.key


def test_the_readmes_and_start_guides_point_to_it() -> None:
    assert DOC.is_file()
    for readme in ("README.md", "README.zh-CN.md"):
        assert RAW_URL in (ROOT / readme).read_text(encoding="utf-8"), readme
    for start in ("start.md", "start.zh-CN.md"):
        assert "(setup-for-agents.md)" in (ROOT / "docs" / start).read_text(encoding="utf-8"), start
