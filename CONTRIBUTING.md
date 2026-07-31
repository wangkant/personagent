# Contributing

Thanks for looking. This is a persona-agent template — the interesting part is
the prompt/learning design, so bug reports that include **the actual reply the
bot produced** are worth far more than feature requests.

## Getting set up

```bash
python quickstart.py     # venv + deps + interactive .env wizard
python try_chat.py       # talk to it in the terminal, no QQ account needed
```

`try_chat.py` runs the full reasoning path (persona + style guide + JSON output
protocol + validator), so it is the fastest way to reproduce a persona bug.

## Running the tests

Run what CI runs — one command, every suite:

```bash
python -m pip install "pytest>=8,<10"
python -m pytest -q
python -m compileall -q .
```

CI runs exactly this on Python 3.10 / 3.11 / 3.12 on Linux, and again on
Windows. Run it before opening a PR.

The suites themselves are framework-free stdlib scripts; pytest is only the
runner. Each stays directly executable for a fast single-file loop:

```bash
python tests/test_gateway.py
```

Tests use a lightweight `check(name, cond)` harness. Add new checks next to the
behaviour they cover, and register the test function in that file's `main()`.

**A new test file must be runnable as a script.** `pytest.ini` collects only
`tests/test_pytest_entry.py`, which discovers the script suites — so a plain
pytest-style file would never run while `pytest -q` still reported success.
`test_every_test_file_is_collected` now fails by name when that happens: give
every new `tests/test_*.py` a `main()` and an `if __name__ == "__main__":`
guard.

**Tests must never write the repo's real state files.** `memory.json`,
`core_memory.json`, `seen_msg_ids.json`, `runtime/` and the sticker library all
live at the repo root; a test that forgets to redirect them will quietly
overwrite a running deployment's learned data. Copy the `make_agent()` helper
from `tests/test_retrieval.py`, which redirects every path into a temp dir.

The evidence log, the candidate ledger and both promoted views resolve from
`examples_file.parent`, so redirecting the example pool moves the whole learning
layer with it — deliberately, so one forgotten line in a test harness cannot
accumulate evidence against a live deployment. If you add another piece of
learned state, hang it off the same directory rather than off `ROOT`.

## The learning path: evidence, candidates, promotion

Four words, used in exactly this sense in code, tests and docs. If a PR blurs
them, it will be asked to un-blur them:

- **Evidence** — an append-only record of something that happened in a
  conversation. A reaction is evidence. It carries no authority.
- **Candidate** — a versioned, proposed behaviour change produced by adjudicating
  evidence. Inert until promoted.
- **Promotion** — granting a candidate authority to affect future behaviour.
- **Rollback / supersession** — removing that authority later, without erasing
  history.

Two rules the design exists to enforce, both load-bearing:

1. **Nothing in the automatic path writes a retrieval pool.** It records
   evidence, proposes a candidate, and asks `promotion.decide`. If you find
   yourself appending to `examples_file` or `feedback_file` from the agent, the
   change is in the wrong layer.
2. **A single automatic signal must never permanently change behaviour.** Two
   distinct compatible events, at least one strong. A new signal source belongs
   in `evidence.classify_strength` with a written justification for its class —
   and "the owner said so" is not a substitute for being the affected recipient.

Both logs are append-only. Correcting a mistake means appending a lifecycle
event, never editing a row: the point of the ledger is that "why does it talk
like this" and "why did it stop" both have answers.

## Code layout

`Agent` is composed from mixins, one per concern:

| Module | Owns |
|---|---|
| `persona_agent/agent.py` | Orchestration: message intake, modes, debounce, `_think`, prompt assembly |
| `persona_agent/prompts.py` | The persona contract (style guide, output protocol, intent rules) — pure constants |
| `persona_agent/textproc.py` | Pure text: tokenising, sanitising, the whitelist validator, splitting |
| `persona_agent/pools.py` | Append-aware JSONL loading for the retrieval datasets |
| `persona_agent/ingestion.py` | Links, share cards, images, OCR, vision, SSRF guard |
| `persona_agent/transport.py` | Throttling, chunking, typing simulation, sends, conversation LRU |
| `persona_agent/learning.py` | Self-eval, reaction adjudication, the evolution loop — the glue that records evidence and proposes candidates |
| `persona_agent/evidence.py` | The append-only evidence log: schema, strength classification, idempotent appends (pure logic) |
| `persona_agent/candidates.py` | Versioned candidates, the append-only lifecycle ledger, the materialized retrieval views (pure logic) |
| `persona_agent/promotion.py` | The promotion policy: strength, scope compatibility, conflicts, thresholds — plus the pre-ledger gate kept for compatibility |
| `persona_agent/reactions.py` | Reaction attribution + adjudicator prompts (pure logic) |
| `persona_agent/evolution.py` | eval → candidate conversion, dedup, pool trimming (pure logic) |

New behaviour goes in the mixin that owns the concern. If a change needs state
from two mixins, it probably belongs in `agent.py`.

## Style

- **Code, comments, logs and commit messages in English.** Chinese is for
  user-facing chat copy and prompt text only.
- Comments should explain a constraint the code cannot show — why a lock is
  released before a send, why a guard is fail-closed. Don't narrate the next
  line.
- Prompt text is data, not code: changes to `prompts.py` change the persona's
  behaviour, so describe the failure mode you observed in the PR.
- No AI-assistant tooling files in the repo (`CLAUDE.md`, `.cursor*`, agent
  scratch directories). Keep it to project files.

## Reporting a persona bug

The useful shape is:

1. The last few context lines (redact names/IDs).
2. What the bot replied.
3. What a real person would have said instead.

That maps directly onto the BAD/OK preference pairs the learning loop consumes,
and can often be dropped straight into `data/feedback.<lang>.jsonl` as a fix.

## Privacy

Never attach real group chat logs, QQ numbers, or API keys to an issue.
`runtime/`, `eval.jsonl`, `memory.json` and the sticker library are gitignored
for this reason — check `git status` before committing. The evidence log quotes
real reactions verbatim, so it lives under `runtime/` with the rest, and it
stores only the structured verdict plus a one-sentence reason: **never a model's
chain of thought.** Don't add a field that would change that.
