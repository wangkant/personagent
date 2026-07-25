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

No test framework — plain stdlib, no pytest:

```bash
python tests/test_gateway.py
python tests/test_evolution.py
python tests/test_benchmark.py
python tests/test_reactions.py
python tests/test_http.py
python tests/test_retrieval.py
python -m compileall -q .
```

CI runs exactly these on Python 3.10 and 3.12. Run them before opening a PR.

Tests use a lightweight `check(name, cond)` harness. Add new checks next to the
behaviour they cover, and register the test function in that file's `main()`.

**Tests must never write the repo's real state files.** `memory.json`,
`core_memory.json`, `seen_msg_ids.json`, `runtime/` and the sticker library all
live at the repo root; a test that forgets to redirect them will quietly
overwrite a running deployment's learned data. Copy the `make_agent()` helper
from `tests/test_retrieval.py`, which redirects every path into a temp dir.

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
| `persona_agent/learning.py` | Self-eval, reaction adjudication, the evolution loop |
| `persona_agent/reactions.py` | Reaction attribution + adjudicator prompts (pure logic) |
| `persona_agent/evolution.py` | eval → feedback conversion, dedup, pool trimming (pure logic) |

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
for this reason — check `git status` before committing.
