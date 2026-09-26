"""Retrieval ranking: one score per row from lexical, embedding, scope and recency.

Pure functions over fields computed ahead, so the ranking can be tested on
hand-built rows and the prompt path never waits on anything in here."""
from __future__ import annotations

import math
from dataclasses import dataclass
from operator import mul
from typing import Iterable, Optional, Sequence

#: Where a row came from, lowest first: a shipped seed, something this
#: deployment learned for its persona, something learned in this conversation.
SEED, PERSONA, CONVERSATION = 0, 1, 2

BM25_K1 = 1.2
BM25_B = 0.75

# math.sumprod (3.12+) halves the cost of a pool's worth of dot products.
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


#: Examples and pairs. The lexical, field, mode and recency weights are the
#: substring scorer's, so without embeddings the order barely moves; scope
#: stays under the mode bonus, a preference rather than a filter.
EXAMPLE_WEIGHTS = Weights(lexical=1.0, embedding=2.0, recency=0.3,
                          half_life_days=14.0, fields=(1.0, 0.3),
                          scope=(0.0, 0.2, 0.4), mode=0.5)
#: Memories all belong to one conversation, so scope and mode say nothing.
#: A 7-day half-life meets the old linear 14-day ramp at 0 and 7 days.
MEMORY_WEIGHTS = Weights(lexical=0.5, embedding=1.0, recency=1.0,
                         half_life_days=7.0)


class Lexicon:
    """BM25 over one pool for one query.

    A term occurs in a field when it is a substring of it, as before, so the
    two-character CJK windows of `_focus_tokens` need no segmenter. IDF is
    rescaled so the query's matching terms average 1.0: a term of average
    rarity in a field of average length scores what one hit always scored,
    and the other signals keep their weight against it."""

    def __init__(self, tokens: Iterable[str], docs: Sequence[Sequence[str]]):
        df = dict.fromkeys(tokens, 0)
        n = len(docs)
        totals = [0] * (len(docs[0]) if docs else 0)
        for doc in docs:
            for i, text in enumerate(doc):
                totals[i] += len(text)
            for tok in df:
                if any(tok in text for text in doc):
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


def cosine(a, b) -> Optional[float]:
    """Cosine similarity of two unit vectors; None when either is missing,
    so such a row is ranked on the other signals alone."""
    if a is None or b is None or len(a) != len(b):
        return None
    return _dot(a, b)


def recency(age_s: float, half_life_days: float) -> float:
    """1.0 now, halving every half-life; a future timestamp counts as now."""
    return 0.5 ** (max(0.0, age_s) / 86400.0 / half_life_days)


def scope_tier(row: dict, conv_id: str) -> int:
    if row.get("_seed"):
        return SEED
    scope = row.get("scope")
    if conv_id and isinstance(scope, dict) and scope.get("conv_id") == conv_id:
        return CONVERSATION
    return PERSONA


def score(weights: Weights, *, lexical: float = 0.0,
          similarity: Optional[float] = None, tier: int = SEED,
          age_s: Optional[float] = None, mode_match: bool = False) -> float:
    s = weights.lexical * lexical + weights.scope[tier]
    if similarity is not None:
        s += weights.embedding * max(0.0, similarity)
    if age_s is not None:
        s += weights.recency * recency(age_s, weights.half_life_days)
    if mode_match:
        s += weights.mode
    return s
