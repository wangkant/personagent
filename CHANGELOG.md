# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **The benchmark's blind judging is now actually blind — and actually judges.**
  Four measurement defects, found by running the thing: the "blind" inbox spelled
  the arm out in every `item_id`; a run the judge scored 5-across-the-board (zero
  variance) was plotted as a tidy curve instead of being refused; the model's
  `PASS` sentinel was graded as if someone had typed the word (polluting both
  the learning material and the judged sample); and a reply-only judge rated a
  drafted apology letter 5/5 "like a friend offering a script" because without
  the chat context, over-formality is invisible. Item ids are opaque digests
  now; `ingest` names void runs (zero variance, silent-rate imbalance,
  no-feedback on-arm, `--style full` ceilings) and exits 2; PASS collapses to
  silence and silence is counted per arm instead of judged; the judge sees the
  scenario context (identical for both arms) and rates against the persona
  register, not mere human-plausibility.
- **An empty reply with `finish_reason=length` is retried once at 4x the
  budget.** A reasoning model can spend the whole token budget on hidden
  chain-of-thought and emit nothing visible; every turn came back empty with
  only a terse warning. The retry recovers the turn and the log now names the
  likely cause (model choice) and the fix.
- **The self-evaluator now treats a blatant AI tell as a failure, not a
  quibble.** Measured on a 30-scenario probe, it scored a "Here you go:
  [drafted apology]" reply 4/5 ("slightly formal"). Since only scores <= 2
  become learning material, the loop was structurally blind to its most common
  failure mode. A scoring anchor caps blatant tells (markdown, drafted
  deliverables, tutorial structure, service politeness) at 2.

### Added

- **Six assistant-bait scenario families** (`rec-request`, `tech-help`,
  `explain-bait`, `decision-bait`, `task-bait`, `plan-bait`, 18 train + 12
  holdout). The original families are all easy social chatter; none exercised
  the style rules the loop is supposed to re-derive. Each new family baits the
  weak-styled model into a register the persona forbids.
- **`tools/scenario_probe.py`** — calibrates candidate scenarios against the
  real model before they earn a place in the benchmark: reports each
  scenario's self-eval and blind-judge score so curation is evidence, not
  intuition.
- **`--judge openai`** — routes blind judging to any OpenAI-compatible
  endpoint (`BENCH_JUDGE_BASE_URL` / `BENCH_JUDGE_API_KEY`, falling back to
  the `DEEPSEEK_*` vars). A failed judge call is dropped, never backfilled
  with a neutral 3 — a fabricated middle score manufactures the "no
  difference" verdict the benchmark exists to test for. The `anthropic`
  backend now behaves the same way.

Recording something and being changed by it are now separate acts. A reaction is
**evidence**. An adjudication creates a **candidate**. **Promotion** grants a
candidate authority over future replies. **Rollback or supersession** takes that
authority away without erasing the history.

### Changed

- **No automatic signal writes a retrieval pool any more.** An accepted
  correction, an accepted retry and a positive reaction previously landed in
  `runtime/feedback.<lang>.jsonl` or `runtime/examples.<lang>.jsonl` — the
  correction and retry paths on the strength of one signal each. All four
  automatic channels (reaction correction, reaction rejection, retry-completion,
  self-eval) now record immutable evidence and propose a versioned candidate.
  Only a promoted candidate reaches few-shot retrieval.
- **`EVOLVE_AUTO` proposes instead of applying.** The unattended loop still
  diagnoses its own low-scoring replies and drafts a BAD → OK rewrite, but a
  self-diagnosis is one automatic signal that nobody witnessed: it now waits for
  a real user event to corroborate it, or for `tools/candidates_admin.py`.
- **Promotion requires corroboration.** At least two distinct compatible events,
  at least one of them strong — an explicit correction from the person the reply
  was aimed at, or a retry that person then accepted. Evidence combines only
  within one persona, persona version, language, conversation and mode. Weak
  evidence (laughter, banter, the agent's own score) never promotes anything at
  any quantity, so **positive examples are now promoted by a human, not by the
  loop**. Contradictory evidence blocks automatic promotion and leaves the
  candidates for review. Owner status no longer substitutes for being the
  affected recipient.
- **Retrieval reads promoted candidates from their own view files**
  (`runtime/promoted.{examples,feedback}.<lang>.jsonl`), rebuilt atomically from
  the ledger and fully derivable from it. The learned pools and the `data/`
  seeds are no longer written by the agent at all, so a rollback or a rebuild
  can never disturb a row you approved yourself.
- `EXAMPLES_MAX_AUTO` / `FEEDBACK_MAX_AUTO` now size the promoted views (the
  offline tools still apply them to what they write). Same names, same reason:
  material promoted under an older prompt should not outvote recent material.

### Added

- `persona_agent/evidence.py` — append-only, content-addressed evidence log.
  Every directed reaction, correction, rejection, retry result and positive
  response is recorded with its scope (language, platform, conversation,
  persona and persona hash), speaker and recipient, the reply and its context,
  the reaction text and how it was directed, the structured verdict, the
  adjudicator model and prompt version, and a parent link for retries and
  elicited corrections. **Chain of thought is never stored** — only the verdict
  and the one-sentence reason. Duplicate events are idempotent.
- `persona_agent/candidates.py` — versioned candidates (`preference_pair` /
  `positive_example`) and the append-only ledger that owns their lifecycle
  (`proposed` → `promoted` → `rolled_back` / `superseded`, plus `rejected`).
  Current state is a replay projection, so a restart cannot disagree with the
  process that wrote it.
- `tools/candidates_admin.py` — list pending candidates, show one with the
  evidence behind it, promote, reject, roll back, supersede, and rebuild the
  retrieval views. Every action appends a lifecycle event; nothing is edited or
  deleted, and the running agent picks the change up on its next turn.
- Promotion policy configuration with conservative defaults: `PROMOTE_AUTO`,
  `PROMOTE_MIN_EVENTS`, `PROMOTE_MIN_STRONG`, `PROMOTE_EVIDENCE_MAX_AGE_DAYS`,
  `PROMOTE_REQUIRE_SAME_CONVERSATION`, and `PERSONA_VERSION`.
- `tests/test_ledger.py` (102 checks) covering the fourteen behaviours that
  matter: one positive promotes nothing, repeated weak engagement promotes
  nothing, one correction proposes without promoting, two compatible events
  including a strong one promote, incompatible scopes never combine,
  contradictions block promotion, an accepted retry corroborates, duplicates are
  idempotent, replay reproduces state exactly, rollback removes a preference
  from retrieval, supersession replaces the active one, both logs stay
  append-only, legacy manual feedback still loads, and no test touches real
  runtime state.

### Compatibility

- Hand-written `data/` seeds are untouched and still read-only.
- Rows you approved through `prompt_lab.py` stay trusted and are still
  retrieved.
- **Pre-ledger automatic rows are left exactly as they are** — not deleted, not
  reclassified, not migrated into the ledger, and still retrieved. They are
  still retractable: an accepted rejection or correction removes the matching
  row, because deletion is the only revocation the pre-ledger design had.
  `promotion.CandidatePool` and `promotion.retract_example` remain public.
- `tools/auto_reviewer.py --yes` is refused. Unattended direct writes cannot
  stand in for a human decision; use interactive `--apply` or promote a
  candidate explicitly with the admin CLI.
- `tools/evolution_benchmark.py` stubs the human gate (`actor="benchmark"` in
  the ledger) so the arm still measures something. No new benchmark numbers are
  claimed for this change.

### Naming and dependencies

The agent talks to one thing: the provider's OpenAI-compatible
`/v1/chat/completions` endpoint, over plain `httpx`. Several names still claimed
otherwise, and one dependency was installed for a vendor SDK the bot never
imports.

- **`ANTHROPIC_PRIVATE_MODEL` is now `PRIVATE_MODEL`.** It was only ever an
  alternate *model name* on the primary endpoint — no Anthropic endpoint was
  involved. The old name is still read as a fallback, so existing `.env` files
  keep working; grep `pre-0.1.2` to find every shim when dropping them.
- **Internals renamed to match what they do:** `_call_anthropic` → `_call_llm`,
  `anthropic_caller` → `llm_caller`, `check_anthropic_chat` → `check_private_chat`.
  Stale comments about the Anthropic SDK, its exception shape and its prompt
  caching were corrected to describe the httpx/OpenAI-compatible path actually
  in use.
- **`anthropic` is no longer a runtime dependency.** Nothing under
  `persona_agent/` imports it. It is now the optional `[judge]` extra, needed
  only by `tools/prompt_lab.py` and `evolution_benchmark.py --judge anthropic`,
  which both fail with an install hint instead of a traceback. Install with
  `pip install -e ".[judge]"`.
- **`start.sh` / `start.ps1` no longer probe for `anthropic`.** The preflight
  import gates the "installing dependencies…" reinstall, so a complete
  environment without the unused SDK triggered a pointless `pip install` on
  every launch. It now checks `PIL` and `ddgs`, which the bot does use.

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

- Development-process notes that were never project documentation. `docs/` now
  holds only the architecture and loop diagrams.
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
