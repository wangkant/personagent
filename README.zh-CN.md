<p align="center"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%"></p>

<h3 align="center">一个知道什么时候该安静、能从别人的纠正里学习的群聊角色。</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="License: MIT"></a>
  <a href="https://github.com/wangkant/astrbot_plugin_personagent"><img src="https://img.shields.io/badge/AstrBot-plugin-8a6d3b" alt="AstrBot plugin"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <b>简体中文</b></p>

personagent 是放进群聊里的一个角色：选一个现成的性格或自己写一个，接上任意 OpenAI 兼容的模型就能用。它经 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 进 QQ、Telegram、Discord 等十几个平台，也能经 [Koishi](https://koishi.chat)（[Satori](https://satori.chat)）或 [Matrix](https://matrix.org) 接入。

想用它一对一聊天，可以试试 [**Charune**](https://www.charune.com/)，它的对话引擎就是 personagent。

![管理面板的聊天视图：沉默的原因、被叫到的回复、划掉的旧回复和它学会的说法](https://raw.githubusercontent.com/wangkant/personagent/main/assets/readme-chat.zh-CN.png)

<sub>管理面板里的一段群聊：它在哪儿没开口、为什么，在哪儿被叫到；被纠正的那句划掉，下面挂着它学会的更好说法。每一处都有记录，点「撤回」就能撤掉。</sub>

## 一分钟试用

```bash
uvx personagent demo --lang zh   # 看它怎么不插嘴、怎么被教会；不要 Key，什么都不用配
uvx personagent init             # 选模型服务、填 Key、挑一个性格
uvx personagent chat             # 在终端里的模拟群聊中和它说话
```

`uvx` 来自 [uv](https://docs.astral.sh/uv/)，它会自己下载 Python。安装 uv：macOS / Linux 运行 `curl -LsSf https://astral.sh/uv/install.sh | sh`，Windows 运行 `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`。

想用 pipx、pip 安装或者从源码运行，见[使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#安装和主目录)。

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
      设置向导中英文都有，11 种模型服务可选；看演示不要 Key。<br>
      经 AstrBot、Koishi、Matrix 接进你已经在用的群。<br>
      自带一个本地管理面板。
    </td>
  </tr>
</table>

- 每个聊天的记忆各管各的，互不相通。
- 改人设不会丢掉它学到的东西。
- 效果是量过的，数字见[效果评测](https://github.com/wangkant/personagent/blob/main/README.zh-CN.md#效果评测)。

## 接进你的 QQ 群

personagent 自己不登录 QQ：[NapCat](https://github.com/NapNeko/NapCatQQ) 登录机器人的 QQ 小号，AstrBot 转发消息，personagent 决定说不说、说什么。

1. 安装 [AstrBot](https://docs.astrbot.app)（用它的启动器、Docker，或者 `uv tool install astrbot`），先启动一次。
2. 安装 NapCat，用机器人的 QQ 号登录（建议用小号）。
3. 运行 `personagent connect astrbot`，聊天平台选 QQ，再填机器人的 QQ 号、要加入的群号和你自己的 QQ 号。它会找到 AstrBot 的文件夹、装好插件，并在两边写入同一个 `CONNECTOR_TOKEN`。
4. 在 AstrBot 的 WebUI 里添加 QQ（OneBot v11 / aiocqhttp）平台，再把 NapCat 的反向 WebSocket 指向 `ws://127.0.0.1:6199/ws`。
5. 运行 `personagent run` 并保持开着，然后重启 AstrBot，或在它的 WebUI 里重载插件。
6. 在群里说「小夏，你好」（换成你起的名字）。

插件也有独立仓库 [astrbot_plugin_personagent](https://github.com/wangkant/astrbot_plugin_personagent)，可以在 AstrBot 的 WebUI 里填这个地址安装，再把插件设置里的 `connector_token` 填成 personagent 的 `CONNECTOR_TOKEN`。从零开始、每一步都写明会看到什么，见[中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)；Telegram、Discord 等其他平台和 Docker 部署，见[使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#接进聊天平台)和[部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.md)（英文）。

## 和同类项目对比

| | personagent | AstrBot（自带功能） | 麦麦 MaiBot | Koishi ChatLuna 伪装群友 | ElizaOS |
|---|---|---|---|---|---|
| 没人叫时插不插话 | 由模型判断真人会不会接话 | 可选“主动回复”，按概率随机（默认 10%，默认关闭） | 由规划模型决定，按发言频率设置调节 | 规则触发：固定间隔、活跃度、空闲 | 由模型选择回复、忽略或停止 |
| 从别人对它回复的反应中学习 | 会：纠正、否定、接受重答 | 没有内置 | 从群聊里学表达方式和黑话；从反应中学习：文档未提及 | 文档未提及 | 文档未提及 |
| 改动前要求多方佐证 | 同一聊天两条一致反应，其中一条为强 | 没有内置 | 可选人工审核学到的表达 | 文档未提及 | 文档未提及 |
| 审计记录与撤销 | 只追加的账本；终端或面板里撤销 | 没有内置 | 文档未提及 | 文档未提及 | 文档未提及 |
| 公开的行为评测 | 开口、人设、学习三项（[见下文](https://github.com/wangkant/personagent/blob/main/README.zh-CN.md#效果评测)） | 文档未提及 | 文档未提及 | 文档未提及 | 文档未提及 |
| 配置与管理 | 终端设置向导；本地管理面板 | WebUI、桌面启动器 | WebUI、一键启动器 | Koishi 控制台 | 命令行、网页客户端 |
| 运行方式 | Python 服务，接在 AstrBot、Koishi（Satori）或 Matrix 后面 | Python 程序，18 个以上平台 | Python 程序，QQ 走 NapCat | Koishi 插件 | TypeScript（Bun）；Discord、Telegram、Slack 等 |
| 许可证 | MIT | AGPL-3.0 | GPL-3.0 | AGPL-3.0 | MIT |

以上依据各项目 2026 年 10 月的文档。“文档未提及”指我们没找到相关说明，不代表做不到；AstrBot 插件市场里有学习类插件，其中一个带审核队列和回滚。

这些情况下别的项目可能更合适：想要一键安装的桌面程序、所有设置都在 WebUI 里点（麦麦、AstrBot）；想要庞大的插件生态，或者把学黑话、表情包、图片记忆当主打功能（麦麦、AstrBot 的插件）。personagent 不是来替代 AstrBot 或 Koishi 的：它接在它们后面，平台和插件照用，只是多了一个懂得收着说、学东西有据可查的角色。

## 效果评测

`personagent eval` 用标注好的中英文用例驱动真实的 agent，量三件事：该不该开口、像不像人设、纠正能不能按规则生效。下面是一次运行的结果：

| | 中文 | 英文 |
|---|---|---|
| 被测模型 | `deepseek/deepseek-v4.1-flash` (OpenRouter) | `deepseek/deepseek-v4.1-flash` (OpenRouter) |
| 裁判模型 | `openai/gpt-4.1-mini` | `openai/gpt-4.1-mini` |
| 日期 | 2026-10-03 | 2026-10-03 |
| 开口：准确率 | 88%（21/24） | 92%（22/24） |
| 开口：该沉默时开了口 | 3/11 | 2/11 |
| 开口：该开口时沉默了 | 0/13 | 0/13 |
| 人设：盲选中胜过普通助手（95% 置信区间） | 17/18（74–99%） | 18/18（82–100%） |
| 学习：生效或搁置符合预期（k/n） | 10/10 | 10/10 |
| 学习：生效后下一次回复变了 | 2 个中 0 个（另外 4 个生效场景的探针本来就答对了） | 2 个中 1 个（另外 4 个生效场景的探针本来就答对了） |
| 学习：变差的场景 | 6 个中 1 个 | 6 个中 0 个 |

`开口` 错的大多是顺口提到名字的话（比如「Wi-Fi 现在叫小夏-5G」）；学习要看「符合预期」那一行：站得住的纠正全部生效，捣乱、旁观、说完就走的一个也没生效。每个用例、每条回复和判定都在 [docs/evals/2026-10-03](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-03)。

「盲选中胜过普通助手」大概是这样的（同一次运行，同一个模型，同一句话）：

| 消息 | personagent | 普通助手 |
|---|---|---|
| 「麻薯，现在躲在沙发底下不出来」（私聊，刚养的猫） | 正常，新环境都这样，别硬拉它 / 给点吃的放旁边，人走开它自己就出来了 | 恭喜！麻薯这名字太可爱了，软乎乎的。刚到家躲沙发底下**非常正常**……1. **给它退路，别堵沙发底** …… |
| 「明天第一次约会，有啥建议」 | 别安排太满，吃个饭散散步就够了，聊得来比去哪重要 / 要是冷场就聊聊最近看的片，比硬找话题自然 | 大刘，第一次约会记住：干净清爽、准时到，地点选能聊天又不尴尬的，比如咖啡+散步。多听少吹，别查户口，少提前任…… |

一次运行只是一次抽样，结果会有波动；人设和学习两项由一个和被测模型不同的裁判模型来判。各测试集测什么、怎么自己跑，见[使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#效果评测)。

## 文档

- [使用手册](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)：安装、设置、终端试聊、接入各平台、教它、管理面板、评测、排错，README 没写的都在这里
- [中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)：Windows + QQ，从零开始，每一步都写明会看到什么
- [部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.md)（英文）：长期运行要知道的事，包括连接器、多平台、对外暴露、费用和排查
- [连接器协议](https://github.com/wangkant/personagent/blob/main/docs/connectors.md)（英文）：给别的平台自己写连接器
- [工具脚本](https://github.com/wangkant/personagent/blob/main/docs/tools.md)（英文）：`tools/` 里给源码版用的脚本
- [更新日志](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md)（英文），含[从 0.4 升级](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04)的完整清单
- [贡献指南](https://github.com/wangkant/personagent/blob/main/CONTRIBUTING.md)（英文）
- [安全策略](https://github.com/wangkant/personagent/blob/main/SECURITY.md)（英文）：怎么私下报告漏洞
- [免责声明](https://github.com/wangkant/personagent/blob/main/DISCLAIMER.zh-CN.md)

## 隐私

personagent 存的一切，包括设置、人设、记忆和账本，都在你自己机器的主目录里。模型服务商会看到对话内容；接入真实的群之前，请告诉群友这是机器人，并征得他们同意。哪些内容会发给谁，见[使用手册的隐私一节](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#隐私与知情同意)。

## 项目状态

1.0。QQ（经 AstrBot）是跑得最多的路线，AstrBot 的其他平台走同一个插件；Satori 和 Matrix 连接器目前只在模拟环境里测过。CI 在 Linux 上用 Python 3.10–3.14、在 Windows 上用 Python 3.12 跑测试。

## 许可证

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang。

## 致谢

- [AstrBot](https://github.com/AstrBotDevs/AstrBot)、[satori-python](https://github.com/RF-Tar-Railt/satori-python) 与 [Koishi](https://koishi.chat)、[matrix-nio](https://github.com/matrix-nio/matrix-nio) 与 [mautrix 桥接](https://docs.mau.fi/bridges/) 把 personagent 带到各个聊天平台，[NapCat](https://github.com/NapNeko/NapCatQQ) 负责 QQ。
- [FastAPI](https://github.com/fastapi/fastapi) 和 [httpx](https://github.com/encode/httpx) 支撑服务本身和模型调用，[uv](https://github.com/astral-sh/uv) 和 [pipx](https://github.com/pypa/pipx) 让它一行命令就能装好。
- 从反应中学习的思路借鉴了 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557) 和 [BlenderBot 3x](https://arxiv.org/abs/2306.04707)。
- 世界书与输出过滤器参考了 [SillyTavern](https://github.com/SillyTavern/SillyTavern) 的 World Info 与正则扩展。
