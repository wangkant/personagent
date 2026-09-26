"""Tests for hybrid retrieval: lexical, embedding, scope and recency.

The ranking math is checked on hand-built rows; the embedding path through a
real agent, against an /embeddings endpoint served by httpx.MockTransport with
hand-picked vectors. Nothing here reaches a network or needs a key.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

import httpx

from persona_agent import embeddings, health, preflight, ranking
from persona_agent.agent import Agent
from persona_agent.endpoints import embedding_endpoint, embeddings_url
from persona_agent.llm import _PooledHTTP
from persona_agent.settings import AgentSettings
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


# ---------------------------------------------------------------------------
# Through the real agent
# ---------------------------------------------------------------------------

def make_agent(tmp: Path, **settings) -> Agent:
    """An agent whose every state file, the embedding cache included, is in `tmp`."""
    tmp.mkdir(parents=True, exist_ok=True)
    a = Agent(
        api_key="k", qq_bot_id="1", persona_name="B", lang="en",
        memory_file=str(tmp / "memory.json"),
        eval_enabled=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"), stickers_file=str(tmp / "stickers.json"),
        **settings,
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.core_memory_file = tmp / "core_memory.json"
    a.core_memory = {}
    a.examples_seed_file = tmp / "seed_examples.jsonl"
    a.examples_file = tmp / "examples.jsonl"
    a.feedback_seed_file = tmp / "seed_feedback.jsonl"
    a.feedback_file = tmp / "feedback.jsonl"
    return a


def ex(reply: str, scenario: str, context: list[str], **extra) -> dict:
    return {"scenario": scenario, "mode": "called", "context": context,
            "reply": reply, **extra}


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                    encoding="utf-8")


def test_the_same_text_ranks_by_where_it_was_learned(tmp: Path) -> None:
    a = make_agent(tmp)
    scope = {"lang": a.agent_lang, "platform": "qq", "conv_id": "g1",
             "persona": a.persona_name, "persona_hash": a.persona_hash,
             "persona_version": a.persona_version}
    same = dict(scenario="deploy broke prod", context=["[u] it broke"])
    write_jsonl(a.examples_seed_file, [ex("SEED_ROW", **same)])
    write_jsonl(a.examples_file, [ex("LEARNED_ROW", **same)])
    write_jsonl(a.promoted_examples_file, [ex(
        "PROMOTED_ROW", **same, src="promoted_candidate", candidate_id="c1", scope=scope)])
    block = a._examples_for_prompt("deploy broke", "called", conv_id="g1", limit_good=3)
    order = [block.index(r) for r in ("PROMOTED_ROW", "LEARNED_ROW", "SEED_ROW")]
    check("scope: this conversation, then this persona, then the seed",
          order == sorted(order), block)


# ---------------------------------------------------------------------------
# Embeddings, against a stub endpoint
# ---------------------------------------------------------------------------

EMBEDDING = dict(embedding_model="stub-embed",
                 embedding_base_url="http://embed.test/v1")
FELINE = [1.0, 0.0, 0.0]
OTHER = [0.0, 0.0, 1.0]
QUERY = "my kitten threw up"
#: No row shares a word with QUERY except DEPLOY's context ("threw").
ROWS = [
    ex("VET_REPLY", "feline at the vet", ["[u] she hid under the bed all day"]),
    ex("DEPLOY_REPLY", "deploy broke prod", ["[u] my build threw errors again"]),
    ex("CHATTER_REPLY", "small talk", ["[u] nice weather out"]),
]
MEMORIES = [
    {"text": "Bob threw a party on friday", "time": 1_700_000_000.0},
    {"text": "Mochi the feline hates car rides", "time": 1_700_000_000.0},
]


class StubEndpoint:
    """An OpenAI-style /embeddings endpoint: FELINE for any text naming a cat,
    OTHER for the rest. Records every request."""

    def __init__(self, *, status: int = 200, delay_s: float = 0.0):
        self.status, self.delay_s = status, delay_s
        self.requests: list[list[str]] = []

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        texts = json.loads(request.content)["input"]
        self.requests.append(texts)
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": "unavailable"})
        return httpx.Response(200, json={"data": [
            {"index": i, "embedding": FELINE if ("feline" in t or "kitten" in t) else OTHER}
            for i, t in enumerate(texts)]})


def serve(agent: Agent, endpoint: StubEndpoint) -> httpx.AsyncClient:
    client = httpx.AsyncClient(transport=httpx.MockTransport(endpoint))
    agent._http = lambda **kw: _PooledHTTP(client)
    return client


def seeded(tmp: Path, **settings) -> Agent:
    a = make_agent(tmp, **settings)
    write_jsonl(a.examples_file, ROWS)
    a.memories["g1"] = [dict(m) for m in MEMORIES]
    return a


async def prepared(a: Agent, focus: str = QUERY) -> None:
    """One turn's async half: the query now, the pool in the background."""
    await a._prepare_retrieval(focus, "g1")
    if a._embedding_backfill is not None:
        await a._embedding_backfill


def first_example(block: str) -> str:
    return block.split("Your reply: ", 1)[1].split("\n", 1)[0] if "Your reply: " in block else ""


async def test_examples_and_memories_use_stub_vectors(tmp: Path) -> None:
    off = seeded(tmp / "off")
    await off._prepare_retrieval(QUERY, "g1")
    check("off: nothing is embedded without EMBEDDING_MODEL",
          off._embedding_backfill is None
          and not (tmp / "off" / "embeddings.jsonl").exists())
    check("off: the word match leads",
          first_example(off._examples_for_prompt(QUERY, "", conv_id="g1", limit_good=1))
          == "DEPLOY_REPLY")
    memories = off._memories_for_prompt("g1", QUERY)
    check("off: the memory sharing a word leads",
          memories.index("Bob threw") < memories.index("Mochi"))

    on = seeded(tmp / "on", **EMBEDDING)
    endpoint = StubEndpoint()
    client = serve(on, endpoint)
    try:
        await prepared(on)
    finally:
        await client.aclose()
    check("on: the endpoint was asked", bool(endpoint.requests))
    check("on: the paraphrase with no shared word leads",
          first_example(on._examples_for_prompt(QUERY, "", conv_id="g1", limit_good=1))
          == "VET_REPLY")
    memories = on._memories_for_prompt("g1", QUERY)
    check("on: the memory that means the same thing leads",
          memories.index("Mochi") < memories.index("Bob threw"), memories)


async def test_vectors_are_cached_in_memory_and_on_disk(tmp: Path) -> None:
    a = seeded(tmp, **EMBEDDING)
    endpoint = StubEndpoint()
    client = serve(a, endpoint)
    try:
        await prepared(a)
        sent = [t for batch in endpoint.requests for t in batch]
        check("first run: the query, both memories and every row are embedded",
              sent[0] == QUERY and len(sent) == 1 + len(MEMORIES) + len(ROWS), repr(sent))
        check("first run: batches stay within the provider limit",
              all(len(b) <= embeddings.BATCH_SIZE for b in endpoint.requests))

        endpoint.requests.clear()
        await prepared(a)
        check("second run: no request at all", endpoint.requests == [], repr(endpoint.requests))

        restarted = seeded(tmp, **EMBEDDING)
        restarted._http = a._http
        await prepared(restarted)
        check("after a restart: only the query, which is never written to disk",
              endpoint.requests == [[QUERY]], repr(endpoint.requests))
    finally:
        await client.aclose()
    stored = (tmp / "embeddings.jsonl").read_text(encoding="utf-8")
    check("the file holds keys and vectors, no text",
          "feline" not in stored and "Mochi" not in stored
          and embeddings.text_key(QUERY) not in stored)


def test_the_cache_file_is_pruned_once_mostly_dead(tmp: Path) -> None:
    cache = embeddings.EmbeddingCache(tmp / "embeddings.jsonl")
    vec = embeddings.unit([1.0, 2.0])
    cache.put("m", {f"k{i}": vec for i in range(150)}, persist=True)
    cache.prune("m", {"k1", "k2"})
    lines = (tmp / "embeddings.jsonl").read_text(encoding="utf-8").splitlines()
    fresh = embeddings.EmbeddingCache(tmp / "embeddings.jsonl")
    check("prune: only the kept vectors remain", len(lines) == 2, str(len(lines)))
    check("prune: and they read back intact",
          list(fresh.get("m", "k1")) == list(vec) and fresh.get("m", "k3") is None)
    check("another model's vectors are not this one's",
          fresh.get("other-model", "k1") is None)


async def test_a_down_or_slow_endpoint_changes_nothing_and_says_so_once(
        tmp: Path, caplog, monkeypatch) -> None:
    monkeypatch.setattr(embeddings, "QUERY_TIMEOUT_S", 0.05)
    caplog.set_level(logging.INFO, logger="agent")
    for label, endpoint in (("down", StubEndpoint(status=503)),
                            ("slow", StubEndpoint(delay_s=2.0))):
        plain = seeded(tmp / label / "plain")
        expected = (plain._examples_for_prompt(QUERY, "", conv_id="g1")
                    + plain._memories_for_prompt("g1", QUERY))
        a = seeded(tmp / label / "on", **EMBEDDING)
        client = serve(a, endpoint)
        caplog.clear()
        try:
            for turn in range(3):
                started = time.monotonic()
                await a._prepare_retrieval(QUERY, "g1")
                check(f"{label}: turn {turn} is not held past the query timeout",
                      time.monotonic() - started < 1.0)
                got = (a._examples_for_prompt(QUERY, "", conv_id="g1")
                       + a._memories_for_prompt("g1", QUERY))
                check(f"{label}: turn {turn} ranks exactly as without embeddings",
                      got == expected)
        finally:
            await client.aclose()
        lines = [r.getMessage() for r in caplog.records
                 if "embedding" in r.getMessage().lower()]
        check(f"{label}: one log line for three turns", len(lines) == 1, repr(lines))
        check(f"{label}: and one request - the endpoint is left alone after",
              len(endpoint.requests) == 1, repr(endpoint.requests))
        check(f"{label}: nothing backfilled against a failing endpoint",
              a._embedding_backfill is None)


async def test_the_startup_probe_reports_an_unreachable_endpoint(tmp: Path, caplog) -> None:
    caplog.set_level(logging.INFO, logger="agent")
    a = seeded(tmp, **EMBEDDING)
    client = serve(a, StubEndpoint(status=404))
    try:
        await a._probe_embeddings()
    finally:
        await client.aclose()
    check("probe: a configured but unreachable endpoint is reported",
          any("embedding endpoint failed" in r.getMessage() and r.levelno == logging.WARNING
              for r in caplog.records))
    check("probe: and not retried on the next turn",
          a._embedding_retry_at > time.monotonic())


def test_the_embeddings_endpoint_is_spelled_like_the_chat_one() -> None:
    cases = {
        "https://api.openai.com": "https://api.openai.com/v1/embeddings",
        "https://api.siliconflow.cn/v1/": "https://api.siliconflow.cn/v1/embeddings",
        "https://open.bigmodel.cn/api/paas/v4": "https://open.bigmodel.cn/api/paas/v4/embeddings",
        "https://x.example/v1/chat/completions": "https://x.example/v1/embeddings",
        "http://127.0.0.1:11434/v1/embeddings": "http://127.0.0.1:11434/v1/embeddings",
    }
    got = {base: embeddings_url(base) for base in cases}
    check("url: root, version base, chat endpoint and full endpoint", got == cases, repr(got))
    primary = dict(base_url="https://api.openai.com", api_key="sk-primary")
    check("endpoint: blank base URL is the primary's endpoint and key",
          embedding_endpoint(**primary, embedding_base_url="", embedding_api_key="")
          == ("https://api.openai.com/v1/embeddings", "sk-primary"))
    check("endpoint: a URL of its own is never sent the primary's key",
          embedding_endpoint(**primary, embedding_base_url="http://127.0.0.1:11434",
                             embedding_api_key="")
          == ("http://127.0.0.1:11434/v1/embeddings", ""))


def test_embedding_settings_are_off_unless_named(monkeypatch) -> None:
    check("settings: off by default",
          AgentSettings.from_env(env={"LLM_API_KEY": "k"}).embedding_model == "")
    s = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "EMBEDDING_MODEL": " bge-m3 ",
        "EMBEDDING_BASE_URL": "http://127.0.0.1:11434/v1/", "EMBEDDING_API_KEY": " ek "})
    check("settings: read, trimmed",
          (s.embedding_model, s.embedding_base_url, s.embedding_api_key)
          == ("bge-m3", "http://127.0.0.1:11434/v1", "ek"))
    for name in ("EMBEDDING_MODEL", "EMBEDDING_BASE_URL", "EMBEDDING_API_KEY"):
        monkeypatch.setenv(name, "set")
    check("settings: a deployment setting, not read behind an embedder's back",
          AgentSettings(api_key="k").embedding_model == "")

    findings = preflight.check_config(env={
        "LLM_API_KEY": "k", "EMBEDDING_BASE_URL": "http://127.0.0.1:11434"})
    check("preflight: an endpoint without a model is reported",
          any(f.key == "EMBEDDING_BASE_URL" and f.level == "WARN" for f in findings),
          repr(findings))
    monkeypatch.setenv("EMBEDDING_MODEL", "")
    check("healthcheck: not configured is skipped, not a failure",
          health.check_embeddings()[0] is None)
    check("healthcheck: the probe is never critical",
          [c for n, _f, c in health.CHECKS if n == "Embeddings"] == [False])
