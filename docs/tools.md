# The `tools/` scripts

The scripts in `tools/` are for people who run personagent from a clone. They
are not installed with the package, and they read `.env` and `runtime/` from
the clone. Run them with the clone's interpreter, from the repository root:

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

Everyday jobs are `personagent` subcommands rather than scripts:
`personagent doctor`, `personagent learned` and `personagent eval`. To try a
prompt change, use `personagent chat`. To measure one, use `personagent eval`.

| Script | What it does | Needs | Calls a model | Status |
|---|---|---|---|---|
| `import_stickers_folder.py` | Imports a folder of images into the sticker library and tags each one, so a new library does not start empty. `--dry-run` shows the counts and `--no-tag` only copies the files | A folder of images, plus `VISION_MODEL`, `VISION_API_KEY` and `VISION_BASE_URL` for tagging | Yes, one vision call per image, unless you pass `--dry-run` or `--no-tag` | Supported |
| `bootstrap_from_history.py` | Gives a new deployment a one-time start from a QQ group's history. It builds the admin's sticker and message-length profile and saves the stickers it sees to the library | The HTTP server of NapCat, a third-party QQ client, at `QQ_ONEBOT_URL` (required), and QQ groups in `ACCESS_GROUPS` or `--group` | No. The running bot's vision model tags the saved stickers later | Experimental, QQ and NapCat only |
| `auto_reviewer.py` | Reads low self-eval scores from `runtime/eval.jsonl` and has a model turn each one into a before/after pair. With `--apply` it then asks you, pair by pair, whether to add it to the shared feedback pool | `EVAL_ENABLED=true` for a while, so that scores exist | Yes, one call per entry reviewed (`--limit`, default 20). `--dry-run` calls nothing | Experimental. `--apply` writes to a pool that every chat uses. To approve a fix for one chat only, use `personagent learned` |
| `evolution_benchmark.py` | Runs the real agent over the scenarios in `data/benchmark/` for several rounds, once with the self-improvement loop on and once with it off, and compares the two. `run` does the runs and `ingest` reads back the judge scores | `LLM_API_KEY`, and a judge that is not the model under test (`--judge export`, `openai` or `anthropic`, with `BENCH_JUDGE_MODEL`) | Yes, heavily: every scenario, round and arm | Experimental |
| `scenario_probe.py` | Tries candidate benchmark scenarios against the real model and reports which ones expose the failure the benchmark needs | `LLM_API_KEY`, a file of candidate scenarios in the shape of `data/benchmark/scenarios.train.en.jsonl`, and `--judge-model` for the judge pass | Yes, a reply, a self-eval and a judge call per scenario | Experimental, for building the benchmark |
| `sticker_holdout_eval.py` | Measures how stable and accurate the sticker approval gate is against stickers you labelled by hand | `runtime/holdout.jsonl` (format in `tools/holdout.example.jsonl`) and the three `VISION_*` settings | Yes, images × `--runs` (default 5) vision calls, about 150 for 30 images | Experimental |
| `package_smoke.py` | Checks an installed `personagent` command end to end: version, `init --no-input`, `chat`, `run` with `/health`, and `doctor --json` | An installed `personagent` (`--personagent PATH`) and nothing else | No, a stand-in server answers | Supported. CI runs it on Linux and Windows |
| `welcome_smoke.py` | Checks the installed local page end to end: `start --no-browser`, saving a key, one chat with the real character, a second launch that reuses the page, and a clean exit | An installed `personagent` (`--personagent PATH`) and nothing else | No, the same stand-in server answers | Supported. CI runs it on Linux and Windows |
| `release_notes.py` | Checks a release tag against `pyproject.toml` and prints that version's CHANGELOG section | The tag, such as `v1.1.0` | No | Supported. The release workflow runs it |

Experimental scripts are research and maintenance aids and can change or be
removed without a deprecation period. Scripts that call a model spend credit on
the account in your `.env`; read `--help` first and try `--dry-run` where it
exists.
