"""The AstrBot handshake (plugin copy, config merge, shared token) and
quickstart's flags."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import quickstart
from persona_agent import setup_wizard as sw


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
        sw.write_env(env, {"LLM_API_KEY": "sk-new"})
        check("write_env: the leftover temp file is gone", not leftover.exists())
        text = env.read_text(encoding="utf-8")
        check("write_env: the new value is written", "LLM_API_KEY=sk-new" in text, text)
        check("write_env: nothing from the leftover survives", "STALE" not in text, text)
        if os.name != "nt":   # Windows ACLs do not map onto POSIX mode bits
            mode = env.stat().st_mode & 0o777
            check("write_env: the result is 0600", mode == 0o600, oct(mode))


def test_plugin_config_is_merged_not_replaced() -> None:
    cfg = sw.astrbot_plugin_config(
        {"timeout_s": 300, "block_default": False, "custom": 1},
        personagent_url="http://127.0.0.1:8080", token="t",
        qq=True, groups=["123", " 456 ", ""], dm_users=[])
    check("config: managed keys written", cfg["connector_token"] == "t"
          and cfg["groups"] == ["123", "456"] and cfg["dm_users"] == [], repr(cfg))
    check("config: qq clears the aiocqhttp exclusion", cfg["excluded_platforms"] == [])
    check("config: unmanaged keys survive", cfg["timeout_s"] == 300
          and cfg["block_default"] is False and cfg["custom"] == 1, repr(cfg))
    cfg2 = sw.astrbot_plugin_config(None, personagent_url="u", token="t", qq=False,
                                            groups=["*"], dm_users=["telegram:9"])
    check("config: no qq keeps aiocqhttp excluded", cfg2["excluded_platforms"] == ["aiocqhttp"])
    check("config: DM senders and a wildcard written as given",
          cfg2["dm_users"] == ["telegram:9"] and cfg2["groups"] == ["*"], repr(cfg2))
    check("config: defaults filled", cfg2["timeout_s"] == 180 and cfg2["block_default"] is True)


def test_connect_writes_both_sides() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        data = tmp / "astrbot" / "data"
        (data / "plugins").mkdir(parents=True)
        (data / "config").mkdir()
        # AstrBot's own writer leaves a BOM; the merge must read through it.
        sw.astrbot_config_path(data).write_text(
            "\ufeff" + json.dumps({"timeout_s": 240}), encoding="utf-8")
        env = tmp / ".env"
        env.write_text("SERVER_PORT=9090\nCONNECTOR_TOKEN=\n", encoding="utf-8")
        values: dict = {}
        cfg_path = sw.connect_astrbot(env, values, data_dir=data, qq=True,
                                              groups=["1"], dm_users=[])
        sw.write_env(env, values)
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        check("connect: plugin copied", (data / "plugins" / sw.PLUGIN_NAME / "main.py").is_file())
        check("connect: no __pycache__ copied",
              not (data / "plugins" / sw.PLUGIN_NAME / "__pycache__").exists())
        check("connect: token generated and shared",
              len(values["CONNECTOR_TOKEN"]) >= 32 and cfg["connector_token"] == values["CONNECTOR_TOKEN"])
        check("connect: personagent_url follows SERVER_PORT",
              cfg["personagent_url"] == "http://127.0.0.1:9090")
        check("connect: existing config merged through the BOM", cfg["timeout_s"] == 240)
        check("connect: qq routed natively", values["CONNECTOR_QQ_PLATFORMS"] == "aiocqhttp")
        text = env.read_text(encoding="utf-8")
        check("connect: .env carries the token", f"CONNECTOR_TOKEN={values['CONNECTOR_TOKEN']}" in text)
        # Second run reuses the token instead of rotating it under AstrBot.
        values2: dict = {}
        sw.connect_astrbot(env, values2, data_dir=data, qq=False, groups=[], dm_users=[])
        check("connect: rerun keeps the token", values2["CONNECTOR_TOKEN"] == values["CONNECTOR_TOKEN"])
        check("connect: rerun can exclude qq again", values2["CONNECTOR_QQ_PLATFORMS"] == "")


def test_connect_removes_the_plugin_under_its_retired_name(tmp_path) -> None:
    """Both copies would forward every message, so the agent would answer
    each one twice."""
    data = tmp_path / "data"
    retired = data / "plugins" / sw.RETIRED_PLUGIN_NAME
    (retired / "__pycache__").mkdir(parents=True)
    (retired / "main.py").write_text("# old\n", encoding="utf-8")
    env = tmp_path / ".env"
    env.write_text("CONNECTOR_TOKEN=\n", encoding="utf-8")
    out = io.StringIO()
    with redirect_stdout(out):
        sw.connect_astrbot(env, {}, data_dir=data, qq=None, groups=None,
                                   dm_users=None)
    check("retired: the old directory is gone", not retired.exists())
    check("retired: the new one is installed",
          (data / "plugins" / sw.PLUGIN_NAME / "main.py").is_file())
    lines = [line for line in out.getvalue().splitlines()
             if sw.RETIRED_PLUGIN_NAME in line]
    check("retired: one line says so", len(lines) == 1, out.getvalue())

    out = io.StringIO()
    with redirect_stdout(out):
        sw.connect_astrbot(env, {}, data_dir=data, qq=None, groups=None,
                                   dm_users=None)
    check("retired: nothing to say on a rerun",
          sw.RETIRED_PLUGIN_NAME not in out.getvalue(), out.getvalue())


def test_an_upgrade_keeps_qq_routing_from_the_retired_config(tmp_path) -> None:
    """Without --qq or --no-qq QQ routing stays as it was, including across
    the plugin's rename; the keys that were renamed are not carried over."""
    data = tmp_path / "data"
    (data / "plugins").mkdir(parents=True)
    retired = sw.retired_astrbot_config_path(data)
    retired.parent.mkdir(parents=True)
    retired.write_text("﻿" + json.dumps({
        "excluded_platforms": [], "group_whitelist": ["123"], "timeout_s": 300,
        "agent_url": "http://127.0.0.1:8080/webhook/gateway"}), encoding="utf-8")
    env = tmp_path / ".env"
    env.write_text("CONNECTOR_TOKEN=tok\n", encoding="utf-8")
    values: dict = {}
    with redirect_stdout(io.StringIO()):
        sw.connect_astrbot(env, values, data_dir=data, qq=None, groups=None,
                                   dm_users=None)
    cfg = sw.read_astrbot_config(data)
    check("upgrade: QQ stays routed", sw.astrbot_qq_routed(cfg), repr(cfg))
    check("upgrade: CONNECTOR_QQ_PLATFORMS follows",
          values.get("CONNECTOR_QQ_PLATFORMS") == "aiocqhttp", repr(values))
    check("upgrade: a key that kept its name comes across", cfg["timeout_s"] == 300)
    check("upgrade: renamed keys do not",
          cfg["groups"] == [] and "group_whitelist" not in cfg
          and cfg["personagent_url"] == "http://127.0.0.1:8080", repr(cfg))
    check("upgrade: the retired config is removed", not retired.exists())


def test_a_key_written_twice_is_read_and_written_as_dotenv_reads_it(tmp_path) -> None:
    """dotenv takes the last line for a key. The wizard read the first and
    rewrote only the first, so the plugin and the server could end up with
    different tokens."""
    env = tmp_path / ".env"
    env.write_text("CONNECTOR_TOKEN=first\nOTHER=x\nCONNECTOR_TOKEN=last\n", encoding="utf-8")
    check("dotenv: the last line is the value", sw.env_get(env, "CONNECTOR_TOKEN") == "last")
    sw.write_env(env, {"CONNECTOR_TOKEN": "new"})
    text = env.read_text(encoding="utf-8")
    check("dotenv: every line for the key is rewritten",
          text.count("CONNECTOR_TOKEN=new") == 2 and "first" not in text
          and "last" not in text, text)


def test_a_rerun_keeps_what_the_operator_set() -> None:
    """`--astrbot` passes no allowlists and no QQ choice. A re-run used to empty
    the allowlists, reset a proxied personagent_url and drop every other
    excluded platform."""
    existing = {"personagent_url": "https://agent.example.com",
                "groups": ["123"], "dm_users": ["telegram:9"],
                "excluded_platforms": ["aiocqhttp", "wecom"], "timeout_s": 300}
    local = "http://127.0.0.1:9090"
    cfg = sw.astrbot_plugin_config(dict(existing), personagent_url=local, token="t",
                                           qq=None, groups=None, dm_users=None)
    check("rerun: groups kept", cfg["groups"] == ["123"], repr(cfg))
    check("rerun: DM senders kept", cfg["dm_users"] == ["telegram:9"], repr(cfg))
    check("rerun: a proxied personagent_url is kept",
          cfg["personagent_url"] == existing["personagent_url"], cfg["personagent_url"])
    check("rerun: exclusions untouched without a QQ choice",
          cfg["excluded_platforms"] == ["aiocqhttp", "wecom"], repr(cfg))
    check("rerun: token still written", cfg["connector_token"] == "t")

    on = sw.astrbot_plugin_config(dict(existing), personagent_url=local, token="t",
                                          qq=True, groups=None, dm_users=None)
    check("rerun: qq removes only aiocqhttp", on["excluded_platforms"] == ["wecom"], repr(on))
    off = sw.astrbot_plugin_config({"excluded_platforms": ["wecom"]},
                                           personagent_url=local, token="t", qq=False,
                                           groups=None, dm_users=None)
    check("rerun: no-qq adds aiocqhttp and keeps the rest",
          off["excluded_platforms"] == ["wecom", "aiocqhttp"], repr(off))

    tunnel = "http://127.0.0.1:9000"     # e.g. ssh -L 9000:agent:8080
    kept = sw.astrbot_plugin_config({"personagent_url": tunnel}, personagent_url=local,
                                            token="t", qq=None, groups=None, dm_users=None)
    check("rerun: a tunnel on another loopback port is kept",
          kept["personagent_url"] == tunnel, kept["personagent_url"])
    for refused in ("http://agent:8080", "http://0.0.0.0:8080",
                    "localhost:8080", "http://[::1", ""):
        fixed = sw.astrbot_plugin_config({"personagent_url": refused},
                                                 personagent_url=local, token="t", qq=None,
                                                 groups=None, dm_users=None)
        check(f"rerun: {refused!r}, which the plugin refuses, is replaced",
              fixed["personagent_url"] == local, fixed["personagent_url"])

    numeric = sw.astrbot_plugin_config(
        {"dm_users": [789]}, personagent_url=local, token="t", qq=None, groups=None,
        dm_users=["789", " 790"])
    check("rerun: a DM list given is written as trimmed strings",
          numeric["dm_users"] == ["789", "790"], repr(numeric))
    odd = sw.astrbot_plugin_config({"excluded_platforms": "aiocqhttp,wecom"},
                                           personagent_url=local, token="t", qq=None,
                                           groups=None, dm_users=None)
    check("rerun: a hand-written exclusion string is left alone without a QQ choice",
          odd["excluded_platforms"] == "aiocqhttp,wecom", repr(odd))
    odd_off = sw.astrbot_plugin_config({"excluded_platforms": "wecom"},
                                               personagent_url=local, token="t", qq=False,
                                               groups=None, dm_users=None)
    check("rerun: an exclusion string becomes a list when QQ is chosen",
          odd_off["excluded_platforms"] == ["wecom", "aiocqhttp"], repr(odd_off))
    check("routed: read the way the plugin reads it",
          sw.astrbot_qq_routed({"excluded_platforms": "aiocqhttp"})
          and sw.astrbot_qq_routed({"excluded_platforms": ["aiocqhttp "]})
          and not sw.astrbot_qq_routed({"excluded_platforms": ["aiocqhttp"]}))
    grown = sw.astrbot_plugin_config(dict(existing), personagent_url=local, token="t",
                                             qq=None, groups=["123"],
                                             dm_users=["telegram:9", "telegram:7"])
    check("rerun: a changed DM list is written",
          grown["dm_users"] == ["telegram:9", "telegram:7"], repr(grown))

    fresh = sw.astrbot_plugin_config(None, personagent_url=local, token="t",
                                             qq=None, groups=None, dm_users=None)
    check("fresh: aiocqhttp excluded by default", fresh["excluded_platforms"] == ["aiocqhttp"])
    check("fresh: empty allowlists forward nothing",
          fresh["groups"] == [] and fresh["dm_users"] == [], repr(fresh))


def test_connect_without_a_qq_choice_keeps_qq_routing(tmp_path) -> None:
    data = tmp_path / "data"
    (data / "plugins").mkdir(parents=True)
    sw.write_astrbot_config(data, {
        "connector_token": "plugin-token", "excluded_platforms": [],
        "groups": ["123"], "dm_users": []})
    env = tmp_path / ".env"
    env.write_text("CONNECTOR_TOKEN=\nCONNECTOR_QQ_PLATFORMS=aiocqhttp,wecom\n", encoding="utf-8")

    values: dict = {}
    path = sw.connect_astrbot(env, values, data_dir=data, qq=None, groups=None, dm_users=None)
    cfg = json.loads(path.read_text(encoding="utf-8"))
    check("connect: no QQ choice leaves CONNECTOR_QQ_PLATFORMS alone",
          "CONNECTOR_QQ_PLATFORMS" not in values, repr(values))
    check("connect: QQ stays routed", cfg["excluded_platforms"] == [], repr(cfg))
    check("connect: allowlists kept", cfg["groups"] == ["123"], repr(cfg))
    check("connect: the plugin's token is reused when .env has none",
          values["CONNECTOR_TOKEN"] == "plugin-token" == cfg["connector_token"], repr(values))

    # The plugin forwards QQ but .env lost aiocqhttp (a wizard interrupted
    # between the two writes): a plain rerun puts .env back in step.
    env.write_text("CONNECTOR_TOKEN=plugin-token\nCONNECTOR_QQ_PLATFORMS=wecom\n", encoding="utf-8")
    values_sync: dict = {}
    sw.connect_astrbot(env, values_sync, data_dir=data, qq=None, groups=None, dm_users=None)
    check("connect: .env follows the plugin's QQ routing",
          values_sync.get("CONNECTOR_QQ_PLATFORMS") == "aiocqhttp,wecom", repr(values_sync))
    sw.write_env(env, values_sync)

    # A token that would not survive .env is not reused.
    cfg = sw.read_astrbot_config(data)
    cfg["connector_token"] = "abc #def"
    sw.write_astrbot_config(data, cfg)
    env.write_text("CONNECTOR_TOKEN=\nCONNECTOR_QQ_PLATFORMS=aiocqhttp,wecom\n", encoding="utf-8")
    values_tok: dict = {}
    sw.connect_astrbot(env, values_tok, data_dir=data, qq=None, groups=None, dm_users=None)
    check("connect: an unsafe plugin token is replaced",
          values_tok["CONNECTOR_TOKEN"] != "abc #def" and len(values_tok["CONNECTOR_TOKEN"]) >= 32)
    sw.write_env(env, values_tok)

    values_off: dict = {}
    sw.connect_astrbot(env, values_off, data_dir=data, qq=False, groups=None, dm_users=None)
    check("connect: no-qq drops only aiocqhttp from the native list",
          values_off["CONNECTOR_QQ_PLATFORMS"] == "wecom", repr(values_off))


def test_env_values_are_read_the_way_dotenv_reads_them(tmp_path) -> None:
    env = tmp_path / ".env"
    env.write_text('A="wecom"\nB=\'aiocqhttp,wecom\'\nC=aiocqhttp  # routed\nD=x#y\n',
                   encoding="utf-8")
    get = lambda key: sw.env_get(env, key)  # noqa: E731
    check("env: double quotes dropped", get("A") == "wecom", get("A"))
    check("env: single quotes dropped", get("B") == "aiocqhttp,wecom", get("B"))
    check("env: an inline comment dropped", get("C") == "aiocqhttp", get("C"))
    check("env: a # inside a value kept", get("D") == "x#y", get("D"))


def _astrbot_data(root: Path) -> Path:
    """An AstrBot data folder as AstrBot leaves it after its first start."""
    data = root / "data"
    (data / "plugins").mkdir(parents=True)
    (data / "cmd_config.json").write_text('{"platform": []}', encoding="utf-8")
    return data


def _flag_run(monkeypatch, tmp_path, argv: list[str]) -> int:
    """Run main() down the `--astrbot` path without a venv or pip."""
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setattr(quickstart, "ensure_venv", lambda: tmp_path / ".venv")
    monkeypatch.setattr(quickstart, "ensure_deps", lambda _venv: None)
    with redirect_stdout(io.StringIO()):
        return quickstart.main(argv)


def test_the_astrbot_flag_can_be_rerun(monkeypatch, tmp_path) -> None:
    """Re-running the flag path keeps the allowlists set in AstrBot's WebUI
    and the QQ routing."""
    data = _astrbot_data(tmp_path / "astrbot")
    (tmp_path / ".env").write_text("LLM_API_KEY=sk-x\n", encoding="utf-8")

    _flag_run(monkeypatch, tmp_path, ["--astrbot", str(data), "--qq"])
    cfg = sw.read_astrbot_config(data)
    cfg.update(groups=["123"], dm_users=["456"])
    sw.write_astrbot_config(data, cfg)

    _flag_run(monkeypatch, tmp_path, ["--astrbot", str(data.parent)])
    cfg = sw.read_astrbot_config(data)
    check("flag rerun: AstrBot's root folder is accepted too", cfg.get("connector_token"))
    check("flag rerun: allowlists kept", cfg["groups"] == ["123"]
          and cfg["dm_users"] == ["456"], repr(cfg))
    check("flag rerun: QQ still routed", cfg["excluded_platforms"] == [], repr(cfg))
    check("flag rerun: native ids kept",
          sw.env_get(tmp_path / ".env", "CONNECTOR_QQ_PLATFORMS") == "aiocqhttp")

    _flag_run(monkeypatch, tmp_path, ["--astrbot", str(data), "--no-qq"])
    cfg = sw.read_astrbot_config(data)
    check("flag: --no-qq excludes aiocqhttp", cfg["excluded_platforms"] == ["aiocqhttp"], repr(cfg))
    check("flag: --no-qq clears native ids",
          sw.env_get(tmp_path / ".env", "CONNECTOR_QQ_PLATFORMS") == "")

    _flag_run(monkeypatch, tmp_path, ["--astrbot", str(data), "--platform", "telegram",
                                      "--token", "123:abc"])
    platforms = json.loads((data / "cmd_config.json").read_text(encoding="utf-8"))["platform"]
    check("flag: --platform writes the adapter",
          [p["telegram_token"] for p in platforms] == ["123:abc"], repr(platforms))

    for bad in (["--astrbot", str(data), "--qq", "--no-qq"], ["--qq"],
                ["--astrbot", str(tmp_path / "nowhere")], ["--bogus"]):
        try:
            _flag_run(monkeypatch, tmp_path, bad)
            raised = False
        except SystemExit:
            raised = True
        check(f"flag: {bad[-1]} is refused", raised)


def test_flags_are_checked_before_anything_is_installed(monkeypatch) -> None:
    """--help and a bad flag must not create .venv or run pip."""
    installed: list = []
    monkeypatch.setattr(quickstart, "ensure_venv", lambda: installed.append("venv"))
    monkeypatch.setattr(quickstart, "ensure_deps", lambda _venv: installed.append("pip"))
    for argv in (["--help"], ["--provider", "nope"], ["--platform", "telegram"]):
        try:
            with redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                quickstart.main(argv)
        except SystemExit:
            pass
        check(f"quickstart {argv[0]}: nothing installed", not installed, repr(installed))


def test_quickstart_hands_the_wizard_its_venv(monkeypatch, tmp_path) -> None:
    """The questions run with the .venv's interpreter, so the chat it offers
    has the dependencies."""
    seen: dict = {}
    monkeypatch.setattr(quickstart, "ensure_venv", lambda: tmp_path / ".venv")
    monkeypatch.setattr(quickstart, "ensure_deps", lambda _venv: None)

    def fake_run(argv, prog, **kwargs):
        seen.update(kwargs, prog=prog)
        return 0

    monkeypatch.setattr(sw, "run", fake_run)
    quickstart.main(["--no-input", "--name", "Mika"])
    check("quickstart: the .venv python is passed on",
          seen["python"] == str(quickstart._venv_python(tmp_path / ".venv")), repr(seen))
    check("quickstart: a re-run is confirmed first", seen["confirm_rerun"] is True)
    check("quickstart: its parsed flags are passed on", seen["args"].name == "Mika")


def test_agent_home_divergence_warning(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AGENT_HOME", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    env = home / ".env"

    def said() -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            sw.warn_if_agent_home_diverges(env, home)
        return out.getvalue()

    check("agent_home: silent when unset", said() == "")
    # A line in .env redirects the agent once that file is loaded.
    elsewhere = tmp_path / "elsewhere"
    env.write_text(f"AGENT_HOME={elsewhere}\n", encoding="utf-8")
    check("agent_home: .env value is picked up",
          sw.configured_agent_home(env) == str(elsewhere))
    check("agent_home: warns on divergence from .env",
          str(elsewhere.resolve()) in said(), said())
    # The shell's AGENT_HOME wins over .env, and pointing here is no divergence.
    monkeypatch.setenv("AGENT_HOME", str(home))
    check("agent_home: os.environ takes precedence over .env",
          sw.configured_agent_home(env) == str(home))
    check("agent_home: silent when it resolves to this home", said() == "", said())
