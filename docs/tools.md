# The `tools/` scripts

English · [简体中文](tools.zh-CN.md) · [繁體中文](tools.zh-TW.md) · [日本語](tools.ja.md) · [한국어](tools.ko.md) · [Español](tools.es.md) · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

The scripts in `tools/` are for people who run personagent from a clone. They
are not installed with the package, and they read `.env` and `runtime/` from
the clone. Run them with the clone's interpreter, from the repository root:

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

Everyday jobs are `personagent` subcommands rather than scripts:
`personagent doctor`, `personagent learned` and `personagent eval`. To try a
prompt change, use `personagent chat`. To measure one, use `personagent eval`.
`personagent eval --suite memory` runs offline with scripted consolidation
answers, 21 cases per language, and needs no key; in this version all of
them hold. The other suites call a model.

| Script | What it does | Needs | Calls a model | Status |
|---|---|---|---|---|
| `import_stickers_folder.py` | Imports a folder of images into the sticker library and tags each one, so a new library does not start empty. `--dry-run` shows the counts and `--no-tag` only copies the files | A folder of images, plus `VISION_MODEL`, `VISION_API_KEY` and `VISION_BASE_URL` for tagging | Yes, one vision call per image, unless you pass `--dry-run` or `--no-tag` | Supported |
| `bootstrap_from_history.py` | Gives a new deployment a one-time start from a QQ group's history. It builds the admin's sticker and message-length profile and saves the stickers it sees to the library | The HTTP server of NapCat, a third-party QQ client, at `QQ_ONEBOT_URL` (required), and QQ groups in `ACCESS_GROUPS` or `--group` | No. The running bot's vision model tags the saved stickers later | Experimental, QQ and NapCat only |
| `sticker_holdout_eval.py` | Measures how stable and accurate the sticker approval gate is against stickers you labelled by hand | `runtime/holdout.jsonl` (format in `tools/holdout.example.jsonl`) and the three `VISION_*` settings | Yes, images × `--runs` (default 5) vision calls, about 150 for 30 images | Experimental |
| `package_smoke.py` | Checks an installed `personagent` command end to end: version, `init --no-input`, `chat`, `run` with `/health`, and `doctor --json` | An installed `personagent` (`--personagent PATH`) and nothing else | No, a stand-in server answers | Supported. CI runs it on Linux and Windows |
| `welcome_smoke.py` | Checks the installed local page end to end: `start --no-browser`, saving a key, one chat with the real character, a second launch that reuses the page, and a clean exit | An installed `personagent` (`--personagent PATH`) and nothing else | No, the same stand-in server answers | Supported. CI runs it on Linux and Windows |
| `window_smoke.py` | Opens the real app window on a scratch home, sets the page up and chats inside the window, then closes it | `personagent` installed with the app extra (`pip install "personagent[app]"`) on macOS and Linux; on Linux also a display, such as `xvfb-run` | No, the same stand-in server answers | Supported. CI runs it on Linux, macOS and Windows |
| `release_notes.py` | Checks a release tag against `pyproject.toml` and prints that version's CHANGELOG section | The tag, such as `v1.1.0` | No | Supported. The release workflow runs it |
| `locale_gaps.py` | Counts, for each language in `persona_agent/locales/`, how many sentences of the setup wizard, the terminal chat and the demo have a translation. With a language code, such as `ja`, it prints the ones still missing, which would show in English | Nothing | No | Supported. `tests/test_locales.py` fails on a gap |

Experimental scripts are research and maintenance aids and can change or be
removed without a deprecation period. Scripts that call a model spend credit on
the account in your `.env`; read `--help` first and try `--dry-run` where it
exists.
