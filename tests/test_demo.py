"""`personagent demo`: three scripted scenes through the real decision,
ledger and promotion code, leaving nothing behind."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

import pytest

from persona_agent import demo, paths, reactions
from persona_agent.textproc import TextProcessing


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
        assert "PROMOTED: 2 events, 1 strong, same chat" in out
        assert "[x] 2 of 2 agreeing events" in out
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
        assert ("ledger: 2 reaction(s) recorded, 2 dismissed; 0 proposal(s), "
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
