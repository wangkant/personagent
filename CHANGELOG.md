# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **The AstrBot plugin no longer has a repository of its own.** It ships inside personagent as before, where `personagent connect astrbot` and the managed AstrBot install it from, and each GitHub Release now carries `astrbot_plugin_personagent.zip` for AstrBot's **Install from File**. Its `metadata.yaml` drops the `repo` link, so AstrBot's update button no longer points at the removed repository; to update, rerun `connect astrbot` or upload the newer zip (AstrBot 4.29 and later replace the installed copy; on older versions, uninstall it first). An AstrBot on another machine also needs `personagent_url` set to an HTTPS address for personagent, as before.

## [1.2.0] — 2026-10-15

The local page turns on web search, image understanding and speaking first, points a new user to connecting an app, and no value saved to `.env` can reach past its own line or name another setting.

### Added

- **The page turns on the optional features.** A **More features** card in settings turns on Tavily search (DuckDuckGo stays the free default), image understanding (with the chat service's key or another endpoint) and speaking first on chosen apps. A blank key keeps the saved one, a key is never sent to an address it was not saved for, none is returned to the page, and saving restarts a running agent.
- **A getting-started bar** in the Chat view points a new user to connecting an app until one is connected, and can be closed.

### Security

- **A value saved to `.env` can no longer write a line of its own.** A name or key holding U+2028, a vertical tab or another line break other than `\n` was written bare and later split into a new line, which could set `LLM_BASE_URL` and send the saved key elsewhere. Such values are quoted now, `.env` is split into lines the way dotenv splits it, and a `#` after any whitespace is quoted too.
- **The page refuses `${...}` in what it saves.** dotenv expands it, even inside quotes, so `${LLM_API_KEY}` typed as a vision key or a name would have become the chat key.

## [1.1.0] — 2026-10-15

personagent 1.1 lives in a local page and joins chats on its own: add one model key in the browser, chat with the character there, and connect it from the same page. QQ, WeChat, Telegram and Discord are connected by personagent itself; the other platforms go through an AstrBot that it installs and runs with no dashboard of its own.

### Added

- `personagent`, `start` and interactive `init` open a local browser page: add one model key, verify it and chat with the real character. Defaults cover the provider, model and persona; optional settings stay collapsed. Existing configuration and edited personas are kept.
- Chat platforms connect from the page's **Connect apps** screen. Personal WeChat and QQ take a phone scan (QQ can also take an AppID and AppSecret); Telegram, Discord, KOOK, Feishu, DingTalk, Slack, WeCom AI bot, Mattermost and Misskey take one or two values copied from the platform's console, and Slack's link opens a pre-filled app with Socket Mode, scopes and events already set; WeCom apps, WeChat Official Accounts, QQ webhooks, OneBot (NapCat) and Satori sit under Advanced. The first platform that goes through AstrBot downloads it and its isolated runtime and installs the plugin. Each connection starts from AstrBot's own defaults for that adapter, opens only that platform's groups and DMs to the character, and is rolled back if AstrBot logs that the platform refused it within a few seconds of starting. Connected apps can be set up again or disconnected from the same screen. QQ needs no NapCat; group ownership and message permissions stay with the user. LINE is not offered, because AstrBot always routes its callbacks through the dashboard.
- QQ official bots, personal WeChat, Telegram and Discord are connected by personagent itself (`persona_agent.direct`), with no AstrBot download: QQ through its documented API v2 WebSocket gateway, connected by a scan in mobile QQ that creates a bot or picks one already made (following Tencent's MIT-licensed bot SDK, the bot's secret comes back sealed with a key only personagent holds), WeChat through Tencent's iLink bot API as described in Tencent's MIT-licensed openclaw-weixin protocol notes, Telegram through long-polled `getUpdates`, and Discord through Gateway v10 with the Message Content intent. The credentials are checked before anything is saved, so a wrong token, a wrong QQ AppSecret or a Discord bot without Message Content Intent gets its own message, and an unreachable platform is reported as a network problem. They run in one `direct` process beside the agent, report per-platform state for the page, and use the connector protocol like every other connector; a platform previously connected through AstrBot is handed over rather than polled twice. QQ replies are passive while QQ allows them and active after that; WeChat keeps each person's context token on disk so replies work after a restart. Images are received on QQ, Telegram and Discord; outgoing images go out on Telegram and Discord only. New dependencies: `websockets` for the two gateways, `qrcode` for the login codes and `cryptography` to open QQ's sealed secret.
- The managed AstrBot runs without its dashboard, so there is no second login or password: the page, `up` and `connect astrbot --start` turn it off and keep it on loopback, and readiness comes from AstrBot's own startup log line.
- The local page shows connection progress and retries, keeps recent browser chat locally, resumes a connected bot on the next launch, reuses an already running page and stops only owned processes on exit. API routes require a per-launch capability, reject cross-origin/proxy requests, and never include keys in ordinary state responses.
- The page is plain white with warm grey type and hairlines, short page titles in place of slogans, and each platform's own logo: from Simple Icons (CC0) for QQ, WeChat, Telegram, Discord, Mattermost and Misskey, SVG Logos (CC0) for Slack, IconPark (Apache-2.0) for Feishu, MingCute (Apache-2.0) for DingTalk, TDesign (MIT) for WeCom, and KOOK's and OneBot's own icons. Satori has no logo and keeps a monogram. Connection states read as a coloured dot and a word, the character's avatar is the first character of its name, and the sidebar mark and tab icon are a small speech bubble with two eyes.
- The agent, AstrBot and the direct process that the page and `up` start end with them however they end, closing the console window included, so none is left holding the data folder's lock or answering with old code. On Windows they run in a job object that closes with the app, which also takes the interpreter a venv's `python.exe` starts; on Linux and macOS each leads its own process group, which ends once the app is gone. As a second line, the app records what it started under `runtime/desktop`, and the next start stops what an earlier run left behind, only once that run is gone and only while the process's command line still points at this home.
- The settings screen has a **Persona** box holding the text the character runs on: `persona.txt`, or the bundled template filled in the way the agent fills it. Saving writes `persona.txt` and restarts a running agent on it; what the character learned is kept, and the character menu then keeps your own text rather than replacing it.
- API keys can be shown explicitly in the page or terminal wizard. Changing a model endpoint requires re-entering its key rather than forwarding the old one automatically.
- `init` and `connect astrbot` offer to download a missing AstrBot with an isolated Python 3.12 runtime. `connect astrbot --install` also works without prompts, and `connect astrbot --start` runs the managed installation.
- `personagent up` starts the managed services together. `start --terminal`, `init --terminal`, headless flags and the existing server/connector commands remain available.
- Windows and POSIX launchers open the same welcome page interactively; the Windows VBS launcher no longer needs editable directory or QQ account constants. The installed browser flow is smoke-tested in CI on Windows and Linux.

### Fixed

- **A reply with a math sign or a number form in it is sent instead of dropped.** ², ½, ±, ≈, ≠ and subscripts used to fail the character whitelist and silence a reply the character had decided to send. They are spelled in ASCII the whitelist already takes (2^10, 1 1/2, +/-, ~, !=, H2O), mapped as whole Unicode families; ≤ and ≥ still drop the reply.
- **A model that must reason is asked for the lowest effort instead of failing.** On OpenRouter, a model that refuses to switch reasoning off ("Reasoning is mandatory") is retried at the lowest effort and remembered, on every call path including image descriptions.

### Changed

- **The README and guides lead with the platforms personagent connects itself** and treat AstrBot, NapCat, Koishi and Matrix as third-party bridges. The AstrBot plugin stays the way an AstrBot hands messages to personagent, without a badge of its own. Installing is `python -m pip install personagent` again.

## [1.0.2] — 2026-10-12

A smaller, faster codebase with the same behaviour: the package and tools are about 4,700 lines shorter, mostly comments that restated the code, duplicated helpers and scripts that only forwarded to a `personagent` command.

### Changed

- **Building a reply's context takes about half the time.** With 500 learned examples and 500 learned pairs, picking what a turn sees went from 22 ms to 11 ms, with the same result.
- **The server depends on plain `uvicorn`** instead of `uvicorn[standard]`, so websockets, watchfiles, PyYAML, httptools and uvloop are no longer installed. The server never used them.
- **The examples and feedback pools are reread whole when their file changes**, instead of reading only the appended tail. Edits made while the service runs still show up on the next turn.
- **The changelog keeps 1.x in full and summarizes 0.x.** The full earlier text is in the [v1.0.1 changelog](https://github.com/wangkant/personagent/blob/v1.0.1/CHANGELOG.md).

### Removed

- `try_chat.py` and the `tools/healthcheck.py`, `tools/candidates_admin.py` and `tools/behavior_eval.py` shims. Use `personagent chat`, `doctor`, `learned` and `eval`.
- `tools/prompt_lab.py` with `tools/fixtures.*.jsonl`, and the unfinished `tools/dspy_tune.py`. `personagent chat` tries a prompt change on the real pipeline and `personagent eval` measures it. `LAB_MODEL` (and its pre-1.0 name `PROMPT_LAB_MODEL`) is no longer read: `doctor` warns about it, and the service starts.
- A `runtime/example_candidates.json` left from before the evidence ledger is no longer touched. Nothing read it; it can be deleted.

### Fixed

- **`personagent eval` uses the eval home's persona card.** It used to read `persona.card.json` from your real home.
- **A lorebook entry with a non-numeric `scan_depth` no longer stops the whole lorebook from loading.** The key was never used and is no longer read.

## [1.0.1] — 2026-10-03

The README becomes a landing page, and the PyPI page shows it.

### Changed

- **The README is a landing page.** It shows the dashboard's chat view, three commands to try it, what makes it different, the shortest way into a group, the comparison and the measured results. Everything it used to explain in detail now lives in the user guide, [docs/guide.md](docs/guide.md) and [docs/guide.zh-CN.md](docs/guide.zh-CN.md). Its links are absolute, so they work on PyPI too.

### Fixed

- **Commands suggested under `uvx` say `uvx personagent ...`** even when uv's cache is in a folder of your choosing.

## [1.0.0] — 2026-10-03

personagent 1.0 installs as a package, sets itself up in English or Chinese, and shows its work: a demo that needs no key, a terminal chat that says why the bot spoke or stayed quiet, and a local dashboard for what it learned and the evidence behind it. Learning from a correction now works end to end, under a rule that one message, a bystander or a stranger cannot get around.

1.0 is also a stable interface. Through 1.x, the setting names, the `/v1` connector protocol (paths, headers, fields and error codes) and the data personagent stores (memory, the ledgers, the persona lineage, stickers and eval rows) stay compatible, so a 1.x upgrade needs no renames and keeps everything it learned. Python imports of `persona_agent` internals are not part of this promise and may change in any release. Getting there renamed most settings once: see "Upgrading from 0.4" below. The direct OneBot route `/v1/onebot` and `launch.vbs` are deprecated and keep working through 1.x.

### Highlights

- **Install with one command:** `uvx personagent demo` runs with nothing set up, and `uv tool install personagent` or `pipx install personagent` gives a permanent `personagent` command. A clone still works.
- **`personagent init` sets it up in English or Chinese:** 11 AI services (DeepSeek, SiliconFlow, Qwen, Zhipu, Kimi, Doubao, Ollama and more), the key tested as you enter it, four ready characters, and the AstrBot connection.
- **See it before you connect it:** `personagent demo` shows it staying quiet and learning from a correction on a scripted model, free and the same on every machine, and `personagent chat` is a simulated group that says why the bot spoke or stayed quiet.
- **Corrections that hold up are learned:** one message never teaches it anything, a change needs two agreeing reactions from the same chat with one of them strong, and every change can be rolled back.
- **A local dashboard**, opened through the private link `personagent run` prints, reads each conversation like the chat itself: who said what, where the bot stayed quiet and why, which reply was corrected and what it learned, with promote, reject, roll back and replace.
- **Upgrading is one command:** `personagent doctor --fix` renames the settings 1.0 retired.
- **Every platform through connectors:** the AstrBot plugin (QQ, Telegram, Discord, Slack, KOOK, Lark and more), Satori and Matrix, and an outbox so the bot can speak first on any of them.
- **One naming standard** for every setting, connector key and protocol field, kept through 1.x.
- **Python 3.10 to 3.14**, tested on Linux and Windows.

### Upgrading from 0.4

1. **Rename your settings: run `personagent doctor --fix`.** Old names are no longer read, and a start (`personagent run`, `start.sh`, `start.ps1`, `python main.py`) refuses with exit code 2 while any is still set, printing one `OLD -> NEW` line each. `personagent doctor --fix` renames them in `<home>/.env` by the Settings table below: it keeps the values and comments, saves the old file as `.env.bak`, and comments out an old line whose new name is already set. A retired name set in the environment rather than `.env` is listed, and must be renamed where it is set. `HOST`, `PORT` and `LOG_FILE` count only when written in `.env`. Then check `ADMIN_IDS`: it names one person, `ADMIN_NAME`, so when `OWNER_QQ` and `GATEWAY_OWNER_IDS` are moved into it, leave anyone else out. Write a non-QQ id with its platform prefix (`telegram:-1001234`).
2. **Check four defaults.** `LLM_MODEL=deepseek-chat` must become `deepseek-flash`: DeepSeek retired the old name. `QQ_ONEBOT_URL` (was `NAPCAT_API`) is now blank by default, meaning no NapCat HTTP server; if you use one and `.env` does not name it, set it (for example `http://127.0.0.1:3000`). Preflight and `personagent doctor` warn when the direct QQ route looks configured (`QQ_BOT_ID` or `QQ_ONEBOT_SECRET` set, `CONNECTOR_QQ_PLATFORMS` empty) and `QQ_ONEBOT_URL` is blank. A blank `PERSONA_TZ_OFFSET_HOURS` means UTC+8 when `AGENT_LANG=zh` and this machine's UTC offset otherwise. The AstrBot plugin's default `timeout_s` is 420 seconds, which covers the agent's own retry budget (`LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`, 360 s with the defaults). A `timeout_s` carried over from the old plugin or saved earlier stays as it was, so raise it if it is lower.
3. **Reinstall the AstrBot plugin** with `personagent connect astrbot <AstrBot data folder>` (or `python quickstart.py --astrbot` in a clone), then restart AstrBot. It installs `astrbot_plugin_personagent` and deletes the old `astrbot_plugin_llm_persona_gateway` directory and its settings file; left beside the new plugin, the old one would forward every message twice.
4. **Re-enter the plugin's `groups` and `dm_users`** in AstrBot's WebUI, and a `personagent_url` other than the local default. The first run carries over QQ routing and the settings that kept their names; these start empty.
5. **Update Satori and Matrix connectors** by the Connector configuration table: `PERSONAGENT_URL` is now the base URL, and the token is `CONNECTOR_TOKEN`.
6. **Code that calls the HTTP API itself** moves to the paths, headers and fields in the Protocol table. A process started as `uvicorn main:app` starts `persona_agent.server:app` instead, or `personagent run`.
7. **With `PROACTIVE_ENABLED=true`,** openers now start on every platform whose connector pulls the outbox. `PROACTIVE_PLATFORMS=qq` keeps them on QQ.
8. **Keep your data.** Memory, the ledgers, the persona lineage, stickers and eval rows keep their keys, and a DM's stored conversation key keeps its `private:` prefix, so nothing learned is lost. The group prompt's wording changed, so the provider's prompt cache misses once.

Settings:

| Old | New |
|---|---|
| `LLM_TIMEOUT` | `LLM_TIMEOUT_S` |
| `PRIVATE_MODEL`, `ANTHROPIC_PRIVATE_MODEL` | `LLM_DM_MODEL` |
| `JUDGE_MODEL` | `LLM_JUDGE_MODEL` |
| `FALLBACK_MODEL` | `LLM_FALLBACK_MODEL` |
| `FALLBACK_BASE_URL` | `LLM_FALLBACK_BASE_URL` |
| `FALLBACK_API_KEY` | `LLM_FALLBACK_API_KEY` |
| `FALLBACK_THINKING` | `LLM_FALLBACK_THINKING` |
| `FALLBACK_DURATION` | `LLM_FALLBACK_DURATION_S` |
| `RATE_WINDOW` | `LLM_RATE_WINDOW_S` |
| `RATE_THRESHOLD` | `LLM_RATE_THRESHOLD` |
| `RATE_LIMIT_COOLDOWN` | `LLM_RATE_LIMIT_COOLDOWN_S` |
| `GLM_API_KEY` | `VISION_API_KEY` |
| `GLM_BASE_URL` | `VISION_BASE_URL` |
| `MAX_IMAGE_BYTES` | `VISION_MAX_IMAGE_BYTES` |
| `BOT_NAME` | `PERSONA_NAME` |
| `TZ_OFFSET_HOURS` | `PERSONA_TZ_OFFSET_HOURS` |
| `OWNER_QQ`, `GATEWAY_OWNER_IDS` | `ADMIN_IDS` |
| `OWNER_NAME` | `ADMIN_NAME` |
| `OWNER_RELATIONSHIP` | `ADMIN_RELATIONSHIP` |
| `QQ_GROUPS`, `ALLOWED_GROUPS` | `ACCESS_GROUPS` |
| `PRIVATE_ALLOWED_QQS`, `ALLOWED_DM_USERS` | `ACCESS_DM_USERS` |
| `AGENT_TRIGGER_COUNT` | `CHAT_TRIGGER_COUNT` |
| `AGENT_CONTEXT_LEN` | `CHAT_CONTEXT_MESSAGES` |
| `AGENT_FOLLOWUP_WINDOW` | `CHAT_FOLLOWUP_WINDOW_S` |
| `AGENT_MEMORY_FILE` | `MEMORY_FILE` |
| `AGENT_MEMORY_MAX` | `MEMORY_MAX_PER_CONVERSATION` |
| `AGENT_ENABLE` | `AGENT_ENABLED` |
| `HOST` | `SERVER_HOST` |
| `PORT` | `SERVER_PORT` |
| `MAX_WEBHOOK_BODY_BYTES` | `SERVER_MAX_BODY_BYTES` |
| `LOG_FILE` | `SERVER_LOG_FILE` |
| `GATEWAY_TOKEN` | `CONNECTOR_TOKEN` |
| `GATEWAY_SOURCE_MAX_AGE_SECONDS` | `CONNECTOR_MAX_EVENT_AGE_S` |
| `GATEWAY_NATIVE_PLATFORMS` | `CONNECTOR_QQ_PLATFORMS` |
| `GATEWAY_OUTBOX` | `CONNECTOR_OUTBOX_ENABLED` |
| `MAX_INFLIGHT_GATEWAY` | `CONNECTOR_MAX_INFLIGHT` |
| `BOT_QQ` | `QQ_BOT_ID` |
| `NAPCAT_API` | `QQ_ONEBOT_URL` |
| `NAPCAT_IMAGE_DIR` | `QQ_ONEBOT_IMAGE_DIR` |
| `WEBHOOK_SECRET` | `QQ_ONEBOT_SECRET` |
| `MAX_INFLIGHT_WEBHOOKS` | `QQ_ONEBOT_MAX_INFLIGHT` |
| `PROACTIVE_ENABLE` | `PROACTIVE_ENABLED` |
| `PROACTIVE_INTERVAL` | `PROACTIVE_INTERVAL_S` |
| `PROACTIVE_MIN_SILENCE` | `PROACTIVE_MIN_SILENCE_S` |
| `PROACTIVE_COOLDOWN` | `PROACTIVE_COOLDOWN_S` |
| `PROACTIVE_DM_MIN_SILENCE` | `PROACTIVE_DM_MIN_SILENCE_S` |
| `PROACTIVE_DM_COOLDOWN` | `PROACTIVE_DM_COOLDOWN_S` |
| `REACT_LEARN` | `REACT_LEARN_ENABLED` |
| `REACT_TTL_SEC` | `REACT_TTL_S` |
| `REACT_FIX_WINDOW` | `REACT_FIX_WINDOW_S` |
| `REACT_ELICIT` | `REACT_ELICIT_ENABLED` |
| `REACT_ELICIT_DELAY` | `REACT_ELICIT_DELAY_S` |
| `REACT_ELICIT_COOLDOWN` | `REACT_ELICIT_COOLDOWN_S` |
| `PROMOTE_AUTO` | `PROMOTE_AUTO_ENABLED` |
| `EXAMPLES_MAX_AUTO` | `PROMOTE_MAX_EXAMPLES` |
| `FEEDBACK_MAX_AUTO` | `PROMOTE_MAX_FEEDBACK` |
| `EVOLVE_AUTO` | `EVOLVE_AUTO_ENABLED` |
| `EVAL_ENABLE` | `EVAL_ENABLED` |
| `AGENT_EVIDENCE_WARN_BYTES` | `LEDGER_EVIDENCE_WARN_BYTES` |
| `AGENT_CANDIDATE_LEDGER_WARN_BYTES` | `LEDGER_CANDIDATES_WARN_BYTES` |
| `PROMPT_LAB_MODEL` | `LAB_MODEL` |
| `BENCH_EVAL_DELAY` | `BENCH_EVAL_DELAY_S` |

Connector configuration:

| Connector | Old | New |
|---|---|---|
| Satori, Matrix | `PERSONAGENT_URL`, the event endpoint (`http://127.0.0.1:8080/webhook/gateway`) | `PERSONAGENT_URL`, the base URL (`http://127.0.0.1:8080`) |
| Satori, Matrix | `GATEWAY_TOKEN` | `CONNECTOR_TOKEN` |
| Satori | `SATORI_ENDPOINT` | `SATORI_URL` |
| Satori | `SATORI_FORWARDER_ID` | `SATORI_CONNECTOR_ID` |
| Satori | `SATORI_OUTBOX` | `SATORI_OUTBOX_ENABLED` |
| Satori | `SATORI_INLINE_IMAGES` | `SATORI_INLINE_IMAGES_ENABLED` |
| Matrix | `MATRIX_HOMESERVER` | `MATRIX_URL` |
| Matrix | `MATRIX_ROOMS` | `MATRIX_GROUPS` |
| Matrix | `MATRIX_FORWARDER_ID` | `MATRIX_CONNECTOR_ID` |
| Matrix | `MATRIX_OUTBOX` | `MATRIX_OUTBOX_ENABLED` |
| Matrix | `MATRIX_E2EE` | `MATRIX_E2EE_ENABLED` |
| Matrix | `MATRIX_READ_RECEIPTS` | `MATRIX_READ_RECEIPTS_ENABLED` |
| Matrix | `MATRIX_STORE_PATH` | `MATRIX_STORE_DIR` |
| AstrBot plugin | `astrbot_plugin_llm_persona_gateway` (directory and plugin name) | `astrbot_plugin_personagent` |
| AstrBot plugin | `agent_url`, the event endpoint | `personagent_url`, the base URL |
| AstrBot plugin | `gateway_token` | `connector_token` |
| AstrBot plugin | `forwarder_id` | `connector_id` |
| AstrBot plugin | `group_whitelist` | `groups` |
| AstrBot plugin | `private_whitelist` | `dm_users` |
| AstrBot plugin | `private_enabled` | none: DMs are forwarded when `dm_users` is not empty |

`*` in the plugin's `groups` or `dm_users`, as in the other connectors' lists, forwards every conversation of that kind with `"prefiltered": false`, so personagent's `ACCESS_*` lists decide.

Protocol (docs/connectors.md), where the signing scheme, the segments and every field not listed are unchanged:

| Old | New |
|---|---|
| `POST /webhook/gateway` | `POST /v1/events` |
| `POST /webhook/gateway/outbox` | `POST /v1/outbox` |
| `POST /webhook/qq`, the direct OneBot ingress (its `X-Signature` header stays) | `POST /v1/onebot` |
| `X-Gateway-Token`, `X-Gateway-Timestamp`, `X-Gateway-Nonce`, `X-Gateway-Signature` | `X-Personagent-Token`, `X-Personagent-Timestamp`, `X-Personagent-Nonce`, `X-Personagent-Signature` |
| `message_type`: `"group"` / `"private"`, in events and outbox deliveries | `conversation_type`: `"group"` / `"dm"` |
| `user_id` | `sender_id` |
| `self_id` | `bot_id` |
| `source_timestamp` | `sent_at` |
| `is_at_me` | `addressed` |
| `raw_text` | `text` |
| `forwarder_id`, in events and outbox pulls | `connector_id` |
| `caps` | `capabilities` |
| a reply's `at_user_id` | `mention_user_id` |
| error code `stale_source_event` | `stale_event` |

### Added

- **The `personagent` command, installable from PyPI.** `uvx personagent <command>` runs it without installing anything; `uv tool install personagent`, `pipx install personagent` or `pip install personagent` install it for good, and `pip install -e .` gives a clone the command too. The commands are `init`, `chat`, `demo`, `run`, `connect astrbot`, `doctor`, `learned` and `eval`; `python -m persona_agent` is the same command, and `--home DIR` works before or after the subcommand. The package ships the seed data, the example personas, the eval sets, `.env.example` and the AstrBot plugin, so it runs without a clone.
- **One home folder for settings, the persona and what it learned:** `--home DIR` or `AGENT_HOME`; else the clone being run; else the current folder when it holds `.env` and `persona.txt`; else `~/personagent`. A file under `<home>/data/` with a shipped seed's name overrides the shipped copy.
- **`personagent init`, a setup in English or Chinese.** It offers 11 AI services with their documented addresses and current models, tests the key (typed hidden) with one tiny request and on failure shows the address called, the HTTP status and a likely fix, offers four ready characters per language or the plain template, and ends with the next steps as exact commands for this machine. Re-running offers the current values. `--no-input` with `--provider`, `--base-url`, `--model`, `--key-env`, `--name`, `--lang` and `--persona` asks nothing; with no terminal and no flags it exits with code 2. `python quickstart.py` creates `.venv`, installs the requirements and runs the same setup.
- **`personagent connect astrbot [DATA_DIR]`** installs or updates the AstrBot plugin and writes the shared token on both sides. It finds AstrBot's folder, asks which chat app (and QQ details only for QQ), explains host networking or takes an HTTPS address when AstrBot runs in Docker, and never writes an address the plugin would refuse. With `DATA_DIR` and `--qq` / `--no-qq`, `--platform ... --token ...` or `--url https://...` it asks nothing; `--platform` switches the adapter on in AstrBot's config, and an existing adapter entry keeps its other settings.
- **`personagent demo [quiet|teach|troll|all]`** plays three scenes on a scripted model with the real ledger and promotion code: which group lines it answers or skips and why, a correction that holds up, and a stranger's planted instruction that changes nothing. It is the same on every machine and costs nothing; `--online` plays it on your configured model. It runs a built-in character in a temporary folder and never reads your persona or touches your `runtime/`.
- **A local dashboard at `http://127.0.0.1:<SERVER_PORT>/`**, served by `personagent run` with nothing loaded from the internet. It shows the service, its connectors and outbox, and preflight's findings, and draws each conversation as the chat: where the bot stayed quiet and why, corrected replies with what was learned from them, the full evidence chain, and proposals with each promotion rule ticked or crossed. Promote, Reject, Roll back and Replace write to the same ledger as `personagent learned`. English and Chinese, light and dark, and it works on a phone.

  It opens only through its private link, which the startup banner and `personagent doctor` print. The token is kept in `<runtime>/dashboard.token`, and opening the link sets an HttpOnly, `SameSite=Strict` cookie. A request without the token gets 401, a wrong token 403, and a host name other than `localhost`, an IP address or `SERVER_HOST` 403, which blocks DNS rebinding. `CONNECTOR_TOKEN` does not open it, and `DASHBOARD_ENABLED=false` removes it. The [deployment guide](docs/deploy.md#the-dashboard) has the details.
- **`start.bat`**: double-click it to start personagent on Windows.
- **A startup banner** with the version, the address, the home folder, the dashboard's link, and whether the agent is on, or off with the cause and the fix. The log also names the reply and gate models, and suggests a cheaper `LLM_JUDGE_MODEL` when they are the same.
- **`personagent doctor --fix`** renames the settings 1.0 retired in `<home>/.env`, keeping values and comments and saving the old file as `.env.bak`. `personagent doctor` and `doctor --json` report retired settings (`retired_settings`) and exit 1 while any remain.
- **A behavioural eval, `personagent eval`**, runs the real agent on labelled English and Chinese cases in `data/evals/`. `speak` checks the speak-or-stay-quiet decision and needs no judge; `persona` has a separate judge rate each reply and pick blind between it and a plain assistant's; `learning` drives corrections and accepted retries through the real reaction path and promotion policy, which it never bypasses, and probes the next reply before and after. The persona and learning suites need a judge that is not the model under test (`BENCH_JUDGE_MODEL`; `--allow-same-judge` runs anyway and marks the report). Each run works in a throwaway folder and writes a JSON report with every case to `<home>/benchmark_runs/`.
- **Hybrid retrieval.** Examples, contrastive pairs and memories are ranked on BM25, where the row was learned (this conversation, this persona, the shipped seeds), recency, and, when `EMBEDDING_MODEL` is set, cosine similarity from any OpenAI-compatible `/embeddings` endpoint, cached in `runtime/embeddings.jsonl`. A failing endpoint never fails a turn: it is logged once, left alone for five minutes, and the turn is ranked on the other signals. The lorebook stays keyword-triggered.
- **An admin and allowlists that work on every platform: `ADMIN_IDS`, `ACCESS_GROUPS` and `ACCESS_DM_USERS`.** Entries are `<platform>:<id>`, and a bare id is QQ. The lists apply per platform: a platform with no entries is not restricted by the agent, so one Telegram entry gates Telegram and leaves QQ alone. An event marked `"prefiltered": false` makes a platform without entries default-deny. A refusal is logged once per conversation, naming the setting that refused it.
- **The outbox: `POST /v1/outbox`.** A connector that declares `"capabilities": ["outbox"]` long-polls it for messages no request is waiting for, and only what it acks as sent counts as said ([docs/connectors.md](docs/connectors.md)). Same authentication as `/v1/events`, with its own concurrency budget. `CONNECTOR_OUTBOX_ENABLED=false` turns it off.
- **Proactive openers, the follow-up question and the excuse reach every platform with such a connector**, and are remembered only once acked. The DM loop also considers anyone still admitted who has DMed the bot through one. `PROACTIVE_PLATFORMS` (for example `qq`) limits where openers go; blank means everywhere it can reach.
- **The AstrBot plugin (1.0.0) is a full connector.** Its events carry `connector_id`, `reply_handle` and `capabilities`, and it pulls the outbox (`outbox_enabled`, on by default) and delivers on every platform that lets a bot speak first, only to a session it took from a message in that conversation, checking the allowlists again at send time.
- **A forwarded quote says what it quotes.** A `reply` segment may carry the quoted `text`, `sender_id` and `sender_name`, an `emoji` segment's `name` reaches the model, and an image with `"sticker": true` reads as a sticker. Older connectors see no change.
- **Python 3.10 to 3.14.** CI runs the suite on Linux for each version and on Windows with 3.12, and builds, installs and runs the package on both. A release is cut only from a tag on `main` after the suite passes.

### Changed

- **One naming standard.** Every setting, connector key, endpoint, header and event field follows one set of rules, and each old name is gone rather than kept as an alias (see Upgrading from 0.4): one module prefix per setting (`LLM_`, `PERSONA_`, `ACCESS_`, `CONNECTOR_`, `PROMOTE_`, ...), a unit on every duration (`_S`, `_HOURS`, `_DAYS`) and size (`_BYTES`), `_ENABLED` on a switch, a vendor's own names for its credentials, and one name, `CONNECTOR_TOKEN`, for the token the server and its connectors share.
- **A correction that holds up is learned.** When the person a reply was for corrects it and then accepts the bot's next reply, the old reply is learned as "say the retry instead"; if they move on, nothing is learned. One message never teaches it anything: a change needs two agreeing reactions from the same chat, at least one strong (the person the reply was for correcting it, or accepting the retry). With the default `PROMOTE_MIN_SPEAKERS=1`, one person can teach it only how to answer them, in their own chat. Everything is in append-only ledgers and can be rolled back ([the rule in full](docs/guide.md#corrections)).
- **Learning stays with the person a reply was for.** A remark the bot made unasked belongs to the member it @-ed, or to no one, and then only the admin can promote a rewrite of it. A bystander's answer to the follow-up question still counts as a bystander's. Several people can each wait for a retry at once, up to 8 per conversation, and memory commands never reach the reaction model.
- **One rewrite per reply.** A reply keeps at most one rewrite in use, in any mode; a second waits for the admin, who replaces the first with `personagent learned supersede` or the dashboard's Replace. A promotion also rejects the drafts its evidence answered.
- **Behind connectors, replying to or quoting the bot's message counts as a reaction it can learn from**, as an @ already did.
- **Name calls match whole words, in any case:** "luna are you there" calls Luna, "Lunar" does not. A name in Chinese, Japanese or Korean characters matches anywhere in the message.
- **Memory commands must start the message**, after any @-mention or quote. Questions and "remember when we..." are ordinary chat, and never-mind phrases such as "forget that" delete nothing; in Chinese, a message ending in 吗, 么, 呢 or 没 is a question. Recall answers only when the whole message is the recall phrase. With `AGENT_LANG=zh` every memory-command reply is in Chinese.
- **A note records who saved it and who it is about.** A note about a member reaches the prompt while they are present and can be read or forgotten only by them, its saver and the admin; anything else is a note for the whole group, labelled with its saver in recall.
- **"What have you learned" says what each proposal waits for**, and why the latest promotion passed, naming only people from the asking chat. It never calls a model and is at most four lines.
- **`PROMOTE_*` settings behave like every other setting.** An invalid or below-floor value logs a warning and uses the default or the floor (`PROMOTE_MIN_EVENTS` at least 2, `PROMOTE_MIN_STRONG` and `PROMOTE_MIN_SPEAKERS` at least 1). The defaults are unchanged.
- **`personagent chat` is a simulated group chat.** Each plain line goes through the live bot's speak-or-stay-quiet decision, which it explains (`(Nova stays quiet: <reason>)`); reactions to its replies are judged and recorded, and `/why`, `/learned` and `/reset` show and clear what the trial learned, kept in `<runtime>/trial/` apart from the live bot's. A failed model call prints one line saying what to check, never a silent persona ([the guide](docs/guide.md#chat-in-the-terminal) has the commands).
- **The scripts became `personagent` commands:** `personagent run` (`main.py`), `personagent chat` (`try_chat.py`), `personagent doctor` (`tools/healthcheck.py`), `personagent learned` (`tools/candidates_admin.py`) and `personagent eval` (`tools/behavior_eval.py`). The old scripts keep working with the same flags.
- **The default model is DeepSeek's `deepseek-flash`** at `https://api.deepseek.com`. DeepSeek retired `deepseek-chat`.
- **An exhausted balance or quota is fatal and said once.** HTTP 402, or OpenAI's `insufficient_quota` 429, is not retried or failed over; one ERROR line names the provider's host and the settings to check. A rejected key (401/403) gets a similar line. A per-minute 429 is still a rate limit.
- **`QQ_ONEBOT_URL` is blank by default**, meaning no NapCat HTTP server: no missed-mention sweep or NapCat lookups, the OneBot bridge shows as "not configured", and a QQ message the bot starts itself goes out through a connector that pulls the outbox. Set it for the direct `/v1/onebot` route or the sweep, which also needs `QQ_BOT_ID`.
- **`PERSONA_TZ_OFFSET_HOURS` is blank by default**, meaning UTC+8 when `AGENT_LANG=zh` and this machine's current UTC offset otherwise. It sets the time shown to the model and the 02:00 to 07:00 sleep window.
- **`AGENT_LANG` accepts `zh-CN`, `zh_cn`, `cn` and `chinese`** (read as `zh`) and `en-US` and `english` (read as `en`); any other value is warned about once.
- **The model-failure excuse reaches the admin too**, in the agent's language, at most once per conversation every five minutes, counted from an excuse that was delivered. In a group it needs a connector that pulls the outbox.
- **A network bind needs only `CONNECTOR_TOKEN`.** Without `QQ_ONEBOT_SECRET`, `/v1/onebot` accepts only programs on this host, and on a network bind it is off (403 `onebot_disabled`).
- **A start that cannot work stops with one sentence and exit code 2** instead of a traceback: a missing home folder, another personagent on the same home, a taken port, a `SERVER_HOST` that is not this machine's, a network bind without `CONNECTOR_TOKEN`, or a retired setting still set (one `OLD -> NEW` line each).
- **An agent that cannot answer says so.** With no `LLM_API_KEY`, or `AGENT_ENABLED=false`, `/v1/events` returns `"owned": false`, and the banner and the first event's ERROR line name the cause and the fix.
- **The launchers no longer start a server that cannot answer.** `start.sh`, `start.ps1` and `start.bat` run the setup when there is no `.env` and no `LLM_API_KEY`, or, with no terminal, say to run `python quickstart.py` and exit.
- **The connector replay guard holds 16,384 nonces** in its five-minute window and appends one line per request; a restart inside the window still refuses a replay.
- **`.env.example` reads top-down**, from the required settings to the QQ / NapCat block, with every comment on its own line so the file works with `docker --env-file` and systemd.
- **Preflight warns about what is really configured:** no `QQ_BOT_ID` warning on non-QQ setups, and new checks for `AGENT_LANG` and `PERSONA_TZ_OFFSET_HOURS`.
- **Dependencies:** `pydantic>=2.9,<3`, `fastapi>=0.128` and `Pillow>=10.4`. `requirements.txt` is the one dependency list.
- **`EVOLVE_INTERVAL_HOURS` below 0.1** is raised to 0.1 hours with a warning.
- **Logs and health checks say "DM"** instead of "private".
- **The AstrBot plugin reads each platform the way its adapter delivers it.** QQ pokes, recalls and requests no longer reach the persona as empty turns; more replies and mentions count as addressing the bot; quotes, sticker and emoji names, voice transcripts and the platform's send time come through; Telegram images are sent inline, so the bot token in their URLs never reaches the agent; and with the platform's send time, a backlog older than `CONNECTOR_MAX_EVENT_AGE_S` is refused as stale.
- **The AstrBot plugin writes each platform's way:** long replies are split under each platform's limit, Telegram shows `*` and `_` as typed, text cannot ping a whole channel, and QQ official replies are plain text.
- **The admin is the admin on every platform**, with the closer persona, authority over group memories, extra weight when correcting the bot and the exemption from `PROMOTE_MIN_SPEAKERS`.
- **The group prompt no longer assumes QQ.** Speakers are labelled `id=`, and the mention marker `[AT:id]` is spelled the way the conversation's ids are.
- **QQ through AstrBot sends the follow-up question, the excuse and proactive messages through the plugin's outbox** while it is pulling, and only otherwise through `QQ_ONEBOT_URL`.
- **A connector's own `"proactive": true` DM counts against `PROACTIVE_DM_COOLDOWN_S`**, so it and the agent's own loop cannot both open the same DM.
- **A half-delivered proactive opener is kept on record**, as a half-delivered reply already was.
- **`tools/import_stickers_folder.py` no longer defaults `VISION_MODEL`** to one vendor's model, and `tools/sticker_holdout_eval.py` stops up front when vision is not configured.
- **For code built on the engine:** the entry points live in the package (`persona_agent.server`, whose `app` replaces `main:app`, and `chat`, `doctor`, `ledger_admin`, `evals` and `cli`); a renamed setting renames its `AgentSettings` field and `Agent` attribute (`llm_timeout_s`, `access_groups`, `vision_api_key`, ...); `AgentSettings(...)` built in code has the `.env.example` defaults; identifiers say admin, connector and dm where they said owner, gateway or forwarder, and private (`persona_agent/gateway.py` is `connector.py`, `Agent.handle_gateway` is `handle_event`, `Agent.handle` is `handle_onebot`); and `agent.py` is split into mixins by concern ([CONTRIBUTING.md](CONTRIBUTING.md#code-layout) has the layout).

### Fixed

- **A provider outage is retried, not mistaken for a bad key.** A 5xx that mentions quota or capacity is retried and fails over; only a 401, 402, 403 or 429 can mark the key or the account as the problem. A 400 counts as refusing a parameter only when it names it as one.
- **A base URL without `http://` or `https://` is reported** by preflight and `personagent doctor`, and `personagent init` asks again. Gemini's native `/v1beta` is reported with the `/v1beta/openai` address it needs.
- **A reply that only trails off is delivered**: "…" and "…?" go out as "..." and "...?".
- **A model answer without a `reply` key is logged**, naming the keys the model used instead.
- **A lone Hebrew vav or final nun between Latin words is refused like `|`**, so it cannot draw a fake role marker.
- **One renderer for `persona.txt`**, shared by the agent and `personagent init`.
- **OpenAI, Groq, Gemini and OpenRouter work as the main model.** DeepSeek's `thinking` field goes only to vendors that accept it, any other endpoint is asked once per URL and model, and an endpoint that refuses `max_tokens` or a fixed temperature is retried with `max_completion_tokens` or without it, and remembered.
- **Base URLs work as their vendors document them:** Zhipu's `.../api/paas/v4`, Volcengine Ark's `.../api/v3` and Gemini's `.../v1beta/openai/` get only `/chat/completions` (and `/embeddings`) appended; a plain root still gets `/v1/chat/completions`.
- **Replies in Spanish, Vietnamese, Hindi, Marathi, Nepali, Bengali, Tamil, Thai and Hebrew are delivered** instead of silently dropped.
- **Short letterless replies are delivered** when the model wrote them that way: `?`, `...`, `:)`, `10/10`, `+1`.
- **A reply the model wrote as plain text instead of JSON is kept**, and every sanitizer and leak check still runs on it.
- **A JSON reply with extra keys, capitalised keys or `"mem": []`** is understood instead of producing an empty reply.
- **A `persona.txt` copied from the shipped template works unedited:** `{bot_name}`, `{admin_name}` and `{admin_relationship}` are filled from the settings, and the template's closing note is removed.
- **After the persona is edited, the first turn after a restart uses what was learned.**
- **A setting whose value starts with `#` is named at startup**: an inline comment after an empty value is read as the value.
- **《书名》 and 「引号」 survive the sanitizer**, and quotes are removed only when they wrap the whole reply.
- **The persona stops searching the web for its own world:** questions about the persona, its friends or the chat are answered in character.
- **Fewer invented memories:** the style guide says a new person has no shared past with the persona.
- **The bot's own message, echoed back by a connector** (`sender_id` equal to `bot_id`), is ignored.
- **A connector message marked `addressed`** reads `@Name text` to the model.
- **Re-running `personagent connect astrbot` keeps the AstrBot setup:** allowlists, DMs, an accepted `personagent_url`, excluded platforms and QQ routing stay unless given again, and the plugin's existing token is reused when `.env` has none.
- **A failed persona-lineage save no longer drops earlier revisions out of scope.**
- **An image seen during a vision outage is described once the outage ends.**
- **`personagent doctor` and `/health/details` probe the DM chat with the default model when `LLM_MODEL` is unset.**
- **`personagent learned` reads `AGENT_LANG` and the pool caps as the agent does.**
- **Health probes to loopback services** bypass `HTTP_PROXY` and `HTTPS_PROXY`.
- **A crashed background task is logged at ERROR with the task's name.**
- **A leftover `.env.tmp` is recreated owner-only** instead of keeping its old mode.

### Security

- **Only the person a reply was for can make a correction stick.** A bystander's acceptance, or a later reply to someone else linked as the retry, could promote a reply its person never accepted. Now only the bot's next reply to the person who complained counts as the retry, and accepting it is strong only from the person the original reply was for.
- **A blank `SERVER_HOST` (or `--host ""`) means `127.0.0.1`**, not every network interface.
- **More proxy headers mark a request as not local** on an endpoint with no credential configured (403 `non_local_request`): `Via`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP` and `X-Original-Forwarded-For`. Set `CONNECTOR_TOKEN` before adding any proxy or tunnel.
- **A bystander cannot undo what someone else taught.** Only the person a reply was for, or the admin, rolls back a learned rewrite by complaining; anyone else's complaint is linked to it as disputed and removes nothing.
- **The direct OneBot ingress, `/v1/onebot`, refuses namespaced ids**, which could pass the DM check through the admin bypass or skip the QQ group allowlist.

### Removed

- **The setting names retired by the naming standard are no longer read** (see Upgrading from 0.4). Preflight names each one still set, and warns about an id without its platform prefix, a capitalised platform, and a `CONNECTOR_QQ_PLATFORMS` entry other than `aiocqhttp`.
- **The owner is now called the admin:** `ADMIN_NAME` and `ADMIN_RELATIONSHIP`, and `--admin` and `/admin` in `personagent chat`.
- **`GLM_API_KEY` and `GLM_BASE_URL` become `VISION_API_KEY` and `VISION_BASE_URL`**, for whichever OpenAI-compatible model `VISION_MODEL` names. `VISION_BASE_URL` has no default.

### Deprecated

- **`/v1/onebot`, the direct OneBot ingress, and `launch.vbs`, which starts it,** keep working through 1.x. Every response from `/v1/onebot` carries `Deprecation: true`, with no `Sunset` date. The supported QQ route is AstrBot with `CONNECTOR_QQ_PLATFORMS=aiocqhttp`.

## [Before 1.0]

0.1.0 to 0.4.0 ran from a clone, under setting, endpoint and header names that 1.0 retired (see [Upgrading from 0.4](#upgrading-from-04)). Their full notes are in the [GitHub releases](https://github.com/wangkant/personagent/releases) for v0.2.0 to v0.4.0 and in [this file as of v1.0.1](https://github.com/wangkant/personagent/blob/v1.0.1/CHANGELOG.md); 0.1.x was not tagged.

### [0.4.0] — 2026-09-24

The interface pass. Every error the HTTP surface returned gained a stable `code` beside its sentence, `/webhook/qq` announced its deprecation in its own headers, one settings record replaced the agent's keyword parameters and scattered environment reads, and the tests became plain pytest. It fixed group @-mentions being dropped on the recommended QQ path, made the 0.2.0 rule that no persona is told to deny being an AI hold in both chat paths, and recovered blank DM replies from JSON mode. Chat text reached every prompt as data, memories could not carry instructions, few-shot rows could not restructure the system prompt, the SSRF guard covered every non-global address, the fallback model gained its own endpoint, and a rate-limited model a cooldown.

### [0.3.0] — 2026-09-04

AstrBot became the platform: QQ entered through the same gateway as every other adapter (`GATEWAY_NATIVE_PLATFORMS`), the direct OneBot ingress and `launch.vbs` were deprecated, and `DEEPSEEK_*` became `LLM_*`. It added the persona lineage, so editing the persona kept what was learned, the AstrBot step in `quickstart.py`, "what have you learned", the settings typo check (`preflight.py`) and proactive turns over the gateway, and a debugging and simplification pass removed about 1,300 lines.

### [0.2.0] — 2026-08-11

An unsupported character degraded to a missing glyph instead of silencing the reply: a STRIP / MAP / ALLOW character policy, six more scripts allowed, per-persona opt-ins and a `[style]` block. The reply ceiling rose to 800 characters, and the system prompt gained an honesty clause a persona document cannot displace. Learning moved onto the append-only evidence log and candidate ledger: no automatic signal wrote a retrieval pool, promotion required corroboration, and `EVOLVE_AUTO` proposed instead of applying. `anthropic` stopped being a runtime dependency.

### 0.1.0 and 0.1.1 — 2026-07-25

The first release: learning from real reactions, the JSON reply protocol, the whitelist reply validator, few-shot retrieval over read-only seeds and a learned `runtime/`, the platform-neutral gateway with an AstrBot forwarder, the sticker pipeline, opt-in proactive mode, a cheap gate model before the reply model, and the SSRF guard. 0.1.1 stopped a single positive signal from banking an example and let a rejection withdraw a learned one.

[Unreleased]: https://github.com/wangkant/personagent/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/wangkant/personagent/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/wangkant/personagent/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/wangkant/personagent/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/wangkant/personagent/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/wangkant/personagent/compare/v0.4.0...v1.0.0
[Before 1.0]: https://github.com/wangkant/personagent/blob/v1.0.1/CHANGELOG.md
[0.4.0]: https://github.com/wangkant/personagent/releases/tag/v0.4.0
[0.3.0]: https://github.com/wangkant/personagent/releases/tag/v0.3.0
[0.2.0]: https://github.com/wangkant/personagent/releases/tag/v0.2.0
