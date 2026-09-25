"""quickstart's AstrBot handshake: plugin copy, config merge, shared token."""
from __future__ import annotations

import io
import json
import os
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import quickstart


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English.

    The suites state a property per line rather than one per function, and
    they keep saying it that way; this turns each statement into the assert
    pytest reports on."""
    assert cond, name + (f" - {detail}" if detail else "")


def test_a_leftover_env_tmp_does_not_keep_its_mode() -> None:
    """os.open applies its mode only at creation, so a leftover .env.tmp from an
    interrupted run kept whatever mode it had when the keys were written."""
    with tempfile.TemporaryDirectory() as d:
        env = Path(d) / ".env"
        leftover = Path(d) / ".env.tmp"
        leftover.write_text("STALE=1\n", encoding="utf-8")
        os.chmod(leftover, 0o644)
        quickstart.write_env(env, {"LLM_API_KEY": "sk-new"})
        check("write_env: the leftover temp file is gone", not leftover.exists())
        text = env.read_text(encoding="utf-8")
        check("write_env: the new value is written", "LLM_API_KEY=sk-new" in text, text)
        check("write_env: nothing from the leftover survives", "STALE" not in text, text)
        if os.name != "nt":   # Windows ACLs do not map onto POSIX mode bits
            mode = env.stat().st_mode & 0o777
            check("write_env: the result is owner-only", mode == 0o600, oct(mode))


def test_plugin_config_is_merged_not_replaced() -> None:
    cfg = quickstart.astrbot_plugin_config(
        {"timeout_s": 300, "block_default": False, "custom": 1},
        agent_url="http://127.0.0.1:8080/webhook/gateway", token="t",
        qq=True, groups=["123", " 456 ", ""], private=[])
    check("config: managed keys written", cfg["gateway_token"] == "t"
          and cfg["group_whitelist"] == ["123", "456"], repr(cfg))
    check("config: qq clears the aiocqhttp exclusion", cfg["excluded_platforms"] == [])
    check("config: private stays off without senders", cfg["private_enabled"] is False)
    check("config: unmanaged keys survive", cfg["timeout_s"] == 300
          and cfg["block_default"] is False and cfg["custom"] == 1, repr(cfg))
    cfg2 = quickstart.astrbot_plugin_config(None, agent_url="u", token="t", qq=False,
                                            groups=[], private=["telegram:9"])
    check("config: no qq keeps aiocqhttp excluded", cfg2["excluded_platforms"] == ["aiocqhttp"])
    check("config: a private sender enables DMs", cfg2["private_enabled"] is True)
    check("config: defaults filled", cfg2["timeout_s"] == 180 and cfg2["block_default"] is True)


def test_connect_writes_both_sides() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        data = tmp / "astrbot" / "data"
        (data / "plugins").mkdir(parents=True)
        (data / "config").mkdir()
        # AstrBot's own writer leaves a BOM; the merge must read through it.
        quickstart.astrbot_config_path(data).write_text(
            "\ufeff" + json.dumps({"timeout_s": 240}), encoding="utf-8")
        env = tmp / ".env"
        env.write_text("PORT=9090\nGATEWAY_TOKEN=\n", encoding="utf-8")
        values: dict = {}
        cfg_path = quickstart.connect_astrbot(env, values, data_dir=data, qq=True,
                                              groups=["1"], private=[])
        quickstart.write_env(env, values)
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        check("connect: plugin copied", (data / "plugins" / quickstart.PLUGIN_NAME / "main.py").is_file())
        check("connect: no __pycache__ copied",
              not (data / "plugins" / quickstart.PLUGIN_NAME / "__pycache__").exists())
        check("connect: token generated and shared",
              len(values["GATEWAY_TOKEN"]) >= 32 and cfg["gateway_token"] == values["GATEWAY_TOKEN"])
        check("connect: agent_url follows PORT", cfg["agent_url"] == "http://127.0.0.1:9090/webhook/gateway")
        check("connect: existing config merged through the BOM", cfg["timeout_s"] == 240)
        check("connect: qq routed natively", values["GATEWAY_NATIVE_PLATFORMS"] == "aiocqhttp")
        text = env.read_text(encoding="utf-8")
        check("connect: .env carries the token", f"GATEWAY_TOKEN={values['GATEWAY_TOKEN']}" in text)
        # Second run reuses the token instead of rotating it under AstrBot.
        values2: dict = {}
        quickstart.connect_astrbot(env, values2, data_dir=data, qq=False, groups=[], private=[])
        check("connect: rerun keeps the token", values2["GATEWAY_TOKEN"] == values["GATEWAY_TOKEN"])
        check("connect: rerun can exclude qq again", values2["GATEWAY_NATIVE_PLATFORMS"] == "")


def test_a_rerun_keeps_what_the_operator_set() -> None:
    """`--astrbot` passes no allowlists and no QQ choice. A re-run used to empty
    the allowlists, turn DMs off, reset a proxied agent_url and drop every
    other excluded platform."""
    existing = {"agent_url": "https://agent.example.com/webhook/gateway",
                "group_whitelist": ["123"], "private_whitelist": ["telegram:9"],
                "private_enabled": False, "excluded_platforms": ["aiocqhttp", "wecom"],
                "timeout_s": 300}
    local = "http://127.0.0.1:9090/webhook/gateway"
    cfg = quickstart.astrbot_plugin_config(dict(existing), agent_url=local, token="t",
                                           qq=None, groups=None, private=None)
    check("rerun: groups kept", cfg["group_whitelist"] == ["123"], repr(cfg))
    check("rerun: DM senders kept", cfg["private_whitelist"] == ["telegram:9"], repr(cfg))
    check("rerun: DMs stay off when the operator turned them off",
          cfg["private_enabled"] is False, repr(cfg))
    check("rerun: a proxied agent_url is kept",
          cfg["agent_url"] == existing["agent_url"], cfg["agent_url"])
    check("rerun: exclusions untouched without a QQ choice",
          cfg["excluded_platforms"] == ["aiocqhttp", "wecom"], repr(cfg))
    check("rerun: token still written", cfg["gateway_token"] == "t")

    on = quickstart.astrbot_plugin_config(dict(existing), agent_url=local, token="t",
                                          qq=True, groups=None, private=None)
    check("rerun: qq removes only aiocqhttp", on["excluded_platforms"] == ["wecom"], repr(on))
    off = quickstart.astrbot_plugin_config({"excluded_platforms": ["wecom"]}, agent_url=local,
                                           token="t", qq=False, groups=None, private=None)
    check("rerun: no-qq adds aiocqhttp and keeps the rest",
          off["excluded_platforms"] == ["wecom", "aiocqhttp"], repr(off))

    tunnel = "http://127.0.0.1:9000/webhook/gateway"     # e.g. ssh -L 9000:agent:8080
    kept = quickstart.astrbot_plugin_config({"agent_url": tunnel}, agent_url=local,
                                            token="t", qq=None, groups=None, private=None)
    check("rerun: a tunnel on another loopback port is kept", kept["agent_url"] == tunnel,
          kept["agent_url"])
    for refused in ("http://agent:8080/webhook/gateway", "http://0.0.0.0:8080",
                    "localhost:8080/webhook/gateway", "http://[::1", ""):
        fixed = quickstart.astrbot_plugin_config({"agent_url": refused}, agent_url=local,
                                                 token="t", qq=None, groups=None, private=None)
        check(f"rerun: {refused!r}, which the plugin refuses, is replaced",
              fixed["agent_url"] == local, fixed["agent_url"])

    same = quickstart.astrbot_plugin_config(dict(existing), agent_url=local, token="t",
                                            qq=None, groups=["123"], private=["telegram:9"])
    check("rerun: the same DM list keeps the operator's switch", same["private_enabled"] is False)
    numeric = quickstart.astrbot_plugin_config(
        {"private_whitelist": [789, " 790"], "private_enabled": False}, agent_url=local,
        token="t", qq=None, groups=None, private=["789", "790"])
    check("rerun: ids stored as numbers still count as the same list",
          numeric["private_enabled"] is False, repr(numeric))
    unset = quickstart.astrbot_plugin_config({"private_whitelist": ["789"]}, agent_url=local,
                                             token="t", qq=None, groups=None, private=None)
    check("rerun: a missing private_enabled stays off, as the plugin reads it",
          unset["private_enabled"] is False, repr(unset))
    odd = quickstart.astrbot_plugin_config({"excluded_platforms": "aiocqhttp,wecom"},
                                           agent_url=local, token="t", qq=None,
                                           groups=None, private=None)
    check("rerun: a hand-written exclusion string is left alone without a QQ choice",
          odd["excluded_platforms"] == "aiocqhttp,wecom", repr(odd))
    odd_off = quickstart.astrbot_plugin_config({"excluded_platforms": "wecom"},
                                               agent_url=local, token="t", qq=False,
                                               groups=None, private=None)
    check("rerun: an exclusion string becomes a list when QQ is chosen",
          odd_off["excluded_platforms"] == ["wecom", "aiocqhttp"], repr(odd_off))
    check("routed: read the way the plugin reads it",
          quickstart.astrbot_qq_routed({"excluded_platforms": "aiocqhttp"})
          and quickstart.astrbot_qq_routed({"excluded_platforms": ["aiocqhttp "]})
          and not quickstart.astrbot_qq_routed({"excluded_platforms": ["aiocqhttp"]}))
    grown = quickstart.astrbot_plugin_config(dict(existing), agent_url=local, token="t",
                                             qq=None, groups=["123"], private=["telegram:9", "telegram:7"])
    check("rerun: a changed DM list turns DMs on", grown["private_enabled"] is True)

    fresh = quickstart.astrbot_plugin_config(None, agent_url=local, token="t",
                                             qq=None, groups=None, private=None)
    check("fresh: aiocqhttp excluded by default", fresh["excluded_platforms"] == ["aiocqhttp"])
    check("fresh: empty allowlists, DMs off", fresh["group_whitelist"] == []
          and fresh["private_whitelist"] == [] and fresh["private_enabled"] is False, repr(fresh))


def test_connect_without_a_qq_choice_keeps_qq_routing(tmp_path) -> None:
    data = tmp_path / "data"
    (data / "plugins").mkdir(parents=True)
    quickstart.write_astrbot_config(data, {
        "gateway_token": "plugin-token", "excluded_platforms": [],
        "group_whitelist": ["123"], "private_whitelist": [], "private_enabled": False})
    env = tmp_path / ".env"
    env.write_text("GATEWAY_TOKEN=\nGATEWAY_NATIVE_PLATFORMS=aiocqhttp,wecom\n", encoding="utf-8")

    values: dict = {}
    path = quickstart.connect_astrbot(env, values, data_dir=data, qq=None, groups=None, private=None)
    cfg = json.loads(path.read_text(encoding="utf-8"))
    check("connect: no QQ choice leaves GATEWAY_NATIVE_PLATFORMS alone",
          "GATEWAY_NATIVE_PLATFORMS" not in values, repr(values))
    check("connect: QQ stays routed", cfg["excluded_platforms"] == [], repr(cfg))
    check("connect: allowlists kept", cfg["group_whitelist"] == ["123"], repr(cfg))
    check("connect: the plugin's token is reused when .env has none",
          values["GATEWAY_TOKEN"] == "plugin-token" == cfg["gateway_token"], repr(values))

    # The plugin forwards QQ but .env lost aiocqhttp (a wizard interrupted
    # between the two writes): a plain rerun puts .env back in step.
    env.write_text("GATEWAY_TOKEN=plugin-token\nGATEWAY_NATIVE_PLATFORMS=wecom\n", encoding="utf-8")
    values_sync: dict = {}
    quickstart.connect_astrbot(env, values_sync, data_dir=data, qq=None, groups=None, private=None)
    check("connect: .env follows the plugin's QQ routing",
          values_sync.get("GATEWAY_NATIVE_PLATFORMS") == "aiocqhttp,wecom", repr(values_sync))
    quickstart.write_env(env, values_sync)

    # A token that would not survive .env is not reused.
    cfg = quickstart.read_astrbot_config(data)
    cfg["gateway_token"] = "abc #def"
    quickstart.write_astrbot_config(data, cfg)
    env.write_text("GATEWAY_TOKEN=\nGATEWAY_NATIVE_PLATFORMS=aiocqhttp,wecom\n", encoding="utf-8")
    values_tok: dict = {}
    quickstart.connect_astrbot(env, values_tok, data_dir=data, qq=None, groups=None, private=None)
    check("connect: an unsafe plugin token is replaced",
          values_tok["GATEWAY_TOKEN"] != "abc #def" and len(values_tok["GATEWAY_TOKEN"]) >= 32)
    quickstart.write_env(env, values_tok)

    values_off: dict = {}
    quickstart.connect_astrbot(env, values_off, data_dir=data, qq=False, groups=None, private=None)
    check("connect: no-qq drops only aiocqhttp from the native list",
          values_off["GATEWAY_NATIVE_PLATFORMS"] == "wecom", repr(values_off))


def test_env_values_are_read_the_way_dotenv_reads_them(tmp_path) -> None:
    env = tmp_path / ".env"
    env.write_text('A="wecom"\nB=\'aiocqhttp,wecom\'\nC=aiocqhttp  # routed\nD=x#y\n',
                   encoding="utf-8")
    get = lambda key: quickstart._env_get(env, key)  # noqa: E731
    check("env: double quotes dropped", get("A") == "wecom", get("A"))
    check("env: single quotes dropped", get("B") == "aiocqhttp,wecom", get("B"))
    check("env: an inline comment dropped", get("C") == "aiocqhttp", get("C"))
    check("env: a # inside a value kept", get("D") == "x#y", get("D"))


def _flag_run(monkeypatch, tmp_path, argv: list[str]) -> None:
    """Run main() down the `--astrbot` path without a venv or pip."""
    monkeypatch.setattr(quickstart, "ROOT", tmp_path)
    monkeypatch.setattr(quickstart, "ensure_venv", lambda: tmp_path / ".venv")
    monkeypatch.setattr(quickstart, "ensure_deps", lambda _venv: None)
    monkeypatch.setattr(quickstart, "copy_persona_template", lambda _lang: None)
    monkeypatch.setattr(quickstart.sys, "argv", ["quickstart.py", *argv])
    quickstart.main()


def test_the_astrbot_flag_can_be_rerun(monkeypatch, tmp_path) -> None:
    """`--help` promises re-running is safe; the flag path used to wipe the
    allowlists set in AstrBot's WebUI and switch QQ routing off."""
    data = tmp_path / "data"
    (data / "plugins").mkdir(parents=True)
    (tmp_path / ".env").write_text("LLM_API_KEY=sk-x\n", encoding="utf-8")

    _flag_run(monkeypatch, tmp_path, ["--astrbot", str(data), "--qq"])
    cfg = quickstart.read_astrbot_config(data)
    cfg.update(group_whitelist=["123"], private_whitelist=["456"], private_enabled=True)
    quickstart.write_astrbot_config(data, cfg)

    _flag_run(monkeypatch, tmp_path, ["--astrbot", str(data)])
    cfg = quickstart.read_astrbot_config(data)
    check("flag rerun: allowlists kept", cfg["group_whitelist"] == ["123"]
          and cfg["private_whitelist"] == ["456"] and cfg["private_enabled"] is True, repr(cfg))
    check("flag rerun: QQ still routed", cfg["excluded_platforms"] == [], repr(cfg))
    check("flag rerun: native ids kept",
          quickstart._env_get(tmp_path / ".env", "GATEWAY_NATIVE_PLATFORMS") == "aiocqhttp")

    _flag_run(monkeypatch, tmp_path, ["--astrbot", str(data), "--no-qq"])
    cfg = quickstart.read_astrbot_config(data)
    check("flag: --no-qq excludes aiocqhttp", cfg["excluded_platforms"] == ["aiocqhttp"], repr(cfg))
    check("flag: --no-qq clears native ids",
          quickstart._env_get(tmp_path / ".env", "GATEWAY_NATIVE_PLATFORMS") == "")

    raised = False
    try:
        _flag_run(monkeypatch, tmp_path, ["--astrbot", str(data), "--qq", "--no-qq"])
    except SystemExit:
        raised = True
    check("flag: --qq and --no-qq together are refused", raised)


def test_the_wizard_rerun_keeps_the_astrbot_setup(monkeypatch, tmp_path) -> None:
    """Enter on the allowlist prompts used to write empty lists."""
    data = tmp_path / "data"
    (data / "plugins").mkdir(parents=True)
    quickstart.write_astrbot_config(data, {
        "excluded_platforms": [], "group_whitelist": ["123", "456"],
        "private_whitelist": ["789"], "private_enabled": True})
    env = tmp_path / ".env"
    env.write_text("LLM_API_KEY=sk-test-abcd\nLLM_BASE_URL=https://api.openai.com/\n"
                   "LLM_MODEL=gpt-4o-mini\nBOT_NAME=Mika\nAGENT_LANG=en\nBOT_QQ=10001\n"
                   "GATEWAY_NATIVE_PLATFORMS=aiocqhttp\nOWNER_QQ=42\nOWNER_NAME=Kay\n"
                   "QQ_GROUPS=123\nALLOWED_GROUPS=telegram:-100,qq:999\n", encoding="utf-8")

    prompts: list[str] = []

    def scripted_input(prompt: str = "") -> str:
        prompts.append(prompt)
        assert len(prompts) < 80, "the wizard kept re-asking: " + prompts[-1]
        if "Connect to an AstrBot" in prompt:
            return "y"
        if "AstrBot data directory" in prompt:
            return str(data)
        if "Include QQ" in prompt:
            return ""                                   # Enter: keep the current answer
        if "[Y/n]" in prompt or "[y/N]" in prompt:
            return "n"
        return ""

    monkeypatch.setattr("builtins.input", scripted_input)
    monkeypatch.setattr(quickstart, "copy_persona_template", lambda _lang: None)
    monkeypatch.setattr(quickstart, "_probe_key", lambda *_a: True)
    monkeypatch.setattr(quickstart, "_warn_if_agent_home_diverges", lambda _p: None)
    monkeypatch.setattr(quickstart.subprocess, "call", lambda *_a, **_k: 0)

    quickstart.run_wizard(tmp_path / ".venv", env)

    cfg = quickstart.read_astrbot_config(data)
    check("wizard rerun: groups kept", cfg["group_whitelist"] == ["123", "456"], repr(cfg))
    check("wizard rerun: DMs kept", cfg["private_whitelist"] == ["789"]
          and cfg["private_enabled"] is True, repr(cfg))
    check("wizard rerun: QQ kept", cfg["excluded_platforms"] == [], repr(cfg))
    got = {k: quickstart._env_get(env, k) for k in (
        "ALLOWED_GROUPS", "QQ_GROUPS", "ADMIN_IDS", "ADMIN_NAME", "OWNER_QQ", "OWNER_NAME")}
    check("wizard rerun: QQ entries follow the kept groups, other platforms' stay",
          got["ALLOWED_GROUPS"] == "telegram:-100,123,456", repr(got))
    check("wizard rerun: the old owner moves to the admin names",
          got["ADMIN_IDS"] == "42" and got["ADMIN_NAME"] == "Kay", repr(got))
    check("wizard rerun: the old names are emptied, so nothing outlives a removal",
          got["QQ_GROUPS"] == got["OWNER_QQ"] == got["OWNER_NAME"] == "", repr(got))

    # With QQ off, Enter on the QQ question keeps it off.
    cfg["excluded_platforms"] = ["aiocqhttp"]
    quickstart.write_astrbot_config(data, cfg)
    quickstart.write_env(env, {"GATEWAY_NATIVE_PLATFORMS": ""})
    quickstart.run_wizard(tmp_path / ".venv", env)
    cfg = quickstart.read_astrbot_config(data)
    check("wizard rerun: QQ stays off", cfg["excluded_platforms"] == ["aiocqhttp"], repr(cfg))


def test_platform_entry_replaces_same_id_and_keeps_the_rest() -> None:
    with tempfile.TemporaryDirectory() as d:
        data = Path(d)
        cfg = {"platform": [{"id": "telegram", "type": "telegram", "enable": True,
                             "telegram_token": "old"},
                            {"id": "kook", "type": "kook", "enable": False}],
               "other": {"kept": 1}}
        (data / "cmd_config.json").write_text("\ufeff" + json.dumps(cfg), encoding="utf-8")
        entry = quickstart.astrbot_platform_entry("telegram", {"telegram_token": "new"})
        check("platform: entry carries AstrBot's own fields",
              entry["type"] == "telegram" and entry["telegram_token"] == "new"
              and "telegram_api_base_url" in entry, repr(entry))
        quickstart.write_astrbot_platform(data, entry)
        out = json.loads((data / "cmd_config.json").read_text(encoding="utf-8"))
        ids = [p["id"] for p in out["platform"]]
        check("platform: same id replaced, others kept", ids == ["kook", "telegram"], repr(ids))
        check("platform: token updated", out["platform"][1]["telegram_token"] == "new")
        check("platform: unrelated config kept", out["other"] == {"kept": 1})
        try:
            quickstart.astrbot_platform_entry("slack", {"bot_token": "x"})
            check("platform: missing credential rejected", False)
        except ValueError as exc:
            check("platform: missing credential rejected", "app_token" in str(exc), str(exc))
        try:
            quickstart.astrbot_platform_entry("irc", {})
            check("platform: unknown kind rejected", False)
        except ValueError:
            check("platform: unknown kind rejected", True)


def test_agent_home_divergence_warning() -> None:
    saved = os.environ.pop("AGENT_HOME", None)
    try:
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"

            # Nothing set anywhere: quiet, since quickstart's ROOT is where the
            # agent will look by default.
            out = io.StringIO()
            with redirect_stdout(out):
                quickstart._warn_if_agent_home_diverges(env)
            check("agent_home: silent when unset", out.getvalue() == "", repr(out.getvalue()))

            # A previous wizard run left AGENT_HOME in .env pointing elsewhere;
            # load_dotenv(override=False) in main.py/try_chat.py means this is
            # what the agent actually uses, so it must be flagged even though
            # nothing is exported in the shell right now.
            elsewhere = Path(d) / "elsewhere"
            env.write_text(f"AGENT_HOME={elsewhere}\n", encoding="utf-8")
            check("agent_home: .env value is picked up",
                  quickstart._configured_agent_home(env) == str(elsewhere))
            out = io.StringIO()
            with redirect_stdout(out):
                quickstart._warn_if_agent_home_diverges(env)
            check("agent_home: warns on divergence from .env",
                  "AGENT_HOME" in out.getvalue() and str(elsewhere.resolve()) in out.getvalue(),
                  repr(out.getvalue()))

            # os.environ wins over .env (matches load_dotenv(override=False)),
            # and pointing back at ROOT is not a divergence.
            os.environ["AGENT_HOME"] = str(quickstart.ROOT)
            check("agent_home: os.environ takes precedence over .env",
                  quickstart._configured_agent_home(env) == str(quickstart.ROOT))
            out = io.StringIO()
            with redirect_stdout(out):
                quickstart._warn_if_agent_home_diverges(env)
            check("agent_home: silent when it resolves to ROOT", out.getvalue() == "",
                  repr(out.getvalue()))
    finally:
        if saved is None:
            os.environ.pop("AGENT_HOME", None)
        else:
            os.environ["AGENT_HOME"] = saved


def test_rerunning_the_wizard_keeps_the_current_setup(monkeypatch, tmp_path, capsys) -> None:
    """Enter-through on a re-run used to fall back to the first-run presets:
    DeepSeek's URL and model with the OpenAI key, BOT_NAME=Nova, AGENT_LANG=en."""
    env = tmp_path / ".env"
    env.write_text(
        "LLM_API_KEY=sk-test-abcd\nLLM_BASE_URL=https://api.openai.com/\n"
        "LLM_MODEL=gpt-4o-mini\nBOT_NAME=Mika\nAGENT_LANG=zh\n", encoding="utf-8")
    prompts: list[str] = []

    def scripted_input(prompt: str = "") -> str:
        prompts.append(prompt)
        # A required prompt with no default re-asks forever on Enter.
        assert len(prompts) < 50, "the wizard kept re-asking: " + prompts[-1]
        return "n" if ("[Y/n]" in prompt or "[y/N]" in prompt) else ""

    monkeypatch.setattr("builtins.input", scripted_input)
    monkeypatch.setattr(quickstart, "copy_persona_template", lambda _lang: None)
    monkeypatch.setattr(quickstart, "_probe_key", lambda *_a: True)
    monkeypatch.setattr(quickstart, "_warn_if_agent_home_diverges", lambda _p: None)
    monkeypatch.setattr(quickstart.subprocess, "call", lambda *_a, **_k: 0)

    quickstart.run_wizard(tmp_path / ".venv", env)

    get = lambda key: quickstart._env_get(env, key)  # noqa: E731
    check("rerun: provider kept", get("LLM_BASE_URL").rstrip("/") == "https://api.openai.com",
          get("LLM_BASE_URL"))
    check("rerun: model kept", get("LLM_MODEL") == "gpt-4o-mini", get("LLM_MODEL"))
    check("rerun: key kept", get("LLM_API_KEY") == "sk-test-abcd", get("LLM_API_KEY"))
    check("rerun: name kept", get("BOT_NAME") == "Mika", get("BOT_NAME"))
    check("rerun: language kept", get("AGENT_LANG") == "zh", get("AGENT_LANG"))
    shown = "\n".join(prompts) + capsys.readouterr().out
    check("rerun: the key is never printed", "sk-test-abcd" not in shown, shown)
    check("rerun: the key is shown masked", "sk-…abcd" in shown, shown)
