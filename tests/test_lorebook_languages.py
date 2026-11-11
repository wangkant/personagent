"""The shipped lorebook in every chat language: an entry fires on what it is
about, not on a word that happens to contain a keyword.

zh and zh-TW read data/lorebook.zh.json; the other eight read the English
book, so their keywords live there.
"""
from __future__ import annotations

from pathlib import Path

from persona_agent import chatlangs

from helpers import check, isolated_agent

ROOT = Path(__file__).resolve().parents[1]

_SHARED, _KNOW, _AI = ("shared_memory_honesty", "knowledge_honesty",
                       "ai_identity_question")

# (line, the entries it must bring, in prompt order).
_ROWS = {
    "en": [("the database migration ran past midnight", []),
           ("what's the scope of the next generation", []),
           ("check netflix.com/browse later", []),
           ("do you remember when we went hiking?", [_SHARED]),
           ("wait are you a bot?", [_AI]),
           ("have you seen dune", [_KNOW]),
           ("that take is so mid", ["internet_slang"])],
    "zh": [("我们小区今天停水了", []),
           ("车次是G1880", []),
           ("这首歌的曲子不错", []),
           ("你还记得上次我们去爬山吗", [_SHARED]),
           ("你是不是机器人", [_AI]),
           ("88", ["numeric_meme"]),
           ("哈哈哈2333333", ["numeric_meme"])],
    "zh-TW": [("我們社區今天停水了", []),
              ("你還記得上次我們去爬山嗎", [_SHARED]),
              ("你是不是機器人", [_AI]),
              ("你看過鬼滅嗎", [_KNOW])],
    "ja": [("今日はいい天気だね", []),
           ("この前一緒に行った山のこと覚えてる？", [_SHARED]),
           ("あなたはAIなの？", [_AI]),
           ("鬼滅の刃見たことある？", [_KNOW])],
    "ko": [("오늘 날씨 좋다", []),
           ("우리 저번에 등산 갔던 거 기억나?", [_SHARED]),
           ("너 AI야?", [_AI]),
           ("오징어 게임 본 적 있어?", [_KNOW])],
    "es": [("mañana trabajo hasta tarde", []),
           ("¿te acuerdas cuando fuimos de excursión?", [_SHARED]),
           ("¿eres un bot?", [_AI]),
           ("¿has visto Dune?", [_KNOW])],
    "fr": [("je bosse tard demain", []),
           ("tu te souviens quand on est allés randonner ?", [_SHARED]),
           ("t'es un bot ?", [_AI]),
           ("tu as vu Dune ?", [_KNOW])],
    "de": [("morgen arbeite ich lange", []),
           ("weißt du noch, wie wir wandern waren?", [_SHARED]),
           ("bist du ein bot?", [_AI]),
           ("hast du Dune schon gesehen?", [_KNOW])],
    "pt-BR": [("amanhã trabalho até tarde", []),
              ("lembra quando a gente foi fazer trilha?", [_SHARED]),
              ("você é um bot?", [_AI]),
              ("você já viu Duna?", [_KNOW])],
    "ru": [("завтра работаю допоздна", []),
           ("помнишь, как мы ходили в поход?", [_SHARED]),
           ("ты бот?", [_AI]),
           ("ты смотрел Дюну?", [_KNOW])],
}


def _entries(injected: str) -> list[str]:
    return [line[1:line.index("]")] for line in injected.splitlines()
            if line.startswith("[")]


async def test_the_lorebook_in_every_chat_language(tmp: Path) -> None:
    check("a table for every chat language", set(_ROWS) == set(chatlangs.CODES),
          repr(sorted(set(_ROWS) ^ set(chatlangs.CODES))))
    agents = {}
    for book in ("en", "zh"):
        a = isolated_agent(tmp / book, seeds=True, qq_bot_id="1", persona_name="B",
                           lang=book)
        a.lorebook_file = ROOT / "data" / f"lorebook.{book}.json"
        agents[book] = a
    try:
        for code, rows in _ROWS.items():
            agent = agents["zh" if code in ("zh", "zh-TW") else "en"]
            for line, want in rows:
                got = _entries(agent._lorebook_for_prompt([], focus_text=line))
                check(f"{code}: {line!r} brings {want}", got == want, repr(got))
    finally:
        for a in agents.values():
            await a.aclose()
