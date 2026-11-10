"""`personagent shortcut`: an icon on the desktop and in the Start menu that
opens the window with no terminal behind it. Windows only."""
from __future__ import annotations

import argparse
import base64
import html
import os
import re
import subprocess
import sys
from pathlib import Path

from . import home as homes
from . import langs, window

WINDOWS = os.name == "nt"
LINK = "personagent.lnk"
# The desktop and the Start menu's Programs folder, wherever Windows keeps them.
EVERYWHERE = "@([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))"


def _quoted(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def target(home: Path) -> tuple[Path, str]:
    """What the icon runs: this install's Python without a console, on `home`."""
    python = Path(sys.executable)
    quiet = python.with_name("pythonw.exe")
    return (quiet if quiet.is_file() else python), f'-m persona_agent start --home "{home}"'


def script(home: Path, *, remove: bool = False, folders: list[Path] | None = None) -> str:
    """The PowerShell that writes the links, or takes them away."""
    where = "@(" + ", ".join(map(_quoted, folders)) + ")" if folders else EVERYWHERE
    if remove:
        return (f"foreach ($folder in {where}) {{ Remove-Item -LiteralPath "
                f"(Join-Path $folder {_quoted(LINK)}) -Force -ErrorAction SilentlyContinue }}")
    program, arguments = target(home)
    return "\n".join([
        "$ErrorActionPreference = 'Stop'",
        "$shell = New-Object -ComObject WScript.Shell",
        f"foreach ($folder in {where}) {{",
        f"  $link = $shell.CreateShortcut((Join-Path $folder {_quoted(LINK)}))",
        f"  $link.TargetPath = {_quoted(program)}",
        f"  $link.Arguments = {_quoted(arguments)}",
        f"  $link.WorkingDirectory = {_quoted(home)}",
        f"  $link.IconLocation = {_quoted(window.icon())}",
        "  $link.Description = 'personagent'",
        "  $link.Save()",
        "}"])


def run(source: str) -> str:
    """Run it; the answer is what went wrong, or ''."""
    # Encoded: a home or a user name outside ASCII survives any console code page.
    source = "[Console]::OutputEncoding = [Text.Encoding]::UTF8\n" + source
    encoded = base64.b64encode(source.encode("utf-16-le")).decode("ascii")
    try:
        done = subprocess.run(
            ["powershell", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-EncodedCommand", encoded],
            capture_output=True, timeout=60, stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as error:
        return str(error)
    if done.returncode == 0:
        return ""
    # An encoded command reports its errors as CLIXML; the first is the reason.
    said = re.search(r'<S S="Error">(.*?)</S>', done.stderr.decode("utf-8", errors="replace"), re.S)
    reason = re.sub(r"_x[0-9A-Fa-f]{4}_", " ", said.group(1)).strip() if said else ""
    return html.unescape(reason) or f"exit {done.returncode}"


def main(argv: list[str] | None = None, prog: str = "personagent shortcut") -> int:
    from .cli import COMMANDS
    parser = argparse.ArgumentParser(prog=prog, description=langs.term(COMMANDS["shortcut"][2]))
    parser.add_argument("--remove", action="store_true", help=langs.term("take the shortcuts away again"))
    args = parser.parse_args(argv)
    if not WINDOWS:
        print(langs.term("Shortcuts are made on Windows only. "
                         "Elsewhere, add `personagent` to your launcher yourself."))
        return 1
    if langs.under_uvx() and not args.remove:
        print(langs.term("uvx runs personagent from a temporary copy, which a shortcut cannot "
                         "point at. Install it first: uv tool install personagent"))
        return 1
    failed = run(script(homes.find_home(), remove=args.remove))
    if failed:
        print(langs.term(f"The shortcut could not be made: {failed}"))
        return 1
    print(langs.term("The personagent shortcuts are gone.") if args.remove
          else langs.term("personagent is on your desktop and in the Start menu."))
    return 0
