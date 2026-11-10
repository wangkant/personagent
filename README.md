<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">A character for your group chats that knows when to stay quiet, and learns from being corrected.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-0969da?style=flat-square&labelColor=24292f" alt="License: PolyForm Noncommercial"></a>
</p>

<p align="center"><strong>English</strong> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

personagent is a character for your group chats: pick a ready one or write your own, and run it on any OpenAI-compatible model. Start by chatting with it on your own computer, then bring it into QQ, WeChat, Telegram, Discord and eighteen more from the same local page.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="The Connect apps screen of the local page, with every platform it can join" width="960">
</p>

<p align="center"><em>Connect apps, in the same local page as setup and the character chat.</em></p>

## Why personagent

<table>
<tr>
<td width="220" valign="top"><strong>It knows when to stay quiet.</strong></td>
<td valign="top">
It answers when called. Otherwise a model judges whether a person would chime in.<br>
A burst of messages gets one reply.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>It learns from corrections that hold up.</strong></td>
<td valign="top">
What a correction teaches, like what the group calls the gym, carries into every later reply in that chat.<br>
A troll or a bystander cannot retrain it.<br>
Every change is on record, and any of them can be rolled back.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>It is easy to start, and lives where your group is.</strong></td>
<td valign="top">
One command opens it on your computer, in English, Chinese or eight more languages.<br>
Paste one model key to chat, then connect an app with a phone scan or one or two pasted values.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>It can be a ready character, or your own.</strong></td>
<td valign="top">
Seven ready personalities. Three are characters the community already draws: the DeepSeek whale girl, the GPT dragon girl and the Claude lady, with portraits that blink, think and talk.<br>
Rewrite the persona whenever you like. What the character learned is kept.
</td>
</tr>
</table>

Each chat has its own memory, and it forgets when asked: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian` ([memory commands](https://github.com/wangkant/personagent/blob/main/docs/guide.md#memory-commands)).

## Start here

```sh
python -m pip install personagent
personagent
```

With [uv](https://docs.astral.sh/uv/), `uvx personagent` runs it without a separate install step. On Windows you can also download the source ZIP and double-click `start.bat`.

It opens in a window of its own on Windows, and in your browser on macOS and Linux. Paste a model API key and click **Verify & start chatting**. No key yet? OpenRouter's free models are preselected, and their key costs nothing. `personagent demo` plays three scripted scenes with no key at all. The [getting-started guide](https://github.com/wangkant/personagent/blob/main/docs/start.md) walks through the page screen by screen.

personagent is free. You pay the model service you choose, at its own rates. OpenRouter's free models allow 50 requests a day, and some free providers keep what they receive; Ollama runs a model on your own computer with no key.

## Put it in your group

Open **Connect apps** in the local page:

| On the page | Apps | What you need |
|---|---|---|
| Scan to connect | QQ, personal WeChat | Your phone. WeChat bots get one-to-one chats only |
| Paste one or two values | Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat, KOOK, Feishu/Lark, DingTalk, Slack, WeCom AI bot, Mattermost, Misskey | Values from the app's console; the page says which |
| Advanced | WeCom app, WeChat Official Account, QQ webhook, OneBot v11 (NapCat), Satori | A public address, or other software on this computer |

Connected apps start again each time personagent starts. The scan-to-connect apps, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK and Stoat are connected by personagent itself; the rest go through an [AstrBot](https://github.com/AstrBotDevs/AstrBot) it downloads and runs in the background. On a server, `personagent up` starts everything without a browser. Setup for each app is in the [user guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat), and QQ from zero in the [Chinese deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

Already running AstrBot, Koishi or Matrix? personagent can sit behind it as the character: see [bridges you run yourself](https://github.com/wangkant/personagent/blob/main/docs/guide.md#bridges-you-run-yourself), the [Satori connector](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md) and the [Matrix connector](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md).

## Coding agents

**Let one set it up.** Give the line below to a coding agent that can run commands on your computer. You paste your model key into the local page yourself, so the key never passes through the agent.

```text
Read https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md and set up personagent for me.
```

**Talk to your character while you work.** Claude Code, Codex and DeepSeek Harness (`dsh`) can reach the character, with the same chat and memory as the local page:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove` takes it out again, and **Coding assistants** under **Connect apps** does both from the page. The [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#coding-agents) covers permissions and `--react`, which lets the character say a line when a turn ends.

## Update and uninstall

When a newer version is on PyPI, the page shows a notice with the update command. With pip that is `python -m pip install -U personagent`. On most installations, **Update and reopen** in the page's App view runs it for you. Settings, character, what it learned and connected apps carry over. To remove it, follow the [uninstall steps](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it).

## Privacy

Everything personagent stores stays on your machine, in one home folder. The model provider you choose sees the conversations it answers, and once a day personagent asks pypi.org whether a newer version is out (`UPDATE_CHECK_ENABLED=false` stops that). Before you connect it to real people, tell them it is a bot and get their consent; the [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) lists what goes where.

## Documentation

- [User guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md): setup, connectors, teaching it, the Activity view, troubleshooting.
- [Deployment guide](https://github.com/wangkant/personagent/blob/main/docs/deploy.md): running it for real, costs, and what to check when the bot goes quiet.
- [Connector protocol](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): for writing your own connector.
- [Tools](https://github.com/wangkant/personagent/blob/main/docs/tools.md): the scripts in `tools/`, for running from a clone.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Contributing](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Security policy](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Disclaimer](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## License

personagent is licensed under the [PolyForm Noncommercial License 1.0.0](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang: free to use, change and share for noncommercial purposes, and not for commercial ones. The connectors under `integrations/` remain under the MIT License, as do versions up to 1.4.0. The three character portraits are licensed under CC BY-NC-SA 4.0, with credits in [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Acknowledgements

- Other chat platforms are reached through [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) with [satori-python](https://github.com/RF-Tar-Railt/satori-python), and [matrix-nio](https://github.com/matrix-nio/matrix-nio) with the [mautrix bridges](https://docs.mau.fi/bridges/); the WeChat connection follows Tencent's [openclaw-weixin protocol notes](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md).
- Learning from reactions draws on [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) and [BlenderBot 3x](https://arxiv.org/abs/2306.04707); the lorebook follows [SillyTavern](https://github.com/SillyTavern/SillyTavern)'s World Info.
