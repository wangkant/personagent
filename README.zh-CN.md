<p align="center"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%"></p>

<h3 align="center">一个知道什么时候该安静、能从别人的纠正里学习的群聊角色。</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="License: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <b>简体中文</b></p>

personagent 是放进群聊里的一个角色：选一个现成的性格或自己写一个，接上任意 OpenAI 兼容的模型就能用。QQ、微信、Telegram、Discord 由它自己连接；KOOK、飞书、钉钉、Slack、企业微信、Mattermost、Misskey 在同一个页面里接入。

先在本地页面里聊天，填一个模型 Key 就能开始。想把角色带进群，扫一次码或填一两项就行。

![本地页面的「连接平台」：能接入的平台一目了然](https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.zh-CN.jpg)

<sub>「连接平台」和设置、角色聊天在同一个本地页面里。截图来自一个临时环境，使用本机模拟模型。</sub>

## 从这里开始

从 PyPI 安装后打开：

```sh
python -m pip install personagent
personagent
```

装了 [uv](https://docs.astral.sh/uv/) 的话，`uvx personagent` 不用单独安装就能运行。

浏览器会打开一个本地页面，分三栏：「开始聊天」「连接平台」「角色与设置」。填入模型 API Key，点「验证并开始聊天」，它会发一次小请求校验 Key。模型服务有 10 种预设，也可以选其他 OpenAI 兼容服务；角色有名字和性格预设。「人设」框里就是 `persona.txt`，保存后会重启角色服务，学到的东西不会丢。「更多功能」里可以开联网搜索、看图和主动说话。再次运行 `personagent` 会沿用已经打开的页面。

Windows 也可以下载源码 ZIP，解压后双击 `start.bat`；克隆了仓库的话运行 `python quickstart.py`。需要 Python 3.10–3.14。详见[简明入门](https://github.com/wangkant/personagent/blob/main/docs/start.zh-CN.md)；命令行和连接器的用法在[完整手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)里。

## 为什么用它

<table>
  <tr>
    <td width="220"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="托着腮听大家聊天" width="220"></td>
    <td>
      <b>知道什么时候该安静</b><br>
      叫它才回。没人叫时，由一个模型判断真人这时会不会接话，不靠掷骰子。<br>
      有人连着刷屏，它只回一条。
    </td>
  </tr>
  <tr>
    <td width="220"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/learned-notebook.webp" alt="本子上划掉一句，换成更好的一句" width="220"></td>
    <td>
      <b>只从站得住的纠正里学</b><br>
      一处改动要同一个聊天里两条一致的反应，其中一条是强证据。<br>
      捣乱的人、旁观者都教不坏它。<br>
      每一处改动都有记录，随时能撤回。
    </td>
  </tr>
  <tr>
    <td width="220"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="拿着本子准备聊天的兔子" width="220"></td>
    <td>
      <b>上手快，你的群在哪它就去哪</b><br>
      在浏览器里设置和聊天，中英文都有，11 种模型服务可选。<br>
      QQ、微信、Telegram、Discord 由它自己连接，另外十几个平台也在同一个页面里接入。<br>
      自带一个本地管理面板。
    </td>
  </tr>
</table>

- 每个聊天的记忆各管各的，互不相通。
- 改人设不会丢掉它学到的东西。
- 效果是量过的，数字见[效果评测](https://github.com/wangkant/personagent/blob/main/README.zh-CN.md#效果评测)。

## 接进你的群

在本地页面打开「连接平台」，平台分三组：

| 页面分组 | 平台 | 要准备什么 |
|---|---|---|
| 扫码就能连 | QQ、个人微信 | 手机。微信这类机器人只能私聊 |
| 粘贴一两项 | Telegram、Discord、KOOK、飞书、钉钉、Slack、企业微信智能机器人、Mattermost、Misskey | 从平台后台复制，页面会说复制哪一项 |
| 高级 | 企业微信应用、微信公众号、QQ（Webhook）、OneBot v11（NapCat）、Satori | 公网地址，或本机的其他软件 |

填的内容先校验，通过才保存；连好的平台以后每次启动 personagent 都会自动连上。QQ、微信、Telegram、Discord 由 personagent 直接连接，其余平台经它在后台下载并运行的 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 接入，不用另外打开什么。在服务器上不开浏览器的话，`personagent up` 会启动角色和所有连好的平台。

**已经在用 AstrBot、Koishi 或 Matrix？** 这台电脑上的 AstrBot，运行 `personagent connect astrbot` 就会装好插件、配好口令。AstrBot 在别的机器上的话，从[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下载 `astrbot_plugin_personagent.zip`，在它插件页的「从文件安装」上传，再按下面的手册填好口令和 personagent 的 HTTPS 地址。[Koishi](https://koishi.chat) 经 [Satori 连接器](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md)（英文）接入，[Matrix](https://matrix.org)（可经 mautrix 桥接 WhatsApp、Signal）经 [Matrix 连接器](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md)（英文）接入。

具体做法见[使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#接进聊天平台)和[部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.md)（英文）；[中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)从零讲 QQ，每一步都写明会看到什么。

## 和同类项目对比

常被拿来比较的几个项目，依据各自 2026 年 10 月的文档：

- **AstrBot**（AGPL-3.0）：机器人框架，能接 18 个以上的平台，有 WebUI 和很大的插件市场。可以开“主动回复”按概率随机插话（默认 10%，默认关闭），学习交给插件。
- **麦麦 MaiBot**（GPL-3.0）：QQ 上的角色机器人，经 NapCat 接入，有 WebUI 和一键启动器。由一个规划模型决定多久说一次话，会从群聊里学表达方式和黑话。
- **ChatLuna 伪装群友**（AGPL-3.0）：Koishi 插件，按规则插话：固定间隔、群里的活跃度、冷场了多久。
- **ElizaOS**（MIT）：TypeScript 写的 agent 框架，支持 Discord、Telegram、Slack 等，由模型决定回不回。

personagent 自带、而它们交给插件或文档里没写的：从别人对它回复的反应里学（纠正、否定、接受了的重答）；一处改动要同一个聊天里两条一致的反应，其中一条是强证据；每处改动都有记录，可以撤回；行为有公开的评测（[见下文](https://github.com/wangkant/personagent/blob/main/README.zh-CN.md#效果评测)）。

它们更强的地方：桌面程序、所有设置都在 WebUI 里点，插件生态大，还有学黑话、表情包、图片记忆。已经在用 AstrBot 或 Koishi 也不用二选一：personagent 可以接在它们后面，只当那个角色。

## 效果评测

`personagent eval` 用标注好的用例驱动真实的 agent，每个用例、每条回复和判定都会存下来。最近公开的一次是 2026-10-03，被测模型 `deepseek/deepseek-v4.1-flash`（经 OpenRouter），裁判 `openai/gpt-4.1-mini`：

| | 中文 | 英文 |
|---|---|---|
| 该说话时说、该安静时安静 | 21 / 24 | 22 / 24 |
| 和普通助手盲选，裁判选了它 | 17 / 18 | 18 / 18 |
| 纠正该生效的生效、该挡的挡下 | 10 / 10 | 10 / 10 |

- 开口出错的全是顺口提到名字的话，比如「Wi-Fi 现在叫小夏-5G」；该它回的话一句没漏。
- 站得住的 6 条纠正全部生效，捣乱、旁观、说完就走的全被挡下。生效之后多数看不出变化，因为模型本来就答得像这个角色；有一条中文回复在纠正之后反而变差了。

同一次运行、同一个模型、同一句话：

**大刘（私聊，刚养的猫）：** 麻薯，现在躲在沙发底下不出来

| personagent | 普通助手 |
|---|---|
| 正常，新环境都这样，别硬拉它<br><br>给点吃的放旁边，人走开它自己就出来了 | 恭喜！麻薯这名字太可爱了，软乎乎的。<br><br>刚到家躲沙发底下**非常正常**，别急着把它拉出来。…… |

一次运行只是一次抽样，结果会有波动。完整报告在 [docs/evals/2026-10-03](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-03)；各项测什么、怎么自己跑，见[使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#效果评测)。

## 文档

- [使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)：安装、设置、终端试聊、接入各平台、教它、管理面板、评测、排错，README 没写的都在这里
- [中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)：装好、扫码接 QQ、排查，从零开始，每一步都写明会看到什么
- [部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.md)（英文）：长期运行要知道的事，包括连接器、多平台、对外暴露、费用和排查
- [连接器协议](https://github.com/wangkant/personagent/blob/main/docs/connectors.md)（英文）：给别的平台自己写连接器
- [工具脚本](https://github.com/wangkant/personagent/blob/main/docs/tools.md)（英文）：`tools/` 里给源码版用的脚本
- [更新日志](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md)（英文），含[从 0.4 升级](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04)的完整清单
- [贡献指南](https://github.com/wangkant/personagent/blob/main/CONTRIBUTING.md)（英文）
- [安全策略](https://github.com/wangkant/personagent/blob/main/SECURITY.md)（英文）：怎么私下报告漏洞
- [免责声明](https://github.com/wangkant/personagent/blob/main/DISCLAIMER.zh-CN.md)

## 隐私

personagent 存的一切都在你自己机器上的一个主目录里：放 Key 的 `.env`、`persona.txt`、`runtime/`，以及放托管 AstrBot 和直连平台凭据的 `platforms/`。模型服务商会看到对话内容；接入真实的群之前，请告诉群友这是机器人，并征得他们同意。哪些内容会发给谁，见[使用手册的隐私一节](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#隐私与知情同意)。

## 项目状态

1.2.1 已发布到 PyPI（2026-10-17）。QQ 是跑得最多的平台，1.0 经 AstrBot，1.1 起直接连接。微信、Telegram、Discord 的直连会在保存前向真实服务校验凭据，其余部分在模拟环境里测试；Satori 和 Matrix 连接器目前只在模拟环境里测过。CI 在 Linux 上用 Python 3.10–3.14、在 Windows 上用 Python 3.12 跑测试，另有任务安装软件包，跑命令和本地页面。

## 许可证

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang。

## 致谢

- 其余平台接入靠 [AstrBot](https://github.com/AstrBotDevs/AstrBot)、[NapCat](https://github.com/NapNeko/NapCatQQ)、[Koishi](https://koishi.chat) 与 [satori-python](https://github.com/RF-Tar-Railt/satori-python)、[matrix-nio](https://github.com/matrix-nio/matrix-nio) 与 [mautrix 桥接](https://docs.mau.fi/bridges/)；微信直连依据腾讯的 [openclaw-weixin 协议说明](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)。
- 本地页面的平台图标来自 [Simple Icons](https://github.com/simple-icons/simple-icons)、[SVG Logos](https://github.com/gilbarbara/logos)、[IconPark](https://github.com/bytedance/IconPark)、[MingCute](https://github.com/Richard9394/MingCute) 和 [TDesign Icons](https://github.com/Tencent/tdesign-icons)，以及 KOOK 和 OneBot 自己的图标，商标归各自所有者。
- 从反应中学习借鉴了 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557) 和 [BlenderBot 3x](https://arxiv.org/abs/2306.04707)；世界书参考了 [SillyTavern](https://github.com/SillyTavern/SillyTavern) 的 World Info。
