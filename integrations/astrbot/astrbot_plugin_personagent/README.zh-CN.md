# astrbot_plugin_personagent

[English](README.md) · 简体中文 · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


本 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 插件将 AstrBot 连接到 [personagent](https://github.com/wangkant/personagent)。插件将每条允许的消息转发给 personagent，再将 personagent 的回复发回聊天。

## 是否需要本插件

QQ、微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 不需要本插件。personagent 会直接连接这些平台，不经过 AstrBot。运行 `personagent` 打开本地页面，在 **连接平台** 中添加即可；也可以在终端中运行 `personagent connect <平台>`。

只有在由 AstrBot 负责收发消息时才需要本插件，分为两种情况。

- **在 personagent 页面中添加其他平台。** KOOK、飞书、钉钉、Slack、企业微信智能机器人、Mattermost、Misskey，以及「高级」分组中的平台，均经由 AstrBot 接入。页面会代为下载并运行 AstrBot，并安装本插件，你无需在此进行任何操作。
- **你已在运行 AstrBot**，且其已有自己的平台和插件。请按以下步骤安装插件。

## 功能

- 接收 AstrBot 所有平台适配器（Telegram、Discord、Slack、QQ……）的群消息和私聊，`excluded_platforms` 中的除外。
- 将白名单内的群和发送者的消息，以平台中立的事件转发到 personagent 的 `POST /v1/events`。插件按各适配器的实际交付方式读取消息，包括谁被 @、引用了什么、表情、图片、语音，以及平台记录的发送时间。
- 经 AstrBot 将 personagent 的回复按各平台要求的形式发回。回复可以包含文字和图片，在群聊中可按 personagent 的要求带上 @。
- 拉取 personagent 的 outbox，发送其主动发出的消息，例如定时开场、追问，或模型不可用时在群中的致歉。见 [Outbox](#outbox)。
- personagent 接管会话时停止 AstrBot 自身的流水线（`block_default`），以免 AstrBot 自带的模型代替角色回答。

人设、记忆、防抖和打字模拟都在 personagent 中运行。本插件是 personagent 的 [`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.zh-CN.md) 所定义的连接器。

## 安装到你自己的 AstrBot

你需要 AstrBot（至少启动过一次，使其 data 文件夹已经存在）和 personagent（`python -m pip install personagent`，见其 README）。

### 使用 personagent 的设置流程

```bash
personagent connect astrbot
```

该命令先查找 AstrBot 的 data 文件夹，即存放 `cmd_config.json`、`plugins/` 和 `config/` 的文件夹。找不到时，可以代为下载 AstrBot。接着询问 AstrBot 是否运行在 Docker 中、机器人加入哪个聊天平台（AstrBot 仍需要时会索取该平台的 token）、哪些群、管理员是谁、允许哪些人私聊。经 NapCat 接入 QQ 时还会询问机器人账号的 QQ 号。最后复制本插件，生成共享 token 并写入两边，同时写入白名单。`personagent init --terminal` 的最后一步也提供同样的流程。

如不希望逐项回答，可以直接指定 data 文件夹：

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

以此方式运行时，首次连接的白名单为**空**，需要在插件设置中填写。`personagent connect astrbot --help` 列出了同时在 AstrBot 中开启平台的参数。

该命令可随时重复运行。它会保留白名单、其他被排除的平台，以及插件接受的 `personagent_url`（见[personagent 可以运行在哪里](#personagent-可以运行在哪里)）。插件会拒绝的 `personagent_url` 则替换为默认的本机地址。只有指定 `--qq` 或 `--no-qq` 时 QQ 路由才会改变，personagent 的 `CONNECTOR_QQ_PLATFORMS` 随之变化。询问时，当前白名单就是默认值：按回车保留，输入 `-` 清空。

然后重启 AstrBot 并启动 personagent（见[确认运行正常](#确认运行正常)）。

### 从 AstrBot 网页安装

1. 从 [personagent 最新 Release](https://github.com/wangkant/personagent/releases/latest) 下载 `astrbot_plugin_personagent.zip`。
2. 在 AstrBot 插件页的 **从文件安装** 中上传该文件。
3. 将 `connector_token` 设为 personagent 的 `.env` 中的 `CONNECTOR_TOKEN`，并按下文填写白名单。
4. 如果 AstrBot 与 personagent 不在同一台电脑上，请将 `personagent_url` 设为 HTTPS 地址（见[personagent 可以运行在哪里](#personagent-可以运行在哪里)）。

升级时以相同方式上传新版 zip。AstrBot 4.29 及以后的版本会替换已安装的副本。更早的版本需要先卸载插件，卸载时请勿勾选 **同时删除插件配置文件**。

### 手动安装

1. 将本文件夹复制到 `<AstrBot data dir>/plugins/astrbot_plugin_personagent/`。
2. 重启 AstrBot，或在网页中重新加载插件。AstrBot 会安装 `requirements.txt`，其中只列有 `httpx`。
3. 在网页中打开插件设置。设置保存在 `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json`。
   - 将角色可以加入的群 ID 填入 `groups`。
   - 将允许私聊并获得回答的发送者 ID 填入 `dm_users`。
   - 如果 personagent 的 `.env` 设置了 `CONNECTOR_TOKEN`，请将相同的值填入 `connector_token`。personagent 位于其他主机上时必须填写。
   - personagent 在同一主机上且使用默认的 `SERVER_PORT=8080` 时，`personagent_url` 保持默认。

插件**默认拒绝**。白名单为空时，插件不转发任何消息，AstrBot 的表现与未安装插件时相同。ID 按 AstrBot 显示的格式填写；在聊天中发送 `/sid` 即可查看。不带前缀的 ID 对所有适配器生效。`qq_official:ID` 只对该适配器生效，`qq_official:*` 转发该适配器上的全部同类会话。

`groups` 或 `dm_users` 中单独的 `*` 转发所有适配器上的全部同类会话，并标记为 `prefiltered: false`。此时仅由 personagent 自身的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 决定。没有条目的平台会被 personagent 拒绝，QQ 群除外：`ACCESS_GROUPS` 未列出任何 QQ 群时，personagent 回应所有 QQ 群。

### 确认运行正常

1. 用 `personagent run` 启动 personagent，该命令只启动服务本身。启动信息应显示 `agent: on`。
2. 在允许的群中发送包含机器人名字的消息（personagent 的 `PERSONA_NAME`）。

如果没有回复，请先在 AstrBot 日志中查找以 `personagent:` 开头的行，再查看 `personagent run` 在启动信息之后打印的内容，并参阅[问题排查](#问题排查)。

## 设置

| 设置 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | personagent 的基础地址。插件会加上 `/v1/events` 和 `/v1/outbox`。必须是本机地址，或已设置 `connector_token` 的 HTTPS 地址。 |
| `connector_token` | string | `""` | 共享密钥。必须与 personagent 的 `CONNECTOR_TOKEN` 一致。`personagent_url` 不是本机地址时必须填写。 |
| `timeout_s` | int | `420` | 每次尝试等待的秒数。见[超时](#超时)。 |
| `excluded_platforms` | list | `["aiocqhttp"]` | 永不转发的适配器名。删除 `aiocqhttp` 后 QQ（NapCat）经本插件接入。见[经 NapCat 接入 QQ](#经-napcat-接入-qq)。 |
| `groups` | list | `[]` | 要转发的群 ID。为空时不转发任何群。`adapter:ID` 或 `adapter:*` 将条目限定于一个适配器。单独的 `*` 不加过滤地转发所有群。 |
| `dm_users` | list | `[]` | 私聊会被转发的发送者 ID。为空时不转发私聊。`adapter:ID` 或 `adapter:*` 将条目限定于一个适配器。单独的 `*` 不加过滤地转发所有私聊。 |
| `block_default` | bool | `true` | personagent 接管会话时停止 AstrBot 的流水线。 |
| `forward_quoted_text` | bool | `true` | 平台提供时，将被引用消息的文字和作者连同其 id 一起发送。开启且 `quote_max_chars` 大于 0 时，每个事件都声明 `quote_text` 能力。 |
| `quote_max_chars` | int | `200` | 发送的被引用文字的最大长度。更长的引用会被截断。 |
| `max_inline_image_bytes` | int | `4000000` | 内嵌发送图片的最大字节数。personagent 无法自行获取的图片（Telegram、本地文件、私有地址）会内嵌发送。更大的图片只以提示 `(sent an image)` 到达。应小于 personagent 的 `VISION_MAX_IMAGE_BYTES`。 |
| `outbox_enabled` | bool | `true` | 拉取并发送 personagent 的 outbox。见 [Outbox](#outbox)。 |
| `outbox_wait_s` | int | `25` | 一次 outbox 拉取在 personagent 处最多等待多久，上限 30。 |
| `connector_id` | string | `""` | 该 AstrBot 在 personagent 中的名称。留空时生成一次并保存。两台 AstrBot 主机需要不同的名称。 |

### personagent 可以运行在哪里

- **同一主机**，或与主机共享网络命名空间、使用主机网络的容器：保持默认的本机 `personagent_url`。
- **其他容器或主机**：使用 HTTPS 的 `personagent_url`，并在 `connector_token` 和 personagent 的 `CONNECTOR_TOKEN` 中设置相同的非空密钥。终点为 AstrBot 可见的本机地址的私有隧道也可以。这种情况下同样须在两边设置相同的 token，因为 personagent 会拒绝经代理到达的无 token 请求。

插件拒绝发往本机以外的明文 `http://`，例如 `http://host.docker.internal:8080`，即使有 token 也是如此。此时每条消息都会记录 `refusing unsafe personagent_url`，由 AstrBot 自带的模型回答。

**AstrBot 运行在 Docker 中。** 在容器内，`127.0.0.1` 指向容器自身，因此默认的 `personagent_url` 无法连接到任何服务。有两种选择：

- 让 AstrBot 使用主机网络：在 compose 文件中写入 `network_mode: host`，或使用 `docker run --network host`。Docker Desktop 需要 4.34 或更高版本并开启 host networking。同一 compose 文件中的 NapCat 容器也须使用主机网络。
- 将 personagent 部署在 HTTPS 之后，并将该地址设为 `personagent_url`（`personagent connect astrbot <dir> --url https://...`）。

personagent 默认监听 `127.0.0.1:8080`。如果将其 `SERVER_HOST` 设为非本机地址，未设置 `CONNECTOR_TOKEN` 时它会拒绝启动。在 personagent 前部署代理或隧道之前，请先设置 token，即使在同一主机上也是如此。

### 超时

每次请求持续到 personagent 完成一个回合，包括一小段防抖时间，以及每次模型调用和重试。`timeout_s` 用尽后，personagent 仍会完成该回合并保留学到的内容，但回复会丢失，AstrBot 自带的模型转而回答该消息。

让 personagent 的 3 × `LLM_TIMEOUT_S` 低于 `timeout_s`。一个回合的所有模型调用（含重试）共用 1.5 × `LLM_TIMEOUT_S`，且消息须先等待其到达时正在思考的回合结束。按 personagent 的默认值（`LLM_TIMEOUT_S=120`），该值为 360 秒，默认的 `timeout_s` 420 足以覆盖。如果调大 personagent 的 `LLM_TIMEOUT_S`，`timeout_s` 也须相应调大。

只要签名后的请求仍在有效期内，插件会对 personagent 返回的 429 或 500 最多重试两次，429 时遵循 `Retry-After`。

### `block_default` 与会话归属

每当 personagent 报告会话归它所有（`owned: true`），无论它是否回复，插件都会停止 AstrBot 的流水线，以免在角色不发言的回合中 AstrBot 自带的模型插话。

传输错误、无效响应和 personagent 拒绝的会话会继续经过 AstrBot 的普通流水线。如果 personagent 的响应没有 `owned` 字段，插件改用 `handled`。

## 经 NapCat 接入 QQ

QQ 官方机器人由 personagent 直接连接，无需 AstrBot。本节仅适用于使用 NapCat（或其他 OneBot v11 实现）运行 QQ 账号、经 AstrBot 的 `aiocqhttp` 适配器接入的情况。在 personagent 自身的页面上添加 OneBot v11 时，页面会代为从 `excluded_platforms` 删除 `aiocqhttp` 并设置 `CONNECTOR_QQ_PLATFORMS`。

1. 从 `excluded_platforms` 删除 `aiocqhttp`，并将 QQ 群加入 `groups`。
2. 在 personagent 的 `.env` 中设置 `CONNECTOR_QQ_PLATFORMS=aiocqhttp` 和 `QQ_BOT_ID`（机器人账号的 QQ 号）。
3. 可选：将 personagent 的 `QQ_ONEBOT_URL` 设为 NapCat 的 HTTP 服务。这会开启补收遗漏 @ 的扫描，该扫描同样需要 `QQ_BOT_ID`。插件拉取时，主动消息、被拒绝后的追问和模型失败时群中的致歉都经本插件的 [outbox](#outbox) 发送。否则在设置了该地址的前提下，直接经 NapCat 发送。
4. 如果 NapCat 仍在向 personagent 的 `/v1/onebot` 发送事件，请将其关闭。此路线已弃用，两者同时运行会让每条消息送达两次。

`personagent connect astrbot <data dir> --qq` 会从 `excluded_platforms` 删除 `aiocqhttp` 并设置 `CONNECTOR_QQ_PLATFORMS`。不指定文件夹运行时，还会询问 `QQ_BOT_ID`。部署教程也介绍了此路线：[docs/deploy.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md#第三方路线astrbot--napcat)。

请勿省略 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。缺少该项时，personagent 会将 QQ 会话记在带 `aiocqhttp:` 前缀的 ID 下，原有 QQ ID 下学到的内容不再匹配，且学习记录事后无法迁移。

由于 QQ ID 不带前缀，personagent 自身的 QQ 设置依然适用。`ACCESS_GROUPS` 中的 QQ 条目决定群（没有条目表示所有 QQ 群），私聊只回应 `ADMIN_IDS` 中的管理员或 `ACCESS_DM_USERS` 中的用户。设置向导会将你提供的 QQ 群写入 personagent 的 `.env`。以后添加 QQ 群时，请将其同时加入 `groups` 和 `ACCESS_GROUPS`，或在 `ACCESS_GROUPS` 中不列任何 QQ 群。

让 AstrBot 接入消息较多的 QQ 群之前，请检查 AstrBot 的两项设置。它们都在插件处理之前运行。

- `platform_settings.rate_limit` 默认每 60 秒 30 条。超出的消息会被延迟，而非丢弃。请调高或关闭该限制。
- `content_safety.internal_keywords` 默认开启，会丢弃命中关键词列表的消息，包括角色本应回答的消息。请检查该列表。

## 平台

personagent 只使用一种中立格式，插件在边界处用各平台自身的机制转换。下表已对照 AstrBot 4.25.5 的适配器核对。

在所有平台上：

- 只转发真人发送的消息。QQ 通知（戳一戳、撤回、入群）和请求，以及 Slack 的入群和话题变更，都不算回合。
- 视频、文件和语音消息以角色可以反应的提示到达，例如 `(sent a video)`、`(sent a file: deck.pdf)` 或 `(sent a voice message)`，平台有转写时附上转写。
- 平台提供时，被引用的消息带有文字和作者（`forward_quoted_text`）。
- 只要适配器保留，消息时间即为平台自身的时间，而不是 AstrBot 收到的时间。
- 回复按低于平台长度上限的长度拆分，@ 和转义按平台的算法计数。回复绝不会变成文字转图片，并按平台的方式称呼他人。
- 只有平台能主动发送时才使用 outbox。

| 平台（适配器） | 可用功能 | 平台本身做不到的事 |
| --- | --- | --- |
| QQ 经 OneBot（`aiocqhttp`） | 群和私聊。@ 和回复机器人，包括适配器查不到被 @ 者时。表情名称、商城表情（`mface`）和标记为表情的图片。真正的 QQ @，后跟一个空格。长回复按 AstrBot 的 `forward_threshold` 以下拆分，不会变成合并转发卡片。Outbox。 | Markdown 按原样显示。 |
| QQ 官方（`qq_official`、`qq_official_webhook`） | @ 机器人的群消息和私聊。表情显示为 `[表情:name]`。回复请求纯文本，而不是适配器的 markdown。 | 群里只投递 @ 机器人的消息，所以角色无法跟上对话。没有引用、没有名字（只有 openid），回复中不能 @。只能在消息后 5 分钟内回复，所以没有 outbox。 |
| Telegram（`telegram`） | 群、话题（`<chat>#<thread>`）和私聊。回复机器人的任意类型消息，并去掉适配器的 `/@bot` 唤醒前缀。贴纸表情，静态贴纸还带图片。图片经适配器的机器人获取，所以 bot token 不会离开 AstrBot。被提及的用户名在此人发过言后变成数字 id。回复用用户名提及，没有用户名的人用 `tg://user` 链接，`*`、`_` 等字符按原样显示。Outbox。 | BotFather 的隐私模式开启时（默认），群里只投递命令、@ 和回复机器人的消息。关闭它，角色才能跟上对话。动画和视频贴纸无法查看。 |
| Discord（`discord`） | 频道和子区算群，还有私聊。开头的 `@bot`（适配器会去掉）、提及机器人的某个身份组、回复机器人，都算对它说话。带文字的引用。贴纸。语音和视频附件以提示到达。提及为 `<@id>`，`@everyone` 和 `@here` 保持无效。回复按 2000 字符拆分。Outbox，包括私聊。 | 需要 Message Content intent。 |
| Slack（`slack`） | 频道和私聊。在机器人消息下的 thread 回复视为对机器人发言。链接展开。消息 id 是 Slack 的 `ts`。提及为 `<@id>`。`&`、`<` 和 `>` 转义，文字无法提及频道。回复按 3000 字符拆分。Outbox。 | thread 回复不带父消息文字。机器人没有输入提示。回答落在频道里，不在 thread 里（适配器）。 |
| KOOK（`kook`） | 频道和私聊。@，以及提及机器人持有的角色。KOOK 附带时的引用。`(emj)` 表情和真实发送时间。提及写在文字中，角色文字里 `(met)` 式的标记保持无效。图片作为文件发送，因为适配器只上传 JPEG base64。Outbox。 | AstrBot 的适配器在任何插件看到之前就丢弃纯图片、文件、语音和视频消息（卡片除外）。没有输入提示。 |
| Lark / 飞书（`lark`） | 群和私聊。@ 和回复机器人（Lark 把应用标为发送者）。带文字的引用。表情以 emoji 到达。Outbox。 | 没有「读取群内所有消息」权限时，只收到 @ 消息。每条回复都引用它回答的消息，markdown 会渲染（适配器）。名字是 id 前缀。 |
| 钉钉（`dingtalk`） | 群和私聊。适配器以本地文件交付的图片会内嵌发送。视频以提示到达。Outbox。私聊能到达给机器人写过信的人。 | 群里只投递 @ 机器人的消息。没有引用，回复中不能 @ 或引用回复。每条回复都是标题为 "AstrBot" 的 markdown（适配器）。 |
| LINE（`line`） | 群、房间和私聊。@ 机器人。引用 id。贴图关键词。一个回合的气泡一次调用发送，每次五个，免费的 reply token 足以覆盖。Outbox，计入推送配额。 | LINE 不发送被引用的文字。回复中不能提及（适配器）。发送图片需要公开的 HTTPS `callback_api_base`。名字是 id 前缀。 |
| Mattermost（`mattermost`） | 频道和私聊。@ 机器人。thread 根消息作为引用。图片内嵌。此人发过言后可按用户名提及。`@channel`、`@all` 和 `@here` 保持无效。回复按 4000 字符拆分。Outbox。 | 被引用的文字需要一次插件不做的查询。没有输入提示。 |
| Misskey（`misskey`） | Chat 私聊和房间，房间消息任意位置的 `@bot`。此人发过言后提及为 `@user@host`，角色文字中其他的 `@` 保持无效。回复按 3000 字符拆分。聊天和房间的 Outbox。 | Note（公开帖子）不转发，因为 AstrBot 把它们归为系统事件，回复也会公开。`unique_session` 会破坏房间（适配器）。 |
| Satori（`satori`） | Satori 后端桥接的内容：群、私聊、@、回复机器人、带文字的引用。毫秒时间戳按秒读取。Outbox。 | 群 id 是 guild，所以一个 guild 的频道共用一个会话。被桥接平台的限制同样适用。 |
| WebChat（`webchat`） | 仪表盘聊天，算私聊。引用和图片。Outbox，实时显示或保存到会话。 | 只有一对一。 |
| 企业微信应用（`wecom`） | 私聊、图片，以及带转写的语音。客服模式只转发客户的消息，带真实发送时间。回复按字节拆分。应用模式的 Outbox，要求 AstrBot 启动后有人写过信。 | 只有私聊，没有引用。客服模式不能主动发送。Markdown 按原样显示。 |
| 企业微信智能机器人（`wecom_ai_bot`） | 群（企业微信只在 @ 机器人时投递群消息）和私聊。语音、文件和视频提示。一个回合以一条流式回答发送。 | 只能在回答某条消息时回复，所以没有 outbox，也不能提及。回答按 markdown 渲染。在 AstrBot 中设置 `wecom_ai_bot_name`，这样 "@bot" 会从文字中去掉。 |
| 微信公众号（`weixin_official_account`） | 私聊，以及带转写的语音。一个回合以一条消息发送。 | 被动模式每条用户消息只能回复一条，且在微信的 5 秒窗口内。其余的等用户下一条消息，角色不开口的回合会让用户一直等（适配器）。只有主动模式能发图片。没有 outbox。 |
| 个人微信（`weixin_oc`） | 私聊。带文字的引用。图片内嵌。带转写的语音。输入提示。Outbox。 | 没有群。重新登录后，对方再次写信之前都联系不到。 |
| 其他适配器 | 按 AstrBot 的交付转发。提及为 At。 | 不声明 outbox。 |

## Outbox

有些消息并非对任何消息的回答：定时开场、被拒绝后的追问，或模型不可用时群里的致歉。（私聊的致歉在事件自身的响应中返回。）personagent 将这些消息排入队列，本插件使用与事件相同的签名从 `POST <personagent_url>/v1/outbox` 拉取，因此 personagent 无需访问 AstrBot。Outbox 默认开启（`outbox_enabled`）。

- 每次投递都经该会话自己的 AstrBot session 按顺序发出，每条消息最多发送一次。
- 投递只发往插件本身从同一会话的消息中取得的 session。这些 session 保存在 AstrBot 的插件存储中，因此重新加载后仍然存在。其他向 personagent 发送事件的程序都不能将 outbox 指向其他聊天，插件会拒绝这样的投递。
- 插件在发送时再次检查白名单和 `excluded_platforms`，并拒绝已被移除的会话。
- 不能主动发言的平台（见上表）绝不会收到 outbox 消息，因为插件不为其会话声明 outbox。
- 没有 outbox 的 personagent 返回 404。插件每十分钟重新查询一次。

personagent 通过 `connector_id` 识别该 AstrBot，该 id 由插件生成一次并保存。连接同一个 personagent 的两台 AstrBot 主机需要不同的 id。

## 请求认证

设置了 `connector_token` 时，每个请求都带四个请求头：

- `X-Personagent-Token`：token。
- `X-Personagent-Timestamp`：Unix 秒。
- `X-Personagent-Nonce`：新生成的随机值。
- `X-Personagent-Signature`：`sha256=` 后跟十六进制 HMAC-SHA256，以 token 为密钥，内容为 `timestamp + "." + nonce + "." + body`。

请求体是规范 JSON：UTF-8、键排序、紧凑分隔符、非 ASCII 字符不转义。签名覆盖这些确切的字节，因此代理不能改写请求体。personagent 拒绝错误的签名、重复的 nonce，以及与其自身时钟相差超过五分钟的时间戳。请保持两边时钟同步。

请求体还以 `sent_at` 携带适配器记录的消息时间。personagent 单独按 `CONNECTOR_MAX_EVENT_AGE_S`（默认 24 小时）检查该时间，因此用新签名重发的旧事件仍会被拒绝。适配器没有给出有效时间戳的消息，插件不转发，由 AstrBot 照常处理。角色看到的每条消息都附有这一时间；群聊消息到达时若已超过 10 分钟（例如重启后 AstrBot 补发的积压消息），只作为上下文保留，不予回复。

## personagent 一侧的身份

personagent 为每个转发的 id 加上平台前缀，写作 `<platform>:<raw id>`（例如 `telegram:12345`），因此不同平台的 id 不会冲突。`CONNECTOR_QQ_PLATFORMS` 中列出的平台保持不带前缀的 id。personagent 的 `ADMIN_IDS`、`ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 使用相同格式的 id。例如 `ADMIN_IDS=telegram:12345` 使该账号成为 Telegram 上的管理员，群聊和私聊均适用。在 `ACCESS_GROUPS` 或 `ACCESS_DM_USERS` 中有条目的平台，既受 personagent 把关，也受本插件的白名单把关。

## 问题排查

插件在 AstrBot 日志中的行都以 `personagent:` 开头。

| 日志 | 处理方法 |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` 是发往其他主机的明文 HTTP，或没有 `connector_token` 的 HTTPS。见[personagent 可以运行在哪里](#personagent-可以运行在哪里)。 |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` 为空或与 personagent 的 `CONNECTOR_TOKEN` 不一致，两边时钟相差超过五分钟，或代理改动了请求体。如果 personagent 的日志显示 `connector replay guard full`，请等待其清空。 |
| `agent refused the request (403): stale or invalid sent_at` | 消息比 personagent 的 `CONNECTOR_MAX_EVENT_AGE_S` 更旧。通常发生在 AstrBot 一次性投递积压消息之后。 |
| `agent refused the request (403): authentication required` 或 `... only local requests accepted` | personagent 没有 `CONNECTOR_TOKEN`，而请求并非来自本机。在两边设置相同的 token。 |
| `agent at capacity (429)` | personagent 已在运行 `CONNECTOR_MAX_INFLIGHT` 个回合，重试后仍拒绝该消息，因此由 AstrBot 自带的模型回答。如果经常发生，请调大 `CONNECTOR_MAX_INFLIGHT`。 |
| `agent rejected the body as too large (413)` | 通常是内嵌图片过大。调大 personagent 的 `SERVER_MAX_BODY_BYTES`。 |
| `agent rejected the event schema (400)` | 事件没有消息 id 或发送者 id（某些适配器会省略），或本插件存在缺陷。请附上该行日志进行报告。 |
| `timed out waiting for the agent` | 见[超时](#超时)。 |
| `dropping event without a valid time the platform sent it` | 适配器没有给出时间戳。AstrBot 自行处理该消息。 |
| `agent request failed: ...` 或 `agent request failed (<status>)` | 通常是 personagent 未运行或 `personagent_url` 填写错误。404 表示路径错误：`personagent_url` 是基础地址，不带 `/v1/events`。500 表示 personagent 出错，请查看其日志。 |
| `outbox off: ...` | Outbox 遵循与事件相同的 `personagent_url` 规则。见第一行。 |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | personagent 的 `CONNECTOR_OUTBOX_ENABLED` 已关闭。 |
| `outbox: outbox pull refused (403)` 或 `outbox pull failed: ...` | 原因与事件相同：token、时钟，或 personagent 未运行。插件两次尝试之间最多退避一分钟。 |
| `outbox: no running platform '<id>'` | 投递对应的适配器在 AstrBot 中已被禁用或改名。插件向 personagent 报告投递失败。 |
| `could not store connector_id` | AstrBot 的插件存储失败。请自行设置 `connector_id`，否则每次重启后 personagent 都会看到一个新的 AstrBot。 |

如果 AstrBot 自带的模型突然以另一种口吻回复，说明插件未连接到 personagent，或 personagent 未接管该会话。请对照上表排查，再运行 `personagent doctor`。如果 personagent 由本地页面启动，请打开页面上的 **动态**，查看消息是否到达、角色为何未发言。如果由 `personagent run` 启动，请查看其终端。

如果 personagent 自身的日志显示连接器发送了 `X-Personagent-Token` 但 `CONNECTOR_TOKEN` 为空，说明 personagent 忽略了 token。请在其 `.env` 中设置相同的值。

在 QQ、Telegram、Discord、KOOK、QQ 官方和 Misskey 上，消息时间是平台自身的时间，而非 AstrBot 收到的时间。AstrBot 停机时间超过 personagent 的 `CONNECTOR_MAX_EVENT_AGE_S` 时，personagent 会将 AstrBot 投递的积压消息作为过期消息拒绝。

## 已知限制：Telegram 提及

AstrBot 的 Telegram 适配器用数字用户 id 标识发送者（`telegram:<numeric id>`），但只用用户名标识消息中的 `@username` 提及。在此人于 AstrBot 启动后发过言之后，插件会将被提及的用户名改写为其数字 id。在此之前，提及以用户名到达 personagent。

回复按用户名提及，没有用户名的人用 `tg://user` 链接。AstrBot 启动后没见过的人，插件不会提及。
