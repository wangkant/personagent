"""The lorebook panel, the data-file status it shares with doctor, and the loaders."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from persona_agent import health, paths, views
from persona_agent import setup_wizard as sw
from persona_agent import welcome
from persona_agent.home import resource
from persona_agent.panels import lore

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
SCRIPT = Path(welcome.ASSETS) / "panels" / "lore.js"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    value = welcome.Workspace(tmp_path)
    sw.copy_env_template(tmp_path)
    sw.write_env(value.env, {"LLM_API_KEY": "sk-main-key-0123456789", "LLM_BASE_URL": "https://api.deepseek.com",
                             "LLM_MODEL": "deepseek-chat", "PERSONA_NAME": "Mira", "AGENT_LANG": "zh-TW"})
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


def get(client):
    response = client.get("/api/lore", headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


def post(client, payload, path="/api/lore"):
    return client.post(path, headers=HEADERS, json=payload)


def own_file(workspace) -> Path:
    return workspace.home / "data" / "lorebook.zh.json"


def test_routes_need_the_page_token(client):
    assert client.get("/api/lore").status_code == 403
    for path in ("/api/lore", "/api/lore/reset", "/api/lore/import"):
        assert client.post(path, json={}).status_code == 403


def test_an_empty_home_lists_the_built_in_set_for_the_characters_content_language(client, workspace):
    body = get(client)
    built_in = json.loads(resource("data", "lorebook.zh.json").read_text(encoding="utf-8"))["entries"]
    assert body["lang"] == "zh" and body["own"] is False and body["error"] == {}
    assert body["file"] == str(own_file(workspace))
    assert [e["keywords"] for e in body["entries"]] == [e["keywords"] for e in built_in]
    assert body["filters"]["own"] is False and body["filters"]["count"] > 0
    assert body["examples"]["own"] is False and body["examples"]["count"] == 5
    assert not own_file(workspace).exists()


def test_the_first_save_copies_the_built_in_set_and_the_agent_reads_the_file(client, workspace):
    body = get(client)
    entries = body["entries"] + [{"name": "", "keywords": " gym ,the cave，Gym", "content": " The cave. \r\n",
                                  "priority": ""}]
    saved = post(client, {"entries": entries, "stamp": body["stamp"]}).json()
    assert saved["changed"] and saved["own"] and saved["restarted"] is False
    assert workspace.restarts == [True]
    data = json.loads(own_file(workspace).read_text(encoding="utf-8"))
    # The built-in file's notes come along; the new entry is written as the guide shows it.
    assert "_comment" in data
    assert data["entries"][-1] == {"name": "gym", "keywords": ["gym", "the cave"],
                                   "content": "The cave.", "priority": 100}
    used = views.parse_lorebook(data)
    assert len(used) == len(entries) and any(e["keywords"] == ["gym", "the cave"] for e in used)
    again = get(client)
    assert again["own"] and again["path"] == str(own_file(workspace))
    assert len(again["entries"]) == len(entries)


def test_edit_delete_and_a_backup_of_the_previous_file(client, workspace):
    body = get(client)
    first = post(client, {"entries": body["entries"][:2], "stamp": body["stamp"]}).json()
    edited = [dict(first["entries"][0], content="Changed.")]
    second = post(client, {"entries": edited, "stamp": first["stamp"]}).json()
    assert [e["content"] for e in second["entries"]] == ["Changed."]
    backup = json.loads(own_file(workspace).with_name("lorebook.zh.json.bak").read_text(encoding="utf-8"))
    assert len(backup["entries"]) == 2


@pytest.mark.parametrize("entry, field", [
    ({"keywords": [], "content": "x"}, "keywords"),
    ({"keywords": ["  "], "content": "x"}, "keywords"),
    ({"keywords": ["a" * 101], "content": "x"}, "keywords"),
    ({"keywords": "a", "content": " "}, "content"),
    ({"keywords": "a", "content": "x" * 4001}, "content"),
    ({"keywords": "a", "content": "x", "name": "n" * 81}, "name"),
    ({"keywords": "a", "content": "x", "priority": "high"}, "priority"),
    ({"keywords": "a", "content": "x", "priority": 10_000}, "priority"),
    ({"keywords": "a", "content": "x", "priority": True}, "priority"),
])
def test_what_the_loader_cannot_use_is_refused_at_its_entry(client, workspace, entry, field):
    body = get(client)
    good = {"keywords": ["ok"], "content": "fine"}
    response = post(client, {"entries": [good, entry], "stamp": body["stamp"]})
    assert response.status_code == 400 and response.json()["error"] == f"lore_invalid:1:{field}"
    assert not own_file(workspace).exists() and workspace.restarts == []


def test_too_many_entries_an_old_page_and_a_file_changed_elsewhere(client, workspace):
    body = get(client)
    many = [{"keywords": [f"k{i}"], "content": "x"} for i in range(lore.MAX_ENTRIES + 1)]
    assert post(client, {"entries": many, "stamp": body["stamp"]}).json()["error"] == "lore_too_many"
    assert post(client, {"stamp": body["stamp"]}).json()["error"] == "lore_unknown"
    own_file(workspace).parent.mkdir(parents=True)
    own_file(workspace).write_text('{"entries": []}', encoding="utf-8")
    response = post(client, {"entries": [{"keywords": ["a"], "content": "b"}], "stamp": body["stamp"]})
    assert response.json()["error"] == "lore_changed"


def test_a_large_lorebook_is_saved_beyond_the_pages_usual_request_size(client, workspace):
    body = get(client)
    entries = [{"keywords": [f"key{i}"], "content": "y" * 3000} for i in range(20)]
    response = post(client, {"entries": entries, "stamp": body["stamp"]})
    assert response.status_code == 200 and len(response.json()["entries"]) == 20


def test_reset_keeps_a_bak_and_brings_back_the_built_in_set(client, workspace):
    body = get(client)
    saved = post(client, {"entries": [{"keywords": ["a"], "content": "b"}], "stamp": body["stamp"]}).json()
    reset = post(client, {"stamp": saved["stamp"]}, "/api/lore/reset").json()
    assert reset["changed"] and reset["own"] is False and len(reset["entries"]) == len(body["entries"])
    assert not own_file(workspace).exists()
    assert json.loads(own_file(workspace).with_name("lorebook.zh.json.bak").read_text(encoding="utf-8"))[
        "entries"][0]["keywords"] == ["a"]
    assert workspace.restarts == [True, True]
    # Nothing of the person's own to remove: nothing happens.
    assert post(client, {"stamp": reset["stamp"]}, "/api/lore/reset").json()["changed"] is False
    # A second book, saved twice and reset: the first one is still on disk under its dated name.
    again = post(client, {"entries": [{"keywords": ["c"], "content": "d"}], "stamp": reset["stamp"]}).json()
    again = post(client, {"entries": [{"keywords": ["e"], "content": "f"}], "stamp": again["stamp"]}).json()
    post(client, {"stamp": again["stamp"]}, "/api/lore/reset")
    kept = {json.loads(path.read_text(encoding="utf-8"))["entries"][0]["keywords"][0]
            for path in own_file(workspace).parent.glob("lorebook.zh.json.*.bak")}
    assert kept == {"a", "e"}


def test_a_broken_file_is_reported_and_can_be_replaced_or_reset(client, workspace):
    own_file(workspace).parent.mkdir(parents=True)
    own_file(workspace).write_text('{"entries": [\n  {"keywords": ["a"],}\n]}', encoding="utf-8")
    body = get(client)
    assert body["own"] and body["entries"] == []
    # Python 3.13 reports the trailing comma itself, earlier versions the brace after it.
    assert body["error"]["reason"] == "syntax" and body["error"]["line"] == 2
    assert body["error"]["column"] in (21, 22)
    saved = post(client, {"entries": [{"keywords": ["a"], "content": "b"}], "stamp": body["stamp"]}).json()
    assert saved["error"] == {} and len(saved["entries"]) == 1
    assert "keywords\": [\"a\"],}" in own_file(workspace).with_name("lorebook.zh.json.bak").read_text(
        encoding="utf-8")
    own_file(workspace).write_text('{"entries": [{"keywords": ["a"], "content": "b", "priority": "x"}]}',
                                   encoding="utf-8")
    assert get(client)["error"] == {"reason": "shape"}


def test_a_sillytavern_world_info_export_is_converted():
    export = {"entries": {
        "0": {"uid": 0, "key": ["Ayla", "the captain"], "comment": "Captain", "content": "Ayla runs the ship.",
              "order": 250, "disable": False},
        "1": {"uid": 1, "key": ["off"], "content": "Disabled.", "disable": True},
        "2": {"uid": 2, "key": [], "content": "Always on, no keyword.", "constant": True},
        "3": {"uid": 3, "key": ["empty"], "content": ""},
        "4": {"uid": 4, "key": "port, harbour", "content": "The port.", "order": 99999},
    }}
    entries, skipped = lore.convert(export)
    assert skipped == 3
    assert entries == [
        {"name": "Captain", "keywords": ["Ayla", "the captain"], "content": "Ayla runs the ship.", "priority": 250},
        {"name": "port", "keywords": ["port", "harbour"], "content": "The port.", "priority": 9999}]
    # The older list shape and a character card's embedded book.
    book = {"entries": [{"keys": ["moon"], "content": "Moon.", "enabled": True, "insertion_order": 5},
                        {"keys": ["sun"], "content": "Sun.", "enabled": False}]}
    assert lore.convert(book) == ([{"name": "moon", "keywords": ["moon"], "content": "Moon.", "priority": 5}], 1)
    assert lore.convert({"data": {"character_book": book}})[1] == 1


def test_a_personagent_file_is_taken_as_is_and_unknown_files_are_refused(client):
    own = {"entries": [{"name": "gym", "keywords": ["gym"], "content": "The cave.", "priority": 120},
                       {"keywords": ["gym"], "content": "The cave.", "priority": 120}]}
    body = post(client, {"data": own}, "/api/lore/import").json()
    assert body == {"entries": [{"name": "gym", "keywords": ["gym"], "content": "The cave.", "priority": 120}],
                    "skipped": 1}
    assert post(client, {"data": {"name": "card"}}, "/api/lore/import").json()["error"] == "lore_import_unknown"
    assert post(client, {"data": {"entries": [{"key": [], "content": ""}]}},
                "/api/lore/import").json()["error"] == "lore_import_empty"
    huge = {"data": {"entries": [{"keywords": ["a"], "content": "x" * 1000}] * 1100}}
    assert post(client, huge, "/api/lore/import").status_code == 413


def test_the_status_of_the_word_filters_and_examples(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "output_filter.en.json").write_text(json.dumps({"filters": [
        {"name": "a", "pattern": "x"}, {"name": "b", "pattern": "("}]}), encoding="utf-8")
    (data / "examples.en.jsonl").write_text('{"reply": "a"}\nnot json\n\n{"reply": "b"}\n', encoding="utf-8")
    filters = views.data_file_status(tmp_path, "en", "filters")
    assert (filters["own"], filters["count"], filters["skipped"]) == (True, 1, 1)
    examples = views.data_file_status(tmp_path, "en", "examples")
    assert (examples["own"], examples["count"], examples["skipped"]) == (True, 2, 1)
    lorebook = views.data_file_status(tmp_path, "en", "lorebook")
    assert lorebook["own"] is False and lorebook["path"] == str(resource("data", "lorebook.en.json"))
    (data / "output_filter.en.json").write_bytes(b"\xff\xfe{")
    assert views.data_file_status(tmp_path, "en", "filters")["error"] == {"reason": "encoding"}


def test_the_loader_reads_a_file_saved_with_a_byte_order_mark(tmp_path):
    path = tmp_path / "lorebook.en.json"
    path.write_text('{"entries": [{"keywords": ["A"], "content": "b"}]}', encoding="utf-8-sig")

    class Holder(views.DataViews):
        lorebook_file = path
        _lorebook_cache: list = []
        _lorebook_stamp: tuple = ()

    holder = Holder()
    holder._reload_lorebook_if_stale()
    assert holder._lorebook_cache[0]["keywords"] == ["a"]
    assert views.data_file_status(tmp_path, "en", "lorebook")["error"] == {}


def test_the_seed_resolver_takes_another_home():
    home = Path("/nowhere/home")
    assert paths.resolve_seed_lang_file("lorebook", "json", "en", home) == resource("data", "lorebook.en.json")
    assert paths.resolve_seed_lang_file("missing", "json", "en", home) == home / "data" / "missing.json"


def test_the_doctor_row_reports_own_files_and_never_fails_without_them(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    monkeypatch.setenv("AGENT_LANG", "en")
    assert health.check_data_files() == (
        None, "lorebook: built-in; word filters: built-in; example dialogues: built-in")
    data = tmp_path / "data"
    data.mkdir()
    (data / "lorebook.en.json").write_text(json.dumps({"entries": [
        {"keywords": ["a"], "content": "b"}, {"keywords": [], "content": "c"}]}), encoding="utf-8")
    ok, detail = health.check_data_files()
    assert ok is True and detail.startswith("lorebook: 1 entries from lorebook.en.json, 1 skipped;")
    (data / "output_filter.en.json").write_text("{", encoding="utf-8")
    ok, detail, advice = health.check_data_files()
    assert ok is False and "output_filter.en.json could not be read (JSON error at line 1, column 2)" in detail
    assert str(data / "output_filter.en.json") in advice


def test_the_doctor_row_is_not_critical_and_its_advice_reaches_the_table(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    monkeypatch.setenv("AGENT_LANG", "en")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "lorebook.en.json").write_text("[", encoding="utf-8")
    monkeypatch.setattr(health, "CHECKS", [("Custom data files", health.check_data_files, False)])
    [row] = health.run_checks()
    assert row["id"] == "data" and row["ok"] is False and row["critical"] is False
    assert "lorebook.en.json" in row["advice"] and health.all_critical_ok([row])


def tables():
    text = SCRIPT.read_text(encoding="utf-8")
    found = {}
    for lang in ("en", "zh"):
        block = re.search(rf"\n  {lang}: {{\n(.*?)\n  }},", text, re.S).group(1)
        found[lang] = dict(re.findall(r'^    (lore_\w+): "(.*)",$', block, re.M))
        assert len(found[lang]) == len(block.splitlines())
    return found


def test_both_languages_have_the_same_keys_and_placeholders():
    found = tables()
    assert found["en"].keys() == found["zh"].keys()
    for key, en in found["en"].items():
        assert set(re.findall(r"{\w+}", en)) == set(re.findall(r"{\w+}", found["zh"][key])), key


def test_the_panel_uses_the_pages_names_and_formal_wording():
    found = tables()
    assert found["en"]["lore_title"] == "Lorebook" and found["zh"]["lore_title"] == "背景设定"
    assert found["zh"]["lore_filters"] == "屏蔽词" and found["zh"]["lore_examples"] == "示例对话"
    for key, zh in found["zh"].items():
        assert not re.search(r"[吧呢啦哦]([。，！？]|$)|您", zh), (key, zh)


def test_every_error_the_panel_raises_has_words_on_the_page():
    found = tables()["en"]
    for code in lore.ERRORS:
        key = code.split(":")[0]
        assert key == "lore_invalid" or key in found, code
    for field in lore.FIELDS:
        assert f"lore_err_{field}" in found
