# astrbot_plugin_personagent

[English](README.md) · **简体中文**

这是 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 把消息交给 [personagent](https://github.com/wangkant/personagent) 的插件：把允许的消息转发给 personagent，再把它的回复发回聊天里。

## 你需要它吗

QQ、微信、Telegram、Discord 用不到它：这几个由 personagent 自己连接，不经过 AstrBot。运行 `personagent` 打开本地页面，在「连接平台」里添加即可。

下面两种情况才需要这个插件：

- **在 personagent 页面里添加其他平台**（KOOK、飞书、钉钉、Slack、企业微信、Mattermost、Misskey，以及高级选项里的那些）。页面会替你下载并运行一个 AstrBot，并自动装好这个插件，这里什么都不用做。
- **你自己已经在用的 AstrBot**，带着它自己的平台和插件。按下面的步骤安装。

## 它做什么

- 把白名单里的群和私聊的每条消息，转发给 personagent 的 `POST /v1/events`，再把回复发回聊天里（文字、图片，群里按需 @ 对方）。
- 读懂各平台的差异：谁被 @ 了、引用了哪条消息、表情和图片、语音、消息真正的发送时间。
- 接收 personagent 主动说的话（定时开场、追问、群里模型挂了时的道歉），靠的是拉取它的 outbox。
- personagent 接管某个会话时，让 AstrBot 自带的模型闭嘴（`block_default`），避免两个声音同时回答。

人设、记忆、防抖和「打字」节奏都在 personagent 里，插件只负责翻译，不决定说什么。

## 装进你自己的 AstrBot

先启动一次 AstrBot，让它生成 data 文件夹（里面有 `cmd_config.json`、`plugins`、`config`），并装好 personagent（`python -m pip install personagent`）。然后运行：

```bash
personagent connect astrbot
```

它会自己找 AstrBot 的 data 文件夹（找不到时可以替你下载 AstrBot），复制插件，在两边写入同一个 `CONNECTOR_TOKEN`，并问你 AstrBot 是否在 Docker 里、机器人进哪个平台、哪些群、管理员是谁。`personagent init --terminal` 的最后一步也会问这些。之后重启 AstrBot，运行 `personagent run`（只启动服务本身）。

不想回答问题的话：`personagent connect astrbot <data 文件夹>`，要经 NapCat 接 QQ 再加 `--qq`。这样第一次白名单是空的，要在 AstrBot 的网页里自己填 `groups`（群）和 `dm_users`（允许私聊的人）。

也可以从 personagent 的[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下载 `astrbot_plugin_personagent.zip`，在 AstrBot 插件页的「从文件安装」上传，再把 `connector_token` 设成 personagent 的 `.env` 里的 `CONNECTOR_TOKEN`，并填好白名单。升级时上传新版 zip 即可（AstrBot 4.29 起会直接替换旧版）。

手动安装：把本文件夹复制到 `<AstrBot data>/plugins/astrbot_plugin_personagent/`，重启 AstrBot，在网页里填设置。

插件**默认什么都不转发**：白名单为空时，AstrBot 就像没装这个插件。群号、用户 ID 按 AstrBot 显示的写（在聊天里发 `/sid` 可以看到）。不带前缀的 ID 对所有适配器都生效；写成 `qq_official:ID` 只对这个适配器生效，`qq_official:*` 放行这个适配器上的全部会话。

## 设置

| 设置 | 默认 | 说明 |
| --- | --- | --- |
| `personagent_url` | `http://127.0.0.1:8080` | personagent 的地址，插件会自己加 `/v1/events` 和 `/v1/outbox`。只能是本机地址，或者设了 `connector_token` 的 HTTPS 地址。 |
| `connector_token` | 空 | 共享密钥，必须和 personagent 的 `CONNECTOR_TOKEN` 一致。地址不是本机时必填。 |
| `timeout_s` | `420` | 每次请求最多等多少秒。要大于 personagent 的 `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`，见下文。 |
| `excluded_platforms` | `["aiocqhttp"]` | 不转发的适配器。要经 NapCat 接 QQ，就把 `aiocqhttp` 从里面删掉，见下面「经 NapCat 接 QQ」。 |
| `groups` | 空 | 要转发的群 ID。空 = 一个都不转发；`适配器:ID` 或 `适配器:*` 只对一个适配器生效；单独的 `*` = 全部转发，交给 personagent 的 `ACCESS_GROUPS` 决定。 |
| `dm_users` | 空 | 允许私聊的发送者 ID。空 = 不转发私聊；`适配器:ID` 或 `适配器:*` 只对一个适配器生效；单独的 `*` = 全部转发，交给 personagent 的 `ACCESS_DM_USERS` 决定。 |
| `block_default` | 开 | personagent 接管会话后，不再让 AstrBot 自带的模型回答。 |
| `forward_quoted_text` | 开 | 有人引用消息时，把被引用的文字和作者一起发给 personagent。 |
| `quote_max_chars` | `200` | 被引用的文字最多发多少字。 |
| `max_inline_image_bytes` | `4000000` | 内嵌发送的图片最大字节数。要小于 personagent 的 `VISION_MAX_IMAGE_BYTES`。 |
| `outbox_enabled` | 开 | 拉取并发送 personagent 主动说的话。 |
| `outbox_wait_s` | `25` | 每次拉取最多等多久（最多 30 秒）。 |
| `connector_id` | 空 | 这个 AstrBot 在 personagent 眼里的名字。留空会自动生成并保存；两个 AstrBot 连同一个 personagent 时要取不同的名字。 |

## 经 NapCat 接 QQ

QQ 官方机器人由 personagent 自己连接，不需要 AstrBot。这一节只适用于用 NapCat（或其他 OneBot v11 实现）登录 QQ 号、经 AstrBot 的 `aiocqhttp` 适配器接入的情况。在 personagent 页面里添加 OneBot v11 时，删掉 `aiocqhttp` 和写 `CONNECTOR_QQ_PLATFORMS` 这两件事会自动完成。

1. 在 `excluded_platforms` 里删掉 `aiocqhttp`，把 QQ 群号填进 `groups`。
2. personagent 的 `.env` 里要有 `CONNECTOR_QQ_PLATFORMS=aiocqhttp` 和 `QQ_BOT_ID`（机器人小号的 QQ 号）。**不能省**：少了前者，所有 QQ 会话都会被当成新会话，学到的东西对不上，而且事后改不回来。`personagent connect astrbot <data 文件夹> --qq` 会替你写好。
3. 如果 NapCat 还把事件直接发给 personagent 的 `/v1/onebot`，要关掉，否则每条消息会收到两遍。
4. QQ 的号还受 personagent 自己的设置约束：`ACCESS_GROUPS` 里写了 QQ 群，就只放行写了的；QQ 私聊必须来自 `ADMIN_IDS` 或 `ACCESS_DM_USERS`。之后新增 QQ 群，要同时加进插件的 `groups` 和 `ACCESS_GROUPS`。

NapCat 的 HTTP 服务是可选的：开了，`QQ_ONEBOT_URL` 填它的地址，personagent 能补回离线期间漏掉的 @。

这条路线的简要步骤见 [docs/deploy.zh-CN.md 的「第三方路线：AstrBot + NapCat」](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md#第三方路线astrbot--napcat)。

AstrBot 在很繁忙的 QQ 群里使用前，先看两个 AstrBot 自己的设置，它们在插件之前就生效：`platform_settings.rate_limit` 默认每 60 秒 30 条，超过的会被延迟；`content_safety.internal_keywords` 默认开启，会悄悄丢掉命中关键词的消息。

## AstrBot 在 Docker 里

在容器里，`127.0.0.1` 指的是容器自己，插件访问不到你电脑上的 personagent，而发往其他地址的明文 `http://` 会被拒绝。二选一：

- 给 AstrBot 用主机网络（compose 里写 `network_mode: host`，或 `docker run --network host`；Docker Desktop 需要 4.34 以上并打开 host networking）。同一个文件里的 NapCat 也要用主机网络。
- 给 personagent 一个 HTTPS 地址（反向代理或隧道），用 `personagent connect astrbot <data 文件夹> --url https://你的地址` 写进插件。

personagent 在另一台机器上时，也是 HTTPS 地址加两边相同的 token。加反向代理或隧道之前，先在两边设好 token。

## 超时

一次请求要等 personagent 完成一整个回合：一小段防抖，加上每次模型调用和重试。`timeout_s` 到了，personagent 仍会把回合做完、记住学到的东西，但没人会看到那条回复，而且 AstrBot 自带的模型会用另一种口气回答同一条消息。

personagent 默认 `LLM_TIMEOUT_S=120`、`LLM_MAX_RETRIES=2`，最坏要 360 秒，插件默认的 420 秒够用。如果在 personagent 那边调大了这两个设置，`timeout_s` 也要跟着调大。

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

AstrBot 自带的模型突然用另一种口气回话，说明插件没连上 personagent，或者 personagent 没接管这个会话：先看上表，再运行 `personagent doctor`，并用它最后一行打印的链接打开 personagent 的控制面板。更多排查步骤见 [docs/deploy.zh-CN.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md#机器人不说话)。

完整的英文说明（各平台的支持情况、outbox、请求签名）见 [README.md](README.md)。
