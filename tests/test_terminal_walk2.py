"""What the second terminal walk found: `up` on a damaged memory file, doctor's
learning rows and unreachable services, the platform menu, `--help`."""
from __future__ import annotations

import builtins
import socket
from pathlib import Path

import pytest

from persona_agent import cli, doctor, health, langs, paths, services
from persona_agent import setup_wizard as sw

from helpers import check


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".env").write_text("LLM_API_KEY=sk-test-walk2\n", encoding="utf-8")
    (tmp_path / "runtime").mkdir()
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    for name in ("MEMORY_FILE", "AGENT_RUNTIME_DIR"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


# ---- up on a damaged memory file

def _no_start(monkeypatch) -> None:
    def refuse(*a, **k):
        raise AssertionError("nothing may start")
    monkeypatch.setattr(services, "Services", refuse)
    monkeypatch.setattr(services, "stop_leftovers", refuse)


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_up_on_a_damaged_memory_file_gives_the_sentence(home, monkeypatch, capsys, lang) -> None:
    monkeypatch.setenv("AGENT_LANG", lang)
    memory = home / "runtime" / "memory.json"
    memory.write_text('{"broken', encoding="utf-8")
    _no_start(monkeypatch)
    check("refused, non-zero", services.main([]) == 1)
    err = capsys.readouterr().err.strip()
    want = {"en": f"The memory file {memory} is damaged and was left untouched, and no "
                  "earlier copy of it exists. Move the damaged file aside, for example by "
                  "renaming it, to start with an empty memory.",
            "zh": f"记忆文件 {memory} 已损坏，未作任何改动，且不存在更早的副本。"
                  "请将损坏文件移至别处（例如将其重命名），以空白记忆启动。"}[lang]
    check(f"{lang}: the same sentence the other commands give", err == want, err)
    check("the file is left as it was", memory.read_text(encoding="utf-8") == '{"broken')


def test_up_names_the_daily_copy_and_a_damaged_core_file(home, monkeypatch, capsys) -> None:
    core = home / "runtime" / "core_memory.json"
    core.write_text("[1]", encoding="utf-8")
    (home / "runtime" / "core_memory.json.bak").write_text("{}", encoding="utf-8")
    _no_start(monkeypatch)
    check("refused", services.main([]) == 1)
    err = capsys.readouterr().err
    check("the file, its copy, both ways forward",
          f"The memory file {core} is damaged" in err and f"{core}.bak" in err
          and "start with an empty memory" in err, err)


def test_up_translates_why_a_service_did_not_start(home, monkeypatch, capsys) -> None:
    monkeypatch.setenv("AGENT_LANG", "zh")

    class Failing:
        def __init__(self, home):
            pass

        def start_agent(self):
            raise RuntimeError("agent could not start; see runtime/desktop/agent.log")

        def close(self):
            pass
    monkeypatch.setattr(services, "Services", Failing)
    monkeypatch.setattr(services, "stop_leftovers", lambda home: [])
    monkeypatch.setattr("persona_agent.updates.refresh_soon", lambda home: None)
    monkeypatch.setattr(services, "write_env", lambda *a, **k: None)
    check("non-zero", services.main([]) == 1)
    err = capsys.readouterr().err.strip()
    check("in the terminal's language", err == "agent 未能启动；详情请查看 runtime/desktop/agent.log。", err)


def test_the_trial_names_its_own_damaged_file(home, monkeypatch, capsys) -> None:
    from persona_agent import chat

    trial = home / "runtime" / chat.TRIAL_DIR
    trial.mkdir()
    (trial / "memory.json").write_text('{"broken', encoding="utf-8")
    (home / "runtime" / "memory.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as stop:
        chat.build_agent("en", 1)
    err = capsys.readouterr().err.strip()
    check("refused", stop.value.code == 1)
    check("the trial's file, the live memory untouched, the folder to delete",
          err == f"The practice chat's memory file {trial / 'memory.json'} is damaged; the "
                 "memory the character uses in its chats is not affected. Delete the folder "
                 f"{trial} to start the practice chat with an empty memory.", err)


# ---- doctor: the models the character learns with

class Probe:
    def __init__(self, fail: set[str] | None = None) -> None:
        self.asked: list[str] = []
        self.fail = fail or set()

    def __call__(self, url, payload, headers, timeout=30):
        self.asked.append(payload["model"])
        if payload["model"] in self.fail:
            raise health.Unreachable(url, ConnectionRefusedError(10061, "refused"))
        message = {"content": "ok"}
        if payload.get("tools"):
            message["tool_calls"] = [{"function": {"name": "web_search"}}]
        return {"choices": [{"message": message}]}


@pytest.fixture
def models(monkeypatch) -> Probe:
    for name in ("LLM_DM_MODEL", "LLM_JUDGE_MODEL", "LLM_FALLBACK_MODEL", "REACT_MODEL",
                 "PROMOTE_JUDGE_MODEL", "EVOLVE_MODEL", "EVAL_MODEL", "EVAL_ENABLED",
                 "VISION_MODEL", "EMBEDDING_MODEL", "TAVILY_API_KEY", "QQ_BOT_ID",
                 "PROMOTE_JUDGE_ENABLED", "PROMOTE_AUTO_ENABLED", "REACT_LEARN_ENABLED",
                 "EVOLVE_AUTO_ENABLED"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_API_KEY", "sk-test-walk2")
    monkeypatch.setenv("LLM_BASE_URL", "https://models.example/v1")
    monkeypatch.setenv("LLM_MODEL", "main-m")
    probe = Probe()
    monkeypatch.setattr(health, "_post_json", probe)
    monkeypatch.setattr(health, "check_ledger_sizes", lambda: (True, "no ledgers yet"))
    return probe


def _rows() -> dict:
    return {r["name"]: r for r in health.run_checks()}


def test_doctor_probes_the_decision_and_evolve_models_once_each(models, monkeypatch) -> None:
    monkeypatch.setenv("PROMOTE_JUDGE_MODEL", "judge-x")
    monkeypatch.setenv("EVOLVE_AUTO_ENABLED", "true")
    monkeypatch.setenv("EVOLVE_MODEL", "evo-x")
    rows = _rows()
    check("a row for the character's decisions",
          rows["Learning decisions"]["ok"] is True
          and "judge-x" in rows["Learning decisions"]["detail"], str(rows["Learning decisions"]))
    check("a row for its review of its own replies",
          rows["Reviewing its own replies"]["ok"] is True
          and "evo-x" in rows["Reviewing its own replies"]["detail"])
    check("each asked once", models.asked.count("judge-x") == 1
          and models.asked.count("evo-x") == 1, str(models.asked))


def test_doctor_does_not_ask_a_model_twice(models, monkeypatch) -> None:
    monkeypatch.setenv("EVOLVE_AUTO_ENABLED", "true")
    rows = _rows()
    decisions, evolve = rows["Learning decisions"], rows["Reviewing its own replies"]
    check("the same model as an earlier row: its answer, no call of its own",
          decisions["ok"] is True and decisions["detail"]
          == "main-m: the same model as the row DM chat, so it is not asked again",
          str(decisions))
    check("the evolve model too", evolve["ok"] is True
          and "the same model as the row DM chat" in evolve["detail"], str(evolve))
    check("main-m: the rows that asked it before; the learning rows add no call",
          models.asked.count("main-m") == 4, str(models.asked))
    monkeypatch.setenv("PROMOTE_JUDGE_MODEL", "judge-x")
    monkeypatch.setenv("EVOLVE_MODEL", "judge-x")
    models.asked.clear()
    rows = _rows()
    check("evolve on the decisions model is not asked again",
          models.asked.count("judge-x") == 1
          and "the same model as the row Learning decisions"
          in rows["Reviewing its own replies"]["detail"], str(models.asked))


def test_doctor_learning_rows_follow_their_switches(models, monkeypatch) -> None:
    monkeypatch.setenv("PROMOTE_JUDGE_ENABLED", "false")
    rows = _rows()
    check("off: not probed", rows["Learning decisions"]["ok"] is None
          and rows["Learning decisions"]["detail"] == "turned off"
          and rows["Reviewing its own replies"]["detail"] == "turned off")


def test_doctor_learning_rows_in_chinese(models, monkeypatch, capsys) -> None:
    monkeypatch.setenv("AGENT_LANG", "zh")
    monkeypatch.setattr(doctor, "check_config", lambda: [])
    doctor.main([])
    out = capsys.readouterr().out
    check("zh: the row and the same-model sentence",
          "学习决定" in out and "main-m：与「私聊模型」一行为同一模型，因此不再重复询问" in out, out)


# ---- doctor: a service that cannot be reached

def _closed_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_an_unreachable_model_reads_as_a_sentence(monkeypatch, capsys) -> None:
    port = _closed_port()
    monkeypatch.setenv("LLM_API_KEY", "sk-test-walk2")
    monkeypatch.setenv("LLM_BASE_URL", f"http://127.0.0.1:{port}/v1")
    monkeypatch.setenv("LLM_MODEL", "main-m")
    monkeypatch.delenv("LLM_DM_MODEL", raising=False)
    monkeypatch.setattr(health, "CHECKS", [("DM chat", health.check_dm_chat, True)])
    row = health.run_checks()[0]
    want = (f"Could not connect to 127.0.0.1:{port}. Check LLM_BASE_URL in .env, that the "
            "service is running, and that the network or proxy lets the connection through.")
    check("refused: what to check", row["ok"] is False and row.get("advice") == want, str(row))
    check("the raw cause stays for the page", "URLError" in row["detail"], row["detail"])
    monkeypatch.setattr(doctor, "check_config", lambda: [])
    monkeypatch.setattr(doctor, "run_checks", lambda: [row])
    for lang, sentence in (("en", want),
                           ("zh", f"无法连接到 127.0.0.1:{port}。请检查 .env 中的 LLM_BASE_URL、"
                                  "该服务是否正在运行，以及网络或代理是否允许连接。")):
        monkeypatch.setenv("AGENT_LANG", lang)
        check("doctor still fails", doctor.main([]) == 1)
        out = capsys.readouterr().out
        check(f"{lang}: the sentence, not the Python error", sentence in out
              and "WinError" not in out and "Errno" not in out, out)


def test_http_failures_say_what_to_check() -> None:
    import urllib.error

    def http(code: int) -> str:
        return health.failure_sentence(urllib.error.HTTPError(
            "https://api.example.com/v1/chat/completions", code, "x", {}, None))
    check("401", http(401) == "api.example.com refused the key (HTTP 401). "
                              "Check the key for this service in .env.")
    check("404", http(404).startswith("api.example.com answered HTTP 404."))
    check("429", "quota" in http(429))
    check("500", http(500).startswith("api.example.com answered with an error (HTTP 500)."))
    timeout = health.Unreachable("https://api.example.com/v1", TimeoutError("timed out"))
    check("a timeout", health.failure_sentence(timeout).startswith(
        "api.example.com did not answer in time."))
    check("anything else keeps the raw detail", health.failure_sentence(KeyError("x")) == "")


# ---- start --terminal: the platform menu

def test_the_platform_menu_says_why_it_asks_again(monkeypatch, capsys) -> None:
    answers = iter(["99", "x", "0"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(answers))
    for lang, said in (("en", '"99" is not one of the options. Enter a number from 0 to '),
                       ("zh", "「99」不是可选项。请输入 0 至 ")):
        answers = iter(["99", "x", "0"])
        monkeypatch.setattr(builtins, "input", lambda prompt="": next(answers))
        sw.set_lang(lang)
        check("back with 0", sw.choose_platform() == [])
        out = capsys.readouterr().out
        check(f"{lang}: each invalid answer is named", said in out and out.count("99") == 1
              and ("x" in out), out)
    sw.set_lang("en")


# ---- --help

def test_help_names_memory_among_what_eval_measures(capsys) -> None:
    check("exit 0", cli.main([]) == 0)
    out = capsys.readouterr().out
    check("eval: speaking, persona, learning and memory",
          "Measure speaking, persona, learning and memory on labelled cases" in out, out)


def test_a_slot_value_named_to_keep_is_not_translated(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_LANG", "ru")
    check("a sentence in a slot is translated", langs.term("Chat: reply") == "Чат: ответ")
    check("a kept value stays as given", langs.term("Chat: reply", keep=("reply",)) == "Чат: reply")
