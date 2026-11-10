<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">一个懂得何时保持沉默、并能从纠正中学习的群聊角色。</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-0969da?style=flat-square&labelColor=24292f" alt="License: PolyForm Noncommercial"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <strong>简体中文</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

personagent 是一个用于群聊的角色：可选用现成角色或自行编写，接入任意兼容 OpenAI 接口的模型即可使用。你可以先在本机与角色聊天，再通过同一个本地页面将其接入 QQ、微信、Telegram、Discord 及其他十余个平台。

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.zh-CN.jpg" alt="本地页面中的「连接平台」：列出所有可接入的平台" width="960">
</p>

<p align="center"><em>「连接平台」与设置、聊天位于同一个本地页面中。</em></p>

## 主要特点

<table>
<tr>
<td width="220" valign="top"><strong>懂得何时保持沉默</strong></td>
<td valign="top">
被点名时即回复。无人点名时，由模型判断真人此时是否会接话。<br>
有人连续刷屏时，角色只回复一条。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>只采纳可靠的纠正</strong></td>
<td valign="top">
纠正所教的内容（例如群里对健身房的称呼）会应用于该聊天此后的每一条回复。<br>
恶意干扰者和旁观者都无法教坏角色。<br>
每一处改动均有记录，且均可撤回。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>上手迅速，可接入你的群聊所在的平台</strong></td>
<td valign="top">
一条命令即可在电脑上打开，页面支持中文、英文及其他八种语言。<br>
填写一个模型 Key 即可聊天；再用手机扫码一次或粘贴一至两项，即可接入一个平台。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>可选用现成角色，也可自行编写</strong></td>
<td valign="top">
提供七种现成性格。其中三个是社区中早已流行的形象：DeepSeek 鲸鱼娘、GPT 娘（白龙）和 Claude 娘，立绘会眨眼、思考和说话。<br>
人设可随时改写，角色已学到的内容将保留。
</td>
</tr>
</table>

每个聊天都有独立的记忆，也可以让角色忘记指定内容：`小夏，记住 阿杰不吃辣`、`小夏 忘掉 不吃辣`（[记忆命令](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#教导角色)）。

## 快速开始

```sh
python -m pip install personagent
personagent
```

如已安装 [uv](https://docs.astral.sh/uv/)，可直接运行 `uvx personagent`，无需单独安装。在 Windows 上也可以下载源码 ZIP，然后双击 `start.bat`。

在 Windows 上，personagent 会在独立窗口中打开；在 macOS 和 Linux 上则在浏览器中打开。填写模型 API Key 后，点击「验证并开始聊天」。如尚无 Key，可使用默认选中的 OpenRouter 免费模型，其 Key 不收费。`personagent demo` 无需 Key，会播放三段预先编写的场景。[简明入门](https://github.com/wangkant/personagent/blob/main/docs/start.zh-CN.md)逐屏介绍了页面的各个部分。

personagent 本身免费。费用支付给你选择的模型服务，按其价格计算。OpenRouter 的免费模型每天限 50 次请求，部分免费服务商会保留收到的内容；Ollama 在你自己的电脑上运行模型，无需 Key。

## 接入群聊

在本地页面中打开「连接平台」：

| 页面分组 | 平台 | 需要准备 |
|---|---|---|
| 扫码连接 | QQ、个人微信 | 手机。微信机器人仅支持一对一聊天 |
| 填写一至两项 | Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK、Stoat、KOOK、飞书、钉钉、Slack、企业微信智能机器人、Mattermost、Misskey | 从平台后台复制，页面会说明需要复制哪几项 |
| 高级 | 企业微信应用、微信公众号、QQ（Webhook）、OneBot v11（NapCat）、Satori | 公网地址，或本机的其他软件 |

已连接的平台在每次启动 personagent 时都会自动连接。扫码连接的平台，以及 Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 由 personagent 直接连接；其余平台通过 personagent 在后台下载并运行的 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 接入。在没有显示器的服务器上，可在终端中运行 `personagent connect <平台>` 连接上述十个平台中的任意一个，操作步骤和核验方式与页面相同；运行 `personagent up` 即可在不打开浏览器的情况下全部启动。各平台的设置方法见[使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#接入聊天平台)；从零开始接入 QQ 请参阅[部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)。

如果你已在运行 AstrBot、Koishi 或 Matrix，personagent 可以接在其后，仅作为角色运行：请参阅[你自己运行的桥接](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#你自己运行的桥接)、[Satori 连接器](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.zh-CN.md)和 [Matrix 连接器](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.zh-CN.md)。

## 编程助手

**由编程助手代为安装。** 将下面这句话发送给能在你电脑上运行命令的 AI 编程助手。模型 Key 由你自己在本地页面中填写，不经过编程助手。

```text
读 https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md ，然后帮我把 personagent 装好并设置好
```

**编写代码时与角色对话。** Claude Code、Codex 和 DeepSeek Harness（`dsh`）均可连接你的角色，聊天和记忆与本地页面共用同一份：

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove` 可将其移除；也可以在页面「连接平台」的「编程助手」中接入或移除。权限设置，以及让角色在一轮结束时发表一句评论的 `--react`，请参阅[使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#编程助手)。

## 更新与卸载

PyPI 上发布新版本时，页面会显示提示及相应的更新命令。如使用 pip 安装，更新命令为 `python -m pip install -U personagent`。对于大多数安装方式，页面「应用」视图中的「更新并重新打开」可代为执行更新。设置、角色、已学到的内容和已连接的平台均会保留。如需卸载，请按照[卸载步骤](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it)（英文）操作。

## 隐私

personagent 保存的所有数据都位于你本机的一个主目录中。你选择的模型服务商可以看到角色所回复的对话；personagent 每天向 pypi.org 查询一次是否有新版本（设置 `UPDATE_CHECK_ENABLED=false` 可关闭）。将角色接入真人聊天之前，请告知对方这是机器人，并征得其同意；哪些内容会发送至何处，[使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#隐私与知情同意)中均有列出。

## 文档

- [使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)：设置、连接器、教导角色、「动态」视图和故障排查。
- [部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)：实际运行所需了解的事项、费用，以及机器人不发言时的排查方法。
- [连接器协议](https://github.com/wangkant/personagent/blob/main/docs/connectors.zh-CN.md)：供自行编写连接器的开发者参阅。
- [工具脚本](https://github.com/wangkant/personagent/blob/main/docs/tools.zh-CN.md)：`tools/` 中的脚本，从克隆的源码运行时使用。
- [更新日志](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md)（英文） · [贡献指南](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md)（英文） · [安全策略](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md)（英文） · [免责声明](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.zh-CN.md)

## 许可证

personagent 以 [PolyForm Noncommercial License 1.0.0](https://github.com/wangkant/personagent/blob/main/LICENSE) 发布，© 2026 Qiankang (Kant) Wang：可免费用于非商业目的的使用、修改和分享，不得用于商业目的。`integrations/` 下的连接器仍采用 MIT 许可，1.4.0 及更早的版本亦然。三张角色立绘采用 CC BY-NC-SA 4.0 许可，署名见 [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md)。

## 致谢

- 其他聊天平台的接入依托 [AstrBot](https://github.com/AstrBotDevs/AstrBot)、[NapCat](https://github.com/NapNeko/NapCatQQ)、[Koishi](https://koishi.chat) 与 [satori-python](https://github.com/RF-Tar-Railt/satori-python)、[matrix-nio](https://github.com/matrix-nio/matrix-nio) 与 [mautrix 桥接](https://docs.mau.fi/bridges/)；微信连接依据腾讯的 [openclaw-weixin 协议说明](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)。
- 从反应中学习借鉴了 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557) 和 [BlenderBot 3x](https://arxiv.org/abs/2306.04707)；世界书参考了 [SillyTavern](https://github.com/SillyTavern/SillyTavern) 的 World Info。
