# Satori 连接器

[English](README.md) · 简体中文 · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


本连接器将 [personagent](https://github.com/wangkant/personagent) 接入 [Satori](https://satori.chat) 服务器。Satori 是一种跨平台聊天协议。[Koishi](https://koishi.chat)（配合其 `server-satori` 插件）、Chronocat 或 LLOneBot 这类服务器负责登录各聊天平台，本客户端则通过一条 websocket 接收所有登录账号的每条消息。因此一个连接器进程即可将角色接入服务器具备适配器的每个平台。

Satori 和 Koishi 是第三方软件。QQ、微信、Telegram、Discord 由 personagent 直接连接，本地页面通过 AstrBot 配置的平台也是如此，这些平台均无需使用 Satori 或 Koishi。如果你已在运行 Koishi，或者需要接入只有 Koishi 能连接的平台，再使用本连接器。

连接器将每条允许的消息作为中立事件发送到 agent 的 `POST /v1/events`（[docs/connectors.md](../../docs/connectors.zh-CN.md)），再将回复通过 Satori 发回。它也会拉取 agent 的发件箱，因此定时开场、追问和致歉都能送达聊天。

[satori-python](https://github.com/RF-Tar-Railt/satori-python) 负责 Satori 一侧：websocket、登录列表和 HTTP API。本连接器负责在 Satori 和 personagent 的事件格式之间转换，并使用 [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py) 处理签名和发件箱循环。

## 配置（以 Koishi 为例）

1. **Koishi。** 使用桌面启动器或 `npm init koishi@latest` 安装 Koishi。在其控制台中添加并配置你的平台适配器，例如 `adapter-telegram` 或 `adapter-discord`，并确认机器人在线。启用 `server` 和 `server-satori` 插件。Koishi 随后会在 `http://127.0.0.1:5140/satori` 提供 Satori 服务。如果本机以外的程序能访问该端口，请为 `server-satori` 设置一个 `token`。

   Koishi 的其他插件会继续运行。如果其中有同样会回复消息的插件，例如聊天模型或回复插件，它会与角色同时回复，连接器无法使其停止。请关闭该插件，或将其作用范围限定在你转发的会话之外。

2. **Agent。** 运行 personagent（`personagent run`，见其 README）。如果连接器和 agent 不在同一台主机上，请在 agent 的 `.env` 中设置 `CONNECTOR_TOKEN`，并将 agent 部署在 HTTPS 之后。即使只有一台主机，在添加代理或隧道之前也须先设置令牌。

3. **连接器。** 连接器是本仓库中的脚本，因此需要一份仓库副本（克隆，或 GitHub 上的 ZIP）和独立的 Python 环境，因为 `satori-python` 不是 personagent 的依赖。如果克隆中已有 personagent 的 `.venv`，请安装到该环境中：

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   如果你使用 pip 从 PyPI 安装了 personagent，或者使用 uvx 运行，请在副本旁边另建一个 venv：

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   在 Windows 上，解释器是 `.venv\Scripts\python.exe` 或 `connector-venv\Scripts\python.exe`。接着复制配置文件：

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   在 `integrations/satori/.env` 中设置 Satori 服务器的 URL 和令牌、agent 的基础 URL 和 `CONNECTOR_TOKEN`，以及要转发的会话（见[允许名单](#允许名单)）。然后用同一个解释器启动连接器：

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE` 读取另一个配置文件。每项配置也可以通过环境变量指定，环境变量优先于文件。

4. **确认运行正常。** 服务器上的每个机器人都会在日志中显示一行，例如 `Satori login telegram:7000 is ONLINE`。在转发的群中提及机器人。agent 的日志会显示该轮处理，回复会出现在聊天中。如果没有任何反应，请设置 `SATORI_LOG_LEVEL=DEBUG`。

## 配置项

| 配置项 | 默认值 | 含义 |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | Satori 服务器。末尾的 `/v1` 可省略。 |
| `SATORI_TOKEN` | | 服务器的令牌（在 Koishi 中为 `server-satori` → `token`）。 |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | agent 的基础 URL。会自动追加 `/v1/events` 和 `/v1/outbox`。 |
| `CONNECTOR_TOKEN` | | agent 的 `CONNECTOR_TOKEN`。 |
| `SATORI_GROUPS` | | 需要转发的群，填写频道或服务器 id，可写为 `platform:id`。留空则不转发，`*` 表示全部转发。 |
| `SATORI_DM_USERS` | | 需要转发其私聊的用户，填写用户 id，可写为 `platform:id`。留空则不转发，`*` 表示全部转发。 |
| `SATORI_PLATFORMS` | 全部 | 将连接器限定于这些 Satori 平台。 |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | 改写 agent 看到的平台名：`satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | 拉取 agent 的发件箱。 |
| `SATORI_CONNECTOR_ID` | 由 `SATORI_URL` 得出 | 本连接器在 agent 一侧的 id。请保持不变。 |
| `SATORI_TIMEOUT_S` | `420` | 一轮的最长耗时。须大于 agent 的 3 × `LLM_TIMEOUT_S`。 |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | 在连接器中下载公开图片 URL，而非将 URL 传给 agent。 |
| `SATORI_LOG_LEVEL` | `INFO` | |

agent 的 URL 必须是回环地址，或是设置了 `CONNECTOR_TOKEN` 的 HTTPS，否则连接器拒绝启动。如果 `SATORI_TOKEN` 会通过明文 `http` 发往其他主机，连接器会记录一条警告。

## 允许名单

连接器默认拒绝。名单为空时不转发任何内容。

- 群即 Satori 频道。只有其频道 id 或服务器 id 位于 `SATORI_GROUPS` 中时才会转发。因此在 Discord 或 KOOK 上，一个服务器 id 会放行该服务器的所有频道，每个频道仍是单独的会话。
- 只有发送者的用户 id 位于 `SATORI_DM_USERS` 中时，才会转发私聊。
- 条目可以注明平台，例如 `telegram:-1001234` 或 `discord:4242`，此时只在该平台匹配。不带平台的条目在所有平台匹配。
- `*` 转发所有群（或所有私聊），并将事件标记为 `prefiltered: false`。此后由 agent 自身的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 决定，那里没有条目的平台会被拒绝。

Koishi 的 `inspect` 插件会打印一条消息的平台、频道、服务器和用户 id。

## 平台名和 QQ

personagent 将 id 存储为 `<platform>:<id>`，平台即 Satori 登录账号的平台（`telegram`、`discord`、`onebot` 等）。第 4 步的日志行会显示平台名。有两种特殊情况：

- **通过 OneBot 的 QQ**（Koishi 的 `adapter-onebot`，后面接 NapCat 或 LLOneBot）用 QQ 号作为 id。如需保留 agent 在已有 QQ 部署上学到的内容，请将该平台加入 agent 的 `CONNECTOR_QQ_PLATFORMS`（`CONNECTOR_QQ_PLATFORMS=onebot`）。此后其 id 会不带前缀地存储，与 NapCat 的 QQ 号相同，`ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 里的 QQ 条目也适用。只有 id 确实为 QQ 号的平台才能这样设置。
- **QQ 官方机器人 API**（Koishi 的 `adapter-qq`）将平台命名为 `qq`，但其 id 是 openid，而非 QQ 号。连接器将平台重命名为 `qqbot`。`SATORI_PLATFORM_NAMES` 可以覆盖该重命名。personagent 也可以不经 Koishi 直接连接 QQ 官方机器人。

## 支持情况

| 功能 | 状态 |
|---|---|
| 群聊和私聊 | 支持。私聊是 `DIRECT` 频道，或没有服务器的消息。 |
| 点名判断（`addressed`） | 对机器人的 `<at>`（按 id；服务器未提供 id 时按机器人的名字），以及回复机器人的消息。`@all` 视为文本，不视为提及。 |
| 引用消息 | 引用的文本、发送者和 id，取自 `<quote>` 元素或 `message.quote`。 |
| 收到的图片 | `data:` 和 `internal:` 图片以及 Satori 服务器上的图片会内联。公开 URL 传给 agent 自行获取。内网 URL 描述为 `(sent an image)`。每条消息最多下载 4 张，每张 4 MB。 |
| 贴纸和表情 | `<emoji>` 和 QQ 的 `<face>` 作为表情到达，角色知道自己无法看到它们。 |
| 语音、视频、文件 | 以文字描述：`(sent a voice message)`、`(sent a video)`、`(sent a file: deck.pdf)`。 |
| 回复 | 文本，以及作为 `data:` URI 的图片，分别作为单独消息发出，中间有短暂间隔。在群中，agent 要求的提及会转换为 `<at>`。 |
| 被动回复的平台 | 回复带有事件的 `referrer`，QQ 官方机器人 API 回复消息时需要该字段。 |
| 发件箱 | 定时开场、追问和致歉通过收到该会话的登录账号发到频道。连接器使用由 `SATORI_TOKEN` 和 `CONNECTOR_TOKEN` 派生的密钥为每个回复句柄签名，只发送给自己签过名的句柄。修改其中任何一个令牌后，会话须再发送一条消息才能重新送达。设置了 `CONNECTOR_OUTBOX_ENABLED=false` 的 agent 会返回 404，连接器每 10 分钟重试一次。 |
| 正在输入提示 | 不支持。Satori 没有输入状态 API。 |
| `owned` | 遵守：连接器不再发送其他内容。但它无法阻止 Koishi 的其他插件（见第 1 步）。 |

平台规则依然适用。例如 QQ 官方机器人 API 严格限制机器人主动发送消息，因此在该平台上的发件箱投递可能返回 `failed`。

## 测试

`tests/test_satori_connector.py` 无需 satori-python 和网络。它模拟了元素对象、账号和 agent。
