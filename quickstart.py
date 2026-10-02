"""Checkout bootstrap: a virtualenv, the dependencies, then the setup questions.

    python quickstart.py

Creates .venv, installs requirements.txt, and runs the same setup as
`personagent init`: the AI service and key, the character, and optionally
AstrBot. `--astrbot DATA_DIR` connects AstrBot without questions. Safe to
re-run: existing files are kept, and the questions start from your answers.
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 10):
    sys.exit("personagent needs Python 3.10 or newer; this is Python "
             + sys.version.split()[0] + ". Get one at https://www.python.org/downloads/")

import argparse  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
from pathlib import Path  # noqa: E402

from persona_agent import home as homes  # noqa: E402
from persona_agent import setup_wizard  # noqa: E402
from persona_agent.setup_wizard import (  # noqa: E402
    PLATFORMS, PLUGIN_NAME, astrbot_platform_entry, astrbot_plugin_config,
    connect_astrbot, install_astrbot_plugin, read_astrbot_config, secure_env_file,
    set_env_values, write_astrbot_config, write_astrbot_platform, write_env)

# Kept importable from here for scripts written against this file.
__all__ = ["PLATFORMS", "PLUGIN_NAME", "astrbot_platform_entry", "astrbot_plugin_config",
           "connect_astrbot", "install_astrbot_plugin", "read_astrbot_config",
           "secure_env_file", "set_env_values", "write_astrbot_config",
           "write_astrbot_platform", "write_env", "main"]

ROOT = Path(__file__).resolve().parent
PROG = "python quickstart.py"


def _info(msg: str) -> None:
    print(f"[quickstart] {msg}")


def _bin_dir(venv: Path) -> Path:
    return venv / ("Scripts" if os.name == "nt" else "bin")


def _venv_python(venv: Path) -> Path:
    return _bin_dir(venv) / ("python.exe" if os.name == "nt" else "python")


def ensure_venv() -> Path:
    venv = ROOT / ".venv"
    if venv.exists():
        _info(f".venv already exists at {venv}")
        return venv
    _info(f"creating virtualenv at {venv} ...")
    subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
    return venv


def ensure_deps(venv: Path) -> None:
    # `python -m pip`: venvs made by some tools (uv) have no pip.exe shim.
    py = str(_venv_python(venv))
    _info("installing dependencies (pip install -r requirements.txt) ...")
    try:
        # Best effort: an old pip that works must not stop the bootstrap.
        subprocess.check_call([py, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    except subprocess.CalledProcessError:
        _info("pip self-upgrade failed - continuing with the bundled pip")
    subprocess.check_call([py, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=PROG, parents=[setup_wizard.init_parser(PROG, add_help=False)],
        description="Set up a checkout: create .venv, install requirements.txt, then "
                    "ask for the AI service, key and character (as `personagent init`). "
                    "Without a terminal, or with --no-input, nothing is asked.",
        epilog="Re-running is safe: existing files are kept, and the questions offer "
               "your current answers.")
    p.add_argument("--astrbot", metavar="DATA_DIR",
                   help="connect AstrBot without questions: copy the plugin, share a token "
                        "(a first run leaves the allowlists empty; later runs keep them)")
    qq = p.add_mutually_exclusive_group()
    qq.add_argument("--qq", dest="qq", action="store_const", const=True,
                    help="with --astrbot: route QQ through AstrBot too")
    qq.add_argument("--no-qq", dest="qq", action="store_const", const=False,
                    help="with --astrbot: stop routing QQ through AstrBot "
                         "(without either, QQ routing is left as it is)")
    p.add_argument("--platform", choices=tuple(PLATFORMS),
                   help="with --astrbot: switch on that adapter in AstrBot's own config, "
                        "using --token (and --app-token for slack, or --app-id and "
                        "--app-secret for lark)")
    p.add_argument("--token", default="", help=argparse.SUPPRESS)
    p.add_argument("--app-token", default="", help=argparse.SUPPRESS)
    p.add_argument("--app-id", default="", help=argparse.SUPPRESS)
    p.add_argument("--app-secret", default="", help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None) -> int:
    # Every flag is checked before anything is installed.
    parser = build_parser()
    args = parser.parse_args(argv)
    if (args.qq is not None or args.platform) and not args.astrbot:
        parser.error("--qq, --no-qq and --platform only make sense with --astrbot")

    venv = ensure_venv()
    ensure_deps(venv)
    python = str(_venv_python(venv))
    if args.astrbot:
        home = homes.find_home()
        setup_wizard.apply_flags(home, args)
        creds = setup_wizard.flag_platform_creds(args.platform or "", args.token,
                                                 args.app_token, args.app_id, args.app_secret)
        return setup_wizard.connect_without_questions(
            home, Path(args.astrbot), qq=args.qq, platform=args.platform or "", creds=creds,
            launcher=setup_wizard.Launcher(python=python, home=home))
    try:
        return setup_wizard.run(None, PROG, python=python, confirm_rerun=True, args=args)
    except (KeyboardInterrupt, EOFError):
        print()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
