"""`personagent connect <platform>`: the terminal connects the platforms the
page connects, through the same checks, into the same file."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from persona_agent import connections as conn
from persona_agent import direct, direct_setup
from persona_agent import setup_wizard as sw
from persona_agent.direct import base as direct_base

from helpers import check


class StandIn:
    """A platform that answers `check` as told, with no network."""

    def __init__(self, outcome: BaseException | None = None):
        self.outcome, self.checked, self.closed = outcome, [], False

    def factory(self, kind: str, values: dict, home: Path):
        self.checked.append((kind, dict(values)))
        return self

    async def check(self) -> str:
        if self.outcome is not None:
            raise self.outcome
        return "ok"

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    return tmp_path


def stand_in(monkeypatch, outcome: BaseException | None = None) -> StandIn:
    platform = StandIn(outcome)
    monkeypatch.setattr(direct, "platform_for", platform.factory)
    return platform


def saved(home: Path) -> dict:
    path = direct_base.credentials_path(home)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def flow(shown: str, values: dict | None = None, error: BaseException | None = None):
    """A QR or link sign-in that shows `shown`, then returns `values` or raises `error`."""
    class Failed(Exception):
        pass

    async def scan(client, show, given):
        show(shown)
        if error is not None:
            raise error
        return {**given, **(values or {})}
    return lambda kind: (scan, Failed)


# ---- arguments

def test_every_direct_platform_is_a_target_under_its_word_and_its_id() -> None:
    targets = sw.direct_targets()
    for kind in direct.KINDS:
        check(f"{kind} by its id", targets[kind] == kind)
    check("qq and wechat by their words", targets["qq"] == "qq_official" and targets["wechat"] == "weixin_oc")
    check("nothing else", set(targets.values()) == set(direct.KINDS))


def test_each_field_is_an_option_named_after_its_key() -> None:
    parser = sw.connect_parser("personagent connect")
    args = parser.parse_args(["matrix", "--matrix-homeserver", "https://example.org", "--matrix-token", "t",
                              "--matrix-owner", "@me:example.org", "--no-input"])
    check("the target", args.target == "matrix")
    check("each value under its key", (args.field_matrix_homeserver, args.field_matrix_token,
                                        args.field_matrix_owner) == ("https://example.org", "t", "@me:example.org"))
    check("--no-input", args.no_input)
    for kind in direct.KINDS:
        for item in conn.platform(kind).fields:
            check(f"{kind}: --{item.key.replace('_', '-')} exists",
                  parser.parse_args([kind, f"--{item.key.replace('_', '-')}", "x"]) is not None)


def test_the_help_names_the_platforms_and_their_values(home, capsys) -> None:
    with pytest.raises(SystemExit) as exit_:
        sw.connect_main(["--help"])
    out = capsys.readouterr().out
    check("help exits cleanly", exit_.value.code == 0)
    check("platforms are named", "telegram" in out and "wechat" in out, out)
    check("a value carries its catalog label", "--telegram-token" in out and "Bot token" in out, out)


def test_the_help_follows_lang(home, capsys) -> None:
    with pytest.raises(SystemExit):
        sw.connect_main(["--help", "--lang", "zh"])
    out = capsys.readouterr().out
    check("the description in Chinese", "可直接连接的聊天平台" in out, out)


@pytest.mark.parametrize("argv, words", [
    (["telegram", "--token", "x"], "--token"),
    (["telegram", "--qq"], "--qq"),
    (["telegram", "somewhere"], "DATA_DIR"),
    (["telegram", "--matrix-token", "x"], "--matrix-token"),
    (["telegram", "--remove", "--telegram-token", "x"], "--remove"),
    (["--remove"], "personagent connect telegram"),
    (["astrbot", "--no-input"], "--no-input"),
])
def test_options_that_do_not_belong_are_refused_by_name(home, argv, words) -> None:
    with pytest.raises(SystemExit) as exit_:
        sw.connect_main(argv)
    check(f"{argv} names {words}", words in str(exit_.value.code), str(exit_.value.code))
    check("nothing saved", saved(home) == {})


def test_an_unknown_platform_is_reported_in_words(home, capsys) -> None:
    check("exit 2", sw.connect_main(["myspace"]) == 2)
    err = capsys.readouterr().err
    check("named, with the way to list", "myspace" in err and "`personagent connect`" in err, err)


# ---- the list

def test_the_list_says_what_is_connected_and_what_can_be(home, capsys) -> None:
    direct_base.save_credentials(home, "telegram", {"telegram_token": "t"})
    check("exit 0", sw.connect_main([]) == 0)
    out = capsys.readouterr().out
    rows = {line.split()[0]: line for line in out.splitlines() if line.startswith("    ")}
    for kind in direct.KINDS:
        word = sw.DIRECT_WORDS.get(kind, kind)
        check(f"{word} is listed", word in rows, out)
    check("telegram is connected", rows["telegram"].rstrip().endswith(" connected"), rows["telegram"])
    check("discord is not", rows["discord"].rstrip().endswith("not connected"), rows["discord"])
    check("the way to connect one", "personagent connect <platform>" in out, out)


def test_the_list_in_chinese(home, capsys) -> None:
    check("exit 0", sw.connect_main(["--lang", "zh"]) == 0)
    out = capsys.readouterr().out
    check("Chinese sentences", "可直接连接的聊天平台" in out and "微信" in out and "未连接" in out, out)


# ---- values

def test_no_input_with_a_missing_value_names_it_and_saves_nothing(home, monkeypatch, capsys) -> None:
    platform = stand_in(monkeypatch)
    code = sw.connect_main(["matrix", "--no-input", "--matrix-token", "t"])
    err = capsys.readouterr().err
    check("non-zero", code == 2, str(code))
    check("the missing value by option and label",
          "--matrix-owner (Your own Matrix ID, for example @you:matrix.org) was not given" in err, err)
    check("the default homeserver is not missing", "--matrix-homeserver" not in err, err)
    check("the platform was not asked", platform.checked == [])
    check("nothing saved", saved(home) == {})


def test_a_malformed_value_is_refused_before_the_platform_is_asked(home, monkeypatch, capsys) -> None:
    platform = stand_in(monkeypatch)
    code = sw.connect_main(["irc", "--no-input", "--irc-nick", "nova", "--irc-channels", "#a",
                            "--irc-port", "99999"])
    err = capsys.readouterr().err
    check("non-zero", code == 2)
    check("the option is named", "--irc-port" in err and "not valid" in err, err)
    check("the platform was not asked", platform.checked == [])
    check("nothing saved", saved(home) == {})


def test_values_are_asked_in_a_terminal_with_the_catalog_labels(home, monkeypatch, capsys) -> None:
    platform = stand_in(monkeypatch)
    monkeypatch.setattr(sw.langs, "interactive", lambda: True)
    prompts = []
    answers = iter(["", "@me:example.org"])
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or next(answers))
    monkeypatch.setattr(sw, "_read_secret", lambda prompt: prompts.append(prompt) or "syt_token")
    check("exit 0", sw.connect_main(["matrix"]) == 0)
    out = capsys.readouterr().out
    spec = conn.platform("matrix")
    for item in spec.fields:
        check(f"asked with its label: {item.label[0]}", any(item.label[0] in p for p in prompts), str(prompts))
    for i, step in enumerate(spec.steps, 1):
        check(f"step {i} is shown", f"{i}. {step[0]}" in out)
    check("the note is shown", spec.note[0] in out)
    check("the default homeserver was taken",
          saved(home)["matrix"] == {"matrix_homeserver": "https://matrix.org", "matrix_token": "syt_token",
                                    "matrix_owner": "@me:example.org"}, str(saved(home)))
    check("the page's check ran once", len(platform.checked) == 1)


# ---- connecting with a key

def test_a_key_platform_is_checked_then_saved_as_the_page_saves_it(home, monkeypatch, capsys) -> None:
    platform = stand_in(monkeypatch)
    code = sw.connect_main(["irc", "--no-input", "--irc-nick", "nova", "--irc-channels", "#a,#b"])
    out = capsys.readouterr().out
    check("exit 0", code == 0, out)
    expected = conn.clean_values(conn.platform("irc"), {"irc_nick": "nova", "irc_channels": "#a,#b"})
    check("checked with the cleaned values", platform.checked == [("irc", expected)], str(platform.checked))
    check("closed after the check", platform.closed)
    check("saved in the page's form", saved(home) == {"irc": expected}, str(saved(home)))
    check("what happens next", "is connected" in out and " up" in out, out)


def test_qq_with_its_app_values_is_checked_not_scanned(home, monkeypatch, capsys) -> None:
    platform = stand_in(monkeypatch)
    monkeypatch.setattr(direct, "sign_in_for", lambda kind: pytest.fail("no scan when values are given"))
    check("exit 0", sw.connect_main(["qq", "--appid", "102", "--secret", "s"]) == 0)
    check("checked", platform.checked == [("qq_official", {"appid": "102", "secret": "s"})])
    check("saved", saved(home) == {"qq_official": {"appid": "102", "secret": "s"}})


@pytest.mark.parametrize("refusal, words", [
    (direct_base.Refused("token_rejected"), "Telegram did not accept this token"),
    (direct_base.Refused("bot_in_use"), "Another program is using this bot"),
    (direct_base.Refused("something new"), "Telegram refused the connection"),
    (ConnectionError("down"), "could not be reached"),
    (TypeError("secret-value"), "unexpected error (TypeError)"),
])
def test_a_refusal_is_reported_in_words_and_nothing_is_saved(home, monkeypatch, capsys, refusal, words) -> None:
    stand_in(monkeypatch, refusal)
    code = sw.connect_main(["telegram", "--telegram-token", "123:abc"])
    captured = capsys.readouterr()
    check("non-zero", code == 1, str(code))
    check("why, in words", words in captured.err, captured.err)
    check("not connected", "was not connected, and nothing was saved" in captured.err, captured.err)
    check("no credential or raw error is echoed", "123:abc" not in captured.err + captured.out
          and "secret-value" not in captured.err)
    check("no traceback", "Traceback" not in captured.err)
    check("nothing saved", saved(home) == {})


def test_the_platforms_own_refusal_wording_wins(home, monkeypatch, capsys) -> None:
    stand_in(monkeypatch, direct_base.Refused("token_rejected"))
    sw.connect_main(["zulip", "--zulip-site", "https://chat.example.org", "--zulip-email", "b@example.org",
                     "--zulip-api-key", "k"])
    check("Zulip's sentence", "Zulip does not accept this bot email" in capsys.readouterr().err)


def test_connecting_takes_the_platform_out_of_astrbot(home, monkeypatch, capsys) -> None:
    stand_in(monkeypatch)
    released = []
    monkeypatch.setattr(direct_setup, "release_from_astrbot", lambda h, spec: released.append(spec.kind) or True)
    check("exit 0", sw.connect_main(["telegram", "--telegram-token", "t"]) == 0)
    check("released once", released == ["telegram"])
    check("said so", "also connected through AstrBot" in capsys.readouterr().out)


# ---- sign-in by code or link

def test_wechat_shows_a_code_and_saves_what_the_scan_returns(home, monkeypatch, capsys) -> None:
    platform = stand_in(monkeypatch)
    monkeypatch.setattr(direct, "sign_in_for", flow("https://liteapp.example/qr?k=1", {"token": "w"}))
    direct.state_path(home, "weixin_oc").parent.mkdir(parents=True)
    direct.state_path(home, "weixin_oc").write_text("{}", encoding="utf-8")
    check("exit 0", sw.connect_main(["wechat", "--no-input"]) == 0)
    out = capsys.readouterr().out
    check("the code is drawn", "█" in out or "▀" in out or "▄" in out, out[:400])
    check("its address is printed", "https://liteapp.example/qr?k=1" in out)
    check("the window is named as the alternative, with its command",
          "personagent window" in out and any(line.rstrip().endswith(" start") for line in out.splitlines()), out)
    check("a scan is saved without a second check, as on the page", platform.checked == [])
    check("saved", saved(home) == {"weixin_oc": {"token": "w"}})
    check("the old login's state is gone", not direct.state_path(home, "weixin_oc").exists())


def test_twitch_prints_the_link_and_code_then_checks_the_tokens(home, monkeypatch, capsys) -> None:
    platform = stand_in(monkeypatch)
    link = "https://www.twitch.tv/activate?public=true&device-code=ABCDEFGH"
    monkeypatch.setattr(direct, "sign_in_for", flow(link, {"twitch_access_token": "a",
                                                           "twitch_refresh_token": "r"}))
    code = sw.connect_main(["twitch", "--twitch-client-id", "cid", "--twitch-channels", "nova"])
    out = capsys.readouterr().out
    check("exit 0", code == 0, out)
    check("the link", link in out)
    check("the code", "Code: ABCDEFGH" in out, out)
    check("how to stop", "Ctrl+C" in out)
    values = {"twitch_client_id": "cid", "twitch_channels": "nova", "twitch_access_token": "a",
              "twitch_refresh_token": "r"}
    check("the tokens are checked", platform.checked == [("twitch", values)], str(platform.checked))
    check("saved", saved(home) == {"twitch": values})


def test_a_declined_sign_in_is_reported_and_nothing_saved(home, monkeypatch, capsys) -> None:
    stand_in(monkeypatch)

    class Declined(Exception):
        pass

    async def scan(client, show, given):
        show("https://www.twitch.tv/activate")
        raise Declined("denied")
    monkeypatch.setattr(direct, "sign_in_for", lambda kind: (scan, Declined))
    code = sw.connect_main(["twitch", "--twitch-client-id", "cid", "--twitch-channels", "nova"])
    err = capsys.readouterr().err
    check("non-zero", code == 1)
    check("Twitch's own sentence", "The Twitch sign-in did not finish" in err, err)
    check("nothing saved", saved(home) == {})


def test_ctrl_c_while_waiting_stops_cleanly(home, monkeypatch, capsys) -> None:
    stand_in(monkeypatch)
    monkeypatch.setattr(direct, "sign_in_for", flow("https://liteapp.example/qr", error=KeyboardInterrupt()))
    code = sw.connect_main(["wechat"])
    captured = capsys.readouterr()
    check("exit 130", code == 130, str(code))
    check("said so", "Stopped. Nothing was saved." in captured.out, captured.out)
    check("no traceback", "Traceback" not in captured.err)
    check("nothing saved", saved(home) == {})


# ---- disconnecting

def test_remove_disconnects_as_the_page_does(home, monkeypatch, capsys) -> None:
    direct_base.save_credentials(home, "telegram", {"telegram_token": "t"})
    direct_base.save_credentials(home, "discord", {"discord_token": "d"})
    direct.state_path(home, "telegram").parent.mkdir(parents=True)
    direct.state_path(home, "telegram").write_text("{}", encoding="utf-8")
    check("exit 0", sw.connect_main(["telegram", "--remove"]) == 0)
    out = capsys.readouterr().out
    check("said so", "Telegram is disconnected" in out, out)
    check("only telegram is gone", saved(home) == {"discord": {"discord_token": "d"}})
    check("its state too", not direct.state_path(home, "telegram").exists())


def test_remove_of_something_not_connected_changes_nothing(home, capsys) -> None:
    check("exit 0", sw.connect_main(["vk", "--remove"]) == 0)
    check("said so", "VK is not connected. Nothing was changed." in capsys.readouterr().out)
    check("no file written", not direct_base.credentials_path(home).exists())


# ---- the menu and the first run lead here

def test_the_menu_offers_every_direct_platform(monkeypatch, capsys) -> None:
    answers = iter(["4"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    check("the fourth is discord", sw.choose_platform() == ["connect", "discord"])
    out = capsys.readouterr().out
    for kind in direct.KINDS:
        check(f"{kind} offered", conn.platform(kind).name[0] in out, out)
    check("astrbot still offered", "through AstrBot" in out)


def test_the_menu_can_go_back_or_to_astrbot(monkeypatch) -> None:
    answers = iter(["0", str(len(direct.KINDS) + 1)])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    check("back", sw.choose_platform() == [])
    check("astrbot", sw.choose_platform() == ["connect", "astrbot"])
