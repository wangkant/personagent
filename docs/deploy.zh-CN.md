# 部署 personagent：QQ 扫码直连，以及排查

[English](deploy.md) · 简体中文 · [繁體中文](deploy.zh-TW.md) · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

本文按顺序介绍如何将角色接入 QQ 群：安装、填写 key、用手机 QQ 扫码。QQ 官方机器人由 personagent 直接连接，无需 AstrBot，也无需 NapCat 和 QQ 小号。微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 同样由 personagent 直接连接。如需使用个人 QQ 小号，请参阅后文的[第三方路线：AstrBot + NapCat](#第三方路线astrbot--napcat)。

```text
QQ 群  ⇄  personagent（直连进程 + 角色服务）  ⇄  AI 模型
```

每一步都写明了「你应该看到」的结果。如果结果不符，请勿继续，直接查看[机器人不发言](#机器人不发言)。

## 开始之前

- 一台能长期开机的电脑（Windows、macOS 或 Linux），已安装 Python 3.10 到 3.14。personagent 关闭后，机器人也随之停止。
- 一个 AI 服务的 API key。DeepSeek、硅基流动、阿里云百炼、智谱、Kimi、火山方舟等均可，在各自的控制台中创建。
- 一部已登录你本人 QQ 的手机，用于扫码。

## 第一步：安装并打开

```sh
python -m pip install personagent
personagent
```

如已安装 [uv](https://docs.astral.sh/uv/)，可使用 `uvx personagent` 免安装运行。在 Windows 上也可以下载源码 ZIP，解压后双击 `start.bat`。从 Git 仓库运行的方法见[简明入门](start.zh-CN.md)。

你应该看到一个本地页面：在 Windows 上显示在独立窗口中，在 macOS 和 Linux 上则在浏览器中打开。页面侧栏有六个视图：「开始聊天」「动态」「连接平台」「角色与设置」「演练」「应用」。再次运行 `personagent` 会复用已打开的页面。

> 如需将数据存放在其他磁盘，请运行 `personagent --home D:\personagent`，此后每条命令都须带上相同的 `--home`。不指定时，数据存放在用户目录下的 `personagent` 文件夹。

## 第二步：填写 key 并选择角色

第一次打开页面时，设置表单直接显示在「开始聊天」中；之后可在「角色与设置」中修改。在表单中选择模型服务（共 10 个预设，另有「其他」，可填写任何兼容 OpenAI 的地址），粘贴 API key，再选定名字和性格。保存时，程序会发送一个很小的请求来验证 key，验证不通过则不保存任何内容。

你应该能在「开始聊天」中与角色进行对话，角色会以你选择的性格回复。

「人设」框中是 `persona.txt` 的内容，即角色当前使用的人设。修改后点击「保存人设」，角色服务会重启，已学到的内容将保留。

「角色与设置」中的「更多功能」可开启联网搜索、识别图片和偶尔主动发言。未开启「识别图片」时，角色看不到经各平台收到的图片内容，图片中的文字也不例外。

## 第三步：扫码连接 QQ

1. 打开「连接平台」，选择 **QQ**。
2. 页面会显示二维码。用手机 QQ 扫码并确认，可以新建一个机器人，也可以选择一个已有的机器人，密钥由 personagent 自动获取。如果无法扫码，也可以在 [QQ 开放平台](https://q.qq.com/qqbot/openclaw/login.html)创建机器人，再将 AppID 和 AppSecret 粘贴到页面中。
3. 程序确认 QQ 接受该机器人之后才会保存。如果 QQ 拒绝，页面会给出提示，不保存任何内容。

你应该看到 QQ 出现在页面上方，状态为已连接。

**将机器人添加到群中。** 在手机 QQ 中找到该机器人，可与其私聊或将其添加到群中。机器人能进哪些群由 QQ 决定：通过认证之前，QQ 只允许它加入你担任群主的群。在群中，机器人默认只接收 @ 它的消息，因此不会主动插话；如需让角色跟上群里的对话，请由群主在该群中机器人的资料页开启「接收全量消息」。认证等账号相关事项见 [QQ 机器人官方指南](https://bot.q.qq.com/wiki/bot_new_product-intro/)。

**测试。** 在群中发送一条包含机器人名字的消息（例如 `小夏，你好`），或者 @ 机器人。通常在数秒至十余秒内即可看到回复。

## 其他平台

所有平台都在「连接平台」中添加。凭据会先交给平台验证，通过后才保存。

- **personagent 直接连接**：QQ、个人微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat。个人微信使用手机微信扫码登录（使用腾讯的 iLink 机器人接口），仅支持私聊，因为微信不会将群消息转发给此类机器人。Telegram 需要粘贴 @BotFather 提供的 token；Discord 需要粘贴机器人 token，并开启 Message Content Intent。其余六个平台需要填写的内容和使用限制见[使用手册](guide.zh-CN.md#personagent-直接连接的平台)。
- **经托管的 AstrBot 连接**：其余平台。首次连接此类平台时，personagent 会下载 AstrBot 和独立的 Python 3.12，并在后台运行。该 AstrBot 没有网页后台，也无需另外登录账号。只需粘贴一至两项即可连接的平台有：KOOK、飞书（长连接）、钉钉（Stream 模式）、Slack（Socket Mode，页面上的链接会预先填好应用设置）、企业微信智能机器人（长连接）、Mattermost、Misskey。「高级」分组中的平台需要公网地址或本机的其他软件：企业微信应用、微信公众号、QQ（Webhook）、OneBot v11（NapCat）、Satori。暂不提供 LINE。

已连接的平台默认回复所有群聊和私聊。如需只在部分群聊中回复，请在「角色与设置」→「高级设置」→「管理员与回复范围」中点击「从最近的聊天中选择」，为要保留的群聊勾选「在此群聊中回复」，或直接在「仅在以下群聊中回复」中填写，然后保存，详见[管住它](#管住它)。页面将其保存为 `.env` 中的 `ACCESS_GROUPS`，私聊对应 `ACCESS_DM_USERS`（格式均为 `平台:ID`）。

## 管住它

以下操作都在本地页面中完成。相关设置位于「角色与设置」→「高级设置」，点击「保存」后生效。

- **把自己设为管理员。** 先私聊角色一次，再在「管理员与回复范围」中点击「从最近的聊天中选择」，在自己的账号旁点击「这是我」。扫码接入的 QQ 官方机器人看到的是 openid，而不是 QQ 号，因此请用这种方式设置。
- **只在部分群聊中回复。** 在同一列表中为要保留的群聊勾选「在此群聊中回复」，或在「仅在以下群聊中回复」中填写群聊编号。某个平台一旦列出任一群聊，角色在该平台的其他群聊中便不再回复。
- **暂停全部回复。** 在「其他设置」中关闭「回复消息」。角色仍保持连接，但在重新开启之前不回复任何消息。
- **撤销学到的内容。** 在「动态」中选中该聊天，点击条目旁的「撤销」，或运行 `personagent learned rollback <编号>`。
- **将机器人移出群聊。** 请在平台中将机器人移出群。在「连接平台」中断开只会结束 personagent 的连接，机器人仍是群成员。
- **被移出群或被限制时。** 机器人被移出的群只是不再有消息送达，无需重新连接。平台封禁机器人或将其下架时，personagent 直接连接的平台会停止连接，「连接平台」中会显示原因。

## 日常使用

- 每次开机后运行 `personagent`。页面打开期间，角色服务、直连进程和托管的 AstrBot 均处于运行状态，已连接的平台会自动恢复连接。如不需要打开浏览器，可使用 `personagent up`，效果相同。
- 由 personagent 启动的进程会随其一同结束，无论其以何种方式退出。上次异常退出遗留的进程，会在下次启动时先被停止。
- 所有数据都位于一个主目录中：`.env`（设置）、`persona.txt`（人设）、`runtime/`（学到的内容和日志）、`platforms/`（托管的 AstrBot，以及直连平台的凭据 `direct.json`）。key 仅保存在本机，对话内容会发送给你选择的模型服务。
- 如需直接修改 `.env`，可使用记事本编辑，保存为 UTF-8（不带 BOM），然后重启 `personagent`。
- 发布新版本时，「开始聊天」视图和终端会给出与你的安装方式对应的更新命令。页面和 `personagent up` 每天最多向 pypi.org 查询一次，请求中仅包含版本号；在 `.env` 中设置 `UPDATE_CHECK_ENABLED=false` 即可关闭此项检查。
- 手动更新：`python -m pip install -U personagent`（如使用 uv 安装，请运行 `uv tool upgrade personagent`）。从 0.x 升级时，如果启动时提示存在旧设置名，请运行 `personagent doctor --fix`，该命令会将 `.env` 中的旧名称改为新名称，并将原文件另存为 `.env.bak`。
- 命令行：`personagent init --terminal`（终端设置向导）、`chat`（在终端中聊天）、`demo`（无需 key 的演示）、`run`（只启动角色服务）、`doctor`（检查设置和各项服务）、`learned`（查看学到的内容，必要时介入）、`memory`（查看记住的内容，删除或恢复某一项）、`eval`（评测）。

## 动态

本地页面侧栏中的「动态」列出角色所在的每个群聊和私聊。选中一个聊天，可以看到角色学到的内容及各自如何投入使用、仍在观察的内容及各自的进展、角色记住的内容，以及近期的消息：角色每次发言的原因，以及未发言时的理由。这里没有任何内容需要你确认。详见[使用指南](guide.zh-CN.md#动态)。

「动态」的数据来自本地页面所启动的角色服务，取自其在 `/api/dashboard/` 下的 JSON 接口。仅使用 `personagent run` 启动服务时，请查看服务日志，并使用 `personagent learned` 查看学到的内容、`personagent memory` 查看记住的内容。每次调用都须带有 `X-Personagent-Dashboard-Token` 请求头，值是运行目录（默认 `<主目录>/runtime/`，可用 `AGENT_RUNTIME_DIR` 修改）中 `dashboard.token` 文件的内容。该文件在服务启动时生成，仅本人可读。修改操作还须带有 `X-Personagent-Dashboard: 1` 和 `Content-Type: application/json`；请求如果带有 `Origin`，则必须是服务自身的地址。跨站的浏览器请求一律拒绝，`CONNECTOR_TOKEN` 也无法访问该接口。返回内容中的密钥均会被遮盖。脚本也可以按相同的方式调用。设置 `DASHBOARD_ENABLED=false` 会关闭该接口，「动态」随之不显示内容，`personagent doctor` 会打印 `activity: off (...)`。

角色服务本身不提供网页，访问 `http://127.0.0.1:8080/` 只会显示一段说明，指向本地页面和 `personagent learned`，以前的 `?token=` 链接现在也只打开这段说明。本地页面只监听 127.0.0.1。在没有本地页面的服务器上，可使用 `personagent learned` 查看角色学到的内容、正在观察的内容及原因，并可立即启用、搁置、撤回某项，或恢复由角色或时限搁置、由角色或规则停止使用的内容；`personagent memory` 可列出角色记住的内容，并删除或恢复某一项。

## 学习机制

一声「哈哈」或单独一句话不会改变机器人。同一个聊天中出现两次一致的反应、且其中至少一次足够「强」时，反应即可让改动投入使用。「强」是指**被回复的成员用自己的话纠正了机器人，或者接受了机器人的第二次回答**。旁观者的纠正（即使机器人事后询问了此人）、陌生人的指令、有人直接转换话题，均不计入。因此在默认设置下，一个人只能教会机器人如何回答自己，且仅在其所在的聊天中生效。

后续反应无法确定的条目，由角色自行判断：例如两个人的纠正相互矛盾、同一条回复的两种改写并存，或者被回复的成员作了纠正但无人确认。角色每次判断调用一次模型，决定投入使用、搁置或继续观察，并记录理由。旁观者对学到内容的抱怨，同样由角色权衡后决定是否继续使用。连续 30 天（`PROMOTE_OBSERVE_MAX_DAYS`）没有新反应的条目会被搁置。任何内容都无需你确认。

学到的所有内容都记录在只追加的学习记录中，可随时介入：

- 在「动态」中，「学习记录」下的每一条都说明了如何投入使用，并带有「撤销」按钮；「仍在观察」下的每一条都说明了当前进展，没有按钮。下方的「角色学到的内容」列出全部学到的内容，并可选择「立即投入使用」「搁置」「撤销」，或对由角色或时限搁置、由角色或规则停止使用的条目「恢复使用」；角色未运行时也可以在此操作。
- 也可以使用命令：`personagent learned`（正在观察的内容）、`personagent learned show <编号>`、`personagent learned rollback <编号>`、`personagent learned restore <编号>`。

如需更保守的学习方式，请在 `.env` 中添加 `PROMOTE_MIN_SPEAKERS=2`，此时需要两个不同的人都认可，反应才会让改动投入使用；在此之前角色会继续观察。设置 `PROMOTE_JUDGE_ENABLED=false` 后，角色不再自行判断，反应无法确定的条目保持观察中；设置 `PROMOTE_AUTO_ENABLED=false` 后，不会再有新的内容投入使用。

在群中向机器人发送 `小夏 记住 …`、`小夏 忘掉 …`、`小夏 你都记得什么`，可以直接管理其记忆；`小夏 学到了什么` 会列出其学到的内容。命令必须放在消息开头。以「吗」「呢」「没」等结尾的问句（例如 `小夏 记住了吗`）仅作为聊天处理；`小夏 忘掉这个` 的意思是「算了」，不会删除任何内容。每条笔记都会记录记录者及其涉及的成员；不涉及具体成员的笔记全群可见，列出时标注「来自某某」。

修改人设不会清空角色学到的内容。

## 记忆

角色会为每个聊天保存近期消息（在 `runtime/recent.json` 中保留 72 小时，重新启动不会丢失）、此前对话的摘要、带日期的事件、关于成员和群聊的事实，以及常驻记忆。较早的消息离开近期消息的范围时，会调用一次判断模型进行记忆整理，更新摘要、事件和事实，每项更改都单独检查。每个聊天每天最多整理 16 次，所有聊天合计不超过 `MEMORY_CALLS_PER_DAY`（默认 40）次；设为 0 即关闭。角色自行移除的内容可在 30 天内恢复，在页面或终端中删除的内容可在 24 小时内恢复；在聊天中要求忘记的内容和「清除此聊天的记忆」都无法恢复，磁盘上的每日副本也不会保留。在「动态」中选中一个聊天，「记忆」部分会列出全部内容；在终端中可使用 `personagent memory`。详见[使用指南的记忆一节](guide.zh-CN.md#记忆)。

## 机器人不发言

请按顺序排查，越靠前的原因越常见。角色服务由本地页面启动时，请先查看「动态」：聊天是否出现、是否收到消息、角色为何未发言，均可在此处查看。在服务器上，请查看服务日志，学到的内容请用 `personagent learned` 查看，记住的内容请用 `personagent memory` 查看。然后查看主目录下 `runtime/desktop/` 中的日志：`agent.log`（角色服务）、`direct.log`（personagent 直接连接的平台）、`astrbot.log`（其他平台）。

1. **消息未送达。** 在「连接平台」中确认该平台显示为已连接。QQ 机器人必须已在群中，群中能接收哪些消息由 QQ 的设置决定；个人微信仅支持私聊。使用第三方 AstrBot 时，请参阅[第三方路线排查](#第三方路线排查)。
2. **角色服务未开启，或缺少 key。** 在「角色与设置」中重新填写 key 并保存。如果 `.env` 中设置了 `AGENT_ENABLED=false`，请改为 `true` 后重启。
3. **未点名角色。** 在群中，角色只回应包含其名字（`PERSONA_NAME`）或 @ 它的消息。其他情况下，须待群中消息累计达到 `CHAT_TRIGGER_COUNT` 条（默认 30 条）后才会考虑插话，且考虑之后也可能选择不发言。凌晨 2 点到 7 点角色更少插话。`AGENT_LANG` 为 `zh` 或 `zh-TW` 时按北京时间计算，如需更换时区，请在 `.env` 中设置 `PERSONA_TZ_OFFSET_HOURS`。测试时请先用名字点名角色。
4. **被 personagent 自身的白名单拦截。** `.env` 中的 `ACCESS_GROUPS`、`ACCESS_DM_USERS` 一旦包含某个平台的条目，该平台就只放行列出的条目。被拦截的会话会在 `agent.log` 中记录一行。
5. **模型调用失败。** key 无效或余额耗尽时，`agent.log` 中会有一行 ERROR，注明相关服务及应修改的设置。运行 `personagent doctor` 会向每个模型发送一个很小的请求，直接显示状态码。主模型超时或连接中断、且 `LLM_FALLBACK_MODEL` 指定了不同的模型时，本次调用会立即改用备用模型；服务方在正常响应中返回的错误（如 OpenRouter 的上游故障）按相应的 HTTP 错误处理。「动态」中会将这一回合标为「模型未作出回应」。
6. **设置名拼写错误。** 拼写错误的设置名不会报错，程序只会继续使用默认值。`personagent doctor` 和启动日志会列出无法识别的设置名。
7. **`.env` 带有 BOM。** 用记事本另存时选错编码，会导致第一行设置失效。`personagent doctor` 会报告此问题，改用「UTF-8」（不带 BOM）重新保存即可。
8. **可以回复，但遗忘了学过的内容。** 修改 `PERSONA_NAME` 或 `PERSONA_VERSION` 会使其被视为新角色；在「人设」框中修改人设则不会。

如果仍然无法解决，请在 [Issues](https://github.com/wangkant/personagent/issues) 中提问，并附上 `personagent doctor` 的输出（先遮盖 key 和账号）。

## 第三方路线：AstrBot + NapCat

AstrBot、NapCat（OneBot）、Koishi（经 Satori 连接器）和 Matrix（经 mautrix 桥接 WhatsApp、Signal 等）是 personagent 可以配合使用的第三方桥接，连接 personagent 直接连接的平台时无需使用这些桥接。只有在需要使用**个人 QQ 小号**而非官方机器人时，才需要 NapCat。

注意：NapCat 不是腾讯官方客户端，小号有被限制甚至封禁的风险。请勿使用你本人的主号，详见 [DISCLAIMER.zh-CN.md](DISCLAIMER.zh-CN.md)。

### 使用托管的 AstrBot（推荐）

1. 按 [NapCat 文档](https://napneko.github.io/)安装 NapCat，使用手机上的**小号**扫码登录。
2. 在 personagent 页面的「连接平台」中选择「高级 → OneBot v11（NapCat）」，端口默认为 `6199`。
3. 在 NapCat 的网页中依次点击「网络配置」→「新建」→「WebSockets 客户端」，勾选「启用」，URL 填 `ws://127.0.0.1:6199/ws`，然后保存。

托管的 AstrBot 会自动安装 personagent 插件，并写入 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。使用此路线时，NapCat 也需要持续运行。

### 使用你自己的 AstrBot

插件 `astrbot_plugin_personagent` 是 AstrBot 将消息转交给 personagent 的途径。有两种安装方式：

- 运行 `personagent connect astrbot`，按提示选择 QQ（通过 NapCat），填写小号的 QQ 号、群号和你自己的 QQ 号。该命令会将插件复制到 AstrBot 的 `plugins` 文件夹，在两边写入同一个 `CONNECTOR_TOKEN`，并写入白名单和 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。如果不确定 AstrBot 的 `data` 文件夹位于何处，可以搜索 `cmd_config.json`。
- 也可以从 personagent 的[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下载 `astrbot_plugin_personagent.zip`，在 AstrBot 插件页的「从文件安装」中上传，再将插件设置中的 `connector_token` 填为 personagent `.env` 中的 `CONNECTOR_TOKEN`。AstrBot 不在本机时请使用此方式，此时插件的 `personagent_url` 还需要填写 personagent 的 HTTPS 地址（见下文 Docker 一段）。

升级 personagent 后，重新运行 `personagent connect astrbot` 或上传新的 zip。AstrBot 4.29 及以后的版本会直接替换已安装的插件；更早的版本需要先卸载插件，卸载时请勿勾选删除插件配置文件。

安装完成后，重启 AstrBot（或在插件页重载插件），然后用 `personagent run` 启动角色服务并保持运行。在 AstrBot 中添加 OneBot v11 机器人（反向 WebSocket 端口 `6199`），再按上一节第 3 步让 NapCat 指向它。AstrBot 的界面以[其官方文档](https://docs.astrbot.app)为准。

如果 AstrBot 运行在 Docker 中，`127.0.0.1` 指的是容器本身，而插件会拒绝发往其他地址的明文 `http://`。可任选其一：为 AstrBot（以及同一个 compose 中的 NapCat）使用主机网络（`network_mode: host`，`docker run` 时用 `--network host`；Docker Desktop 需要 4.34 及以上版本，并开启 `Enable host networking`）；或者为 personagent 提供一个 HTTPS 地址，再运行 `personagent connect astrbot <data 文件夹> --url https://你的地址`。

### 第三方路线排查

1. **AstrBot 未转发消息。** 在插件设置中确认 `groups` 包含该群号；私聊需要在 `dm_users` 中填写发送者的 QQ 号。再确认 `excluded_platforms` 中没有 `aiocqhttp`。
2. **回复来自 AstrBot 自带的模型（语气突然改变）。** 查看 AstrBot 的日志：
   - `refusing unsafe personagent_url`：插件中的 `personagent_url` 不正确。在同一台电脑上应填写 `http://127.0.0.1:8080`。
   - `agent refused the request (403)`：两边的 `CONNECTOR_TOKEN` 不一致，或者两台电脑的时钟相差超过五分钟。重新运行 `personagent connect astrbot` 会将两边改为同一个令牌。
   - `timed out waiting for the agent`：模型响应过慢。插件的 `timeout_s` 默认为 420 秒，足以覆盖 personagent 默认设置下最长的 360 秒；如果调大了 `LLM_TIMEOUT_S`，也须相应调大 `timeout_s`。
   - `agent request failed`：personagent 未运行，或者地址、端口填写有误。
3. **QQ 私聊被拦截。** 经 NapCat 接入的 QQ 私聊，必须来自管理员（`ADMIN_IDS`），或者在 `ACCESS_DM_USERS` 之中。
4. **`QQ_BOT_ID` 未填写或填写错误。** 此处应填写小号的 QQ 号。
5. **遗忘了学过的内容。** 经 NapCat 的 QQ 会话必须配置 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`，缺少该项时，所有 QQ 会话都会被视为新会话。

**NapCat 的 HTTP 服务**是可选的。开启后，personagent 能补收其离线期间遗漏的 @ 消息。方法是在 NapCat 中开启 HTTP 服务，并在 `.env` 中写入 `QQ_ONEBOT_URL=http://127.0.0.1:3000`（端口以 NapCat 中的设置为准）和 `QQ_BOT_ID`（小号的 QQ 号）。

**旧的直连方式。** NapCat 直接将事件发送到 personagent 的 `/v1/onebot`，此方式已不再推荐，但在 1.x 中仍然可用。该方式要求在 `.env` 中写入 `QQ_ONEBOT_URL`，否则机器人只接收不回复，`personagent doctor` 会对此给出提醒。改用 AstrBot 之后，须关闭 NapCat 中指向 `/v1/onebot` 的 HTTP 客户端，否则每条消息都会收到两遍。已学到的记忆会保留。

## 部署参考

前文的教程介绍了如何完成部署。本部分是长期运行所需了解的全部内容：设置、进程、接口、错误码和费用。

### 最小可运行配置

本地页面（`personagent`，或用 `personagent init --terminal` 运行终端向导）会发送一个很小的请求验证 key，然后将 `.env` 写入主目录。聊天需要 key，`.env.example` 默认使用 OpenRouter 的免费模型：

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

`.env` 中只写 key 时，地址和模型分别为 `https://api.deepseek.com` 和 `deepseek-flash`。二者可以指向任何兼容 OpenAI 的接口，托管或本地（Ollama、llama.cpp）均可。API 地址请按服务商文档粘贴，根地址或 `.../v1`、`.../api/paas/v4` 这类带版本的地址均可。在你编写 `persona.txt` 之前，使用的是随包附带的 `data/persona.example.<lang>.txt`。在设置 `PERSONA_NAME` 之前（设置流程会写入），角色名为 "bot"。

页面还会写入 `PERSONA_NAME`、`AGENT_LANG` 和一个 `CONNECTOR_TOKEN`。从页面连接的平台无需在 `.env` 中另行写入任何内容。其凭据存放在 `<home>/platforms/`：`direct.json` 保存 personagent 直接连接的平台，其余平台由托管的 AstrBot 保存在其自身的配置中。可选的补充：

```
ADMIN_IDS=telegram:12345             # 管理员的账号，<platform>:<id>
# 只有经 NapCat（OneBot）接 QQ 时才需要
QQ_BOT_ID=...                        # 机器人账号的号码
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

key 仅保存在本机，对话内容会发送给你选择的模型服务。`.env.example` 中的其他设置均有可用的默认值。`SERVER_HOST` 和 `SERVER_PORT` 是 `127.0.0.1:8080`，`QQ_ONEBOT_URL` 为空（没有 NapCat HTTP 服务），`ACCESS_GROUPS` 为空表示所有群均由连接器决定。

### 运行

`personagent` 打开本地页面。页面打开期间，personagent 运行角色服务、直连平台的进程，以及已安装的托管 AstrBot。再次运行 `personagent` 会复用已打开的页面。`personagent up` 启动同样的进程，但不打开浏览器。

两种方式下，这些进程都随 personagent 一同结束，无论其以何种方式退出。上次崩溃遗留的进程会在下次启动时被停止。每个进程将日志写入 `<home>/runtime/desktop/`（`agent.log`、`direct.log`、`astrbot.log`）。

本地页面和 `personagent up` 每天最多向 pypi.org 查询一次是否有新版本。发布新版本时，「开始聊天」视图和终端会显示更新当前安装的命令。请求中仅包含版本号，`UPDATE_CHECK_ENABLED=false` 可关闭此项检查。

`personagent run` 只启动角色服务，见[只启动服务](guide.zh-CN.md#只启动服务)。你自己的连接器（你运行的 AstrBot、Satori、Matrix）连接角色服务时，请使用此命令。`personagent doctor` 检查设置，并探测每个上游服务。

**1.0 修改了设置名。** 只要仍在使用 1.0 已废弃的设置名，启动就会以退出码 2 拒绝，并逐个列出 `OLD -> NEW`。`personagent doctor --fix` 会修改 `<home>/.env` 中的名称。该命令保留值和注释，将旧文件另存为 `.env.bak`；如果新名称已经设置，则将旧的那一行注释掉。写在环境变量而非 `.env` 中的废弃名称，须在设置它的位置修改。只要仍有残留，`personagent doctor` 就以 1 退出，`--json` 会将其列在 `retired_settings` 下。`HOST`、`PORT` 和 `LOG_FILE` 只有写在 `.env` 中才会生效。

#### 动态接口

[动态](guide.zh-CN.md#动态)是本地页面中的一个视图。该视图无需额外安装，不从互联网加载任何内容，也从不显示 key 或 token。它读取本地页面所启动的角色服务的 JSON 接口。仅使用 `personagent run` 时，请查看服务日志，并使用 `personagent learned` 和 `personagent memory`。`DASHBOARD_ENABLED=false` 会关闭该接口，此时视图会说明情况，`personagent doctor` 打印 `activity: off (...)`。

接口位于角色服务的 `/api/dashboard/` 下：

- `GET conversations` 和 `GET conversation?id=<chat id>` 读取服务知道的聊天，以及某个聊天的详情。`conversations` 中的每个聊天带有 `learned`、`observing`（观察中的条目数）和 `latest`（最近一次有内容投入使用的时间）。`conversation` 返回 `learned` 和 `observing` 两个列表：观察中的条目带有 `standing`（所处阶段、尚缺的条件、角色的理由，以及将被搁置的日期）；使用中的条目带有 `by`（`reactions`、`character` 或 `person`）和 `why`。它还返回该聊天记住的内容：`memories`、`core_note` 与 `core_at`、`thread`、`episodes`、`removed` 和 `memory_status`。
- `POST candidates/<id>/promote`、`replace`、`reject`、`rollback` 和 `restore` 是人工可选的操作。每次操作都与 `personagent learned` 写入同一份学习记录，操作者记为 `dashboard`。`restore` 可以恢复由角色或时限搁置的内容，以及由角色或规则停止使用的内容；由人工撤销或搁置的内容、被内容规则舍弃的内容保持不变；`promote` 不能恢复已撤销的内容。
- `POST memory/forget` 带上请求体 `{"conv": "<chat id>", "kind": "note", "id": "<id>"}`，删除一项记忆，并返回 `tid`；将 `{"tid": "<tid>"}` 发给 `POST memory/restore` 即可恢复。`kind` 可以是 `note`、`episode`、`thread` 或 `core`。原有的请求体 `{"conv": "<chat id>", "note": "<note id>"}` 仍然可用，不带 `note` 时删除该聊天的核心笔记。
- `POST memory/forget_chat` 带上 `{"conv": "<chat id>"}`，清除该聊天记住的全部内容，无法撤销。
- `GET memory/list?conv=<chat id>` 列出各聊天记住的内容以及仍可恢复的内容；服务运行时，`personagent memory` 通过它读取。

每次调用都须带有 `X-Personagent-Dashboard-Token` 请求头，值为运行目录（默认 `<home>/runtime/`，除非 `AGENT_RUNTIME_DIR` 修改了该目录）中 `dashboard.token` 文件内的 token。该文件仅本人可读，在服务启动时生成。不带该请求头的调用返回 401（`dashboard_token`），token 错误返回 403（`wrong_token`）。`CONNECTOR_TOKEN` 和 `X-Personagent-Token` 无法访问该接口，二者仅用于连接器和 `/health/details`。

- 写操作还须带有 `X-Personagent-Dashboard: 1` 和 `Content-Type: application/json`。请求带有 `Origin` 时，必须是服务自身的地址。
- 跨站的浏览器请求一律拒绝。
- 响应中的所有凭据都替换为 `***`。启动检查中的 URL 还会遮盖用户名、密码和查询串。
- 同一台电脑上的脚本可以按本地页面的方式调用该接口。

服务本身不提供页面。`GET /` 返回一段简短说明，指向本地页面和 `personagent learned`，以前的 `?token=` 链接现在也打开这段说明。本地页面只绑定 127.0.0.1。在没有本地页面的服务器上，可使用 `personagent learned` 查看角色学到的内容、正在观察的内容及原因，并可立即启用、搁置、撤回某项，或恢复由角色或时限搁置、由角色或规则停止使用的内容；`personagent memory` 可列出角色记住的内容，并删除或恢复某一项。

### 主机要求

1. **可写的主目录。** 启动时会在 `<home>/.personagent.instance.lock` 上加锁，该文件位于 `runtime/` 之外。主目录只读时无法启动。
2. **每个主目录一个进程。** 同一主目录上的第二个 `personagent run` 会退出，并用一句话说明。
3. **空闲的端口。** 端口被占用或被禁止时也会退出，并用一句话说明。可用 `--port` 或 `SERVER_PORT` 更换端口。

`AGENT_RUNTIME_DIR` 必须解析到主目录之内，否则启动失败。相对路径的 `PERSONA_FILE` 或 `PERSONA_CARD_FILE` 也按主目录解析，因此存放在其他位置的人设须使用绝对路径。

`memory.json`、`core_memory.json` 或 `episodes.json` 损坏时，启动会以退出码 2 停止，并用一句话指出损坏的文件以及应换上的 `.bak` 副本。损坏的文件保持原样。

### 连接平台

在本地页面的「连接平台」中添加平台。personagent 在保存之前会先向平台验证凭据。平台拒绝时，页面会显示拒绝原因，且不保留任何内容。

在没有显示器的服务器上，可在终端中使用 `personagent connect <平台>` 连接 personagent 直接连接的平台，例如 `personagent connect telegram`。该命令执行与页面相同的步骤和核验，并以相同的格式保存。QQ 和微信会在终端中显示二维码，Twitch 会显示一个链接和一个代码。加 `--no-input` 并以参数形式提供全部内容时，命令不进行任何询问；缺少必填项时以退出码 2 结束。随后运行 `personagent up`，即可启动 personagent 及其已连接的平台。[该命令及其参数](guide.zh-CN.md#在终端中连接平台)的说明见使用手册。

**由 personagent 直接连接。** QQ、个人微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 运行在一个「直连」进程中，不需要 AstrBot 和 NapCat。某个平台无法加载时会被跳过，其余平台仍正常启动。下表列出前四个平台；其余六个平台需要填写的内容和使用限制见[使用手册](guide.zh-CN.md#personagent-直接连接的平台)。

| 平台 | 操作 | 限制 |
|---|---|---|
| QQ（官方机器人） | 用手机 QQ 扫码，新建机器人或选择你已创建的机器人。备用方法是粘贴 AppID 和 AppSecret。 | 通过认证之前，QQ 只允许它加入你担任群主的群。在群中默认只接收 @ 它的消息，群主可在该群中机器人的资料页开启「接收全量消息」；开启之前它无法主动插话。 |
| 个人微信 | 用微信扫码（腾讯的 iLink 机器人接口）。 | 仅支持一对一聊天。微信不会将群消息转发给此类机器人。 |
| Telegram | 粘贴 @BotFather 提供的 token。 | |
| Discord | 粘贴机器人 token，并开启 Message Content Intent。 | |

**经托管的 AstrBot。** 其他平台均经由 personagent 下载的 AstrBot（连同其专用的 Python 3.12 运行环境）接入，在后台运行。该 AstrBot 没有网页后台，也无需另外登录。KOOK、飞书（长连接）、钉钉（Stream 模式）、Slack（Socket Mode，指南链接会预先填好应用设置）、企业微信智能机器人（长连接）、Mattermost 和 Misskey 只需填写一至两项。「高级」分组需要公网地址或其他软件：企业微信应用、微信公众号、QQ Webhook、OneBot v11（NapCat）和 Satori。不提供 LINE。

两种路径下，已连接的平台都会回应平台转发给机器人的每个群聊和私聊。一旦 `ACCESS_GROUPS` 或 `ACCESS_DM_USERS` 列出了该平台的条目，情况即会改变（见[personagent 自身的白名单](#经已在运行的-astrbot)）。ID 以 `<platform>:<id>` 形式到达，例如 `qq_official:<openid>`、`weixin_oc:<id>`、`telegram:<id>` 和 `discord:<id>`。QQ 官方机器人获取的是 openid，而非 QQ 号。直接连接某个平台时，会移除同一平台的 AstrBot 连接。

### 经已在运行的 AstrBot

AstrBot、NapCat（OneBot）、Koishi（经 [Satori 连接器](../integrations/satori/README.zh-CN.md)）和 Matrix（经 [Matrix 连接器](../integrations/matrix/README.zh-CN.md)和 mautrix 桥接）是 personagent 可以配合使用的第三方桥接。连接 personagent 直接连接的平台时无需使用这些桥接。

AstrBot 通过 `integrations/astrbot/astrbot_plugin_personagent/` 中的插件将消息转交给 personagent。插件将每条消息发送到 `POST /v1/events`，并转发响应中的回复。插件还会拉取 personagent 的 outbox（`outbox_enabled`，默认开启），因此在平台允许机器人主动发言的场合，角色可以主动发起对话。插件说明中有详细的表格。托管的 AstrBot 会自动安装插件。使用你自己的 AstrBot 时，请先启动一次，使其生成 data 文件夹（其中有 `cmd_config.json`、`plugins/` 和 `config/`），然后运行：

```
personagent connect astrbot                       # 询问，并自行查找 AstrBot 的文件夹
personagent connect astrbot <AstrBot data dir>    # 不询问
```

该命令将插件复制到 `<data dir>/plugins/`，并将同一个 `CONNECTOR_TOKEN` 写入 `.env` 和插件配置。它将 `personagent_url` 设为 `http://127.0.0.1:<SERVER_PORT>`，除非插件已有其接受的地址（本机地址，包括隧道，或 HTTPS）。

AstrBot 位于另一台机器上时，请从[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下载 `astrbot_plugin_personagent.zip`，在 AstrBot 插件页的「从文件安装」中上传。将其 `connector_token` 设为 personagent `.env` 中的 `CONNECTOR_TOKEN`，并将 `personagent_url` 设为 personagent 的 HTTPS 地址（见[对外暴露接口](#对外暴露接口)）。

升级 personagent 后，重新运行 `connect astrbot` 或上传新的 zip。AstrBot 4.29 及以后的版本会替换已安装的副本。更早的版本需要先卸载，卸载时请勿勾选「同时删除插件配置文件」。

`connect astrbot` 的选项：

- `--qq` 将 `aiocqhttp` 从 `excluded_platforms` 中移除，`--no-qq` 将其重新加入。两者均未指定时，QQ 路由保持原样。`CONNECTOR_QQ_PLATFORMS` 跟随插件的最终行为。
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>` 同时在 AstrBot 自身的配置中开启该适配器。Slack 还需要 `--app-token`，飞书和 QQ 要 `--app-id` 和 `--app-secret`。已有的适配器条目保留其他设置（代理、基础地址、轮询），只更新凭据。
- `--url https://...` 设置插件发送请求的 HTTPS 地址。
- `--install` 改为下载托管的 AstrBot，`--start` 启动它。

首次运行时白名单为空。重复运行会保留白名单，以及其他被排除的平台。

插件默认拒绝所有消息。请在 AstrBot 网页中填写 `groups`，私聊填写 `dm_users`，或者回答 `connect` 的提问。`dm_users` 不为空后才转发私聊。[插件说明](../integrations/astrbot/astrbot_plugin_personagent/README.zh-CN.md)列出了所有设置项。托管的 AstrBot 会用 `<platform>:*` 放行你连接的每个平台。安装插件后，重启 AstrBot 或在网页中重新加载插件。在 personagent 这边：

- `CONNECTOR_TOKEN` 认证每个请求。请求带 `X-Personagent-Token` 请求头，外加以 token 为密钥、对 `timestamp.nonce.body` 计算的 HMAC-SHA256，防重放机制会拒绝重复的 nonce。截获的请求无法重放或篡改。token 同时也是签名密钥，因此请勿将其写入日志，泄露后须更换。同一主机上可选，跨主机时必须设置。
- `ADMIN_IDS` 以 `<platform>:<id>` 列出管理员的账号（`telegram:12345`、`discord:4242`）。不带前缀的 ID 或 `qq:<id>` 是 QQ 号。`ADMIN_NAME` 设置管理员的名字。列出的所有账号都属于同一个人，此人在群聊和私聊中会得到更亲近的人设，可以管理机器人记住的群内容，也可以独自教导机器人。经 AstrBot 时，平台名是 AstrBot 显示的适配器名，在聊天中发送 `/sid` 可查看 ID。
- `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 让 personagent 自行对平台进行把关，格式同为 `<platform>:<id>`。每个平台单独把关。没有条目的平台由连接器决定；只要有一条条目，该平台就只放行列出的条目。personagent 拒绝的回合不会被接管，因此 AstrBot 自带的模型可能会回答。

AstrBot 位于 Docker 中或另一台主机上时，请参阅[使用指南](guide.zh-CN.md#你自己运行的桥接)。

#### 经 NapCat（OneBot）接入 QQ

此路径使用个人 QQ 账号代替官方机器人。你需要一个已在目标群中的 QQ 小号，请勿使用本人的主号（见 [DISCLAIMER.zh-CN.md](DISCLAIMER.zh-CN.md)）。该小号登录（通常通过扫码，会话在重启后保留）一个 OneBot v11 实现，后者连接 AstrBot 的 `aiocqhttp` 适配器。[NapCat](https://github.com/NapNeko/NapCatQQ) 已经过测试，它附着在 QQ NT 桌面客户端上。LLOneBot 和 Lagrange 是其他 OneBot v11 实现。

使用托管的 AstrBot 时，在本地页面添加「高级 → OneBot v11（NapCat）」，并让 NapCat 指向 `ws://127.0.0.1:6199/ws`。[第三方路线](#第三方路线astrbot--napcat)一节有分步说明。使用你自己的 AstrBot 时，请从插件的 `excluded_platforms` 中移除 `aiocqhttp`，设置 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`（`--qq` 会同时完成这两项），并设置 `QQ_BOT_ID`（`personagent connect astrbot` 会询问）。

**此处必须设置 `CONNECTOR_QQ_PLATFORMS`。** 缺少该项时，QQ ID 会带命名空间（`aiocqhttp:123456`）到达，每个会话看起来都是新会话。记忆、历史和学到的样例都以不带前缀的 ID 为键，学习记录的行 ID 也由会话 ID 派生，因此这种分裂事后无法修复。

不带前缀的 ID 具有 QQ 权限，因此 `ADMIN_IDS`、`ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 的 QQ 条目在插件白名单之上继续生效。QQ 私聊必须在 `dm_users` 中，*并且*来自管理员或 `ACCESS_DM_USERS` 的条目。`ACCESS_GROUPS` 列出 QQ 群时，QQ 群必须同时在两边。只有在信任某个连接器拥有此权限时，才将其平台列入 `CONNECTOR_QQ_PLATFORMS`。

**NapCat 的 HTTP 服务**（`QQ_ONEBOT_URL`，默认为空）在此路径上是可选的。personagent 还会主动发送以下消息：

- 主动消息（`PROACTIVE_ENABLED`，默认关闭）；
- 被否定两分钟后的追问（`REACT_ELICIT_ENABLED`）；
- 模型调用失败时在群中发送的致歉。

插件拉取 outbox 时，这些消息经插件的 outbox 发回。未拉取时，如果设置了 `QQ_ONEBOT_URL`，则发送到该地址。只有补收离线期间遗漏的 @ 才需要该服务，同时需要 `QQ_BOT_ID`。此项扫描在启动时运行，之后每 30 分钟运行一次。其范围覆盖 `ACCESS_GROUPS` 中的 QQ 群，以及上次重启后有消息的群，并重放一小时内的 @。地址为空时，`personagent doctor` 把 OneBot 桥接显示为 "not configured"。

**所有连接器路径均不具备的功能**（直连、AstrBot 或其他连接器），无法通过任何设置恢复：

- 没有视觉模型描述的图片的 OCR 备用方案；
- 经 NapCat 查询引用。引用从 personagent 自身的近期消息索引，以及连接器随引用发送的被引用文字中解析。

所有路径都会收集新表情，与 QQ 相同：来源是群中发送的、直接附带图片或标为表情的图片。连接器仅以链接形式发送的照片不会被收集。

### 同时接多个平台

多个连接器可以同时连接一个 personagent，因为每个连接器都标明其所属平台（`telegram:-1001234`、`matrix:!room:example.org`）。直连进程、AstrBot、Satori 和 Matrix 可以同时运行。请勿让同一个聊天经两个连接器接入，否则每条消息都会收到两次。带命名空间的 ID 不会与不带前缀的 QQ 号冲突。

非应答的消息经拉取 personagent outbox 的连接器到达平台。这些消息包括主动开场、被否定后的追问，以及群聊中模型调用失败时的致歉。私聊的致歉随带来该消息的请求的响应返回。

直连进程和这里的三个连接器都会拉取 outbox，前提是平台允许机器人先发言。QQ 会限制官方机器人主动发消息的频率，用户也可以关闭这类消息。你自己的连接器在事件中发送 `connector_id`、`reply_handle` 和 `"capabilities": ["outbox"]`，并长轮询 `/v1/outbox`（见[连接器协议](connectors.zh-CN.md)）。没有此类连接器时，personagent 只能在带来消息的请求内发言。主动发言循环会跳过这些会话，追问和致歉也不会发送。

本地页面也会拉取 outbox，但仅限其自身的对话。不拉取 outbox 的程序（例如在某个对话中发言的编程助手）所发送的事件，不会使拉取 outbox 的连接器失去该对话（见[连接器协议](connectors.zh-CN.md#outboxpost-v1outbox)）。

`PROACTIVE_PLATFORMS` 限制主动发言循环可以在哪些平台上主动发起对话。`PROACTIVE_PLATFORMS=qq_official` 限定在 QQ 官方机器人，`qq` 限定在经 NapCat 的 QQ。`CONNECTOR_OUTBOX_ENABLED=false` 彻底关闭 outbox。

如需不经 outbox 在私聊中主动发起对话，你自己的调度程序（AstrBot 插件任务、cron 条目）可以发送标记了 `"proactive": true` 的私聊事件。见[不经 outbox 主动发起对话](connectors.zh-CN.md#不经-outbox-主动发起对话)。

### 对外暴露接口

连接器和 personagent 在同一台机器上时，保持 `SERVER_HOST=127.0.0.1`。容器只有共享主机的网络命名空间或使用主机网络时，才算同一台机器。本地页面和 `personagent up` 始终绑定 `127.0.0.1`。其他情况下：

1. 设置 `SERVER_HOST=0.0.0.0`（或 `--host 0.0.0.0`）和 `CONNECTOR_TOKEN`。没有 token 时，启动会拒绝绑定网络地址。此处不要求 `QQ_ONEBOT_SECRET`，但没有它时，已弃用的 `/v1/onebot` 在网络绑定下是关闭的。发往它的每个请求都返回 403 `onebot_disabled`，日志会说明一次原因。
2. 在服务前部署 HTTPS 反向代理或私有隧道。此处的每个连接器都只向本机地址或设置了 token 的 HTTPS 地址发送。AstrBot 插件把其他情况记录为 `refusing unsafe personagent_url`，Satori 和 Matrix 连接器拒绝启动。
3. 保持请求体逐字节不变，因为签名覆盖请求体；并确保两边时钟相差不超过五分钟。

凭据为空时，对应接口只服务直接调用 `http://127.0.0.1` 或 `http://localhost` 的本地程序。请求只要带有下列任何一项，即返回 403 `non_local_request`：

- `Origin` 请求头；
- 不是 `none` 的 `Sec-Fetch-Site`；
- 不是 `localhost`、`127.0.0.1` 或 `::1` 的 `Host`；
- 代理请求头：`X-Forwarded-For`、`Forwarded`、`X-Real-IP`、`CF-Connecting-IP`、`Via`、`X-Forwarded-Host`、`X-Forwarded-Proto`、`X-Forwarded-Port`、`True-Client-IP`、`X-Client-IP` 或 `X-Original-Forwarded-For`。

同一主机上不添加这些请求头的代理仍然看起来像本地请求。在添加任何代理或隧道之前，先设置 `CONNECTOR_TOKEN`（使用 `/v1/onebot` 时还有 `QQ_ONEBOT_SECRET`），即使在同一台主机上。

### 健康检查接口

- `GET /health` 免费、公开，不调用任何服务。
- `GET /health/details` 探测上游服务（缓存 60 秒）。`CONNECTOR_TOKEN` 为空时，只回应本地请求。设置了 token 时，它**只**回应带有匹配 `X-Personagent-Token` 请求头的请求，来自本机的请求也不例外。关键探测失败或无法运行时返回 503。关键探测是聊天模型，以及 QQ 使用 OneBot 直连入口时的 OneBot 桥接（设置了 `QQ_BOT_ID` 和 `QQ_ONEBOT_URL`，未设置 `CONNECTOR_QQ_PLATFORMS`）。
- `personagent doctor [--json]` 运行同样的探测和设置检查，在同样的情况下以非零退出。上次更新检查已过一天时，它还会向 pypi.org 查询最新版本（`UPDATE_CHECK_ENABLED=false` 可跳过）。

### 费用

- **探测会产生费用。** `personagent doctor` 和 `/health/details` 向角色实际调用的每个模型发送一个很小的聊天请求：群聊和私聊回复、联网搜索判断、反应判断（`REACT_LEARN_ENABLED` 开启时）、自我审查（`EVAL_ENABLED` 开启时）和视觉。设置了 `EMBEDDING_MODEL` 时还会发送一次嵌入请求，设置了 `TAVILY_API_KEY` 时还会进行一次 Tavily 搜索。`/health` 以及设置和学习记录检查不产生费用。
- **模型用量会被统计。** 每次模型请求都按模型、按日统计，依据是服务方返回的用量，服务方提供费用时一并记录。`personagent doctor` 输出今日与近 7 日的用量，本地页面的「应用」视图也显示同样的数据。统计文件在后台写入，每分钟最多一次，停止运行时再写入一次。
- **学习与记忆。** 角色每次自行判断学习条目时，调用一次 `PROMOTE_JUDGE_MODEL`，每隔 `PROMOTE_JUDGE_INTERVAL_S` 最多 `PROMOTE_JUDGE_BATCH` 次。记忆整理每处理一段聊天调用一次 `LLM_JUDGE_MODEL`，每个聊天每天最多 16 次，所有聊天合计每天不超过 `MEMORY_CALLS_PER_DAY`（40）次。设置 `PROMOTE_JUDGE_ENABLED=false` 和 `MEMORY_CALLS_PER_DAY=0` 即可分别关闭。
- **`tools/` 中的脚本**各不相同，有的免费，有的调用模型。[tools.zh-CN.md](tools.zh-CN.md) 的表格中逐一注明。
- **`personagent eval`** 对每个用例都调用模型，`memory` 测试集除外：它以预设的回答离线运行。人设和学习两套用例还需要第二个模型进行评判（`BENCH_JUDGE_MODEL`）。
- **记忆。** 带命名空间（非 QQ）的会话超过 256 个时，最久未活动的空闲会话会从内存中移除，并失去待处理的反应。移除前会先整理其尚未整理的消息；除非设置 `MEMORY_KEEP_RECENT=false`，其近期消息会在 `runtime/recent.json` 中保留 72 小时。事实、事件、核心笔记和学习记录会保留。正在处理请求的会话不会被清除。长期记忆在启动时从磁盘加载，不受此上限限制。
- **磁盘。** `runtime/` 中的证据日志和候选学习记录只追加，从不截断。任何一个超过 50 MB 时，`personagent doctor` 会标记（`LEDGER_EVIDENCE_WARN_BYTES`、`LEDGER_CANDIDATES_WARN_BYTES`）。记忆文件始终较小：`recent.json` 只保存最近 72 小时内活跃的聊天，`memory_trash.jsonl` 中被移除的内容最多保留 30 天。每天第一次修改之前，`memory.json`、`core_memory.json` 和 `episodes.json` 会复制为同名的 `.bak` 文件；本版本首次启动时，会将旧的记忆文件保留为 `memory.json.pre-v2`。使用「清除此聊天的记忆」或在聊天中要求忘记之后，`.bak` 副本会按当前文件重新写入，`memory.json.pre-v2` 也会删去被忘记的内容，因此 `runtime/` 中不会留下任何副本；但此前制作的备份仍然保留这些内容。请备份 `runtime/`，因为机器人学到和记住的全部内容都保存在其中。

### 完整排查清单

本节是[机器人不发言](#机器人不发言)的完整版，最常见的原因排在前面。本地页面运行角色服务时，[动态](guide.zh-CN.md#动态)会显示消息是否到达，以及角色未发言的原因。在服务器上，请查看服务日志，学到的内容请用 `personagent learned` 查看，记住的内容请用 `personagent memory` 查看。

1. **消息未送达。** 在本地页面确认平台显示为已连接，并查看 `runtime/desktop/direct.log` 或 `astrbot.log`。QQ 官方机器人必须已在群中，QQ 决定其能接收哪些群消息。个人微信机器人无法接收群消息。在你运行的 AstrBot 中，请填写插件的 `groups`（私聊填写 `dm_users`），使用 NapCat 时还须将 `aiocqhttp` 从 `excluded_platforms` 中移除。Satori 和 Matrix 连接器在各自的 `.env` 中有独立的白名单，详见其 README。这种情况下，聊天不会出现在「动态」中。
2. **角色服务未开启。** `personagent run` 的启动信息显示 `agent: OFF`，并给出原因和解决办法。没有 `LLM_API_KEY` 时，请在本地页面添加 key（或设置 `LLM_API_KEY`）并重启。`AGENT_ENABLED=false` 时，请在 `<home>/.env` 中改为 `true` 并重启。在此之前，每个事件都返回 `owned: false`，第一个事件会记录一行内容相同的 ERROR。
3. **AstrBot 自带的模型代为回答。** 插件已回退，原因是请求失败、personagent 拒绝了该消息（第 5 项），或角色服务未开启（第 2 项）。AstrBot 的日志显示 `refusing unsafe personagent_url`、`agent refused the request (403): <message>`（或其他状态，见下表）或 `timed out waiting for the agent`。`timeout_s` 必须覆盖防抖和回合内的模型调用，还须计入消息到达时仍在思考的回合。不论群聊还是私聊，一个回合的所有模型调用共用 1.5 × `LLM_TIMEOUT_S`，因此应使 3 × `LLM_TIMEOUT_S` 低于该值。其默认值（420）覆盖角色服务的默认值（3 × 120 = 360 秒）。调大 `LLM_TIMEOUT_S` 时也须相应调大该值。
4. **未点名角色。** 在群中，角色回应其名字（`PERSONA_NAME`）或 @。其他情况下，须待消息累计达到 `CHAT_TRIGGER_COUNT` 条（默认 30 条）后才会考虑插话，且仍可能不发言。在角色所在时区的 02:00 到 07:00，角色大多不参与未点名的聊天。时区由 `PERSONA_TZ_OFFSET_HOURS` 设定。留空时，`AGENT_LANG` 为 `zh` 或 `zh-TW` 按 UTC+8，其他语言按本机时区。personagent 启动后，在某个平台的第一条消息到达起两分钟内，距发送时已超过 10 分钟才到达的群聊消息视为积压消息：只作为上下文保留，不予回复，服务日志会予以记录。「动态」显示最近每个回合的原因。如需离线观察同样的判断，请运行 `personagent chat --trigger 4`。
5. **personagent 自身的白名单。** `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 在每条路径上都生效，不带前缀 ID 的 QQ 私聊还需要是管理员或有条目。被其拦截的消息不会被接管，因此经 AstrBot 时，AstrBot 自带的模型可能会回答。personagent 对每个被拒绝的会话以 INFO 记录一次，并写明拒绝它的设置。
6. **模型调用失败。** key 被拒（401 或 403）或余额耗尽（402 或配额用完）时，会记录一行 ERROR，注明服务商主机和需要修改的设置。运行 `personagent doctor`，该命令会向每个模型接口发送一个很小的请求并显示状态，也能查出错误的 `LLM_BASE_URL` 或 `LLM_MODEL`。主模型超时或连接中断、且 `LLM_FALLBACK_MODEL` 指定了不同的模型时，本次调用会立即改用备用模型，因此本回合仍能在时限内作答。服务方在正常响应中返回的错误（如 OpenRouter 的上游故障）按相应的 HTTP 错误处理。模型不可用期间，被点名时角色会发送一句符合人设的简短致歉，每个会话每五分钟最多一次；「动态」中会将这一回合标为「模型未作出回应」。
7. **设置名拼写错误。** 启动日志和 `personagent doctor` 会列出 `.env.example` 中不存在的所有键，以及任何以 `#` 开头的值。
8. **`.env` 带有 BOM。** 第一个设置的名称带有 BOM，无法传入进程。启动和 `personagent doctor` 都会报告此问题。请将文件重新保存为不带 BOM 的 UTF-8。
9. **使用 NapCat 时 `QQ_BOT_ID` 未设置或有误。** 经 AstrBot 时 @ 仍然有效，但补收遗漏的 @ 须依靠该设置进行匹配。在 OneBot 直连入口上，@ 永远不会被识别：机器人正常启动，不记录任何内容，也从不回应。`QQ_BOT_ID` 为空而设置了其他 QQ 设置时，`personagent doctor` 会警告。QQ 官方机器人不使用该设置。
10. **可以回答，但遗忘了学过的内容。** 原因可能是 NapCat 的 QQ 消息到达时没有 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`，或者 `PERSONA_NAME` 或 `PERSONA_VERSION` 发生了变化，后者会开始一个新角色。旧角色已生效的内容被整体拒绝时，日志会警告。修改 `persona.txt`（包括在页面的「人设」框中修改）不会开始新角色。同一 `PERSONA_VERSION` 下的修订共享学习范围（`runtime/persona_lineage.json`）。要并入在谱系未列出的人设哈希下学到的行，运行 `personagent learned lineage adopt <hash>`，再运行 `personagent learned rebuild`。哈希位于 `personagent learned show <id>` 显示的候选范围中。在中文和其他语言之间切换 `AGENT_LANG`，也会切换到 `runtime/` 中另一组学习文件。

以下列出 `/v1/events` 的错误。AstrBot 插件会记录消息，`code` 是客户端可据以分支处理的稳定字段。

| 状态 | `code` | AstrBot 日志中的消息 | 原因 |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | 没有 `CONNECTOR_TOKEN`，且调用方不在本机 |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | 没有 `CONNECTOR_TOKEN`，请求来自浏览器、代理或其他主机名 |
| 403 | `invalid_envelope` | invalid request envelope: … | token、请求头或签名缺失或错误，时钟相差超过 5 分钟，nonce 重复，或防重放已满（角色服务日志中有 `connector replay guard full`） |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` 与当前时间相差超过 `CONNECTOR_MAX_EVENT_AGE_S`（24 小时），包括未来或毫秒时间戳 |
| 400 | `invalid_schema` | invalid event schema: … | 缺少必填字段：`platform`、`conversation_type`、`sender_id`、`message_id`、`sent_at`，群聊还有 `conversation_id` |
| 400 | `client_disconnected` | client disconnected | 调用方在发送时断开 |
| 408 | `body_timeout` | request body not received in time | 请求体超过 30 秒才到达 |
| 413 | `body_too_large` | request body too large | 超过 `SERVER_MAX_BODY_BYTES`（8 MB），通常是内嵌图片 |
| 429 | `capacity_exceeded` | webhook capacity exceeded | 进行中的回合超过 `CONNECTOR_MAX_INFLIGHT`；3 秒后重试 |

### 旧方式：OneBot 直连入口

NapCat 的 webhook 仍然可以将事件发送到 `POST /v1/onebot`，personagent 经 `QQ_ONEBOT_URL` 回复。此路线已弃用，在 1.x 中保留。请改用 QQ 官方机器人连接，或经 AstrBot 使用 NapCat 并设置 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。此路线在首次使用时会警告一次，并在每个响应中标记 `Deprecation: true`。

如需迁移到经 AstrBot 的 NapCat，请在本地页面添加 OneBot v11（NapCat），或者为你自己的 AstrBot 运行 `personagent connect astrbot <AstrBot data dir> --qq` 并填写白名单。让 NapCat 的 WebSocket 客户端指向该地址，并关闭 NapCat 的 HTTP 客户端（保留 HTTP 服务）。记忆和学习内容会延续，因为 `CONNECTOR_QQ_PLATFORMS` 保持 ID 不变。

如果仍在使用旧路线：

- 按 [NapCat 文档](https://napneko.github.io/)配置两个方向。你需要一个位于 `QQ_ONEBOT_URL` 的 **HTTP 服务**用于发送，以及一个向 `http://127.0.0.1:8080/v1/onebot`（`SERVER_HOST`、`SERVER_PORT`）发送的 **HTTP 客户端**。`QQ_ONEBOT_URL` 默认为空，因此须写入 `.env`，否则机器人只接收不回复。此路线看起来已配置（设置了 `QQ_BOT_ID` 或 `QQ_ONEBOT_SECRET`，`CONNECTOR_QQ_PLATFORMS` 为空）而 `QQ_ONEBOT_URL` 为空时，启动检查和 `personagent doctor` 会警告。
- NapCat 位于另一台机器上时，请将 `QQ_ONEBOT_SECRET` 设为 HTTP 客户端的 `secret`。否则任何能访问该端口的人都能伪造事件。请求体必须带 `x-signature: sha1=<hex>`（否则 403 `bad_signature`），时间戳偏差超过五分钟的事件返回 403 `stale_event`。没有该密钥时，此路线只回应本机程序，在网络绑定下是关闭的（403 `onebot_disabled`）。
- 同一账号上还运行 AstrBot 时，请将 `aiocqhttp` 保留在 `excluded_platforms` 中，否则每条消息都会收到两次。

使用 `curl http://127.0.0.1:3000/get_login_info` 检查发送。向机器人发送群消息，同时观察 personagent 的日志，以检查接收。

## 其他文档

- [AstrBot 插件说明](../integrations/astrbot/astrbot_plugin_personagent/README.zh-CN.md)
- [免责声明](DISCLAIMER.zh-CN.md)
