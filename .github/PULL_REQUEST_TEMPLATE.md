## What and why

<!-- What the change does, and the problem it fixes. For a persona or prompt change, describe the reply you saw and the one you wanted. -->

## Tests

<!-- Run these from the repo with the venv active, and tick what you ran. -->

- [ ] `python -m pytest -q`
- [ ] `ruff check . --select F401,F811,F821,F841`
- [ ] A test for the new behaviour, or the reason there is none
- [ ] `tools/package_smoke.py`, if packaging, the CLI or shipped files changed

## Docs

- [ ] README, `docs/` or `.env.example` updated where behaviour or a setting changed (and the `*.zh-CN.md` twin, if there is one)
- [ ] `CHANGELOG.md` has a line under `## [Unreleased]` for anything a user can see

## Checks

- [ ] No keys, tokens, QQ numbers or real chat text in the diff
- [ ] Code, comments and commit messages are in English
