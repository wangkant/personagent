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

personagent is a character for your group chats: pick a ready one or write your own, and run it on any OpenAI-compatible model. Start by chatting with it in your browser, then bring it into QQ, WeChat, Telegram, Discord and a dozen more from the same local page.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="The Connect apps screen of the local page, with every platform it can join" width="960">
</p>

<p align="center"><em>Connect apps, in the same local page as setup and the character chat.</em></p>

## Why personagent

<table>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="" width="220"></td>
<td valign="top">
<strong>It knows when to stay quiet.</strong><br>
It answers when called. Otherwise a model judges whether a person would chime in.<br>
A burst of messages gets one reply.
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
One command opens a local page in your browser, in English, Chinese or eight more languages.<br>
Paste one model key to chat: ten model services are preset, and any other OpenAI-compatible one works.<br>
Connect an app with a phone scan or one or two pasted values. The Activity view shows what the character did there.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/characters.webp" alt="" width="220"></td>
<td valign="top">
<strong>It can be a ready character, or your own.</strong><br>
Seven ready personalities. Three are characters the community already draws, the DeepSeek whale girl, the GPT dragon girl and the Claude lady, with portraits that blink, think while a reply is on its way and talk when it arrives.<br>
Rewrite the persona whenever you like. What the character learned is kept.
</td>
</tr>
</table>

- Each chat has its own memory, and it forgets when asked: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian`, `Nova, what do you remember` ([memory commands](https://github.com/wangkant/personagent/blob/main/docs/guide.md#memory-commands)). What a group noted about someone follows them into their DM with it, and never the other way.
- It answers in the language the chat uses. Starter personas come in each of the page's ten languages; the bundled examples, filters and prompts are English and Chinese.
- It is measured: `personagent eval` scores when it speaks, whether it stays in character, and whether corrections stick ([results](https://github.com/wangkant/personagent#measured)).

## Start here

```sh
python -m pip install personagent
personagent
```

With [uv](https://docs.astral.sh/uv/), `uvx personagent` runs it without a separate install step. On Windows you can also download the source ZIP and double-click `start.bat`. personagent is tested on Linux with Python 3.10–3.14 and on Windows with Python 3.12.

Your browser opens on a local page. Paste a model API key and click **Verify & start chatting**; one small request checks the key. No key yet? OpenRouter's free models are preselected, and their key costs nothing. To watch it before you get any key, `personagent demo` plays three scripted scenes for free. The [getting-started guide](https://github.com/wangkant/personagent/blob/main/docs/start.md) walks through the page screen by screen.

## What it costs

personagent is free. You pay the model service you choose, at its own rates.

- **Free to start.** OpenRouter's free models allow 50 requests a day; the model can change from one request to the next, and some free providers keep what they receive. Zhipu's `glm-4.7-flash` is free as well, and Ollama runs a model on your own computer with no key.
- **What calls the model.** Every reply, and two smaller steps: deciding whether to join in when nobody called it, and judging how people react to its replies. `personagent doctor` and `personagent eval` send requests too; the [deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.md#costs) has the rest.
- **What never does.** `personagent demo` and the memory commands.

## Put it in your group

Open **Connect apps** in the local page. It groups the apps like this:

| On the page | Apps | What you need |
|---|---|---|
| Scan to connect | QQ, personal WeChat | Your phone. WeChat bots get one-to-one chats only |
| Paste one or two values | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, WeCom AI bot, Mattermost, Misskey | Values from the app's console; the page says which |
| Advanced | WeCom app, WeChat Official Account, QQ webhook, OneBot v11 (NapCat), Satori | A public address, or other software on this computer |

Credentials are checked before they are saved, and connected apps start again each time personagent starts. The scan-to-connect apps, Telegram and Discord are connected by personagent itself; the rest go through an [AstrBot](https://github.com/AstrBotDevs/AstrBot) it downloads and runs in the background, with nothing else to open. On a server, `personagent up` starts the character and every connected app without a browser. Setup for each app is in the [user guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat), and QQ from zero, step by step, in the [Chinese deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

Already running a bridge?

- **AstrBot**: `personagent connect astrbot` installs the plugin and the shared token. The [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#bridges-you-run-yourself) covers one on another machine.
- **[Koishi](https://koishi.chat)**, or any Satori server: the [Satori connector](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md).
- **[Matrix](https://matrix.org)**, with WhatsApp and Signal behind mautrix bridges: the [Matrix connector](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md).

## Coding agents

**Let one set it up.** Give the line below to a coding agent that can run commands on your computer. It asks what you want, installs personagent and starts the local page. You paste your model key into that page yourself, so the key never passes through the agent.

```text
Read https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md and set up personagent for me.
```

**Talk to your character while you work.** Once a model key is set up, Claude Code, Codex and DeepSeek Harness (`dsh`) can reach the character:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

Start a new session there (restart DeepSeek Harness first) and ask it to say something to your character. It is the same one-to-one chat and memory as the local page. On Claude Code and Codex, `--react` lets the character say a line when a turn ends. `--remove` takes everything out again. The [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#coding-agents) covers permissions, what `--react` sends to your model service, and other MCP tools.

## Measured

`personagent eval` drives the real agent through labelled chat moments. The latest run, on 2026-10-18, was measured on 1.3.0: the shipped character on two models through OpenRouter, every case tried three times, with Claude Opus 5.5 judging blind. English / Chinese:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Right about when to speak (60 moments) | 83% / 80% | 93% / 91% |
| Plays the character better than the same model given only its prompt (40 moments) | 63% / 58% | 75% / 53% |
| Uses what a correction taught in a later, differently worded message | 76% / 56% | 71% / 67% |

- It rarely ignores a message meant for it. Most misses are its name used for something else, such as a cinema or a puppy.
- None of 84 corrections from trolls, bystanders or people who walked away got through.

The [full results](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) give the intervals, the misses by kind, the method and every report.

## How it compares

Projects it is often compared with, as of November 2026:

- **AstrBot** (AGPL-3.0) is a bot framework for more than a dozen platforms, with a WebUI and a large plugin market. It can reply unasked at random (10% of the time, off by default) and leaves learning to plugins.
- **MaiBot** (GPL-3.0) is a character bot for QQ, through NapCat, with a WebUI and a one-click launcher. A planner model decides how often it talks, and it picks up expressions and slang from the chat.
- **ChatLuna's character plugin** for Koishi (AGPL-3.0) joins in on rules: a fixed interval, how busy the chat is, or how long it has gone quiet.
- **ElizaOS** (MIT) is an agent framework in TypeScript for Discord, Telegram, Slack and more, where a model decides whether to respond.

What personagent has built in: it learns from how people react to its replies (corrections, rejections, retries they accepted), keeps a record of every change with a way to roll it back, and publishes an eval of how it behaves.

Where they are ahead: desktop apps with every setting in a WebUI, big plugin ecosystems, and slang, sticker packs and image memory. If you already run AstrBot or Koishi, you don't have to choose: personagent can run behind either one as the character.

## Update and uninstall

When a newer version is on PyPI, the page shows a notice with the update command for the way you installed it. With pip that is `python -m pip install -U personagent`. The home folder carries over: settings, character, what it learned and connected apps.

To remove it, first take it out of any coding agent you connected (`personagent connect claude-code --remove`, or the same with `codex` or `dsh`). Then quit personagent and run `python -m pip uninstall personagent`. Last, delete the home folder, which is `~/personagent` for an install from PyPI unless you chose another: it holds your key, the character and everything it learned, so this cannot be undone. The [full steps](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) cover uv, pipx and what to revoke.

## Privacy

Everything personagent stores stays on your machine, in one home folder: `.env` with your keys, `persona.txt`, `runtime/`, and `platforms/` with the managed AstrBot and the direct connections' credentials. The model provider you choose sees the conversations it answers, and once a day personagent asks pypi.org whether a newer version is out (`UPDATE_CHECK_ENABLED=false` stops that). Before you connect it to real people, tell them it is a bot and get their consent; the [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) lists what goes where.

## Documentation

- [User guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md): install, setup, the terminal chat, connectors, teaching it, the Activity view, troubleshooting.
- [Deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.md): running it for real: connectors, QQ, exposing the endpoints, costs, and what to check when the bot goes quiet.
- [Connector protocol](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): one signed HTTP request per message, for writing your own connector.
- [Tools](https://github.com/wangkant/personagent/blob/main/docs/tools.md): the scripts in `tools/`, for running from a clone.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Contributing](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Security policy](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Disclaimer](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## License

The code is [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang. The three character portraits are licensed under CC BY-NC-SA 4.0, with credits in [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Acknowledgements

- Other chat platforms are reached through [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) with [satori-python](https://github.com/RF-Tar-Railt/satori-python), and [matrix-nio](https://github.com/matrix-nio/matrix-nio) with the [mautrix bridges](https://docs.mau.fi/bridges/); the WeChat connection follows Tencent's [openclaw-weixin protocol notes](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md).
- Learning from reactions draws on [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) and [BlenderBot 3x](https://arxiv.org/abs/2306.04707); the lorebook follows [SillyTavern](https://github.com/SillyTavern/SillyTavern)'s World Info.
