# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] — 2026-07-25

### Changed

- **A single positive signal no longer banks an example.** One `haha` could
  previously mint a permanent few-shot example, and the LLM self-evaluator —
  documented in-code as generous — could do the same on its own score. Replies
  now enter a candidate pool (`persona_agent/promotion.py`) carrying a weight
  chosen by how much the source is worth, and are promoted only once
  corroboration passes the threshold: two owner reactions, three from other
  members, or four top self-eval scores. Confidence decays with a 21-day
  half-life, so a reply that landed once and never again fades instead of
  waiting at the threshold forever.

### Added

- **Retraction.** An accepted rejection or correction now withdraws the reply
  from the candidate pool *and* deletes it from the live example pool — the
  strongest evidence about a reply is a human disagreeing with it, and until
  now that evidence was discarded.
- `tests/test_promotion.py` (23 checks) covering the weights, the decay curve,
  promotion consuming its candidate, retraction, persistence and pool bounds.

### Removed

- `docs/superpowers/` — 2,000 lines of development-process notes that were
  never project documentation. `docs/` now holds only the architecture and
  loop diagrams.
- The GitHub Pages demo. Its one irreplaceable idea — that the visible reply is
  a single field of a larger decision — now animates in the README itself,
  including a PASS beat where the agent decides not to speak.

### Fixed

- `paths.ROOT` anchored state next to `site-packages` when installed as a
  wheel; it now honours `AGENT_HOME`, else whichever of the package parent /
  cwd actually looks like a deployment root.
- `persona_agent/py.typed` was declared in `pyproject.toml` but never existed.
  CI now asserts it is present inside the built wheel.
- Benchmark and README no longer name a specific vendor as "the judge" — the
  judge is configurable and naming one was both a leftover and inaccurate.

## [0.1.0] — 2026-07-25

First tagged release. The agent has been running against real group chats for
months; this is the point where the layout and the configuration surface are
stable enough to build on.

### Added

- **Learning from real user reactions** as the primary self-evolution signal.
  A directed reaction to a sent reply — a quote, an @, or the interlocutor's
  next DM — is adjudicated in one LLM call into `correction` / `rejection` /
  `positive` / `neutral`. Corrections become BAD→OK preference pairs, genuine
  positives bank the reply as an example. Owner-weighted, banter-filtered, and
  audited in `candidates.jsonl`.
  - **Retry-completion**: after an accepted rejection, the bot's next reply is
    tracked as the fix; if the user then accepts it, `(rejected → retry)`
    closes into a pair with zero user effort.
  - **Delayed elicitation**: when a rejection taught nothing concrete, the bot
    may ask what the user meant — delayed past its own reply, cooldown-limited.
  - **Teacher reputation**: per-user adopted/dismissed history feeds the
    adjudicator; persistently bad teachers are blocked before any LLM call.
- **JSON output protocol.** `reasoning` / `intent` / `reply` / `mem` are JSON
  fields rather than inline tags, so a truncated or malformed generation cannot
  leak chain-of-thought into the visible reply.
- **Whitelist reply validator.** Only characters that look like normal chat for
  the active language are released; XML residue, JSON fragments and tokenizer
  artifacts are dropped wholesale (fail-closed).
- **Dynamic few-shot retrieval** over a read-only `data/` seed plus learned
  `runtime/` pools, ranked by language-aware token overlap, scenario tag, mode
  and recency decay.
- **Platform-neutral gateway** (`/webhook/gateway`) plus an AstrBot forwarder
  plugin, so the same persona reaches Telegram / Discord / Slack / … without
  touching the persona pipeline.
- **Sticker pipeline**: auto-steal → vision-tag → persona-fit gate (text and
  visual) → eval-driven demotion of stickers that score consistently low.
- **Proactive mode** (opt-in): occasionally speaks first, heavily gated by
  silence, cooldown, sleep hours and a PASS-biased prompt.
- **Two-stage model routing**: a cheap gate decides whether to reply at all;
  every reply the group actually sees is written by the main model.
- `EXAMPLES_MAX_AUTO` / `FEEDBACK_MAX_AUTO` — bound the learned pools to the
  newest N machine-written entries. Hand-approved rows are never counted or
  dropped.
- Offline tooling: `try_chat.py`, `tools/prompt_lab.py`,
  `tools/auto_reviewer.py`, `tools/evolution_benchmark.py`,
  `tools/import_stickers_folder.py`.
- `pyproject.toml` — the package is now installable (`pip install -e .`).

### Changed

- **`persona_agent/agent.py` split from ~5,800 lines into focused modules**
  (`prompts`, `textproc`, `pools`, `ingestion`, `transport`, `learning`), with
  `Agent` composing them as mixins. Every previously importable name still
  resolves from `persona_agent.agent`; retrieval output is byte-identical
  across a 60-pool differential test.
- Few-shot pools load incrementally: only the appended tail is parsed when a
  64-byte signature proves the consumed prefix is unchanged. At the 5 MB
  ceiling this cut per-turn retrieval from ~48 ms to ~25 ms, and the turn after
  the agent banks its own example from ~116 ms to ~33 ms.
- Learned data moved to a gitignored `runtime/` directory; `data/` is a
  read-only seed. Real chat content no longer risks being committed.
- Agent state is committed only after delivery succeeds, so a failed send can
  no longer leave a phantom "sent" reply in the buffer.

### Fixed

- Appending to a JSONL pool that lacked a trailing newline glued the new record
  onto the last line and destroyed both.
- `evolution.append_jsonl` refused to write past `FEEDBACK_MAX_BYTES`, which
  silently stopped reaction learning once `feedback.jsonl` filled up.
- Pool staleness now keys on size as well as mtime; an append landing in the
  same filesystem clock tick as the previous read was invisible.
- A future-dated example timestamp could exceed the documented +0.3 recency cap
  and jump the retrieval queue.
- SSRF guard on all outbound URL fetches, including redirect targets; bounded
  and MIME-validated image ingestion; webhook body size limits.

### Security

- Third-party page content (link previews, search results) is fenced in the
  prompt and excluded from the control plane, so a web page cannot trigger
  name-call mode or write memories.
- Gateway DM whitelisting gates on a context-local sink, not on a payload flag,
  so a crafted webhook body cannot bypass it.

[0.1.1]: https://github.com/wangkant/personagent/releases/tag/v0.1.1
[0.1.0]: https://github.com/wangkant/personagent/releases/tag/v0.1.0
