"""Character cards: reading V1, V2 and V3 as JSON, PNG and CHARX, what a card
becomes in a home, hostile files, saving the character as a card, the page's
routes, the persona draft and the terminal command."""
from __future__ import annotations

import base64
import io
import json
import os
import struct
import zipfile
import zlib
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from persona_agent import charcard, cli, drafting, usage, welcome
from persona_agent import setup_wizard as sw
from persona_agent.llm import _PooledHTTP

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}


def v2(**data) -> dict:
    base = {"name": "Luna", "description": "{{char}} bakes bread at night and teases {{user}}.",
            "personality": "warm, sleepy", "scenario": "A bakery at 3 a.m.",
            "first_mes": "Oh, you are up too?", "alternate_greetings": ["Hello."],
            "mes_example": "<START>\n{{user}}: hi\n{{char}}: hey, flour everywhere\n"
                           "<START>\n<USER>: bread?\n<BOT>: always\nstill warm",
            "system_prompt": "", "post_history_instructions": "", "creator_notes": "Have fun.",
            "tags": [], "creator": "someone", "character_version": "1", "extensions": {}}
    base.update(data)
    return {"spec": "chara_card_v2", "spec_version": "2.0", "data": base}


def png(payloads: dict, size=(64, 48)) -> bytes:
    info = PngInfo()
    for key, obj in payloads.items():
        info.add_text(key, base64.b64encode(json.dumps(obj).encode()).decode())
    out = io.BytesIO()
    Image.new("RGB", size, "teal").save(out, "PNG", pnginfo=info)
    return out.getvalue()


def charx(card: dict, files: dict | None = None, *, method=zipfile.ZIP_DEFLATED) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", method) as archive:
        archive.writestr("card.json", json.dumps(card))
        for name, data in (files or {}).items():
            archive.writestr(name, data)
    return out.getvalue()


def picture_bytes(size=(40, 40)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, "orange").save(out, "PNG")
    return out.getvalue()


@pytest.fixture
def home(tmp_path):
    sw.copy_env_template(tmp_path)
    sw.write_env(tmp_path / ".env", {"AGENT_LANG": "en", "PERSONA_NAME": "Mira",
                                     "LLM_API_KEY": "sk-test-0123456789", "LLM_MODEL": "standin",
                                     "LLM_BASE_URL": "http://127.0.0.1:9/v1"})
    return tmp_path


def values(home: Path) -> dict:
    from dotenv import dotenv_values
    return {k: str(v or "") for k, v in dotenv_values(home / ".env").items()}


# ---- reading


def test_a_v1_card_is_its_top_level_fields():
    card = charcard.read(json.dumps({"name": "Old", "description": "d", "personality": "p",
                                     "scenario": "s", "first_mes": "f", "mes_example": ""}).encode())
    assert (card.spec, card.name, card.description, card.first_mes) == ("v1", "Old", "d", "f")


def test_a_v2_card_reads_its_data_and_book():
    raw = v2(character_book={"entries": [{"keys": ["oven"], "content": "Old oven.", "enabled": True,
                                          "insertion_order": 5, "extensions": {}}]})
    card = charcard.read(b"\xef\xbb\xbf" + json.dumps(raw).encode())
    assert card.spec == "v2" and card.name == "Luna" and card.alternate_greetings == ["Hello."]
    assert card.character_book["entries"][0]["keys"] == ["oven"]


def test_a_v3_card_brings_its_nickname():
    raw = v2(nickname="Lu")
    raw.update(spec="chara_card_v3", spec_version="3.0")
    card = charcard.read(json.dumps(raw).encode())
    assert card.spec == "v3" and card.nickname == "Lu"


@pytest.mark.parametrize("blob, code", [
    (b"not a card", "card_unknown"),
    (b"{\"hello\": 1}", "card_unknown"),
    (b"{broken", "card_broken"),
    (json.dumps(v2(name="  ")).encode(), "card_no_name"),
])
def test_what_is_not_a_card_is_named(blob, code):
    with pytest.raises(charcard.CardError) as caught:
        charcard.read(blob)
    assert str(caught.value) == code


def test_in_a_png_ccv3_wins_over_chara_whatever_the_case_of_the_keyword():
    v3 = v2(name="Three")
    v3.update(spec="chara_card_v3", spec_version="3.0")
    card = charcard.read(png({"chara": v2(name="Two"), "CCv3": v3}))
    assert card.name == "Three" and card.spec == "v3"
    assert charcard.read(png({"Chara": v2(name="Two")})).name == "Two"
    # The PNG's own picture comes with it, kept as a picture the page may show.
    assert card.picture.startswith(b"\x89PNG") and not card.picture_note


def test_a_png_without_a_card_says_so():
    with pytest.raises(charcard.CardError, match="card_no_data"):
        charcard.read(picture_bytes())


def test_a_charx_card_and_its_main_icon():
    raw = v2()
    raw.update(spec="chara_card_v3", spec_version="3.0")
    raw["data"]["assets"] = [{"type": "icon", "uri": "https://example.invalid/x.png", "name": "web", "ext": "png"},
                             {"type": "icon", "uri": "embeded://assets/icon/images/main.png", "name": "main",
                              "ext": "png"}]
    card = charcard.read(charx(raw, {"assets/icon/images/main.png": picture_bytes()}))
    assert card.name == "Luna" and card.picture.startswith(b"\x89PNG")


# ---- hostile files


def test_every_size_is_bounded(monkeypatch):
    with pytest.raises(charcard.CardError, match="card_too_large"):
        charcard.read(b"{" + b" " * charcard.MAX_FILE)
    with pytest.raises(charcard.CardError, match="card_too_large"):
        charcard.read(json.dumps(v2(description="x" * (charcard.MAX_JSON + 10))).encode())
    with pytest.raises(charcard.CardError, match="card_too_large"):
        charcard.read(png({"chara": v2(description="x" * (charcard.MAX_JSON + 10))}))


def test_too_many_png_chunks_are_refused():
    data = picture_bytes()
    chunk = struct.pack(">I", 0) + b"zzZz" + struct.pack(">I", zlib.crc32(b"zzZz"))
    hostile = data[:33] + chunk * (charcard.MAX_CHUNKS + 1) + data[33:]
    with pytest.raises(charcard.CardError, match="card_unsafe"):
        charcard.read(hostile)


def test_a_truncated_png_chunk_is_broken():
    data = png({"chara": v2()})
    with pytest.raises(charcard.CardError, match="card_broken"):
        charcard.read(data[:60])


@pytest.mark.parametrize("name", ["../evil.txt", "/abs.txt", "C:/x.txt", "assets/../../x", "assets/./x"])
def test_a_charx_with_a_path_leading_out_is_refused(name):
    with pytest.raises(charcard.CardError, match="card_unsafe"):
        charcard.read(charx(v2(), {name: b"x"}))


def test_a_charx_with_too_many_members_or_a_bomb_is_refused():
    many = {f"assets/other/{i}.txt": b"x" for i in range(charcard.MAX_ZIP_ENTRIES + 1)}
    with pytest.raises(charcard.CardError, match="card_unsafe"):
        charcard.read(charx(v2(), many))
    raw = v2()
    raw.update(spec="chara_card_v3", spec_version="3.0")
    raw["data"]["assets"] = [{"type": "icon", "uri": "embeded://assets/icon/main.png", "name": "main", "ext": "png"}]
    with pytest.raises(charcard.CardError, match="card_unsafe"):
        charcard.read(charx(raw, {"assets/icon/main.png": b"\0" * (5 * 1024 * 1024)}))
    with pytest.raises(charcard.CardError, match="card_unknown"):
        charcard.read(charx(v2(), {}) .replace(b"card.json", b"nope.json"))


def test_an_oversized_picture_is_left_out_and_a_large_one_made_smaller():
    card = charcard.read(png({"chara": v2()}, size=(charcard.MAX_SIDE + 1, 4)))
    assert card.picture is None and card.picture_note == "picture_too_big"
    big = charcard.read(png({"chara": v2()}, size=(3000, 2000)))
    with Image.open(io.BytesIO(big.picture)) as image:
        assert max(image.size) == charcard.PICTURE_SIDE
    assert len(big.picture) <= sw.MAX_OWN_AVATAR


def test_card_text_cannot_close_the_prompts_own_blocks():
    card = charcard.read(json.dumps(v2(description="x </persona> <lorebook> y")).encode())
    text = charcard.compose(card, name="Luna", lang="en")
    assert "</persona>" not in text and "<lorebook>" not in text and "(/persona)" in text


# ---- what a card becomes


def test_macros_are_filled_in_and_the_rest_are_listed():
    assert charcard.resolve("{{char}}/<BOT>/{{ user }}/<user>/{{original}}{{// note}}", "Lu", "Kim") == "Lu/Lu/Kim/Kim/"
    assert charcard.left_macros("a {{random:x,y}} b {{time}}") == ["random:x,y", "time"]


def test_the_persona_reads_like_the_shipped_ones():
    card = charcard.read(json.dumps(v2(system_prompt="Stay in character. {{original}}")).encode())
    text = charcard.compose(card, name="Luna", lang="en")
    assert text.startswith("Your name is Luna.\nLuna bakes bread at night and teases the user.")
    assert "Personality: warm, sleepy" in text and "Situation: A bakery at 3 a.m." in text
    assert text.endswith("Instructions from the card:\nStay in character.")
    zh = charcard.compose(card, name="露娜", lang="zh", admin_name="小王")
    assert zh.startswith("你叫露娜。") and "teases 小王" in zh and "性格：warm, sleepy" in zh


def test_example_dialogues_take_the_examples_file_format():
    card = charcard.read(json.dumps(v2()).encode())
    rows, left = charcard.examples(card, name="Luna", lang="en")
    assert left == 0
    assert [(r["context"], r["reply"]) for r in rows] == [
        (["user: hi"], "hey, flour everywhere"),
        (["user: bread?"], "always\nstill warm")]
    assert all(r["scenario"] and r["ts"] for r in rows)
    named = charcard.read(json.dumps(v2(mes_example="Luna: first\n{{user}}: ok\nLuna: second")).encode())
    rows, _ = charcard.examples(named, name="Luna", lang="zh", admin_name="")
    assert [(r["context"], r["reply"]) for r in rows] == [([], "first"), (["Luna: first", "用户: ok"], "second")]


def test_long_examples_are_counted_not_cut():
    card = charcard.read(json.dumps(v2(mes_example="{{user}}: hi\n{{char}}: " + "x" * 3000)).encode())
    assert charcard.examples(card, name="Luna", lang="en") == ([], 1)


def test_the_lorebook_goes_through_the_world_info_import():
    card = charcard.read(json.dumps(v2(character_book={"entries": [
        {"keys": ["oven"], "content": "@@depth 4\nThe oven is old.", "enabled": True, "insertion_order": 7},
        {"keys": ["x"], "content": "r", "use_regex": True, "enabled": True},
        {"keys": ["off"], "content": "c", "enabled": False},
        {"keys": [], "content": "always", "constant": True, "enabled": True},
    ]})).encode())
    entries, skipped, partly = charcard.lorebook(card)
    assert entries == [{"name": "oven", "keywords": ["oven"], "content": "The oven is old.", "priority": 7}]
    assert skipped == {"regex": 1, "disabled": 1, "always_on": 1} and partly == {"decorators": 1}


# ---- applying, backups, export and the round trip


def test_applying_writes_each_part_and_keeps_copies(home):
    (home / "persona.txt").write_text("My own words", encoding="utf-8")
    (home / "data").mkdir()
    (home / "data" / "examples.en.jsonl").write_text('{"context": [], "reply": "mine"}\n', encoding="utf-8")
    (home / "persona.card.json").write_text(json.dumps({"reply_style": {"emoji": True}}), encoding="utf-8")
    raw = v2(nickname="Lu", character_book={"entries": [{"keys": ["oven"], "content": "Old.", "enabled": True}]})
    card = charcard.read(png({"chara": raw}))
    text = charcard.compose(card, name="Luna", lang="en")
    done = charcard.apply(home, card, charcard.PARTS, name="Luna", persona=text, values=values(home))
    assert done["done"] == list(charcard.PARTS)
    assert values(home)["PERSONA_NAME"] == "Luna" and values(home)["PERSONA_AVATAR"] == "own"
    assert (home / "persona.txt").read_text(encoding="utf-8") == text + "\n"
    assert (home / "persona.txt.bak").read_text(encoding="utf-8") == "My own words"
    assert len(list(home.glob("persona.txt.*.bak"))) == 1
    assert len(list((home / "data").glob("examples.en.jsonl.*.bak"))) == 1
    assert json.loads((home / "data" / "lorebook.en.json").read_text(encoding="utf-8"))["entries"][0]["keywords"] == ["oven"]
    assert json.loads((home / "persona.card.json").read_text(encoding="utf-8")) == {
        "reply_style": {"emoji": True}, "aliases": ["Lu"]}
    assert sw.own_avatar(home) is not None


def test_only_the_chosen_parts_change(home):
    card = charcard.read(json.dumps(v2()).encode())
    done = charcard.apply(home, card, ["examples"], name="", persona="", values=values(home))
    assert done["done"] == ["examples"] and values(home)["PERSONA_NAME"] == "Mira"
    assert not (home / "persona.txt").exists()
    with pytest.raises(charcard.CardError, match="card_nothing"):
        charcard.apply(home, card, [], name="", persona="", values=values(home))
    with pytest.raises(charcard.CardError, match="card_persona"):
        charcard.apply(home, card, ["persona"], name="", persona="x" * (charcard.PERSONA_LIMIT + 1),
                       values=values(home))
    with pytest.raises(charcard.CardError, match="card_name"):
        charcard.apply(home, card, ["name"], name="${LLM_API_KEY}", persona="", values=values(home))


@pytest.mark.parametrize("kind", ["png", "json"])
def test_export_then_import_is_the_same_character(home, kind):
    sw.write_env(home / ".env", {"ADMIN_NAME": "Kim"})
    raw = v2(nickname="Lu", description="{{char}} bakes for {{user}}.",
             character_book={"entries": [{"keys": ["oven", "stove"], "content": "Old oven, {{user}} fixed it.",
                                          "enabled": True, "insertion_order": 9, "comment": "oven"}]})
    first = charcard.read(png({"chara": raw}))
    text = charcard.compose(first, name="Luna", lang="en", admin_name="Kim")
    charcard.apply(home, first, charcard.PARTS, name="Luna", persona=text, values=values(home))
    blob = (charcard.png_card if kind == "png" else charcard.json_card)(home, values(home))
    again = charcard.read(blob)
    assert again.personagent is not None and again.name == "Luna"
    assert charcard.compose(again, name="Luna", lang="en", admin_name="Kim") == text
    strip = (lambda rows: [(r["context"], r["reply"]) for r in rows])
    assert strip(charcard.examples(again, name="Luna", lang="en", admin_name="Kim")[0]) == \
        strip(charcard.examples(first, name="Luna", lang="en", admin_name="Kim")[0])
    assert charcard.lorebook(again)[0] == charcard.lorebook(first)[0]
    # The admin's own name stays at home.
    assert b"Kim" not in (blob if kind == "json" else json.dumps(charcard.export(home, values(home))).encode())
    if kind == "png":
        assert again.picture is not None and charcard.read(blob).spec == "v3"
        assert "Lu" in charcard.export(home, values(home))["data"]["extensions"]["personagent"]["aliases"]


def test_nothing_private_goes_into_a_card(home):
    sw.write_env(home / ".env", {"ADMIN_NAME": "Kim Private", "TAVILY_API_KEY": "tvly-secret-1234"})
    (home / "runtime").mkdir()
    (home / "runtime" / "memory.json").write_text('{"secret note": "lives here"}', encoding="utf-8")
    (home / "data").mkdir()
    (home / "data" / "examples.en.jsonl").write_text(
        json.dumps({"context": ["Alex Realname: hello Kim Private"], "reply": "hi"}) + "\n", encoding="utf-8")
    (home / "persona.txt").write_text("Your name is Mira. Kim Private is your friend.", encoding="utf-8")
    text = json.dumps(charcard.export(home, values(home)))
    for secret in ("sk-test-0123456789", "tvly-secret", "Kim Private", "Alex Realname", "secret note"):
        assert secret not in text, secret
    assert "{{user}} is your friend" in text


def test_a_png_card_without_a_picture_of_its_own_uses_the_portrait_or_a_plain_square(home):
    sw.write_env(home / ".env", {"PERSONA_AVATAR": "deepseek"})
    with Image.open(io.BytesIO(charcard.png_card(home, values(home)))) as image:
        assert image.size[0] == image.size[1]
    sw.write_env(home / ".env", {"PERSONA_AVATAR": ""})
    with Image.open(io.BytesIO(charcard.png_card(home, values(home)))) as image:
        assert image.size == (512, 512)


# ---- the page


@pytest.fixture
def page(home, monkeypatch, tmp_path_factory):
    folders = tmp_path_factory.mktemp("user-dirs")
    monkeypatch.setenv("PERSONAGENT_USER_DIRS", os.pathsep.join([str(folders / "Desktop"), str(folders / "Documents")]))
    (folders / "Desktop").mkdir()
    workspace = welcome.Workspace(home)
    restarts = []
    monkeypatch.setattr(workspace, "_restart_agent", lambda: restarts.append(True))
    with TestClient(welcome.create_app(home, TOKEN, workspace=workspace), base_url="http://127.0.0.1") as client:
        client.restarts, client.folders = restarts, folders
        yield client
    workspace.close()


def test_card_routes_need_the_page_token(page):
    assert page.get("/api/cards").status_code == 403
    for path in ("read", "apply", "cancel", "export", "draft"):
        assert page.post(f"/api/cards/{path}", content=b"{}").status_code == 403


def test_the_page_previews_then_applies_a_card(page, home):
    (home / "persona.txt").write_text("My own words", encoding="utf-8")
    raw = v2(system_prompt="Write long replies.", description="{{char}} {{time}}")
    shown = page.post("/api/cards/read", headers=HEADERS, content=png({"chara": raw})).json()
    assert shown["name"] == "Luna" and shown["oldName"] == "Mira" and shown["personaOwn"]
    assert shown["examples"] == 2 and shown["instructions"] and shown["macros"] == ["time"]
    assert shown["picture"].startswith("data:image/png;base64,") and shown["greeting"] == "Oh, you are up too?"
    assert (home / "persona.txt").read_text(encoding="utf-8") == "My own words"
    wrong = page.post("/api/cards/apply", headers=HEADERS, json={"id": "nope", "parts": ["name"]})
    assert wrong.json()["error"] == "card_expired"
    done = page.post("/api/cards/apply", headers=HEADERS, json={
        "id": shown["id"], "parts": ["name", "persona"], "name": "Lunette", "persona": "Your name is Lunette."}).json()
    assert done["done"] == ["name", "persona"] and done["state"]["name"] == "Lunette" and page.restarts == [True]
    assert (home / "persona.txt").read_text(encoding="utf-8") == "Your name is Lunette.\n"
    again = page.post("/api/cards/apply", headers=HEADERS, json={"id": shown["id"], "parts": ["name"]})
    assert again.json()["error"] == "card_expired"


def test_the_page_names_a_file_that_is_not_a_card(page):
    for blob, code in ((b"hello", "card_unknown"), (picture_bytes(), "card_no_data")):
        response = page.post("/api/cards/read", headers=HEADERS, content=blob)
        assert response.status_code == 400 and response.json()["error"] == code
    response = page.post("/api/cards/read", headers={**HEADERS, "content-length": str(charcard.MAX_FILE + 1)},
                         content=b"x")
    assert response.json()["error"] == "card_too_large"


def test_the_page_saves_a_card_in_a_known_folder_only(page):
    assert [t["id"] for t in page.get("/api/cards", headers=HEADERS).json()["targets"]] == ["desktop", "documents"]
    done = page.post("/api/cards/export", headers=HEADERS, json={"to": "desktop", "format": "png"}).json()
    path = Path(done["path"])
    assert path.parent == page.folders / "Desktop" and path.name == "Mira.card.png"
    assert charcard.read(path.read_bytes()).name == "Mira"
    second = page.post("/api/cards/export", headers=HEADERS, json={"to": "desktop", "format": "png"}).json()
    assert second["name"] == "Mira.card-2.png"
    for bad in ({"to": "../x", "format": "png"}, {"to": "desktop", "format": "exe"}):
        assert page.post("/api/cards/export", headers=HEADERS, json=bad).json()["error"] == "card_invalid_place"


def test_the_persona_box_takes_a_long_imported_persona(page, home):
    text = "人" * welcome.PERSONA_LIMIT
    response = page.post("/api/persona", headers=HEADERS, json={"text": text})
    assert response.status_code == 200
    assert page.get("/api/catalog", headers=HEADERS).json()["personaLimit"] == welcome.PERSONA_LIMIT


# ---- the draft


def model(monkeypatch, handler):
    def pooled(self, **kwargs):
        client = self._http_pool.get("mock")
        if client is None:
            client = self._http_pool["mock"] = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return _PooledHTTP(client)

    monkeypatch.setattr(drafting._Client, "_http", pooled)


def test_a_draft_comes_back_unsaved_and_is_counted(page, home, monkeypatch):
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "You fix old radios.\n- Speak briefly."},
                                                      "finish_reason": "stop"}],
                                         "usage": {"prompt_tokens": 100, "completion_tokens": 20}})

    model(monkeypatch, handler)
    done = page.post("/api/cards/draft", headers=HEADERS, json={"idea": "a radio repairer"}).json()
    assert done["text"] == "Your name is Mira.\nYou fix old radios.\n- Speak briefly."
    assert not (home / "persona.txt").exists()
    assert "a radio repairer" in seen[0]["messages"][-1]["content"] and "English" in seen[0]["messages"][0]["content"]
    found = usage.read_summary(home / "runtime" / usage.USAGE_FILE)
    assert found["todayPurposes"] == {"persona": 1} and found["today"]["tokens"] == 120


@pytest.mark.parametrize("status, code", [(401, "key_rejected"), (429, "model_limited"), (500, "model_unreachable")])
def test_a_draft_reports_the_model_error(page, monkeypatch, status, code):
    monkeypatch.setattr("persona_agent.llm.asyncio.sleep", lambda s: _done())
    model(monkeypatch, lambda request: httpx.Response(status, json={"error": {"message": "no"}}))
    response = page.post("/api/cards/draft", headers=HEADERS, json={"idea": "someone"})
    assert response.status_code == 400 and response.json()["error"] == code


async def _done():
    return None


def test_a_draft_needs_a_model_and_an_idea(page, home):
    assert page.post("/api/cards/draft", headers=HEADERS, json={"idea": " "}).json()["error"] == "draft_idea"
    sw.write_env(home / ".env", {"LLM_API_KEY": ""})
    assert page.post("/api/cards/draft", headers=HEADERS, json={"idea": "x"}).json()["error"] == "key_required"


# ---- the terminal


def test_the_terminal_imports_and_exports_a_card(home, tmp_path_factory, capsys, monkeypatch):
    # cli.main sets AGENT_HOME for the process; this puts the old value back afterwards.
    monkeypatch.setenv("AGENT_HOME", str(home))
    folder = tmp_path_factory.mktemp("cards")
    source = folder / "luna.png"
    source.write_bytes(png({"chara": v2()}))
    assert cli.main(["--home", str(home), "character", "import", str(source)]) == 2
    assert "--yes" in capsys.readouterr().err and values(home)["PERSONA_NAME"] == "Mira"
    assert cli.main(["--home", str(home), "character", "import", str(source), "--yes",
                     "--only", "name,persona"]) == 0
    said = capsys.readouterr().out
    assert "Imported: name, persona." in said and "learned as Mira" in said
    assert values(home)["PERSONA_NAME"] == "Luna"
    assert (home / "persona.txt").read_text(encoding="utf-8").startswith("Your name is Luna.")
    target = folder / "out.json"
    assert cli.main(["--home", str(home), "character", "export", str(target)]) == 0
    assert charcard.read(target.read_bytes()).name == "Luna"
    assert cli.main(["--home", str(home), "character", "export", str(target)]) == 2
    assert cli.main(["--home", str(home), "character", "import", str(folder / "missing.png"), "--yes"]) == 2
