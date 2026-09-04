"""quickstart's AstrBot handshake: plugin copy, config merge, shared token."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import quickstart  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + ("" if condition else f": {detail}"))
    if not condition:
        FAILURES.append(name)


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


def main() -> int:
    test_plugin_config_is_merged_not_replaced()
    test_connect_writes_both_sides()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED: {FAILURES}")
        return 1
    print("all quickstart checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
