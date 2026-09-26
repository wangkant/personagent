# Contributing

Thanks for looking. The interesting part of this project is the prompt and
learning design, so a bug report that includes **the reply the bot actually
produced** is worth far more than a feature request.

## Getting set up

```bash
python quickstart.py            # creates .venv, installs dependencies, runs the .env wizard
.venv/bin/python try_chat.py    # Windows: .venv\Scripts\python.exe try_chat.py
```

`try_chat.py` runs the persona, example retrieval, generation and the
character check, the same path a live reply takes, so it is the fastest way to
reproduce a persona bug. It skips the allowlists, reply triggers, output
filters, self-evaluation and vision.

## Running the tests

With the venv active, run the checks CI runs:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
ruff check . --select F401,F811,F821,F841
python -m compileall -q persona_agent main.py try_chat.py quickstart.py tools tests integrations
```

Run these before opening a PR.

The ruff line catches dead and undefined names. It is not a style gate. CI
also runs the suite on Python 3.10, 3.11 and 3.12 on Linux and 3.12 on
Windows, checks `start.sh` for syntax and its executable bit, and builds the
wheel and sdist and imports each from a clean venv. CI compiles `.`; locally,
name the directories so compileall skips `.venv`.

One file, or one test, for a fast loop:

```bash
python -m pytest tests/test_outbox.py
python -m pytest tests/test_outbox.py -k long_poll
```

### Writing a test

- A test is a module-level `test_*` function in `tests/test_*.py`. pytest
  finds it; nothing needs registering.
- `pytest.ini` puts the repo root and `tools/` on the import path, so tests
  import `persona_agent`, `main`, `quickstart` and the CLI tools the way a
  deployment does.
- `tests/conftest.py` provides the `tmp` fixture (a per-test scratch
  directory) and runs each `async def` test on its own event loop. pytest is
  the only test dependency.
- Many suites define a local `check(name, cond, detail)` that asserts and
  names the property that failed. Use it or a plain `assert`.

**Tests must never write the repo's real state files.** Everything mutable
lives under `runtime/`, and a relative state-file setting such as
`MEMORY_FILE=memory.json` resolves there. A test that forgets to
redirect a path will overwrite a running deployment's learned data. Start
from the `make_agent()` helper in `tests/test_retrieval.py`, which redirects
every state file into `tmp`.

The evidence log, the candidate ledger, both promoted views and the persona
lineage all live next to `examples_file` (`Agent.learning_dir`). Redirecting
the example pool therefore moves the whole learning layer, so one forgotten
line in a test cannot write evidence into a live deployment. Put any new
learned state in that directory, not under `ROOT`.

## The learning path: evidence, candidates, promotion

These terms mean exactly this in code, tests and docs. Keep them distinct in
a PR:

- **Evidence**: an append-only record of something that happened in a
  conversation. A reaction is evidence. It carries no authority.
- **Candidate**: a versioned, proposed behaviour change produced by
  adjudicating evidence. Inert until promoted.
- **Promotion**: granting a candidate authority to affect future behaviour.
- **Rollback / supersession**: removing that authority later, without
  erasing history.

The design enforces two rules:

1. **Nothing in the automatic path writes a retrieval pool.** It records
   evidence, proposes a candidate, and asks `promotion.decide`. If you are
   appending to `examples_file` or `feedback_file` from the agent, the change
   is in the wrong layer.
2. **A single automatic signal must never permanently change behaviour.**
   Promotion needs at least two distinct compatible events, at least one of
   them strong. `PROMOTE_MIN_EVENTS` and `PROMOTE_MIN_STRONG` can raise those
   floors but not lower them. A new signal source belongs in
   `evidence.classify_strength`, with a written reason for its class. "The
   admin said so" is not a substitute for being the person the reply was
   aimed at.

Both logs are append-only. To correct a mistake, append a lifecycle event;
never edit a row. That way "why does it talk like this" and "why did it stop"
both have answers.

## Code layout

`Agent` (`agent.py`) builds the runtime state and is composed from mixins,
one per concern; it calls the pure modules below by name. Deciding whether to
speak, building the prompt and retrieving what goes into it are separate
modules, so each can be read, tested and replaced on its own:

| Module | Owns |
|---|---|
| `persona_agent/agent.py` | `Agent`: construction, runtime state, the ledgers and views it holds, shutdown |
| `persona_agent/turns.py` | Intake: dedup, admission, debounce and the group turn from message to send |
| `persona_agent/decision.py` | Whether to speak: a group turn's mode (`choose_group_mode`), pacing skips (`pacing_skip`), the cheap gate model (`_gate`), chat signals |
| `persona_agent/prompt.py` | What the model reads: `_build_group_prompt`, `_build_dm_prompt` and their context blocks |
| `persona_agent/retrieval.py` | What past material a turn sees: examples, memories, lorebook entries |
| `persona_agent/thinking.py` | One group turn's model work: prompt, gate, reply (`_think`) |
| `persona_agent/dm.py` | The one-on-one turn |
| `persona_agent/messages.py` | Reading a message: its text, quotes, buffer lines, @-mentions |
| `persona_agent/llm.py` | Model calls: clients, endpoints, retries, fallback, probes, model routing |
| `persona_agent/search.py` | Web search when a turn needs it |
| `persona_agent/proactive.py` | Speaking first: the proactive loops |
| `persona_agent/memory.py` | Memory commands, automatic memories, core memory |
| `persona_agent/views.py` | Seed and learned data kept fresh from disk: pools, promoted views, filters, lorebook |
| `persona_agent/settings.py` | `AgentSettings`: everything the agent is configured with, built once and passed in |
| `persona_agent/config_env.py` | The one way to read a setting from the environment (`env_int`, `env_bool`, `env_str`, ...) |
| `persona_agent/prompts.py` | The persona contract (style guide, output protocol, intent rules) and the `[style]` block parser |
| `persona_agent/textproc.py` | Pure text: tokenising, sanitising, the whitelist validator, splitting, the prompt's data frames |
| `persona_agent/pools.py` | Append-aware JSONL loading for the retrieval datasets |
| `persona_agent/ingestion.py` | Links, share cards, images, OCR, vision, SSRF guard |
| `persona_agent/transport.py` | Throttling, chunking, typing simulation, sends, connector conversation LRU |
| `persona_agent/learning.py` | Self-eval, reaction adjudication, the evolution loop: the glue that records evidence and proposes candidates |
| `persona_agent/evidence.py` | The append-only evidence log: schema, strength classification, idempotent appends (pure logic) |
| `persona_agent/candidates.py` | Versioned candidates, the append-only lifecycle ledger, the materialized retrieval views (pure logic) |
| `persona_agent/promotion.py` | The promotion policy: thresholds, scope compatibility, conflicts. Also `CandidatePool` and `retract_example`, which only withdraw rows learned before the ledger existed |
| `persona_agent/reactions.py` | Reaction attribution and adjudicator prompts (pure logic) |
| `persona_agent/evolution.py` | Low-score eval → diagnosis → BAD/OK pair, dedup, pool trimming (pure logic) |
| `persona_agent/endpoints.py` | Which OpenAI-compatible endpoint serves a model name (the fallback may have its own), and base-URL spelling |
| `persona_agent/connector.py` | The platform-neutral `/v1/events` event schema and reply sink |
| `persona_agent/outbox.py` | Messages no request is waiting for: each connector conversation's reply handle, and the queue a connector pulls from `/v1/outbox` |
| `persona_agent/channels.py` | The one place conversation, memory and learning keys are derived from an event |
| `persona_agent/access.py` | Who the admin is and who is admitted, per platform: `ADMIN_IDS`, `ACCESS_GROUPS` and `ACCESS_DM_USERS` (pure logic) |
| `persona_agent/lineage.py` | Which persona-document hashes count as one character, so a persona edit doesn't orphan what was learned |
| `persona_agent/stickers.py` | Sticker library: ingestion, dedup, tagging, persona-fit gate, selection |
| `persona_agent/storage.py` | File locks, atomic replace, locked JSONL appends and rotation |
| `persona_agent/paths.py` | Deployment root (`AGENT_HOME`), runtime-dir isolation, seed lookup |
| `persona_agent/health.py`, `preflight.py` | Dependency probes; startup config check (missing or misspelled keys) |

New behaviour goes in the module that owns the concern. If a change needs
state from two mixins, it probably belongs in `agent.py`.

A module stays out of the mixin chain when it needs no agent state.
`textproc.py` is one: it is called by name (`TextProcessing._sanitize_reply(...)`),
so a reply-safety gate can be tested without constructing an `Agent`.
Reaching for `self` in such a module undoes the split.

To add a setting, add it to `AgentSettings` in `settings.py` and read it with
the `config_env` helpers (settings of the HTTP layer, such as `SERVER_HOST`, are read
in `main.py`). Then document it in `.env.example`: preflight reports any
`.env` key that is not in `.env.example` as a misspelling, and
`tests/test_http.py` fails if a setting the code reads is missing from
`.env.example`.

## Style

- **Code, comments, logs and commit messages in English.** Chinese is for
  user-facing chat copy and prompt text only.
- Comments explain a constraint the code cannot show, such as why a lock is
  released before a send or why a guard fails closed. Don't narrate the next
  line.
- Prompt text is data, not code: a change to `prompts.py` changes the
  persona's behaviour, so describe the failure you observed in the PR.
- No AI-assistant tooling files in the repo (`CLAUDE.md`, `.cursor*`, agent
  scratch directories). Keep it to project files.

## Reporting a persona bug

Send three things:

1. The last few context lines (redact names and IDs).
2. What the bot replied.
3. What a real person would have said instead.

That is the BAD/OK pair the learning loop uses, and it often becomes the fix
directly: a row in `data/feedback.<lang>.jsonl`. Copy the shape of an existing
row (`context`, `reply`, `better`, and `"rating": "better"`).

## Privacy

Never attach real group chat logs, QQ numbers or API keys to an issue.
`.env`, `persona.txt`, `runtime/`, `eval.jsonl`, `memory.json` and the sticker
library are gitignored for this reason; check `git status` before committing.
The evidence log quotes real reactions verbatim, so it lives under `runtime/`
with the rest. It stores only the structured verdict and a one-sentence
reason, **never a model's chain of thought**. Don't add a field that would
change that.
