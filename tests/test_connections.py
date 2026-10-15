"""The platform catalog behind the local page's connect screen."""
from __future__ import annotations

import pytest

from persona_agent import connections as conn


def test_every_platform_is_listed_once_and_only_scan_platforms_may_ask_for_nothing():
    kinds = [p.kind for p in conn.PLATFORMS]
    assert len(kinds) == len(set(kinds))
    assert {p.kind for p in conn.PLATFORMS if p.group == conn.SCAN} == {"weixin_oc", "qq_official"}
    assert {p.kind for p in conn.PLATFORMS if conn.is_direct(p.kind)} == {
        "qq_official", "weixin_oc", "telegram", "discord"}
    for item in conn.PLATFORMS:
        assert item.group in (conn.SCAN, conn.KEY, conn.ADVANCED)
        # A scan platform's fields, if any, are for a bot made elsewhere.
        assert item.fields or item.group == conn.SCAN
        assert all(f.required for f in item.fields) or item.group == conn.ADVANCED
    # LINE always routes callbacks through AstrBot's dashboard, which does not run.
    assert "line" not in kinds


def test_the_catalog_never_carries_values():
    listed = conn.catalog()
    assert [p["id"] for p in listed] == [p.kind for p in conn.PLATFORMS]
    assert all(set(f) == {"key", "label", "secret", "required", "kind", "default"}
               for p in listed for f in p["fields"])


def test_values_are_checked_trimmed_and_limited_to_the_asked_fields():
    mattermost = conn.platform("mattermost")
    clean = conn.clean_values(mattermost, {"mattermost_url": " https://chat.example.com/ ",
                                           "mattermost_bot_token": "token", "extra": "dropped"})
    assert clean == {"mattermost_url": "https://chat.example.com", "mattermost_bot_token": "token"}
    for values in ({"mattermost_url": "https://chat.example.com"},
                   {"mattermost_url": "javascript:alert(1)", "mattermost_bot_token": "t"},
                   {"mattermost_url": "https://chat.example.com", "mattermost_bot_token": "a\nb"}):
        with pytest.raises(ValueError):
            conn.clean_values(mattermost, values)
    wecom = conn.platform("wecom")
    base = {"corpid": "c", "secret": "s", "token": "t", "encoding_aes_key": "k"}
    assert conn.clean_values(wecom, base)["port"] == 6195
    assert conn.clean_values(wecom, {**base, "port": "8443"})["port"] == 8443
    for port in ("0", "70000", "80a"):
        with pytest.raises(ValueError, match="invalid_field"):
            conn.clean_values(wecom, {**base, "port": port})
    with pytest.raises(ValueError, match="invalid_platform"):
        conn.platform("line")


def test_an_entry_is_astrbots_template_then_our_settings_then_the_values():
    template = {"id": "default", "type": "wecom", "enable": False, "hint": "shown in its UI",
                "unified_webhook_mode": True, "api_base_url": "https://qyapi.weixin.qq.com/cgi-bin/"}
    entry = conn.entry(template, conn.platform("wecom"), {"corpid": "c", "port": 6195})
    assert entry["id"] == entry["type"] == "wecom" and entry["enable"] is True
    assert entry["unified_webhook_mode"] is False
    assert entry["api_base_url"] == "https://qyapi.weixin.qq.com/cgi-bin/"
    assert entry["corpid"] == "c" and "hint" not in entry


def test_saving_replaces_one_entry_and_keeps_the_operators_others(tmp_path):
    (tmp_path / "cmd_config.json").write_text(
        '﻿{"platform": [{"id": "mine", "type": "telegram", "enable": true}]}', encoding="utf-8")
    conn.save_entry(tmp_path, {"id": "telegram", "type": "telegram", "enable": True, "telegram_token": "a"})
    conn.save_entry(tmp_path, {"id": "telegram", "type": "telegram", "enable": True, "telegram_token": "b"})
    # Only entries this page manages (id == type) count as connected here.
    assert conn.connected(tmp_path) == ["telegram"]
    conn.remove_entry(tmp_path, "telegram")
    assert conn.connected(tmp_path) == []
    assert conn._main_config(tmp_path)[1]["platform"] == [{"id": "mine", "type": "telegram", "enable": True}]


def test_scope_opens_and_closes_one_platform_only():
    cfg = {"groups": ["123", "discord:*"], "dm_users": []}
    conn.scope(cfg, "telegram", allow=True)
    conn.scope(cfg, "telegram", allow=True)
    assert cfg == {"groups": ["123", "discord:*", "telegram:*"], "dm_users": ["telegram:*"]}
    conn.scope(cfg, "telegram", allow=False)
    assert cfg == {"groups": ["123", "discord:*"], "dm_users": []}


def test_the_slack_guide_creates_an_app_with_socket_mode_and_what_the_adapter_reads():
    from urllib.parse import parse_qs, urlsplit
    import json

    link = urlsplit(conn.platform("slack").guide)
    query = parse_qs(link.query)
    assert (link.scheme, link.netloc, link.path) == ("https", "api.slack.com", "/apps")
    assert query["new_app"] == ["1"]
    manifest = json.loads(query["manifest_json"][0])
    assert manifest["settings"]["socket_mode_enabled"] is True
    assert {"app_mention", "message.im", "message.channels"} <= set(
        manifest["settings"]["event_subscriptions"]["bot_events"])
    assert {"chat:write", "app_mentions:read", "im:history"} <= set(manifest["oauth_config"]["scopes"]["bot"])
