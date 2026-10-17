# 部署 personagent：QQ 扫码直连，以及排查

[English](deploy.md) · **简体中文**

这篇按顺序带你把角色放进 QQ 群：装好、填 key、用手机 QQ 扫码。personagent 自己连接 QQ 官方机器人，不需要 AstrBot，也不需要 NapCat 和 QQ 小号。微信、Telegram、Discord 同样由它直接连接；想用个人 QQ 小号的，见后面的[第三方路线：AstrBot + NapCat](#第三方路线astrbot--napcat)。

```text
QQ 群  ⇄  personagent（直连进程 + 角色服务）  ⇄  AI 模型
```

每一步都写了「你应该看到」，对不上就先别往下走，直接翻到[机器人不说话](#机器人不说话)。

## 开始之前

- 一台能一直开着的电脑（Windows、macOS、Linux 都行），装有 Python 3.10 到 3.14。关掉 personagent，机器人就停了。
- 一个 AI 服务的 API key。DeepSeek、硅基流动、阿里云百炼、智谱、Kimi、火山方舟等都可以，在它们的控制台里创建。
- 一部登着你自己 QQ 的手机，用来扫码。

## 第一步：安装并打开

```sh
python -m pip install personagent
personagent
```

装了 [uv](https://docs.astral.sh/uv/) 的话，`uvx personagent` 不用单独安装就能运行。Windows 也可以下载源码 ZIP，解压后双击 `start.bat`；从 Git 仓库运行见[简明入门](start.zh-CN.md)。

你应该看到浏览器打开一个本地页面，有三个视图：「开始聊天」「连接平台」「角色与设置」。再运行一次 `personagent` 会复用已经打开的页面。

> 想把数据放在别的盘：`personagent --home D:\personagent`。之后每条命令都带上同样的 `--home`。不加的话，数据放在用户目录下的 `personagent` 文件夹。

## 第二步：填 key，选角色

在「角色与设置」里选模型服务（10 个预设，另有「其他」可填任何兼容 OpenAI 的地址），粘贴 API key，再选名字和性格。保存时它会发一个很小的请求验证 key，不通过就什么都不存。

你应该能在「开始聊天」里和角色聊几句，它用你选的性格回话。

「人设」框里是 `persona.txt`，就是角色正在用的人设。改完点保存，角色服务会重启，它学到的东西保留。

## 第三步：扫码连接 QQ

1. 打开「连接平台」，选 **QQ**。
2. 页面出现二维码。用手机 QQ 扫码并确认：会新建一个机器人，或者选一个你已有的，密钥由 personagent 自己取回。扫不了码的话，也可以在 [QQ 开放平台](https://q.qq.com/qqbot/openclaw/login.html)创建机器人，把 AppID 和 AppSecret 粘贴进来。
3. 程序先确认 QQ 接受了这个机器人，再保存。QQ 拒绝的话，页面会提示，什么都不保存。

你应该看到 QQ 列在页面上方，显示已连接。

**把机器人拉进群。** 在手机 QQ 里找到这个机器人，私聊它，或把它加进群。能进哪些群由 QQ 决定：机器人通过认证之前，QQ 只让它进你自己当群主的群。它在群里能收到哪些消息，也在 QQ 里设置。认证等账号上的事见 [QQ 机器人官方指南](https://bot.q.qq.com/wiki/bot_new_product-intro/)。

**测试。** 在群里发一句带机器人名字的话（比如 `小夏，你好`），或者 @ 它。你应该在几秒到十几秒内看到回复。

## 其他平台

都在「连接平台」里添加，凭据先拿到平台验证，通过了才保存。

- **personagent 直接连接**：QQ、个人微信、Telegram、Discord。个人微信用手机微信扫码登录（腾讯的 iLink 机器人接口），只能私聊，微信不会把群消息交给这类机器人。Telegram 粘贴 @BotFather 给的 token；Discord 粘贴机器人 token，并打开 Message Content Intent。
- **经托管的 AstrBot**：其余平台。第一次连接时，personagent 会下载 AstrBot 和独立的 Python 3.12，在后台运行，没有网页后台，也没有第二个账号要登录。粘贴一两项就能连的：KOOK、飞书（长连接）、钉钉（Stream 模式）、Slack（Socket Mode，页面上的链接会预填好应用）、企业微信智能机器人（长连接）、Mattermost、Misskey。「高级」里的需要公网地址或另外的软件：企业微信应用、微信公众号、QQ（Webhook）、OneBot v11（NapCat）、Satori。LINE 暂不提供。

连好的平台，群聊和私聊都会回复。想只放行一部分，在 `.env` 里写 `ACCESS_GROUPS` 或 `ACCESS_DM_USERS`（格式 `平台:ID`，见[英文部署指南](deploy.md#through-an-astrbot-you-already-run)）。

## 日常使用

- 每次开机后运行 `personagent`。页面开着期间，角色服务、直连进程和托管的 AstrBot 都在运行；已经连好的平台会自动恢复。不想开浏览器，用 `personagent up`，效果一样。
- 由它启动的进程会跟着它一起结束，不管它是怎么结束的；上次异常退出留下的进程，下次启动时会先被停掉。
- 所有数据在一个主目录里：`.env`（设置）、`persona.txt`（人设）、`runtime/`（学到的东西和日志）、`platforms/`（托管的 AstrBot 和直连平台的凭据 `direct.json`）。key 只存在这台电脑上；对话会发给你选的模型服务。
- 想直接改 `.env` 的话，用记事本改，保存为 UTF-8（不带 BOM），再重启 `personagent`。
- 更新：`python -m pip install -U personagent`（用 uv 装的就 `uv tool upgrade personagent`）。从 0.x 升级上来的，如果启动时说有旧设置名，运行 `personagent doctor --fix`，它会把 `.env` 里的旧名字换成新的（原文件另存为 `.env.bak`）。
- 命令行：`personagent init --terminal`（终端里的设置向导）、`chat`（终端里聊）、`demo`（不需要 key 的演示）、`run`（只启动角色服务）、`doctor`（检查设置和各项服务）、`learned`（查看和撤回学到的东西）、`eval`（评测）。

## 管理面板

管理面板显示服务状态、收到的消息、每一轮说或不说的原因，以及它学到的东西。它只能用带令牌的专用链接打开：运行 `personagent doctor`，输出里有 `dashboard` 那一行（`personagent run` 启动时也会打印）。打开过一次，这个浏览器一年内都不用再输。直接输 `http://127.0.0.1:8080/` 会提示你去找链接；`CONNECTOR_TOKEN` 也打不开它。面板里不会显示密钥。想在别的电脑上看，用 SSH 隧道，或者把 `SERVER_HOST` 设成这台电脑的局域网或 Tailscale 地址（这时必须同时设 `CONNECTOR_TOKEN`）。

## 它怎么学习

机器人不会因为一句话就变样。一个改变要同时满足：同一个聊天里有两次一致的反应，并且其中至少一次够「强」，也就是**被回复的那个人用自己的话纠正它，或者接受了它的第二次回答**。一声哈哈、旁观者的纠正（哪怕机器人回头问了他）、陌生人的指令、有人直接换了话题，都不算。所以默认情况下，一个人只能教它怎么回答他自己，并且只在他自己的那个聊天里。旁观者抱怨也撤不掉它学到的东西，只有原回复的对象或者管理员能撤。

学到的所有东西都记在只追加的账本里，随时可以撤销：

- 在管理面板里，每一条学到的东西后面有「采纳」「拒绝」「撤回」按钮（点两下确认）。同一条回复已经有改写在用时，「采纳」会换成「替换」。
- 或者用命令：`personagent learned list`、`personagent learned show <编号>`、`personagent learned rollback <编号>`。

想让它更保守，在 `.env` 里加 `PROMOTE_MIN_SPEAKERS=2`：要两个不同的人都同意才会改。

在群里对它说 `小夏 记住 …`、`小夏 忘掉 …`、`小夏 你都记得什么` 可以直接管理它的记忆；`小夏 学到了什么` 会列出它学到的东西。命令要放在消息开头；以「吗」「呢」「没」等结尾的问句（比如 `小夏 记住了吗`）只是聊天，`小夏 忘掉这个` 等于「算了」，什么都不删。每条笔记会记下是谁记的、说的是谁；不针对某个人的笔记全群可见，列出来时标着「来自某某」。

改人设不会清空它学到的东西。

## 机器人不说话

按顺序排查，越靠前越常见。先看管理面板，它会直接告诉你「还没收到任何消息」「消息被拒绝了」或者「收到了但没说话」；再看主目录 `runtime/desktop/` 下的日志：`agent.log`（角色服务）、`direct.log`（QQ、微信、Telegram、Discord）、`astrbot.log`（其他平台）。

1. **消息没送到。** 在「连接平台」里确认这个平台显示已连接。QQ 机器人要已经在群里，群里能收到哪些消息由 QQ 的设置决定；个人微信只能私聊。走第三方 AstrBot 的，见[那一节的排查](#第三方路线排查)。
2. **角色服务没开，或者没有 key。** 在「角色与设置」里重新填 key 并保存。`.env` 里写了 `AGENT_ENABLED=false` 的话，改成 `true` 再重启。
3. **它没被叫到。** 在群里它只回应带它名字（`PERSONA_NAME`）或者 @ 它的消息。别的时候，它要等群里聊够 `CHAT_TRIGGER_COUNT` 条（默认 30 条）才会考虑插话，而且考虑了也可能选择不说。凌晨 2 点到 7 点它更不爱插话：`AGENT_LANG=zh` 时按北京时间算，想换时区就在 `.env` 里设 `PERSONA_TZ_OFFSET_HOURS`。先用名字叫它测试。
4. **被 personagent 自己的白名单挡了。** `.env` 里的 `ACCESS_GROUPS`、`ACCESS_DM_USERS` 只要写了某个平台的条目，这个平台就只放行写了的。被挡的会话，`agent.log` 里会记一行，管理面板里也有。
5. **模型调用失败。** key 无效、余额用完，`agent.log` 里会有一行 ERROR，写着是哪个服务、该改哪个设置。运行 `personagent doctor` 会向每个模型发一个很小的请求，直接看到状态码。
6. **设置写错了。** 写错的设置名不会报错，只是悄悄用默认值。`personagent doctor` 和启动日志会列出不认识的设置名。
7. **`.env` 带了 BOM。** 用记事本另存时选错了编码，第一行设置会失效。`personagent doctor` 会报告，改成「UTF-8」（不带 BOM）重新保存。
8. **说话了，但忘了学过的东西。** 改了 `PERSONA_NAME` 或 `PERSONA_VERSION` 会让它当作新角色；在「人设」框里改人设不会。

还不行，就在 [Issues](https://github.com/wangkant/personagent/issues) 里提问，附上 `personagent doctor` 的输出（先把 key 和账号打码）。

## 第三方路线：AstrBot + NapCat

AstrBot、NapCat（OneBot）、Koishi（经 Satori 连接器）和 Matrix（经 mautrix 桥接 WhatsApp、Signal 等）是 personagent 可以配合的第三方桥接，连 QQ、微信、Telegram、Discord 都用不到它们。只有想用**个人 QQ 小号**而不是官方机器人时，才需要 NapCat。

注意：NapCat 不是腾讯官方的客户端，小号有被限制甚至封禁的风险。不要用你自己的主号，详见 [DISCLAIMER.zh-CN.md](DISCLAIMER.zh-CN.md)。

### 用托管的 AstrBot（推荐）

1. 按 [NapCat 文档](https://napneko.github.io/)装好 NapCat，用手机上的**小号**扫码登录。
2. 在 personagent 页面的「连接平台」里选「高级 → OneBot v11（NapCat）」，端口默认 `6199`。
3. 在 NapCat 的网页里点「网络配置」→「新建」→「WebSockets 客户端」，勾选「启用」，URL 填 `ws://127.0.0.1:6199/ws`，保存。

托管的 AstrBot 会自动装好 personagent 插件，并写好 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。这条路上 NapCat 也要一直开着。

### 用你自己的 AstrBot

插件 `astrbot_plugin_personagent` 只是 AstrBot 把消息交给 personagent 的方式。两种装法：

- 运行 `personagent connect astrbot`，按提示选 QQ（通过 NapCat），填小号的 QQ 号、群号和你自己的 QQ 号。它会把插件复制进 AstrBot 的 `plugins` 文件夹，在两边写进同一个 `CONNECTOR_TOKEN`，写好白名单和 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。不确定 AstrBot 的 `data` 文件夹在哪，就搜 `cmd_config.json`。
- 或者从 personagent 的[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下载 `astrbot_plugin_personagent.zip`，在 AstrBot 插件页的「从文件安装」上传，再把插件设置里的 `connector_token` 填成 personagent `.env` 里的 `CONNECTOR_TOKEN`。AstrBot 不在这台电脑上时用这种，这时插件的 `personagent_url` 还要填成 personagent 的 HTTPS 地址（见下面 Docker 那段）。

装好后重启 AstrBot（或在插件页重载插件），然后用 `personagent run` 启动角色服务并一直开着。在 AstrBot 里添加 OneBot v11 机器人（反向 WebSocket 端口 `6199`），NapCat 照上面第 3 步指向它。AstrBot 的界面以[它的官方文档](https://docs.astrbot.app)为准。

AstrBot 在 Docker 里的话，`127.0.0.1` 指的是容器自己，插件会拒绝发往其他地址的明文 `http://`。二选一：给 AstrBot（和同一个 compose 里的 NapCat）用主机网络（`network_mode: host`，`docker run` 用 `--network host`；Docker Desktop 需要 4.34 以上，并打开 `Enable host networking`）；或者给 personagent 一个 HTTPS 地址，再运行 `personagent connect astrbot <data 文件夹> --url https://你的地址`。

### 第三方路线排查

1. **AstrBot 没把消息交出来。** 在插件设置里确认 `groups` 里有这个群号；私聊要在 `dm_users` 里填发送者的 QQ 号。再确认 `excluded_platforms` 里没有 `aiocqhttp`。
2. **回话的是 AstrBot 自带的模型（口气突然变了）。** 看 AstrBot 的日志：
   - `refusing unsafe personagent_url`：插件里的 `personagent_url` 不对。在同一台电脑上就用 `http://127.0.0.1:8080`。
   - `agent refused the request (403)`：两边的 `CONNECTOR_TOKEN` 不一致，或者两台电脑的时钟差了五分钟以上。重新运行 `personagent connect astrbot` 会把两边改成同一个。
   - `timed out waiting for the agent`：模型太慢。插件的 `timeout_s` 默认 420 秒，够 personagent 默认设置下最坏的 360 秒；调大过 `LLM_TIMEOUT_S` 或 `LLM_MAX_RETRIES` 的话，把 `timeout_s` 也调大。
   - `agent request failed`：personagent 没在运行，或者地址、端口写错了。
3. **QQ 私聊被挡。** 经 NapCat 来的 QQ 私聊，必须来自管理员（`ADMIN_IDS`）或在 `ACCESS_DM_USERS` 里。
4. **`QQ_BOT_ID` 没填或填错。** 应该是小号的 QQ 号。
5. **忘了学过的东西。** 经 NapCat 的 QQ 会话必须有 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`，少了它所有 QQ 会话都会被当成新会话。

**NapCat 的 HTTP 服务**是可选的。开了之后，personagent 还能补回它离线期间漏掉的 @：在 NapCat 里打开 HTTP 服务，并在 `.env` 里写 `QQ_ONEBOT_URL=http://127.0.0.1:3000`（端口按 NapCat 里设的）和 `QQ_BOT_ID`（小号的 QQ 号）。

**旧的直连方式。** NapCat 直接把事件发给 personagent 的 `/v1/onebot` 这条路已经不推荐，但在 1.x 里仍然能用，需要在 `.env` 里写 `QQ_ONEBOT_URL`（没有它机器人只收不回；`personagent doctor` 会提醒）。改用 AstrBot 后，要把 NapCat 里指向 `/v1/onebot` 的 HTTP 客户端关掉，否则每条消息会收到两遍。学到的记忆会保留。

## 其他文档

- [英文版部署指南](deploy.md)：所有设置、对外暴露端口、错误码。
- [AstrBot 插件说明](../integrations/astrbot/astrbot_plugin_personagent/README.zh-CN.md)
- [免责声明](DISCLAIMER.zh-CN.md)
