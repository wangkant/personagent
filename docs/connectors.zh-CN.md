# 连接器协议

[English](connectors.md) · 简体中文 · [繁體中文](connectors.zh-TW.md) · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · [Español](connectors.es.md) · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

agent 本身从不直接与聊天平台交互，这项工作由连接器完成。连接器登录一个平台，或登录一个覆盖多个平台的框架，将收到的每条消息转换为中立的事件并发送给 personagent，再将返回的内容发送出去。所有与平台相关的内容都保留在连接器中，因此 agent 看到的格式在每个平台上都相同。

本仓库自带四个连接器：

| 连接器 | 可连接 | 路径 |
|---|---|---|
| 直连 | QQ 官方机器人、个人微信（iLink）、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat，无需其他软件。本地页面和 `personagent up` 使用一个进程运行它：`python -m persona_agent.direct`。 | `persona_agent/direct/` |
| AstrBot 插件 | 第三方桥接 AstrBot 支持的平台。personagent 为 KOOK、飞书/Lark、钉钉、Slack、企业微信、Mattermost、Misskey、OneBot v11 等管理的 AstrBot 会自动安装插件。对于已在运行的 AstrBot，请使用 `personagent connect astrbot` 进行设置。也可以通过 AstrBot 的“从文件安装”上传 GitHub Release 中的 `astrbot_plugin_personagent.zip`，然后自行设置 `connector_token`。 | `integrations/astrbot/` |
| Satori | 所有 Satori 实现（Koishi 等第三方）：QQ、Telegram、Discord、KOOK、Lark、钉钉、LINE、WhatsApp、Matrix、Zulip、电子邮件等。 | `integrations/satori/` |
| Matrix | Matrix 房间，并可通过第三方 mautrix 桥接连接到 WhatsApp、Signal、Messenger、Instagram、Google Messages 等。 | `integrations/matrix/` |

编程 agent 不是聊天平台，因此采用单独的方式：一个 MCP 服务器 `personagent mcp`，详见[使用手册](guide.zh-CN.md#编程助手)。

这四个连接器均使用本页描述的协议。编写新的连接器只需要本页和一个 HTTP 客户端。`integrations/sdk/personagent_connector.py` 中的 Python 辅助工具可代为签名请求并运行 outbox 循环。它接收基础 URL、令牌和连接器的 `connector_id`，并依赖 `httpx`。其 [README](../integrations/sdk/README.zh-CN.md) 提供了一个完整示例。

## 在本机试用

```
personagent run --port 8080
curl http://127.0.0.1:8080/health
```

`personagent run` 在 `127.0.0.1` 上提供下文的两个端点。它从启动横幅所示主目录的 `.env` 中读取 `CONNECTOR_TOKEN`；`--home DIR` 可指定其他主目录。

- `CONNECTOR_TOKEN` 为空时，agent 只接受本机上调用 `127.0.0.1` 或 `localhost` 的程序，这些程序无需发送认证请求头。`personagent init` 不会设置它。本地页面、`personagent up` 和 `personagent connect astrbot` 会在它为空时写入一个随机值。
- 如需设置，请在 `.env` 中写入一个足够长的随机值，例如 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 的输出，为连接器配置相同的值，然后重启 agent。
- `GET /health` 返回 `{"status": "ok", "agent_enabled": true}`，不产生任何费用。`"agent_enabled": false` 表示 agent 无法回答（没有 `LLM_API_KEY`，或 `AGENT_ENABLED=false`），此时每个事件都会得到 `owned: false`。`GET /health/details` 还会检查模型和其他服务，可能产生少量费用。设置了令牌时，它要求带上 `X-Personagent-Token` 请求头；未设置时只接受本机请求；其他请求会得到 `403` 和代码 `forbidden`。

## 配置

本地页面负责配置直连连接器。另外三个连接器使用相同的设置名称，因此同一设置在三者中的含义相同：

| 含义 | Satori | Matrix | AstrBot 插件键 |
|---|---|---|---|
| personagent 的基础 URL，例如 `http://127.0.0.1:8080`。连接器会追加 `/v1/events` 和 `/v1/outbox`。 | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| 共享令牌，等于 agent 的 `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| 此连接器的 id（即下文的 `connector_id`） | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| 一次请求最长耗时，单位秒 | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| 拉取 outbox | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| 要转发的群 | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| 要转发其私聊的人 | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| 平台的服务器 | `SATORI_URL` | `MATRIX_URL` | AstrBot 自身的设置 |

群或私聊列表为空时，该类消息均不转发。`*` 转发该类的全部内容，并将事件标记为 `"prefiltered": false`，交由 agent 的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 决定。其余设置见各连接器的 README。

## 地址

personagent 将每个 id 存储为 `<platform>:<id>`，例如群 `telegram:-1001234` 或用户 `discord:4242`。`platform` 是连接器为平台指定的名称，使用小写，且不含 `:`。

QQ 是唯一的例外，为兼容而保留。其 id 存储时不带前缀（`123456`），在任何设置中写 `qq:123456` 含义相同。如果连接器接入 QQ，且希望学到的状态与已有的 QQ 部署保持一致，请将其平台名称写入 `CONNECTOR_QQ_PLATFORMS`。AstrBot 插件的 QQ 适配器是 `aiocqhttp`。此处列出的平台，其 id 同样不带前缀存储。

## 认证

以下两个端点使用同一套方案。agent 设置了 `CONNECTOR_TOKEN` 时，每个请求都须带有四个请求头：

- `X-Personagent-Token`：令牌。
- `X-Personagent-Timestamp`：unix 秒。与 agent 时钟相差超过五分钟的值会被拒绝。
- `X-Personagent-Nonce`：一个新的随机值。重复使用的 nonce 会被拒绝。
- `X-Personagent-Signature`：`sha256=` 后接 `timestamp + "." + nonce + "." + body` 的十六进制 HMAC-SHA256，以令牌为密钥。

签名覆盖实际发送的请求体字节，因此任何 UTF-8 编码的有效 JSON 都能通过。推荐使用规范 JSON（键排序、紧凑分隔符、非 ASCII 字符不转义），本仓库自带的连接器也如此发送，但 agent 并不要求。令牌同时是签名密钥，因此请勿将其写入日志。

没有令牌时，agent 只接受直接调用 `127.0.0.1` 或 `localhost` 的本地程序。连接器必须拒绝发送到回环 URL 以外的地址，除非是带令牌的 HTTPS URL。

## 入站：`POST /v1/events`

每个请求携带一条消息，并返回对该消息的回复。

```json
{
  "platform": "telegram",
  "conversation_type": "group",
  "conversation_id": "-1001234",
  "sender_id": "42",
  "sender_name": "Alex",
  "bot_id": "7000",
  "message_id": "881",
  "sent_at": 1790320000,
  "addressed": true,
  "text": "Nova, how was your day?",
  "segments": [
    {"type": "text", "text": "Nova, how was your day?"}
  ],
  "connector_id": "astrbot-7f3c",
  "reply_handle": "tg-bot:GroupMessage:-1001234",
  "capabilities": ["outbox", "quote_text"]
}
```

必填字段是 `platform`、`conversation_type`（`group` 或 `dm`）、`sender_id`、`message_id` 和 `sent_at`，群聊还须包含 `conversation_id`。`sent_at` 是平台为消息标记的时间，单位为 unix 秒，取整数（也接受纯数字字符串）。角色看到的每条消息都附有这一时间。agent 启动后，在某个平台的第一条消息到达起两分钟内，如果群聊消息到达时已超过 10 分钟，即视为重启后补发的积压消息：只作为上下文保留，不予回复。两分钟之后，较早的 `sent_at` 不再使消息被搁下，因此时钟偏慢的连接器发来的消息仍会得到回复。请发送平台原始 id，前缀由 agent 添加。

`addressed` 由连接器设置。消息提及机器人、回复机器人的某条消息，或按平台自身规则是对机器人说的，该字段即为 true。agent 本身也会留意文本中出现的名称。它将对自身消息的引用或对机器人的 @ 视为可供学习的反应，因此回复机器人消息时须设置 `addressed`。对其他成员消息的引用从不视为对机器人的反应。转发消息中对机器人的提及不算对机器人说话，因此不要为此设置 `addressed`。

`sender_id` 等于 `bot_id` 的事件，是机器人自身消息的回传。agent 不读取即丢弃，并返回 `{"handled": false, "owned": true, "replies": []}`，以便连接器自身的机器人逻辑同样保持沉默。请在连接器中跳过此类事件。

片段按顺序排列：

| 类型 | 字段 | 说明 |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | 提及某人。`user_id` 等于 `bot_id` 时，即提及机器人。角色读到的是 `name` 而不是 id，因此请发送 `name`。`name` 交给模型时标明为并非发送者所写的名字，因此永远不会点名角色或构成命令。`forward` 片段之后对机器人的提及不算点名。 |
| `image` | `url` 或 `b64`，`sticker`（布尔值） | `sticker` 标记以图片形式发送的表情包。以 `b64` 发送或标有 `sticker` 的群聊图片可被收入表情包库；仅以 `url` 发送的照片不会被收入。 |
| `emoji` | `name`, `id` | agent 看不到的平台贴纸或自定义表情。`name` 是人们对它的通常称呼。 |
| `media` | `kind`, `name`, `transcript`, `emoji` | agent 看不到的内容。`kind` 为 `voice`、`video`、`file`、`photo`（无法获取的图片）或 `sticker`。文件请附上 `name`，平台已转写的语音请附上 `transcript`，表情请附上 `emoji`。 |
| `forward` | `name` | 其后的片段转发自 `name`，而非发送者本人所写。`name` 可以为空。这些片段中的文字视为被转发者的话：其中的名字不算点名，也不会执行记忆命令。发送者自己的评论请放在 `forward` 片段之前，或作为单独的消息发送。 |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | 该消息所引用的消息。平台提供 `text` 时一律发送。 |

媒体内容请以 `media` 片段发送，不要写成 `(sent a voice message)` 这样的文字：角色会把这些文字当作发送者本人输入的内容。agent 会丢弃未知类型的片段。

以下可选字段可启用 agent 的更多功能：

| 字段 | 含义 |
|---|---|
| `connector_id` | 此连接器实例的稳定 id。outbox 需要该字段。 |
| `reply_handle` | 连接器在未收到消息时也能联系到该会话所需的任何信息：AstrBot 的 `unified_msg_origin`、Matrix 房间 id，或 Satori 登录加频道 id。agent 把它当作不透明的值，按会话存储，并在 outbox 投递中交回。 |
| `capabilities` | 连接器的能力。`outbox` 表示其轮询 outbox，并可主动发送。`quote_text` 表示回复片段带有被引用的文字。 |
| `prefiltered` | 连接器应用了自己的允许列表时为 `true`（默认）。`false` 使 agent 的列表成为唯一的过滤器。 |
| `proactive` | 将私聊事件标记为连接器编写的提示，而非此人说的话。见“不经 outbox 主动发起对话”。 |

响应格式如下：

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`：按顺序发送，每条作为单独的消息。存在 `mention_user_id` 时，其值为要提及的带前缀 id。请按平台的方式呈现提及。带有 `"reason": "excuse"` 的条目是模型出错时角色在私聊中发送的简短说明，而非回复；可以照常发送，也可以作为错误处理。
- `owned`：agent 已接管该消息，即该消息已通过 agent 的允许列表，无论人设随后如何应对。为 true 时，即使 `replies` 为空，也须阻止其他机器人逻辑回答，因为人设可能选择了保持沉默。为 false 时，agent 未参与该消息：该会话不在 agent 的允许列表中，或 agent 根本无法回答（没有 `LLM_API_KEY`，或 `AGENT_ENABLED=false`）。agent 无法回答时，其日志中会有一行 ERROR 注明原因。重复的 `message_id` 仍由 agent 接管（见下文“重复消息”）。
- `handled`：本请求自身的一轮送出了内容（回复或记忆命令的回答）时为 true，用于日志和统计。请依据 `owned` 作判断，并且无论 `handled` 为何值，都发送 `replies` 中的全部内容：例如托词就随 `handled: false` 返回。

连接器会遇到以下组合：

| 响应 | 情形 | 连接器的处理 |
|---|---|---|
| `handled: true`，`owned: true`，有回复 | 正常回复。 | 发送 `replies`，并让其他机器人逻辑保持沉默。 |
| `handled: false`，`owned: true`，`replies: []` | 人设保持沉默；事件是机器人自身消息的回传；该消息已并入后一条消息的一轮（见“连发的消息”）；记忆命令的回答稍后经 outbox 送达；带有 `proactive` 的群事件；重复的 `message_id`（重投）。 | 不发送任何内容，并让其他机器人逻辑保持沉默。 |
| `handled: false`，`owned: true`，一条带 `"reason": "excuse"` 的回复 | 私聊中模型出错。 | 发送它，或作为错误处理。 |
| `handled: false`，`owned: false`，`replies: []` | 该会话不在允许列表中，或 agent 无法回答。 | 该消息由你处理。 |

其他规则：

- **重复消息。** agent 记住它最近接纳的 2,000 条消息，不分会话。键由 `platform`、会话（群为 `conversation_id`，私聊为 `sender_id`）和 `message_id` 组成；`CONNECTOR_QQ_PLATFORMS` 中的平台只用不带前缀的 `message_id`。该列表会不时保存到主目录的 `runtime/` 文件夹，关闭时也会保存，因此重启后依然有效。再次发送的消息（例如平台重投，或超时后的重试）会立即得到 `{"handled": false, "owned": true, "replies": []}`，即使第一次请求仍在进行。对此不要发送任何内容；其回复只出现在第一次请求的响应中。调用方放弃后，该轮仍会继续，因此超时后回复就会丢失；请预留足够的时间，而不要重试。被允许列表拒绝的消息不会被记住，再次发送时会重新判断。
- **连发的消息。** 同一会话中在短暂防抖时间内到达的消息（2.5 秒；群聊中只喊人设名字的消息之后为 5 秒）合并为一轮，一并作答。在进行中的一轮之后等待的消息，同样会并入下一轮。只有最新一条消息的请求携带回复；之前的每个请求都返回 `{"handled": false, "owned": true, "replies": []}`。在群聊中，回复的 `mention_user_id` 指向人设所回答的人，此人发送的可能是较早的消息，而不是携带回复的那个请求的消息。记忆命令不合并，见最后一条。
- 请求会持续到该轮结束，即一小段防抖时间加上模型的用时。不论群聊还是私聊，一轮的所有模型调用（含重试）共用一份 1.5 × `LLM_TIMEOUT_S` 的时间预算；如果消息到达时同一会话的上一轮仍在思考，它会先等待那一轮结束。请至少预留 3 × `LLM_TIMEOUT_S` 秒（默认为 360 秒）。
- 如果记忆命令（例如“记住……”）到达时，同一会话的某一轮仍在思考，该命令会等待那一轮结束后才得到回答。声明了 `outbox` 的连接器会立即收到 `{"handled": false, "owned": true, "replies": []}`，回答稍后作为 `follow_up` 投递送达。没有 `outbox` 时，回答随某个响应返回：可能是该命令自身的响应，也可能是同一会话中另一个正在等待的请求的响应，因此一个响应中可能包含提及事件发送者以外的人的回复。

## Outbox：`POST /v1/outbox`

有些消息并非对请求的回答，例如定时的开场白、被拒绝后的追问、排在某一轮之后的记忆命令的回答，以及群聊中模型不可用时的托词。agent 按会话将其排队，由声明了 `outbox` 的连接器拉取，因此位于 NAT 或防火墙之后的连接器也能正常工作。以不带前缀的 QQ id 存储的会话（见“地址”）在其连接器拉取期间也使用 outbox。否则，设置了 `QQ_ONEBOT_URL` 时，它们通过 NapCat 的 HTTP API 发送。

请求：

```json
{
  "kind": "outbox.pull",
  "connector_id": "astrbot-7f3c",
  "wait_s": 25,
  "max_deliveries": 10,
  "acks": [
    {"delivery_id": "d_5c1f...", "status": "sent", "sent_items": 2}
  ]
}
```

agent 最多将请求挂起 `wait_s` 秒（上限 30），直到有内容排队，然后返回：

```json
{
  "deliveries": [
    {
      "delivery_id": "d_9a07...",
      "conversation_key": "telegram:-1001234",
      "reply_handle": "tg-bot:GroupMessage:-1001234",
      "platform": "telegram",
      "conversation_type": "group",
      "conversation_id": "-1001234",
      "reason": "proactive",
      "expires_in_s": 300,
      "items": [{"type": "text", "text": "anyone still up?"}]
    }
  ],
  "next_wait_s": 25
}
```

`items` 的结构与 `replies` 相同。`reason` 是 `proactive`、`follow_up` 或 `excuse`，`conversation_type` 是 `group` 或 `dm`。`conversation_key` 是 agent 存储该会话所用的键，例如私聊的 `private:telegram:42`。`conversation_id` 是事件带来的原始 id，私聊时即为用户 id。agent 记录每个会话最近一条被接纳事件中的 `reply_handle`、`connector_id` 和 `capabilities`，因此会话只要发送过一条消息，即可被联系到。有一项例外，用于保留拉取 outbox 的连接器：来自不具备 `outbox` 能力的连接器的事件，不会替换另一个具备该能力的连接器为同一会话保存的信息。因此，即使其他程序（例如编程助手）在该会话中发过言，拉取 outbox 的连接器仍可联系到该会话。来自同一连接器的事件，或来自任何声明了 `outbox` 的连接器的事件，仍照常替换已保存的信息。

本地页面本身也是一个 outbox 连接器，其 `connector_id` 为 `local-welcome`。它只接收发往本页面对话的投递，并将其显示在「开始聊天」视图中。

请在下一次拉取的 `acks` 中报告每次投递：

| `status` | 含义 |
|---|---|
| `sent` | 所有项目均已发出。 |
| `partial` | 前 `sent_items` 项已发出。 |
| `failed` | 未发出任何内容。 |
| `expired` | 未在 `expires_in_s` 内开始发送。 |
| `refused` | 连接器不再允许该会话。 |
| `unsupported` | 平台无法主动向该会话发送。 |

规则：

- **最多一次。** 无论 ack 结果如何，agent 只交出一次投递，绝不重发。请保留最近几百个 `delivery_id`，同一投递绝不发送两次。
- **按顺序。** 一个会话的投递按收到的顺序发送。不同会话可以并行发送。
- **只有确认过的投递才算。** agent 将未确认的投递视为未发送，只将已确认的记为已发送。它会等待 ack 直到你下一次拉取，且交出投递后最多等待 `expires_in_s` 再加 60 秒。请发送完一批后再拉取。
- **存活。** 90 秒内未拉取的连接器视为已离开。在其再次拉取之前，不为其会话排队，已排队或已交付但未确认的内容均以未发送结束。一批送达后请立即再次拉取，该次拉取同时携带这一批的确认。
- **`unsupported` 会保持。** 收到此确认后，agent 停止为该会话排队，直到某个事件带来不同的 `reply_handle`。
- **请求体类型。** 签名不覆盖 URL 路径。因此，agent 拒绝发到 outbox 端点的事件请求体和发到事件端点的 `outbox.pull` 请求体，返回 `400` 和代码 `invalid_schema`。事件可以带 `"kind": "event"`。带其他 `kind` 的事件会被拒绝。

没有 `code` 的 404 表示 agent 不提供 outbox。带有代码 `outbox_disabled` 的 `404` 表示运营者已通过 `CONNECTOR_OUTBOX_ENABLED` 将其关闭。两种情况下都应间隔较长时间再拉取。

## 错误

出错时返回 `{"error": "...", "code": "..."}`。`code` 保持稳定，请依据它分支处理。`error` 是给查看日志的人阅读的句子，措辞可能变化。

| 状态码 | `code` | 端点 | 原因 |
|---|---|---|---|
| 400 | `invalid_schema` | 两者 | 请求体不是 JSON 对象；缺少必填字段或字段为空；`conversation_type` 既不是 `group` 也不是 `dm`；`segments` 不是列表；请求体类型错误（见“请求体类型”）；拉取请求没有可用的 `connector_id`（最多 128 个字符），`wait_s` 或 `max_deliveries` 不是数字，或 ack 超过 1,000 条。 |
| 400 | `client_disconnected` | 两者 | 调用方在发送请求体时断开了连接。 |
| 403 | `unauthenticated` | 两者 | 没有 `CONNECTOR_TOKEN`，且调用方不在 agent 所在的机器上。 |
| 403 | `non_local_request` | 两者 | 没有 `CONNECTOR_TOKEN`，且请求带有本地程序不会发送的请求头：`Origin`、值不为 `none` 的 `Sec-Fetch-Site`、`localhost`、`127.0.0.1` 和 `::1` 以外的 `Host`，或 `X-Forwarded-For` 之类的代理请求头。 |
| 403 | `invalid_envelope` | 两者 | 设置了 `CONNECTOR_TOKEN`，而令牌或某个请求头缺失或错误、签名不匹配、时间戳相差超过五分钟、nonce 已用过，或重放防护已满。 |
| 403 | `stale_event` | events | `sent_at` 不是整数秒，或与 agent 的时钟相差超过 `CONNECTOR_MAX_EVENT_AGE_S`（24 小时），无论偏早还是偏晚。以毫秒为单位的值会落在遥远的未来。 |
| 404 | `outbox_disabled` | outbox | `CONNECTOR_OUTBOX_ENABLED=false`，或 agent 已关闭（`AGENT_ENABLED=false`）。 |
| 408 | `body_timeout` | 两者 | 请求体超过 30 秒仍未送达。 |
| 413 | `body_too_large` | 两者 | 请求体大于 `SERVER_MAX_BODY_BYTES`（8,000,000 字节），通常是内联图片所致。 |
| 429 | `capacity_exceeded` | 两者 | 同时请求过多：事件端点进行中的轮次超过 `CONNECTOR_MAX_INFLIGHT`（默认 64），或 outbox 的拉取超过 16 个。`Retry-After` 响应头给出需等待的秒数：3，outbox 为 5。 |

路径错误会得到 `404 {"detail": "Not Found"}`，方法错误（例如 `GET /v1/events`）会得到 `405 {"detail": "Method Not Allowed"}`。这两种响应来自 Web 框架，不带 `code`。

## 不经 outbox 主动发起对话

不能轮询的连接器也可以主动开启私聊。其自身的调度器（例如 AstrBot 插件任务或 cron 条目）向 `/v1/events` 发送一个带有 `"proactive": true` 的普通私聊事件。agent 将文本视为给人设的提示（“他们安静一天了；今天早上有考试”），截断至 500 字符，绝不将其存储为此人说的话。引擎的主动发言指令仍决定该轮的行为，也可能让人设保持沉默。如果人设发言，回复会在响应中返回，由调度器转发。

此事件需要连接器普通事件所带的全部内容：签名请求头、所有必填字段、与连接器向此人发送时相同的 `platform` 和原始 `sender_id`、非空文本，以及每次都不同的 `message_id`。`message_id` 重复的事件不会再次处理，并得到 `owned: true` 且没有回复。此提示与 agent 自身的开场白计入同一个私聊冷却（`PROACTIVE_DM_COOLDOWN_S`），且不计为此人的活动。

务必设置此标记；否则 agent 会将提示存储为此人说的话。带有此标记的群事件会被接管（`owned: true`，因此连接器会让自身的机器人保持沉默），且不读取即丢弃。

## 能力和降级

| 缺少 | 影响 |
|---|---|
| `outbox` | 没有定时开场白和追问，群聊中模型调用失败时也没有托词。设置了 `QQ_ONEBOT_URL` 且可访问时，QQ id 仍可通过 NapCat 获得这些功能。私聊的托词在响应的 `replies` 中返回，无需 outbox。 |
| `quote_text` | agent 只能理解对其自身见过的消息的引用。 |
| `reply_handle` | 与缺少 `outbox` 相同。 |
| `addressed` 错误 | 人设会将对其说的话视为背景闲聊。 |

## 编写连接器

1. 从平台接收消息。跳过机器人自身的消息以及非消息事件（入群、撤回、戳一戳）。
2. 构造上面描述的事件。根据平台自身的提及和回复规则设置 `addressed`。
3. 签名并发送事件。按顺序发送 `replies`，`owned` 为 true 时让其他机器人逻辑保持沉默。
4. 如果平台支持主动发送，请加上 `connector_id`、`reply_handle` 和 `capabilities: ["outbox"]`，然后运行拉取循环：拉取，通过 `reply_handle` 送出每次投递，在下一次拉取时确认。

`integrations/sdk/personagent_connector.py` 负责第 3 和第 4 步。其 [README](../integrations/sdk/README.zh-CN.md) 用一个简短的程序演示了这两步。
