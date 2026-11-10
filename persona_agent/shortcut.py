"""`personagent shortcut`: an icon on the desktop and in the Start menu that
opens the window with no terminal behind it. Windows only."""
from __future__ import annotations

import argparse
import base64
import html
import json
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
# Where each kind of link lives; Startup is the one that runs at sign-in.
SPECIAL = {"desktop": "Desktop", "programs": "Programs", "startup": "Startup"}
ICON = ("desktop", "programs")
LOGIN = ("startup",)
# "desktop;programs;startup" in place of the real folders, for tests and trial runs.
DIRS_ENV = "PERSONAGENT_SHORTCUT_DIRS"


def _quoted(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _override() -> dict[str, Path] | None:
    raw = os.environ.get(DIRS_ENV, "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(os.pathsep)]
    if len(parts) != len(SPECIAL) or not all(parts):
        # Never fall back to the real folders when someone meant to redirect them.
        raise ValueError(f"{DIRS_ENV} needs {len(SPECIAL)} folders")
    return {kind: Path(p) for kind, p in zip(SPECIAL, parts)}


def _where(kinds: tuple[str, ...]) -> str:
    override = _override()
    if override:
        return "@(" + ", ".join(_quoted(override[k]) for k in kinds) + ")"
    return "@(" + ", ".join(f"[Environment]::GetFolderPath('{SPECIAL[k]}')" for k in kinds) + ")"


def target(home: Path) -> tuple[Path, str]:
    """What the icon runs: this install's Python without a console, on `home`."""
    python = Path(sys.executable)
    quiet = python.with_name("pythonw.exe")
    return (quiet if quiet.is_file() else python), f'-m persona_agent start --home "{home}"'


def _arguments(base: str, kind: str) -> str:
    # At sign-in it stays behind its icon, when closing is set to keep it running.
    return base + " --background" if kind == "startup" else base


def script(home: Path, *, remove: bool = False, folders: list[Path] | None = None,
           kinds: tuple[str, ...] = ICON) -> str:
    """The PowerShell that writes the links, or takes them away."""
    where = "@(" + ", ".join(map(_quoted, folders)) + ")" if folders else _where(kinds)
    if remove:
        # A link that is not there is already removed; one that stays is a failure.
        return (f"foreach ($folder in {where}) {{ if (-not $folder) {{ continue }}; "
                f"$path = Join-Path $folder {_quoted(LINK)}; "
                f"if (Test-Path -LiteralPath $path) {{ Remove-Item -LiteralPath $path -Force -ErrorAction Stop }} }}")
    program, arguments = target(home)
    if kinds == LOGIN:
        arguments = _arguments(arguments, "startup")
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


def _powershell(source: str) -> tuple[str, str]:
    """Run it; (what it printed, what went wrong or '')."""
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
        return "", str(error)
    out = done.stdout.decode("utf-8", errors="replace")
    if done.returncode == 0:
        return out, ""
    # An encoded command reports its errors as CLIXML; the first is the reason.
    said = re.search(r'<S S="Error">(.*?)</S>', done.stderr.decode("utf-8", errors="replace"), re.S)
    reason = re.sub(r"_x[0-9A-Fa-f]{4}_", " ", said.group(1)).strip() if said else ""
    return out, html.unescape(reason) or f"exit {done.returncode}"


def run(source: str) -> str:
    """Run it; the answer is what went wrong, or ''."""
    return _powershell(source)[1]


def status(home: Path) -> dict[str, str]:
    """Each link kind: "on" (opens this install on `home`), "other" (opens
    something else) or "off". RuntimeError when Windows cannot be asked."""
    pairs = ", ".join(f"@({_quoted(kind)}, {_where((kind,))}[0])" for kind in SPECIAL)
    source = "\n".join([
        "$ErrorActionPreference = 'Stop'",
        "$shell = New-Object -ComObject WScript.Shell",
        "$found = @()",
        f"foreach ($pair in @({pairs})) {{",
        "  if (-not $pair[1]) { continue }",
        f"  $path = Join-Path $pair[1] {_quoted(LINK)}",
        "  if (Test-Path -LiteralPath $path) {",
        "    $link = $shell.CreateShortcut($path)",
        "    $found += [pscustomobject]@{kind = $pair[0]; target = $link.TargetPath; arguments = $link.Arguments}",
        "  }",
        "}",
        "ConvertTo-Json -InputObject @($found) -Compress"])
    out, failed = _powershell(source)
    if failed:
        raise RuntimeError(failed)
    try:
        found = json.loads(out.strip() or "[]")
    except ValueError:
        raise RuntimeError("unreadable answer") from None
    program, arguments = target(home)
    result = dict.fromkeys(SPECIAL, "off")
    for item in found if isinstance(found, list) else [found]:
        kind = str(item.get("kind") or "") if isinstance(item, dict) else ""
        if kind in result:
            same = (os.path.normcase(str(item.get("target") or "")) == os.path.normcase(str(program))
                    and str(item.get("arguments") or "") == _arguments(arguments, kind))
            result[kind] = "on" if same else "other"
    return result


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
        print(langs.term(f"The shortcuts could not be removed: {failed}") if args.remove
              else langs.term(f"The shortcut could not be made: {failed}"))
        return 1
    print(langs.term("The personagent shortcuts are gone.") if args.remove
          else langs.term("personagent is on your desktop and in the Start menu."))
    return 0
