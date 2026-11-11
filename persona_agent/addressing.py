"""Is the persona being named in a message: one rule for every caller.

A Latin-script name matches case-insensitively as a whole word ("luna" calls
Luna, "Lunar" does not); a name with CJK in it matches as a substring. Text
and names are folded first, so full-width letters and missing accents still
call ("ＬＵＮＡ", "sofia" for Sofía). Nicknames come from the persona card.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Iterable

_CJK = ("⺀-⿟぀-ヿ㄀-ㇿ㐀-䶿一-鿿"
        "가-힯豈-﫿ｦ-ﾟ")
_HAS_CJK = re.compile(f"[{_CJK}]")
# A letter or digit of a space-separated script: what a name must not touch.
_WORDLIKE = rf"[^\W{_CJK}]"
# Kana voicing marks tell different syllables apart, unlike Latin accents;
# so do a tilde and a breve (niña, pão, мой): they make another letter.
_KEEP_MARKS = frozenset("\u3099\u309a\u0303\u0306")
_LETTER_MARKS = frozenset("\u0303\u0306")
# A katakana name inside a longer katakana word is that word (ミラー, カミラ).
_KATAKANA = "ァ-ヺー"
_ALL_KATAKANA = re.compile(f"[{_KATAKANA}・]+")
_HANGUL = "가-힣"


def _strip_marks(s: str) -> str:
    """Accents dropped; NFC again so Hangul and kana stay whole."""
    return unicodedata.normalize("NFC", "".join(
        ch for ch in unicodedata.normalize("NFD", s)
        if ch in _KEEP_MARKS or unicodedata.category(ch) != "Mn"))


def fold(text: str) -> str:
    """Width, case and accents folded away."""
    return _strip_marks(unicodedata.normalize("NFKC", str(text or "")).casefold())


def name_regex(name: str) -> str:
    """Regex source matching `name` as a mention; '' for an empty name.

    Compile it with re.IGNORECASE."""
    name = " ".join(str(name or "").split())
    if not name:
        return ""
    body = r"\s+".join("".join(_char_regex(ch) for ch in part) for part in name.split(" "))
    if _ALL_KATAKANA.fullmatch(name.replace(" ", "")):
        return rf"(?<![{_KATAKANA}]){body}(?![{_KATAKANA}])"
    if re.match(f"[{_HANGUL}]", name):
        # Korean is spaced: a name ends a word's start, not its middle (우리나라).
        return rf"(?<![{_HANGUL}]){body}"
    if _HAS_CJK.search(name):
        return body
    return rf"(?<!{_WORDLIKE}){body}(?!{_WORDLIKE})"


def _char_regex(ch: str) -> str:
    """One character of a name; a tilde or breve it has may be left off."""
    bare = unicodedata.normalize("NFC", "".join(
        c for c in unicodedata.normalize("NFD", ch) if c not in _LETTER_MARKS))
    if bare == ch:
        return re.escape(ch)
    return f"(?:{re.escape(ch)}|{re.escape(bare)})"


def names_regex(name: str, aliases: Iterable[str] = ()) -> str:
    """One regex source for the name and its aliases, each as written and
    without its accents, for matching unfolded text; '' when all are empty."""
    sources: list[str] = []
    for n in (name, *aliases):
        for form in (str(n or ""), _strip_marks(str(n or ""))):
            src = name_regex(form)
            if src and src not in sources:
                sources.append(src)
    return "(?:" + "|".join(sources) + ")" if sources else ""


@lru_cache(maxsize=64)
def _compiled(name: str) -> re.Pattern | None:
    source = name_regex(fold(name))
    return re.compile(source, re.IGNORECASE) if source else None


def mentions_name(text: str, name: str, aliases: Iterable[str] = ()) -> bool:
    """True when `text` names the persona called `name` or by an alias."""
    if not text:
        return False
    folded = fold(text)
    for n in (name, *aliases):
        pattern = _compiled(str(n or ""))
        if pattern and pattern.search(folded):
            return True
    return False
