# 连接器协议

[English](connectors.md) · 简体中文 · [繁體中文](connectors.zh-TW.md) · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · [Español](connectors.es.md) · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

agent 自己从不和聊天平台打交道，这件事由连接器来做。连接器登录一个平台，或登录一个覆盖多个平台的框架，把每条收到的消息转成中立的事件，发给 personagent，再把返回的内容送出去。所有平台相关的东西都留在连接器里，所以 agent 看到的格式在每个平台上都一样。

这个仓库自带四个连接器：

| 连接器 | 能连到 | 路径 |
|---|---|---|
| 直连 | QQ 官方机器人、个人微信（iLink）、Telegram 和 Discord，不需要其他软件。本地页面和 `personagent up` 用一个进程运行它：`python -m persona_agent.direct`。 | `persona_agent/direct/` |
| AstrBot 插件 | 第三方桥接 AstrBot 支持的平台。personagent 为 KOOK、飞书/Lark、钉钉、Slack、企业微信、Mattermost、Misskey、OneBot v11 等管理的 AstrBot 会自动装好插件。已经在运行的 AstrBot 用 `personagent connect astrbot` 设置。也可以用 AstrBot 的“从文件安装”上传 GitHub Release 里的 `astrbot_plugin_personagent.zip`，再自己设置 `connector_token`。 | `integrations/astrbot/` |
| Satori | 所有 Satori 实现（Koishi 等第三方）：QQ、Telegram、Discord、KOOK、Lark、钉钉、LINE、WhatsApp、Matrix、Zulip、电子邮件等。 | `integrations/satori/` |
| Matrix | Matrix 房间，并可通过第三方 mautrix 桥接连到 WhatsApp、Signal、Messenger、Instagram、Google Messages 等。 | `integrations/matrix/` |

编程 agent 不是聊天平台，所以走自己的路线：一个 MCP 服务器 `personagent mcp`，详见[使用手册](guide.zh-CN.md#编程助手)。

这四个连接器都使用本页描述的协议。写一个新的连接器，只需要本页和一个 HTTP 客户端。`integrations/sdk/personagent_connector.py` 里的 Python 辅助工具会替你签名请求并运行 outbox 循环。它接收基础 URL、令牌和连接器的 `connector_id`，并依赖 `httpx`。

## 配置

本地页面负责配置直连连接器。另外三个使用相同的名称，所以同一个设置在它们之中含义相同：

| 含义 | Satori | Matrix | AstrBot 插件键 |
|---|---|---|---|
| personagent 的基础 URL，比如 `http://127.0.0.1:8080`。连接器会追加 `/v1/events` 和 `/v1/outbox`。 | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| 共享令牌，等于 agent 的 `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| 这个连接器的 id（即下文的 `connector_id`） | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| 一次请求最长耗时，单位秒 | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| 拉取 outbox | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| 要转发的群 | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| 要转发其私聊的人 | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| 平台的服务器 | `SATORI_URL` | `MATRIX_URL` | AstrBot 自身的设置 |

群或私聊列表为空时，这一类都不转发。`*` 转发这一类的全部内容，并把事件标记为 `"prefiltered": false`，交由 agent 的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 决定。其余设置见各连接器的 README。

## 地址

personagent 把每个 id 存成 `<platform>:<id>`，比如群 `telegram:-1001234` 或用户 `discord:4242`。`platform` 是连接器给平台起的名字，用小写，不含 `:`。

QQ 是唯一的例外，为了兼容而保留。它的 id 存储时不带前缀（`123456`），在任何设置里写 `qq:123456` 都是同一个意思。如果连接器接入 QQ，又想让学到的状态和已有的 QQ 部署对上，就把它的平台名写进 `CONNECTOR_QQ_PLATFORMS`。AstrBot 插件的 QQ 适配器是 `aiocqhttp`。这里列出的平台，其 id 同样不带前缀存储。

## 认证

下面两个端点使用同一套方案。agent 设置了 `CONNECTOR_TOKEN` 时，每个请求都带四个请求头：

- `X-Personagent-Token`：令牌。
- `X-Personagent-Timestamp`：unix 秒。和 agent 时钟相差超过五分钟的值会被拒绝。
- `X-Personagent-Nonce`：一个新的随机值。重复使用的 nonce 会被拒绝。
- `X-Personagent-Signature`：`sha256=` 后接 `timestamp + "." + nonce + "." + body` 的十六进制 HMAC-SHA256，以令牌为密钥。

请求体是规范 JSON：UTF-8、键排序、紧凑分隔符，非 ASCII 字符不转义。令牌同时是签名密钥，所以不要让它进入日志。

没有令牌时，agent 只接受直接调用 `127.0.0.1` 或 `localhost` 的本地程序。连接器必须拒绝发送到回环 URL 以外的地址，除非是带令牌的 HTTPS URL。

## 入站：`POST /v1/events`

每个请求带来一条消息，并返回对它的回复。

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

必填字段是 `platform`、`conversation_type`（`group` 或 `dm`）、`sender_id`、`message_id` 和 `sent_at`，群聊还要加 `conversation_id`。`sent_at` 是平台给消息打上的时间，单位是 unix 秒。发送平台原始 id，前缀由 agent 添加。

`addressed` 由连接器设置。消息提及机器人、回复机器人的某条消息，或按平台自身规则是对机器人说的，它就为 true。agent 自己也会注意文本里出现的名字。它把对自己消息的引用或对机器人的 @ 视为可以学习的反应，所以回复机器人的消息要设置 `addressed`。对其他成员消息的引用从来不算对机器人的反应。

`sender_id` 等于 `bot_id` 的事件，是机器人自己的消息被回传。agent 不读就丢弃，并回答 `{"handled": false, "owned": true, "replies": []}`，这样连接器自己的机器人逻辑也保持安静。请在连接器里跳过这类事件。

片段按顺序排列：

| 类型 | 字段 | 说明 |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | 提及某人。`user_id` 等于 `bot_id` 时，就是提及机器人。 |
| `image` | `url` 或 `b64`，`sticker`（布尔值） | `sticker` 标记以图片形式发送的表情包。 |
| `emoji` | `name`, `id` | agent 看不到的平台贴纸或自定义表情。`name` 是人会怎样称呼它。 |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | 这条消息引用的消息。平台提供 `text` 时一律发送。 |

其他内容用文字描述，作为 `text` 片段，比如 `(sent a voice message)` 或 `(sent a file: deck.pdf)`。agent 会丢弃未知类型的片段。

下面这些可选字段能启用 agent 的更多功能：

| 字段 | 含义 |
|---|---|
| `connector_id` | 这个连接器实例的稳定 id。outbox 需要它。 |
| `reply_handle` | 连接器以后没有收到消息也能联系到这个会话所需的任何东西：AstrBot 的 `unified_msg_origin`、Matrix 房间 id，或 Satori 登录加频道 id。agent 把它当作不透明的值，按会话存储，并在 outbox 投递中交回。 |
| `capabilities` | 连接器能做什么。`outbox` 表示它轮询 outbox，并且可以主动发送。`quote_text` 表示回复片段带有被引用的文字。 |
| `prefiltered` | 连接器应用了自己的允许列表时为 `true`（默认）。`false` 让 agent 的列表成为唯一的过滤器。 |
| `proactive` | 把私聊事件标记为连接器写的提示，而不是这个人说的话。见“不用 outbox 先开口”。 |

响应是这样的：

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`：按顺序发送，每条作为单独的消息。`mention_user_id` 存在时，它是要提及的带前缀 id。按平台的方式呈现提及。
- `owned`：agent 已经接管这个会话。为 true 时，即使 `replies` 为空也要阻止其他机器人逻辑回答，因为这是人设选择了沉默。为 false 时，这条消息归你处理。要么这个会话不在 agent 的允许列表上，要么 agent 根本无法回答（没有 `LLM_API_KEY`，或 `AGENT_ENABLED=false`）。第二种情况下，agent 的日志里有一行 ERROR 写明原因。
- 请求会一直持续到这一轮结束，也就是一小段防抖加上模型的用时。不论群聊还是私聊，一轮的所有模型调用（含重试）共用一份 1.5 × `LLM_TIMEOUT_S` 的时间预算；如果消息到达时同一会话的上一轮还在思考，它会先等那一轮结束，再轮到自己。至少留出 3 × `LLM_TIMEOUT_S` 秒（默认是 360 秒）。
- 如果记忆命令（比如“记住……”）到达时，同一会话的某一轮还在思考，它会等那一轮结束后才得到回答。声明了 `outbox` 的连接器会立刻收到 `{"handled": false, "owned": true, "replies": []}`，回答稍后作为 `follow_up` 投递送达。没有 `outbox` 时，回答随某个响应返回：可能是它自己的响应，也可能是同一会话里另一个正在等待的请求的响应，所以一个响应里可能有提及事件发送者以外的人的回复。

## Outbox：`POST /v1/outbox`

有些消息不是对请求的回答，比如定时的开场白、被拒绝后的追问、排在一轮后面的记忆命令的回答，以及群里模型不可用时的托词。agent 按会话把它们排队，声明了 `outbox` 的连接器来拉取，所以 NAT 或防火墙后面的连接器也能照常工作。以不带前缀的 QQ id 存储的会话（见“地址”）在其连接器拉取期间也使用 outbox。否则，设置了 `QQ_ONEBOT_URL` 时，它们走 NapCat 的 HTTP API。

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

agent 最多把请求挂起 `wait_s` 秒（上限 30），直到有内容排队，然后回答：

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

`items` 的形状和 `replies` 相同。`reason` 是 `proactive`、`follow_up` 或 `excuse`，`conversation_type` 是 `group` 或 `dm`。`conversation_key` 是 agent 存储这个会话用的键，比如私聊的 `private:telegram:42`。`conversation_id` 是事件带来的原始 id，私聊时就是用户 id。agent 记住每个会话最新一条被接纳事件里的 `reply_handle`、`connector_id` 和 `capabilities`，所以会话只要发过一条消息就可以联系到。

在下一次拉取的 `acks` 里报告每次投递：

| `status` | 含义 |
|---|---|
| `sent` | 所有项目都发出去了。 |
| `partial` | 前 `sent_items` 项发出去了。 |
| `failed` | 什么都没发出去。 |
| `expired` | 没有在 `expires_in_s` 内开始发送。 |
| `refused` | 连接器不再允许这个会话。 |
| `unsupported` | 平台无法主动向这个会话发送。 |

规则：

- **最多一次。** 无论 ack 发生什么，agent 只交出一次投递，绝不重发。保留最近几百个 `delivery_id`，同一个绝不发两次。
- **按顺序。** 一个会话的投递按收到的顺序发送。不同会话可以并行发送。
- **只有确认过的投递才算。** agent 把未确认的投递视为未发送，只把确认过的记为已发送。它等待 ack 直到你下一次拉取，并且交出投递后最多等 `expires_in_s` 再加 60 秒。发完一批再拉取。
- **存活。** 90 秒没有拉取的连接器视为已离开。在它再次拉取之前，不为它的会话排队，已排队或已交给它但没有确认的内容都以未发送结束。一批送达后立刻再拉取。这次拉取也带上这批的确认。
- **`unsupported` 会保持。** 收到这个确认后，agent 停止为这个会话排队，直到某个事件带来不同的 `reply_handle`。
- **请求体类型。** 签名不覆盖 URL 路径。因此，agent 拒绝发到 outbox 端点的事件请求体和发到事件端点的 `outbox.pull` 请求体，返回 `400` 和代码 `invalid_schema`。事件可以带 `"kind": "event"`。带其他 `kind` 的事件会被拒绝。

没有 `code` 的 404 表示 agent 不提供 outbox。带代码 `outbox_disabled` 的 `404` 表示运营者用 `CONNECTOR_OUTBOX_ENABLED` 关闭了它。两种情况都要等很久再拉取。

## 不用 outbox 先开口

不能轮询的连接器也可以开启私聊。它自己的调度器，比如 AstrBot 插件任务或 cron 条目，向 `/v1/events` 发送一个带 `"proactive": true` 的普通私聊事件。agent 把文本当作给人设的提示（“他们安静一天了；今天早上有考试”），截断到 500 字符，绝不把它存成这个人说的话。引擎的主动发言指令仍然决定这一轮，也可能让人设保持沉默。如果人设开口，回复会在响应里返回，由调度器转发。

这个事件需要连接器普通事件带的所有内容：签名请求头、所有必填字段、连接器给这个人发送时相同的 `platform` 和原始 `sender_id`、非空文本，以及每次新的 `message_id`。`message_id` 重复的事件会被静默丢弃。这个提示和 agent 自己的开场白计入同一个私聊冷却（`PROACTIVE_DM_COOLDOWN_S`），并且不算这个人的活动。

一定要设置这个标记；没有它，agent 会把提示存成这个人说的话。带这个标记的群事件会被接管（`owned: true`，所以连接器让自己的机器人保持安静），并且不读就丢弃。

## 能力和降级

| 缺少 | 影响 |
|---|---|
| `outbox` | 没有定时开场白、没有追问，群里模型调用失败时也没有托词。设置了 `QQ_ONEBOT_URL` 且可达时，QQ id 仍能通过 NapCat 得到这些。私聊的托词在响应的 `replies` 里返回，不需要 outbox。 |
| `quote_text` | 只有 agent 自己见过的消息，它才能理解对该消息的引用。 |
| `reply_handle` | 和缺少 `outbox` 相同。 |
| `addressed` 错误 | 人设把对它说的话当成背景闲聊。 |

## 编写连接器

1. 从平台接收消息。跳过机器人自己的消息和不是消息的事件（入群、撤回、戳一戳）。
2. 构造上面描述的事件。根据平台自身的提及和回复规则设置 `addressed`。
3. 签名并发送事件。按顺序发送 `replies`，`owned` 为 true 时让其他机器人逻辑保持安静。
4. 如果平台可以主动发送，加上 `connector_id`、`reply_handle` 和 `capabilities: ["outbox"]`，然后运行拉取循环：拉取，通过 `reply_handle` 送出每次投递，在下一次拉取时确认。

`integrations/sdk/personagent_connector.py` 负责第 3 和第 4 步。
