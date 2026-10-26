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

<p align="center"><strong>English</strong> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

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

The browser opens on a local page with three views: **Chat**, **Connect apps** and **Character & settings**. Paste your model API key and click **Verify & start chatting**; one small request checks it. There are 10 model service presets plus any other OpenAI-compatible one, and name and personality presets for the character. The **Persona** box holds `persona.txt`; saving it restarts the agent and keeps what it learned. **More features** turns on web search, image understanding and speaking first. Running `personagent` again reuses a page that is already open. The menu at the top right shows the page in English, Chinese or eight more languages. The character answers in the language the chat uses; its built-in prompts and data are English and Chinese, so how well it does in another language depends on the model.

On Windows you can also download the source ZIP and double-click `start.bat`. Python 3.10–3.14. See the [short getting-started guide](https://github.com/wangkant/personagent/blob/main/docs/start.md); terminal commands and connectors are in the [full guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md).

## Let your coding agent set it up

A coding agent that can run commands on your computer can install and set up personagent for you. Give it this:

```text
Read https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md and set up personagent for me.
```

It asks for the character's language, name and personality, your model service and the chat apps you want, then installs personagent, creates the home folder and starts the local page. You paste your model key into that page yourself, so the key never passes through the agent. The [instructions it follows](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md) are plain Markdown you can read too.

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
What a correction teaches, like what the group calls the gym, carries into every later reply in that chat.<br>
A change needs two agreeing reactions from the same chat, one of them strong.<br>
A troll or a bystander cannot retrain it.<br>
Every change is on record, and any of them can be rolled back.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="" width="220"></td>
<td valign="top">
<strong>It is easy to start, and lives where your group is.</strong><br>
Browser setup and chat in English, Chinese or eight more languages, with 11 model services and optional advanced settings.<br>
It joins QQ, WeChat, Telegram and Discord by itself and a dozen more apps from the same page; its Activity view shows what it did.
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

`personagent eval` drives the real agent through labelled chat moments. The latest run, on 2026-10-18, put the shipped character on two models through OpenRouter, tried every case three times, and had Claude Opus 5.5 judge blind. English / Chinese:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Right about when to speak (60 moments) | 83% / 80% | 93% / 91% |
| Plays the character better than the same model given only its prompt (40 moments) | 63% / 58% | 75% / 53% |
| Uses what a correction taught in a later, differently worded message | 76% / 56% | 71% / 67% |

- It rarely ignores a message meant for it. Most misses are its name used for something else, such as a cinema or a puppy.
- In Chinese, its edge over the plain prompt is within the noise.
- Before corrections kept their lesson, which was fixed after the first run that day, only 2 of 58 later messages used it.
- No troll's, bystander's or walked-away correction got through, in 84 tries.

The [full results](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) give the intervals, the misses by kind, the method, what the numbers don't show, and every report.

## Documentation

- [User guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md) ([中文](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)): install, setup, the terminal chat, connectors, teaching it, the Activity view, troubleshooting.
- [Deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.md): running it for real: connectors, QQ, exposing the endpoints, costs, and what to check when the bot goes quiet.
- [中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md): QQ from zero, step by step.
- [Connector protocol](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): one signed HTTP request per message, for writing your own connector.
- [Tools](https://github.com/wangkant/personagent/blob/main/docs/tools.md): the scripts in `tools/`, for running from a clone.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md), including [upgrading from 0.4](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04).
- [Contributing](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Security policy](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Disclaimer](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## Privacy

Everything personagent stores stays on your machine, in one home folder: `.env` with your keys, `persona.txt`, `runtime/`, and `platforms/` with the managed AstrBot and the direct connections' credentials. The model provider you choose does see the conversations it answers, and once a day personagent asks pypi.org whether a newer version is out (`UPDATE_CHECK_ENABLED=false` stops that). Before you connect it to real people, tell them it is a bot and get their consent; the [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) lists exactly what goes where.

## Status

1.3.1 is on PyPI, released 2026-10-26. QQ is the most exercised platform, through AstrBot in 1.0 and directly since 1.1. The WeChat, Telegram and Discord connections check credentials against the real services before saving and are otherwise tested against stand-ins; the Satori and Matrix connectors are tested against stand-ins. CI runs the tests on Linux with Python 3.10–3.14 and on Windows with Python 3.12, plus jobs that install the package and drive the command and the local page.

## License

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## Acknowledgements

- Other chat platforms are reached through [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) with [satori-python](https://github.com/RF-Tar-Railt/satori-python), and [matrix-nio](https://github.com/matrix-nio/matrix-nio) with the [mautrix bridges](https://docs.mau.fi/bridges/); the WeChat connection follows Tencent's [openclaw-weixin protocol notes](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md).
- Learning from reactions draws on [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) and [BlenderBot 3x](https://arxiv.org/abs/2306.04707); the lorebook follows [SillyTavern](https://github.com/SillyTavern/SillyTavern)'s World Info.
