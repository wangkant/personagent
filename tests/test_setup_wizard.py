"""`personagent init` / `connect`: the questions, the files they write, the key probe."""
from __future__ import annotations

import builtins
import contextlib
import hashlib
import io
import json
import re
import string
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from persona_agent import home as homes
from persona_agent import setup_wizard as sw
from persona_agent.config_env import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL
from persona_agent.prompts import _TEMPLATE_RULE_RE

from helpers import check

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _english_by_default():
    sw.set_lang("en")
    yield
    sw.set_lang("en")


class Script:
    """Answers prompts by the first matching substring; records every prompt."""

    def __init__(self, answers: list[tuple[str, str]], limit: int = 80) -> None:
        self.answers = answers
        self.prompts: list[str] = []
        self.limit = limit

    def __call__(self, prompt: str = "") -> str:
        self.prompts.append(prompt)
        assert len(self.prompts) < self.limit, "kept re-asking: " + prompt
        for needle, answer in self.answers:
            if needle in prompt:
                return answer
        return ""


def _wire(monkeypatch, script: Script, probe_ok: bool = True) -> list:
    """Scripted input, a canned key probe, and no real chat hand-off."""
    calls: list = []
    monkeypatch.setattr("builtins.input", script)
    monkeypatch.setattr(sw, "probe_key", lambda base, key, model, timeout=30: (
        calls.append(("probe", base, key, model))
        or sw.Probe(sw.completions_url(base), 200 if probe_ok else 401, "")))
    monkeypatch.setattr(sw.subprocess, "call", lambda argv, **kw: calls.append(("chat", argv)) or 0)
    monkeypatch.setattr(sw, "find_astrbot_data", lambda: None)
    return calls


def _launcher(home: Path) -> sw.Launcher:
    return sw.Launcher(python="python", home=home)


FAN_MADE = ("chatgpt", "deepseek", "claude")


@pytest.fixture
def portraits(monkeypatch, tmp_path_factory) -> Path:
    """Portrait sprites for the fan-made characters, never the package's own folder."""
    folder = tmp_path_factory.mktemp("portraits")
    for key in FAN_MADE:
        (folder / f"{key}.webp").write_bytes(b"RIFF\x04\x00\x00\x00WEBP")
    monkeypatch.setattr(sw, "PORTRAITS", folder)
    return folder


# ---------------------------------------------------------------------------
# Text, language, providers
# ---------------------------------------------------------------------------

def test_every_message_exists_in_both_languages_with_the_same_fields() -> None:
    fields = string.Formatter()
    for key, (en, zh) in sw._TEXT.items():
        check(f"text {key}: both languages written", en.strip() and zh.strip())
        en_fields = {f for _, f, _, _ in fields.parse(en) if f}
        zh_fields = {f for _, f, _, _ in fields.parse(zh) if f}
        check(f"text {key}: the same placeholders", en_fields == zh_fields,
              repr((en_fields, zh_fields)))
        if key not in ("yes_no", "no_yes"):
            check(f"text {key}: the Chinese is Chinese", re.search(r"[一-鿿]", zh), zh)


def test_the_system_language_picks_the_default(monkeypatch) -> None:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LANG", "zh_CN.UTF-8")
    check("locale: zh_CN is Chinese", sw.detect_lang() == "zh")
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    check("locale: en_US is English", sw.detect_lang() == "en")
    check("locale: Windows' own name for Chinese",
          sw._lang_of("Chinese (Simplified)_China") == "zh")
    check("locale: C.UTF-8 says nothing", sw._lang_of("C.UTF-8") == "")


def test_the_providers_are_complete() -> None:
    keys = [p.key for p in sw.PROVIDERS]
    check("providers: the eleven choices, Other last",
          keys == ["openrouter", "deepseek", "siliconflow", "bailian", "zhipu", "moonshot", "ark",
                   "openai", "gemini", "ollama", "other"], repr(keys))
    for p in sw.PROVIDERS[:-1]:
        check(f"{p.key}: https or a local address",
              p.base_url.startswith("https://") or p.key == "ollama", p.base_url)
        check(f"{p.key}: a default model", p.model)
        check(f"{p.key}: says where keys come from", p.key_url or not p.needs_key)
        check(f"{p.key}: found again from its base URL", sw.provider_for_base(p.base_url) is p)
    check("providers: a root written without /v1 is still recognised",
          sw.provider_for_base("https://api.openai.com/").key == "openai")
    deepseek = sw.provider_named("deepseek")
    check("providers: the DeepSeek preset is the code's default endpoint",
          (deepseek.base_url, deepseek.model) == (DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL))


# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------

def test_every_character_ships_in_both_languages_ready_to_use() -> None:
    for lang in sw.LANGS:
        for character in sw.CHARACTERS:
            source = sw.persona_source(character.key, lang)
            check(f"persona {lang}/{character.key}: shipped", source.is_file(), str(source))
            raw = source.read_text(encoding="utf-8")
            text = sw.persona_text(character.key, name="Mika", lang=lang)
            check(f"persona {lang}/{character.key}: no placeholders left", "{" not in text, text)
            check(f"persona {lang}/{character.key}: no alternatives to pick from",
                  not re.search(r"\b(e\.g\.|or:)|比如：|或者：", raw), raw)
            check(f"persona {lang}/{character.key}: no notes to the reader",
                  not _TEMPLATE_RULE_RE.search(raw) and "persona.txt" not in raw, raw)
            check(f"persona {lang}/{character.key}: names the character", "Mika" in text, text)
            check(f"persona {lang}/{character.key}: short", len(text) < 1200, str(len(text)))
    shipped = {p.stem for p in (ROOT / "data" / "personas" / "en").glob("*.txt")}
    check("persona: every shipped file is on the menu",
          shipped == set(sw.PERSONA_KEYS) - {sw.TEMPLATE}, repr(shipped))


def test_a_template_is_filled_and_its_notes_dropped() -> None:
    template = ("You're {bot_name}.\n"
                "- The person you're closest to is {admin_name} ({admin_relationship}).\n"
                "- Everyone else: read the room\n\n————\n"
                "This is the persona template. Copy it to persona.txt.")
    alone = sw.render_persona(template, name="Nova", lang="en")
    check("render: name filled", alone.startswith("You're Nova."), alone)
    check("render: no admin, no admin line", "closest" not in alone, alone)
    check("render: the note is gone", "template" not in alone, alone)
    with_admin = sw.render_persona(template, name="Nova", lang="en", admin_name="Kay")
    check("render: an admin without a relationship has no empty brackets",
          "closest to is Kay." in with_admin, with_admin)
    related = sw.render_persona(template, name="Nova", lang="en", admin_name="Kay",
                                admin_relationship="sister")
    check("render: relationship filled", "Kay (sister)" in related, related)
    zh = sw.render_persona("- 你最熟的人是 {admin_name}（{admin_relationship}）。\n其他", name="小夏",
                           lang="zh", admin_name="小林")
    check("render: Chinese brackets dropped too", "小林。" in zh and "（" not in zh, zh)
    check("render: a text that never names the character gets a name line",
          zh.startswith("你叫小夏。"), zh)


def test_only_an_unedited_shipped_persona_is_offered_for_replacement(monkeypatch) -> None:
    for lang in sw.LANGS:
        for character in sw.CHARACTERS:
            text = sw.persona_text(character.key, name="Mika", lang=lang)
            check(f"origin {lang}/{character.key}: recognised with its name",
                  sw.shipped_persona(text) == (character.key, lang, "Mika"),
                  repr(sw.shipped_persona(text)))
            check(f"origin {lang}/{character.key}: CRLF does not count as an edit",
                  sw.shipped_persona(text.replace("\n", "\r\n")) is not None)
            check(f"origin {lang}/{character.key}: an edit is the user's",
                  sw.shipped_persona(text + "Loves jazz.\n") is None)
    raw = sw.persona_source(sw.TEMPLATE, "en").read_text(encoding="utf-8")
    check("origin: the raw template copied as is",
          sw.shipped_persona(raw) == (sw.TEMPLATE, "en", ""))
    old = "You're {bot_name}, an earlier template.\n"
    monkeypatch.setattr(sw, "_LEGACY_PERSONA_SHA256", frozenset(
        {hashlib.sha256(old.strip().encode()).hexdigest()}))
    check("origin: an earlier release's template", sw.shipped_persona(old)[0] == "legacy")
    check("origin: an earlier template defaults to the plain character",
          sw.default_character(("legacy", "", "")) == sw.TEMPLATE)


def test_the_fan_made_characters_come_last_with_their_own_names(portraits) -> None:
    check("menu: the three after the original four, the template last",
          sw.PERSONA_KEYS == ("dry-wit", "warm-listener", "gamer", "bookworm", *FAN_MADE, sw.TEMPLATE),
          repr(sw.PERSONA_KEYS))
    check("menu: only they have names of their own",
          [c.name for c in sw.CHARACTERS if c.name] == ["ChatGPT", "DeepSeek", "Claude"])
    check("name: the default follows the character", sw.name_for("claude", "Nova", "en") == "Claude")
    check("name: the language's default too", sw.name_for("deepseek", "小夏", "zh") == "DeepSeek")
    check("name: another character's own name follows", sw.name_for("claude", "ChatGPT", "en") == "Claude")
    check("name: a chosen name stays", sw.name_for("claude", "Mira", "en") == "Mira")
    check("name: a character without one keeps the name", sw.name_for("gamer", "Nova", "en") == "Nova")
    check("name: leaving a fan-made character goes back to the default, as on the page",
          sw.name_for("gamer", "Claude", "en") == "Nova")
    check("portrait: the fan-made ones", [k for k in sw.PERSONA_KEYS if sw.portrait(k)] == list(FAN_MADE))
    check("portrait: none for a name that is not a character",
          sw.portrait("../portraits/claude") is None and sw.avatar_for("gamer") == "")
    (portraits / "claude.webp").unlink()
    check("portrait: a missing file means none", sw.avatar_for("claude") == "")


# ---------------------------------------------------------------------------
# .env.example
# ---------------------------------------------------------------------------

def test_the_env_template_reads_top_down() -> None:
    from dotenv import dotenv_values

    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    values = dotenv_values(ROOT / ".env.example")
    keys = list(values)
    check("template: the settings the page fills in come first",
          keys[:6] == ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "PERSONA_NAME", "PERSONA_AVATAR",
                       "AGENT_LANG"],
          repr(keys[:6]))
    check("template: the QQ / OneBot block comes last",
          all(k.startswith("QQ_") for k in keys[-5:]), repr(keys[-5:]))
    inline = [line for line in text.splitlines()
              if not line.lstrip().startswith("#") and re.search(r"\s#", line)]
    check("template: every comment is on its own line", not inline, repr(inline))
    check("template: nothing parses as a comment's words",
          not [k for k, v in values.items() if v and v.lstrip().startswith("#")])
    check("template: no NapCat address unless you run one", values["QQ_ONEBOT_URL"] == "")
    check("template: the time zone defaults to this machine",
          values["PERSONA_TZ_OFFSET_HOURS"] == "")
    check("template: the default endpoint is the first preset's",
          (values["LLM_BASE_URL"], values["LLM_MODEL"])
          == (sw.PROVIDERS[0].base_url, sw.PROVIDERS[0].model))
    check("template: present tense, no release history",
          not re.search(r"\b(since|in|until) 0\.\d|before it existed|as they were|used to\b",
                        text))


# ---------------------------------------------------------------------------
# The key probe
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def fake_openai(statuses: list[int], seen: list):
    """A local OpenAI-compatible endpoint answering with `statuses` in turn."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - http.server's naming
            length = int(self.headers.get("Content-Length") or 0)
            seen.append((self.path, self.headers.get("Authorization"),
                         json.loads(self.rfile.read(length) or b"{}")))
            status = statuses.pop(0) if statuses else 200
            body = (b'{"choices":[{"message":{"content":"OK"}}]}' if status == 200
                    else b'{"error":{"message":"Unsupported parameter: max_tokens"}}'
                    if status == 400 else b'{"error":{"message":"nope"}}')
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


def test_the_probe_calls_the_agents_url_and_explains_a_failure() -> None:
    seen: list = []
    with fake_openai([200], seen) as base:
        probe = sw.probe_key(base, "sk-test", "fake-model", timeout=5)
    check("probe: OK on 200", probe.ok, repr(probe))
    check("probe: the URL the agent posts to", probe.url == base + "/v1/chat/completions"
          and seen[0][0] == "/v1/chat/completions", repr((probe.url, seen)))
    check("probe: the key as a bearer token", seen[0][1] == "Bearer sk-test")
    check("probe: one token asked for", seen[0][2]["max_tokens"] == 1, repr(seen[0][2]))

    seen.clear()
    with fake_openai([400, 200], seen) as base:
        probe = sw.probe_key(base, "sk-test", "reasoner", timeout=5)
    check("probe: a model refusing max_tokens is asked again without it",
          probe.ok and len(seen) == 2 and "max_tokens" not in seen[1][2], repr(seen))

    with fake_openai([401], []) as base:
        probe = sw.probe_key(base, "sk-bad", "m", timeout=5)
    deepseek = sw.provider_named("deepseek")
    check("probe: 401 reported", probe.status == 401, repr(probe))
    check("probe: 401 points at the key page",
          deepseek.key_url in sw.explain_probe(probe, deepseek))
    for status, needle in ((402, "balance"), (404, "Base URL"), (429, "minute"), (503, "error")):
        check(f"probe: {status} has a likely fix",
              needle in sw.explain_probe(sw.Probe("u", status), deepseek))
    dead = sw.probe_key("http://127.0.0.1:9", "k", "m", timeout=3)
    text = sw.explain_probe(dead, sw.provider_named("ollama"))
    check("probe: nothing listening is named, with the Ollama hint",
          dead.status == 0 and "127.0.0.1" in text and "ollama serve" in text, text)


# ---------------------------------------------------------------------------
# The questions
# ---------------------------------------------------------------------------

def test_a_first_run_in_english(monkeypatch, tmp_path, capsys) -> None:
    script = Script([("Choose / 选择", "1"), ("Service", "1"),
                     ("API key", "sk-test-1234567890"), ("Bot name", "Mira"),
                     ("Character", "3"), ("Connect to AstrBot", "n"),
                     ("Chat with the bot", "y")])
    calls = _wire(monkeypatch, script)
    sw.run_wizard(tmp_path, _launcher(tmp_path))
    out = capsys.readouterr().out
    get = lambda key: sw.env_get(tmp_path / ".env", key)  # noqa: E731
    check("first run: the preset's endpoint and model",
          (get("LLM_BASE_URL"), get("LLM_MODEL")) == ("https://openrouter.ai/api/v1", "openrouter/free"))
    check("first run: key, name and language", (get("LLM_API_KEY"), get("PERSONA_NAME"),
                                                 get("AGENT_LANG")) == ("sk-test-1234567890", "Mira", "en"))
    persona = (tmp_path / "persona.txt").read_text(encoding="utf-8")
    check("first run: the chosen character, named", persona.startswith("Your name is Mira.")
          and "gamer" in persona, persona)
    check("first run: the key was tested", ("probe", "https://openrouter.ai/api/v1",
                                            "sk-test-1234567890", "openrouter/free") in calls)
    check("first run: the key is never printed", "sk-test-1234567890" not in out
          and not any("sk-test-1234567890" in p for p in script.prompts))
    check("first run: titled for a first run", "First-time setup" in out)
    check("first run: where the key comes from", "openrouter.ai/keys" in out)
    check("first run: the chat is handed over",
          any(c[0] == "chat" and c[1][-1] == "chat" for c in calls), repr(calls))
    check("first run: nine questions including key visibility", len(script.prompts) == 9,
          "\n".join(script.prompts))
    check("first run: no English-only jargon left",
          "OpenAI-compatible" not in "".join(script.prompts))


def test_a_first_run_in_chinese_asks_in_chinese(monkeypatch, tmp_path, capsys) -> None:
    script = Script([("Choose / 选择", "2"), ("选择服务", "5"), ("API key", "sk-zh-1234567890"),
                     ("[Y/n]", "n"), ("[y/N]", "n")])
    _wire(monkeypatch, script)
    sw.run_wizard(tmp_path, _launcher(tmp_path))
    out = capsys.readouterr().out
    after_language = script.prompts[1:]
    check("zh: every later question is in Chinese",
          all(re.search(r"[一-鿿]", p) for p in after_language), "\n".join(after_language))
    check("zh: Zhipu's documented base URL",
          sw.env_get(tmp_path / ".env", "LLM_BASE_URL") == "https://open.bigmodel.cn/api/paas/v4")
    check("zh: the Chinese default name", sw.env_get(tmp_path / ".env", "PERSONA_NAME") == "小夏")
    check("zh: the Chinese character", (tmp_path / "persona.txt").read_text(
        encoding="utf-8").startswith("你叫小夏。"))
    check("zh: the output is Chinese too", "设置完成" in out and "首次设置" in out)


def test_a_failed_probe_offers_another_try(monkeypatch, tmp_path, capsys) -> None:
    outcomes = [401, 200]
    script = Script([("Choose / 选择", "1"), ("Service", "1"), ("Base URL", ""),
                     ("API key", "sk-wrong-1234567"), ("try again", "y"),
                     ("[Y/n]", "n"), ("[y/N]", "n")])
    _wire(monkeypatch, script)
    keys: list = []

    def probe(base, key, model, timeout=30):
        keys.append(key)
        return sw.Probe(sw.completions_url(base), outcomes.pop(0))

    monkeypatch.setattr(sw, "probe_key", probe)
    sw.run_wizard(tmp_path, _launcher(tmp_path))
    out = capsys.readouterr().out
    check("retry: the failure is explained with the URL called",
          "HTTP 401" in out and sw.completions_url("https://openrouter.ai/api/v1") in out, out)
    check("retry: the Base URL is offered on the second pass",
          sum("Base URL" in p for p in script.prompts) == 1, "\n".join(script.prompts))
    check("retry: tried twice", len(keys) == 2, repr(keys))


def test_rerunning_the_wizard_keeps_the_current_setup(monkeypatch, tmp_path, capsys) -> None:
    """Enter-through on a re-run keeps every answer, including the key."""
    env = tmp_path / ".env"
    env.write_text(
        "LLM_API_KEY=sk-test-abcd\nLLM_BASE_URL=https://api.openai.com/\n"
        "LLM_MODEL=gpt-6-luna\nPERSONA_NAME=Mika\nAGENT_LANG=zh\n", encoding="utf-8")
    script = Script([("[Y/n]", "n"), ("[y/N]", "n")])
    _wire(monkeypatch, script)
    sw.run_wizard(tmp_path, _launcher(tmp_path))

    get = lambda key: sw.env_get(env, key)  # noqa: E731
    check("rerun: provider kept", get("LLM_BASE_URL").rstrip("/") == "https://api.openai.com",
          get("LLM_BASE_URL"))
    check("rerun: model kept", get("LLM_MODEL") == "gpt-6-luna", get("LLM_MODEL"))
    check("rerun: key kept", get("LLM_API_KEY") == "sk-test-abcd", get("LLM_API_KEY"))
    check("rerun: name kept", get("PERSONA_NAME") == "Mika", get("PERSONA_NAME"))
    check("rerun: language kept", get("AGENT_LANG") == "zh", get("AGENT_LANG"))
    shown = "\n".join(script.prompts) + capsys.readouterr().out
    check("rerun: titled Reconfigure", "重新配置" in shown)
    check("rerun: the key is never printed", "sk-test-abcd" not in shown, shown)
    check("rerun: the key is shown masked", "sk-…abcd" in shown, shown)


def test_an_edited_persona_is_left_alone(monkeypatch, tmp_path, capsys) -> None:
    (tmp_path / "persona.txt").write_text("My own character.\n", encoding="utf-8")
    script = Script([("Choose / 选择", "1"), ("API key", "sk-test-1234567890"),
                     ("[Y/n]", "n"), ("[y/N]", "n")])
    _wire(monkeypatch, script)
    sw.run_wizard(tmp_path, _launcher(tmp_path))
    check("persona: an edited file is kept",
          (tmp_path / "persona.txt").read_text(encoding="utf-8") == "My own character.\n")
    check("persona: no character menu for it",
          not any("Character" in p for p in script.prompts), "\n".join(script.prompts))


def test_the_wizard_rerun_keeps_the_astrbot_setup(monkeypatch, tmp_path) -> None:
    data = tmp_path / "astrbot" / "data"
    (data / "plugins").mkdir(parents=True)
    (data / "cmd_config.json").write_text("{}", encoding="utf-8")
    sw.write_astrbot_config(data, {
        "excluded_platforms": [], "groups": ["123", "456"], "dm_users": ["789"]})
    env = tmp_path / ".env"
    env.write_text("LLM_API_KEY=sk-test-abcd\nLLM_BASE_URL=https://api.openai.com/\n"
                   "LLM_MODEL=gpt-6-luna\nPERSONA_NAME=Mika\nAGENT_LANG=en\nQQ_BOT_ID=10001\n"
                   "CONNECTOR_QQ_PLATFORMS=aiocqhttp\nADMIN_IDS=42,telegram:7\nADMIN_NAME=Kay\n"
                   "ACCESS_GROUPS=telegram:-100,qq:999\n", encoding="utf-8")
    script = Script([("Connect to AstrBot", "y"), ("AstrBot folder", str(data.parent)),
                     ("[Y/n]", "n"), ("[y/N]", "n")])
    _wire(monkeypatch, script)
    with contextlib.redirect_stdout(io.StringIO()):
        sw.run_wizard(tmp_path, _launcher(tmp_path))

    cfg = sw.read_astrbot_config(data)
    check("astrbot rerun: groups kept", cfg["groups"] == ["123", "456"], repr(cfg))
    check("astrbot rerun: DMs kept, and the admin may DM", cfg["dm_users"] == ["789", "42"],
          repr(cfg))
    check("astrbot rerun: QQ kept", cfg["excluded_platforms"] == [], repr(cfg))
    got = {k: sw.env_get(env, k) for k in ("ACCESS_GROUPS", "ADMIN_IDS", "ADMIN_NAME", "QQ_BOT_ID")}
    check("astrbot rerun: QQ entries follow the kept groups, other platforms' stay",
          got["ACCESS_GROUPS"] == "telegram:-100,123,456", repr(got))
    check("astrbot rerun: the admin on every platform is kept",
          got["ADMIN_IDS"] == "telegram:7,42" and got["ADMIN_NAME"] == "Kay", repr(got))
    check("astrbot rerun: the QQ number kept", got["QQ_BOT_ID"] == "10001")
    check("astrbot rerun: the platform defaults to the routed one",
          any("Chat app [1]" in p for p in script.prompts), "\n".join(script.prompts))

    # With QQ off, Enter on the platform keeps it off.
    cfg["excluded_platforms"] = ["aiocqhttp"]
    sw.write_astrbot_config(data, cfg)
    sw.write_env(env, {"CONNECTOR_QQ_PLATFORMS": ""})
    with contextlib.redirect_stdout(io.StringIO()):
        sw.run_wizard(tmp_path, _launcher(tmp_path))
    check("astrbot rerun: QQ stays off",
          sw.read_astrbot_config(data)["excluded_platforms"] == ["aiocqhttp"])


def test_a_first_astrbot_connection_for_telegram(monkeypatch, tmp_path, capsys) -> None:
    """QQ is not the default, its questions are not asked, and the
    admin's id is written the way the agent spells Telegram ids."""
    data = tmp_path / "astrbot" / "data"
    (data / "plugins").mkdir(parents=True)
    (data / "cmd_config.json").write_text('{"platform": []}', encoding="utf-8")
    script = Script([("Choose / 选择", "1"), ("API key", "sk-test-1234567890"),
                     ("Connect to AstrBot", "y"), ("AstrBot folder", str(data)),
                     ("Chat app", "2"), ("Telegram bot token", "123:tok"),
                     ("Group ids", "-1001"), ("user id on Telegram", "555"),
                     ("call you", "Kay"), ("[Y/n]", "n"), ("[y/N]", "n")])
    _wire(monkeypatch, script)
    sw.run_wizard(tmp_path, _launcher(tmp_path))
    out = capsys.readouterr().out
    prompts = "\n".join(script.prompts)
    check("telegram: the platform had no default", any(p.rstrip().endswith("Chat app:")
                                                       for p in script.prompts), prompts)
    check("telegram: no QQ questions", "QQ number" not in prompts, prompts)
    check("telegram: the token was read hidden-style and not echoed", "123:tok" not in out)
    env = tmp_path / ".env"
    check("telegram: the admin as telegram:<id>", sw.env_get(env, "ADMIN_IDS") == "telegram:555")
    cfg = sw.read_astrbot_config(data)
    check("telegram: QQ stays excluded", cfg["excluded_platforms"] == ["aiocqhttp"], repr(cfg))
    check("telegram: plugin allowlists", cfg["groups"] == ["-1001"]
          and cfg["dm_users"] == ["555"], repr(cfg))
    platforms = json.loads((data / "cmd_config.json").read_text(encoding="utf-8"))["platform"]
    check("telegram: the adapter is switched on",
          platforms and platforms[0]["telegram_token"] == "123:tok", repr(platforms))
    check("telegram: the next steps say how to start the service",
          re.search(r"(-m persona_agent|personagent) .* run\s*$", out, re.MULTILINE), out)


def test_astrbot_in_docker_gets_the_fix_instead_of_a_refused_url(monkeypatch, tmp_path, capsys) -> None:
    root = tmp_path / "astrbot"
    data = root / "data"
    (data / "plugins").mkdir(parents=True)
    (data / "cmd_config.json").write_text("{}", encoding="utf-8")
    (root / "compose.yml").write_text("services: {}\n", encoding="utf-8")
    check("docker: a compose file beside the data folder is noticed", sw.astrbot_in_docker(data))
    script = Script([("Choose / 选择", "1"), ("API key", "sk-test-1234567890"),
                     ("Connect to AstrBot", "y"), ("AstrBot folder", str(root)),
                     ("HTTPS address", "http://host.docker.internal:8080"),
                     ("Chat app", "7"), ("[Y/n]", "n"), ("[y/N]", "n")])
    answers = iter(["http://host.docker.internal:8080", "https://agent.example.com"])
    script.answers.insert(0, ("HTTPS address", ""))
    real = script.__call__

    def call(prompt: str = "") -> str:
        if "HTTPS address" in prompt:
            script.prompts.append(prompt)
            return next(answers)
        if "Docker" in prompt:
            script.prompts.append(prompt)
            return ""            # Enter: the noticed compose file makes Yes the default
        return real(prompt)

    _wire(monkeypatch, script)
    monkeypatch.setattr("builtins.input", call)
    sw.run_wizard(tmp_path, _launcher(tmp_path))
    out = capsys.readouterr().out
    check("docker: the host-networking fix is printed", "network_mode: host" in out, out)
    check("docker: a plain-http address is refused", "only accepts" in out, out)
    cfg = sw.read_astrbot_config(data)
    check("docker: the HTTPS address is written",
          cfg["personagent_url"] == "https://agent.example.com", repr(cfg))


def test_no_input_writes_the_flags_and_asks_nothing(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("MY_KEY", "sk-from-env-123456")
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("asked a question"))
    sw.main(["--no-input", "--provider", "siliconflow", "--key-env", "MY_KEY",
             "--name", "Mika", "--lang", "en", "--persona", "bookworm"])
    env = tmp_path / ".env"
    get = lambda key: sw.env_get(env, key)  # noqa: E731
    check("no-input: the preset", (get("LLM_BASE_URL"), get("LLM_MODEL"))
          == ("https://api.siliconflow.cn/v1", "deepseek-ai/DeepSeek-V3.2"))
    check("no-input: the key from the named variable", get("LLM_API_KEY") == "sk-from-env-123456")
    check("no-input: name and language", (get("PERSONA_NAME"), get("AGENT_LANG")) == ("Mika", "en"))
    persona = (tmp_path / "persona.txt").read_text(encoding="utf-8")
    check("no-input: the chosen character", persona.startswith("Your name is Mika.")
          and "reader" in persona, persona)
    out = capsys.readouterr().out
    check("no-input: the key is not printed", "sk-from-env" not in out, out)

    sw.main(["--no-input", "--name", "Juno"])
    persona = (tmp_path / "persona.txt").read_text(encoding="utf-8")
    check("no-input: an unedited character follows a new name",
          persona.startswith("Your name is Juno.") and "reader" in persona, persona)
    (tmp_path / "persona.txt").write_text("Mine.\n", encoding="utf-8")
    sw.main(["--no-input", "--persona", "gamer"])
    check("no-input: an edited persona is never replaced",
          (tmp_path / "persona.txt").read_text(encoding="utf-8") == "Mine.\n")
    with pytest.raises(SystemExit):
        sw.main(["--no-input", "--key-env", "NO_SUCH_VARIABLE_SET"])
    with pytest.raises(SystemExit):
        sw.main(["--no-input", "--provider", "other"])


def _name_and_avatar(home: Path) -> tuple[str, str]:
    return sw.env_get(home / ".env", "PERSONA_NAME"), sw.env_get(home / ".env", "PERSONA_AVATAR")


def test_the_wizard_names_a_fan_made_character_after_itself(monkeypatch, tmp_path, portraits,
                                                            capsys) -> None:
    claude = str(sw.PERSONA_KEYS.index("claude") + 1)
    gamer = str(sw.PERSONA_KEYS.index("gamer") + 1)
    answers = [("Choose / 选择", "1"), ("Service", "1"), ("API key", "sk-test-1234567890"),
               ("[Y/n]", "n"), ("[y/N]", "n")]
    _wire(monkeypatch, Script([("Character", claude), *answers]))
    sw.run_wizard(tmp_path, _launcher(tmp_path))
    check("wizard: Enter on the default name takes the character's own",
          _name_and_avatar(tmp_path) == ("Claude", "claude"), repr(_name_and_avatar(tmp_path)))
    check("wizard: the persona carries it",
          (tmp_path / "persona.txt").read_text(encoding="utf-8").startswith("Your name is Claude."))
    check("wizard: says why the name changed", "the name follows the character: Claude"
          in capsys.readouterr().out)

    _wire(monkeypatch, Script([("Bot name", "Mira"), ("Character", claude), *answers]))
    sw.run_wizard(tmp_path, _launcher(tmp_path))
    check("wizard: a typed name stays", _name_and_avatar(tmp_path) == ("Mira", "claude"))

    _wire(monkeypatch, Script([("Character", gamer), *answers]))
    sw.run_wizard(tmp_path, _launcher(tmp_path))
    check("wizard: the saved name stays, and no portrait without one",
          _name_and_avatar(tmp_path) == ("Mira", ""))


def test_no_input_names_a_fan_made_character_unless_a_name_is_given(monkeypatch, tmp_path,
                                                                      portraits) -> None:
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("asked a question"))
    # A key in the environment would need --provider; this test is about names.
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    first, second = tmp_path / "first", tmp_path / "second"
    monkeypatch.setenv("AGENT_HOME", str(first))
    sw.main(["--no-input", "--lang", "en", "--persona", "deepseek"])
    check("no-input: no name given or saved takes the character's own",
          _name_and_avatar(first) == ("DeepSeek", "deepseek"), repr(_name_and_avatar(first)))
    check("no-input: the persona carries it",
          (first / "persona.txt").read_text(encoding="utf-8").startswith("Your name is DeepSeek."))
    sw.main(["--no-input", "--persona", "claude"])
    check("no-input: a name that was only the last character's own follows the new one",
          _name_and_avatar(first) == ("Claude", "claude"), repr(_name_and_avatar(first)))
    sw.main(["--no-input", "--persona", "gamer"])
    check("no-input: and goes back to the default for one without a name",
          _name_and_avatar(first) == ("Nova", ""), repr(_name_and_avatar(first)))

    monkeypatch.setenv("AGENT_HOME", str(second))
    sw.main(["--no-input", "--lang", "en", "--persona", "chatgpt", "--name", "Mika"])
    check("no-input: --name wins", _name_and_avatar(second) == ("Mika", "chatgpt"))
    sw.main(["--no-input", "--persona", "bookworm"])
    check("no-input: a character without a portrait clears it", _name_and_avatar(second) == ("Mika", ""))
    sw.main(["--no-input", "--persona", "claude"])
    check("no-input: the saved name wins", _name_and_avatar(second) == ("Mika", "claude"))
    (second / "persona.txt").write_text("Mine.\n", encoding="utf-8")
    sw.main(["--no-input", "--persona", "gamer"])
    check("no-input: an edited persona keeps its portrait", _name_and_avatar(second)[1] == "claude")


def test_a_piped_stdin_says_the_questions_were_skipped(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO("1\n1\nsk-x\n"))
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("asked a question"))
    sw.main(["--lang", "en"])
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if "skipped" in line]
    check("piped: one line says why the questions were skipped",
          len(lines) == 1 and "not a terminal" in lines[0], out)
    check("piped: the home is still set up", (tmp_path / ".env").is_file()
          and (tmp_path / "persona.txt").is_file())
    check("piped: the missing key is the next step", "LLM_API_KEY" in out, out)


def test_connect_from_flags(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    data = tmp_path / "astrbot" / "data"
    (data / "plugins").mkdir(parents=True)
    (data / "cmd_config.json").write_text("{}", encoding="utf-8")
    sw.connect_main(["astrbot", str(data.parent), "--qq", "--url", "https://agent.example.com"])
    cfg = sw.read_astrbot_config(data)
    env = tmp_path / "home" / ".env"
    check("connect: plugin installed", (data / "plugins" / sw.PLUGIN_NAME / "main.py").is_file())
    check("connect: token shared", cfg["connector_token"] == sw.env_get(env, "CONNECTOR_TOKEN") != "")
    check("connect: the given URL", cfg["personagent_url"] == "https://agent.example.com")
    check("connect: QQ routed", sw.env_get(env, "CONNECTOR_QQ_PLATFORMS") == "aiocqhttp")
    out = capsys.readouterr().out
    check("connect: says the allowlists are empty", "forwards no group" in out, out)
    for bad in (["astrbot", str(tmp_path / "nowhere")],
                ["astrbot", str(data), "--url", "http://10.0.0.2:8080"],
                ["astrbot", "--qq"]):
        with pytest.raises(SystemExit):
            sw.connect_main(bad)


def test_astrbot_is_found_where_it_keeps_its_data(monkeypatch, tmp_path) -> None:
    root = tmp_path / "custom"
    (root / "data").mkdir(parents=True)
    (root / "data" / "cmd_config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv(sw.ASTRBOT_ROOT_VAR, str(root))
    check("find: ASTRBOT_ROOT", sw.find_astrbot_data() == root / "data")
    monkeypatch.delenv(sw.ASTRBOT_ROOT_VAR)
    monkeypatch.setattr(sw.Path, "home", classmethod(lambda cls: tmp_path))
    desktop = tmp_path / ".astrbot" / "data"
    desktop.mkdir(parents=True)
    (desktop / "cmd_config.json").write_text("{}", encoding="utf-8")
    check("find: the desktop app's ~/.astrbot", sw.find_astrbot_data() == desktop)
    check("resolve: the folder above an AstrBot checkout",
          sw.resolve_astrbot_data(tmp_path / "nothing") is None)


def test_the_next_steps_fit_this_machine(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AGENT_HOME", raising=False)
    launcher = sw.Launcher(python=str(homes.CHECKOUT / ".venv" / "Scripts" / "python.exe"),
                           home=homes.CHECKOUT)
    if homes.is_checkout():
        lines = launcher.shown("run")
        check("checkout: from the checkout, with its .venv python",
              lines[0].startswith("cd ") and lines[1].endswith("-m persona_agent run")
              and not Path(lines[1].split(" -m")[0]).is_absolute(), repr(lines))
        check("checkout: the chat runs from the checkout", launcher.cwd() == str(homes.CHECKOUT))
    elsewhere = sw.Launcher(python=launcher.python, home=tmp_path)
    monkeypatch.delenv("AGENT_HOME", raising=False)
    check("a home that a bare command would not find is named, set or not",
          "--home" in " ".join(elsewhere.shown("chat")))
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    check("--home is carried into the commands", "--home" in " ".join(elsewhere.shown("chat"))
          and elsewhere.argv("chat")[-3:] == ["--home", str(tmp_path), "chat"])


def test_uvx_is_named_whatever_the_cache_folder(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AGENT_HOME", raising=False)
    monkeypatch.setattr(homes, "is_checkout", lambda path=None: False)
    monkeypatch.setattr(homes, "default_home", lambda: tmp_path)
    launcher = sw.Launcher(python="python", home=tmp_path)
    for prefix in ("C:/Users/a/AppData/Local/uv/cache/archive-v0/abc",
                   "D:/claude/uvcache/archive-v0/abc", "/home/a/.cache/uv/archive-v0/x"):
        monkeypatch.setattr(sw.sys, "prefix", prefix)
        check(f"uvx from {prefix}", launcher.shown("demo") == ["uvx personagent demo"],
              repr(launcher.shown("demo")))


def test_a_base_url_without_its_scheme_is_asked_again(monkeypatch) -> None:
    answers = iter([str(len(sw.PROVIDERS)), "api.example.com", "https://api.example.com",
                    "some-model", "n", "sk-test-123456"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    current = dict.fromkeys(("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"), "")
    values = sw.step_model(current)
    check("asked again until the address has a scheme",
          values["LLM_BASE_URL"] == "https://api.example.com", repr(values))
    with pytest.raises(SystemExit):
        sw.main(["--no-input", "--provider", "other", "--base-url", "api.example.com"])


# ---------------------------------------------------------------------------
# Flags typed at a terminal
# ---------------------------------------------------------------------------

@pytest.fixture
def at_a_terminal(monkeypatch, tmp_path) -> Path:
    """`init` run by a person: a terminal on stdin, and a home of its own."""
    monkeypatch.setattr(sw.langs, "interactive", lambda: True)
    # At a terminal a key is read hidden; the script answers that too.
    monkeypatch.setattr(sw.getpass, "getpass", lambda prompt="": builtins.input(prompt))
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    return tmp_path


def _asked(script: Script, *needles: str) -> list[str]:
    return [p for p in script.prompts if any(n in p for n in needles)]


def test_flags_at_a_terminal_answer_their_questions(monkeypatch, at_a_terminal, capsys) -> None:
    home = at_a_terminal
    monkeypatch.setenv("MY_KEY", "sk-from-env-123456")
    script = Script([("Connect to AstrBot", "n"), ("Chat with the bot", "n")])
    calls = _wire(monkeypatch, script)
    code = sw.main(["--provider", "siliconflow", "--key-env", "MY_KEY", "--name", "Mika",
                    "--lang", "en", "--persona", "bookworm"])
    out = capsys.readouterr().out
    get = lambda key: sw.env_get(home / ".env", key)  # noqa: E731
    check("flags: the wizard finished", code == 0)
    check("flags: --provider chose the service",
          (get("LLM_BASE_URL"), get("LLM_MODEL"))
          == ("https://api.siliconflow.cn/v1", "deepseek-ai/DeepSeek-V3.2"))
    check("flags: --key-env gave the key, and it was tested",
          get("LLM_API_KEY") == "sk-from-env-123456"
          and ("probe", "https://api.siliconflow.cn/v1", "sk-from-env-123456",
               "deepseek-ai/DeepSeek-V3.2") in calls, repr(calls))
    check("flags: --name and --lang", (get("PERSONA_NAME"), get("AGENT_LANG")) == ("Mika", "en"))
    persona = (home / "persona.txt").read_text(encoding="utf-8")
    check("flags: --persona chose the character",
          persona.startswith("Your name is Mika.") and "reader" in persona, persona)
    answered = _asked(script, "Choose / 选择", "Service", "API key", "Bot name", "Character")
    check("flags: no question a flag answered is asked", not answered, "\n".join(script.prompts))
    check("flags: the model, which no flag gave, is still asked",
          len(_asked(script, "Model")) == 1, "\n".join(script.prompts))
    for flag in ("--provider", "--key-env MY_KEY", "--name", "--lang", "--persona"):
        check(f"flags: says what {flag} answered", f"({flag})" in out, out)
    check("flags: the answers themselves are shown",
          all(said in out for said in ("SiliconFlow", "Mika", "English", "Bookworm", "sk-…3456")), out)
    check("flags: the key is never printed", "sk-from-env-123456" not in out)


def test_an_address_flag_names_the_service_and_a_typed_name_stays(monkeypatch, at_a_terminal,
                                                                    capsys) -> None:
    home = at_a_terminal
    script = Script([("Choose / 选择", "1"), ("API key (paste", "sk-test-1234567890"),
                     ("Connect to AstrBot", "n"), ("Chat with the bot", "n")])
    calls = _wire(monkeypatch, script)
    sw.main(["--base-url", "https://llm.example.com/v1", "--model", "my-model",
             "--name", "Nova", "--persona", "claude"])
    out = capsys.readouterr().out
    check("flags: --base-url and --model reach the probe and the file",
          ("probe", "https://llm.example.com/v1", "sk-test-1234567890", "my-model") in calls
          and sw.env_get(home / ".env", "LLM_MODEL") == "my-model", repr(calls))
    check("flags: neither the service, the address nor the model is asked",
          not _asked(script, "Service", "Base URL", "Model"), "\n".join(script.prompts))
    check("flags: what they answered is shown",
          "(--base-url)" in out and "my-model (--model)" in out, out)
    check("flags: the questions no flag answered are asked",
          len(_asked(script, "Choose / 选择")) == 1 and len(_asked(script, "API key (paste")) == 1,
          "\n".join(script.prompts))
    check("flags: a name given as a flag does not follow the character",
          sw.env_get(home / ".env", "PERSONA_NAME") == "Nova"
          and (home / "persona.txt").read_text(encoding="utf-8").startswith("Your name is Nova."))


def test_a_failed_probe_asks_again_with_the_flags_as_defaults(monkeypatch, at_a_terminal) -> None:
    home = at_a_terminal
    monkeypatch.setenv("MY_KEY", "sk-wrong-12345678")
    outcomes = [401, 200]
    script = Script([("Choose / 选择", "1"), ("try again", "y"), ("Enter keeps", "sk-right-12345678"),
                     ("Connect to AstrBot", "n"), ("Chat with the bot", "n")])
    _wire(monkeypatch, script)
    keys: list = []

    def probe(base, key, model, timeout=30):
        keys.append((base, key))
        return sw.Probe(sw.completions_url(base), outcomes.pop(0))

    monkeypatch.setattr(sw, "probe_key", probe)
    with contextlib.redirect_stdout(io.StringIO()):
        sw.main(["--provider", "deepseek", "--key-env", "MY_KEY"])
    deepseek = sw.PROVIDER_KEYS.index("deepseek") + 1
    check("retry: the flag's service is the default of the question now asked",
          _asked(script, "Service") == [f"  Service [{deepseek}]: "], "\n".join(script.prompts))
    check("retry: the flag's key was tried, then the typed one",
          keys == [("https://api.deepseek.com", "sk-wrong-12345678"),
                   ("https://api.deepseek.com", "sk-right-12345678")], repr(keys))
    check("retry: the typed key is the one saved",
          sw.env_get(home / ".env", "LLM_API_KEY") == "sk-right-12345678")


def test_a_language_flag_wins_over_the_saved_language(monkeypatch, at_a_terminal, capsys) -> None:
    home = at_a_terminal
    (home / ".env").write_text(
        "LLM_API_KEY=sk-test-abcd\nLLM_BASE_URL=https://api.openai.com/v1\n"
        "LLM_MODEL=gpt-6-luna\nPERSONA_NAME=Mika\nAGENT_LANG=zh\n", encoding="utf-8")
    (home / "persona.txt").write_text("My own character.\n", encoding="utf-8")
    script = Script([("[Y/n]", "n"), ("[y/N]", "n")])
    _wire(monkeypatch, script)
    sw.main(["--lang", "en", "--persona", "gamer"])
    out = capsys.readouterr().out
    check("rerun: --lang replaces the saved language",
          sw.env_get(home / ".env", "AGENT_LANG") == "en" and "Reconfigure" in out, out)
    check("rerun: the language is not asked", not _asked(script, "Choose / 选择"))
    check("rerun: an edited persona.txt is kept, and --persona is told why",
          (home / "persona.txt").read_text(encoding="utf-8") == "My own character.\n"
          and "left as it is" in out, out)


@pytest.mark.parametrize("flags, why", [
    (["--key-env", "NO_SUCH_VARIABLE_SET"], "that environment variable is empty"),
    (["--provider", "other", "--base-url", "llm.example.com"], "--base-url needs https://")])
def test_a_flag_that_cannot_be_used_stops_before_the_first_question(monkeypatch, at_a_terminal,
                                                                     flags, why) -> None:
    monkeypatch.setenv("AGENT_LANG", "en")
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("asked a question"))
    with pytest.raises(SystemExit) as stop:
        sw.main(flags)
    check("refused in words", why in str(stop.value.code), repr(stop.value.code))
    check("nothing was written", not (at_a_terminal / ".env").exists())


# ---------------------------------------------------------------------------
# One place for each shared answer
# ---------------------------------------------------------------------------

def test_uvx_is_recognised_in_one_place(monkeypatch, tmp_path) -> None:
    from persona_agent import coding, updates

    monkeypatch.delenv("AGENT_HOME", raising=False)
    monkeypatch.setattr(homes, "is_checkout", lambda path=None: False)
    monkeypatch.setattr(homes, "default_home", lambda: tmp_path)
    launcher = sw.Launcher(python="python", home=tmp_path)
    # A folder that merely starts with "archive-v" is not uv's cache.
    monkeypatch.setattr(sw.sys, "prefix", str(tmp_path / "Archive-Videos" / ".venv"))
    check("a look-alike folder: not uvx in the next steps",
          not launcher.shown("demo")[0].startswith("uvx"), repr(launcher.shown("demo")))
    check("a look-alike folder: not uvx for the coding agents", coding._launcher()[0] != "uvx")
    monkeypatch.setattr(sw.sys, "prefix", "/home/a/.cache/uv/archive-v0/x")
    check("uv's cache: uvx for the coding agents", coding._launcher() == ["uvx", "personagent"])

    monkeypatch.setattr(sw.sys, "prefix", str(tmp_path))
    monkeypatch.setattr(sw.langs, "under_uvx", lambda: True)
    check("the next steps ask it", launcher.shown("demo") == ["uvx personagent demo"])
    check("the coding agents' launcher asks it", coding._launcher() == ["uvx", "personagent"])
    check("the update notice asks it", updates.how_to_update() == ("uvx personagent@latest", True))


def test_terminal_columns_are_counted_in_one_place(monkeypatch, capsys) -> None:
    from persona_agent import chat, doctor

    check("CJK takes two columns", sw.langs.width("中a文") == 5 and sw.langs.width("abc") == 3)
    monkeypatch.setattr(sw.langs, "width", lambda text: 2)
    check("doctor's table asks it", doctor._pad("中文字", 5) == "中文字" + " " * 3)
    sw._header("中文字")
    check("the wizard's headers ask it", capsys.readouterr().out == "\n-- 中文字 " + "-" * 58 + "\n")

    class Session:
        t = {"commands": [("/命令", "does it")], "memory_hint": "memory"}
        name, lang = "Nova", "en"

    chat.ChatSession.commands(Session())
    check("the trial's command list asks it",
          capsys.readouterr().out == "\n  /命令" + " " * 14 + "does it\n  memory\n\n")


#: What each adapter's fields were asked as before connections.py named them.
ADAPTER_PROMPTS = {
    "qq_official": {"appid": "QQ bot AppID", "secret": "QQ bot AppSecret"},
    "telegram": {"telegram_token": "Telegram bot token (from @BotFather)"},
    "discord": {"discord_token": "Discord bot token (Developer Portal > Bot)"},
    "slack": {"bot_token": "Slack bot token (xoxb-...)",
              "app_token": "Slack app-level token (xapp-..., Socket Mode)"},
    "kook": {"kook_bot_token": "KOOK bot token"},
    "lark": {"app_id": "Lark / Feishu app id", "app_secret": "Lark / Feishu app secret"},
}
ADAPTER_LABELS = {"qq_official": ("QQ official bot", "QQ 官方机器人"),
                  "telegram": ("Telegram", "Telegram"), "discord": ("Discord", "Discord"),
                  "slack": ("Slack", "Slack"), "kook": ("KOOK", "KOOK"),
                  "lark": ("Lark / Feishu", "Lark / Feishu")}


def test_the_astrbot_adapters_are_described_once() -> None:
    import inspect

    from persona_agent import connections as conn

    check("the same six adapters", list(sw.PLATFORMS) == list(ADAPTER_PROMPTS))
    for kind, fields in sw.PLATFORMS.items():
        spec = conn.platform(kind)
        check(f"{kind}: its fields are the catalog's, in the catalog's order",
              [key for key, _ in fields] == [f.key for f in spec.fields])
        check(f"{kind}: each field is asked as before",
              {key: prompt[0] for key, prompt in fields} == ADAPTER_PROMPTS[kind], repr(fields))
        for lang, label in zip(("en", "zh"), ADAPTER_LABELS[kind]):
            sw.set_lang(lang)
            check(f"{kind}: named as before in {lang}", sw.platform_label(kind) == label,
                  sw.platform_label(kind))
        check(f"{kind}: what is typed hidden is the catalog's decision too",
              {f.key: f.secret for f in spec.fields}
              == {key: "token" in key or "secret" in key for key, _ in fields})
    check("no second table of names", not hasattr(sw, "PLATFORM_LABELS"))
    # --token and its siblings map onto the keys once; nothing else spells them.
    source = inspect.getsource(sw)
    for key in sorted({key for fields in ADAPTER_PROMPTS.values() for key in fields}):
        check(f"the wizard spells {key} once", source.count(f'"{key}"') == 1,
              str(source.count(f'"{key}"')))


def test_the_console_is_prepared_once_by_the_command(monkeypatch, tmp_path) -> None:
    from persona_agent import cli

    class Stream(io.StringIO):
        def __init__(self) -> None:
            super().__init__()
            self.reconfigured: list[dict] = []

        def reconfigure(self, **how) -> None:
            self.reconfigured.append(how)

    out, err = Stream(), Stream()
    monkeypatch.setattr("sys.stdout", out)
    monkeypatch.setattr("sys.stderr", err)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    code = cli.main(["init", "--no-input", "--lang", "en"])
    check("init ran", code == 0 and (tmp_path / ".env").is_file(), out.getvalue())
    once = [{"encoding": "utf-8", "errors": "replace"}]
    check("the command prepares each stream, and init does not repeat it",
          out.reconfigured == once and err.reconfigured == once,
          repr((out.reconfigured, err.reconfigured)))
