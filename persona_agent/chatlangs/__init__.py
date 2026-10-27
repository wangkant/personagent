"""The languages people may chat in, for the few things the agent says or
reads without the model: memory commands, their replies, the learned
summary and the line sent when a model call fails.

AGENT_LANG stays en or zh: it picks the prompts and the bundled data. A spec
here only decides how a memory command in its language is read and which
language a fixed line answers in. Each language is one module of this
package; `detect` guesses which one a message is written in.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import re

#: Every chat language, in the order a memory command is tried: the two the
#: prompts are written in first.
CODES = ("en", "zh", "zh-TW", "ja", "ko", "es", "fr", "de", "pt-BR", "ru")

#: Keys every `Spec.replies` carries, and the placeholders in each.
REPLY_KEYS = ("remember_what", "not_instructions", "noted", "forget_what",
              "nothing_to_forget", "forgotten", "empty", "recall_head",
              "about", "from")

#: Keys of `Spec.learned_text` (the "what have you learned" summary) and the
#: fields each must use. English builds its own, with plurals, in views.py.
LEARNED_FIELDS = {
    "head": ("memories", "examples", "fixes", "voice", "admin"),
    "score": ("score",),
    "pair": ("was", "better"),
    "someone_else": (),
    "someone": (),
    "retry": ("who",),
    "self_review": (),
    "self_eval": (),
    "corrected": ("who",),
    "missed": ("who",),
    "liked": ("who",),
    "by_admin": (),
    "passed": ("events", "strong"),
    "why": ("steps",),
    "sep": (),
}


@dataclass(frozen=True)
class Spec:
    """One chat language. Regexes are sources, matched case-insensitively."""

    code: str
    # -- memory commands, read right after the persona's name -------------
    #: The keyword of each command. remember and forget take what follows
    #: as the note or the query; recall and learned are the whole message.
    remember: str
    forget: str
    recall: str
    learned: str
    #: Allowed between the name and the command: a vocative particle
    #: ("노바야", "ノヴァちゃん").
    vocative: str = ""
    #: The same two commands with the keyword at the END, for languages that
    #: put the verb last: the note or query is everything before it.
    remember_last: str = ""
    forget_last: str = ""
    #: Lookaheads right after the keyword: reminiscing ("remember when we")
    #: and never mind ("forget it") stay conversation.
    not_a_note: str = ""
    not_a_delete: str = ""
    #: A note or query matching this is a question, not a command.
    question_end: str = r"[?？][\s?？!！.。~～]*$"
    #: Asking words: a forget containing one asks ("what if I forget").
    asking: str = ""
    #: Stripped from the start of a note ("that ", a particle).
    note_lead: str = ""
    #: Stripped from the start of a forget query ("about ").
    query_lead: str = ""
    #: Allowed after the recall phrase, before the closing punctuation.
    recall_tail: str = ""
    #: A forget naming one of these names no note: never mind.
    deictic: frozenset = frozenset()
    #: ...and one naming all of them is too broad to act on.
    everything: frozenset = frozenset()
    #: The saver talking about themself, so the note is about them.
    first_person: str = ""
    # -- what the agent says ---------------------------------------------------
    #: One tuple of variants per `REPLY_KEYS` entry; "about" and "from" take
    #: {name}. Plain chat text: the character policy checks them like replies.
    replies: dict = field(default_factory=dict)
    #: Sent when a model call fails on a direct question.
    failure_excuses: tuple = ()
    #: The learned summary, per `LEARNED_FIELDS`; empty for English.
    learned_text: dict = field(default_factory=dict)
    # -- telling Latin-script languages apart -----------------------------------
    #: Common short words of this language.
    stopwords: frozenset = frozenset()
    #: Letters that, among these languages, point to this one.
    letters: str = ""


SPECS: dict[str, Spec] = {
    code: importlib.import_module(f".{code.replace('-', '_')}", __name__).SPEC
    for code in CODES}


def spec(code: str) -> Spec:
    """The spec for `code`, English when there is none."""
    return SPECS.get(code) or SPECS["en"]


_KANA = re.compile(r"[ぁ-ゟ゠-ヿ]")
_HANGUL = re.compile(r"[가-힣ᄀ-ᇿㄱ-ㆎ]")
_HAN = re.compile(r"[一-鿿]")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_LATIN_WORD = re.compile(r"[a-zà-öø-ÿœß]+(?:'[a-z]+)?")
# Common characters written differently in the two Chinese scripts, paired
# position by position.
_TRADITIONAL = frozenset("們個這來說時會對還過裡麼為點網體學開關樣後讓給誰嗎聽見覺應該將從貓愛車東門問題請謝麼沒記憶")
_SIMPLIFIED = frozenset("们个这来说时会对还过里么为点网体学开关样后让给谁吗听见觉应该将从猫爱车东门问题请谢么没记忆")
_LATIN_CODES = ("en", "es", "fr", "de", "pt-BR")


def detect(text: str, default: str = "en") -> str:
    """The chat language `text` is most likely in, or `default` when nothing
    says. Script first; Latin-script languages by common words and letters."""
    if _KANA.search(text):
        return "ja"
    hangul, han = len(_HANGUL.findall(text)), len(_HAN.findall(text))
    if hangul and hangul >= han:
        return "ko"
    if han:
        traditional = sum(ch in _TRADITIONAL for ch in text)
        simplified = sum(ch in _SIMPLIFIED for ch in text)
        if traditional > simplified:
            return "zh-TW"
        return "zh"
    if _CYRILLIC.search(text):
        return "ru"
    lower = text.lower()
    words = _LATIN_WORD.findall(lower)
    if not words:
        return default
    scores = {}
    for code in _LATIN_CODES:
        s = SPECS[code]
        scores[code] = (sum(word in s.stopwords for word in words)
                        + 2 * sum(lower.count(ch) for ch in s.letters))
    best = max(scores.values(), default=0)
    if not best:
        return default if default in _LATIN_CODES else "en"
    tied = [code for code, value in scores.items() if value == best]
    for code in (default, "en"):
        if code in tied:
            return code
    return tied[0]
