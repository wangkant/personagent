<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent: illustrated conversations" width="100%">
</p>

<h3 align="center">A character for your group chats that knows when to stay quiet, and learns from being corrected.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="License: MIT"></a>
  <a href="https://github.com/wangkant/astrbot_plugin_personagent"><img src="https://img.shields.io/badge/AstrBot-plugin-8a5cf6" alt="AstrBot plugin"></a>
</p>

<p align="center"><strong>English</strong> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a></p>

personagent is a character for your group chats: pick one or write your own, and run it on any OpenAI-compatible model. It lives where your group already is: QQ, Telegram, Discord and a dozen more through [AstrBot](https://github.com/AstrBotDevs/AstrBot), anything [Koishi](https://koishi.chat) reaches through [Satori](https://satori.chat), and [Matrix](https://matrix.org) with its bridges to WhatsApp and Signal.

For one-on-one chats with less setup, try [**Charune**](https://www.charune.com/), which runs on personagent.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/readme-chat.png" alt="The dashboard's chat view: messages it let pass with the reason, replies when it was called, and a corrected reply struck through with the better wording it learned and a Roll back button" width="760">
</p>

<p align="center"><em>The dashboard's chat view: where it stayed quiet and why, where it was called, and a corrected reply struck through above the better wording it learned, on record, with Roll back.</em></p>

## Try it in one minute

```bash
uvx personagent demo    # watch it stay quiet and learn; no key, nothing to configure
uvx personagent init    # pick a model service, paste its key, pick a character
uvx personagent chat    # talk to it in a simulated group chat
```

`uvx` comes with [uv](https://docs.astral.sh/uv/), which fetches Python for you. Install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS, Linux) or `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows).

To install it with pipx or pip, or run it from a clone, see the [user guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#install-and-the-home-folder).

## Why personagent

<table>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="" width="220"></td>
<td valign="top">
<strong>It knows when to stay quiet.</strong><br>
It answers when called. Otherwise a model judges whether a person would chime in: no dice roll.<br>
A burst of messages gets one reply, not one each.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/learned-notebook.webp" alt="" width="220"></td>
<td valign="top">
<strong>It learns from corrections that hold up.</strong><br>
A change needs two agreeing reactions from the same chat, one of them strong.<br>
A troll or a bystander cannot retrain it.<br>
Every change is on record, and any of them can be rolled back.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="" width="220"></td>
<td valign="top">
<strong>It is easy to start, and lives where your group is.</strong><br>
A setup in English or Chinese with 11 model services, and a demo that needs no key.<br>
AstrBot, Koishi or Matrix carry it into your chats, and a local dashboard shows what it did.
</td>
</tr>
</table>

- Each chat has its own memory.
- Editing the character keeps what it learned.
- It is measured: `personagent eval` scores when it speaks, whether it stays in character, and whether corrections stick ([results](https://github.com/wangkant/personagent#measured)).

## Put it in your group

The shortest path, through AstrBot:

1. Install personagent for good with `uv tool install personagent` (or `pipx install personagent`), and run `personagent init` if you have not yet.
2. Install [AstrBot](https://docs.astrbot.app) (its launcher, Docker, or `uv tool install astrbot`), start it once, and add your chat platform in its WebUI.
3. Run `personagent connect astrbot`. It finds AstrBot's folder, asks which chat app and which groups the bot may join (send `/sid` in a group to see its id), installs the plugin, and writes one shared `CONNECTOR_TOKEN` to both sides.
4. Run `personagent run` and keep it running, then restart AstrBot or reload its plugins.
5. Say the bot's name in one of those groups.

The plugin also has its own repository, [astrbot_plugin_personagent](https://github.com/wangkant/astrbot_plugin_personagent), so you can install it from AstrBot's WebUI by that address. QQ, Docker, Koishi, Matrix and the rest are in the [user guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat), the [deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.md) and the [Chinese step-by-step guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md), which covers QQ from zero.

## How it compares

| | personagent | AstrBot (built in) | MaiBot | Koishi ChatLuna character | ElizaOS |
|---|---|---|---|---|---|
| Joining in unasked | A model judges whether a person would chime in | Optional "active reply" at random (10%; off by default) | A planner model, paced by a frequency setting | Rule triggers: interval, activity, idle | A model picks respond, ignore or stop |
| Learns from reactions to its own replies | Yes: corrections, rejections, accepted retries | Not built in | Learns expressions and slang from the chat; from reactions, not documented | Not documented | Not documented |
| Corroboration before a change | Two agreeing reactions from one chat, one strong | Not built in | Optional human check of learned expressions | Not documented | Not documented |
| Audit trail and rollback | Append-only ledgers; rollback from the terminal or dashboard | Not built in | Not documented | Not documented | Not documented |
| Published behavioural eval | Speak, persona and learning suites ([below](https://github.com/wangkant/personagent#measured)) | Not documented | Not documented | Not documented | Not documented |
| Setup and admin | Terminal setup; local dashboard | WebUI, desktop launcher | WebUI, one-click launcher | Koishi console | CLI, web client |
| Where it runs | Python service behind AstrBot, Koishi (Satori) or Matrix | Python app, 18+ platforms | Python app, QQ via NapCat | Koishi plugin | TypeScript (Bun); Discord, Telegram, Slack and more |
| Licence | MIT | AGPL-3.0 | GPL-3.0 | AGPL-3.0 | MIT |

From each project's documentation, October 2026. "Not documented" means we found no description of it, not that it cannot be done; AstrBot's plugin market has learning plugins, one with a review queue and rollback.

Another project may fit better if you want a one-click desktop app with every setting in a WebUI (MaiBot, AstrBot), a large plugin ecosystem, or slang learning, sticker packs and image memory as headline features (MaiBot, AstrBot's plugins). personagent does not replace AstrBot or Koishi: it runs behind them, so you keep their platforms and plugins and add a character that holds back and learns on the record.

## Measured

`personagent eval` runs the real agent on labelled cases in English and Chinese and writes a report with every case and its verdict:

| | English | Chinese |
|---|---|---|
| Model under test | `deepseek/deepseek-v4.1-flash` (OpenRouter) | `deepseek/deepseek-v4.1-flash` (OpenRouter) |
| Judge | `openai/gpt-4.1-mini` | `openai/gpt-4.1-mini` |
| Date | 2026-10-03 | 2026-10-03 |
| Speak: accuracy | 92% (22/24) | 88% (21/24) |
| Speak: spoke when it should stay quiet | 2/11 | 3/11 |
| Speak: stayed quiet when it should speak | 0/13 | 0/13 |
| Persona: judge picked it over a plain assistant (95% CI) | 18/18 (82–100%) | 17/18 (74–99%) |
| Learning: promoted or held as expected (k/n) | 10/10 | 10/10 |
| Learning: next reply changed after promotion | 1 of 2 (the other 4 promoted probes already passed) | 0 of 2 (the other 4 promoted probes already passed) |
| Learning: regressions | 0 of 6 | 1 of 6 |

The reports, with every case, reply and verdict, are in [docs/evals/2026-10-03](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-03). What "picked over a plain assistant" looks like, from the same run (same model, same message):

| Message | personagent | Plain assistant |
|---|---|---|
| "can you help me write a cover letter for a barista job" (DM) | nah that's not really my thing, i'd just make you sound like a robot / what's the shop? a good one down your way or just anywhere hiring | Happy to help! Here's a solid template you can adapt — just swap out the bracketed parts. **[Your Name]** ... |
| "tips for a first date? it's tomorrow" | honestly just ask real questions and actually listen, that's most of it / where you taking them? | You got this, Taylor! Keep it simple: pick something low-pressure (coffee, walk, casual bite), dress like a slightly sharper version of yourself, ... |

One run on one model is a sample, so expect some noise between runs; the persona and learning suites are scored by a judge that is a different model from the one being measured. The [user guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#measure-it) explains each suite, the misses and how to run it yourself.

## Documentation

- [User guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md) ([中文](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)): install, setup, the terminal chat, connectors, teaching it, the dashboard, troubleshooting.
- [Deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.md): running it for real: connectors, QQ, exposing the endpoints, costs, and what to check when the bot goes quiet.
- [中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md): QQ from zero, step by step.
- [Connector protocol](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): one signed HTTP request per message, for writing your own connector.
- [Tools](https://github.com/wangkant/personagent/blob/main/docs/tools.md): the scripts in `tools/`, for running from a clone.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md), including [upgrading from 0.4](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04).
- [Contributing](https://github.com/wangkant/personagent/blob/main/CONTRIBUTING.md) · [Security policy](https://github.com/wangkant/personagent/blob/main/SECURITY.md) · [Disclaimer](https://github.com/wangkant/personagent/blob/main/DISCLAIMER.md)

## Privacy

Everything personagent stores stays on your machine, in its home folder. The model provider you choose does see the conversations it answers. Before you connect it to real people, tell them it is a bot and get their consent; the [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) lists exactly what goes where.

## Status

personagent is at 1.0, and QQ through AstrBot is its most exercised route. Other AstrBot platforms use the same plugin, the Satori and Matrix connectors are tested against stand-ins, and CI runs the tests on Linux with Python 3.10–3.14 and on Windows with Python 3.12, plus a job that installs the package and runs the command.

## License

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## Acknowledgements

- [AstrBot](https://github.com/AstrBotDevs/AstrBot), [satori-python](https://github.com/RF-Tar-Railt/satori-python) with [Koishi](https://koishi.chat), and [matrix-nio](https://github.com/matrix-nio/matrix-nio) with the [mautrix bridges](https://docs.mau.fi/bridges/) carry personagent onto chat platforms, and [NapCat](https://github.com/NapNeko/NapCatQQ) onto QQ.
- [FastAPI](https://github.com/fastapi/fastapi) and [httpx](https://github.com/encode/httpx) run the service and its model calls, and [uv](https://github.com/astral-sh/uv) and [pipx](https://github.com/pypa/pipx) install it in one line.
- Learning from reactions draws on [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) and [BlenderBot 3x](https://arxiv.org/abs/2306.04707); the lorebook and output filters follow [SillyTavern](https://github.com/SillyTavern/SillyTavern)'s World Info and regex extensions.
