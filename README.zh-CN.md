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

[**快速开始**](#快速开始) · [为什么选择 personagent](#为什么选择-personagent) · [部署](#部署) · [架构](#架构) · [配置](#配置)

</div>

<a href="#快速开始">
  <img src="assets/demo.svg" alt="personagent 经过结构化决策后选择回复或保持沉默" width="100%">
</a>

`personagent` 可以把任意 OpenAI 兼容聊天模型变成一个真正处在对话现场中的人设角色。它能在终端本地运行，通过 OneBot v11 直连 QQ，也能借助仓库内置的 AstrBot 网关接入 QQ、Telegram、Discord、Slack、飞书、KOOK 等平台——所有入口共用同一套人设、记忆、安全和学习管线。

## 快速开始

你只需要 Git、Python 3.10+ 和一个 OpenAI 兼容 API Key。本地试用不需要消息平台账号或适配器。

```bash
git clone https://github.com/wangkant/personagent.git
cd personagent
python quickstart.py
```

配置向导会创建 `.venv`、安装依赖、写入 `.env`、创建人设文件、按需检查模型接口，并询问是否直接进入终端试用。它可以安全地重复运行，支持 DeepSeek、Kimi、OpenAI、Ollama 和自定义 OpenAI 兼容接口。

服务启动时的预检会明确报告关键配置缺失、未知 `.env` 键、无效运行目录和空 Bot 名称，避免配置有误时只留下一个“运行正常但始终不说话”的 Agent。

<details>
<summary><strong>再次进入终端试用，或进行无交互初始化</strong></summary>

```bash
# macOS / Linux
.venv/bin/python try_chat.py
.venv/bin/python try_chat.py --lang zh

# Windows
.venv\Scripts\python.exe try_chat.py
.venv\Scripts\python.exe try_chat.py --lang zh

# CI / 自动化部署
python quickstart.py --no-input
```

终端试用与线上部署共用相同的人设、Prompt 组装、检索、输出解析和回复验证链路。使用 `--owner` 测试配置好的主人关系，或用 `--name <名字>` 指定当前说话者。

</details>

## 为什么选择 personagent

大多数聊天机器人始终处于“值班”状态：正式、积极、明显像一个助理。`personagent` 的出发点则是成为聊天中的一个参与者。

| | |
|---|---|
| **处在现场的人设**<br>语域、关系、对话位置、意图和有作用域的记忆都位于核心回复链路中。 | **默认有选择地回应**<br>`PASS` 是一等结果；沉默本身也可以是正确回应。 |
| **门控之后再学习**<br>用户反应先成为只追加证据；只有经过交叉验证并晋升的候选项才能影响后续回复，而且随时可以撤销。 | **把媒体当作上下文**<br>图片、表情包、URL、视频和分享卡片都可以参与理解，也可以成为角色表达的一部分。 |
| **一个角色，多种入口**<br>终端、QQ 直连和网关流量共用同一条 Agent 管线。 | **失败即关闭的输出边界**<br>结构化输出必须经过解析、过滤、角色策略和投递校验才能发出。 |

运行时保持供应商无关，并默认具备生产防线：Webhook 鉴权、重放防护、有界并发与载荷、持久化去重、健康检查、可变状态隔离和跨平台 CI 都已内置。

> **Beta：** 发布版本遵循语义化版本规范，行为与存储变更会记录在[更新日志](CHANGELOG.md)中。当前版本支持受控的个人部署，但平台政策与账号风险仍由部署者承担。连接第三方 IM 客户端前请阅读[部署免责声明](DISCLAIMER.md)。

## 部署

| 方式 | 适用场景 | 入站入口 | 回复路径 |
|---|---|---|---|
| **终端** | 人设设计与本地评估 | `try_chat.py` | 终端 |
| **QQ 直连** | 最直接的完整 QQ 部署 | NapCat → `/webhook/qq` | NapCat HTTP API |
| **AstrBot 网关** | 用一个传输层承载多个平台，也可以包含 QQ | AstrBot → `/webhook/gateway` | 同步网关响应 |

### QQ 现在有两种入站方式——必须二选一

原来的直连路径仍然是默认方案：

```text
QQ → NapCat → /webhook/qq → personagent
```

现在也可以把 QQ 与其他 AstrBot 适配器统一放在网关后面：

```text
QQ → AstrBot → /webhook/gateway → personagent
```

选择第二种方式时，需要从插件的 `excluded_platforms` 中移除 `aiocqhttp`、把 QQ 会话加入白名单、停止 NapCat 向 `/webhook/qq` 投递同一批事件，并设置：

```dotenv
GATEWAY_NATIVE_PLATFORMS=aiocqhttp
```

这个配置会保留记忆、历史、白名单和学习作用域一直使用的原始 QQ ID。**不要同时开启两条 QQ 入站路径**，否则同一事件会被处理两次。

即使 QQ 入站改走 AstrBot，也要继续通过 `NAPCAT_API` 保留 NapCat HTTP API：QQ 专属的主动发送、离线 `@` 补偿、旧引用消息解析和 OCR 仍然使用这条直连动作通道。完整操作见[部署指南](docs/deploy.md)和 [AstrBot 插件说明](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md)。

### QQ 直连配置

1. 运行 `python quickstart.py` 并回答可选的部署问题；也可以直接在 `.env` 中配置 `BOT_QQ`、`BOT_NAME`、`NAPCAT_API` 和 `QQ_GROUPS`。
2. 使用 `python main.py`、`./start.sh` 或 `.\start.ps1` 启动。
3. 为 [NapCat](https://github.com/NapNeko/NapCatQQ) 等 OneBot v11 客户端启用 HTTP API 作为出站动作通道，并把入站 Webhook 指向 `http://127.0.0.1:8080/webhook/qq`。

两个 HTTP 方向彼此独立：

```text
OneBot 客户端 ──事件──▶ personagent :8080   (HOST / PORT)
personagent   ──动作──▶ OneBot 客户端 :3000 (NAPCAT_API)
```

NapCat 的配置格式可能随版本变化；请参考它的[当前文档](https://napneko.github.io/)和仓库内的[验证清单](docs/deploy.md)，不要直接复制可能已经过期的配置块。

### AstrBot 网关

仓库内置的 [AstrBot 转发插件](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md)会把不同适配器的事件映射为平台无关请求，再把返回的文字、图片和提及转发回原平台。插件默认拒绝所有来源：群聊或私聊只有明确加入白名单后才会被转发。

除非平台被显式加入 `GATEWAY_NATIVE_PLATFORMS`，网关身份都会被命名为 `<platform>:<id>`。响应中的 `owned` 与 `handled` 分离，因此 Agent 主动选择 `PASS` 时，AstrBot 的内置模型也不会越过它继续回复。

纯网关平台没有持久的出站通道。要提供一次主动发言机会，调用方应发送标记为 `"proactive": true` 的普通网关事件；若人设决定开口，回复会在同一次请求中返回并由调用方转发。这段提示不会写入用户历史、反应记录或可晋升记忆。

任何非回环部署都必须使用 HTTPS 或私有隧道，并同时配置 **`WEBHOOK_SECRET` 和 `GATEWAY_TOKEN`**。网关请求会对时间戳、nonce 和正文共同签名并检查重放。由于两个 Webhook 始终都会挂载，缺少任一密钥时服务会拒绝绑定公网地址。

## 架构

![personagent 架构](docs/persona_llm_agent_architecture.zh-CN.svg)

QQ 的两种入站选择与所有网关平台最终都会汇入同一条回复边界：

1. **接入**——鉴权、限流、去重、归一化，并补充会话、图片、链接和分享卡片上下文。
2. **决策**——解析关系和模式（主人、直接呼叫、跟进、判断或主动轮次），并决定是否需要回复。
3. **检索**——组合人设、世界书、有作用域的记忆、合成种子，以及与本轮相关的已晋升样例。
4. **生成**——按结构化输出协议调用已配置模型。
5. **验证与投递**——解析 JSON，执行输出过滤和角色策略，安全拆分回复，解析表情包，并且只发送已提交的输出。
6. **异步学习**——把评估和定向用户反应记录成证据；候选晋升不会阻塞实时回复。

可导入的核心代码位于 `persona_agent/`；`main.py`、`try_chat.py` 和各类工具只是轻量入口。可变状态默认与版本化种子分离，统一写入 `runtime/`。

<details>
<summary><strong>核心包结构</strong></summary>

| 模块 | 职责 |
|---|---|
| `agent.py` | 编排、模式、防抖、Prompt 组装和模型调用。 |
| `prompts.py`、`textproc.py`、`pools.py` | 人设协议、安全输出处理和检索数据集。 |
| `ingestion.py`、`transport.py`、`gateway.py` | 内容增强、有界投递和平台无关转发。 |
| `learning.py`、`reactions.py`、`evolution.py` | 评估、反应裁决和候选项生成。 |
| `evidence.py`、`candidates.py`、`promotion.py` | 证据、候选生命周期、晋升、回滚与物化视图。 |
| `stickers.py` | 表情包接入、去重、打标、评分和选择。 |
| `storage.py`、`paths.py`、`health.py`、`preflight.py` | 持久化、运行路径隔离、服务诊断和配置检查。 |

</details>

## 有门控的学习

学习系统把“观察到什么”和“什么有权改变行为”严格分开：

| 阶段 | 权限 |
|---|---|
| **证据（Evidence）** | 记录用户反应、被接受的重试或评估；不能改变行为。 |
| **候选项（Candidate）** | 提出有版本的候选样例或偏好对；默认不生效。 |
| **晋升（Promotion）** | 显式授权候选项进入检索。 |
| **回滚 / 取代** | 不删除历史的前提下撤销或替换这份权限。 |

默认情况下，自动晋升至少需要两个相互兼容的事件，其中至少一个必须是强证据。证据会按人设、版本、语言、会话和模式隔离；过期或相互矛盾的信号不能被静默合并。积极反应和自评分都属于弱信号，无法独自晋升候选项。

已晋升视图会被原子化物化，并在下一次相关对话中热加载。只追加账本始终是唯一事实来源，因此视图可以重建，每一次决策都可以审计或撤销。

```bash
python tools/candidates_admin.py list
python tools/candidates_admin.py show <candidate-id>
python tools/candidates_admin.py promote <candidate-id> --reason "reviewed"
python tools/candidates_admin.py rollback <candidate-id> --reason "regression"
python tools/candidates_admin.py rebuild
```

设置 `PROMOTE_AUTO=false` 可完全改为人工授权。`EVOLVE_AUTO=true` 可以诊断低分回复并创建候选项，但永远不会绕过晋升门控。

## 配置

`.env.example` 是完整且带注释的权威参考，并会与代码中的每一个环境变量读取自动核对。配置向导只写入首次运行所需的内容，其余高级能力保持可选。

| 范围 | 主要设置 | 默认策略 |
|---|---|---|
| 模型 | `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL` | 一个 OpenAI 兼容接口即可启动。 |
| 人设 | `BOT_NAME`、`AGENT_LANG`、`PERSONA_FILE`、`PERSONA_CARD_FILE` | 示例人设；私有自定义文件不进入 Git。 |
| 运行状态 | `AGENT_RUNTIME_DIR`、`LOG_FILE` | 隔离在 `runtime/`；日志只输出到控制台。 |
| QQ | `BOT_QQ`、`QQ_GROUPS`、`NAPCAT_API`、`WEBHOOK_SECRET` | OneBot 直连接入；只绑定回环地址。 |
| 网关 | `GATEWAY_TOKEN`、`GATEWAY_OWNER_IDS`、`GATEWAY_NATIVE_PLATFORMS` | 身份带平台命名空间；默认无原生平台。 |
| 学习 | `REACT_*`、`PROMOTE_*`、`EVOLVE_*`、`EVAL_*` | 反应采集开启；保守晋升；无人值守进化关闭。 |
| 主动消息 | `PROACTIVE_*` | 关闭；不会主动联系从未出现过的会话。 |

```dotenv
AGENT_LANG=en  # 英文人设、数据、验证器与词表
# AGENT_LANG=zh  # 对应的中文资源
```

## 运维与开发

```bash
# 廉价存活探针——不会调用模型
curl http://127.0.0.1:8080/health

# 完整诊断——服务探针会消耗已配置模型的额度
python tools/healthcheck.py

# CI 使用的离线测试套件
python -m pip install -r requirements.txt "pytest>=8,<10"
python -m pytest -q
python -m compileall -q .
```

请将 `AGENT_RUNTIME_DIR` 与私有人设文件一起备份。这里包含记忆、证据、候选账本、已晋升视图、学习样例、去重状态和表情包元数据。不要提交运行状态：其中可能包含凭证、账号标识、对话片段、用户反应和学习内容。

仓库约定见 [CONTRIBUTING.md](CONTRIBUTING.md)；更新现有部署前请先查看 [CHANGELOG.md](CHANGELOG.md)。

<details>
<summary><strong>仓库结构</strong></summary>

```text
persona_agent/   可导入的应用核心
main.py          FastAPI 服务与后台循环
quickstart.py    可重复执行的配置向导
try_chat.py      经过生产回复链路的终端试用
integrations/    平台适配器（包含 AstrBot 转发插件）
data/            版本化的合成人设与检索种子
runtime/         私有可变状态（Git 忽略）
tools/           审核、调优、基准、导入和健康检查 CLI
tests/           离线跨平台回归测试
docs/            部署指南与架构图
```

</details>

## 负责任地使用

本项目与任何即时通信平台或模型供应商均无关联，也未获得其认可或赞助。第三方协议客户端可能违反上游条款或触发账号风控。请使用次要账号、默认保持私有部署、妥善保护密钥和对话数据，并在处理他人消息前取得适当同意。

完整部署说明见 [DISCLAIMER.md](DISCLAIMER.md)。

## 许可证

[MIT](LICENSE) © 2026 Qiankang Wang。

## 致谢

`personagent` 构建于 [OneBot v11](https://github.com/botuniverse/onebot-11) 事件模型、[NapCat](https://github.com/NapNeko/NapCatQQ)、[AstrBot](https://github.com/AstrBotDevs/AstrBot)、[FastAPI](https://github.com/fastapi/fastapi) 和 [httpx](https://github.com/encode/httpx) 之上；学习机制参考了 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557) 与 [BlenderBot 3x](https://arxiv.org/abs/2306.04707)。世界书和过滤器模型受到 SillyTavern World Info 与正则扩展的启发。
