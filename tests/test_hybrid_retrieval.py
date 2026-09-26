"""Tests for hybrid retrieval: lexical, embedding, scope and recency.

The ranking math is checked on hand-built rows. Nothing here reaches a
network or needs a key.
"""
from __future__ import annotations

from persona_agent import ranking
from persona_agent.textproc import _focus_tokens


def check(name: str, cond: bool, detail: str = "") -> None:
    assert cond, name + (f" - {detail}" if detail else "")


# ---------------------------------------------------------------------------
# The ranking math, on hand-built rows
# ---------------------------------------------------------------------------

def test_the_lexical_signal_is_bm25_over_the_pool() -> None:
    docs = [("deploy x1", ""), ("chatter 1", ""), ("others z2", "")]
    lex = ranking.Lexicon({"deploy"}, docs)
    scores = [lex.score(d, (1.0, 0.3)) for d in docs]
    check("lexical: a row sharing a term beats one sharing none",
          scores[0] > 0 and scores[1] == scores[2] == 0.0, repr(scores))
    check("lexical: one term of average rarity in an average-length row counts "
          "1.0, what one substring hit counted before",
          abs(scores[0] - 1.0) < 1e-9, repr(scores))

    docs = [("rare aa", ""), ("common a", ""), ("common b", ""), ("common c", "")]
    lex = ranking.Lexicon({"rare", "common"}, docs)
    check("lexical: IDF - a rare term outweighs a common one",
          lex.score(docs[0], (1.0, 0.3)) > lex.score(docs[1], (1.0, 0.3)))
    check("lexical: a scenario hit outweighs the same hit in context",
          lex.score(("rare", ""), (1.0, 0.3)) > lex.score(("", "rare"), (1.0, 0.3)))
    check("lexical: no query terms, no signal",
          ranking.Lexicon(set(), docs).score(docs[0], (1.0, 0.3)) == 0.0)

    zh_docs = [("服务器又挂了",), ("今天吃什么",)]
    zh = ranking.Lexicon(_focus_tokens("服务器挂了怎么办", "zh"), zh_docs)
    check("lexical: Chinese still matches on _focus_tokens bigrams",
          zh.score(zh_docs[0], (1.0,)) > 0 == zh.score(zh_docs[1], (1.0,)))


def test_scope_orders_the_same_text_by_where_it_was_learned() -> None:
    rows = [{"_seed": True}, {}, {"scope": {"conv_id": "g1"}}, {"scope": {"conv_id": "g2"}}]
    tiers = [ranking.scope_tier(r, "g1") for r in rows]
    check("scope: seed, persona, this conversation, another conversation",
          tiers == [ranking.SEED, ranking.PERSONA, ranking.CONVERSATION, ranking.PERSONA],
          repr(tiers))
    w = ranking.EXAMPLE_WEIGHTS
    same = [ranking.score(w, lexical=1.0, tier=t)
            for t in (ranking.SEED, ranking.PERSONA, ranking.CONVERSATION)]
    check("scope: same text - this conversation > this persona > seed",
          same[2] > same[1] > same[0], repr(same))
    check("scope: a preference, not a filter - a matching seed beats an "
          "unrelated row from this conversation",
          ranking.score(w, lexical=1.0, tier=ranking.SEED)
          > ranking.score(w, lexical=0.0, tier=ranking.CONVERSATION))


def test_recency_decays_exponentially() -> None:
    day = 86400.0
    check("recency: 1.0 now, 0.5 at one half-life, 0.25 at two",
          (ranking.recency(0, 14), ranking.recency(14 * day, 14),
           ranking.recency(28 * day, 14)) == (1.0, 0.5, 0.25))
    check("recency: a future timestamp counts as now, never more",
          ranking.recency(-30 * day, 14) == 1.0)
    w = ranking.EXAMPLE_WEIGHTS
    check("recency: the newer of two otherwise equal rows ranks first",
          ranking.score(w, lexical=1.0, age_s=day) > ranking.score(w, lexical=1.0, age_s=30 * day))
    check("recency: a tiebreaker, capped under one lexical hit",
          ranking.score(w, lexical=1.0, age_s=400 * day)
          > ranking.score(w, lexical=0.0, age_s=-day))


def test_an_embedding_neighbour_with_no_shared_words_needs_embeddings() -> None:
    w = ranking.EXAMPLE_WEIGHTS
    query = [1.0, 0.0, 0.0]
    paraphrase = dict(lexical=0.0, vec=[0.6, 0.8, 0.0])  # unit length, cosine 0.6
    word_match = dict(lexical=0.3, vec=[0.0, 0.0, 1.0])

    def rank(q) -> list[str]:
        scored = {name: ranking.score(w, lexical=r["lexical"],
                                      similarity=ranking.cosine(q, r["vec"]))
                  for name, r in (("paraphrase", paraphrase), ("word_match", word_match))}
        return sorted(scored, key=scored.get, reverse=True)

    check("embedding: without a query vector the word match wins",
          rank(None) == ["word_match", "paraphrase"])
    check("embedding: with one the paraphrase wins",
          rank(query) == ["paraphrase", "word_match"])
    check("embedding: a missing or mismatched row vector is no signal, not an error",
          ranking.cosine(query, None) is None and ranking.cosine(query, [1.0, 0.0]) is None)
