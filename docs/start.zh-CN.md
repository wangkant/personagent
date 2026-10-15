# 开始使用 personagent

[English](start.md) · [完整手册](guide.zh-CN.md)

## 打开应用

当前分支是 1.1 开发预览版，用下面两条命令安装当前源码：

```sh
python -m pip install https://github.com/wangkant/personagent/archive/refs/heads/main.zip
python -m persona_agent
```

Windows 也可以下载源码 ZIP，解压后双击 `start.bat`。程序会准备独立环境并打开同一个本地页面。从 Git 仓库运行则用 `python quickstart.py`。

## 填 Key，开始聊天

选择模型服务，填入 API Key，点「验证并开始聊天」。初始默认是 DeepSeek 和一个温柔倾听者；模型名、接口地址、角色名字和性格都放在可选设置里。

设置好之后，「角色与设置」下面还有一个「人设」框，里面是角色正在用的人设。直接改写它是谁、怎么说话，点「保存人设」就马上生效，它学到的东西会保留。

密钥保存在本机。消息会发送给你选择的模型服务；验证和聊天可能产生该服务正常收取的费用。需要核对时可点「显示」，密钥不会写进浏览器存储或普通状态响应。

角色会直接在页面回复。设置会保存，下次打开就能继续使用。

## 带到其他平台

1. 点「连接平台」，选一个平台。连接后，角色会回复这个平台上的群聊和私聊。
   - **扫码就能连**：个人微信。点「获取二维码」，用微信扫码确认。它只能私聊，微信不会把群消息交给这类机器人。
   - **粘贴一两项**：QQ、Telegram、Discord、KOOK、飞书、钉钉、Slack、企业微信智能机器人、Mattermost、Misskey。页面写明要去平台后台复制哪一项，其余设置都用默认值。QQ 先在 [QQ 官方页面](https://q.qq.com/qqbot/openclaw/login.html)扫码创建机器人，再复制 AppID 和 AppSecret。
   - **高级**：企业微信应用、微信公众号、QQ（Webhook）需要能转发到回调端口的公网地址；OneBot v11（NapCat）和 Satori 需要本机另外运行的软件。
2. QQ、微信、Telegram、Discord 由 personagent 直接连接。其他平台第一次连接时，程序会下载 AstrBot 和独立的 Python 3.12，保持页面打开即可；AstrBot 在后台运行，没有另一个后台要登录。
3. 程序保存凭据，启动角色服务和聊天平台，并等几秒确认平台接受了连接。平台拒绝的话，页面会提示，什么都不保存。
4. 连好的平台列在页面上方，可以重新设置或断开。

QQ 连好后，到手机 QQ「联系人 → 机器人」里找到它，开始私聊，或添加到你管理的群。这条路线使用 QQ 官方机器人，无需 NapCat，也不用准备个人 QQ 小号。能去哪些群由 QQ 决定：没认证的机器人只给管理员自己用，只能进管理员当群主的群，不用再配置沙箱；它默认只收到 @ 它的消息，群主可以在这个群里机器人的资料页打开「接收全量消息」。认证和其他账号侧的事见 [QQ 机器人官方指南](https://bot.q.qq.com/wiki/bot_new_product-intro/)。

二维码过期可以重新获取，下载失败可以点重试，不用重新填写模型设置。自动放行只针对你连接的那个平台，其他适配器仍沿用已有的群和私聊限制。LINE 暂不提供，因为 AstrBot 只能经它的网页后台接收 LINE 的回调。

## 下次使用

再次打开 personagent 即可：配置会保留，已经连接的平台会自动恢复服务。重复打开会复用正在运行的页面。点「退出」会关闭应用，并停止由它启动的进程；使用期间保持启动窗口打开。

熟悉命令行的用户仍可使用 `personagent start --terminal`、`personagent init --terminal`、`personagent up` 和原有的 `chat`、`run`、`connect` 命令。已有 `.env`、自行修改的人设和学习记忆会保留。其他平台的用法见[完整手册](guide.zh-CN.md)。
