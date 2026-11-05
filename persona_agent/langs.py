"""The languages personagent speaks to the person running it.

English and Chinese sit next to the code that prints them. The other languages
read `locales/<code>.json`, keyed by the English sentence. The prompts and the
bundled examples and filters exist in English and Chinese; `content` says which
of the two a language uses.
"""
from __future__ import annotations

import functools
import json
import os
import re
import sys
from pathlib import Path

from .chatlangs import CODES

#: Each language in its own words, for a menu.
NAMES = {"en": "English", "zh": "简体中文", "zh-TW": "繁體中文", "ja": "日本語",
         "ko": "한국어", "es": "Español", "fr": "Français", "de": "Deutsch",
         "pt-BR": "Português (Brasil)", "ru": "Русский"}

#: What the character is called until someone names it.
DEFAULT_NAMES = {"en": "Nova", "zh": "小夏", "zh-TW": "小夏", "ja": "ノヴァ",
                 "ko": "노바", "es": "Nova", "fr": "Nova", "de": "Nova",
                 "pt-BR": "Nova", "ru": "Нова"}

_ALIASES = {"cn": "zh", "chinese": "zh", "中文": "zh", "english": "en",
            "japanese": "ja", "korean": "ko", "spanish": "es", "french": "fr",
            "german": "de", "portuguese": "pt-BR", "pt": "pt-BR", "russian": "ru"}
_LOWER = {code.lower(): code for code in CODES}
_TRADITIONAL = {"tw", "hk", "mo", "hant"}

_LOCALES = Path(__file__).resolve().parent / "locales"
#: `--help`, `doctor` and the refusals of a start, keyed by the English sentence;
#: `{0}` stands for what the sentence is built around.
_TERMINAL = _LOCALES / "terminal"


def normalize(value: object) -> str:
    """The code for a spelling of a language (zh-CN, zh_TW, pt, Japanese), or ''."""
    raw = str(value or "").strip().lower().replace("_", "-")
    if raw in _ALIASES:
        return _ALIASES[raw]
    primary, *rest = raw.split("-")
    if primary == "zh" and _TRADITIONAL & set(rest):
        return "zh-TW"
    return _LOWER.get(raw) or _ALIASES.get(primary) or _LOWER.get(primary, "")


def content(lang: str) -> str:
    """The language of the prompts and bundled data `lang` reads; a code outside
    the ten keeps its own name, since it names files someone put there."""
    if lang in ("zh", "zh-TW"):
        return "zh"
    return "en" if lang in CODES else lang


@functools.lru_cache(maxsize=None)
def catalog(lang: str) -> dict:
    path = _LOCALES / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def say(en: str, zh: str, lang: str) -> str:
    """One sentence in `lang`."""
    if lang == "zh":
        return zh
    if lang == "en":
        return en
    return catalog(lang).get(en, zh if lang == "zh-TW" else en)


def table(en, zh, lang: str):
    """A tree of sentences, written twice with one shape, in `lang`."""
    if lang == "en":
        return en
    if lang == "zh":
        return zh
    if isinstance(en, str):
        return say(en, zh, lang)
    if isinstance(en, dict):
        return {key: table(value, zh[key], lang) for key, value in en.items()}
    if isinstance(en, (list, tuple)):
        return type(en)(table(a, b, lang) for a, b in zip(en, zh))
    return en


@functools.lru_cache(maxsize=None)
def _terminal_catalog(lang: str) -> tuple[dict, tuple]:
    """A language's terminal sentences, and those with slots as patterns, the
    longest first so a short shape cannot swallow a long one."""
    path = _TERMINAL / f"{lang}.json"
    sentences = json.loads(path.read_text(encoding="utf-8"))
    shapes = []
    for english, there in sentences.items():
        if re.search(r"\{\d\}", english):
            pattern = re.sub(r"\\\{(\d)\\\}", r"(?P<s\1>.+?)", re.escape(english))
            shapes.append((len(english), re.compile(pattern, re.DOTALL), there))
    shapes.sort(key=lambda shape: -shape[0])
    return sentences, tuple((pattern, there) for _, pattern, there in shapes)


def utf8_console() -> None:
    """Every language's output must not crash a pipe on a legacy code page."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def terminal_lang() -> str:
    """AGENT_LANG from the environment or the home's `.env`, else the system's."""
    from . import home
    from .setup_wizard import detect_lang, env_get

    return (normalize(os.environ.get("AGENT_LANG"))
            or normalize(env_get(home.find_home() / ".env", "AGENT_LANG"))
            or detect_lang())


def term(text: str) -> str:
    """One terminal sentence in the language of this install, slots kept."""
    lang = terminal_lang()
    if lang == "en":
        return text
    sentences, shapes = _terminal_catalog(lang)
    if text in sentences:
        return sentences[text]
    for pattern, there in shapes:
        match = pattern.fullmatch(text)
        if match:
            return re.sub(r"\{(\d)\}", lambda slot: term(match[f"s{slot[1]}"]), there)
    if "\n" in text:
        return "\n".join(term(line) for line in text.split("\n"))
    return text
