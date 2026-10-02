# astrbot_plugin_personagent

[English](README.md) · **简体中文**

这是一个 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 插件，把 [personagent](https://github.com/wangkant/personagent) 带进 AstrBot 支持的所有平台：QQ、Telegram、Discord、Slack、KOOK、飞书、钉钉、LINE、企业微信等。

## 它做什么

- 把白名单里的群和私聊的每条消息，转发给 personagent 的 `POST /v1/events`，再把回复发回聊天里（文字、图片，群里按需 @ 对方）。
- 读懂各平台的差异：谁被 @ 了、引用了哪条消息、表情和图片、语音、消息真正的发送时间。
- 接收 personagent 主动说的话（定时开场、追问、模型挂了时的道歉），靠的是拉取它的 outbox。
- personagent 接管某个会话时，让 AstrBot 自带的模型闭嘴（`block_default`），避免两个声音同时回答。

人设、记忆、防抖和「打字」节奏都在 personagent 里，插件只负责翻译，不决定说什么。

## 安装

先启动一次 AstrBot，让它生成 data 文件夹（里面有 `cmd_config.json`、`plugins`、`config`），并装好 personagent（`uv tool install personagent`）。然后运行：

```bash
personagent connect astrbot
```

它会自己找 AstrBot 的 data 文件夹，复制插件，在两边写入同一个 `CONNECTOR_TOKEN`，并问你机器人进哪个平台、哪些群、管理员是谁。之后重启 AstrBot，运行 `personagent run`。

不想回答问题的话：`personagent connect astrbot <data 文件夹>`，QQ 再加 `--qq`。这样第一次白名单是空的，要在 AstrBot 的网页里自己填 `groups`（群）和 `dm_users`（允许私聊的人）。

插件**默认什么都不转发**：白名单为空时，AstrBot 就像没装这个插件。群号、用户 ID 按 AstrBot 显示的写，不带平台前缀（在聊天里发 `/sid` 可以看到）。

手动安装：把本文件夹复制到 `<AstrBot data>/plugins/astrbot_plugin_personagent/`，重启 AstrBot，在网页里填设置。

完整的 QQ 部署步骤（NapCat、AstrBot、personagent 从零开始）见 [docs/deploy.zh-CN.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)。

## 设置

| 设置 | 默认 | 说明 |
| --- | --- | --- |
| `personagent_url` | `http://127.0.0.1:8080` | personagent 的地址，插件会自己加 `/v1/events` 和 `/v1/outbox`。只能是本机地址，或者设了 `connector_token` 的 HTTPS 地址。 |
| `connector_token` | 空 | 共享密钥，必须和 personagent 的 `CONNECTOR_TOKEN` 一致。地址不是本机时必填。 |
| `timeout_s` | `180` | 每次请求最多等多少秒。要大于 personagent 的 `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`，见下文。 |
| `excluded_platforms` | `["aiocqhttp"]` | 不转发的适配器。要接 QQ，就把 `aiocqhttp` 从里面删掉。 |
| `groups` | 空 | 要转发的群 ID。空 = 一个都不转发；`*` = 全部转发，交给 personagent 的 `ACCESS_GROUPS` 决定。 |
| `dm_users` | 空 | 允许私聊的发送者 ID。空 = 不转发私聊；`*` = 全部转发。 |
| `block_default` | 开 | personagent 接管会话后，不再让 AstrBot 自带的模型回答。 |
| `forward_quoted_text` | 开 | 有人引用消息时，把被引用的文字和作者一起发给 personagent。 |
| `quote_max_chars` | `200` | 被引用的文字最多发多少字。 |
| `max_inline_image_bytes` | `4000000` | 内嵌发送的图片最大字节数。要小于 personagent 的 `VISION_MAX_IMAGE_BYTES`。 |
| `outbox_enabled` | 开 | 拉取并发送 personagent 主动说的话。 |
| `outbox_wait_s` | `25` | 每次拉取最多等多久（最多 30 秒）。 |
| `connector_id` | 空 | 这个 AstrBot 在 personagent 眼里的名字。留空会自动生成并保存；两个 AstrBot 连同一个 personagent 时要取不同的名字。 |

## 接 QQ

QQ 走 AstrBot 的 `aiocqhttp` 适配器，加 NapCat 这类 OneBot v11 实现。

1. 在 `excluded_platforms` 里删掉 `aiocqhttp`，把 QQ 群号填进 `groups`。
2. personagent 的 `.env` 里要有 `CONNECTOR_QQ_PLATFORMS=aiocqhttp` 和 `QQ_BOT_ID`（机器人小号的 QQ 号）。**不能省**：少了前者，所有 QQ 会话都会被当成新会话，学到的东西对不上，而且事后改不回来。`personagent connect astrbot <data 文件夹> --qq` 会替你写好。
3. 如果 NapCat 还把事件直接发给 personagent 的 `/v1/onebot`，要关掉，否则每条消息会收到两遍。
4. QQ 的号还受 personagent 自己的设置约束：`ACCESS_GROUPS` 里写了 QQ 群，就只放行写了的；QQ 私聊必须来自 `ADMIN_IDS` 或 `ACCESS_DM_USERS`。之后新增 QQ 群，要同时加进插件的 `groups` 和 `ACCESS_GROUPS`。

NapCat 的 HTTP 服务是可选的：开了，`QQ_ONEBOT_URL` 填它的地址，personagent 能补回离线期间漏掉的 @。

AstrBot 在很繁忙的 QQ 群里使用前，先看两个 AstrBot 自己的设置，它们在插件之前就生效：`platform_settings.rate_limit` 默认每 60 秒 30 条，超过的会被延迟；`content_safety.internal_keywords` 默认开启，会悄悄丢掉命中关键词的消息。

## AstrBot 在 Docker 里

在容器里，`127.0.0.1` 指的是容器自己，插件访问不到你电脑上的 personagent，而发往其他地址的明文 `http://` 会被拒绝。二选一：

- 给 AstrBot 用主机网络（compose 里写 `network_mode: host`，或 `docker run --network host`；Docker Desktop 需要 4.34 以上并打开 host networking）。同一个文件里的 NapCat 也要用主机网络。
- 给 personagent 一个 HTTPS 地址（反向代理或隧道），用 `personagent connect astrbot <data 文件夹> --url https://你的地址` 写进插件。

personagent 在另一台机器上时，也是 HTTPS 地址加两边相同的 token。

## 超时

一次请求要等 personagent 完成一整个回合：一小段防抖，加上每次模型调用和重试。`timeout_s` 到了，personagent 仍会把回合做完、记住学到的东西，但没人会看到那条回复，而且 AstrBot 自带的模型会用另一种口气回答同一条消息。

personagent 默认 `LLM_TIMEOUT_S=120`、`LLM_MAX_RETRIES=2`，最坏要 360 秒，超过插件默认的 180 秒。用的模型很慢，就调大 `timeout_s`，或者调小那两个设置。

## 出了问题

AstrBot 日志里，插件的消息都以 `personagent:` 开头。

| 日志里 | 怎么办 |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` 是发往其他主机的明文 HTTP，或者没配 token 的 HTTPS。见上面的 Docker 一节。 |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` 为空或和 personagent 的 `CONNECTOR_TOKEN` 不一致；两台电脑时钟差超过 5 分钟；或者中间的代理改了请求内容。 |
| `agent refused the request (403): stale or invalid sent_at` | 消息太旧，通常是 AstrBot 掉线后一次性补发了积压的消息。 |
| `agent refused the request (403): authentication required` 或 `only local requests accepted` | personagent 没设 `CONNECTOR_TOKEN`，而请求不是来自本机。两边设同一个 token。 |
| `agent at capacity (429)` | personagent 同时在处理的回合太多。可调大它的 `CONNECTOR_MAX_INFLIGHT`。 |
| `agent rejected the body as too large (413)` | 多半是一张大图。调大 personagent 的 `SERVER_MAX_BODY_BYTES`。 |
| `timed out waiting for the agent` | 见上面的「超时」。 |
| `agent request failed ...` | 多半 personagent 没在运行，或者 `personagent_url` 写错了（它是基础地址，不要带 `/v1/events`）。 |
| `outbox: agent has no outbox ...` | personagent 把 `CONNECTOR_OUTBOX_ENABLED` 关了。不影响别的功能。 |

AstrBot 自带的模型突然用另一种口气回话，说明插件没连上 personagent，或者 personagent 没接管这个会话：先看上表，再打开 `http://127.0.0.1:8080/`（personagent 的控制面板）和 `personagent doctor`。更多排查步骤见 [docs/deploy.zh-CN.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md#机器人不说话)。

完整的英文说明（各平台的支持情况、outbox、请求签名）见 [README.md](README.md)。
