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

密钥保存在本机。消息会发送给你选择的模型服务；验证和聊天可能产生该服务正常收取的费用。需要核对时可点「显示」，密钥不会写进浏览器存储或普通状态响应。

角色会直接在页面回复。设置会保存，下次打开就能继续使用。

## 想放进 QQ，再扫码

1. 点「连接 QQ」。页面会说明：角色将回复这个官方机器人收到的群聊和私聊。
2. 程序按需下载 AstrBot 和独立的 Python 3.12，保持页面打开即可。
3. 用手机 QQ 扫页面里的二维码，确认创建或绑定机器人。程序会自动保存凭据，并一起启动角色服务和聊天平台。
4. 到手机 QQ「联系人 → 机器人」里找到它，开始私聊，或添加到你管理的群。

这条路线使用 QQ 官方机器人，无需 NapCat，也不用准备个人 QQ 小号。能加哪些群、能获取哪些消息，由 QQ 控制；目前加进群聊需要你是群主。账号侧的操作见 [AstrBot 官方 QQ 接入说明](https://github.com/AstrBotDevs/AstrBot/wiki/zh-platform-qqofficial-websockets)。

二维码过期可以重新获取，下载失败可以点重试，不用重新填写模型设置。自动放行只针对 QQ 官方机器人这个平台，其他适配器仍沿用已有的群和私聊限制。

## 下次使用

再次打开 personagent 即可：配置会保留，已经连接的 QQ 机器人会自动恢复服务。重复打开会复用正在运行的页面。点「退出」会关闭应用，并停止由它启动的进程；使用期间保持启动窗口打开。

熟悉命令行的用户仍可使用 `personagent start --terminal`、`personagent init --terminal`、`personagent up` 和原有的 `chat`、`run`、`connect` 命令。已有 `.env`、自行修改的人设和学习记忆会保留。其他平台的用法见[完整手册](guide.zh-CN.md)。
