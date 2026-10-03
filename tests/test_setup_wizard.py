"""`personagent init` / `connect`: the questions, the files they write, the key probe."""
from __future__ import annotations

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

ROOT = Path(__file__).resolve().parents[1]


def check(name: str, cond, detail: str = "") -> None:
    assert cond, name + (f" - {detail}" if detail else "")


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
          keys == ["deepseek", "siliconflow", "bailian", "zhipu", "moonshot", "ark",
                   "openrouter", "openai", "gemini", "ollama", "other"], repr(keys))
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


# ---------------------------------------------------------------------------
# .env.example
# ---------------------------------------------------------------------------

def test_the_env_template_reads_top_down() -> None:
    from dotenv import dotenv_values

    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    values = dotenv_values(ROOT / ".env.example")
    keys = list(values)
    check("template: the required settings come first",
          keys[:5] == ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "PERSONA_NAME", "AGENT_LANG"],
          repr(keys[:5]))
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
    check("template: the default endpoint is the code's",
          (values["LLM_BASE_URL"], values["LLM_MODEL"])
          == (DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL))
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
    thread = threading.Thread(target=server.serve_forever, daemon=True)
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
          (get("LLM_BASE_URL"), get("LLM_MODEL")) == ("https://api.deepseek.com", "deepseek-flash"))
    check("first run: key, name and language", (get("LLM_API_KEY"), get("PERSONA_NAME"),
                                                 get("AGENT_LANG")) == ("sk-test-1234567890", "Mira", "en"))
    persona = (tmp_path / "persona.txt").read_text(encoding="utf-8")
    check("first run: the chosen character, named", persona.startswith("Your name is Mira.")
          and "gamer" in persona, persona)
    check("first run: the key was tested", ("probe", "https://api.deepseek.com",
                                            "sk-test-1234567890", "deepseek-flash") in calls)
    check("first run: the key is never printed", "sk-test-1234567890" not in out
          and not any("sk-test-1234567890" in p for p in script.prompts))
    check("first run: titled for a first run", "First-time setup" in out)
    check("first run: where the key comes from", "platform.deepseek.com/api_keys" in out)
    check("first run: the chat is handed over",
          any(c[0] == "chat" and c[1][-1] == "chat" for c in calls), repr(calls))
    check("first run: eight questions to a terminal chat", len(script.prompts) == 8,
          "\n".join(script.prompts))
    check("first run: no English-only jargon left",
          "OpenAI-compatible" not in "".join(script.prompts))


def test_a_first_run_in_chinese_asks_in_chinese(monkeypatch, tmp_path, capsys) -> None:
    script = Script([("Choose / 选择", "2"), ("选择服务", "4"), ("API key", "sk-zh-1234567890"),
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
          "HTTP 401" in out and sw.completions_url("https://api.deepseek.com") in out, out)
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


def test_a_piped_stdin_says_the_questions_were_skipped(monkeypatch, tmp_path, capsys) -> None:
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
                    "some-model", "sk-test-123456"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    current = dict.fromkeys(("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"), "")
    values = sw.step_model(current)
    check("asked again until the address has a scheme",
          values["LLM_BASE_URL"] == "https://api.example.com", repr(values))
    with pytest.raises(SystemExit):
        sw.main(["--no-input", "--provider", "other", "--base-url", "api.example.com"])
