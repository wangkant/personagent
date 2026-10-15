<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent: illustrated conversations" width="100%">
</p>

<h3 align="center">A character for your group chats that knows when to stay quiet, and learns from being corrected.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="License: MIT"></a>
</p>

<p align="center"><strong>English</strong> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a></p>

personagent is a character for your group chats: pick one or write your own, and run it on any OpenAI-compatible model. It connects to QQ, WeChat, Telegram and Discord itself, and to KOOK, Feishu, DingTalk, Slack, WeCom, Mattermost and Misskey from the same page.

Start in a local browser chat: add one model key and say hello. When you want the character in a group, connect an app with a phone scan or one or two values.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="The Connect apps screen of the local page, with every platform it can join" width="960">
</p>

<p align="center"><em>Connect apps, in the same local page as setup and the character chat. Screenshot from a throwaway setup with a local test model.</em></p>

## Start here

Install it from PyPI and open it:

```sh
python -m pip install personagent
personagent
```

With [uv](https://docs.astral.sh/uv/), `uvx personagent` runs it without a separate install step.

The browser opens on a local page with three views: **Chat**, **Connect apps** and **Character & settings**. Paste your model API key and click **Verify & start chatting**; one small request checks it. There are 10 model service presets plus any other OpenAI-compatible one, and name and personality presets for the character. The **Persona** box holds `persona.txt`; saving it restarts the agent and keeps what it learned. **More features** turns on web search, image understanding and speaking first. Running `personagent` again reuses a page that is already open.

Want QQ? Open **Connect apps**, pick QQ and scan the code with mobile QQ: it creates a bot or picks one you already made, and personagent connects to QQ itself. Pasting the AppID and AppSecret is the fallback. Until the bot is certified, QQ lets it join only groups you own, and which group messages it receives is set in QQ.

On Windows you can also download the source ZIP and double-click `start.bat`; from a clone, run `python quickstart.py`. Python 3.10–3.14. See the [short getting-started guide](https://github.com/wangkant/personagent/blob/main/docs/start.md); terminal commands and connectors are in the [full guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md).

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
Browser setup and chat in English or Chinese, with 11 model services and optional advanced settings.<br>
It joins QQ, WeChat, Telegram and Discord by itself and a dozen more apps from the same page; a local dashboard shows what it did.
</td>
</tr>
</table>

- Each chat has its own memory.
- Editing the character keeps what it learned.
- It is measured: `personagent eval` scores when it speaks, whether it stays in character, and whether corrections stick ([results](https://github.com/wangkant/personagent#measured)).

## Put it in your group

Use **Connect apps** in the local page. Credentials are checked before they are saved.

- **Connected by personagent itself:** QQ official bots (scan with mobile QQ), personal WeChat (scan with your phone; one-to-one chats only, since WeChat gives such bots no group messages), Telegram (a BotFather token) and Discord (a bot token, with Message Content Intent on).
- **One or two values:** KOOK, Feishu/Lark (long connection), DingTalk (Stream mode), Slack (Socket Mode; the guide link pre-fills the app), WeCom AI bot (long connection), Mattermost and Misskey.
- **Advanced** (needs a public address or other software): WeCom app, WeChat Official Account, QQ webhook, OneBot v11 and Satori.

The second and third groups run through an [AstrBot](https://github.com/AstrBotDevs/AstrBot) that personagent downloads, with its own Python 3.12, and runs in the background: no dashboard, no second login.

Whatever the page or `personagent up` starts stops with it, however it ends, and anything a crashed run left behind is stopped at the next start. Everything you connected starts again the next time you open it.

From the terminal: `personagent up` runs the agent, the direct connections and the managed AstrBot together; `init --terminal` is the terminal setup; `chat` talks to the character in the terminal; `demo` shows it without a key; `run` starts the server alone; `doctor` checks the setup; `learned` reviews what it learned; `eval` measures it.

## Third-party platforms

personagent also works with bridges you may already run. None of them is needed for QQ, WeChat, Telegram or Discord.

- **AstrBot:** for an AstrBot you already run, `personagent connect astrbot` installs the [astrbot_plugin_personagent](https://github.com/wangkant/astrbot_plugin_personagent) plugin, which hands AstrBot's messages to personagent. You can also install it from AstrBot's WebUI by that address and set its `connector_token` to personagent's `CONNECTOR_TOKEN`.
- **NapCat**, or another OneBot v11 implementation, under Advanced in **Connect apps**.
- **[Koishi](https://koishi.chat)**, through the [Satori](https://satori.chat) connector.
- **[Matrix](https://matrix.org)**, and through mautrix bridges WhatsApp, Signal and more.

Setup for each is in the [user guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat) and the [deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.md); the [Chinese step-by-step guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md) covers QQ from zero.

## How it compares

| | personagent | AstrBot (built in) | MaiBot | Koishi ChatLuna character | ElizaOS |
|---|---|---|---|---|---|
| Joining in unasked | A model judges whether a person would chime in | Optional "active reply" at random (10%; off by default) | A planner model, paced by a frequency setting | Rule triggers: interval, activity, idle | A model picks respond, ignore or stop |
| Learns from reactions to its own replies | Yes: corrections, rejections, accepted retries | Not built in | Learns expressions and slang from the chat; from reactions, not documented | Not documented | Not documented |
| Corroboration before a change | Two agreeing reactions from one chat, one strong | Not built in | Optional human check of learned expressions | Not documented | Not documented |
| Audit trail and rollback | Append-only ledgers; rollback from the terminal or dashboard | Not built in | Not documented | Not documented | Not documented |
| Published behavioural eval | Speak, persona and learning suites ([below](https://github.com/wangkant/personagent#measured)) | Not documented | Not documented | Not documented | Not documented |
| Setup and admin | Browser setup and chat; local dashboard | WebUI, desktop launcher | WebUI, one-click launcher | Koishi console | CLI, web client |
| Where it runs | Python service; QQ, WeChat, Telegram and Discord directly, the rest through a managed AstrBot, or behind Koishi (Satori) or Matrix | Python app, 18+ platforms | Python app, QQ via NapCat | Koishi plugin | TypeScript (Bun); Discord, Telegram, Slack and more |
| Licence | MIT | AGPL-3.0 | GPL-3.0 | AGPL-3.0 | MIT |

From each project's documentation, October 2026. "Not documented" means we found no description of it, not that it cannot be done; AstrBot's plugin market has learning plugins, one with a review queue and rollback.

Another project may fit better if you want a one-click desktop app with every setting in a WebUI (MaiBot, AstrBot), a large plugin ecosystem, or slang learning, sticker packs and image memory as headline features (MaiBot, AstrBot's plugins). personagent does not replace AstrBot or Koishi: it can run behind one you already have, so you keep its platforms and plugins and add a character that holds back and learns on the record.

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

Everything personagent stores stays on your machine, in one home folder: `.env` with your keys, `persona.txt`, `runtime/`, and `platforms/` with the managed AstrBot and the direct connections' credentials. The model provider you choose does see the conversations it answers. Before you connect it to real people, tell them it is a bot and get their consent; the [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) lists exactly what goes where.

## Status

1.2.0 is on PyPI, released 2026-10-15. QQ is the most exercised platform, through AstrBot in 1.0 and directly since 1.1. The WeChat, Telegram and Discord connections check credentials against the real services before saving and are otherwise tested against stand-ins; the Satori and Matrix connectors are tested against stand-ins. CI runs the tests on Linux with Python 3.10–3.14 and on Windows with Python 3.12, plus jobs that install the package and drive the command and the local page.

## License

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## Acknowledgements

- [AstrBot](https://github.com/AstrBotDevs/AstrBot), [satori-python](https://github.com/RF-Tar-Railt/satori-python) with [Koishi](https://koishi.chat), and [matrix-nio](https://github.com/matrix-nio/matrix-nio) with the [mautrix bridges](https://docs.mau.fi/bridges/) carry personagent onto chat platforms, and [NapCat](https://github.com/NapNeko/NapCatQQ) through OneBot v11.
- QQ, WeChat, Telegram and Discord are reached through their own documented APIs, WeChat as described in Tencent's [openclaw-weixin protocol notes](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md); [websockets](https://github.com/python-websockets/websockets) runs the QQ and Discord gateways [python-qrcode](https://github.com/lincolnloop/python-qrcode) draws the QQ and WeChat login codes, and [cryptography](https://github.com/pyca/cryptography) opens the bot secret QQ returns sealed.
- Platform logos on the local page come from [Simple Icons](https://github.com/simple-icons/simple-icons), [SVG Logos](https://github.com/gilbarbara/logos), [IconPark](https://github.com/bytedance/IconPark), [MingCute](https://github.com/Richard9394/MingCute) and [TDesign Icons](https://github.com/Tencent/tdesign-icons), plus KOOK's and OneBot's own; each logo is its owner's trademark.
- [FastAPI](https://github.com/fastapi/fastapi) and [httpx](https://github.com/encode/httpx) run the service and its model calls, and [uv](https://github.com/astral-sh/uv) runs it with `uvx personagent`.
- Learning from reactions draws on [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) and [BlenderBot 3x](https://arxiv.org/abs/2306.04707); the lorebook and output filters follow [SillyTavern](https://github.com/SillyTavern/SillyTavern)'s World Info and regex extensions.
