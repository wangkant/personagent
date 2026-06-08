"""One-shot bootstrap: virtualenv + deps + config templates.

    python quickstart.py

Idempotent — re-running just reports what's already in place.
Designed to be cross-platform (Linux / macOS / Windows).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _info(msg: str) -> None:
    print(f"[quickstart] {msg}")


def _bin_dir(venv: Path) -> Path:
    return venv / ("Scripts" if os.name == "nt" else "bin")


def ensure_venv() -> Path:
    venv = ROOT / ".venv"
    if venv.exists():
        _info(f".venv already exists at {venv}")
        return venv
    _info(f"creating virtualenv at {venv} ...")
    subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
    return venv


def ensure_deps(venv: Path) -> None:
    pip = _bin_dir(venv) / ("pip.exe" if os.name == "nt" else "pip")
    if not pip.exists():
        _info(f"pip not found in venv ({pip}); aborting")
        sys.exit(1)
    _info("installing dependencies (pip install -r requirements.txt) ...")
    subprocess.check_call([str(pip), "install", "--upgrade", "pip"])
    subprocess.check_call([str(pip), "install", "-r", str(ROOT / "requirements.txt")])


def _copy_template(template: str, target: str) -> None:
    src = ROOT / template
    dst = ROOT / target
    if dst.exists():
        _info(f"{target} already exists — skipping")
        return
    if not src.exists():
        _info(f"{template} missing — skipping (nothing to copy)")
        return
    shutil.copy(src, dst)
    _info(f"copied {template} → {target} (please edit this file)")


def main() -> None:
    venv = ensure_venv()
    ensure_deps(venv)
    _copy_template(".env.example", ".env")
    # Copy the language-appropriate persona example. AGENT_LANG defaults to 'en'
    # (the primary build); set AGENT_LANG=zh in your environment before running
    # this to seed the Chinese persona instead.
    lang = (os.getenv("AGENT_LANG") or "en").strip().lower()
    persona_src = f"data/persona.example.{lang}.txt"
    if not (ROOT / persona_src).exists():
        persona_src = "data/persona.example.en.txt"
    _copy_template(persona_src, "persona.txt")
    print()
    _info("done. next steps:")
    activate = (
        ".venv\\Scripts\\activate"
        if os.name == "nt"
        else "source .venv/bin/activate"
    )
    print(f"  1. edit .env (at minimum: DEEPSEEK_API_KEY, BOT_NAME)")
    print(f"  2. edit persona.txt (your bot's personality)")
    print(f"  3. activate venv: {activate}")
    print(f"  4. try it now, no QQ needed:  python try_chat.py")
    print(f"  5. for a live group, run:     python main.py")
    print()
    _info(
        "for a live deployment, set up NapCat (or another OneBot v11 client) "
        "separately and point its webhook to http://127.0.0.1:8080/webhook/qq"
    )


if __name__ == "__main__":
    main()
