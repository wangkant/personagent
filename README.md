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

On Windows you can also download the source ZIP and double-click `start.bat`. Python 3.10–3.14. See the [short getting-started guide](https://github.com/wangkant/personagent/blob/main/docs/start.md); terminal commands and connectors are in the [full guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md).

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

Open **Connect apps** in the local page. It groups the apps like this:

| On the page | Apps | What you need |
|---|---|---|
| Scan to connect | QQ, personal WeChat | Your phone. WeChat bots get one-to-one chats only |
| Paste one or two values | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, WeCom AI bot, Mattermost, Misskey | Values from the app's console; the page says which |
| Advanced | WeCom app, WeChat Official Account, QQ webhook, OneBot v11 (NapCat), Satori | A public address, or other software on this computer |

Credentials are checked before they are saved, and connected apps start again each time personagent starts. personagent connects QQ, WeChat, Telegram and Discord itself; the rest go through an [AstrBot](https://github.com/AstrBotDevs/AstrBot) it downloads and runs in the background, with nothing else to open. On a server, `personagent up` starts the character and every connected app without a browser.

**Already running AstrBot, Koishi or Matrix?** For an AstrBot on this computer, `personagent connect astrbot` installs the plugin and the shared token. For one on another machine, upload `astrbot_plugin_personagent.zip` from the [latest release](https://github.com/wangkant/personagent/releases/latest) under **Install from File** on its plugin page, then set its token and personagent's HTTPS address as the guides below describe. [Koishi](https://koishi.chat) joins through the [Satori connector](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md), and [Matrix](https://matrix.org), with WhatsApp and Signal behind mautrix bridges, through the [Matrix connector](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md).

Setup for each is in the [user guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat) and the [deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.md); the [Chinese step-by-step guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md) covers QQ from zero.

## How it compares

The projects people usually weigh it against, going by each one's documentation in October 2026:

- **AstrBot** (AGPL-3.0) is a bot framework for 18+ platforms, with a WebUI and a large plugin market. It can reply unasked at random (10% of the time, off by default) and leaves learning to plugins.
- **MaiBot** (GPL-3.0) is a character bot for QQ, through NapCat, with a WebUI and a one-click launcher. A planner model decides how often it talks, and it picks up expressions and slang from the chat.
- **ChatLuna's character plugin** for Koishi (AGPL-3.0) joins in on rules: a fixed interval, how busy the chat is, or how long it has gone quiet.
- **ElizaOS** (MIT) is an agent framework in TypeScript for Discord, Telegram, Slack and more, where a model decides whether to respond.

What personagent has built in, where the others leave it to plugins or don't describe it: it learns from how people react to its replies (corrections, rejections, retries they accepted); a change needs two agreeing reactions from the same chat, one of them strong; every change is logged and can be rolled back; and how it behaves is measured in a published eval ([below](https://github.com/wangkant/personagent#measured)).

Where they are ahead: desktop apps with every setting in a WebUI, big plugin ecosystems, and slang, sticker packs and image memory. If you already run AstrBot or Koishi, you don't have to choose: personagent can run behind either one as the character.

## Measured

`personagent eval` runs the real agent on labelled cases and keeps every case, reply and verdict. The last published run, on 2026-10-03, tested `deepseek/deepseek-v4.1-flash` through OpenRouter, with `openai/gpt-4.1-mini` as the judge:

| | English | Chinese |
|---|---|---|
| Spoke when it should, stayed quiet when it should | 22 of 24 | 21 of 24 |
| Judge picked its reply over a plain assistant's | 18 of 18 | 17 of 18 |
| Corrections applied or turned down as they should be | 10 of 10 | 10 of 10 |

- Every speaking miss was a line that named it in passing, like "it's Nova-5G now, same password" about the wifi. It never ignored a message meant for it.
- All six corrections that held up were applied, and the troll, bystander and walk-away cases were all turned down. Most applied ones changed little, since the model already answered those in character; one Chinese reply got worse after its correction.

The same message, from the same run and the same model:

**riley (DM):** can you help me write a cover letter for a barista job

| personagent | Plain assistant |
|---|---|
| nah that's not really my thing, i'd just make you sound like a robot<br><br>what's the shop? a good one down your way or just anywhere hiring | Happy to help! Here's a solid template you can adapt — just swap out the bracketed parts.<br><br>**[Your Name]** … |

One run on one model is a sample, so expect some noise between runs. The reports are in [docs/evals/2026-10-03](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-03), and the [user guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#measure-it) explains each suite and how to run it yourself.

## Documentation

- [User guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md) ([中文](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)): install, setup, the terminal chat, connectors, teaching it, the dashboard, troubleshooting.
- [Deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.md): running it for real: connectors, QQ, exposing the endpoints, costs, and what to check when the bot goes quiet.
- [中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md): QQ from zero, step by step.
- [Connector protocol](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): one signed HTTP request per message, for writing your own connector.
- [Tools](https://github.com/wangkant/personagent/blob/main/docs/tools.md): the scripts in `tools/`, for running from a clone.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md), including [upgrading from 0.4](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04).
- [Contributing](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Security policy](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Disclaimer](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## Privacy

Everything personagent stores stays on your machine, in one home folder: `.env` with your keys, `persona.txt`, `runtime/`, and `platforms/` with the managed AstrBot and the direct connections' credentials. The model provider you choose does see the conversations it answers, and once a day personagent asks pypi.org whether a newer version is out (`UPDATE_CHECK_ENABLED=false` stops that). Before you connect it to real people, tell them it is a bot and get their consent; the [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) lists exactly what goes where.

## Status

1.2.1 is on PyPI, released 2026-10-17. QQ is the most exercised platform, through AstrBot in 1.0 and directly since 1.1. The WeChat, Telegram and Discord connections check credentials against the real services before saving and are otherwise tested against stand-ins; the Satori and Matrix connectors are tested against stand-ins. CI runs the tests on Linux with Python 3.10–3.14 and on Windows with Python 3.12, plus jobs that install the package and drive the command and the local page.

## License

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## Acknowledgements

- Other chat platforms are reached through [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) with [satori-python](https://github.com/RF-Tar-Railt/satori-python), and [matrix-nio](https://github.com/matrix-nio/matrix-nio) with the [mautrix bridges](https://docs.mau.fi/bridges/); the WeChat connection follows Tencent's [openclaw-weixin protocol notes](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md).
- Learning from reactions draws on [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) and [BlenderBot 3x](https://arxiv.org/abs/2306.04707); the lorebook follows [SillyTavern](https://github.com/SillyTavern/SillyTavern)'s World Info.
