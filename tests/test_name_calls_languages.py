"""A name or nickname calls the character; an ordinary word that contains it,
or folds to it, does not. Per chat language."""
from __future__ import annotations

import pytest

import re

from persona_agent import chatlangs
from persona_agent.addressing import mentions_name, names_regex

# (name, aliases, must not call, must call)
CASES = {
    "en": ("Luna", ("Lu",), ["lunar eclipse tonight", "the lunatic left", "Lucy and Lulu",
                             "lunatics"],
           ["Luna, you there?", "hey lu", "LUNA!"]),
    "zh": ("小艺", ("艺艺",), ["艺术展不错", "文艺青年", "手艺人"], ["小艺在吗", "艺艺你好"]),
    "zh-TW": ("小雨", (), ["毛毛雨", "雨傘呢", "小時候"], ["小雨在嗎", "小雨你好"]),
    "ja": ("ミラ", ("ミラちゃん",), ["ミラーを見て", "ミラノに行った", "ミライ", "カミラ", "ミラクル"],
           ["ミラ、おはよう", "ミラちゃん元気？", "ミラはどう思う", "ﾐﾗ、いる？"]),
    "ko": ("나라", (), ["우리나라 최고", "대한민국나라", "그나라"],
           ["나라야 뭐해", "나라 씨 안녕", "나라는 어때?"]),
    "es": ("Nina", (), ["la niña llora", "una niña", "ninguno vino", "Ninja"],
           ["Nina, ven", "nina?", "NINA"]),
    "pt-BR": ("Pao", (), ["comprei pão", "pão de queijo", "pãozinho"],
              ["Pao, cadê você?", "oi pao"]),
    "fr": ("Lea", (), ["il lève", "léger", "Léandre"], ["Léa, t'es là ?", "lea viens"]),
    "de": ("Mia", (), ["Miau", "Miami", "Amia"], ["Mia, bist du da?", "mia!"]),
    "ru": ("Таня", ("Танюша",), ["тайна", "танк", "Танзания", "останься"],
           ["Таня, ты тут?", "танюша привет", "ТАНЯ"]),
}

# Marks in the name are optional in the text: "Niña" is still called as "nina".
WITH_MARKS = [("Niña", "nina, ven"), ("Niña", "Niña?"), ("João", "joao cadê"),
              ("João", "João!"), ("Йоко", "Йоко, привет"), ("Йоко", "иоко"),
              ("Sofía", "sofia?"), ("Sofia", "Sofía!")]


def test_every_language_is_covered() -> None:
    assert set(CASES) == set(chatlangs.CODES)


@pytest.mark.parametrize("code,text", [(c, t) for c, v in CASES.items() for t in v[2]])
def test_an_ordinary_word_does_not_call(code: str, text: str) -> None:
    name, aliases, _, _ = CASES[code]
    assert not mentions_name(text, name, aliases), f"{code}: {text!r} called {name}"
    assert not re.search(names_regex(name, aliases), text, re.IGNORECASE), text


@pytest.mark.parametrize("code,text", [(c, t) for c, v in CASES.items() for t in v[3]])
def test_the_name_calls(code: str, text: str) -> None:
    name, aliases, _, _ = CASES[code]
    assert mentions_name(text, name, aliases), f"{code}: {text!r} did not call {name}"


@pytest.mark.parametrize("name,text", WITH_MARKS)
def test_a_mark_in_the_name_is_optional(name: str, text: str) -> None:
    assert mentions_name(text, name), (name, text)
