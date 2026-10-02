"""`personagent demo`: three scripted scenes through the real decision,
ledger and promotion code, leaving nothing behind."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

import httpx
import pytest

from persona_agent import chat, demo, paths, reactions
from persona_agent.textproc import TextProcessing


@pytest.fixture(autouse=True)
def plain_hints(monkeypatch):
    """Commands spelled the same on every machine."""
    def spelled(sub, lang="en"):
        return f"`personagent {sub}`"
    monkeypatch.setattr(chat, "hint", spelled)
    monkeypatch.setattr(demo, "hint", spelled)


@pytest.fixture(autouse=True)
def daytime(monkeypatch):
    """No sleep window: the pacing rule reads the wall clock."""
    monkeypatch.setattr(TextProcessing, "_is_sleep_hour", staticmethod(lambda: False))


async def play(tmp: Path, scenes, lang: str = "en") -> str:
    lines: list[str] = []
    await demo.run(scenes, lang=lang, offline=True, out=lines.append, base=str(tmp))
    assert list(tmp.iterdir()) == [], "the demo left files behind"
    return "\n".join(lines)


async def test_quiet_scene_says_why_for_every_line(tmp: Path) -> None:
    out = await play(tmp, ["quiet"])
    assert "scripted model, real ledger and promotion code" in out
    assert out.count("(quiet: not addressed,") == 3
    assert "(quiet: not addressed, 3 of 4 messages)" in out
    assert "(joins in: 4 of 4 messages, and the gate model said speak)" in out
    assert "  Nova: the final? count me in, I'll bring snacks" in out
    assert "(named, so it answers)" in out
    assert out.count("but the gate model said stay quiet)") == 2


@pytest.mark.parametrize("lang", ["en", "zh"])
async def test_teach_scene_promotes_the_accepted_retry(tmp: Path, lang: str) -> None:
    out = await play(tmp, ["teach"], lang)
    if lang == "en":
        assert "judged: rejection, accepted" in out
        assert "Nova's next reply to Alex counts as its second try" in out
        assert "ledger: Alex accepted the second try: strong" in out
        assert ('3. Alex accepted the second try "fair. that\'s a rough end to '
                'the day" - strong') in out
        assert out.count("now in use: 2 agreeing reactions, 1 strong, same chat") == 1
        assert "[x] 2 of 2 agreeing reactions" in out
        assert "learned in its prompt: 1 fix from this chat" in out
        assert out.rstrip().splitlines()[-3].strip() == (
            "Nova would say: ugh, mid-demo? that's brutal")
    else:
        assert "判定：否定，采信" in out
        assert "账本：小林接受了第二次尝试：强" in out
        assert "已生效：2 条证据，1 条强证据，同一个聊天" in out
        assert "提示词里的学习结果：这个聊天里学到的 1 条改写" in out
        assert "小夏会说：啊，演示到一半？太惨了" in out


@pytest.mark.parametrize("lang", ["en", "zh"])
async def test_troll_scene_changes_nothing(tmp: Path, lang: str) -> None:
    out = await play(tmp, ["troll"], lang)
    if lang == "en":
        assert out.count("judged: correction, dismissed") == 2
        assert ("even if accepted it could not count: the reply was for Alex,\n"
                "      so Mallory's correction is negative only") in out
        assert "memory: nothing saved; notes keep facts, not instructions" in out
        assert ("ledger: 2 reactions recorded, 2 dismissed; 0 proposals proposed, "
                "0 in use.\n  Nothing Nova says has changed.") in out
    else:
        assert out.count("判定：纠正，不采信") == 2
        assert "那条回复是对小林说的，阿强的纠正只算仅否定" in out
        assert "记忆：没有保存；笔记只记事实，不记指令" in out
        assert "0 条提议，0 条生效。\n  小夏的说话方式没有任何改变。" in out


async def test_every_scene_runs_in_chinese(tmp: Path) -> None:
    out = await play(tmp, demo.SCENES, "zh")
    assert "脚本模型，真实的账本和晋升代码" in out
    assert "（没说话：没被点名，1/4 条消息）" in out
    assert "（插话：攒够 4/4 条消息，判断模型认为该开口）" in out
    assert out.rstrip().endswith("先运行 `personagent init`）。")


async def test_the_demo_restores_what_it_borrowed(tmp: Path) -> None:
    root, env = paths.ROOT, dict(os.environ)
    logger = logging.getLogger("agent")
    level = logger.level
    await play(tmp, ["troll"])
    assert paths.ROOT == root
    assert dict(os.environ) == env
    assert logger.level == level


async def test_the_scripted_model_answers_by_kind() -> None:
    model = demo.ScriptedModel()
    model.load(demo.Beat("x", "", gate=True, reply=lambda system: system.upper(),
                         verdict={"reaction": "positive", "accept": True}))
    gate = json.loads(await model("sys", [{"role": "user", "content": "chat"}],
                                  disable_thinking=True, temperature=0.3))
    reply = json.loads(await model("hello", [{"role": "user", "content": "chat"}],
                                   plain_text_fallback=True))
    judge_prompt = reactions.build_adjudicator_prompt(
        {"reply": "r"}, "no", "Alex", False, "Nova", "en")
    verdict = json.loads(await model("", [{"role": "user", "content": judge_prompt}]))
    assert (gate["reply"], reply["reply"], verdict["reaction"]) == ("ok", "HELLO", "positive")
    assert model.calls == ["gate", "reply", "judge"]
    # Empty queues give the cautious answers.
    assert json.loads(await model("", [{"role": "user", "content": "x"}],
                                  disable_thinking=True, temperature=0.3))["reply"] == "PASS"
    assert json.loads(await model("", [{"role": "user", "content": judge_prompt}])
                      )["accept"] is False


def test_main_runs_offline_without_a_key(tmp: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_HOME", str(tmp / "home"))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    assert demo.main(["quiet", "--lang", "en"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("personagent demo: scripted model, real ledger and promotion code")
    assert "== quiet:" in out and "== teach:" not in out
    assert list(tmp.iterdir()) == []


# -- findings from the review of the demo --------------------------------------

def _http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://api.example.test/v1/chat/completions")
    response = httpx.Response(status, request=request, text="nope")
    return httpx.HTTPStatusError(f"Client error '{status}'", request=request,
                                 response=response)


def _failing(monkeypatch, exc) -> None:
    """Make the demo's model raise `exc` on every call, as an online run would."""
    real = demo.build_agent

    def build(lang, root, *, offline):
        agent, _model = real(lang, root, offline=True)

        async def fail(*args, **kwargs):
            raise exc
        agent._call_llm = fail
        return agent, None
    monkeypatch.setattr(demo, "build_agent", build)


@pytest.mark.parametrize("scene", ["quiet", "teach"])
async def test_an_online_model_failure_stops_the_demo(
        tmp: Path, monkeypatch, scene: str) -> None:
    _failing(monkeypatch, _http_error(401))
    lines: list[str] = []
    code = await demo.run([scene], lang="en", offline=False, out=lines.append,
                          base=str(tmp))
    out = "\n".join(lines)
    assert code == 1
    assert "costs\ntokens" in out
    assert "The demo stopped: the model did not answer. the model provider refused the key" in out
    assert "Try it with your own model" not in out and "(quiet: model error" not in out
    assert list(tmp.iterdir()) == []


async def test_the_demo_ignores_the_real_persona_card(
        tmp: Path, monkeypatch) -> None:
    from persona_agent import agent as agent_module
    real_home = tmp / "real"
    real_home.mkdir()
    (real_home / "persona.card.json").write_text(
        json.dumps({"reply_style": {"max_chars": 20}}), encoding="utf-8")
    (real_home / "persona.txt").write_text("You are somebody else.", encoding="utf-8")
    monkeypatch.setattr(agent_module, "ROOT", real_home)
    monkeypatch.setenv("PERSONA_CARD_FILE", "persona.card.json")
    monkeypatch.setenv("PERSONA_FILE", "persona.txt")
    work = tmp / "work"
    work.mkdir()
    out = await play(work, ["teach"])
    assert "did you check the logs? roll back first, then diff the configs" in out
    assert agent_module.ROOT == real_home
    assert os.environ["PERSONA_CARD_FILE"] == "persona.card.json"


async def test_the_scripted_demo_does_not_depend_on_the_hour(
        tmp: Path, monkeypatch) -> None:
    day = await play(tmp, demo.SCENES)
    monkeypatch.setattr(TextProcessing, "_is_sleep_hour", staticmethod(lambda: True))
    monkeypatch.setattr("random.random", lambda: 0.0)
    assert await play(tmp, demo.SCENES) == day


def test_the_demo_is_scripted_unless_online_is_asked_for(
        monkeypatch, capsys) -> None:
    seen: list[bool] = []

    async def fake_run(scenes, *, lang, offline, **kwargs):
        seen.append(offline)
        return 0
    monkeypatch.setattr(demo, "run", fake_run)
    monkeypatch.setenv("LLM_API_KEY", "a-real-looking-key")
    assert demo.main([]) == 0
    assert demo.main(["--offline"]) == 0
    assert demo.main(["--online"]) == 0
    assert seen == [True, True, False]
    with pytest.raises(SystemExit):
        demo.main(["--online", "--offline"])
    monkeypatch.setenv("LLM_API_KEY", "  ")
    assert demo.main(["--online"]) == 1
    assert "--online needs a model key" in capsys.readouterr().out


async def test_the_online_banner_says_it_costs_tokens(
        tmp: Path, monkeypatch) -> None:
    _failing(monkeypatch, _http_error(401))
    lines: list[str] = []
    await demo.run(["quiet"], lang="en", offline=False, out=lines.append,
                   base=str(tmp))
    banner = "\n".join(lines[:4])
    assert "your model (" in banner and "costs" in banner
    assert "differ from run to run" in banner and "`personagent demo`" in banner


def test_ctrl_c_in_the_demo_is_a_quiet_exit(monkeypatch, capsys) -> None:
    async def interrupted(*args, **kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(demo, "run", interrupted)
    assert demo.main(["quiet"]) == 130
    assert "Traceback" not in capsys.readouterr().err


async def test_no_fix_says_which_condition_failed(
        tmp: Path, monkeypatch) -> None:
    advice = "did you check the logs? roll back first"
    plain = demo._verdict("rejection", True, "venting", better="", scenario="venting")
    script = [
        demo.Beat("alex", "Nova, the deploy failed again", reply=advice),
        demo.Beat("alex", "Nova, I was just venting", reply=advice, verdict=plain),
    ]
    monkeypatch.setitem(demo.SCRIPTS["en"], "teach", script)
    out = await play(tmp, ["teach"])
    assert "no fix was proposed: a reaction was accepted, but no rewrite" in out
    assert "the judge did not accept any reaction" not in out
    monkeypatch.undo()
    # A scene the judge refuses entirely keeps the plain wording.
    out = await play(tmp, ["troll"])
    assert "no fix was proposed" not in out


async def test_the_teach_scene_reads_in_plain_words(tmp: Path) -> None:
    out = await play(tmp, ["teach"])
    assert "By default one person can\n" in out
    assert "what the ledger recorded, in order (rows are only added, never edited):" in out
    assert "not in use yet" not in out and "PROMOTED" not in out
    assert 'a second rewrite was also drafted for that reply: "ugh, again?' in out
    troll = await play(tmp, ["troll"])
    assert "the judge's verdicts are scripted" in troll


async def test_the_scripted_banner_points_at_online(tmp: Path) -> None:
    out = await play(tmp, ["quiet"])
    assert "(it costs tokens): `personagent demo --online`" in out
