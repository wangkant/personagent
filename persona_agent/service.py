"""`personagent service`: keep `personagent up` running after a reboot. A
systemd user unit on Linux, a LaunchAgent on macOS; on Windows the app's own
start at sign-in."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from . import home as homes
from . import langs

LABEL = "com.github.wangkant.personagent"
DOCS = "https://github.com/wangkant/personagent/blob/main/docs/deploy.md"
LOG_NAME = "service.log"
# Seconds a stop may take: the platforms, AstrBot and the character stop in turn.
STOP_S = 45
RESTART_S = 10
# Where systemd looks for user units: the XDG base directory, not a personagent setting.
XDG_CONFIG = "XDG_CONFIG_HOME"


def system() -> str:
    """linux, macos or windows; anything else is treated as Linux."""
    if os.name == "nt":
        return "windows"
    return "macos" if sys.platform == "darwin" else "linux"


def name(home: Path) -> str:
    """The unit or label for `home`: the plain name for the usual home, a suffix for any other."""
    home = Path(home).resolve()
    usual = homes.CHECKOUT if homes.is_checkout() else homes.default_home()
    if home == Path(usual).resolve():
        return "personagent"
    return "personagent-" + hashlib.sha256(str(home).encode("utf-8")).hexdigest()[:8]


def command(home: Path) -> tuple[list[str], Path]:
    """What the service runs, and where: this installation's interpreter on `home`."""
    from .updates import _python

    argv = [_python(), "-m", "persona_agent", "--home", str(Path(home).resolve()), "up"]
    # `-m persona_agent` finds the package from a checkout's root.
    return argv, homes.CHECKOUT if homes.is_checkout() else Path(home).resolve()


def log_path(home: Path) -> Path:
    return Path(home).resolve() / "runtime" / "desktop" / LOG_NAME


# ---- Linux: systemd --user

def _unit_dir() -> Path:
    config = os.environ.get(XDG_CONFIG, "").strip()
    return (Path(config) if config else Path.home() / ".config") / "systemd" / "user"


def unit_path(home: Path) -> Path:
    return _unit_dir() / f"{name(home)}.service"


def _systemd_word(text: str) -> str:
    """One word of a unit file: % and $ would be expanded, quotes and backslashes escape."""
    text = text.replace("%", "%%").replace("$", "$$")
    if not any(c in text for c in ' \t"\'\\;'):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _systemd_path(path: Path) -> str:
    # A path setting takes the rest of the line as it is, specifiers aside.
    return str(path).replace("%", "%%")


def unit(home: Path) -> str:
    argv, cwd = command(home)
    return "\n".join([
        "[Unit]",
        f"Description=personagent ({_systemd_path(Path(home).resolve())})",
        f"Documentation={DOCS}",
        "",
        "[Service]",
        "Type=simple",
        f"WorkingDirectory={_systemd_path(cwd)}",
        "ExecStart=" + " ".join(_systemd_word(word) for word in argv),
        "Environment=PYTHONUNBUFFERED=1",
        # The log and every file it writes stay readable by this user only.
        "UMask=0077",
        "Restart=on-failure",
        # 2 is a refusal (set up first, a page without a password, already running): no loop.
        "RestartPreventExitStatus=2",
        f"RestartSec={RESTART_S}",
        # SIGTERM to `up` alone first: it stops the platforms and the character in order.
        "KillMode=mixed",
        f"TimeoutStopSec={STOP_S}",
        f"StandardOutput=append:{_systemd_path(log_path(home))}",
        "StandardError=inherit",
        "",
        "[Install]",
        "WantedBy=default.target",
        ""])


def _linux_plan(home: Path, action: str) -> list[list[str]]:
    service = f"{name(home)}.service"
    if action == "install":
        return [["systemctl", "--user", "daemon-reload"],
                ["systemctl", "--user", "enable", "--now", service],
                ["loginctl", "enable-linger", getpass.getuser()]]
    if action == "remove":
        return [["systemctl", "--user", "disable", "--now", service],
                ["systemctl", "--user", "daemon-reload"]]
    if action == "restart":
        return [["systemctl", "--user", "restart", service]]
    return [["systemctl", "--user", "is-enabled", service], ["systemctl", "--user", "is-active", service],
            ["loginctl", "show-user", getpass.getuser(), "--property=Linger"]]


# ---- macOS: launchd

def plist_path(home: Path) -> Path:
    suffix = name(home)[len("personagent"):]
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}{suffix}.plist"


def label(home: Path) -> str:
    return LABEL + name(home)[len("personagent"):]


def plist(home: Path) -> bytes:
    argv, cwd = command(home)
    log = str(log_path(home))
    return plistlib.dumps({
        "Label": label(home),
        "ProgramArguments": argv,
        "WorkingDirectory": str(cwd),
        "EnvironmentVariables": {"PYTHONUNBUFFERED": "1", "PERSONAGENT_SERVICE": "launchd"},
        "RunAtLoad": True,
        # Started again when it ends with an error, not after a clean stop.
        "KeepAlive": {"SuccessfulExit": False},
        "ThrottleInterval": RESTART_S,
        "ExitTimeOut": STOP_S,
        "ProcessType": "Background",
        "Umask": 0o077,
        "StandardOutPath": log,
        "StandardErrorPath": log,
    }, sort_keys=False)


def _domain() -> str:
    return f"gui/{os.getuid()}" if hasattr(os, "getuid") else "gui/501"


def _macos_plan(home: Path, action: str) -> list[list[str]]:
    target = f"{_domain()}/{label(home)}"
    if action == "install":
        # Out first, so a second install takes the new file.
        return [["launchctl", "bootout", target], ["launchctl", "bootstrap", _domain(), str(plist_path(home))],
                ["launchctl", "enable", target]]
    if action == "remove":
        return [["launchctl", "bootout", target]]
    if action == "restart":
        return [["launchctl", "kickstart", "-k", target]]
    return [["launchctl", "print", target]]


# ---- running it

def _run(argv: list[str]) -> tuple[int, str]:
    tool = shutil.which(argv[0])
    if tool is None:
        return 127, langs.term(f"{argv[0]} was not found")
    try:
        done = subprocess.run([tool, *argv[1:]], capture_output=True, text=True, timeout=60,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return done.returncode, (done.stdout + done.stderr).strip()


def _shown(argv: list[str]) -> str:
    return " ".join(f'"{word}"' if " " in word else word for word in argv)


def _refusal(home: Path) -> str:
    """Why `up` would not stay up on this home; '' when it would."""
    from . import pageaccess
    from .setup_wizard import command as spelled, env_get

    if langs.under_uvx():
        return langs.term("uvx runs personagent from a temporary copy, which a service cannot point at. "
                          "Install it first: uv tool install personagent")
    settings = pageaccess.read(home)
    problem = [f"{key}: {langs.term(sentence)}" for level, key, sentence in pageaccess.problems(settings)
               if level == "ERROR"]
    if problem:
        return "\n".join(problem)
    if not env_get(Path(home) / ".env", "LLM_API_KEY") and not settings.wanted:
        return langs.term(f"Finish the setup first ({spelled('start', home)}), or set PAGE_HOST and a page "
                          f"password to finish it on the page from another device; docs/deploy.md shows how.")
    return ""


def _windows(home: Path, action: str, dry: bool) -> int:
    from . import shortcut

    if action == "restart":
        print(langs.term("On Windows, quit personagent from its notification-area icon and open it again."))
        return 1
    if action == "status":
        try:
            found = shortcut.status(home)["startup"]
        except (RuntimeError, ValueError) as error:
            print(langs.term(f"Windows could not be asked: {error}"))
            return 1
        print(langs.term({"on": "Start at sign-in: on, for this home.",
                          "other": "Start at sign-in: on, but for another copy or home.",
                          "off": "Start at sign-in: off."}[found]))
        return 0 if found == "on" else 3
    source = shortcut.script(home, remove=action == "remove", kinds=shortcut.LOGIN)
    if dry:
        print(langs.term("On Windows the service is personagent's own start at sign-in: a shortcut in the "
                         "Startup folder that opens the app behind its notification-area icon. It would run:"))
        print(source)
        return 0
    if action == "install" and langs.under_uvx():
        print(langs.term("uvx runs personagent from a temporary copy, which a service cannot point at. "
                         "Install it first: uv tool install personagent"))
        return 1
    failed = shortcut.run(source)
    if failed:
        print(langs.term(f"Windows did not allow this change: {failed}"))
        return 1
    print(langs.term("personagent now starts when you sign in to Windows. On the page, App > Run in the "
                     "background keeps it running behind its notification-area icon.")
          if action == "install" else langs.term("personagent no longer starts when you sign in to Windows."))
    return 0


def main(argv: list[str] | None = None, prog: str = "personagent service") -> int:
    from .cli import COMMANDS
    parser = argparse.ArgumentParser(prog=prog, description=langs.term(COMMANDS["service"][2]), epilog=langs.term(
        "Linux: a systemd user unit, kept running after you log out by `loginctl enable-linger`. macOS: a "
        "LaunchAgent, which runs while you are logged in. Windows: the app's own start at sign-in. The "
        "service runs `personagent up` for this home with this installation's Python, starts it again "
        "after a failure, and writes its output to runtime/desktop/service.log."))
    parser.add_argument("action", choices=("install", "remove", "restart", "status"), help=langs.term("what to do"))
    parser.add_argument("--dry-run", action="store_true",
                        help=langs.term("print the file and the commands instead of running them"))
    args = parser.parse_args(argv)
    home = homes.find_home()
    kind = system()
    if kind == "windows":
        return _windows(home, args.action, args.dry_run)
    if args.action == "install":
        refusal = _refusal(home)
        if refusal:
            print(refusal, file=sys.stderr)
            return 1
    path = unit_path(home) if kind == "linux" else plist_path(home)
    plan = (_linux_plan if kind == "linux" else _macos_plan)(home, args.action)
    if args.dry_run:
        if args.action == "install":
            print(langs.term(f"It would write {path}:"))
            print(unit(home) if kind == "linux" else plist(home).decode("utf-8"))
        elif args.action == "remove":
            print(langs.term(f"It would remove {path}."))
        print(langs.term("And run:"))
        for step in plan:
            print("  " + _shown(step))
        return 0
    if args.action == "install":
        return _install(home, kind, path, plan)
    if args.action == "remove":
        return _remove(kind, path, plan)
    if args.action == "restart":
        return _restart(path, plan)
    return _status(home, kind, path, plan)


def _restart(path: Path, plan: list[list[str]]) -> int:
    if not path.is_file():
        print(langs.term("Not installed. `personagent service install` installs it."))
        return 3
    code, said = _run(plan[0])
    if code:
        print(langs.term(f"`{_shown(plan[0])}` failed: {said}"), file=sys.stderr)
        return 1
    print(langs.term("Restarted."))
    return 0


def _install(home: Path, kind: str, path: Path, plan: list[list[str]]) -> int:
    log = log_path(home)
    log.parent.mkdir(parents=True, exist_ok=True)
    # Made first, readable by this user only: it carries the page's local link.
    log.touch(exist_ok=True)
    os.chmod(log, 0o600)
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "linux":
        path.write_text(unit(home), encoding="utf-8")
    else:
        path.write_bytes(plist(home))
    lingers = True
    for step in plan:
        code, said = _run(step)
        if step[:2] == ["launchctl", "bootout"]:
            continue  # nothing was loaded yet
        if step[:2] == ["loginctl", "enable-linger"]:
            lingers = not code
            continue
        if code:
            print(langs.term(f"`{_shown(step)}` failed: {said}"), file=sys.stderr)
            return 1
    if lingers:
        print(langs.term(f"personagent runs as a service now and starts again after a reboot. Its output goes to {log}."))
    else:
        print(langs.term(f"personagent runs as a service now, while you are logged in. Its output goes to {log}."))
        print(langs.term(f"It runs while you are logged in. To keep it running after you log out and "
                         f"start it at boot, run: sudo loginctl enable-linger {getpass.getuser()}"))
    if kind == "macos":
        print(langs.term("A LaunchAgent runs while you are logged in: on a Mac that serves others, turn on "
                         "automatic login."))
    return 0


def _remove(kind: str, path: Path, plan: list[list[str]]) -> int:
    for step in plan:
        _run(step)  # one that was never loaded has nothing to stop
    path.unlink(missing_ok=True)
    if kind == "linux":
        _run(["systemctl", "--user", "daemon-reload"])
    print(langs.term(f"The service is removed ({path})."))
    return 0


def _status(home: Path, kind: str, path: Path, plan: list[list[str]]) -> int:
    if not path.is_file():
        print(langs.term("Not installed. `personagent service install` installs it."))
        return 3
    print(langs.term(f"Installed: {path}"))
    print(langs.term(f"Output: {log_path(home)}"))
    if kind == "linux":
        enabled, active, linger = (_run(step) for step in plan)
        print(langs.term(f"Starts at boot: {enabled[1] or '-'}; running now: {active[1] or '-'}."))
        if linger[1].strip().lower() != "linger=yes":
            print(langs.term(f"Lingering is off, so it stops when you log out. To keep it running, run: "
                             f"sudo loginctl enable-linger {getpass.getuser()}"))
        return 0 if active[0] == 0 else 3
    code, said = _run(plan[0])
    running = code == 0 and "state = running" in said
    print(langs.term("Running now: yes.") if running else langs.term("Running now: no."))
    return 0 if running else 3
