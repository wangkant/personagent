# Self-evolution benchmark — design

## Goal

Turn the self-evolution loop from a *claim* ("the bot learns from its own
misses") into a *measured result*: a curve of mean AI-tell score versus
learning round, with an evolve-on arm rising and an evolve-off control arm
staying flat. The deliverable is the evidence that separates "a nice bot"
from "a method with data behind it."

Success = one runnable command produces a curve (CSV + SVG) supporting a
sentence like: "with the loop on, held-out AI-tell score rose from X to Y
over N rounds; the control arm stayed flat at ~X."

## Non-goals

- Not a statistical-significance study (small synthetic set; the control
  arm is the noise floor, not a p-value).
- Not a general prompt-tuning tool (that is `prompt_lab.py`).
- Not tuned to any real chat data — scenarios are fully synthetic (public repo).

## Anti-leakage: the methodological core

Three distinct ways a benchmark like this can fool itself, and how each is
closed:

| Leakage risk | Why it invalidates the curve | Mitigation |
|---|---|---|
| Judge model == the model that writes feedback | A rising curve could just mean replies drift toward that model's taste | Judge is **Claude (Opus)**, an independent vendor from the DeepSeek/GLM/Moonshot stack that drives learning |
| Judge model == the agent's `EVAL_MODEL` | Same circularity: the scorer that drives learning also grades success | `EVAL_MODEL` never scores the benchmark; only Claude does |
| Train scenarios == test scenarios | Measures memorization, not generalization | Strict split: a **train** pool drives the loop; a **held-out** pool is only ever judged, never fed to the loop |

A fourth, subtler point: held-out scenarios must be *same-family,
different-wording* variants of the train scenarios. Few-shot retrieval is
similarity-based, so a learned correction only generalizes to nearby
inputs. If held-out were unrelated, the curve would flatten trivially and
prove nothing. So both pools cover the same failure-mode families with
different surface text.

## Architecture

Two arms, N rounds, held-out measurement.

- **evolve-on arm** — full self-evolution: high-score replies auto-append to
  `examples`, low-score replies flow through diagnosis into `feedback`
  pairs, both hot-reloaded into retrieval.
- **evolve-off arm (control)** — identical generation and self-eval, but
  `feedback`/`examples` are frozen and `_evolve_tick` is never called. Its
  held-out curve is the noise floor: any rise in the on-arm above this is
  attributable to learning, not run-to-run variance.

### Per-round procedure (round k = 1..N; round 0 = pre-learning baseline)

1. **Learn (on-arm only).** Drive the agent over the **train** pool: seed
   `agent.buffers[group_id]` with each scenario's context, call `_think`,
   self-eval the reply (`EVAL_MODEL`, writes the arm's private `eval.jsonl`),
   then run one `agent._evolve_tick()` so low scores become `feedback` pairs.
2. **Measure (both arms).** Drive the agent over the **held-out** pool the
   same way, collect `(scenario_id, reply)`; do NOT self-eval or learn from
   these.
3. Record the round's held-out replies for judging.

Round 0 measures held-out before any learning — the shared baseline.

### The judge (Claude, blind)

The harness never scores replies itself. It:

1. Collects all held-out replies across every round and both arms.
2. Writes them to `judge_inbox.jsonl`, **shuffled**, each with an opaque
   `item_id`, stripping arm/round/scenario so the judge cannot infer what
   "should" score higher (blind scoring).
3. A judge fills `judge_scores.jsonl`: `{item_id, score (1-5), reason}`,
   where score rates how much the reply reads like a real person (5 = human,
   1 = obvious AI tell).
4. The harness joins scores back by `item_id` and aggregates.

Judge backend is pluggable behind one interface `score_items(items) ->
{item_id: {score, reason}}`:

- **`export` (default)** — writes `judge_inbox.jsonl` and stops with
  instructions; an external judge (Claude in a Claude Code session, i.e.
  this assistant) reads it, scores every item, writes `judge_scores.jsonl`;
  re-running the harness with `--ingest` resumes at aggregation. Zero extra
  API setup, strongest model, but not headless.
- **`anthropic`** — if a real Anthropic API key is configured, the harness
  calls the Claude API directly with the same prompt and format. Fully
  headless/reproducible. Same inbox/score schema, so results are comparable.

Both backends consume the identical `judge_inbox.jsonl` and produce the
identical `judge_scores.jsonl`, so the methodology is unchanged either way.

### State isolation (hard rule)

The benchmark must never touch the repo's real runtime state. Each arm runs
the agent with **every** state file redirected into its own temp directory
(`memory.json`, `eval.jsonl`, `feedback.<lang>.jsonl`, `examples.<lang>.jsonl`,
`candidates.jsonl`, `seen_msg_ids.json`, `core_memory.json`, `stickers*`).
Both arms start from the same seed state (the committed synthetic
`examples`/`feedback`, or empty — configurable). This follows the existing
"tests must not write real repo state" rule and mirrors how
`tests/test_gateway.py::make_agent` redirects paths.

## Components

| Unit | Responsibility | Depends on |
|---|---|---|
| `data/benchmark/scenarios.train.<lang>.jsonl` | ~24 synthetic train scenarios across failure-mode families (same schema as `tools/fixtures`: `id`, `scenario`, `mode`, `context`) | — |
| `data/benchmark/scenarios.holdout.<lang>.jsonl` | ~16 held-out scenarios, same families, different wording | — |
| `tools/evolution_benchmark.py` | Orchestrates arms/rounds, seeds buffers, drives `_think`, runs `_evolve_tick`, exports judge inbox, ingests scores, emits CSV + SVG. Reuses `persona_agent.evolution` and the Agent ctor | `persona_agent.agent`, `persona_agent.evolution` |
| judge backend (inside the tool) | `export` (default) / `anthropic` behind one interface | `httpx` (anthropic mode) |
| `docs/evolution_benchmark_curve.svg` | Hand-rendered line chart (on vs off mean score by round) + feedback-pool growth; no matplotlib, same SVG style as existing `docs/` diagrams | — |
| `docs/evolution_benchmark_results.csv` | Raw per-round aggregates for reproducibility | — |

## Data flow

```
scenarios.train ─┐
                 ├─(on-arm, per round)→ _think → self-eval → eval.jsonl → _evolve_tick → feedback grows
scenarios.holdout┤
                 └─(both arms, per round)→ _think → replies ──┐
                                                              ▼
                                                     judge_inbox.jsonl (shuffled, blind)
                                                              ▼  Claude scores
                                                     judge_scores.jsonl
                                                              ▼  join by item_id
                                              CSV aggregates + SVG curve
```

## CLI

```
python tools/evolution_benchmark.py run       # run arms/rounds, write judge_inbox.jsonl, stop
python tools/evolution_benchmark.py ingest     # after judge_scores.jsonl exists: aggregate + plot
python tools/evolution_benchmark.py run --judge anthropic   # headless (needs real Anthropic key)
```

Flags: `--rounds N` (default 4), `--lang en|zh`, `--seed-state empty|synthetic`
(default synthetic), `--holdout-votes K` (default 1; >1 asks the judge to
score each item K times to smooth grader noise), `--outdir`.

Run artifacts (inbox, scores, per-round replies, temp state) live under a
gitignored `benchmark_runs/<timestamp>/`; only the final curve SVG + CSV are
meant to be committed as the published result.

## Error handling

- A model call that fails/empties for a scenario: log, record the reply as
  empty, and let the judge score it (an empty reply is a legitimate low
  score); never abort the whole run for one bad call.
- `_evolve_tick` diagnosis that fails to parse: already handled inside
  `evolution` (skips the entry); the round continues.
- Missing `judge_scores.jsonl` on `ingest`: clear error telling the user to
  score `judge_inbox.jsonl` first.
- Every item in `judge_inbox` must appear in `judge_scores` before
  aggregation; the harness errors on any missing `item_id` rather than
  silently averaging a partial set.

## Testing

Add `tests/test_benchmark.py` (stdlib-only, same `check()` harness):

- scenario files parse and train/holdout `id` sets are disjoint;
- inbox export is blind (no arm/round/scenario fields leak) and shuffled;
- score ingest joins by `item_id` and errors on a missing id;
- aggregation math (mean per arm/round) on a hand-built score set;
- a full mini end-to-end with a **stubbed** `_call_anthropic` (so no network):
  2 rounds × 2 scenarios, assert the on-arm feedback pool grew and the
  off-arm stayed frozen, and that the temp state dirs — not the repo — were
  written.

Wire into CI alongside the other two suites.

## Cost

Self-eval + generation run on the cheap DeepSeek/GLM endpoints already
configured. Judging is done by Claude at ~ (rounds+1) × 2 arms × ~16
held-out × votes ≈ 160–320 items for defaults — free when judged in-session,
or a small Anthropic bill in `--judge anthropic` mode.

## Open decision deferred to implementation

Exact buffer-seeding call shape for `_think` (how `agent.buffers[group_id]`
and the `latest_text`/`caller_override` args are populated from a scenario)
— to be pinned against the current `_think` signature during the plan, not a
design-level choice.
