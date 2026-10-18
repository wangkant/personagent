# 部署 personagent：QQ 扫码直连，以及排查

[English](deploy.md) · **简体中文**

本文按顺序介绍如何把角色接入 QQ 群：安装、填写 key、用手机 QQ 扫码。QQ 官方机器人由 personagent 直接连接，不需要 AstrBot，也不需要 NapCat 和 QQ 小号。微信、Telegram、Discord 同样由它直接连接。如果想用个人 QQ 小号，请看后面的[第三方路线：AstrBot + NapCat](#第三方路线astrbot--napcat)。

```text
QQ 群  ⇄  personagent（直连进程 + 角色服务）  ⇄  AI 模型
```

每一步都写明了「你应该看到」的结果。如果对不上，先不要继续，直接查看[机器人不说话](#机器人不说话)。

## 开始之前

- 一台能长期开机的电脑（Windows、macOS 或 Linux），装有 Python 3.10 到 3.14。personagent 关闭后，机器人也随之停止。
- 一个 AI 服务的 API key。DeepSeek、硅基流动、阿里云百炼、智谱、Kimi、火山方舟等均可，在各自的控制台里创建。
- 一部登录了你自己 QQ 的手机，用来扫码。

## 第一步：安装并打开

```sh
python -m pip install personagent
personagent
```

如果装了 [uv](https://docs.astral.sh/uv/)，可以用 `uvx personagent` 免安装运行。在 Windows 上也可以下载源码 ZIP，解压后双击 `start.bat`。从 Git 仓库运行的方法见[简明入门](start.zh-CN.md)。

你应该看到浏览器打开一个本地页面，包含三个视图：「开始聊天」「连接平台」「角色与设置」。再次运行 `personagent` 会复用已经打开的页面。

> 如果想把数据放在别的盘，运行 `personagent --home D:\personagent`，之后每条命令都带上同样的 `--home`。不指定时，数据存放在用户目录下的 `personagent` 文件夹。

## 第二步：填 key，选角色

在「角色与设置」里选择模型服务（共 10 个预设，另有「其他」，可填写任何兼容 OpenAI 的地址），粘贴 API key，再选定名字和性格。保存时，程序会发送一个很小的请求来验证 key，验证不通过则不保存任何内容。

你应该能在「开始聊天」里和角色聊几句，它会以你选的性格回复。

「人设」框里是 `persona.txt` 的内容，也就是角色当前使用的人设。修改后点击保存，角色服务会重启，已经学到的东西会保留。

「角色与设置」里的「更多功能」可以开启联网搜索、看图和主动发言。

## 第三步：扫码连接 QQ

1. 打开「连接平台」，选择 **QQ**。
2. 页面会显示二维码。用手机 QQ 扫码并确认，可以新建一个机器人，也可以选择一个已有的机器人，密钥由 personagent 自动取回。如果无法扫码，也可以在 [QQ 开放平台](https://q.qq.com/qqbot/openclaw/login.html)创建机器人，再把 AppID 和 AppSecret 粘贴进来。
3. 程序确认 QQ 接受了这个机器人之后才会保存。如果 QQ 拒绝，页面会给出提示，不保存任何内容。

你应该看到 QQ 出现在页面上方，状态为已连接。

**把机器人拉进群。** 在手机 QQ 里找到这个机器人，私聊它或把它加进群。机器人能进哪些群由 QQ 决定：通过认证之前，QQ 只允许它加入你担任群主的群。它在群里能收到哪些消息，也在 QQ 里设置。认证等账号相关事项见 [QQ 机器人官方指南](https://bot.q.qq.com/wiki/bot_new_product-intro/)。

**测试。** 在群里发一句带机器人名字的话（比如 `小夏，你好`），或者 @ 它。几秒到十几秒内应该能看到回复。

## 其他平台

所有平台都在「连接平台」里添加。凭据会先交给平台验证，通过后才保存。

- **personagent 直接连接**：QQ、个人微信、Telegram、Discord。个人微信用手机微信扫码登录（使用腾讯的 iLink 机器人接口），只支持私聊，因为微信不会把群消息交给这类机器人。Telegram 需要粘贴 @BotFather 提供的 token；Discord 需要粘贴机器人 token，并开启 Message Content Intent。
- **经托管的 AstrBot 连接**：其余平台。第一次连接这类平台时，personagent 会下载 AstrBot 和独立的 Python 3.12，并在后台运行。它没有网页后台，也不需要再登录一个账号。只需粘贴一两项就能连接的有：KOOK、飞书（长连接）、钉钉（Stream 模式）、Slack（Socket Mode，页面上的链接会预填好应用）、企业微信智能机器人（长连接）、Mattermost、Misskey。「高级」分组里的平台需要公网地址或本机的其他软件：企业微信应用、微信公众号、QQ（Webhook）、OneBot v11（NapCat）、Satori。暂不提供 LINE。

连接好的平台默认回复所有群聊和私聊。如果只想放行一部分，在 `.env` 里写 `ACCESS_GROUPS` 或 `ACCESS_DM_USERS`（格式为 `平台:ID`，见[英文部署指南](deploy.md#through-an-astrbot-you-already-run)）。

## 日常使用

- 每次开机后运行 `personagent`。页面打开期间，角色服务、直连进程和托管的 AstrBot 都在运行，已经连好的平台会自动恢复连接。如果不想打开浏览器，可以用 `personagent up`，效果相同。
- 由它启动的进程会随它一起结束，无论它以何种方式退出。上次异常退出遗留的进程，会在下次启动时先被停止。
- 所有数据都在一个主目录里：`.env`（设置）、`persona.txt`（人设）、`runtime/`（学到的东西和日志）、`platforms/`（托管的 AstrBot，以及直连平台的凭据 `direct.json`）。key 只保存在这台电脑上，对话内容会发送给你选的模型服务。
- 如果要直接修改 `.env`，可以用记事本编辑，保存为 UTF-8（不带 BOM），然后重启 `personagent`。
- 有新版本时，「开始聊天」页面和终端会给出对应你安装方式的更新命令。页面和 `personagent up` 每天最多向 pypi.org 查询一次，请求里只带版本号；在 `.env` 里设置 `UPDATE_CHECK_ENABLED=false` 可以关闭这项检查。
- 手动更新：`python -m pip install -U personagent`（用 uv 安装的，运行 `uv tool upgrade personagent`）。从 0.x 升级上来时，如果启动提示存在旧设置名，运行 `personagent doctor --fix`，它会把 `.env` 里的旧名称改成新名称，并把原文件另存为 `.env.bak`。
- 命令行：`personagent init --terminal`（终端设置向导）、`chat`（在终端里聊天）、`demo`（无需 key 的演示）、`run`（只启动角色服务）、`doctor`（检查设置和各项服务）、`learned`（查看和撤回学到的东西）、`eval`（评测）。

## 动态

本地页面侧边栏里的「动态」列出角色所在的每个群聊和私聊。选中一个聊天，可以看到等你确认的改动、它学到的东西、记住的事，以及最近的消息：它每次开口的原因，和没开口时的理由。详见[使用指南](guide.zh-CN.md#动态)。

「动态」的数据来自本地页面所启动的角色服务，取自它在 `/api/dashboard/` 下的 JSON 接口。只用 `personagent run` 启动服务时，请看服务日志，并用 `personagent learned` 查看学到的东西。每次调用都要带 `X-Personagent-Dashboard-Token` 请求头，值是运行目录（默认 `<主目录>/runtime/`，可用 `AGENT_RUNTIME_DIR` 修改）里 `dashboard.token` 文件的内容。这个文件在服务启动时生成，只有本人能读。修改操作还要带 `X-Personagent-Dashboard: 1` 和 `Content-Type: application/json`，请求如果带了 `Origin`，必须是服务自己的地址。跨站的浏览器请求一律拒绝，`CONNECTOR_TOKEN` 也打不开这个接口。返回内容里的密钥都会被遮住。脚本也可以按同样的方式调用。设置 `DASHBOARD_ENABLED=false` 会关闭这个接口，「动态」随之不显示内容，`personagent doctor` 会打印 `activity: off (...)`。

角色服务本身不提供网页，访问 `http://127.0.0.1:8080/` 只会看到一段说明，指向本地页面和 `personagent learned`，以前的 `?token=` 链接现在也只打开这段说明。本地页面只监听 127.0.0.1。在没有本地页面的服务器上，用 `personagent learned` 查看和推翻它学到的东西。

## 它怎么学习

机器人不会因为一句话就改变。一项改变要同时满足两个条件：同一个聊天里出现两次一致的反应，并且其中至少一次足够「强」，即**被回复的那个人用自己的话纠正了它，或者接受了它的第二次回答**。一声「哈哈」、旁观者的纠正（即使机器人回头问了他）、陌生人的指令、有人直接换了话题，都不算数。因此在默认设置下，一个人只能教它如何回答自己，而且只在他自己所在的聊天里生效。旁观者的抱怨也撤不掉它学到的东西，只有原回复的对象或管理员才能撤回。

学到的所有内容都记录在只追加的账本里，随时可以撤销：

- 在「动态」里，「等你确认」下的每条改动都有「保留」和「不要」两个按钮。「保留」会让它生效，如果同一条回复已经有生效中的改写，就替换掉那条。「学到的」下每一条都有「撤销」按钮。
- 也可以使用命令：`personagent learned list`、`personagent learned show <编号>`、`personagent learned rollback <编号>`。

如果希望它更保守，在 `.env` 里加上 `PROMOTE_MIN_SPEAKERS=2`，这样需要两个不同的人都认可才会改变。

在群里对它说 `小夏 记住 …`、`小夏 忘掉 …`、`小夏 你都记得什么`，可以直接管理它的记忆；`小夏 学到了什么` 会列出它学到的内容。命令必须放在消息开头。以「吗」「呢」「没」等结尾的问句（比如 `小夏 记住了吗`）只当作聊天处理；`小夏 忘掉这个` 的意思是「算了」，不会删除任何内容。每条笔记都会记录是谁记下的、内容涉及谁；不针对具体某人的笔记全群可见，列出时标注「来自某某」。

修改人设不会清空它学到的东西。

## 机器人不说话

请按顺序排查，越靠前的原因越常见。角色服务由本地页面启动时，先看「动态」：聊天是否出现、有没有收到消息、它为什么没开口，都能在这里看到。在服务器上，看服务日志，学到的东西用 `personagent learned` 查看。再看主目录下 `runtime/desktop/` 里的日志：`agent.log`（角色服务）、`direct.log`（QQ、微信、Telegram、Discord）、`astrbot.log`（其他平台）。

1. **消息没有送达。** 在「连接平台」里确认该平台显示为已连接。QQ 机器人必须已经在群里，群里能收到哪些消息由 QQ 的设置决定；个人微信只支持私聊。使用第三方 AstrBot 的，见[第三方路线排查](#第三方路线排查)。
2. **角色服务没有开启，或者缺少 key。** 在「角色与设置」里重新填写 key 并保存。如果 `.env` 里写了 `AGENT_ENABLED=false`，改为 `true` 后重启。
3. **没有叫到它。** 在群里，它只回应带它名字（`PERSONA_NAME`）或 @ 它的消息。其他情况下，它要等群里聊满 `CHAT_TRIGGER_COUNT` 条（默认 30 条）才会考虑插话，考虑之后也可能选择不说。凌晨 2 点到 7 点它更少插话。`AGENT_LANG=zh` 时按北京时间计算，如需换时区，在 `.env` 里设置 `PERSONA_TZ_OFFSET_HOURS`。测试时先用名字叫它。
4. **被 personagent 自己的白名单拦下。** `.env` 里的 `ACCESS_GROUPS`、`ACCESS_DM_USERS` 一旦写了某个平台的条目，这个平台就只放行列出的条目。被拦下的会话会在 `agent.log` 里记录一行。
5. **模型调用失败。** key 无效或余额用完时，`agent.log` 里会有一行 ERROR，写明是哪个服务、该修改哪项设置。运行 `personagent doctor` 会向每个模型发送一个很小的请求，直接显示状态码。
6. **设置名写错。** 写错的设置名不会报错，程序只是继续使用默认值。`personagent doctor` 和启动日志会列出不认识的设置名。
7. **`.env` 带有 BOM。** 用记事本另存时选错编码，会导致第一行设置失效。`personagent doctor` 会报告这个问题，改用「UTF-8」（不带 BOM）重新保存即可。
8. **能回复，但忘了学过的东西。** 修改 `PERSONA_NAME` 或 `PERSONA_VERSION` 会让它被当作新角色；在「人设」框里修改人设则不会。

如果仍然无法解决，请到 [Issues](https://github.com/wangkant/personagent/issues) 提问，并附上 `personagent doctor` 的输出（先遮盖 key 和账号）。

## 第三方路线：AstrBot + NapCat

AstrBot、NapCat（OneBot）、Koishi（经 Satori 连接器）和 Matrix（经 mautrix 桥接 WhatsApp、Signal 等）是 personagent 可以配合使用的第三方桥接，连接 QQ、微信、Telegram、Discord 都用不到它们。只有在想用**个人 QQ 小号**而不是官方机器人时，才需要 NapCat。

注意：NapCat 不是腾讯官方客户端，小号有被限制甚至封禁的风险。不要使用你自己的主号，详见 [DISCLAIMER.zh-CN.md](DISCLAIMER.zh-CN.md)。

### 用托管的 AstrBot（推荐）

1. 按 [NapCat 文档](https://napneko.github.io/)安装 NapCat，用手机上的**小号**扫码登录。
2. 在 personagent 页面的「连接平台」里选择「高级 → OneBot v11（NapCat）」，端口默认为 `6199`。
3. 在 NapCat 的网页里依次点击「网络配置」→「新建」→「WebSockets 客户端」，勾选「启用」，URL 填 `ws://127.0.0.1:6199/ws`，然后保存。

托管的 AstrBot 会自动安装 personagent 插件，并写好 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。走这条路线时，NapCat 也需要一直运行。

### 用你自己的 AstrBot

插件 `astrbot_plugin_personagent` 是 AstrBot 把消息交给 personagent 的途径。有两种安装方式：

- 运行 `personagent connect astrbot`，按提示选择 QQ（通过 NapCat），填写小号的 QQ 号、群号和你自己的 QQ 号。它会把插件复制到 AstrBot 的 `plugins` 文件夹，在两边写入同一个 `CONNECTOR_TOKEN`，并写好白名单和 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。如果不确定 AstrBot 的 `data` 文件夹在哪里，可以搜索 `cmd_config.json`。
- 也可以从 personagent 的[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下载 `astrbot_plugin_personagent.zip`，在 AstrBot 插件页的「从文件安装」中上传，再把插件设置里的 `connector_token` 填为 personagent `.env` 里的 `CONNECTOR_TOKEN`。AstrBot 不在这台电脑上时使用这种方式，此时插件的 `personagent_url` 还需要填写 personagent 的 HTTPS 地址（见下文 Docker 一段）。

升级 personagent 后，重新运行 `personagent connect astrbot` 或上传新的 zip。AstrBot 4.29 及以后的版本会直接替换已安装的插件；更早的版本需要先卸载插件，卸载时不要勾选删除插件配置文件。

安装完成后，重启 AstrBot（或在插件页重载插件），然后用 `personagent run` 启动角色服务并保持运行。在 AstrBot 里添加 OneBot v11 机器人（反向 WebSocket 端口 `6199`），再按上一节第 3 步让 NapCat 指向它。AstrBot 的界面以[其官方文档](https://docs.astrbot.app)为准。

如果 AstrBot 运行在 Docker 里，`127.0.0.1` 指的是容器本身，而插件会拒绝发往其他地址的明文 `http://`。可以二选一：给 AstrBot（以及同一个 compose 里的 NapCat）使用主机网络（`network_mode: host`，`docker run` 时用 `--network host`；Docker Desktop 需要 4.34 及以上版本，并开启 `Enable host networking`）；或者为 personagent 提供一个 HTTPS 地址，再运行 `personagent connect astrbot <data 文件夹> --url https://你的地址`。

### 第三方路线排查

1. **AstrBot 没有把消息交出来。** 在插件设置里确认 `groups` 包含这个群号；私聊需要在 `dm_users` 里填写发送者的 QQ 号。再确认 `excluded_platforms` 里没有 `aiocqhttp`。
2. **回复来自 AstrBot 自带的模型（语气突然变了）。** 查看 AstrBot 的日志：
   - `refusing unsafe personagent_url`：插件里的 `personagent_url` 不正确。在同一台电脑上应填 `http://127.0.0.1:8080`。
   - `agent refused the request (403)`：两边的 `CONNECTOR_TOKEN` 不一致，或者两台电脑的时钟相差超过五分钟。重新运行 `personagent connect astrbot` 会把两边改成同一个令牌。
   - `timed out waiting for the agent`：模型响应太慢。插件的 `timeout_s` 默认为 420 秒，足以覆盖 personagent 默认设置下最长的 360 秒；如果调大了 `LLM_TIMEOUT_S` 或 `LLM_MAX_RETRIES`，也要相应调大 `timeout_s`。
   - `agent request failed`：personagent 没有运行，或者地址、端口填写有误。
3. **QQ 私聊被拦下。** 经 NapCat 进来的 QQ 私聊，必须来自管理员（`ADMIN_IDS`），或者在 `ACCESS_DM_USERS` 之中。
4. **`QQ_BOT_ID` 未填写或填写错误。** 这里应填小号的 QQ 号。
5. **忘了学过的东西。** 经 NapCat 的 QQ 会话必须配置 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`，缺少这项时，所有 QQ 会话都会被当作新会话。

**NapCat 的 HTTP 服务**是可选的。开启后，personagent 能补回它离线期间漏掉的 @ 消息。做法是在 NapCat 里打开 HTTP 服务，并在 `.env` 里写上 `QQ_ONEBOT_URL=http://127.0.0.1:3000`（端口以 NapCat 中的设置为准）和 `QQ_BOT_ID`（小号的 QQ 号）。

**旧的直连方式。** NapCat 直接把事件发到 personagent 的 `/v1/onebot`，这种方式已不再推荐，但在 1.x 中仍然可用。它要求在 `.env` 里写上 `QQ_ONEBOT_URL`，否则机器人只收不回，`personagent doctor` 会对此给出提醒。改用 AstrBot 之后，要关闭 NapCat 里指向 `/v1/onebot` 的 HTTP 客户端，否则每条消息都会收到两遍。已经学到的记忆会保留。

## 其他文档

- [英文版部署指南](deploy.md)：全部设置、对外暴露端口、错误码。
- [AstrBot 插件说明](../integrations/astrbot/astrbot_plugin_personagent/README.zh-CN.md)
- [免责声明](DISCLAIMER.zh-CN.md)
