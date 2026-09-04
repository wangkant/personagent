<div align="center">

# personagent

<p><strong>一个知道怎么说话，也知道什么时候不该说话的人设 Agent。</strong></p>

让同一个角色自然地存在于群聊与私聊中。<br>
理解聊天现场，默认有选择地回应；能够从真实反应中学习，又不会被一次噪声反馈改写性格。

[English](README.md) · [**简体中文**](README.zh-CN.md)

[![CI](https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg)](https://github.com/wangkant/personagent/actions/workflows/ci.yml)
[![最新版本](https://img.shields.io/github/v/release/wangkant/personagent?display_name=tag&sort=semver&color=6f42c1)](https://github.com/wangkant/personagent/releases)
[![Python 3.10–3.12](https://img.shields.io/badge/Python-3.10%E2%80%933.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2f855a.svg)](LICENSE)

[**快速开始**](#快速开始) · [为什么选择 personagent](#为什么选择-personagent) · [部署](#通过-astrbot-部署) · [架构](#架构) · [文档](#文档)

</div>

<a href="#快速开始">
  <img src="assets/demo.svg" alt="personagent 经过结构化决策后选择回复或保持沉默" width="100%">
</a>

`personagent` 可以把任意 OpenAI 兼容聊天模型变成一个对话参与者，而不是永远在线的助理。AstrBot 为 QQ、Telegram、Discord、Slack、飞书、KOOK 等平台提供统一传输层；所有平台共用同一套人设、记忆、安全和学习管线。

## 快速开始

你只需要 Git、Python 3.10+ 和一个 OpenAI 兼容 API Key。本地试用不需要消息平台账号或适配器。

```bash
git clone https://github.com/wangkant/personagent.git
cd personagent
python quickstart.py
```

配置向导会创建 `.venv`、安装依赖、写入 `.env`、创建人设、按需检查模型接口，并打开终端试用。它支持 DeepSeek、Kimi、OpenAI、Ollama 和自定义 OpenAI 兼容接口。

```bash
# 再次进入终端试用
.venv/bin/python try_chat.py                 # macOS / Linux
.venv\Scripts\python.exe try_chat.py        # Windows
.venv/bin/python try_chat.py --lang zh       # 中文人设与数据
.venv/bin/python try_chat.py --owner         # 以配置好的主人身份对话
```

终端试用走的就是生产回复链路：人设、检索、结构化输出、过滤器和验证器。会话内 `/owner <消息>` 以主人身份发一句，`/as <名字> <消息>` 以另一位参与者身份发言，`/reset` 清空上下文，`/quit` 退出。

## 为什么选择 personagent

| | |
|---|---|
| **处在现场的人设**<br>关系、对话位置、意图和有作用域的记忆都位于核心回复链路中。 | **默认有选择地回应**<br>`PASS` 是一等结果；沉默本身也可以是正确回应。 |
| **门控之后再学习**<br>用户反应先成为只追加证据；只有经过交叉验证并晋升的候选项才能影响后续回复。 | **失败即关闭的投递边界**<br>结构化输出必须经过解析、过滤、角色策略和投递校验才能发出。 |

图片、表情包、URL、视频和分享卡片都可以成为上下文。聊天、视觉、评估和裁决模型统一使用 OpenAI 兼容 HTTP 接口，不绑定特定供应商。

## 通过 AstrBot 部署

线上对话只走一条路径：

```text
QQ / Telegram / Discord / Slack / 飞书 / KOOK / …
                         │
                         ▼
                AstrBot + 转发插件
                         │
                         ▼
           personagent /webhook/gateway
```

1. 运行 `python quickstart.py`，在「连接 AstrBot」一步选是：向导会把内置的[转发插件](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md)复制到 AstrBot 的 `data/plugins/`，生成共享的 `GATEWAY_TOKEN` 并写入两边，写入你给的白名单；若接入 QQ，还会设置 `GATEWAY_NATIVE_PLATFORMS=aiocqhttp`。无交互版本：`python quickstart.py --astrbot <AstrBot data 目录> [--qq]`。
2. 重启 AstrBot（或在其 WebUI 里重载插件）。平台本身在 AstrBot 中配置。
3. 用 `python main.py` 启动 Agent（也可用 `start.sh` / `start.ps1`，它们会使用向导创建的 `.venv`）。

手动做的话：把插件目录复制到 `data/plugins/`，把 `agent_url` 指向 `http://127.0.0.1:8080/webhook/gateway`，`gateway_token` 与 Agent 的 `GATEWAY_TOKEN` 设为同一个非空值，填好白名单；接入 QQ 时从 `excluded_platforms` 中移除 `aiocqhttp`，并设置：

   ```dotenv
   GATEWAY_NATIVE_PLATFORMS=aiocqhttp
   ```

这样既能保持 QQ 身份、记忆和学习作用域不变，又能让所有平台统一进入同一个网关。主动消息、OCR 等 QQ 专属后台动作仍通过 OneBot HTTP API（`NAPCAT_API`）发出。插件默认拒绝所有来源，只有显式加入白名单的会话才会被转发。旧的直连入口（OneBot 客户端直接 POST 到 `/webhook/qq`）自 0.3.0 起标记废弃：仍然可用，但不再是文档推荐的路径。

跨主机部署必须使用 HTTPS 或私有隧道，并在插件与 Agent 中设置相同的非空 `GATEWAY_TOKEN`。Agent 绑定公网地址（`HOST=0.0.0.0`）时还必须配置 `WEBHOOK_SECRET`，两者缺一启动就会拒绝。完整步骤见[部署指南](docs/deploy.md)（英文），其中包括如何分别验证两个方向。

## 架构

![personagent 架构](docs/persona_llm_agent_architecture.zh-CN.svg)

每条消息都经过同一条回复边界：

1. **接入**——鉴权、限流、去重、归一化并补充上下文。
2. **决策**——解析关系与意图、检索作用域内信息，并决定是否需要回复。
3. **生成与校验**——按结构化协议调用模型，再过滤和验证输出。
4. **异步学习**——把反应与评估记录为证据，不阻塞实时回复。

单有证据不会改变行为。自动晋升需要相互兼容的交叉验证，所有已晋升候选都可以审计、回滚或取代。修改人设文档不会丢掉已学内容；换一个 `PERSONA_VERSION` 才会从零开始。可变状态统一写入 `runtime/`，只追加账本始终是唯一事实来源。

## 配置

`.env.example` 是完整且带注释的权威参考。配置向导只填入首次运行所需的几项；启动预检（也是 `tools/healthcheck.py` 的第一部分）会报告缺失的必填项以及模板里没有的任何 key，拼错的设置不会再被静默忽略。

| 范围 | 设置 |
|---|---|
| 模型 | `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`——任意 OpenAI 兼容的 `/v1` 接口。`PRIVATE_MODEL`、`FALLBACK_MODEL`、`JUDGE_MODEL` 共用同一接口。 |
| 人设 | `BOT_NAME`、`AGENT_LANG`、`PERSONA_FILE`、`PERSONA_CARD_FILE`——人设卡里的 `reply_style` 用来开启 emoji 和额外字符集。 |
| 网关 | `GATEWAY_TOKEN`、`GATEWAY_OWNER_IDS`、`GATEWAY_NATIVE_PLATFORMS`；QQ 专属 `BOT_QQ`、`NAPCAT_API`、`OWNER_QQ`。 |
| 学习 | `PROMOTE_AUTO`（保守晋升，默认开）；`EVAL_ENABLE` 与 `EVOLVE_AUTO`（自评与无人值守诊断，默认关）。 |
| 状态 | `AGENT_HOME`（部署根目录；相对的人设路径按它解析）、`AGENT_RUNTIME_DIR`（`runtime/`，已被 Git 忽略）。 |

```dotenv
AGENT_LANG=en  # 英文人设与数据
# AGENT_LANG=zh  # 中文人设与数据
```

## 运维

```bash
curl http://127.0.0.1:8080/health           # 存活探针，不调用模型
curl http://127.0.0.1:8080/health/details   # 依赖探测；配置了 GATEWAY_TOKEN 后需带 X-Gateway-Token 头
python tools/healthcheck.py                  # 完整诊断，模型探针会消耗额度
python tools/candidates_admin.py list        # 机器人学到了什么、依据哪些证据
python -m pytest -q                          # 离线回归测试
```

在任何一个人设负责的会话里，`@<BOT_NAME> 你学到了什么`（或 `what have you learned`）会回答这个群的记忆数、已生效的好回复和「别这样说→这样说」配对、还在等第二个人佐证的提议数，以及最近的自评分；`记得什么` 列出记忆。两者都不调用模型。

请将 `AGENT_RUNTIME_DIR` 与私有人设文件一起备份，并且不要提交运行状态；其中可能包含凭证、账号标识、对话片段、用户反应和学习内容。如果机器人正常启动却从不回复，按[机器人沉默时的排查清单](docs/deploy.md#when-the-bot-goes-quiet)逐项检查。

## 文档

- [部署指南](docs/deploy.md)
- [AstrBot 插件](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md)
- [配置参考](.env.example)
- [更新日志](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)
- [部署免责声明](DISCLAIMER.md)

## 负责任地使用

第三方协议客户端可能违反平台条款或触发账号风控。请默认保持私有部署、妥善保护密钥和对话数据、在适当场景使用次要账号，并在处理他人消息前取得同意。

## 许可证

[MIT](LICENSE) © 2026 Qiankang Wang。

## 致谢

基于 [OneBot v11](https://github.com/botuniverse/onebot-11) 事件模型、[NapCat](https://github.com/NapNeko/NapCatQQ)、[AstrBot](https://github.com/AstrBotDevs/AstrBot)、[FastAPI](https://github.com/fastapi/fastapi) 和 [httpx](https://github.com/encode/httpx) 构建，思路借鉴 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557) 和 [BlenderBot 3x](https://arxiv.org/abs/2306.04707)。世界书与输出过滤器的模型参考了 SillyTavern 的 World Info 与正则扩展。
