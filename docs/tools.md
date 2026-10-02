# The `tools/` scripts

The scripts in `tools/` are for people who run personagent from a clone. They
are not installed with the package, and they read `.env` and `runtime/` from
the clone. Run them with the clone's interpreter, from the repository root:

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

Everyday jobs are `personagent` subcommands, not scripts: `personagent doctor`
(was `tools/healthcheck.py`), `personagent learned` (was
`tools/candidates_admin.py`) and `personagent eval` (was
`tools/behavior_eval.py`). The old script names still work and call the same
code.

| Script | What it does | Needs | Calls a model | Status |
|---|---|---|---|---|
| `import_stickers_folder.py` | Imports a folder of images into the sticker library and tags each one, so a new library does not start empty. `--dry-run` shows the counts, `--no-tag` only copies | A folder of images; `VISION_MODEL`, `VISION_API_KEY` and `VISION_BASE_URL` to tag | Yes: one vision call per image, unless `--dry-run` or `--no-tag` | Supported |
| `bootstrap_from_history.py` | One-shot start from a QQ group's history: the admin's sticker and message-length profile, and the stickers seen, saved to the library | NapCat's HTTP server (`QQ_ONEBOT_URL`, which must be set; this is the one script that needs it), QQ groups in `ACCESS_GROUPS` or `--group` | No. The stickers it saves are tagged later by the running bot's vision model | Experimental: QQ and NapCat only |
| `auto_reviewer.py` | Reads low self-eval scores from `runtime/eval.jsonl` and has a model diagnose each into a before/after pair. `--apply` then asks you, pair by pair, whether to add it to the shared feedback pool | `EVAL_ENABLED=true` for a while, so scores exist | Yes, one call per entry reviewed (`--limit`, default 20). `--dry-run` calls nothing | Experimental. `--apply` writes to a pool every chat uses; to approve a fix for one chat only, use `personagent learned` |
| `evolution_benchmark.py` | Drives the real agent over the scenarios in `data/benchmark/` for several rounds, with the self-improvement loop on and off, and compares the two. `run` does it; `ingest` reads back judge scores | `LLM_API_KEY`; a judge that is not the model under test (`--judge export`, `openai` or `anthropic`, with `BENCH_JUDGE_MODEL`) | Yes, and a lot: every scenario, round and arm | Experimental. It measures the value of what the loop drafts, not how much a deployment learns on its own |
| `scenario_probe.py` | Tries candidate benchmark scenarios against the real model and reports which ones expose the failure the benchmark needs | `LLM_API_KEY`; a file of candidate scenarios shaped like `data/benchmark/scenarios.train.en.jsonl`; `--judge-model` for the judge pass | Yes: a reply, a self-eval and a judge call per scenario | Experimental. For building the benchmark |
| `sticker_holdout_eval.py` | Measures how stable and accurate the sticker approval gate is against stickers you labelled by hand | `runtime/holdout.jsonl` (format in `tools/holdout.example.jsonl`); the three `VISION_*` settings | Yes: images × `--runs` (default 5) vision calls, about 150 for 30 images | Experimental |
| `prompt_lab.py` | An interactive menu for trying a prompt change and saving approved replies into the feedback pool | `pip install -e ".[judge]"`, `ANTHROPIC_API_KEY` and `LAB_MODEL`, a different vendor on purpose | Yes: the Anthropic model you name, on each generation | Experimental |
| `dspy_tune.py` | A scaffold that lets DSPy search for better few-shot examples from the feedback pairs. `--bootstrap` previews the pairs, `--tune` runs the optimizer | `pip install dspy-ai` (it is in no extra); `LLM_API_KEY` | `--bootstrap` no; `--tune` yes, many calls | Experimental: a starting point, not a finished tuner |
| `dashboard_snapshot.py` | Seeds a realistic state through the real service and captures the dashboard with headless Edge: en and zh, light and dark, phone, and a fresh home (`--out DIR`, `--only NAME...`) | Microsoft Edge (`--edge PATH`); runs offline | No: a scripted stand-in answers | Supported for maintainers; it makes `docs/dashboard*.png` |
| `package_smoke.py` | Checks an installed `personagent` command end to end: version, `init --no-input`, `chat`, `run` plus `/health`, `doctor --json` | An installed `personagent` (`--personagent PATH`); nothing else | No: a stand-in server answers, nothing leaves the machine | Supported. CI runs it on Linux and Windows |
| `release_notes.py` | Checks a release tag against `pyproject.toml` and prints that version's CHANGELOG section | The tag, e.g. `v1.0.0` | No | Supported. The release workflow runs it |

Supported means it is part of how the project is run and is fixed when it
breaks. Experimental means it works, but it is a research or maintenance aid:
it can change or go without a deprecation period.

None of them runs unless you start it, and the model-calling ones spend credit
on the account in your `.env`. Read a script's header and `--help` before
you run it for the first time, and try `--dry-run` where it has one.
