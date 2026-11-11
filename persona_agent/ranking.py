"""Retrieval ranking: one score per row from lexical, embedding, scope and recency.

Pure functions over fields computed ahead, so the ranking can be tested on
hand-built rows and the prompt path never waits on anything in here."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from operator import mul
from typing import Iterable, Optional, Sequence

from .embeddings import text_key

#: Where a row came from, lowest first: a shipped seed, something this
#: deployment learned for its persona, something learned in this conversation.
SEED, PERSONA, CONVERSATION = 0, 1, 2

BM25_K1 = 1.2
BM25_B = 0.75

# math.sumprod is 3.12+.
_dot = getattr(math, "sumprod", None) or (lambda a, b: sum(map(mul, a, b)))


@dataclass(frozen=True)
class Weights:
    lexical: float
    #: Multiplies cosine similarity, which is clamped at 0.
    embedding: float
    #: The bonus of a row written just now; it halves every half_life_days.
    recency: float
    half_life_days: float
    #: Per field of a row, in the order its fields are given.
    fields: tuple[float, ...] = (1.0,)
    #: Bonus per scope tier: SEED, PERSONA, CONVERSATION.
    scope: tuple[float, float, float] = (0.0, 0.0, 0.0)
    mode: float = 0.0
    #: Times (imp - 1) / 4 for an importance of 1 to 5.
    importance: float = 0.0
    #: Times min(uses, 5) / 5.
    use: float = 0.0
    #: The bonus of an event inside the time a message asks about.
    time_match: float = 0.0


#: Examples and pairs; scope stays under the mode bonus, a preference not a filter.
EXAMPLE_WEIGHTS = Weights(lexical=1.0, embedding=2.0, recency=0.3,
                          half_life_days=14.0, fields=(1.0, 0.3),
                          scope=(0.0, 0.2, 0.4), mode=0.5)
#: Memories all belong to one conversation, so scope and mode say nothing;
#: importance and use keep an old useful fact above new trivia.
MEMORY_WEIGHTS = Weights(lexical=0.5, embedding=1.0, recency=0.6,
                         half_life_days=14.0, importance=0.4, use=0.2,
                         time_match=2.0)

#: Days for the recency part of `retention` to halve.
RETENTION_HALF_LIFE_DAYS = 30.0

_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
           "Oct", "Nov", "Dec")
_MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December")


class Lexicon:
    """BM25 over one pool for one query. Terms match as substrings (CJK
    bigrams need no segmenter); IDF is rescaled to average 1.0 over the
    query's matching terms."""

    def __init__(self, tokens: Iterable[str], docs: Sequence[Sequence[str]]):
        df = dict.fromkeys(tokens, 0)
        n = len(docs)
        totals = [0] * (len(docs[0]) if docs else 0)
        for doc in docs:
            for i, text in enumerate(doc):
                totals[i] += len(text)
            # One substring test per token; NUL never occurs in a token, so
            # no match can straddle two fields.
            blob = doc[0] if len(doc) == 1 else "\x00".join(doc)
            for tok in df:
                if tok in blob:
                    df[tok] += 1
        self.avg_len = [max(1.0, total / n) for total in totals]
        idf = {tok: math.log(1.0 + (n - d + 0.5) / (d + 0.5))
               for tok, d in df.items() if d}
        mean = sum(idf.values()) / len(idf) if idf else 1.0
        self.idf = {tok: value / mean for tok, value in idf.items()}

    def score(self, doc: Sequence[str], field_weights: Sequence[float]) -> float:
        s = 0.0
        for tok, idf in self.idf.items():
            for text, avg, weight in zip(doc, self.avg_len, field_weights):
                tf = text.count(tok)
                if tf:
                    norm = 1.0 - BM25_B + BM25_B * len(text) / avg
                    s += weight * idf * tf * (BM25_K1 + 1.0) / (tf + BM25_K1 * norm)
        return s


def epoch(ts) -> float:
    """ISO timestamp -> epoch seconds; 0.0 when unparsable. Naive stamps are
    read as local time, matching every other timestamp in the pipeline."""
    if not ts:
        return 0.0
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, OSError, OverflowError):
        return 0.0


def embedding_text(rec: dict) -> str:
    """What a row is embedded as: the situation it answers, not the reply."""
    ctx = rec.get("context") or []
    if not isinstance(ctx, list):
        ctx = [ctx]
    return "\n".join([str(rec.get("scenario") or ""), *(str(c) for c in ctx)])


def row_fields(rec: dict) -> tuple[str, str, float, str]:
    """What scoring needs from a row, computed once at load: lowercased
    scenario and context, the timestamp as epoch seconds (0.0 means no
    recency bonus) and the row's embedding key."""
    ctx = rec.get("context") or []
    if not isinstance(ctx, list):
        ctx = [ctx]
    return (
        str(rec.get("scenario") or "").lower(),
        " ".join(str(c) for c in ctx).lower(),
        epoch(rec.get("ts")),
        text_key(embedding_text(rec)),
    )


def cosine(a, b) -> Optional[float]:
    """Cosine similarity of two unit vectors; None when either is missing,
    so such a row is ranked on the other signals alone."""
    if a is None or b is None:
        return None
    return _dot(a, b)


def recency(age_s: float, half_life_days: float) -> float:
    """1.0 now, halving every half-life; a future timestamp counts as now."""
    return 0.5 ** (max(0.0, age_s) / 86400.0 / half_life_days)


def age_phrase(age_s: float) -> str:
    """How old a note is, as a prompt tells the model."""
    days = int(max(0.0, age_s) / 86400.0)
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 60:
        return f"{days} days ago"
    return f"{days // 30} months ago"


def scope_tier(row: dict, conv_id: str) -> int:
    if row.get("_seed"):
        return SEED
    scope = row.get("scope")
    if conv_id and isinstance(scope, dict) and scope.get("conv_id") == conv_id:
        return CONVERSATION
    return PERSONA


def score(weights: Weights, *, lexical: float = 0.0,
          similarity: Optional[float] = None, tier: int = SEED,
          age_s: Optional[float] = None, mode_match: bool = False,
          importance: Optional[float] = None, uses: int = 0,
          time_match: bool = False) -> float:
    s = weights.lexical * lexical + weights.scope[tier]
    if similarity is not None:
        s += weights.embedding * max(0.0, similarity)
    if age_s is not None:
        s += weights.recency * recency(age_s, weights.half_life_days)
    if mode_match:
        s += weights.mode
    if importance is not None:
        s += weights.importance * _importance_part(importance)
    if uses:
        s += weights.use * _use_part(uses)
    if time_match:
        s += weights.time_match
    return s


def _importance_part(imp) -> float:
    try:
        value = float(imp)
    except (TypeError, ValueError):
        value = 3.0
    return (min(5.0, max(1.0, value)) - 1.0) / 4.0


def _use_part(uses) -> float:
    try:
        count = int(uses or 0)
    except (TypeError, ValueError):
        count = 0
    return min(max(0, count), 5) / 5.0


def retention(imp, uses, last_s, now: float) -> float:
    """How much a remembered item is worth keeping: importance, use, and how
    long since it was written, confirmed or used. Missing fields are 3, 0, 0."""
    try:
        last = float(last_s or 0.0)
    except (TypeError, ValueError):
        last = 0.0
    days = max(0.0, now - last) / 86400.0
    return (0.4 * _importance_part(3 if imp is None else imp)
            + 0.2 * _use_part(uses)
            + 0.5 ** (days / RETENTION_HALF_LIFE_DAYS))


def memory_age(born, time_s, now: float) -> str:
    """"first noted X", and ", confirmed Y" when it was written again more
    than a day after it was first noted."""
    try:
        written = float(time_s or 0.0)
    except (TypeError, ValueError):
        written = 0.0
    try:
        first = float(born or 0.0) or written
    except (TypeError, ValueError):
        first = written
    phrase = f"first noted {age_phrase(now - first)}"
    if written - first > 86400.0:
        phrase += f", confirmed {age_phrase(now - written)}"
    return phrase


def gap_phrase(seconds: float) -> str:
    """A pause between two chat lines, as the prompt marks it."""
    seconds = max(0.0, seconds)
    if seconds < 3600:
        n, unit = max(1, int(seconds // 60)), "minute"
    elif seconds < 86400:
        n, unit = int(seconds // 3600), "hour"
    else:
        n, unit = int(seconds // 86400), "day"
    return f"{n} {unit}{'' if n == 1 else 's'} later"


def _local(t: float, tz=None) -> datetime:
    return datetime.fromtimestamp(t, tz)


def day_label(t: float, tz=None) -> str:
    """"Mon 10 Nov", in English whatever the system locale; local time
    unless `tz` is given."""
    d = _local(t, tz)
    return f"{_WEEKDAYS[d.weekday()]} {d.day} {_MONTHS[d.month - 1]}"


def month_label(t: float, tz=None) -> str:
    """"September 2026", for a month's roll-up."""
    d = _local(t, tz)
    return f"{_MONTH_NAMES[d.month - 1]} {d.year}"


def date_span(t0: float, t1: float, now: float, tz=None) -> str:
    """When an event happened, made by code: "Mon 10 Nov, 19:00–20:30" within
    a day, "10 to 12 Nov" across days; the year only when it is not this one."""
    first, last = min(t0, t1), max(t0, t1)
    a, b = _local(first, tz), _local(last, tz)
    year = "" if a.year == b.year == _local(now, tz).year else f" {b.year}"
    if a.date() == b.date():
        hours = (f"{a:%H:%M}" if a.strftime("%H:%M") == b.strftime("%H:%M")
                 else f"{a:%H:%M}–{b:%H:%M}")
        return f"{day_label(first, tz)}{year}, {hours}"
    if (a.year, a.month) == (b.year, b.month):
        return f"{a.day} to {b.day} {_MONTHS[b.month - 1]}{year}"
    left = f"{a.day} {_MONTHS[a.month - 1]}" + (
        f" {a.year}" if a.year != b.year else "")
    return f"{left} to {b.day} {_MONTHS[b.month - 1]}{year}"
