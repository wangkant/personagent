<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">一个知道什么时候该安静、能从别人的纠正里学习的群聊角色。</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-0969da?style=flat-square&labelColor=24292f" alt="License: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <strong>简体中文</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

personagent 是放进群聊里的一个角色：选一个现成的或自己写一个，接上任意 OpenAI 兼容的模型就能用。先在自己电脑上和它聊，再从同一个本地页面把它带进 QQ、微信、Telegram、Discord 和另外十几个平台。

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.zh-CN.jpg" alt="本地页面的「连接平台」：能接入的平台一目了然" width="960">
</p>

<p align="center"><em>「连接平台」和设置、角色聊天在同一个本地页面里。</em></p>

## 为什么用它

<table>
<tr>
<td width="220" valign="top"><strong>知道什么时候该安静</strong></td>
<td valign="top">
叫它就回。没人叫时，由一个模型判断真人这时会不会接话。<br>
有人连着刷屏，它只回一条。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>只从站得住的纠正里学</strong></td>
<td valign="top">
纠正教会的事（比如群里管健身房叫什么）会带进这个聊天之后的每一句回复。<br>
一处改动要同一个聊天里两条一致的反应，其中一条是强证据。<br>
捣乱的人、旁观者都教不坏它。<br>
每一处改动都有记录，哪一处都能撤回。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>上手快，你的群在哪它就去哪</strong></td>
<td valign="top">
一条命令就在电脑上打开它，页面有中文、英文和另外八种语言。<br>
填一个模型 Key 就能聊：预设了十家模型服务，其他 OpenAI 兼容的服务也能用。<br>
接入一个平台，用手机扫一次码或粘贴一两项就行。在「动态」里能看到角色在那边做了什么。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>现成角色可以挑，也能自己写</strong></td>
<td valign="top">
七个现成性格。其中三个是社区里早就有人画的角色：DeepSeek 鲸鱼娘、GPT 娘（白龙）和 Claude 娘，立绘会眨眼，等回复时在想，回复到了就开口说话。<br>
人设随时可以改写，角色学到的东西会留着。
</td>
</tr>
</table>

- 每个聊天有自己的记忆，让它忘它就忘：`小夏，记住 阿杰不吃辣`、`小夏 忘掉 不吃辣`、`小夏 你都记得什么`（[记忆命令](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#教它)）。群里记下的关于某人的事，会跟到 TA 和角色的私聊里，反过来不会。
- 聊天用什么语言，它就用什么语言回。起步人设在页面的十种语言里都有；内置的示例、过滤规则和提示词是中文和英文。
- 效果是量过的：`personagent eval` 会给它打分，看它开口的时机对不对、有没有守住人设、纠正有没有留下来（[结果](https://github.com/wangkant/personagent/blob/main/README.zh-CN.md#效果评测)）。

## 从这里开始

```sh
python -m pip install personagent
personagent
```

装了 [uv](https://docs.astral.sh/uv/) 的话，`uvx personagent` 不用单独安装就能运行。Windows 也可以下载源码 ZIP，双击 `start.bat`，它还会在桌面上放一个 personagent 图标。personagent 在 Linux 上用 Python 3.10–3.14、在 Windows 上用 Python 3.12 测试过。

在 Windows 上，它会开一个独立的窗口；在 macOS 和 Linux 上在浏览器里打开，运行 `pip install "personagent[app]"` 之后也能开窗口。填入模型 API Key，点「验证并开始聊天」，它会发一次小请求校验 Key。还没有 Key？默认选中的是 OpenRouter 的免费模型，它的 Key 不花钱。想在拿到 Key 之前先看看效果，`personagent demo` 会免费播放三段写好的场景。[简明入门](https://github.com/wangkant/personagent/blob/main/docs/start.zh-CN.md)把页面一屏一屏讲了一遍。

## 要花多少钱

personagent 本身免费。钱付给你选的模型服务，按它自己的价格算。

- **免费起步。** OpenRouter 的免费模型每天可以请求 50 次；每次请求用的模型可能不同，有些免费服务商会保留收到的内容。智谱的 `glm-4.7-flash` 也免费；Ollama 在你自己的电脑上跑模型，不需要 Key。
- **哪些会调用模型。** 每一条回复，外加两个小步骤：没人叫它时判断要不要接话，以及判断大家对它回复的反应。`personagent doctor` 和 `personagent eval` 也会发请求；其余的见[部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md#费用)。
- **哪些从不调用。** `personagent demo` 和记忆命令。

## 接进你的群

在本地页面打开「连接平台」，平台是这样分组的：

| 页面分组 | 平台 | 要准备什么 |
|---|---|---|
| 扫码就能连 | QQ、个人微信 | 手机。微信机器人只能一对一聊天 |
| 粘贴一两项 | Telegram、Discord、KOOK、飞书、钉钉、Slack、企业微信智能机器人、Mattermost、Misskey | 从平台后台复制，页面会说复制哪一项 |
| 高级 | 企业微信应用、微信公众号、QQ（Webhook）、OneBot v11（NapCat）、Satori | 公网地址，或本机的其他软件 |

填的凭据先校验，通过才保存；连好的平台以后每次启动 personagent 都会自动连上。扫码连接的平台、Telegram 和 Discord 由 personagent 自己连接；其余平台经它在后台下载并运行的 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 接入，不用另外打开什么。在服务器上，`personagent up` 不开浏览器就能启动角色和所有连好的平台。各平台的设置方法见[使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#接进聊天平台)；从零接 QQ，一步一步的做法见[部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)。

已经在跑桥接了？

- **AstrBot**：`personagent connect astrbot` 会装好插件、配好共享口令。AstrBot 在另一台机器上的做法见[手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#你自己运行的桥接)。
- **[Koishi](https://koishi.chat)** 或任何 Satori 服务：用 [Satori 连接器](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.zh-CN.md)。
- **[Matrix](https://matrix.org)**（可经 mautrix 桥接 WhatsApp、Signal）：用 [Matrix 连接器](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.zh-CN.md)。

## 编程助手

**让编程助手帮你装。** 把下面这句话发给能在你电脑上运行命令的 AI 编程助手。它会先问你想要什么，然后安装 personagent、启动本地页面。模型 Key 由你自己填进那个页面，不经过助手。

```text
读 https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md ，然后帮我把 personagent 装好并设置好
```

**写代码时和角色说话。** 配好模型 Key 之后，Claude Code、Codex 和 DeepSeek Harness（`dsh`）都能找到你的角色：

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

在那边开一个新会话（DeepSeek Harness 要先重启），让它对你的角色说句话。这和本地页面是同一个一对一聊天，记忆也相同。在 Claude Code 和 Codex 上加 `--react`，角色可以在一轮结束时说一句话。`--remove` 会把这些全部撤掉。权限、`--react` 会把什么发给你的模型服务、其他 MCP 工具怎么接，见[手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#编程助手)。

## 效果评测

`personagent eval` 用标注好的聊天场景驱动真实的 agent。最近一次在 2026-10-18，测的是 1.3.0：随包附带的角色、两个模型（经 OpenRouter），每个用例跑 3 遍，由 Claude Opus 5.5 盲判。中文 / 英文：

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| 该不该开口，判对的比例（60 个场景） | 80% / 83% | 91% / 93% |
| 比同一个模型直接贴人设演得好（40 个场景） | 58% / 63% | 53% / 75% |
| 纠正教过的事，之后换个说法再问能用上 | 56% / 76% | 67% / 71% |

- 该它回的话几乎不漏；错的大多是它的名字指的是别的东西，比如一家影城、一只小狗。
- 捣乱的人、旁观者、说完就走的人做的 84 次纠正，一次都没有混进来。

[完整结果](https://github.com/wangkant/personagent/blob/main/docs/evals/2026-10-18/README.zh-CN.md)里有置信区间、各类错误、测法和全部报告。

## 和同类项目对比

常被拿来比较的几个项目（截至 2026 年 11 月）：

- **AstrBot**（AGPL-3.0）：机器人框架，能接十多个平台，有 WebUI 和很大的插件市场。没人叫它时可以随机回复（10% 的概率，默认关闭），学习交给插件。
- **麦麦 MaiBot**（GPL-3.0）：QQ 上的角色机器人，经 NapCat 接入，有 WebUI 和一键启动器。由一个规划模型决定多久说一次话，会从群聊里学表达方式和黑话。
- **ChatLuna 伪装群友**（AGPL-3.0）：Koishi 插件，按规则插话：固定间隔、群里的活跃度、冷场了多久。
- **ElizaOS**（MIT）：TypeScript 写的 agent 框架，支持 Discord、Telegram、Slack 等，由模型决定回不回。

personagent 自带的：从别人对它回复的反应里学（纠正、否定、被接受的重答），每处改动都有记录、可以撤回，还公开了一份行为评测。

它们更强的地方：所有设置都在 WebUI 里的桌面程序，庞大的插件生态，还有黑话、表情包和图片记忆。已经在用 AstrBot 或 Koishi 的话不用二选一：personagent 可以接在任何一个后面，只当那个角色。

## 更新和卸载

PyPI 上有新版本时，页面会显示一条提示，并给出和你的安装方式对应的更新命令。用 pip 装的话是 `python -m pip install -U personagent`。主目录原样保留：设置、角色、它学到的东西和连好的平台都在。

要卸载的话，先把它从你接过的编程助手里撤掉（`personagent connect claude-code --remove`，`codex` 和 `dsh` 同理）。然后退出 personagent，运行 `python -m pip uninstall personagent`。最后删掉主目录：从 PyPI 安装的话是 `~/personagent`，除非你选了别的位置。里面有你的 Key、角色和它学到的一切，删了就找不回来。uv、pipx 的做法和该撤销什么，见[完整步骤](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it)（英文）。

## 隐私

personagent 存的一切都在你自己机器上的一个主目录里：放 Key 的 `.env`、`persona.txt`、`runtime/`，以及放托管 AstrBot 和直连平台凭据的 `platforms/`。你选的模型服务商会看到它回复的对话；personagent 每天向 pypi.org 查一次有没有新版本（`UPDATE_CHECK_ENABLED=false` 可以关掉）。接入真人之前，请告诉他们这是机器人，并征得他们同意；哪些内容会发到哪里，[手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#隐私与知情同意)里都列着。

## 文档

- [使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)：安装、设置、终端聊天、连接器、教它、「动态」页、排错。
- [部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)：真正跑起来要知道的事：连接器、QQ、对外暴露接口、费用，以及机器人不说话时查什么。
- [连接器协议](https://github.com/wangkant/personagent/blob/main/docs/connectors.zh-CN.md)：每条消息一个带签名的 HTTP 请求，给自己写连接器的人看。
- [工具脚本](https://github.com/wangkant/personagent/blob/main/docs/tools.zh-CN.md)：`tools/` 里的脚本，从克隆的源码运行时用。
- [更新日志](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md)（英文） · [贡献指南](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md)（英文） · [安全策略](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md)（英文） · [免责声明](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.zh-CN.md)

## 许可证

代码以 [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) 许可发布，© 2026 Qiankang (Kant) Wang。三张角色立绘采用 CC BY-NC-SA 4.0 许可，署名见 [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md)。

## 致谢

- 其他聊天平台的接入靠 [AstrBot](https://github.com/AstrBotDevs/AstrBot)、[NapCat](https://github.com/NapNeko/NapCatQQ)、[Koishi](https://koishi.chat) 与 [satori-python](https://github.com/RF-Tar-Railt/satori-python)、[matrix-nio](https://github.com/matrix-nio/matrix-nio) 与 [mautrix 桥接](https://docs.mau.fi/bridges/)；微信连接依据腾讯的 [openclaw-weixin 协议说明](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)。
- 从反应中学习借鉴了 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557) 和 [BlenderBot 3x](https://arxiv.org/abs/2306.04707)；世界书参考了 [SillyTavern](https://github.com/SillyTavern/SillyTavern) 的 World Info。
