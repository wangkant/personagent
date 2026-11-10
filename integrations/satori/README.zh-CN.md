# Satori 连接器

[English](README.md) · 简体中文 · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


这个连接器把 [personagent](https://github.com/wangkant/personagent) 接到 [Satori](https://satori.chat) 服务器。Satori 是一种跨平台聊天协议。[Koishi](https://koishi.chat)（配合它的 `server-satori` 插件）、Chronocat 或 LLOneBot 这样的服务器负责登录各聊天平台，这个客户端则通过一条 websocket 收到所有登录账号的每条消息。所以一个连接器进程就能把角色带到服务器有适配器的每个平台。

Satori 和 Koishi 是第三方软件。QQ、微信、Telegram、Discord 由 personagent 自己连接，本地页面通过 AstrBot 配置的平台也一样，这些都不需要它们。如果你已经在跑 Koishi，或者想要只有 Koishi 能连的平台，再用这个连接器。

连接器把每条允许的消息作为中立事件发到 agent 的 `POST /v1/events`（[docs/connectors.md](../../docs/connectors.zh-CN.md)），再把回复通过 Satori 发回去。它也会拉取 agent 的发件箱，所以定时开场、追问和致歉都能送到聊天里。

[satori-python](https://github.com/RF-Tar-Railt/satori-python) 负责 Satori 这一侧：websocket、登录列表和 HTTP API。这个连接器负责在 Satori 和 personagent 的事件格式之间转换，并用 [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py) 处理签名和发件箱循环。

## 配置（以 Koishi 为例）

1. **Koishi。** 用桌面启动器或 `npm init koishi@latest` 安装 Koishi。在它的控制台里添加并配置你的平台适配器，比如 `adapter-telegram` 或 `adapter-discord`，并确认机器人在线。启用 `server` 和 `server-satori` 插件。Koishi 随后会在 `http://127.0.0.1:5140/satori` 提供 Satori 服务。如果这台机器以外的东西能访问那个端口，给 `server-satori` 设一个 `token`。

   Koishi 的其他插件会继续运行。如果其中有也会回消息的，比如聊天模型或回复插件，它会和角色一起回复，连接器没法让它闭嘴。把那个插件关掉，或者把它的范围限制在你转发的会话之外。

2. **Agent。** 运行 personagent（`personagent run`，见它的 README）。如果连接器和 agent 不在同一台主机上，在 agent 的 `.env` 里设置 `CONNECTOR_TOKEN`，并把 agent 放到 HTTPS 后面。即使只有一台主机，也要在加代理或隧道之前先设好令牌。

3. **连接器。** 连接器是这个仓库里的脚本，所以需要一份仓库副本（克隆，或 GitHub 上的 ZIP）和它自己的 Python 环境，因为 `satori-python` 不是 personagent 的依赖。如果克隆里已经有 personagent 的 `.venv`，就装进这个环境：

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   如果你用 pip 从 PyPI 安装了 personagent，或者用 uvx 运行，就在副本旁边另建一个 venv：

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   在 Windows 上，解释器是 `.venv\Scripts\python.exe` 或 `connector-venv\Scripts\python.exe`。接着复制配置文件：

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   在 `integrations/satori/.env` 里设置 Satori 服务器的 URL 和令牌、agent 的基础 URL 和 `CONNECTOR_TOKEN`，以及要转发的会话（见[允许名单](#允许名单)）。然后用同一个解释器启动连接器：

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE` 读取另一个配置文件。每项配置也可以用环境变量给出，环境变量优先于文件。

4. **确认能用。** 服务器上的每个机器人都会在日志里显示一行，比如 `Satori login telegram:7000 is ONLINE`。在转发的群里提到机器人。agent 的日志会显示这一轮，回复会出现在聊天里。如果什么都没发生，设置 `SATORI_LOG_LEVEL=DEBUG`。

## 配置项

| 配置项 | 默认值 | 含义 |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | Satori 服务器。末尾的 `/v1` 可有可无。 |
| `SATORI_TOKEN` | | 服务器的令牌（在 Koishi 里是 `server-satori` → `token`）。 |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | agent 的基础 URL。会自动追加 `/v1/events` 和 `/v1/outbox`。 |
| `CONNECTOR_TOKEN` | | agent 的 `CONNECTOR_TOKEN`。 |
| `SATORI_GROUPS` | | 要转发的群，写频道或服务器 id，可以写成 `platform:id`。留空不转发，`*` 全部转发。 |
| `SATORI_DM_USERS` | | 转发哪些人的私聊，写用户 id，可以写成 `platform:id`。留空不转发，`*` 全部转发。 |
| `SATORI_PLATFORMS` | 全部 | 把连接器限制在这些 Satori 平台。 |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | 改写 agent 看到的平台名：`satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | 拉取 agent 的发件箱。 |
| `SATORI_CONNECTOR_ID` | 由 `SATORI_URL` 得出 | 这个连接器在 agent 那边的 id。请保持不变。 |
| `SATORI_TIMEOUT_S` | `420` | 一轮最长可以花多久。要大于 agent 的 3 × `LLM_TIMEOUT_S`。 |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | 在连接器里下载公开图片 URL，而不是把 URL 传给 agent。 |
| `SATORI_LOG_LEVEL` | `INFO` | |

agent 的 URL 必须是回环地址，或是设置了 `CONNECTOR_TOKEN` 的 HTTPS，否则连接器拒绝启动。如果 `SATORI_TOKEN` 会通过明文 `http` 发往其他主机，连接器会记一条警告。

## 允许名单

连接器默认拒绝。名单为空就什么都不转发。

- 群就是 Satori 频道。它的频道 id 或服务器 id 在 `SATORI_GROUPS` 里时才转发。所以在 Discord 或 KOOK 上，一个服务器 id 会放行该服务器的所有频道，每个频道仍是单独的会话。
- 发送者的用户 id 在 `SATORI_DM_USERS` 里时，才转发私聊。
- 条目可以写明平台，比如 `telegram:-1001234` 或 `discord:4242`，这样只在该平台匹配。不带平台的条目在所有平台匹配。
- `*` 转发所有群（或所有私聊），并把事件标记为 `prefiltered: false`。之后由 agent 自己的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 决定，那里没有条目的平台会被拒绝。

Koishi 的 `inspect` 插件会打印一条消息的平台、频道、服务器和用户 id。

## 平台名和 QQ

personagent 把 id 存成 `<platform>:<id>`，平台就是 Satori 登录账号的平台（`telegram`、`discord`、`onebot` 等）。第 4 步的日志行会显示它。有两种特殊情况：

- **通过 OneBot 的 QQ**（Koishi 的 `adapter-onebot`，后面接 NapCat 或 LLOneBot）用 QQ 号作为 id。要保留 agent 在已有 QQ 部署上学到的东西，把这个平台加到 agent 的 `CONNECTOR_QQ_PLATFORMS`（`CONNECTOR_QQ_PLATFORMS=onebot`）。这样它的 id 会不带前缀地存储，就像 NapCat 的 QQ 号一样，`ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 里的 QQ 条目也适用。只有 id 确实是 QQ 号的平台才能这样做。
- **QQ 官方机器人 API**（Koishi 的 `adapter-qq`）把平台叫作 `qq`，但它的 id 是 openid，不是 QQ 号。连接器把平台改名为 `qqbot`。`SATORI_PLATFORM_NAMES` 可以覆盖这个改名。personagent 也能不经 Koishi 自己连接 QQ 官方机器人。

## 支持情况

| 功能 | 状态 |
|---|---|
| 群聊和私聊 | 支持。私聊是 `DIRECT` 频道，或没有服务器的消息。 |
| 被叫到的判断（`addressed`） | 对机器人的 `<at>`（按 id，服务器不给 id 时按机器人的名字），以及回复机器人的消息。`@all` 算文本，不算提及。 |
| 引用消息 | 引用的文本、发送者和 id，取自 `<quote>` 元素或 `message.quote`。 |
| 收到的图片 | `data:` 和 `internal:` 图片以及 Satori 服务器上的图片会内联。公开 URL 传给 agent 自己获取。内网 URL 描述为 `(sent an image)`。每条消息最多下载 4 张，每张 4 MB。 |
| 贴纸和表情 | `<emoji>` 和 QQ 的 `<face>` 作为表情到达，角色知道自己看不见它们。 |
| 语音、视频、文件 | 用文字描述：`(sent a voice message)`、`(sent a video)`、`(sent a file: deck.pdf)`。 |
| 回复 | 文本，以及作为 `data:` URI 的图片，分别作为单独消息发出，中间有短暂间隔。在群里，agent 要求的提及会变成 `<at>`。 |
| 被动回复的平台 | 回复带上事件的 `referrer`，QQ 官方机器人 API 回复消息时需要它。 |
| 发件箱 | 定时开场、追问和致歉通过收到该会话的登录账号发到频道。连接器用由 `SATORI_TOKEN` 和 `CONNECTOR_TOKEN` 派生的密钥给每个回复句柄签名，只发给自己签过的句柄。改了其中任何一个令牌后，会话要再发一条消息才能重新送达。设置了 `CONNECTOR_OUTBOX_ENABLED=false` 的 agent 会回 404，连接器每 10 分钟重试一次。 |
| 正在输入提示 | 不支持。Satori 没有输入状态 API。 |
| `owned` | 遵守：连接器不再发送别的内容。但它拦不住 Koishi 的其他插件（见第 1 步）。 |

平台规则依然适用。比如 QQ 官方机器人 API 严格限制机器人主动发消息，所以那里的发件箱投递可能返回 `failed`。

## 测试

`tests/test_satori_connector.py` 不需要 satori-python 和网络。它模拟了元素对象、账号和 agent。
