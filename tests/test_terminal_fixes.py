"""Terminal commands: what each says, and that none reports one failure as another."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from persona_agent import chat, coding, connections, demo, direct, direct_setup, doctor
from persona_agent import evals, ledger_admin, shortcut
from persona_agent import setup_wizard as sw
from persona_agent.astrbot_install import start_astrbot
from persona_agent.direct import base as direct_base
from persona_agent.direct import weixin

from helpers import check


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_LANG", "en")
    monkeypatch.setattr(sw.langs, "interactive", lambda: False)
    return tmp_path


# ---- T1: a QR code on a console that has no block characters

class Legacy(io.TextIOWrapper):
    """Standard output on a legacy code page, as a pipe on Windows can be."""

    def __init__(self) -> None:
        super().__init__(io.BytesIO(), encoding="cp1252", errors="strict")

    def text(self) -> str:
        self.flush()
        return self.buffer.getvalue().decode("cp1252")


def test_a_qr_code_falls_back_to_plain_characters(monkeypatch) -> None:
    out = Legacy()
    monkeypatch.setattr(sys, "stdout", out)
    sw.print_qr("https://liteapp.example/qr?k=1")
    drawn = out.text()
    check("drawn with plain characters", "##" in drawn and len(drawn.splitlines()) > 20, drawn[:200])


def test_a_sign_in_that_cannot_be_shown_is_not_a_network_failure(home, monkeypatch, capsys) -> None:
    async def scan(client, show, given):
        show("https://liteapp.example/qr?k=1")
        return {"token": "w"}
    monkeypatch.setattr(direct, "sign_in_for", lambda kind: (scan, LookupError))
    spec = connections.platform("weixin_oc")

    def show(content: str) -> None:
        "█".encode("cp1252")
    with pytest.raises(RuntimeError, match="^display_failed$"):
        direct_setup.sign_in(spec, {}, show)

    monkeypatch.setattr(sw, "print_qr", lambda content: "█".encode("cp1252"))
    check("refused", sw.connect_main(["wechat"]) == 1)
    err = capsys.readouterr().err
    check("in words that fit", "could not display the sign-in" in err and "could not be reached" not in err, err)
    check("nothing saved", not direct_base.credentials_path(home).exists())


# ---- T2: WeChat state belongs to one login

def test_wechat_state_of_another_login_is_ignored(tmp_path) -> None:
    state = tmp_path / "weixin_oc.json"
    old = weixin.Weixin({"weixin_oc_token": "old-token"}, state=state)
    old.cursor, old.contexts = "c-old", {"u@im.wechat": "ctx-old"}
    old._save()
    new = weixin.Weixin({"weixin_oc_token": "new-token"}, state=state)
    check("a new login starts clean", new.cursor == "" and new.contexts == {})
    new.cursor = "c-new"
    new._save()
    old._save()   # the running process of the ended login writes back late
    again = weixin.Weixin({"weixin_oc_token": "new-token"}, state=state)
    check("the late write of the ended login is not taken", again.cursor == "" and again.contexts == {})
    again.cursor = "c-new"
    again._save()
    same = weixin.Weixin({"weixin_oc_token": "new-token"}, state=state)
    check("the same login keeps its own", same.cursor == "c-new")
    check("the token is not written", "new-token" not in state.read_text(encoding="utf-8"))
    state.write_text(json.dumps({"cursor": "c-legacy", "contexts": {}}), encoding="utf-8")
    check("state without an owner is not trusted",
          weixin.Weixin({"weixin_oc_token": "new-token"}, state=state).cursor == "")


# ---- T3, T5: personagent learned

@pytest.fixture
def ledger_files(tmp_path, monkeypatch) -> dict:
    files = {"evidence": tmp_path / "evidence.zh.jsonl", "ledger": tmp_path / "candidate_ledger.zh.jsonl",
             "examples_view": tmp_path / "promoted.examples.zh.jsonl",
             "feedback_view": tmp_path / "promoted.feedback.zh.jsonl"}
    monkeypatch.setattr(ledger_admin, "_paths", lambda lang: files)
    return files


def test_learned_alone_lists(ledger_files, monkeypatch, capsys) -> None:
    monkeypatch.setenv("AGENT_LANG", "en")
    check("exit 0", ledger_admin.main([], prog="personagent learned") == 0)
    out = capsys.readouterr().out
    check("listed", "Nothing is being observed right now." in out, out)
    check("says practice does not count", "practice in `personagent chat`" in out, out)


def test_learned_speaks_the_install_language_without_plural_marks(ledger_files, monkeypatch, capsys) -> None:
    monkeypatch.setenv("AGENT_LANG", "en")
    ledger_admin.main(["rebuild"], prog="personagent learned")
    ledger_admin.main(["show", "abc"], prog="personagent learned")
    english = capsys.readouterr().out
    check("no (s) plurals", "(s)" not in english, english)
    monkeypatch.setenv("AGENT_LANG", "zh")
    ledger_admin.main(["rebuild"], prog="personagent learned")
    ledger_admin.main(["lineage"], prog="personagent learned")
    ledger_admin.main(["show", "abc"], prog="personagent learned")
    out = capsys.readouterr().out
    check("in Chinese", "检索视图已重建" in out and "生效中的候选项" in out and "尚无沿袭记录" in out
          and "没有与 'abc' 匹配的候选项" in out, out)


# ---- T4, T6, T15: the commands a hint names carry the home

def test_hints_name_the_command_with_the_home(home, capsys) -> None:
    check("start without a terminal", sw.start_main([]) == 2)
    out = capsys.readouterr().out
    check("names the terminal menu, with the home", f"--home {home} start --terminal" in out, out)
    with pytest.raises(FileNotFoundError) as missing:
        start_astrbot(home)
    check("AstrBot's install command, with the home",
          f"--home {home} connect astrbot --install" in str(missing.value), str(missing.value))


# ---- T7: removing shortcuts that are not there

@pytest.mark.skipif(not shortcut.WINDOWS, reason="PowerShell removes the links")
def test_removing_absent_shortcuts_succeeds_and_a_failed_removal_says_so(tmp_path) -> None:
    empty = tmp_path / "Desktop"
    empty.mkdir()
    check("nothing there is nothing to fail", shortcut.run(shortcut.script(tmp_path, remove=True, folders=[empty])) == "")
    stuck = tmp_path / "Programs"
    (stuck / shortcut.LINK).mkdir(parents=True)
    (stuck / shortcut.LINK / "keep.txt").write_text("x", encoding="utf-8")
    check("one that stays is a failure",
          shortcut.run(shortcut.script(tmp_path, remove=True, folders=[stuck])) != "")


def test_a_failed_removal_has_its_own_sentence(home, monkeypatch, capsys) -> None:
    monkeypatch.setattr(shortcut, "WINDOWS", True)
    monkeypatch.setattr(shortcut, "run", lambda source: "access denied")
    check("exit 1", shortcut.main(["--remove"]) == 1)
    out = capsys.readouterr().out
    check("removal, not making", "could not be removed: access denied" in out and "made" not in out, out)


# ---- T8: --key-env with an empty variable

def test_an_empty_key_env_is_refused_first_in_the_chosen_language(tmp_path, monkeypatch) -> None:
    fresh = tmp_path / "fresh"
    monkeypatch.setenv("AGENT_HOME", str(fresh))
    monkeypatch.delenv("AGENT_LANG", raising=False)
    monkeypatch.setenv("EMPTY_KEY", "")
    with pytest.raises(SystemExit) as stop:
        sw.main(["--no-input", "--lang", "zh", "--provider", "deepseek", "--key-env", "EMPTY_KEY"])
    check("in Chinese", "该环境变量为空" in str(stop.value.code), str(stop.value.code))
    check("nothing written", not fresh.exists() or not any(fresh.iterdir()))


def test_memory_help_lists_its_four_commands(home, capsys) -> None:
    from persona_agent import cli

    with pytest.raises(SystemExit) as stop:
        cli.main(["memory", "--help"])
    out = capsys.readouterr().out
    check("help exits 0", stop.value.code == 0)
    check("usage names the command", out.startswith("usage: personagent memory"), out)
    for name in ("list", "removed", "forget", "restore"):
        check(f"lists {name}", f"    {name} " in out, out)
    check("the top-level list names it", "memory" in cli._usage()
          and "Look at what it remembers" in cli._usage())


# ---- T9: the demo's ledger line

def test_each_ledger_verb_is_a_whole_sentence() -> None:
    for lang in ("en", "zh"):
        text = demo._in(demo._TEXT, lang)
        for sentence in [*text["verbs"].values(), text["verb_retry"], text["verb_retry_moved"]]:
            check(f"{lang}: {sentence!r} holds the name and the quotation",
                  "{who}" in sentence and "{said}" in sentence)
    check("not the state's key", "rejected" not in demo._TEXT["en"]["verbs"].values())


# ---- T10, T19: the start menu

def test_the_start_menu_has_its_own_words_for_each_unset_value() -> None:
    check("two keys, two sentences", sw._TEXT["start_no_name"][0] != sw._TEXT["start_no_key"][0])


def test_the_start_menu_names_a_choice_it_does_not_have(home, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sw.langs, "interactive", lambda: True)
    choices = iter(["9", "0"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(choices))
    check("left", sw.start_main([]) == 0)
    out = capsys.readouterr().out
    check("said", '"9" is not one of the options' in out, out)
    check("both values named", "Character: not yet chosen" in out and "API key: not yet entered" in out, out)


# ---- T11: an unknown language, and a hook given no JSON

@pytest.mark.parametrize("run", [
    lambda: chat.run(["--lang", "xx"]),
    lambda: demo.main(["--lang", "xx"]),
    lambda: evals.parse_args(["--lang", "xx"]),
])
def test_an_unknown_language_is_refused(run, capsys) -> None:
    with pytest.raises(SystemExit) as stop:
        run()
    check("non-zero", stop.value.code == 2)
    check("in one sentence", "invalid choice: 'xx'" in capsys.readouterr().err)


def test_a_spelling_of_a_known_language_is_taken() -> None:
    check("zh_CN", evals.parse_args(["--lang", "zh_CN"]).lang == "zh")


@pytest.mark.parametrize("stdin", [b"not json", b"[1, 2]"])
def test_the_hook_refuses_input_that_is_not_an_event(home, monkeypatch, capsys, stdin) -> None:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin)))
    check("exit 1, which does not stop the coding agent", coding.hook_main([]) == 1)
    check("in words", "JSON object" in capsys.readouterr().err)


# ---- T12: --no-input never waits for a scan

@pytest.mark.parametrize("word, says", [("qq", "--appid and --secret"), ("wechat", "scanning a code")])
def test_no_input_never_starts_a_scan(home, monkeypatch, capsys, word, says) -> None:
    monkeypatch.setattr(direct, "sign_in_for", lambda kind: pytest.fail("a scan was started"))
    check("refused", sw.connect_main([word, "--no-input"]) == 2)
    err = capsys.readouterr().err
    check("says what to do", says in err, err)


# ---- T14: piped init does not claim to be done

def test_piped_init_does_not_say_setup_is_complete(home, capsys) -> None:
    check("exit 2", sw.main(["--terminal"]) == 2)
    out = capsys.readouterr().out
    check("skipped, not complete", "skipped" in out and "Setup complete" not in out, out)
    check("names the command with the home", f"--home {home} init --terminal" in out, out)
    check("and writes nothing", not (home / ".env").exists() and not (home / "persona.txt").exists())


# ---- T16, T17: AstrBot from the menu; the language the menu is in

def test_astrbot_from_the_menu_has_its_own_words(home, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sw, "ask_yn", lambda prompt, default_yes=False: False)
    check("skipped", sw.step_astrbot(home / ".env", {}, {}, standalone=True) is None)
    out = capsys.readouterr().out
    check("its own sentences", "Slack, KOOK or Feishu" in out and "AstrBot was not connected" in out, out)
    check("not the setup's step", "after this setup" not in out, out)


def test_the_language_question_starts_on_the_menus_language(home, monkeypatch) -> None:
    monkeypatch.setattr(sw, "detect_lang", lambda: "zh")
    asked = []

    def stop(default: str) -> str:
        asked.append(default)
        raise KeyboardInterrupt
    monkeypatch.setattr(sw, "ask_language", stop)
    with pytest.raises(KeyboardInterrupt):
        sw.run_wizard(home, sw.Launcher(python=sys.executable, home=home))
    check("English, as the menu", asked == ["en"], str(asked))


# ---- T18: what each option is for

def test_each_option_says_what_it_belongs_to(home) -> None:
    with pytest.raises(SystemExit) as qq:
        sw.connect_main(["telegram", "--qq"])
    check("--qq is astrbot's", str(qq.value.code) == "--qq: used only with astrbot, not with a chat platform",
          str(qq.value.code))
    with pytest.raises(SystemExit) as react:
        sw.connect_main(["telegram", "--react"])
    check("--react is the coding assistants'", "claude-code and codex" in str(react.value.code)
          and "astrbot" not in str(react.value.code), str(react.value.code))


# ---- T20: doctor names the directly connected platforms

def test_doctor_lists_the_directly_connected_platforms(home, monkeypatch) -> None:
    check("none", doctor.direct_row(doctor.direct_platforms(home))[1] == "none connected")
    direct_base.save_credentials(home, "telegram", {"telegram_token": "t"})
    direct_base.save_credentials(home, "discord", {"discord_token": "d"})
    found = doctor.direct_platforms(home)
    check("not running", found["running"] is False and [p["id"] for p in found["platforms"]] == ["telegram", "discord"])
    check("named, state unknown", "Telegram, Discord (state unknown" in doctor.direct_row(found)[1])
    status = direct_base.Status(home)
    status.set("telegram", "connected")
    status.set("discord", "refused", "token_rejected")
    monkeypatch.setattr(doctor, "_direct_running", lambda found: True)
    mark, words = doctor.direct_row(doctor.direct_platforms(home))
    check("each state", words == "Telegram: connected; Discord: refused the connection (token_rejected)", words)
    check("a refusal is marked", mark == " FAIL")


def test_doctor_json_carries_the_platforms(home, monkeypatch, capsys) -> None:
    monkeypatch.setattr(doctor, "run_checks", lambda: [])
    monkeypatch.setattr(doctor, "check_config", lambda: [])
    monkeypatch.setattr(doctor, "update_notice", lambda: None)
    doctor.main(["--json"])
    report = json.loads(capsys.readouterr().out)
    check("in the report", report["direct_platforms"] == {"running": False, "platforms": []}, str(report))


def test_a_running_direct_process_is_recognised_from_the_app_records(home, monkeypatch) -> None:
    from persona_agent import services

    records = home / "runtime" / "desktop"
    records.mkdir(parents=True)
    (records / "children-1.json").write_text(json.dumps(
        {"owner": 1, "command": "", "children": {"direct": {"pid": 4242, "argv": ["python", "-m", "x"]}}}),
        encoding="utf-8")
    monkeypatch.setattr(services, "_command_line", lambda pid: "python -m x --home " + str(home.resolve()))
    check("running", doctor._direct_running(home.resolve()))
    monkeypatch.setattr(services, "_command_line", lambda pid: "")
    check("gone", not doctor._direct_running(home.resolve()))
