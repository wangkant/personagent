"""The tuning panel: fine-grained settings saved the way the page saves the rest."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from persona_agent import setup_wizard as sw
from persona_agent import welcome
from persona_agent.panels import tuning

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
SECRET = "sk-backup-secret-0123456789"
SCRIPT = Path(welcome.ASSETS) / "panels" / "tuning.js"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    value = welcome.Workspace(tmp_path)
    sw.copy_env_template(tmp_path)
    sw.write_env(value.env, {"LLM_API_KEY": "sk-main-key-0123456789", "LLM_BASE_URL": "https://api.deepseek.com",
                             "LLM_MODEL": "deepseek-chat", "PERSONA_NAME": "Mira", "AGENT_LANG": "en"})
    probes = []
    monkeypatch.setattr(sw, "probe_key", lambda *a, **kw: probes.append(a) or sw.Probe("u", 200, ""))
    value.probes = probes
    restarts = []
    monkeypatch.setattr(value, "_restart_agent", lambda: restarts.append(True))
    value.restarts = restarts
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


def post(client, payload, path="/api/tuning"):
    return client.post(path, headers=HEADERS, json=payload)


def test_routes_need_the_page_token(client):
    assert client.get("/api/tuning").status_code == 403
    assert client.post("/api/tuning", json={}).status_code == 403
    assert client.post("/api/tuning/fresh", json={}).status_code == 403
    assert client.get("/api/tuning/people").status_code == 403


def test_view_lists_every_field_and_never_a_key(client, workspace):
    sw.write_env(workspace.env, {"LLM_FALLBACK_API_KEY": SECRET})
    response = client.get("/api/tuning", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert SECRET not in response.text and "sk-main-key" not in response.text
    assert body["secrets"]["LLM_FALLBACK_API_KEY"] == sw.mask_secret(SECRET)
    assert {f["key"] for f in body["fields"]} == set(tuning.BY_KEY)
    assert "LLM_FALLBACK_API_KEY" not in body["values"]
    assert body["values"]["CHAT_TRIGGER_COUNT"] == "30"
    assert body["card"] == {"emoji": False, "charsets": [], "maxChars": None, "min": 50, "max": 800,
                            "broken": ""}


def test_saving_writes_only_what_changed_and_restarts(client, workspace):
    before = workspace.env.read_text(encoding="utf-8")
    body = post(client, {"values": {"CHAT_TRIGGER_COUNT": "12", "ADMIN_NAME": "Kai",
                                    "PERSONA_TZ_OFFSET_HOURS": "-5", "REACT_ELICIT_ENABLED": False,
                                    # The same as what is there: not written.
                                    "PROACTIVE_PROB": "0.25", "AGENT_ENABLED": "true"}}).json()
    assert body["changed"] and workspace.restarts == [True]
    values = workspace.config()
    assert values["CHAT_TRIGGER_COUNT"] == "12" and values["ADMIN_NAME"] == "Kai"
    assert values["PERSONA_TZ_OFFSET_HOURS"] == "-5" and values["REACT_ELICIT_ENABLED"] == "false"
    after = workspace.env.read_text(encoding="utf-8")
    changed = [(a, b) for a, b in zip(before.splitlines(), after.splitlines()) if a != b]
    assert {b.split("=")[0] for _, b in changed} == {"CHAT_TRIGGER_COUNT", "ADMIN_NAME",
                                                     "PERSONA_TZ_OFFSET_HOURS", "REACT_ELICIT_ENABLED"}
    assert len(before.splitlines()) == len(after.splitlines())
    assert body["values"]["CHAT_TRIGGER_COUNT"] == "12"


def test_nothing_changed_writes_nothing(client, workspace):
    before = workspace.env.read_bytes()
    body = post(client, {"values": {"CHAT_TRIGGER_COUNT": "30"}}).json()
    assert body["changed"] is False and workspace.restarts == []
    assert workspace.env.read_bytes() == before


def test_the_update_check_needs_no_restart(client, workspace):
    body = post(client, {"values": {"UPDATE_CHECK_ENABLED": "false"}}).json()
    assert body["changed"] and not body["restarted"] and workspace.restarts == []
    assert workspace.config()["UPDATE_CHECK_ENABLED"] == "false"


def test_restarted_is_true_only_for_a_running_agent(client, workspace, monkeypatch):
    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    assert post(client, {"values": {"DASHBOARD_ENABLED": False}}).json()["restarted"] is True


@pytest.mark.parametrize("key, value", [
    ("CHAT_TRIGGER_COUNT", "0"), ("CHAT_TRIGGER_COUNT", "many"), ("PROACTIVE_PROB", "1.5"),
    ("PROACTIVE_PROB", "nan"), ("PROMOTE_MIN_EVENTS", "1"), ("PERSONA_TZ_OFFSET_HOURS", "15"),
    ("AGENT_ENABLED", "maybe"), ("PROMOTE_MIN_SPEAKERS", "3"), ("ADMIN_IDS", "telegram:"),
    ("ADMIN_IDS", "a b"), ("ADMIN_NAME", "${LLM_API_KEY}"), ("ADMIN_NAME", "x" * 65),
    ("LLM_FALLBACK_MODEL", "two words"), ("LLM_FALLBACK_BASE_URL", "ftp://x"),
    ("PERSONA_VERSION", "a\nb"),
])
def test_a_bad_value_is_refused_naming_its_field(client, workspace, key, value):
    before = workspace.env.read_bytes()
    response = post(client, {"values": {key: value}})
    assert response.status_code == 400
    assert response.json()["error"] == f"tuning_invalid:{key}"
    assert workspace.env.read_bytes() == before and workspace.restarts == []


def test_other_refusals(client, workspace):
    assert post(client, {"values": {"SERVER_HOST": "0.0.0.0"}}).json()["error"] == "tuning_unknown"
    assert post(client, {"values": {"LLM_API_KEY": "x"}}).json()["error"] == "tuning_unknown"
    assert post(client, {"values": {"LLM_FALLBACK_BASE_URL": "http://example.com"}}).json()["error"] == "tuning_https"
    assert post(client, {"card": {"maxChars": "10"}}).json()["error"] == "tuning_invalid:card"
    assert post(client, {"card": {"charsets": ["stars"]}}).json()["error"] == "tuning_invalid:card"
    assert "SERVER_HOST=127.0.0.1" in workspace.env.read_text(encoding="utf-8")


def test_refused_while_a_job_runs_and_before_a_model(client, workspace):
    class Running:
        def done(self):
            return False
    workspace._future = Running()
    assert post(client, {"values": {"CHAT_TRIGGER_COUNT": "5"}}).json()["error"] == "busy"
    assert post(client, {}, "/api/tuning/fresh").json()["error"] == "busy"
    workspace._future = None
    sw.write_env(workspace.env, {"LLM_API_KEY": ""})
    assert post(client, {"values": {"CHAT_TRIGGER_COUNT": "5"}}).json()["error"] == "tuning_not_configured"


def test_owner_ids_are_written_canonical(client, workspace):
    post(client, {"values": {"ADMIN_IDS": "qq:42， telegram:7,telegram:7", "ACCESS_GROUPS": "discord:9"}})
    assert workspace.config()["ADMIN_IDS"] == "42,telegram:7"
    assert workspace.config()["ACCESS_GROUPS"] == "discord:9"


def test_owner_name_rerenders_a_shipped_persona_but_not_a_custom_one(client, workspace):
    key = sw.PERSONA_KEYS[0]
    sw.write_persona(workspace.home, key, name="Mira", lang="en")
    body = post(client, {"values": {"ADMIN_NAME": "Kai", "ADMIN_RELATIONSHIP": "friend"}}).json()
    expected = sw.persona_text(key, name="Mira", lang="en", admin_name="Kai", admin_relationship="friend")
    assert body["personaUpdated"] is (sw._normal(expected) != sw._normal(
        sw.persona_text(key, name="Mira", lang="en")))
    assert sw._normal((workspace.home / "persona.txt").read_text(encoding="utf-8")) == sw._normal(expected)
    (workspace.home / "persona.txt").write_text("My own words", encoding="utf-8")
    assert post(client, {"values": {"ADMIN_NAME": "Lee"}}).json()["personaUpdated"] is False
    assert (workspace.home / "persona.txt").read_text(encoding="utf-8") == "My own words"


def test_backup_model_key_is_kept_with_its_address_and_never_returned(client, workspace, monkeypatch):
    other = "https://openrouter.ai/api/v1"
    response = post(client, {"values": {"LLM_FALLBACK_MODEL": "cheap", "LLM_FALLBACK_BASE_URL": other}})
    assert response.json()["error"] == "tuning_key_needed"
    response = post(client, {"values": {"LLM_FALLBACK_MODEL": "cheap", "LLM_FALLBACK_BASE_URL": other,
                                        "LLM_FALLBACK_API_KEY": SECRET}})
    assert response.status_code == 200 and SECRET not in response.text
    assert workspace.probes[-1] == (other, SECRET, "cheap")
    values = workspace.config()
    assert values["LLM_FALLBACK_API_KEY"] == SECRET and values["LLM_FALLBACK_BASE_URL"] == other
    # A blank key keeps the saved one; a new address drops it.
    post(client, {"values": {"LLM_FALLBACK_MODEL": "cheaper", "LLM_FALLBACK_API_KEY": ""}})
    assert workspace.config()["LLM_FALLBACK_API_KEY"] == SECRET
    assert post(client, {"values": {"LLM_FALLBACK_BASE_URL": "https://api.groq.com/openai/v1"}}).json()["error"] \
        == "tuning_key_needed"
    post(client, {"values": {"LLM_FALLBACK_BASE_URL": ""}})
    assert workspace.config()["LLM_FALLBACK_API_KEY"] == ""
    # On the main service, the main key is used to check it.
    post(client, {"values": {"LLM_FALLBACK_MODEL": "deepseek-other"}})
    assert workspace.probes[-1] == ("https://api.deepseek.com", "sk-main-key-0123456789", "deepseek-other")


@pytest.mark.parametrize("status, code", [(401, "tuning_fallback_rejected"), (429, "tuning_fallback_limited"),
                                          (500, "tuning_fallback_unreachable")])
def test_a_backup_model_that_does_not_answer_is_not_saved(client, workspace, monkeypatch, status, code):
    monkeypatch.setattr(sw, "probe_key", lambda *a, **kw: sw.Probe("u", status, "echo " + SECRET))
    response = post(client, {"values": {"LLM_FALLBACK_MODEL": "cheap"}})
    assert response.json()["error"] == code and SECRET not in response.text
    assert workspace.config()["LLM_FALLBACK_MODEL"] == ""


def test_backup_model_unreachable_when_the_probe_raises(client, workspace, monkeypatch):
    def boom(*a, **kw):
        raise OSError(SECRET)
    monkeypatch.setattr(sw, "probe_key", boom)
    response = post(client, {"values": {"LLM_FALLBACK_MODEL": "cheap"}})
    assert response.json()["error"] == "tuning_fallback_unreachable" and SECRET not in response.text


def test_reply_style_card_is_written_and_other_keys_kept(client, workspace):
    path = workspace.home / "persona.card.json"
    path.write_text(json.dumps({"note": "mine", "reply_style": {"emoji": False, "extra": 1}}), encoding="utf-8")
    body = post(client, {"card": {"emoji": True, "charsets": ["music", "ellipsis"], "maxChars": "320"}}).json()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved == {"note": "mine", "reply_style": {"extra": 1, "emoji": True,
                                                    "charsets": ["ellipsis", "music"], "max_chars": 320}}
    assert body["card"]["maxChars"] == 320 and workspace.restarts == [True]
    # Unchanged: not written again.
    post(client, {"card": {"emoji": True, "charsets": ["ellipsis", "music"], "maxChars": 320}})
    assert workspace.restarts == [True]
    post(client, {"card": {"emoji": False, "charsets": [], "maxChars": ""}})
    assert json.loads(path.read_text(encoding="utf-8"))["reply_style"] == {"extra": 1, "emoji": False,
                                                                           "charsets": []}


def test_a_broken_or_outside_card_is_refused(client, workspace):
    path = workspace.home / "persona.card.json"
    path.write_text("{nope", encoding="utf-8")
    assert client.get("/api/tuning", headers=HEADERS).json()["card"]["broken"] == "tuning_card_broken"
    assert post(client, {"card": {"emoji": True}}).json()["error"] == "tuning_card_broken"
    assert path.read_text(encoding="utf-8") == "{nope"
    sw.write_env(workspace.env, {"PERSONA_CARD_FILE": "../outside.json"})
    assert post(client, {"card": {"emoji": True}}).json()["error"] == "tuning_card_outside"
    assert not (workspace.home.parent / "outside.json").exists()


def test_start_fresh_sets_a_new_label_and_reports_the_old(client, workspace):
    sw.write_env(workspace.env, {"PERSONA_VERSION": "v1"})
    body = post(client, {}, "/api/tuning/fresh").json()
    assert body["previous"] == "v1" and body["values"]["PERSONA_VERSION"].startswith("fresh-")
    assert workspace.config()["PERSONA_VERSION"] == body["values"]["PERSONA_VERSION"]
    assert workspace.restarts == [True]


def test_people_come_from_activity_without_the_page_chat(client, workspace, monkeypatch):
    async def activity():
        return {"running": True, "off": False, "chats": [
            {"id": "private:telegram:5", "platform": "telegram", "kind": "dm", "last": 1},
            {"id": "private:777", "platform": "qq", "kind": "dm", "last": 2},
            {"id": "private:browser:abc", "platform": "browser", "kind": "dm", "last": 3},
            {"id": "discord:9", "platform": "discord", "kind": "group", "last": 4}]}
    monkeypatch.setattr(workspace, "activity", activity)
    body = client.get("/api/tuning/people", headers=HEADERS).json()
    assert [p["id"] for p in body["people"]] == ["telegram:5", "777"]
    assert [g["id"] for g in body["groups"]] == ["discord:9"] and body["running"] is True


def test_people_when_the_character_is_not_running(client):
    body = client.get("/api/tuning/people", headers=HEADERS).json()
    assert body == {"running": False, "off": False, "people": [], "groups": []}


def test_every_error_code_is_let_through(client):
    for code in ("tuning_key_needed", "tuning_invalid:ADMIN_IDS", "tuning_card_broken"):
        assert code in tuning.ERRORS


def tables():
    text = SCRIPT.read_text(encoding="utf-8")
    found = {}
    for lang in ("en", "zh"):
        block = re.search(rf"\n  {lang}: {{\n(.*?)\n  }},", text, re.S).group(1)
        found[lang] = dict(re.findall(r'^    (tuning_\w+): "(.*)",$', block, re.M))
        assert len(found[lang]) == len(block.splitlines())
    return found


def test_both_languages_use_the_same_placeholders():
    found = tables()
    for key, en in found["en"].items():
        assert set(re.findall(r"{\w+}", en)) == set(re.findall(r"{\w+}", found["zh"][key])), key


def test_wording_is_formal_and_uses_the_page_names():
    found = tables()
    for key, zh in found["zh"].items():
        assert not re.search(r"[吧呢啦哦]([。，！？]|$)|主人|您|不太对|从头来过|捣乱", zh), (key, zh)
    for key, en in found["en"].items():
        assert not re.search(r"\w+n't\b|\b(it's|that's|you're|i'm|they're|let's)\b|[Oo]wner", en), (key, en)
    # Not model fine-tuning.
    assert found["en"]["tuning_title"] == "Advanced settings" and found["zh"]["tuning_title"] == "高级设置"
    # A minimum gap, not a maximum.
    assert "至少" in found["zh"]["tuning_cooldowns"] and "最多" not in found["zh"]["tuning_cooldowns"]
    assert found["en"]["tuning_cooldowns"].startswith("At least")
    # Turning activity data off also stops forgetting a chat in both views.
    for lang in ("en", "zh"):
        hint = found[lang]["tuning_h_dashboard_enabled"]
        assert "{chat}" in hint and "{activity}" in hint
    assert "概率" in found["zh"]["tuning_f_proactive_prob"] and "概率" in found["zh"]["tuning_f_proactive_dm_prob"]
    assert found["zh"]["tuning_f_promote_evidence_max_age_days"].count("天") == 1
    assert "他" not in found["zh"]["tuning_h_proactive_dm_cooldown_s"]


def test_names_borrowed_from_the_page_exist():
    page = (Path(welcome.ASSETS) / "welcome.js").read_text(encoding="utf-8")
    for key in ("chat", "activity", "platforms", "proactiveTitle"):
        assert len(re.findall(rf"^    {key}: \"", page, re.M)) >= 2, key


def test_picker_rows_add_no_listeners_to_the_lists():
    text = SCRIPT.read_text(encoding="utf-8")
    body = re.search(r"\n  function pickRow\(.*?\n  }\n", text, re.S).group(0)
    # Rows are rebuilt on every click; a listener on a list input would outlive them.
    assert "inputs[" not in body and "inputs." not in body
    assert re.search(r'"tuning-pick-me-" \+ n', body) and re.search(r'"tuning-pick-allow-" \+ n', body)


def test_page_strings_match_in_both_languages():
    text = SCRIPT.read_text(encoding="utf-8")
    found = tables()
    assert found["en"].keys() == found["zh"].keys()
    used = set(re.findall(r'"(tuning_[a-z_]+)"', text.split("PA.strings", 1)[1].split("});", 1)[1]))
    for key in tuning.BY_KEY:
        assert f"tuning_f_{key.lower()}" in found["en"] and f"tuning_h_{key.lower()}" in found["en"]
    for code in tuning.ERRORS:
        if not code.startswith("tuning_invalid:"):
            assert code in found["en"]
    prefixed = {k for k in used if not k.endswith("_")}
    assert prefixed <= found["en"].keys() | {"tuning_invalid"}
