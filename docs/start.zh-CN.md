# 开始使用 personagent

[English](start.md) · 简体中文 · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · [Français](start.fr.md) · [Deutsch](start.de.md) · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · [完整手册](guide.zh-CN.md)

## 打开 personagent

从 PyPI 安装后打开：

```sh
python -m pip install personagent
personagent
```

如已安装 [uv](https://docs.astral.sh/uv/)，可直接运行 `uvx personagent`，无需单独安装。

在 Windows 上，页面在独立窗口中打开。在 macOS 和 Linux 上，页面在浏览器中打开；运行 `pip install "personagent[app]"` 后也可在独立窗口中打开。

也可以交由 AI 编程助手完成：请其阅读 [setup-for-agents.md](setup-for-agents.md)，然后代为安装并设置 personagent。

在 Windows 上也可以下载源码 ZIP，解压后双击 `start.bat`。该脚本会在文件夹中建立独立的 Python 环境，然后打开同一个本地页面。首次运行时，还会在桌面和开始菜单中添加 personagent 图标。

从 Git 仓库运行时，请为其单独创建一个虚拟环境：先运行 `python -m venv .venv`，再运行 `.venv/bin/python -m pip install -e .` 和 `.venv/bin/python -m persona_agent`。Windows 上的解释器是 `.venv\Scripts\python.exe`，也可以直接双击 `start.bat`。

## 填写 Key 并开始聊天

选择模型服务，填写 API 密钥，然后点击「验证并开始聊天」。默认选中的是 OpenRouter 的免费模型和「温和的倾听者」角色。该密钥本身不收费，每天限 50 次请求。模型名称和接口地址在「高级设置」中，角色的名称和性格在「更改角色名称或性格」中。

密钥仅保存在本机，点击「显示」即可核对。聊天消息会发送给你选择的模型服务，按该服务的正常价格计费。

角色直接在页面中回复。设置将被保存，下次打开时直接进入聊天。

设置完成后，「角色与设置」中有一个「人设」框，其内容即角色当前使用的人设。修改角色的身份和说话方式后，点击「保存人设」，修改立即生效，角色已学到的内容也将保留。

其下方是「更多功能」，可开启联网搜索、识别图片和偶尔主动发言。联网搜索默认使用 DuckDuckGo，填写 Tavily 密钥可获得更稳定的结果。其下方的「高级设置」汇集了以前只能在 `.env` 中修改的设置。连接第一个平台之前，「开始聊天」页面上方会显示一条「开始使用」提示。

另有两个视图无需连接平台即可使用。「演练」播放预设脚本的演示，并提供一个模拟群聊，可查看角色回复或保持沉默的原因。「应用」执行运行检查，逐项检查角色所依赖的服务，显示运行日志，并提供版本更新、备份和桌面图标等功能。

## 接入其他平台

1. 点击「连接平台」，选择一个平台。连接后，角色将回复此平台上的群聊和私聊。
   - **扫码连接**：QQ 和个人微信。点击「获取二维码」，然后在手机上确认。
     - QQ：使用手机 QQ 扫码。QQ 会新建一个机器人，或由你选用一个已有的机器人，密钥由 personagent 自动获取。如果机器人是你自行在 [QQ 官方页面](https://q.qq.com/qqbot/openclaw/login.html)创建的，请点击「改为手动填写」，并填写 AppID 和 AppSecret。
     - 微信：使用微信扫码。微信不会向此类机器人转发群消息，因此仅支持私聊。
   - **填写一至两项**：Telegram（向 @BotFather 申请 Token）、Discord（机器人 Token，并开启 Message Content Intent）、KOOK、飞书、钉钉、Slack、企业微信智能机器人、Mattermost、Misskey、Matrix、Twitch、IRC、Zulip、VK 和 Stoat。页面会说明需要从平台后台复制哪几项，其余设置均使用默认值。Twitch 还需要通过一个链接批准登录。
   - **高级**：企业微信应用、微信公众号和 QQ（Webhook）需要一个能转发到回调端口的公网地址；OneBot v11（NapCat）和 Satori 需要在本机另外运行相应的软件。
2. QQ、微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 由 personagent 直接连接。其他平台通过第三方桥接程序 AstrBot 接入。首次连接此类平台时，personagent 会下载 AstrBot 和一个独立的 Python 3.12 运行环境，下载完成前请保持页面打开。此后 AstrBot 在后台运行，无需另外登录管理后台。
3. 保存之前，personagent 会先向平台核验凭据。平台拒绝时，页面会显示提示，且不保存任何内容。
4. 已连接的平台列于「连接平台」视图顶部，可在该处重新设置或断开连接。

QQ 机器人连接后，可在手机 QQ 的「联系人 → 机器人」中找到它，既可以私聊，也可以将其添加到你担任群主的群中。此方式使用 QQ 官方机器人平台，无需个人 QQ 小号，也无需安装其他软件。机器人可加入哪些群由 QQ 决定：通过认证之前，它只能加入管理员担任群主的群，且无需配置沙箱。在群中，机器人默认只接收 @ 它的消息，群主可在该群中机器人的资料页开启「接收全量消息」。认证及其他账号相关事项请参阅 [QQ 机器人官方指南](https://bot.q.qq.com/wiki/bot_new_product-intro/)。

二维码过期后可重新获取；下载失败时可重试，无需重新填写模型设置。连接某个平台时，仅对该平台的群聊和私聊放行，其他适配器仍沿用原有的群聊和私聊限制。目前不支持 LINE，因为 AstrBot 只能通过其管理后台接收 LINE 回调，而 personagent 不运行该后台。

## 下次使用

再次打开 personagent 即可。配置将保留，已连接的平台会自动恢复。如果 personagent 已在运行，再次打开会将其窗口切换到前台。使用期间请保持其运行：无论是点击「退出」还是关闭窗口，由其启动的进程都会一并结束；意外崩溃后残留的进程会在下次启动时清理。在 Windows 上，`personagent shortcut` 会在桌面和开始菜单中添加图标，点击即可打开，无需使用终端。同样在 Windows 上，启用「应用」视图中的「后台运行」后，关闭窗口时 personagent 将继续在通知区域图标中运行，角色照常回复消息。

PyPI 上发布新版本时，「开始聊天」视图会显示提示，提供更新说明的链接以及与当前安装方式对应的更新命令；如通过解压源码 ZIP 运行，提示会引导你前往发布页下载新版本源码。对于大多数安装方式，「应用」视图中的「更新并重新打开」可直接完成更新。personagent 每天最多向 pypi.org 查询一次，请求中仅包含其版本号。在 `.env` 中设置 `UPDATE_CHECK_ENABLED=false` 即可关闭此项检查。

习惯使用命令行的用户可以使用 `personagent start --terminal`、`personagent init --terminal`、`personagent up`，以及 `chat`、`demo`（不需要密钥）、`run` 和 `connect` 命令。这些命令会保留现有的 `.env`、修改过的人设和已学到的记忆。其他平台的接入方法请参阅[完整手册](guide.zh-CN.md)。
