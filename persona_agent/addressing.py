"""Is the persona being named in a message.

One rule for every place that asks: the group turn's name-call check, the
missed-mention catch-up and the memory commands. A Latin-script name matches
case-insensitively as a whole word ("luna" calls Luna, "Lunar" does not); a
name with CJK characters in it matches as a substring, because those scripts
put no spaces between words.
"""
from __future__ import annotations

import re
from functools import lru_cache

_CJK = ("⺀-⿟぀-ヿ㄀-ㇿ㐀-䶿一-鿿"
        "가-힯豈-﫿ｦ-ﾟ")
_HAS_CJK = re.compile(f"[{_CJK}]")
# A letter or digit of a space-separated script: what a name must not touch.
_WORDLIKE = rf"[^\W{_CJK}]"


def name_regex(name: str) -> str:
    """Regex source matching `name` as a mention; '' for an empty name.

    Compile it with re.IGNORECASE."""
    name = " ".join(str(name or "").split())
    if not name:
        return ""
    body = r"\s+".join(re.escape(part) for part in name.split(" "))
    if _HAS_CJK.search(name):
        return body
    return rf"(?<!{_WORDLIKE}){body}(?!{_WORDLIKE})"


@lru_cache(maxsize=32)
def _compiled(name: str) -> re.Pattern | None:
    source = name_regex(name)
    return re.compile(source, re.IGNORECASE) if source else None


def mentions_name(text: str, name: str) -> bool:
    """True when `text` names the persona called `name`."""
    pattern = _compiled(str(name or ""))
    return bool(pattern and text and pattern.search(text))
