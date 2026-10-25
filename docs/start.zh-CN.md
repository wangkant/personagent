# 开始使用 personagent

[English](start.md) · [完整手册](guide.zh-CN.md)

## 打开应用

从 PyPI 安装后打开：

```sh
python -m pip install personagent
personagent
```

装了 [uv](https://docs.astral.sh/uv/) 的话，`uvx personagent` 无需单独安装即可运行。

也可以让 AI 编程助手代劳：让它读 [setup-for-agents.md](setup-for-agents.md)，然后帮你把 personagent 装好并设置好。

在 Windows 上也可以下载源码 ZIP，解压后双击 `start.bat`。它会在文件夹里建好自己的 Python 环境，再打开同一个本地页面。

从 Git 仓库运行时，请为它单独建一个虚拟环境：先运行 `python -m venv .venv`，再运行 `.venv/bin/python -m pip install -e .` 和 `.venv/bin/python -m persona_agent`。Windows 上的解释器是 `.venv\Scripts\python.exe`，也可以直接双击 `start.bat`。

## 填 Key，开始聊天

选择模型服务，填入 API 密钥，点「验证并开始聊天」。默认选中的是 DeepSeek 和温柔倾听者这个角色。模型名称和接口地址在「更多设置」里，角色的名字和性格在「给角色换个名字或性格」里。

密钥只保存在本机。聊天消息会发送给你选择的模型服务，验证密钥和聊天都可能产生该服务的正常费用。需要核对密钥时可以点「显示」。密钥不会出现在状态响应里，也不会写进浏览器存储。

角色直接在页面里回复。设置会保存下来，下次打开就直接进入聊天。

设置完成后，「角色与设置」里有一个「人设」框，内容就是角色当前使用的人设。改写它是谁、怎么说话，然后点「保存人设」，修改立即生效，角色学到的东西也会保留。

再往下是「更多功能」，可以打开联网搜索、看懂图片和偶尔主动说话。联网搜索默认使用 DuckDuckGo，填入 Tavily 的密钥会更稳定。连接第一个平台之前，「开始聊天」页面上方会显示一条「开始使用」提示。

## 带到其他平台

1. 点「连接平台」，选择一个平台。连接后，角色会回复这个平台上的群聊和私聊。
   - **扫码就能连**：QQ 和个人微信。点「获取二维码」，然后在手机上确认。
     - QQ：用手机 QQ 扫码。QQ 会新建一个机器人，或让你选一个已有的，密钥由 personagent 自动取回。如果机器人是你自己在 [QQ 官方页面](https://q.qq.com/qqbot/openclaw/login.html)创建的，点「改为手动填写」，填入 AppID 和 AppSecret。
     - 微信：用微信扫码。微信不会把群消息转给这类机器人，所以它只能私聊。
   - **粘贴一两项**：Telegram（向 @BotFather 申请 Token）、Discord（机器人 Token，并打开 Message Content Intent）、KOOK、飞书、钉钉、Slack、企业微信智能机器人、Mattermost 和 Misskey。页面会写明要从平台后台复制哪几项，其余设置都用默认值。
   - **高级**：企业微信应用、微信公众号和 QQ（Webhook）需要一个能转发到回调端口的公网地址；OneBot v11（NapCat）和 Satori 需要在本机另外运行相应的软件。
2. QQ、微信、Telegram 和 Discord 由 personagent 直接连接。其他平台通过第三方桥接程序 AstrBot 接入。第一次连接这类平台时，personagent 会下载 AstrBot 和一个独立的 Python 3.12 运行环境，下载完成前请保持页面打开。之后 AstrBot 在后台运行，没有需要另外登录的管理后台。
3. 保存之前，personagent 会先向平台核验凭据。平台拒绝时，页面会给出提示，不保存任何内容。
4. 已连接的平台列在「连接平台」页面顶部，可以在那里重新设置或断开。

QQ 机器人连好后，在手机 QQ 的「联系人 → 机器人」里找到它，可以私聊，也可以把它加到你担任群主的群里。这条路线使用 QQ 官方机器人平台，不需要个人 QQ 小号，也不需要安装其他软件。机器人能进哪些群由 QQ 决定：通过认证之前，它只能加入管理员担任群主的群，也不需要配置沙箱。在群里它默认只收到 @ 它的消息，群主可以在这个群里机器人的资料页打开「接收全量消息」。认证和其他账号方面的事项见 [QQ 机器人官方指南](https://bot.q.qq.com/wiki/bot_new_product-intro/)。

二维码过期后可以重新获取；下载失败可以重试，不必重新填写模型设置。连接某个平台时，只会对这个平台的群聊和私聊放行，其他适配器仍沿用原有的群和私聊限制。目前不提供 LINE，因为 AstrBot 只能通过它的管理后台接收 LINE 回调，而 personagent 不运行这个后台。

## 下次使用

再次打开 personagent 即可。配置会保留，已连接的平台会自动恢复。如果它已经在运行，再次打开会复用当前页面。使用期间请保持启动窗口打开。无论是点「退出」还是关闭窗口，它启动的进程都会一起结束；意外崩溃后残留的进程会在下次启动时清理。

PyPI 上有新版本时，「开始聊天」页面会显示一条提示，给出更新内容的链接和与当前安装方式对应的更新命令；解压源码 ZIP 运行的，提示会让你到发布页下载新版源码。personagent 每天最多向 pypi.org 查询一次，请求中只包含它的版本号。在 `.env` 中设置 `UPDATE_CHECK_ENABLED=false` 可以关闭这项检查。

习惯命令行的用户可以使用 `personagent start --terminal`、`personagent init --terminal`、`personagent up`，以及 `chat`、`demo`（不需要密钥）、`run` 和 `connect` 命令。这些命令会保留已有的 `.env`、修改过的人设和学到的记忆。其他平台的接入方法见[完整手册](guide.zh-CN.md)。
