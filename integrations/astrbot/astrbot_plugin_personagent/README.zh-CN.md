# astrbot_plugin_personagent

[English](README.md) · **简体中文**

这是连接 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 与 [personagent](https://github.com/wangkant/personagent) 的插件。它把允许的消息转发给 personagent，再把 personagent 的回复发回聊天。

## 你需要它吗

QQ、微信、Telegram、Discord 不需要这个插件，personagent 会直接连接它们，不经过 AstrBot。运行 `personagent` 打开本地页面，在「连接平台」里添加即可。

只有 AstrBot 负责收发消息时才需要这个插件，分两种情况：

- **在 personagent 页面里添加其他平台**：KOOK、飞书、钉钉、Slack、企业微信智能机器人、Mattermost、Misskey，以及「高级」一栏里的平台，都经由 AstrBot 接入。页面会替你下载并运行 AstrBot，并装好这个插件，你无需在这里做任何操作。
- **使用你已有的 AstrBot**，保留它原有的平台和插件。按下面的步骤安装。

## 功能

- 把白名单内群聊和私聊的消息转发到 personagent 的 `POST /v1/events`，再把回复发回聊天。回复可以包含文字和图片，群聊中按 personagent 的要求 @ 对方。
- 按各平台适配器的实际格式解析消息，包括谁被 @、引用了哪条消息、表情和图片、语音，以及消息的实际发送时间。
- 拉取 personagent 的 outbox，发送它主动说的话，例如定时开场、追问，以及模型不可用时在群里的致歉。
- personagent 接管某个会话后，阻止 AstrBot 自带的模型继续回答（`block_default`），避免两个声音同时回复。

人设、记忆、防抖和「打字」节奏都由 personagent 处理。插件只负责格式转换。

## 装进你自己的 AstrBot

先启动一次 AstrBot，让它生成 data 文件夹（其中有 `cmd_config.json`、`plugins`、`config`），再安装 personagent（`python -m pip install personagent`）。然后运行：

```bash
personagent connect astrbot
```

这条命令会自动查找 AstrBot 的 data 文件夹，找不到时可以替你下载 AstrBot。接着它会询问 AstrBot 是否运行在 Docker 里、机器人加入哪个平台（AstrBot 里尚未配置时还会要该平台的 Token）、哪些群、管理员是谁、允许哪些人私聊；经 NapCat 接 QQ 时还会询问机器人账号的 QQ 号。最后它复制插件，生成同一个 `CONNECTOR_TOKEN` 写入两边，并写好白名单。`personagent init --terminal` 的最后一步也提供同样的流程。完成后重启 AstrBot，再运行 `personagent run`（只启动服务本身）。

如果不想逐项回答，可以直接指定文件夹：`personagent connect astrbot <data 文件夹>`，要经 NapCat 接 QQ 时再加 `--qq`。这种方式首次连接时白名单为空，需要在 AstrBot 网页的插件设置里填写 `groups`（群）和 `dm_users`（允许私聊的人）。这条命令可以重复运行，已有的白名单会保留。

也可以从 personagent 的[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下载 `astrbot_plugin_personagent.zip`，在 AstrBot 插件页通过「从文件安装」上传。之后把 `connector_token` 设为 personagent 的 `.env` 中的 `CONNECTOR_TOKEN`，并填好白名单。AstrBot 与 personagent 不在同一台电脑上时，`personagent_url` 必须是 HTTPS 地址（见下文「AstrBot 在 Docker 里」）。升级时用同样的方式上传新版 zip。AstrBot 4.29 及以后的版本会直接替换旧版；更早的版本需要先卸载旧插件，卸载时不要勾选「同时删除插件配置文件」。

手动安装：把本文件夹复制到 `<AstrBot data>/plugins/astrbot_plugin_personagent/`，重启 AstrBot，然后在网页里填写设置。

插件**默认不转发任何消息**：白名单为空时，AstrBot 的表现与未安装插件时相同。群号和用户 ID 按 AstrBot 显示的格式填写，在聊天中发送 `/sid` 即可查看。不带前缀的 ID 对所有适配器生效；`qq_official:ID` 只对该适配器生效，`qq_official:*` 放行该适配器上的全部同类会话。

## 设置

| 设置 | 默认值 | 说明 |
| --- | --- | --- |
| `personagent_url` | `http://127.0.0.1:8080` | personagent 的基础地址，插件会自动加上 `/v1/events` 和 `/v1/outbox`。只能是本机地址，或已设置 `connector_token` 的 HTTPS 地址。 |
| `connector_token` | 空 | 共享密钥，必须与 personagent 的 `CONNECTOR_TOKEN` 一致。地址不是本机时必须填写。 |
| `timeout_s` | `420` | 每次请求最多等待的秒数。应大于 personagent 的 `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`，见下文「超时」。 |
| `excluded_platforms` | `["aiocqhttp"]` | 不转发的适配器。要经 NapCat 接 QQ，需从中删除 `aiocqhttp`，见下文「经 NapCat 接 QQ」。 |
| `groups` | 空 | 要转发的群 ID。为空时不转发任何群；`适配器:ID` 或 `适配器:*` 只对一个适配器生效；单独的 `*` 表示全部转发，由 personagent 的 `ACCESS_GROUPS` 决定是否回应。 |
| `dm_users` | 空 | 允许私聊的发送者 ID。为空时不转发私聊；`适配器:ID` 或 `适配器:*` 只对一个适配器生效；单独的 `*` 表示全部转发，由 personagent 的 `ACCESS_DM_USERS` 决定是否回应。 |
| `block_default` | 开 | personagent 接管会话后，不再让 AstrBot 自带的模型回答。 |
| `forward_quoted_text` | 开 | 有人引用消息时，把被引用的文字和作者一并发给 personagent（平台提供时）。 |
| `quote_max_chars` | `200` | 被引用文字的最大长度，超出部分截断。 |
| `max_inline_image_bytes` | `4000000` | 内嵌发送图片的最大字节数，超过时只发送 `(sent an image)` 提示。应小于 personagent 的 `VISION_MAX_IMAGE_BYTES`。 |
| `outbox_enabled` | 开 | 拉取并发送 personagent 主动说的话。 |
| `outbox_wait_s` | `25` | 每次拉取 outbox 最多等待的秒数，上限 30。 |
| `connector_id` | 空 | 这个 AstrBot 在 personagent 中的标识。留空时自动生成并保存；两个 AstrBot 连接同一个 personagent 时，标识必须不同。 |

## 经 NapCat 接 QQ

QQ 官方机器人由 personagent 直接连接，不需要 AstrBot。本节只适用于用 NapCat（或其他 OneBot v11 实现）登录 QQ 账号、经 AstrBot 的 `aiocqhttp` 适配器接入的情况。在 personagent 页面里添加 OneBot v11 时，页面会自动从 `excluded_platforms` 删除 `aiocqhttp` 并设置 `CONNECTOR_QQ_PLATFORMS`。

1. 从 `excluded_platforms` 删除 `aiocqhttp`，把 QQ 群号填入 `groups`。
2. 在 personagent 的 `.env` 中设置 `CONNECTOR_QQ_PLATFORMS=aiocqhttp` 和 `QQ_BOT_ID`（机器人账号的 QQ 号）。`CONNECTOR_QQ_PLATFORMS` **不能省略**：缺少它时，personagent 会把所有 QQ 会话记在带 `aiocqhttp:` 前缀的 ID 下，原有 QQ ID 下学到的内容不再匹配，而且事后无法迁移。`personagent connect astrbot <data 文件夹> --qq` 会删除 `aiocqhttp` 并设置 `CONNECTOR_QQ_PLATFORMS`；不指定文件夹运行时，它还会询问 `QQ_BOT_ID`。
3. 如果 NapCat 还在把事件直接发给 personagent 的 `/v1/onebot`，请关闭。这条路线已弃用，两者同时开启会让每条消息被处理两次。
4. 由于 QQ 的 ID 不带前缀，personagent 自身的 QQ 设置依然生效：`ACCESS_GROUPS` 中列出了 QQ 群时，只回应列出的群（未列出任何 QQ 群则回应所有 QQ 群）；QQ 私聊只回应 `ADMIN_IDS` 中的管理员或 `ACCESS_DM_USERS` 中的人。以后新增 QQ 群时，要同时加入插件的 `groups` 和 `ACCESS_GROUPS`。

NapCat 的 HTTP 服务是可选的。开启后把它的地址填入 `QQ_ONEBOT_URL`，personagent 就能补回离线期间漏掉的 @（这同样需要 `QQ_BOT_ID`）。插件在拉取 outbox 时，主动消息、追问和群里的致歉都经插件发送；否则在设置了该地址的前提下，直接经 NapCat 发送。

这条路线的简要步骤见 [docs/deploy.zh-CN.md 的「第三方路线：AstrBot + NapCat」](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md#第三方路线astrbot--napcat)。

让 AstrBot 接入消息较多的 QQ 群之前，请检查 AstrBot 自身的两项设置，它们在插件之前生效：`platform_settings.rate_limit` 默认每 60 秒 30 条，超出的消息会被延迟处理，可以调高或关闭；`content_safety.internal_keywords` 默认开启，会丢弃命中关键词的消息，包括角色本该回答的消息。

## AstrBot 在 Docker 里

在容器内，`127.0.0.1` 指向容器自身，插件无法访问宿主机上的 personagent；而发往其他地址的明文 `http://` 请求会被插件拒绝。可以任选一种方式解决：

- 让 AstrBot 使用主机网络：在 compose 文件中写 `network_mode: host`，或使用 `docker run --network host`。Docker Desktop 需要 4.34 或更高版本，并开启 host networking。同一 compose 文件中的 NapCat 也要使用主机网络。
- 为 personagent 提供一个 HTTPS 地址（反向代理或隧道），再用 `personagent connect astrbot <data 文件夹> --url https://你的地址` 写入插件设置。

personagent 运行在另一台机器上时，同样需要 HTTPS 地址，并在两边设置相同的 token。在 personagent 前面加反向代理或隧道之前，请先在两边设好 token。

## 超时

每次请求都要等 personagent 完成一个完整的回合，包括一小段防抖时间，以及每次模型调用和重试。`timeout_s` 用尽后，personagent 仍会完成这个回合并保留学到的内容，但这条回复不会被任何人看到，AstrBot 自带的模型还会以另一种口吻回答同一条消息。

personagent 的默认值为 `LLM_TIMEOUT_S=120`、`LLM_MAX_RETRIES=2`，最坏情况下一个回合超过 360 秒，插件默认的 420 秒足以覆盖。如果在 personagent 中调大了这两项，`timeout_s` 也要相应调大。

## 出了问题

插件在 AstrBot 日志中的消息都以 `personagent:` 开头。

| 日志 | 处理方法 |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` 是发往其他主机的明文 HTTP，或未设置 token 的 HTTPS。见上文「AstrBot 在 Docker 里」。 |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` 为空或与 personagent 的 `CONNECTOR_TOKEN` 不一致；两台机器的时钟相差超过 5 分钟；或中间的代理改动了请求内容。 |
| `agent refused the request (403): stale or invalid sent_at` | 消息太旧，通常是 AstrBot 恢复连接后一次性补发了积压的消息。 |
| `agent refused the request (403): authentication required` 或 `only local requests accepted` | personagent 未设置 `CONNECTOR_TOKEN`，而请求并非来自本机。在两边设置相同的 token。 |
| `agent at capacity (429)` | personagent 同时处理的回合已达上限。如果经常出现，可调大它的 `CONNECTOR_MAX_INFLIGHT`。 |
| `agent rejected the body as too large (413)` | 通常是图片过大。调大 personagent 的 `SERVER_MAX_BODY_BYTES`。 |
| `timed out waiting for the agent` | 见上文「超时」。 |
| `agent request failed ...` | 通常是 personagent 没有运行，或 `personagent_url` 填错了。它是基础地址，不要带 `/v1/events`。 |
| `outbox: agent has no outbox ...` | personagent 关闭了 `CONNECTOR_OUTBOX_ENABLED`。 |

如果 AstrBot 自带的模型突然以另一种口吻回复，说明插件没有连上 personagent，或 personagent 没有接管这个会话。请先对照上表排查，再运行 `personagent doctor`。如果 personagent 是由本地页面启动的，打开页面上的「动态」，看消息有没有到达、它为什么没开口；用 `personagent run` 启动的，看它的终端输出。更多排查步骤见 [docs/deploy.zh-CN.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md#机器人不说话)。

各平台的支持情况、outbox 和请求签名的完整说明见英文版 [README.md](README.md)。
