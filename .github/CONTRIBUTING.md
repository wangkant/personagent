# Contributing

Thanks for taking a look. Most of the work in this project is in the prompt
and the learning design, so a bug report that quotes the reply the bot
produced is worth more than a feature request.

## Getting set up

```bash
git clone https://github.com/wangkant/personagent.git
cd personagent
python -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m persona_agent           # opens the local page
python -m persona_agent chat
```

`python -m persona_agent init --terminal` asks the setup questions in the
terminal instead of opening the page. In a clone, the home folder is the
clone itself. `.env`, `persona.txt`, `runtime/` and `platforms/` sit next to
`persona_agent/` and are gitignored. On Windows you can double-click
`start.bat` instead. It creates `.venv`, installs the package and starts it.

`personagent chat` is a simulated group chat. It runs the persona, the reply
triggers, the speak-or-stay-quiet gate, example retrieval, generation, the
character check, the output filters, memory commands and learning from
reactions, in the same order as a live turn. It skips the allowlists, the
debounce and real delivery, and turns off self-evaluation and vision. It is
the fastest way to reproduce a persona bug. Type `/why` to see why it spoke
or stayed quiet. `personagent demo` runs the same machinery against a
scripted model and needs no key.

## Running the tests

With the venv active, run the checks CI runs:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
ruff check . --select F401,F811,F821,F841
python -m compileall -q persona_agent tools tests integrations
```

The suite takes about a minute and needs no network or API key, because the
tests stub the model and the transport. Run these before you open a PR.

The ruff line catches dead and undefined names.

CI runs the suite on Python 3.10 to 3.14 on Linux and on 3.12 on Windows.
Its `package` job, on Linux and Windows, builds the wheel and the sdist,
runs `twine check --strict`, installs each into a clean venv outside the
checkout, and runs `tools/package_smoke.py` and `tools/welcome_smoke.py`
against the installed command. CI compiles `.`. Locally, name the
directories instead so compileall skips `.venv`.

One file, or one test, for a fast loop:

```bash
python -m pytest tests/test_outbox.py
python -m pytest tests/test_outbox.py -k long_poll
```

### The package smoke tests

`tools/package_smoke.py` checks, offline, that an installed `personagent`
command works with no checkout around it. In a throwaway home it runs
`--version`, `init --no-input`, `chat` against a stand-in model, `run` with
`GET /health`, and `doctor --json`. `tools/welcome_smoke.py` opens the
installed local page, saves a key, chats and exits, using only localhost.
Run both after you change packaging, the CLI, the local page or the files a
wheel ships. Pass the version in `pyproject.toml` to `--version`:

```bash
python -m pip install build
python -m build
python -m venv /tmp/smoke-env
/tmp/smoke-env/bin/python -m pip install dist/*.whl     # Windows: Scripts\python.exe
python tools/package_smoke.py --personagent /tmp/smoke-env/bin/personagent --version 1.2.2
python tools/welcome_smoke.py --personagent /tmp/smoke-env/bin/personagent
```

`--skip init` leaves that step out of the package smoke test. The other
steps (`version`, `chat`, `run`, `doctor`) can be skipped the same way, and
the flag can be repeated.

### Writing a test

- A test is a module-level `test_*` function in `tests/test_*.py`. pytest
  finds it, so there is nothing to register.
- The pytest settings in `pyproject.toml` put the repo root and `tools/` on
  the import path, so tests import `persona_agent` and the CLI tools the way
  a deployment does.
- `tests/conftest.py` provides the `tmp` fixture, a scratch directory per
  test. It also runs each `async def` test on its own event loop, and skips
  the 5 s bare-call debounce unless a test is marked `bare_call_wait`.
  pytest is the only test dependency.
- `tests/helpers.py` has `check(name, cond, detail)`, which asserts and
  names the property that failed. Use it or a plain `assert`.
- `isolated_agent(tmp, **settings)` in `tests/helpers.py` builds a real
  `Agent`. A suite's own `make_agent()` passes only what differs, such as
  the persona name, admins, a NapCat URL or stubs.

**Tests must never write the repo's real state files.** Everything mutable
lives under `runtime/`, and a relative state-file setting such as
`MEMORY_FILE=memory.json` resolves there. `isolated_agent()`
redirects every state file into `tmp`. With `seeds=True` it also swaps the
shipped seed pools for empty ones.

The evidence log, the candidate ledger, both promoted views and the persona
lineage all live next to `examples_file` (`Agent.learning_dir`), so
redirecting the example pool moves the whole learning layer. Put any new
learned state in that directory, not under `ROOT`.

## The learning path: evidence, candidates, promotion

These terms have exactly these meanings in code, tests and docs. Keep them
distinct in a PR.

- **Evidence**: an append-only record of something that happened in a
  conversation. A reaction is evidence. It carries no authority.
- **Candidate**: a versioned, proposed behaviour change produced by
  adjudicating evidence. Inert until promoted.
- **Promotion**: granting a candidate authority to affect future behaviour.
- **Rollback / supersession**: removing that authority later, without
  erasing history.

The design enforces two rules.

1. **Nothing in the automatic path writes a retrieval pool.** It records
   evidence, proposes a candidate, and asks `promotion.decide`. If your
   change appends to `examples_file` or `feedback_file` from the agent, it
   is in the wrong layer.
2. **A single automatic signal must never permanently change behaviour.**
   Promotion needs at least two distinct compatible events, at least one of
   them strong. `PROMOTE_MIN_EVENTS` and `PROMOTE_MIN_STRONG` can raise those
   floors but not lower them. A new signal source belongs in
   `evidence.classify_strength`, with a written reason for its class. "The
   admin said so" is not a substitute for being the person the reply was
   aimed at.

Both logs are append-only. To correct a mistake, append a lifecycle event.
Never edit a row.

## Code layout

`Agent` (`agent.py`) builds the runtime state. It is composed from mixins,
one per concern, and calls the pure modules below by name. Deciding whether
to speak, building the prompt and retrieving what goes into it are separate
modules, so each can be read, tested and replaced on its own.

The entry points:

| Entry | What it is |
|---|---|
| `personagent` (`persona_agent/cli.py`) | The command: `start` (the default), `up`, `init`, `chat`, `demo`, `run`, `connect`, `doctor`, `learned`, `eval`. Each subcommand imports its module only when it runs, so `--home` is in the environment first. Also `python -m persona_agent` |
| `persona_agent/welcome.py`, `static/welcome/` | The local page `personagent start` opens on 127.0.0.1: Chat, Activity, Connect apps, Character & settings, with its JSON API. Activity reads the agent service's `/api/dashboard/` with the token in `<runtime>/dashboard.token`. A second `start` reuses an open page. The images at the top of `static/` are the page's and the README's illustrations |
| `persona_agent/connections.py` | The catalog of platforms the page can connect, and which go direct or through the managed AstrBot |
| `persona_agent/direct/` | QQ official bots, personal WeChat, Telegram and Discord, connected by personagent itself in one process (`python -m persona_agent.direct`), with credentials in `platforms/direct.json` |
| `persona_agent/astrbot_install.py` | The managed AstrBot for every other platform: downloaded into the home on its own Python 3.12, run headless with no dashboard |
| `persona_agent/services.py` | The processes the page or `up` starts (agent, direct, managed AstrBot): they end with it, and what a crashed run left is stopped at the next start |
| `persona_agent/home.py` | Where a deployment lives (`AGENT_HOME`, the checkout, the working folder, `~/personagent`) and where shipped files are found. Stdlib only |
| `persona_agent/server.py` | The FastAPI service: `/v1/events`, `/v1/outbox`, `/health`, the deprecated `/v1/onebot`, startup checks. `personagent run` starts it |
| `persona_agent/setup_wizard.py` | `init --terminal` and `connect`: bilingual terminal questions, the key test, the handshake with an AstrBot you already run |
| `persona_agent/chat.py`, `demo.py` | The simulated group chat and the scripted demo |
| `persona_agent/dashboard.py` | The agent service's Activity API under `/api/dashboard/`, its token, and the plain-text note at `/`. `decision_log.py` keeps the recent speak decisions it returns |
| `persona_agent/doctor.py`, `ledger_admin.py`, `evals.py` | `doctor`, `learned` and `eval` |
| `persona_agent/updates.py` | The update notice: asks PyPI for a newer release at most once a day, sending only the version number. `UPDATE_CHECK_ENABLED=false` turns it off |
| `start.bat`, `start.ps1` | Windows from a source ZIP or a clone: make `.venv`, install, then start |

The rest of the package:

| Module | Owns |
|---|---|
| `persona_agent/agent.py` | `Agent`: construction, runtime state, the ledgers and views it holds, shutdown |
| `persona_agent/turns.py` | Intake: dedup, admission, debounce and the group turn from message to send |
| `persona_agent/decision.py` | Whether to speak: a group turn's mode (`choose_group_mode`), pacing skips (`pacing_skip`), the cheap gate model (`_gate`), the turn's model work (`_think`), and the shared reply finalizer (`_final_reply`) |
| `persona_agent/prompt.py` | What the model reads: `_build_group_prompt`, `_build_dm_prompt` and their context blocks |
| `persona_agent/retrieval.py` | What past material a turn sees: examples, memories, lorebook entries, and the embeddings fetched for them ahead of the prompt |
| `persona_agent/ranking.py` | The retrieval score: BM25, embedding similarity, scope and recency, with their weights (pure logic) |
| `persona_agent/embeddings.py` | The optional `/embeddings` call and its cache, in memory and in `runtime/embeddings.jsonl` |
| `persona_agent/dm.py` | The one-on-one turn |
| `persona_agent/messages.py` | Reading a message: its text, quotes, buffer lines, @-mentions |
| `persona_agent/addressing.py` | Whether a message names the persona: the one rule the group turn, the missed-mention sweep and the memory commands share |
| `persona_agent/llm.py` | Model calls: clients, endpoints, retries, fallback, probes, model routing |
| `persona_agent/search.py` | Web search when a turn needs it |
| `persona_agent/proactive.py` | Speaking first: the proactive loops |
| `persona_agent/memory.py` | Memory commands, automatic memories, core memory |
| `persona_agent/views.py` | Seed and learned data kept fresh from disk: pools, promoted views, filters, lorebook |
| `persona_agent/settings.py` | `AgentSettings`: everything the agent is configured with, built once and passed in |
| `persona_agent/config_env.py` | The one way to read a setting from the environment (`env_int`, `env_bool`, `env_str`, ...) |
| `persona_agent/prompts.py` | The persona contract (style guide, output protocol, intent rules) and the `[style]` block parser |
| `persona_agent/textproc.py` | Pure text: tokenising, sanitising, the whitelist validator, splitting, the prompt's data frames |
| `persona_agent/ingestion.py` | Links, share cards, images, OCR, vision, SSRF guard |
| `persona_agent/transport.py` | Throttling, chunking, typing simulation, sends, connector conversation LRU |
| `persona_agent/learning.py` | Self-eval, reaction adjudication, the evolution loop: the glue that records evidence and proposes candidates |
| `persona_agent/evidence.py` | The append-only evidence log: schema, strength classification, idempotent appends (pure logic) |
| `persona_agent/candidates.py` | Versioned candidates, the append-only lifecycle ledger, the materialized retrieval views (pure logic) |
| `persona_agent/promotion.py` | The promotion policy: thresholds, scope compatibility, conflicts. `EvidenceIndex` and `retract_example` |
| `persona_agent/reactions.py` | Reaction attribution and adjudicator prompts (pure logic) |
| `persona_agent/evolution.py` | Low-score eval → diagnosis → BAD/OK pair, dedup, pool trimming (pure logic) |
| `persona_agent/endpoints.py` | Which OpenAI-compatible endpoint serves a model name (the fallback may have its own), and base-URL spelling |
| `persona_agent/connector.py` | Translating a `/v1/events` event to the internal shape, and the reply sink ([docs/connectors.md](../docs/connectors.md) has the schema) |
| `persona_agent/outbox.py` | Messages no request is waiting for: each connector conversation's reply handle, and the queue a connector pulls from `/v1/outbox` |
| `persona_agent/channels.py` | The one place conversation, memory and learning keys are derived from an event |
| `persona_agent/access.py` | Who the admin is and who is admitted, per platform: `ADMIN_IDS`, `ACCESS_GROUPS` and `ACCESS_DM_USERS` (pure logic) |
| `persona_agent/lineage.py` | Which persona-document hashes count as one character, so a persona edit doesn't orphan what was learned |
| `persona_agent/stickers.py` | Sticker library: ingestion, dedup, tagging, persona-fit gate, selection |
| `persona_agent/storage.py` | File locks, atomic replace, locked JSONL appends and rotation |
| `persona_agent/paths.py` | Deployment root (`AGENT_HOME`), runtime-dir isolation, seed lookup, JSONL reading |
| `persona_agent/health.py`, `preflight.py` | Dependency probes; startup config check (missing or misspelled keys) |
| `tools/` | Offline scripts that are not part of the package; [docs/tools.md](../docs/tools.md) lists them |

New behaviour goes in the module that owns the concern. If a change needs
state from two mixins, it probably belongs in `agent.py`.

A module stays out of the mixin chain when it needs no agent state.
`textproc.py` is an example. It is called by name
(`TextProcessing._sanitize_reply(...)`), so a reply-safety gate can be
tested without constructing an `Agent`.

To add a setting, add it to `AgentSettings` in `settings.py` and read it
with the `config_env` helpers. Settings of the HTTP layer, such as
`SERVER_HOST`, are read in `server.py`. Then document the setting in
`.env.example`. Preflight reports any `.env` key that is not in
`.env.example` as a misspelling, and `tests/test_http.py` fails if a setting
the code reads is missing from `.env.example`.

## Style

- Write code, comments, logs and commit messages in English. Chinese is for
  user-facing chat copy and prompt text only.
- Comments explain a constraint the code cannot show, such as why a lock is
  released before a send or why a guard fails closed. Don't narrate the next
  line.
- A change to `prompts.py` changes the persona's behaviour, so treat prompt
  text as behaviour and describe the failure you observed in the PR.
- Keep AI-assistant tooling files out of the repo, such as `CLAUDE.md`,
  `.cursor*` and agent scratch directories. The repo holds project files
  only.

## Reporting a persona bug

Use the "Persona report" issue form. It asks for three things:

1. The last few context lines, with names and IDs redacted.
2. What the bot replied.
3. What a real person would have said instead.

Together they form the BAD/OK pair the learning loop uses, and they often
become the fix directly as a row in `data/feedback.<lang>.jsonl`. Copy the
shape of an existing row: `context`, `reply`, `better`, and
`"rating": "better"`. The form also asks for the persona excerpt and the
model, because both change what a reply looks like.

## Documentation

The English page is the source of truth. Some pages have a `*.zh-CN.md`
twin: `README`, `docs/start`, `docs/guide`, `docs/DISCLAIMER` and the
AstrBot plugin README. The Chinese twin is written in natural Chinese for
Chinese readers rather than translated line by line. When you change a fact
in one, change it in the other.

`docs/deploy.zh-CN.md` is not a twin. It is a separate step-by-step guide in
Chinese that covers installing, connecting QQ by scan, other platforms and
troubleshooting, and closes with a section on the third-party AstrBot and
NapCat route. Images in a README use absolute `raw.githubusercontent.com`
URLs so they render on PyPI.

## Releasing

A release is a tag. Only the maintainer cuts one.

1. Put the version in `pyproject.toml`, `persona_agent/__init__.py`
   (`__version__`) and the plugin's `metadata.yaml`. A test fails if the
   three differ.
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] — YYYY-MM-DD`
   (an em dash) and put a new, empty `## [Unreleased]` above it. In the link
   list at the end, add
   `[X.Y.Z]: https://github.com/wangkant/personagent/compare/vA.B.C...vX.Y.Z`
   under the `[Unreleased]` line and point that line at `vX.Y.Z...HEAD`. The
   section under the version becomes the release notes.
3. Merge to `main` and wait for CI to pass.
4. Tag `main` and push the tag:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

The `Release` workflow (`.github/workflows/release.yml`) then runs three
jobs in order:

1. **build** refuses a tag whose commit is not on `main`, then runs the test
   suite. Next, `tools/release_notes.py` fails the release if the tag is not
   `v` plus the version in `pyproject.toml`, or if `CHANGELOG.md` has no
   non-empty `## [X.Y.Z]` section. The job then builds the sdist and the
   wheel, runs `twine check --strict`, and smoke-tests the wheel with
   `tools/package_smoke.py` before anything is published.
2. **pypi** publishes that build to PyPI by trusted publishing, through the
   GitHub environment named `pypi`. No token is stored.
3. **github-release** creates the GitHub Release for the tag, attaches the
   sdist and the wheel, and uses the changelog section as the release notes.
   It also attaches `astrbot_plugin_personagent.zip`, the plugin folder
   packed by `git archive`, for AstrBot's Install from File. The plugin has
   no repository of its own.

A manual run of the workflow from a branch only builds the files and
uploads them as workflow artifacts. Run it from a tag to release. PyPI needs
a trusted publisher for this repository, set up once on pypi.org: owner
`wangkant`, repository `personagent`, workflow `release.yml`, environment
`pypi`.

## Privacy

Never attach real group chat logs, QQ numbers, platform credentials or API
keys to an issue. `.env`, `persona.txt`, `runtime/`, `platforms/`,
`eval.jsonl`, `memory.json` and the sticker library are gitignored for this
reason. Check `git status` before you commit.

The evidence log quotes real reactions verbatim, so it lives under
`runtime/` with the rest. It stores only the structured verdict and a
one-sentence reason, never a model's chain of thought. Don't add a field
that would change that.
