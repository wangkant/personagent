"""One-shot bootstrap: virtualenv + deps + config templates + setup wizard.

    python quickstart.py

After installing the environment it walks you through first-time
configuration interactively (API provider, key, bot name, language), writes
the answers into `.env`, can connect the agent to an AstrBot install (copies
the forwarder plugin, generates the shared token, writes the allowlists), and
can drop you straight into a terminal chat. No manual editing needed.

Idempotent - re-running reports what's already in place and only offers the
wizard again if you want to reconfigure. Non-interactive environments (CI,
piped stdin) or `--no-input` skip the wizard and behave like the classic
bootstrap.
"""
from __future__ import annotations

import json
import os
import re
import secrets
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

PLUGIN_NAME = "astrbot_plugin_llm_persona_gateway"
PLUGIN_SRC = ROOT / "integrations" / "astrbot" / PLUGIN_NAME


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
    updated = set_env_values(text, values)
    # Temp file then replace, because this is the file holding live API keys
    # and a raw write_text truncates before it writes: a Ctrl-C in the wizard
    # left an empty .env. `persona_agent.storage.atomic_write_text` does
    # exactly this, but quickstart runs BEFORE the dependencies it installs,
    # which is the whole point of quickstart, so it cannot import it.
    # `.env.tmp` is in .gitignore and in the test suite's PII watch list. It
    # holds the same API keys `.env` does, and an interruption between these
    # two lines — the exact interruption this atomicity exists for — leaves it
    # on disk for `git add -A` to stage.
    tmp = env_path.with_name(env_path.name + ".tmp")
    tmp.write_text(updated, encoding="utf-8")
    try:
        # Carry the original's permissions across, or os.replace hands the
        # secrets file a fresh umask-default mode and quietly widens a
        # deliberate `chmod 600`. No-op on Windows.
        if env_path.exists():
            os.chmod(tmp, env_path.stat().st_mode & 0o7777)
    except OSError:
        pass
    os.replace(tmp, env_path)


def _env_get(env_path: Path, key: str) -> str:
    """The current value of ``key`` in .env ('' if blank/missing)."""
    if not env_path.exists():
        return ""
    m = re.search(rf"^{key}=(.*)$", env_path.read_text(encoding="utf-8"), re.MULTILINE)
    return (m.group(1).strip() if m else "")


def _env_current_key(env_path: Path) -> str:
    return _env_get(env_path, "LLM_API_KEY")


# ---------------------------------------------------------------------------
# AstrBot: the plugin, its config file, the shared token
# ---------------------------------------------------------------------------

def find_astrbot_data() -> Path | None:
    """A likely AstrBot data directory next to this checkout or under $HOME."""
    home = Path.home()
    for cand in (ROOT.parent / "astrbot" / "data", ROOT.parent / "AstrBot" / "data",
                 home / "AstrBot" / "data", home / "astrbot" / "data"):
        if (cand / "plugins").is_dir():
            return cand
    return None


def install_astrbot_plugin(data_dir: Path) -> Path:
    """Copy the forwarder into ``<data>/plugins/``; safe to repeat."""
    dest = data_dir / "plugins" / PLUGIN_NAME
    shutil.copytree(PLUGIN_SRC, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def astrbot_plugin_config(existing: dict | None, *, agent_url: str, token: str,
                          qq: bool, groups: list[str], private: list[str]) -> dict:
    """The plugin's config document. Keys we do not manage are kept."""
    cfg = dict(existing or {})
    cfg["agent_url"] = agent_url
    cfg["gateway_token"] = token
    cfg["excluded_platforms"] = [] if qq else ["aiocqhttp"]
    cfg["group_whitelist"] = [str(g).strip() for g in groups if str(g).strip()]
    cfg["private_whitelist"] = [str(u).strip() for u in private if str(u).strip()]
    cfg["private_enabled"] = bool(cfg["private_whitelist"])
    cfg.setdefault("timeout_s", 180)
    cfg.setdefault("block_default", True)
    return cfg


def astrbot_config_path(data_dir: Path) -> Path:
    return data_dir / "config" / f"{PLUGIN_NAME}_config.json"


def write_astrbot_config(data_dir: Path, cfg: dict) -> Path:
    path = astrbot_config_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def read_astrbot_config(data_dir: Path) -> dict:
    path = astrbot_config_path(data_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))  # AstrBot writes a BOM
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def connect_astrbot(env_path: Path, values: dict, *, data_dir: Path, qq: bool,
                    groups: list[str], private: list[str]) -> Path:
    """Install the plugin and write both halves of the handshake: the shared
    token into .env (via ``values``) and the plugin config into AstrBot."""
    token = values.get("GATEWAY_TOKEN") or _env_get(env_path, "GATEWAY_TOKEN") \
        or secrets.token_urlsafe(32)
    values["GATEWAY_TOKEN"] = token
    values["GATEWAY_NATIVE_PLATFORMS"] = "aiocqhttp" if qq else ""
    port = _env_get(env_path, "PORT") or "8080"
    install_astrbot_plugin(data_dir)
    cfg = astrbot_plugin_config(
        read_astrbot_config(data_dir),
        agent_url=f"http://127.0.0.1:{port}/webhook/gateway", token=token,
        qq=qq, groups=groups, private=private)
    return write_astrbot_config(data_dir, cfg)


def _split_ids(raw: str) -> list[str]:
    return [x.strip() for x in raw.replace("，", ",").split(",") if x.strip()]


# AstrBot platform adapters the wizard can switch on. The shapes are AstrBot's
# own (its config template, 4.25); we only fill the credential fields.
PLATFORMS = {
    "telegram": (("telegram_token", "Telegram bot token (from @BotFather)"),),
    "discord": (("discord_token", "Discord bot token"),),
    "slack": (("bot_token", "Slack bot token (xoxb-...)"),
              ("app_token", "Slack app-level token (xapp-..., Socket Mode)")),
    "kook": (("kook_bot_token", "KOOK bot token"),),
    "lark": (("app_id", "Lark / Feishu app id"), ("app_secret", "Lark / Feishu app secret")),
}
_PLATFORM_DEFAULTS = {
    "telegram": {"start_message": "", "telegram_api_base_url": "https://api.telegram.org/bot",
                 "telegram_file_base_url": "https://api.telegram.org/file/bot",
                 "telegram_command_register": False, "telegram_command_auto_refresh": False,
                 "telegram_command_register_interval": 300, "telegram_polling_restart_delay": 5.0},
    "discord": {"discord_proxy": "", "discord_command_register": False,
                "discord_activity_name": "", "discord_allow_bot_messages": False},
    "slack": {"signing_secret": "", "slack_connection_mode": "socket", "unified_webhook_mode": True,
              "webhook_uuid": "", "slack_webhook_host": "0.0.0.0", "slack_webhook_port": 6197,
              "slack_webhook_path": "/astrbot-slack-webhook/callback"},
    "kook": {"kook_reconnect_delay": 1, "kook_max_reconnect_delay": 60, "kook_max_retry_delay": 60,
             "kook_heartbeat_interval": 30, "kook_heartbeat_timeout": 6,
             "kook_max_heartbeat_failures": 3, "kook_max_consecutive_failures": 5},
    "lark": {"domain": "https://open.feishu.cn", "lark_connection_mode": "socket",
             "webhook_uuid": "", "lark_encrypt_key": "", "lark_verification_token": ""},
}


def astrbot_platform_entry(kind: str, creds: dict) -> dict:
    """One entry for AstrBot's `platform` list."""
    if kind not in PLATFORMS:
        raise ValueError(f"unknown platform {kind!r}; one of {', '.join(PLATFORMS)}")
    missing = [key for key, _ in PLATFORMS[kind] if not creds.get(key)]
    if missing:
        raise ValueError(f"{kind} needs {', '.join(missing)}")
    entry = {"id": kind, "type": kind, "enable": True}
    entry.update(_PLATFORM_DEFAULTS[kind])
    entry.update({key: creds[key] for key, _ in PLATFORMS[kind]})
    return entry


def astrbot_main_config_path(data_dir: Path) -> Path:
    return data_dir / "cmd_config.json"


def write_astrbot_platform(data_dir: Path, entry: dict) -> Path:
    """Add or replace the entry with the same id in AstrBot's cmd_config.json.
    AstrBot must have started once (the file is its), and reads it on start."""
    path = astrbot_main_config_path(data_dir)
    cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    platforms = cfg.get("platform")
    if not isinstance(platforms, list):
        platforms = []
    platforms = [p for p in platforms if not (isinstance(p, dict) and p.get("id") == entry["id"])]
    platforms.append(entry)
    cfg["platform"] = platforms
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


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
    for i, (name, base, _model) in enumerate(PROVIDERS, 1):
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
        "LLM_API_KEY": api_key,
        "LLM_BASE_URL": base_url,
        "LLM_MODEL": model,
        "BOT_NAME": bot_name,
        "AGENT_LANG": lang,
    }

    # 4. Connect to AstrBot (optional): the plugin, the token, the allowlists.
    print()
    astrbot_data = None
    live = _ask_yn("Connect to an AstrBot install now (its plugin gets copied "
                   "and configured for you)? Choosing no still lets you chat "
                   "in the terminal", default_yes=False)
    if live:
        guess = find_astrbot_data()
        while True:
            raw = _ask("AstrBot data directory (the one holding plugins/ and config/)",
                       default=str(guess) if guess else "", required=True)
            astrbot_data = Path(raw).expanduser()
            if (astrbot_data / "plugins").is_dir():
                break
            print(f"    no plugins/ folder under {astrbot_data}; start AstrBot once, "
                  "or give the path to its data directory")
        qq = _ask_yn("Include QQ through AstrBot's aiocqhttp adapter?", default_yes=True)
        if qq:
            values["BOT_QQ"] = _ask("Bot account's QQ number", required=True)
            owner_qq = _ask("Owner QQ - a 'favorite person' the bot is closer to "
                            "(Enter to skip)")
            if owner_qq:
                values["OWNER_QQ"] = owner_qq
                values["OWNER_NAME"] = _ask("Owner display name", required=True)
        groups = _split_ids(_ask("Group / channel IDs the persona should join, "
                                 "comma-separated (as AstrBot shows them; "
                                 "empty = none yet)"))
        private = _split_ids(_ask("Sender IDs allowed to DM it, comma-separated "
                                  "(empty = no DMs)"))
        if qq:
            values["QQ_GROUPS"] = ",".join(g for g in groups if g.isdigit())
        cfg_path = connect_astrbot(env_path, values, data_dir=astrbot_data,
                                   qq=qq, groups=groups, private=private)
        _info(f"plugin installed under {astrbot_data / 'plugins' / PLUGIN_NAME}")
        _info(f"plugin config written to {cfg_path}")
        if astrbot_main_config_path(astrbot_data).exists():
            kind = _ask("Also switch on a platform in AstrBot now - "
                        + " / ".join(PLATFORMS) + " (Enter to skip)").lower()
            if kind in PLATFORMS:
                creds = {key: _ask(prompt, required=True) for key, prompt in PLATFORMS[kind]}
                write_astrbot_platform(astrbot_data, astrbot_platform_entry(kind, creds))
                _info(f"{kind} adapter written to AstrBot's config; it comes up on the next restart")
            elif kind:
                print(f"    (unknown platform {kind!r}; skipped - add it in AstrBot's WebUI)")

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
        print("  AstrBot: restart it (or reload plugins in its WebUI) so it picks")
        print("  up the forwarder; the shared token is already in both places.")
        print("  Platforms (QQ, Telegram, ...) are configured in AstrBot itself.")
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


USAGE = """\
usage: python quickstart.py [--no-input] [--astrbot DATA_DIR [--qq] [--platform KIND --token T ...]]

Sets the project up: creates .venv, installs requirements.txt, copies
.env.example to .env and persona.example to persona.txt, then runs a short
wizard to fill in the API key and bot name and, if you want, to connect the
agent to an AstrBot install (plugin copied, shared token generated and
written to both sides, allowlists written).

  --no-input          skip the wizard (classic bootstrap; also implied by a
                      non-interactive stdin, e.g. CI or a pipe)
  --astrbot DATA_DIR  without the wizard: install and configure the AstrBot
                      plugin against that data directory (allowlists stay
                      empty; fill them in the plugin config or the WebUI)
  --qq                with --astrbot: route QQ through AstrBot too
                      (GATEWAY_NATIVE_PLATFORMS=aiocqhttp)
  --platform KIND     with --astrbot: switch on that adapter in AstrBot's own
                      config (telegram, discord, slack, kook, lark), using
                      --token T (and --app-token T for slack, or
                      --app-id ID --app-secret S for lark)

Re-running is safe: existing files are kept, and the wizard asks before
reconfiguring anything already set.
"""


def main() -> None:
    # ARGV IS PARSED BEFORE ANYTHING HAPPENS. The only argv handling used to
    # be `"--no-input" in sys.argv`, so `python quickstart.py --help` fell
    # straight through to ensure_venv() -> `pip install -r requirements.txt`.
    # A command someone types to find out what a script does must not install
    # packages, and an unrecognised flag must not silently mean "yes, run the
    # whole bootstrap".
    argv = sys.argv[1:]
    if {"-h", "--help"} & set(argv):
        print(USAGE)
        return
    astrbot_dir: Path | None = None
    if "--astrbot" in argv:
        i = argv.index("--astrbot")
        if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
            print(USAGE)
            sys.exit("--astrbot needs the AstrBot data directory")
        astrbot_dir = Path(argv[i + 1]).expanduser()
        del argv[i:i + 2]
    qq_flag = "--qq" in argv

    def take(flag: str) -> str:
        if flag not in argv:
            return ""
        i = argv.index(flag)
        if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
            print(USAGE)
            sys.exit(f"{flag} needs a value")
        value = argv[i + 1]
        del argv[i:i + 2]
        return value

    platform_kind = take("--platform").lower()
    platform_creds = {"token": take("--token"), "app_token": take("--app-token"),
                      "app_id": take("--app-id"), "app_secret": take("--app-secret")}
    unknown = [arg for arg in argv if arg not in ("--no-input", "--qq")]
    if unknown:
        print(USAGE)
        sys.exit(f"unrecognised argument(s): {' '.join(unknown)}")
    if (qq_flag or platform_kind) and astrbot_dir is None:
        print(USAGE)
        sys.exit("--qq and --platform only make sense with --astrbot")

    no_input = "--no-input" in argv or astrbot_dir is not None
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
    if astrbot_dir is not None:
        if not (astrbot_dir / "plugins").is_dir():
            sys.exit(f"no plugins/ folder under {astrbot_dir}; is that AstrBot's data directory?")
        values: dict = {}
        cfg_path = connect_astrbot(env_path, values, data_dir=astrbot_dir,
                                   qq=qq_flag, groups=[], private=[])
        write_env(env_path, values)
        _info(f"AstrBot plugin installed and configured: {cfg_path}")
        _info("allowlists are empty: add group_whitelist / private_whitelist there "
              "or in AstrBot's WebUI, then restart AstrBot")
        if platform_kind:
            token = platform_creds["token"]
            creds = {"telegram": {"telegram_token": token}, "discord": {"discord_token": token},
                     "slack": {"bot_token": token, "app_token": platform_creds["app_token"]},
                     "kook": {"kook_bot_token": token},
                     "lark": {"app_id": platform_creds["app_id"],
                              "app_secret": platform_creds["app_secret"]}}.get(platform_kind, {})
            try:
                path = write_astrbot_platform(
                    astrbot_dir, astrbot_platform_entry(platform_kind, creds))
            except (ValueError, OSError) as exc:
                sys.exit(f"platform not written: {exc}")
            _info(f"{platform_kind} adapter written to {path}; restart AstrBot to bring it up")
    print()
    _info("done. next steps:")
    activate = (
        ".venv\\Scripts\\activate"
        if os.name == "nt"
        else "source .venv/bin/activate"
    )
    print("  1. edit .env (at minimum: LLM_API_KEY, BOT_NAME)")
    print("  2. edit persona.txt (your bot's personality)")
    print(f"  3. activate venv: {activate}")
    print("  4. try it now, no account needed:  python try_chat.py")
    print("  5. for live chats, run:            python main.py")
    print()
    if astrbot_dir is None:
        _info("to go live, connect an AstrBot install: "
              "python quickstart.py --astrbot <AstrBot data dir> [--qq]")


if __name__ == "__main__":
    main()
