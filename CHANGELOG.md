# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] — 2026-09-04

AstrBot is the platform now: QQ enters through the same gateway as every
other adapter, the three model settings are named for the protocol instead of
a vendor, and the package is 1,300 lines lighter after a debugging pass and a
simplification pass. Every fix below was reproduced before it was changed and
is covered by a test that fails without it.

### Deprecated

- **The direct OneBot ingress — `/webhook/qq` fed by the client's own
  webhook — and `launch.vbs`, which starts it.** Still served, still tested,
  warned about once in the log on first use; removal comes in a later
  release. The supported path is AstrBot with
  `GATEWAY_NATIVE_PLATFORMS=aiocqhttp`, which manages the QQ client itself and
  keeps every id spelled the way the ledgers already know it. **No feature is
  lost on that path**: `BOT_QQ`, `QQ_GROUPS` and the OneBot HTTP API
  (`NAPCAT_API`) stay in use for identity and for the QQ-only background
  actions — proactive sends, the catch-up sweep, OCR — exactly as before. Only
  `WEBHOOK_SECRET` belongs to the deprecated door alone.

### Added

- **`persona_agent/preflight.py` — a misspelled setting is no longer silent.**
  The deployment surface is 80 settings and four of them matter for a first
  reply; everything else has a default, which is fine except that it makes a
  TYPO invisible. `.env` with `DEEPSEK_API_KEY=sk-...` produced a bot that
  started cleanly, logged nothing unusual, never answered, and gave the
  operator no way to find out short of reading the source. Reported at startup
  and by `tools/healthcheck.py`: missing required settings, an `AGENT_HOME`
  that is not a directory, an empty `BOT_NAME`, and any key `.env.example`
  does not list. Reported, never fatal — a deployment that is 90% configured
  should start and say what the other 10% is.
- **`GATEWAY_NATIVE_PLATFORMS` — one forwarder can carry QQ too.** The gateway
  namespaces every id as `<platform>:<raw>` so a forwarded identity can never
  collide with a real QQ number. Right for Telegram, exactly wrong for QQ
  itself: routing QQ through the same door renamed every conversation, so
  memory, history and every candidate scope pointed at rooms and people that
  do not exist — and not repairably, because the ledgers content-address their
  rows over `conv_id`, so the rename moves every id derived from it. Naming a
  platform here makes its ids arrive bare, identical to NapCat's. Empty by
  default. It is an operator setting rather than something the forwarder
  asserts, because a bare id is the spelling `OWNER_QQ`, `QQ_GROUPS` and
  `PRIVATE_ALLOWED_QQS` are written in — and for the same reason those
  whitelists now gate on the id's shape rather than on the sink, so a native
  forwarder cannot both claim QQ authority and skip the QQ gate.
- **A proactive turn over the gateway (`"proactive": true`).** A platform
  reached only through a forwarder could never be spoken to first: the reply
  sink closes when the request returns, so there is no channel between
  requests, and the proactive loops skip any namespaced conversation for want
  of anywhere to send. Inverting the turn removes the problem instead of
  solving it — the caller issues the request on a schedule of its own, and the
  reply comes back in the response like any other. The flag marks the event's
  text as a cue the caller wrote rather than the reader's words, which is what
  keeps it out of `private_history`, out of the reaction store's `ctx_lines`,
  and out of anything promotable. Read off the event and threaded as an
  argument, never carried on the payload: `/webhook/qq` accepts arbitrary
  JSON, so a payload field would let a forged request tell the engine "this
  text is mine, do not write it down". Ported from the sibling engine.
- **`.env.example` is checked against the code.** The typo check treats the
  template as the authority on what a key may be called, so a test scans every
  `os.getenv` / `os.environ.get` in the package and asserts the template
  documents it. It found `PERSONA_FILE` and `PERSONA_CARD_FILE` on its first
  run — the card being the carrier for the per-persona reply-style opt-ins, so
  a persona author reading the template had no way to learn the feature
  existed. Both are documented now.

### Security

- **The gateway envelope's HMAC signature is tested against a bad signature.**
  Every existing envelope test supplied a CORRECTLY computed one and varied
  something else, so the comparison could be replaced with `if False:` and the
  whole suite stayed green — measured by mutation. That signature is the only
  thing binding the request body to the token: without it a bearer token seen
  once in a log or a proxy is enough to inject arbitrary chat events. Ten
  cases now, each with a fresh nonce and a fresh replay guard so a replay
  refusal cannot stand in for a signature refusal.
- **A rejection of a candidate's rewrite no longer expires.** The first cut of
  the fix below applied the ordinary evidence-age window to it, so the
  protection could be outwaited: rejection on day 0, two fresh corroborating
  corrections on days 40 and 41, and the refused text promoted. Counter-
  evidence about the REPLY still expires — a stale laugh must not veto a fresh
  correction — because "this person refused this exact text" is a different
  statement and does not go stale.
- **A refused character no longer has a twin that walks past it.** Every
  refusal is spelled in the ORIGINAL — `[`, `]` and `\` by absence from the
  ASCII punctuation string, `<>{}|` by the hard-reject set, the CJK brackets
  by the sanitizer — while the `0xFF00-0xFFEF` branch of the validator admits
  a BLOCK. `[INST] hi [/INST]` was dropped while `［INST］ hi ［/INST］` was
  released, `「persona」` was stripped while `｢persona｣` was not, `a\b` was
  dropped while `a＼b` was not, and `_arrow_frame` could not see `￩persona￫`
  at all because its character class is built from the arrows opt-in. A
  compatibility twin now inherits the fate of its NFKC fold, **derived** at
  import rather than listed — the same argument `_HARD_REJECT_FOLD_RANGES`
  already makes for itself, and the derivation turned up `U+FE47`/`U+FE48`,
  `U+FE68` and the whole vertical-form bracket family that no list had.
- **The CJK punctuation blanket no longer carries combining marks.** Naming
  the whole `0x3000-0x303F` block admitted `U+302A-U+302F`: six stackable,
  zero-width marks, which is the invisible-width channel `_SCRIPT_MARK_RANGES`
  exists to refuse. Forty of them survived a default-style reply intact.
- **A retry acceptance can no longer argue that a rejected reply is a good
  example.** `evidence.supports` accepted one for `positive_example` on the
  strength of its `positive` reaction type, but that event is about the PAIR
  and its `reply` field is the text the user REJECTED — and it classifies
  STRONG, so one would have cleared `min_strong` alone. Only a reply-equality
  check in `supports_candidate` happened to disagree, which was a guard by
  accident rather than by intent.
- **Memory-deletion authority fails closed.** `trusted_admin` was
  `not user_id or is_owner`, so a message that arrived without attribution
  inherited OWNER rights over everyone else's entries.

### Fixed

- **The terminal trial validates with the persona's own style.** `try_chat.py`
  called `_sanitize_reply(reply, lang)` without the `ReplyStyle` every
  production site passes, so a persona that opts into emoji, extra charsets or
  a wider `max_chars` saw replies truncated or dropped in the trial that the
  live bot would send unchanged — the opposite of what the tool is for.
- **`PERSONA_FILE` and `PERSONA_CARD_FILE` resolve under `AGENT_HOME`**, as
  `.env.example` has always said. They were resolved from the working
  directory, so a deployment launched from anywhere but the checkout silently
  fell back to the bundled example persona.
- **`tools/healthcheck.py` no longer calls its probes "read-only".** They POST
  a completion to every configured model and spend credit, which `README.md`
  said and the tool's own `--help` denied. The config and ledger sections are
  free; the service probes are not.
- **`/openapi.json` reports the package version** instead of a hard-coded
  `0.1.0`, and the app title is `personagent`.
- **A OneBot event with an out-of-range `time` is rejected, not a 500.** The
  freshness check caught `OverflowError` on the gateway path and not on the
  QQ path; both now share one implementation.

- **A truncated reply keeps its voice.** `_sanitize_reply` re-validates what
  it truncates, so a cut landing inside a `[STICKER:…]` marker or inside a ZWJ
  sequence left a bare `[` or a joiner modifying nothing and the whole reply
  was dropped — the subtler silence the seam exists to remove, one layer down.
  The sticker case needed no persona configuration and fired at nine
  consecutive body lengths.
- **The vendor gate no longer silences a denial.** Negation guards existed on
  the Chinese `是` branch and on none of the three English patterns, so
  "I'm not ChatGPT, I'm Mira" was dropped whole — along with reported speech
  (`我是说deepseek…`), a pronoun object (`我叫他别用kimi了`) and the customer
  reading (`作为智谱的老用户…`).
- **The same @ is answered once.** The dedup ring is keyed on the string
  spelling at one choke point: the webhook path banked `"12345"` while the
  catch-up replay compared `12345`, so every mention the sweep replayed got a
  second answer.
- **What a DM teaches reaches a DM prompt.** The learning scope (`dm:<uid>`)
  is derived from the memory namespace (`private:<uid>`) instead of being read
  back under it; the two spellings disagree on two of the six fields
  `_authorized_view` compares.
- **A persona's `[style]` block changes the chat it is written for.**
  `prompts.py` carries a full 1:1 renderer set with all six knobs applied and
  the ctor has always parsed the block, but `_chat_private` kept assembling
  itself from the GROUP constants — so a declared knob was stripped from the
  prose and then ignored, and a DM was reading the group PASS list that
  `private_output_protocol` exists to replace.
- **The proactive DM cooldown engages.** The attempt is marked whether or not
  the model answers PASS, which is what the group dispatcher already says and
  does; the assignment sat inside the send-success branch, so the documented
  common case re-rolled every tick.
- **Teacher reputation decays** (30-day half-life). `hard_block` consulted
  counters whose only writer sits behind the gate, making it an absorbing
  state: five dismissals during a tuning session muted someone permanently.
- **The NapCat bridge is not proxied.** httpx has no implicit localhost
  bypass, so an `HTTP_PROXY` in the launching shell relayed every reply,
  history poll and OCR call to `127.0.0.1` through it. Calls to the wider
  internet still honour the proxy.
- **The gateway has its own admission budget** (`MAX_INFLIGHT_GATEWAY`). It
  answers synchronously and holds a slot for the whole turn while
  `/webhook/qq` releases within milliseconds; one shared counter let gateway
  bursts 429 the QQ path.
- **`PROMOTE_AUTO=1` means on.** `_bool` was `raw == "true"`, so every other
  spelling silently disabled automatic promotion.
- **Promotion says which kind of "no" it means.** A `positive_example` cannot
  reach `min_strong` from any quantity of the events that support it — it is
  waiting for a person, not for more evidence — but the reason read
  "0/1 strong events", which describes a bar the next reaction might clear.
- The owner branch gates on `is_owner` alone (`OWNER_NAME` ships empty and is
  independently optional, so gating on both sent the owner down the stranger
  branch); the sticker guide no longer renders `haven't analyzed 's chat
  style`; a non-dict `owner_profile.json` no longer turns every message into
  a silent no-reply; the gateway replay guard un-burns a nonce when its
  persist fails and warns before its cap instead of 403-ing silently;
  `_spawn` retrieves its tasks' exceptions; `_focus_tokens` builds n-grams per
  CJK run (a one-character trigger scored nothing, and `你好，世界` produced
  `好世`); `_split_text` keeps a separator with the clause it terminates.

- **A replayed reaction no longer mints a second candidate.** Evidence
  identity is content-addressed and `adjudication` is deliberately not part of
  it — that is what lets a retried task or a duplicated webhook be absorbed —
  so the same reaction answered differently the second time was ONE evidence
  row and TWO candidates proposing different rewrites, which then blocked each
  other permanently with the promoted view empty.
- **The evolve loop no longer burns a model call per tick, forever, on an
  answer it could not parse.** `src_eval_ts` is the only review-dedup key, and
  a reviewer response that failed to parse wrote no audit row, so the eval
  stayed pending indefinitely. Same failure by a second route: appends past
  `candidates.jsonl`'s 20 MB cap are refused silently and the return value was
  not read, which stopped the loop's progress and the audit trail at once.
- **Two low-score evals in the same second are two evals.** The eval row's
  timestamp is the review-dedup key and had one-second resolution, so the
  second one was invisible from then on. Microseconds now.
- **Bounding a scope field no longer merges two conversations.** Normalising
  both sides of the comparison through a plain truncation made two ids
  differing only past the limit into one string, so material promoted in one
  room could be authorized into another sharing its 128-character prefix. An
  over-length value keeps a prefix and carries a digest of the whole original.
- **Refusing an entire promoted view says so.** Dropping 100% of a non-empty
  view logged nothing, which is what let the `PERSONA_VERSION` mismatch above
  delete the learning loop in silence — and `persona_hash` is one of the six
  compared fields, so editing the persona document by one byte orphans the
  learned corpus the same way, with a trigger nobody opts into.

### Changed

- **BREAKING: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` and `DEEPSEEK_MODEL` are
  now `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL`.** The agent has only ever
  spoken the OpenAI-compatible `/v1` endpoint and runs against Zhipu, Moonshot,
  OpenRouter or a local llama.cpp exactly as well, but a vendor's name on the
  three settings every deployment MUST set read as a requirement, and
  `DEEPSEEK_BASE_URL=https://openrouter.ai/api` is a line nobody should have to
  write. The new names match `LLM_TIMEOUT` and `LLM_MAX_RETRIES`, which were
  already spelled that way. The old names are NOT honoured: an existing `.env`
  has to be updated. Preflight makes that loud rather than mysterious — the
  missing `LLM_API_KEY` is reported as a required setting, and each leftover
  `DEEPSEEK_*` key as one `.env.example` does not list.
- **Simplification pass, no behaviour change: −1,340 lines across the
  package** (agent.py 3,896 → 3,363; prompts.py 1,296 → 874; transport.py
  554 → 439). The reply post-processing pipeline that was copy-pasted at four
  sites is one `_finalize_reply`; the group and private NapCat senders and
  their segment loops are one `_napcat_send` / `_deliver_segments`; the
  lazy-sidecar properties, JSON save/load, stale-file reload, pool-delta
  bookkeeping and search formatters each have one implementation. Shared
  helpers replaced copies: `textproc.strip_json_fences`, `salvage_json_object`
  and `apply_k2_quirks` (five, two and six sites), `storage.file_stamp` /
  `warning_bytes` / `append_jsonl_rotating`, `health.eval_endpoint`,
  `preflight.private_model_from_env`, `pools.epoch`. `_call_llm` takes the
  system prompt as a string: the `cache_control` block lists were flattened to
  one string on arrival and no test or tool read the list form.
- **Dead code removed**: `promotion._rewrite_is_unwitnessed` (superseded by
  `witnessed_rewrites`), `EvidenceLog.get` / `.has`, `CandidatePool.sightings`,
  the `_classify_api_error` branch whose both arms returned `"transient"`, an
  unreachable `StopIteration` handler, and the language / persona-region /
  trusted-directives blocks in `prompts.py` that nothing in this repository
  or its siblings imports.
- **Comments were cut to the "why".** The incident narratives above the
  `[style]` parser, the fullwidth-twin and arrow-frame tables, the sanitizer
  tiers and a dozen methods in `agent.py` are one to three lines each now;
  `_call_llm`'s docstring is in English.
- **Per-reply rebuilds hoisted**: the sticker/AT marker regexes and both
  `str.maketrans` strip tables are module constants; `TZ_OFFSET_HOURS` is
  parsed by one helper; `_handle_memory_command` compiles its three
  bot-name patterns once per name instead of once per @-message.
- **The corroboration scan reads each ledger once**, not once per pending
  candidate (`_decide_promotion` accepts pre-fetched `events` / `peers`).
- **The ingestion-only constants (URL patterns, OG regexes, vision prompts)
  live on `ContentIngestion`**, the mixin that reads them, instead of on
  `Agent`.
- **Docs**: `docs/deploy.md` states the `/health/details` token rule (token
  configured ⇒ header only, loopback alone refused) and the two path rules
  that follow from `AGENT_HOME`. `CONTRIBUTING.md`'s module map lists every
  module, its install line pulls the runtime deps, and it names the ruff gate
  and launcher checks CI runs beyond `pytest`. `.env.example` lost a
  duplicated persona block and a reference to a `0.1.2` release that never
  existed, and documents the `GLM_BASE_URL` default. The launchers no longer
  call the project `persona-llm-agent`.
  Both READMEs gain a six-row settings table, the trial's flags and in-session
  commands, the `/health/details` header rule, `candidates_admin.py list`, a
  pointer to the quiet-bot checklist, and their acknowledgements back.
  The README demo animation shows two lines of the room's chat above each
  incoming message and grows from two scenes to four: reply, pass, a reply
  that saves a memory, and a direct call answered with a sticker.
  The architecture diagram is redrawn: every platform, QQ included via NapCat,
  enters through AstrBot and `/webhook/gateway` into one five-stage path, the
  learning column runs bottom-up from signals to promoted views and hot-reloads
  into prompt assembly, every arrow is labelled, and nothing overflows its box.

- **`tools/auto_reviewer.py --dry-run` no longer calls the model.** It
  suppressed only the write, so reaching for it to find out what the tool
  would do got you billed for finding out. The old behaviour is `--no-write`.
- **`quickstart.py --help` no longer runs the bootstrap.** The only argv
  handling was `"--no-input" in sys.argv`, so `--help` — or any unrecognised
  flag — fell through to `pip install -r requirements.txt`.
  `tools/healthcheck.py --help` had the same shape and fired live probes.
- **`persona_agent/channels.py`** is now the only place the conversation-key
  vocabulary lives. Routing, memory and learning keys are three different
  names for one conversation, three call sites derived the mapping between
  them independently, and two were wrong.
- `AGENT_EVIDENCE_WARN_BYTES` and `AGENT_CANDIDATE_LEDGER_WARN_BYTES` now
  change something observable: `run_checks` has a ledger-size probe. Both
  knobs were documented, both were computed by a `health_metadata` with no
  caller outside the test suite.
- **The DM key prefixes are minted in `channels`, not spelled at twelve call
  sites.** The derivations already went through that module; what was left was
  twelve hand-written `f"private:{uid}"` / `f"dm:{uid}"` literals in `agent.py`
  and `transport.py`. Each was audited before it was replaced and each was
  correct, so this changes no behaviour — but the prefixes are frozen (`dm:` is
  in the scope of every DM candidate in a live ledger), and the warning saying
  so now sits where the format is decided. Those twelve literals were also the
  only thing pinning the wire format, so a test pins it explicitly instead.
- `httpcore` is a direct dependency — `ingestion.py` imports a private module
  of it for the SSRF guard's per-hop DNS pinning, and `httpx` pins only the
  major version.
- CI gates on `ruff --select F401,F811,F821,F841`, and a `dev` extra installs it.
- `.env.example` documents `AGENT_HOME`, `LLM_TIMEOUT`, `LLM_MAX_RETRIES`,
  `MAX_INFLIGHT_GATEWAY` and the two ledger warn-byte settings.

- **A gateway reply of silence no longer reads as "not my conversation".**
  The response said only whether a reply came back, and the forwarder used
  that to decide whether to suppress its own model. But this agent stays quiet
  on purpose far more often than it speaks — a PASS, several messages merged
  into one answer, the rhythm gate — so AstrBot's built-in model answered in
  rooms the persona had deliberately sat out, as someone else. The response
  now carries `owned` alongside `handled`, set once the turn clears admission;
  the plugin gates on that and falls back to `handled` against an older agent.

- **A failed log rotation no longer swallows the log line.** Windows refuses
  `os.rename` on a file another handle holds open, and a leftover uvicorn is a
  normal state on this platform. `RotatingFileHandler.emit` calls `doRollover`
  inside its own try, so the failure is not "rotation skipped" — it is
  `handleError`, and the record is never written. The log would start losing
  exactly the lines it exists to keep, at the moment the file grew big enough
  to be worth rotating. A rollover that cannot happen is now one that did not
  happen: the file grows past `maxBytes` until a later attempt succeeds. Only
  affects deployments that set `LOG_FILE`. Ported from the sibling engine,
  where it was measured.
- **The group send no longer simulates typing into a sink.** On QQ the sleep
  IS the pause the reader sees — this coroutine and the chat window are one
  timeline. Behind a gateway sink they are not: every chunk is collected and
  handed back as a finished list, so the waiting happens before the caller has
  anything to show, and the caller then emits the burst it already paced. The
  private path was fixed when this was measured at 7.0s of a 12.3s turn; the
  group path kept sleeping, inside a held HTTP request holding an admission
  slot — and it is the path that carries the volume once a forwarder brings QQ
  groups in. Asserted by recording the calls, not by timing the turn.

### Performance

Both items were measured before and after; the two that an audit also flagged
but measurement found to be 4% of the time were left alone.

- **The candidate ledger no longer replays the whole log on every write.** It
  kept an in-memory projection and then dropped it after each append, so a
  write cost a full re-parse of the file it had just appended one line to.
  Ten proposals against a 2,000-row ledger: 0 full-file replays, was 10. The
  invalidation is a `(size, mtime_ns)` stamp read INSIDE the append's own
  lock, so a second writer's rows are still picked up — the projection is only
  kept when the file is exactly what this process last left.
- **`EvidenceLog.append` re-reads only when the file moved**, not on every
  call. 10.9× at 20,000 rows.

### Removed

- `_handle_private_legacy` — 106 lines, defined once and called nowhere,
  carrying a hand-rolled lock protocol the live path no longer uses.
- 114 unused imports: one header copied into six modules by the split that
  produced this package.
- `EvidenceLog.reload` and `CandidateLedger.reload`, `_ends_with_newline`, and
  `transition`'s `supersedes` / `superseded_by` keyword arguments — all
  unreachable once the projection above became the single read path. The
  schema-1 READ path for those two fields is kept.
- The unused `httpx.AsyncClient` in `tools/bootstrap_from_history.py`, which
  was opened per run and never issued a request. Note that passing it to
  `download_sticker` would have been a regression, not a fix: that function
  builds its own DNS-pinned client when `client=None`, which is the SSRF
  guard.

## [0.2.0] — 2026-08-11

The headline: **an unsupported character now degrades to a missing glyph,
never to silence.** The reply validator is still a fail-closed whitelist —
that is a token-leak defence and it stays — but "reject" used to mean "drop
the whole reply", and a whitelist narrow enough to catch a chat template is
also narrow enough to catch `ok ❤️ sure`. Measured against the old
validator, ordinary replies with emoji, curly quotes, an ellipsis or a
katakana word produced `""`: the user saw nothing on the turn they cared
about.

### Added

- **A three-tier reply character policy: STRIP / MAP / ALLOW.** Emoji,
  variation selectors, ZWJ sequences and decorative symbol blocks are
  stripped (the reply survives minus the glyph); curly quotes, dashes and
  no-break spaces are mapped to their ASCII spelling; and named letter
  ranges join the whitelist itself, each with a written reason. A code point
  named in no tier still drops the reply — adding a script stays a
  deliberate act. The policy ships with its own suite
  (`tests/test_textproc.py`): a leak corpus that must stay silenced under
  the widest style a persona can express, plus a test-of-the-test that
  fails if the corpus could no longer detect an over-broad widening.
- **Six more scripts on the default path.** Kana, Hangul, Cyrillic, Greek,
  Arabic and Latin-with-diacritics are how languages are spelled, not
  registers a persona opts into: `café later`, `нет проблем` and `なるほど`
  are content now. Thai, Hebrew, Devanagari and friends still fail closed
  until someone names them.
- **Per-persona character opt-ins (`ReplyStyle`), with a card to carry
  them.** A new optional `PERSONA_CARD_FILE` (default `persona.card.json`)
  may declare `{"reply_style": {"emoji": true, "charsets": ["music"],
  "max_chars": 320}}`. Optional charsets are ellipsis, music and arrows —
  registers, not languages. Every malformed value fails toward the narrow
  default, and the arrows opt-in buys narration (`s1 → s2`), not a frame:
  an arrow hugging a bare token (`←persona→`) is rejected by shape, so the
  opt-in cannot be used to smuggle a template past the whitelist.
- **A persona `[style]` declaration block.** A persona document may end
  with a `[style]` block declaring six register knobs (`length`, `vent`,
  `recs`, `good_news`, `particles`, `fatigue`). The block is parsed against
  a single knob table and stripped from the prose, so raw configuration
  never reaches the model as persona text; prose-shaped lines, unclosed or
  repeated blocks and orphan closers all resolve toward keeping the
  persona's sentences.
- **`current_tz_offset_h`** — a per-turn timezone contextvar for gateway
  embedders whose users are not all in the deployment's `TZ_OFFSET_HOURS`.

### Changed

- **The per-turn reply ceiling rose from 500 to 800 characters, and
  truncation got a visible seam.** The ceiling is also the per-turn
  exfiltration bound, so it moved deliberately: the widest length band's
  English reading did not fit under 500, which turned the band into a
  truncation machine. A cut reply now ends in a visible ` ...` rather than
  pretending it was whole.
- **The trusted trailer, and honesty about being an AI.** The system prompt
  now ends with `<trusted_directives>` — application-authored text a persona
  document cannot displace — and the persona sits in an unforgeable
  `<persona>` region above it. The directives carry the safety exceptions
  and an affirmative honesty clause; the engine no longer instructs any
  persona to deny being an AI, in either chat path.
- **Gateway transport hardening.** The gateway-conversation LRU warns once
  instead of per message, skips evicting a conversation whose lock is
  currently held, and releases waiters on eviction; private DM history is
  capped instead of growing without bound.

### Fixed

- **Pacing survives CRLF, and no bubble is a wall.** `\r\n` breaks are
  honored by the splitter instead of leaking `\r` into bubbles; a run of
  punctuation can no longer produce a zero-length bubble, and discarding an
  all-whitespace chunk no longer discards the hard break it carried.
- **Emoji modifiers no longer drop the whole reply.** U+FE0F, U+200D,
  keycaps, flags and skin-tone modifiers survived the old emoji strip,
  reached the whitelist, and silenced the turn.

The engine work below was ported back from the maintainer's private fork of
this engine; the entries above are that sync. What follows was already on
main awaiting release.

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
- **The self-evaluator scores register, not "quality" — and the learning
  trigger moved to match.** Measured three times: a "Here you go: [drafted
  apology]" reply got 4/5 ("slightly formal") from the quality-framed prompt,
  a bolted-on "blatant tells cap at 2" anchor was talked around ("AI-like,
  though not blatant" -> 4), and the same model that rated the same letter
  5/5 as a quality-evaluator rated it 3 as a register-judge -- the frame, not
  the model, was the problem. The eval prompt now defines the persona register
  and scores against it (5 = the register, 3 = drifting into
  helpful-assistant, 1 = broke character). Validated on 8 known-label
  replies: every known tell scored exactly 3, every casual line 5. Because 3
  now *means* "assistant drift", `EVOLVE_THRESHOLD` defaults to 3 -- with the
  old default of 2 the loop would still collect nothing.

- **Thinking-mode models no longer silently skip the JSON reply protocol.**
  Measured on the real reply path: with thinking on, the model treats its
  hidden reasoning channel as having satisfied the protocol's `reasoning`
  field and emits only the bare chat line -- 9 of 17 @-directed turns were
  dropped whole by the fail-closed parser. JSON-protocol call sites now send
  `response_format={"type":"json_object"}` (0 drops in 52 measured turns and
  a 10-turn live check), and the budget-starvation retry also fires on a
  truncated-but-non-empty JSON, which used to vanish without even a length
  warning. Bare text is still never accepted by the parser: the protocol
  boundary stays fail-closed.
- **Token budgets raised for reasoning models, and `disable_thinking` is now
  real.** Hidden thinking tokens bill against `max_tokens`, so the old
  budgets starved: the reply path truncated about 1 turn in 10, and the
  web-search decision at 150 tokens could not even fit its tool call -- with
  thinking on that endpoint rarely emits tool calls at any budget, so the
  search gate now disables thinking outright. Reply 1200->3000, gate
  600->1500, search decision 150->800, evolve draft 600->2000, self-eval
  800->1500, reaction adjudication 400->1000, sticker tagging 200->600 and
  40->300 (thinking off), default cap 2048->4096. The `disable_thinking`
  parameter, previously documented as ignored, now maps to the endpoint's
  thinking switch.

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

[0.3.0]: https://github.com/wangkant/personagent/releases/tag/v0.3.0
[0.2.0]: https://github.com/wangkant/personagent/releases/tag/v0.2.0
[0.1.1]: https://github.com/wangkant/personagent/releases/tag/v0.1.1
[0.1.0]: https://github.com/wangkant/personagent/releases/tag/v0.1.0
