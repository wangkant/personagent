"""One-shot bootstrap: virtualenv + deps + config templates + setup wizard.

    python quickstart.py

After installing the environment it walks you through first-time
configuration interactively (API provider, key, bot name, language - and
optionally the live-QQ settings), writes the answers into `.env`, and can
drop you straight into a terminal chat. No manual .env editing needed.

Idempotent - re-running reports what's already in place and only offers the
wizard again if you want to reconfigure. Non-interactive environments (CI,
piped stdin) or `--no-input` skip the wizard and behave like the classic
bootstrap.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Provider presets for the wizard. base_url is the OpenAI-compatible root the
# agent appends /v1/chat/completions to; model is the suggested default.
PROVIDERS = [
    ("DeepSeek", "https://api.deepseek.com", "deepseek-chat"),
    ("Moonshot / Kimi", "https://api.moonshot.cn", "kimi-k2-turbo-preview"),
    ("OpenAI", "https://api.openai.com", "gpt-4o-mini"),
    ("Ollama (local)", "http://localhost:11434", "qwen3"),
    ("Other OpenAI-compatible", "", ""),
]

NAPCAT_SNIPPET = """{
  "http": { "enable": true, "host": "0.0.0.0", "port": 3000 },
  "webhook": {
    "enable": true,
    "url": "http://127.0.0.1:8080/webhook/qq",
    "timeout": 5000
  }
}"""


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
    # `python -m pip` rather than the pip.exe shim: venvs created by some
    # tools (e.g. uv) ship pip as a module without the console script.
    py = str(_venv_python(venv))
    _info("installing dependencies (pip install -r requirements.txt) ...")
    try:
        # Best-effort: an old-but-working pip must not abort the bootstrap.
        subprocess.check_call([py, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    except subprocess.CalledProcessError:
        _info("pip self-upgrade failed - continuing with the bundled pip")
    subprocess.check_call([py, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])


def _copy_template(template: str, target: str) -> None:
    src = ROOT / template
    dst = ROOT / target
    if dst.exists():
        _info(f"{target} already exists - skipping")
        return
    if not src.exists():
        _info(f"{template} missing - skipping (nothing to copy)")
        return
    shutil.copy(src, dst)
    _info(f"copied {template} -> {target}")


def copy_persona_template(lang: str) -> None:
    persona_src = f"data/persona.example.{lang}.txt"
    if not (ROOT / persona_src).exists():
        persona_src = "data/persona.example.en.txt"
    _copy_template(persona_src, "persona.txt")


# ---------------------------------------------------------------------------
# .env editing
# ---------------------------------------------------------------------------

def set_env_values(env_text: str, values: dict) -> str:
    """Return env_text with each KEY=... line replaced by KEY=<value>.

    Only the first uncommented occurrence of a key is rewritten; comments and
    everything else are preserved so .env keeps doubling as the annotated
    reference. Keys that don't exist yet are appended at the end.
    """
    lines = env_text.splitlines()
    remaining = dict(values)
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if m and m.group(1) in remaining:
            key = m.group(1)
            lines[i] = f"{key}={remaining.pop(key)}"
    for key, value in remaining.items():
        lines.append(f"{key}={value}")
    out = "\n".join(lines)
    if env_text.endswith("\n") and not out.endswith("\n"):
        out += "\n"
    return out


def write_env(env_path: Path, values: dict) -> None:
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    env_path.write_text(set_env_values(text, values), encoding="utf-8")


def _env_current_key(env_path: Path) -> str:
    """The currently-configured API key in .env ('' if blank/missing)."""
    if not env_path.exists():
        return ""
    m = re.search(r"^DEEPSEEK_API_KEY=(.*)$", env_path.read_text(encoding="utf-8"),
                  re.MULTILINE)
    return (m.group(1).strip() if m else "")


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------

def _ask(prompt: str, default: str = "", required: bool = False) -> str:
    """input() with a shown default; re-asks while a required answer is empty."""
    suffix = f" [{default}]" if default else ""
    while True:
        answer = input(f"  {prompt}{suffix}: ").strip()
        if not answer:
            answer = default
        if answer or not required:
            return answer
        print("    (required - please enter a value)")


def _ask_yn(prompt: str, default_yes: bool = True) -> bool:
    d = "Y/n" if default_yes else "y/N"
    answer = input(f"  {prompt} [{d}]: ").strip().lower()
    if not answer:
        return default_yes
    return answer.startswith("y")


def _probe_key(venv: Path, base_url: str, api_key: str, model: str) -> bool:
    """Fire a 1-token test call through the venv's python (httpx lives there,
    not necessarily in the interpreter running this script)."""
    code = (
        "import sys, httpx\n"
        "base, key, model = sys.argv[1:4]\n"
        "r = httpx.post(base.rstrip('/') + '/v1/chat/completions',\n"
        "    headers={'Authorization': 'Bearer ' + key},\n"
        "    json={'model': model, 'max_tokens': 1,\n"
        "          'messages': [{'role': 'user', 'content': 'hi'}]},\n"
        "    timeout=30)\n"
        "print('    HTTP', r.status_code, '' if r.status_code == 200 else r.text[:200])\n"
        "sys.exit(0 if r.status_code == 200 else 1)\n"
    )
    try:
        return subprocess.call(
            [str(_venv_python(venv)), "-c", code, base_url, api_key, model],
            cwd=str(ROOT),
        ) == 0
    except OSError as e:
        print(f"    probe could not run ({e}); skipping")
        return True


def run_wizard(venv: Path, env_path: Path) -> None:
    print()
    print("-- First-time setup ------------------------------------------")
    print("  Answers are written to .env (which stays your annotated")
    print("  reference - only the relevant lines are filled in).")
    print()

    # 1. Provider
    print("  Which chat API will the bot use?")
    for i, (name, base, model) in enumerate(PROVIDERS, 1):
        hint = f" ({base})" if base else ""
        print(f"    {i}. {name}{hint}")
    while True:
        choice = _ask("Choose 1-5", default="1")
        if choice in {"1", "2", "3", "4", "5"}:
            break
        print("    (enter a number 1-5)")
    name, base_url, model = PROVIDERS[int(choice) - 1]
    if not base_url:
        base_url = _ask("Base URL (OpenAI-compatible root, no /v1)", required=True)
    model = _ask("Model name", default=model, required=True)

    # 2. Key (local providers like ollama don't need a real one)
    api_key = _ask("API key", default="ollama" if "localhost" in base_url else "",
                   required=True)

    # 3. Bot identity + language
    bot_name = _ask("Bot display name (what group members call it)",
                    default="Nova", required=True)
    lang = ""
    while lang not in ("en", "zh"):
        lang = _ask("Language - en or zh", default="en").lower()

    values = {
        "DEEPSEEK_API_KEY": api_key,
        "DEEPSEEK_BASE_URL": base_url,
        "DEEPSEEK_MODEL": model,
        "BOT_NAME": bot_name,
        "AGENT_LANG": lang,
    }

    # 4. Live QQ deployment (optional)
    print()
    live = _ask_yn("Deploy to a live QQ group (needs NapCat + a spare QQ "
                   "account)? Choosing no still lets you chat in the terminal",
                   default_yes=False)
    if live:
        values["BOT_QQ"] = _ask("Bot account's QQ number", required=True)
        values["QQ_GROUPS"] = _ask("Group ID(s) to listen on, comma-separated "
                                   "(empty = every group)")
        owner_qq = _ask("Owner QQ - a 'favorite person' the bot is closer to "
                        "(Enter to skip)")
        if owner_qq:
            values["OWNER_QQ"] = owner_qq
            owner_name = _ask("Owner display name", required=True)
            values["OWNER_NAME"] = owner_name

    write_env(env_path, values)
    copy_persona_template(lang)
    _info("wrote your answers to .env")

    # 5. Optional key probe
    if _ask_yn("Test the API key now (one 1-token call)?", default_yes=True):
        if _probe_key(venv, base_url, api_key, model):
            print("    key works: OK")
        else:
            print("    the test call FAILED - double-check the key/base URL in")
            print("    .env later; everything else is already saved.")

    # 6. Next steps / hand-off
    print()
    print("-- Setup complete --------------------------------------------")
    print(f"  persona:  edit persona.txt to shape who {bot_name} is")
    if live:
        print()
        print("  NapCat: log in a spare QQ account, then paste this into its")
        print("  OneBot HTTP config (http server + webhook -> this agent):")
        print()
        for line in NAPCAT_SNIPPET.splitlines():
            print(f"    {line}")
        print()
        print("  then start the agent with:")
        print(f"    {_venv_python(venv)} main.py")
        print()
    if _ask_yn("Chat with the bot in this terminal right now?", default_yes=True):
        cmd = [str(_venv_python(venv)), "try_chat.py"]
        if lang == "zh":
            cmd += ["--lang", "zh"]
        print()
        subprocess.call(cmd, cwd=str(ROOT))
    else:
        print(f"  try it any time:  {_venv_python(venv)} try_chat.py")


def main() -> None:
    no_input = "--no-input" in sys.argv
    venv = ensure_venv()
    ensure_deps(venv)
    _copy_template(".env.example", ".env")
    env_path = ROOT / ".env"

    interactive = not no_input and sys.stdin.isatty()
    if interactive:
        if _env_current_key(env_path):
            _info(".env already has an API key configured")
            if not _ask_yn("Run the setup wizard again anyway?", default_yes=False):
                _info("keeping the existing configuration. done.")
                return
        run_wizard(venv, env_path)
        return

    # Classic non-interactive bootstrap (CI / piped stdin / --no-input).
    lang = (os.getenv("AGENT_LANG") or "en").strip().lower()
    copy_persona_template(lang)
    print()
    _info("done. next steps:")
    activate = (
        ".venv\\Scripts\\activate"
        if os.name == "nt"
        else "source .venv/bin/activate"
    )
    print("  1. edit .env (at minimum: DEEPSEEK_API_KEY, BOT_NAME)")
    print("  2. edit persona.txt (your bot's personality)")
    print(f"  3. activate venv: {activate}")
    print("  4. try it now, no QQ needed:  python try_chat.py")
    print("  5. for a live group, run:     python main.py")
    print()
    _info(
        "for a live deployment, set up NapCat (or another OneBot v11 client) "
        "separately and point its webhook to http://127.0.0.1:8080/webhook/qq"
    )


if __name__ == "__main__":
    main()
