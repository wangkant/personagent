# 从零部署：让机器人在 QQ 群里说话

[English](deploy.md) · **简体中文**

这篇是写给 Windows 上的 QQ 用户的，按顺序做完，就能让一个机器人小号在你的 QQ 群里开口。需要三个程序一起运行：

```text
QQ 群  ⇄  NapCat（登录 QQ）  ⇄  AstrBot（装着 personagent 插件）  ⇄  personagent  ⇄  AI 模型
```

personagent 自己不登录 QQ。NapCat 负责登录，AstrBot 负责转发，personagent 负责决定说不说、说什么。

每一步都写了「你应该看到」，对不上就先别往下走，直接翻到最后的[机器人不说话](#机器人不说话)。

## 开始之前

- 一个 Windows 10 或 11 的电脑，能一直开着（关机或关掉窗口，机器人就停了）。
- **一个专门给机器人用的 QQ 小号**，并且已经加进目标群。不要用你自己的主号：NapCat 不是腾讯官方的客户端，号有被限制甚至封禁的风险。详见 [DISCLAIMER.zh-CN.md](../DISCLAIMER.zh-CN.md)。
- 一个 AI 服务的 API key。DeepSeek、硅基流动、阿里云百炼、智谱、Kimi、火山方舟都可以，注册后在它们的控制台里创建。
- 一部登录着小号的手机，用来扫码。

## 第一部分：装 personagent

**1. 装 uv。** uv 是装 Python 程序的工具，它会自己下载合适的 Python。打开 PowerShell，运行：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

关掉 PowerShell 再重新打开，运行 `uv --version`。你应该看到一行版本号。

**2. 装 personagent。**

```powershell
uv tool install personagent
personagent --version
```

你应该看到 `personagent 1.0.0`。如果提示找不到命令，运行 `uv tool update-shell`，再重开一次 PowerShell。

**3. 做第一次设置。**

```powershell
personagent init
```

它会先问语言（中文系统默认中文），然后依次问：用哪家 AI 服务、模型名、API key（输入时屏幕上不显示，这是正常的）、机器人的名字、选一个性格。输完 key 它会立刻发一个很小的请求测试，你应该看到「可以用。」。如果失败，它会告诉你访问了哪个地址、HTTP 状态码和可能的原因，然后让你重试。

到「现在连接 AstrBot 吗？」这一步先选**否**（直接回车），最后选择在终端里聊几句。你应该看到机器人用你选的性格回话。

> 想把数据放在别的盘：每条命令前加 `--home`，例如 `personagent --home D:\personagent init`，之后的 `chat`、`connect`、`run` 都要带上同样的 `--home`。不加的话，数据放在 `C:\Users\你的用户名\personagent`。

在终端里它是怎么判断「该说还是该安静」的，可以先运行 `personagent demo --lang zh` 看一遍（不需要 key，一分钟）。

## 第二部分：装 AstrBot

AstrBot 有两种装法，选一种。

### 方法 A：启动器（点安装包）

1. 打开 [AstrBotDevs/astrbot-launcher 的 Releases](https://github.com/AstrBotDevs/astrbot-launcher/releases)，下载 `AstrBot.Launcher_x64-setup.exe`（ARM 电脑下 `arm64` 版）。
2. 运行安装包，装好后打开启动器，按它的界面创建并启动一个 AstrBot。

### 方法 B：uv 命令行

```powershell
uv tool install astrbot --python 3.12
mkdir D:\astrbot
cd D:\astrbot
astrbot init
astrbot run
```

`astrbot init` 只在第一次运行。**以后每次都要在 `D:\astrbot` 这个文件夹里运行 `astrbot run`**，它的数据就放在这个文件夹的 `data` 里。

### 确认 AstrBot 跑起来了

你应该在日志里看到 `管理面板已启动，可访问`，后面跟着几个链接。浏览器打开其中的 `http://localhost:6185`：

- 用户名 `astrbot`，密码是日志里打印的随机初始密码（只有第一次启动才有）。
- 登录后马上去改密码。

AstrBot 第一次启动时会生成 `data` 文件夹，里面有 `cmd_config.json`、`plugins`、`config`。**后面要用到这个 `data` 文件夹。**不确定它在哪的话，在文件资源管理器里搜 `cmd_config.json`。

> AstrBot 的界面和命令以[它的官方文档](https://docs.astrbot.app)为准，版本更新后可能有出入。

## 第三部分：装 NapCat，登录小号

1. 打开 [NapCatQQ 的 Releases](https://github.com/NapNeko/NapCatQQ/releases)，下载 Windows 一键包 `NapCat.Shell.Windows.OneKey.zip`，解压到一个固定的文件夹。
2. 运行里面的 `NapCatInstaller.exe`，等它自动配置完。然后进入生成的 `NapCat.XXXX.Shell` 文件夹，按 [NapCat 文档](https://napneko.github.io/guide/boot/Shell)的说明启动（一键包是运行 `napcat.bat`）。
3. 启动后窗口里会打印一行 `WebUi User Panel Url: http://127.0.0.1:6099/webui?token=...`。在浏览器里打开它。
4. 在网页里选择扫码登录，用手机上的**小号**扫码确认。

你应该看到 NapCat 的网页上显示小号已登录。

先不要配「网络配置」，等 AstrBot 那边准备好。

## 第四部分：让 AstrBot 和 NapCat 连起来

**1. 在 AstrBot 里添加 QQ。** 打开 AstrBot 的网页（`http://localhost:6185`）：

1. 点左边栏的「机器人」，再点「创建机器人」。
2. 协议选「OneBot v11」。
3. 填写：ID 随便起（比如 `napcat`）；勾选「启用」；「反向 WebSocket 主机地址」填 `0.0.0.0`；「反向 WebSocket 端口」保持默认的 `6199`；「反向 Websocket Token」留空。
4. 保存。

**2. 在 NapCat 里指向 AstrBot。** 回到 NapCat 的网页：

1. 点「网络配置」，再点「新建」，选「WebSockets 客户端」。
2. 勾选「启用」。
3. 「URL」填 `ws://127.0.0.1:6199/ws`。
4. 「心跳间隔」和「重连间隔」都建议改成 `1000`（毫秒）。
5. 保存。

你应该看到：在 AstrBot 网页的「数据与日志」→「日志」里出现蓝色的 `aiocqhttp(OneBot v11) 适配器已连接`。

如果几秒后日志里变成适配器已关闭，说明连接超时：检查地址和端口有没有写错、AstrBot 有没有在运行、防火墙有没有拦住 6199 端口。

> AstrBot 在 Docker 里的话，`127.0.0.1` 指的是容器自己，地址要换成对应的主机地址，见本文最后的[用 Docker 的话](#用-docker-的话)。

## 第五部分：把 personagent 接上 AstrBot

回到 PowerShell：

```powershell
personagent connect astrbot
```

它会问下面几个问题，每个问题后面都有说明，直接回车就是用方括号里的默认值：

1. **AstrBot 文件夹**：它会自己找，找到就直接回车；找不到就填第二部分里说的那个 `data` 文件夹（或者它的上一级）。这个文件夹里必须有 `cmd_config.json`，没有说明 AstrBot 还没启动过。
2. **AstrBot 是在 Docker 里运行的吗？** 按实际情况选。
3. **机器人要进哪个聊天平台？** 选 `1. QQ（通过 NapCat）`。
4. **机器人自己的 QQ 号**：小号的 QQ 号。
5. **要加入的 QQ 群号**：多个用逗号隔开。群号在群资料里看。
6. **你自己的 QQ 号**：你的主号，就是管理员。机器人和管理员最熟，管理员随时可以私聊它，也可以管理它记住的内容。不想设就回车。
7. **机器人怎么称呼你**。
8. **还允许谁私聊机器人**：填 QQ 号，逗号隔开；暂时没有就回车。

你应该看到 `AstrBot 插件已安装` 和 `插件设置已写入`，最后它会打印接下来要做的事。这一步做了三件事：把插件复制进 AstrBot 的 `plugins` 文件夹，在 personagent 的 `.env` 和插件配置里写进同一个 `CONNECTOR_TOKEN`（两边用它互相确认身份），并把你填的群号写进两边的白名单。

然后**重启 AstrBot**（关掉再开；或者在 AstrBot 网页的插件页重载插件），让它加载插件。你应该在插件页看到 `astrbot_plugin_personagent`，它的设置里 `groups` 是你刚才填的群号。

## 第六部分：启动并测试

**1. 启动 personagent，并一直开着。**

```powershell
personagent run
```

你应该看到类似这样的几行：

```text
personagent 1.0.0
  listening:  http://127.0.0.1:8080
  home:       C:\Users\你的用户名\personagent
  dashboard:  http://127.0.0.1:8080/
  agent:      on (model deepseek-flash, lang zh)
```

如果最后一行是 `agent: OFF`，后面会写原因，多半是没填 API key：重新运行 `personagent init`。

如果它一句话就退出了，也会写原因：同一个文件夹里已经有一个 personagent 在跑、`8080` 端口被占用等等。按它说的处理。

**2. 在群里测试。** 用你的主号（或别的号）在目标群里发一句 `小夏，你好`（换成机器人的名字）。你应该在几秒到十几秒内看到小号回复。

**3. 打开控制面板。** 浏览器打开 `http://127.0.0.1:8080/`。你应该看到服务在运行、连接器一栏有记录、群里刚才那条消息的「说话原因」。面板只有这台电脑能打开，里面不会显示密钥。

现在你有三个窗口要一直开着：NapCat、AstrBot、personagent。

## 它怎么学习

机器人不会因为一句话就变样。一个改变要同时满足：同一个聊天里有两次一致的反应，并且其中至少一次够「强」，也就是**被回复的那个人用自己的话纠正它，或者接受了它的第二次回答**。一声哈哈、旁观者的纠正、陌生人的指令、有人直接换了话题，都不算。所以默认情况下，一个人只能教它怎么回答他自己，并且只在他自己的那个聊天里。

学到的所有东西都记在只追加的账本里，随时可以撤销：

- 在控制面板里，每一条学到的东西后面有「采纳」「拒绝」「撤回」按钮（点两下确认）。
- 或者用命令：`personagent learned list`、`personagent learned show <编号>`、`personagent learned rollback <编号>`。

想让它更保守，在 `.env` 里加 `PROMOTE_MIN_SPEAKERS=2`：要两个不同的人都同意才会改。

在群里对它说 `小夏 记住 …`、`小夏 忘掉 …`、`小夏 你都记得什么` 可以直接管理它的记忆；`小夏 学到了什么` 会列出它学到的东西。

## 日常使用

- 每次开机后，要重新启动三个：NapCat、AstrBot、`personagent run`。
- `.env`（设置）和 `persona.txt`（人设）都在 personagent 的数据文件夹里，也就是 `personagent run` 启动时打印的 `home` 那一行。用记事本改，保存为 UTF-8。
- 改了 `.env` 或 `persona.txt`，重启 `personagent run`。改了 AstrBot 或插件的设置，重启 AstrBot。
- 更新：`uv tool upgrade personagent`。
- 改人设不会清空它学到的东西。

## 机器人不说话

按顺序排查，越靠前越常见。先看 `personagent run` 的窗口，再看 AstrBot 网页里的日志，再看控制面板（`http://127.0.0.1:8080/`），它会直接告诉你「还没收到任何消息」「消息被拒绝了」或者「收到了但没说话」。

1. **AstrBot 没把消息交出来。** 在 AstrBot 网页里打开 personagent 插件的设置，确认 `groups` 里有这个群号；私聊要在 `dm_users` 里填发送者的 QQ 号。再确认 `excluded_platforms` 里没有 `aiocqhttp`（有就删掉）。
2. **personagent 没开，或者没有 key。** 看 `personagent run` 那一行 `agent:`。是 `OFF` 就重新运行 `personagent init`，或者在 `.env` 里填 `LLM_API_KEY`。
3. **回话的不是机器人，是 AstrBot 自带的模型（口气突然变了）。** 说明 AstrBot 没连上 personagent，或者 personagent 拒绝了这条消息。看 AstrBot 的日志：
   - `refusing unsafe personagent_url`：插件里的 `personagent_url` 不对。在同一台电脑上就用 `http://127.0.0.1:8080`。
   - `agent refused the request (403)`：两边的 `CONNECTOR_TOKEN` 不一致，或者两台电脑的时钟差了五分钟以上。重新运行 `personagent connect astrbot` 会把两边改成同一个。
   - `timed out waiting for the agent`：模型太慢。把插件的 `timeout_s` 调大，或者把 `.env` 里的 `LLM_TIMEOUT_S` 调小。
   - `agent request failed`：personagent 没在运行，或者地址、端口写错了。
4. **它没被叫到。** 在群里它只回应带它名字（`PERSONA_NAME`）或者 @ 它的消息。别的时候，它要等群里聊够 `CHAT_TRIGGER_COUNT` 条（默认 30 条）才会考虑插话，而且考虑了也可能选择不说。凌晨 2 点到 7 点它更不爱插话。先用名字叫它测试。
5. **QQ 群或私聊被 personagent 自己的白名单挡了。** `.env` 里的 `ACCESS_GROUPS`、`ACCESS_DM_USERS` 只要写了 QQ 号，就只放行写了的。QQ 私聊还必须来自管理员（`ADMIN_IDS`）或在 `ACCESS_DM_USERS` 里。被挡的会话，personagent 的窗口里会记一行，控制面板里也有。
6. **模型调用失败。** key 无效、余额用完，窗口里会有一行 ERROR，写着是哪个服务、该改哪个设置。运行 `personagent doctor` 会向每个模型发一个很小的请求，直接看到状态码。
7. **设置写错了。** 写错的设置名不会报错，只是悄悄用默认值。`personagent doctor` 和启动日志会列出不认识的设置名。
8. **`.env` 带了 BOM。** 用记事本另存为 UTF-8 时选错了编码，第一行设置会失效。`personagent doctor` 会报告，改成「UTF-8」（不带 BOM）重新保存。
9. **`QQ_BOT_ID` 没填或填错。** 应该是小号的 QQ 号。
10. **说话了，但忘了学过的东西。** QQ 的会话必须用 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`（`personagent connect astrbot` 在你选了 QQ 时会替你写好）。少了它，所有 QQ 会话都会被当成新会话。改了 `PERSONA_NAME` 或 `PERSONA_VERSION` 也会让它当作新角色。

还不行，就在 [Issues](https://github.com/wangkant/personagent/issues) 里提问，附上 `personagent doctor` 的输出（先把 key 和 QQ 号打码）。

## 其他情况

### 用 Docker 的话

在容器里，`127.0.0.1` 指的是容器自己，所以 AstrBot 访问不到你电脑上的 personagent，而插件会拒绝发往其他地址的明文 `http://`。二选一：

1. 给 AstrBot 用主机网络：在 compose 文件里把 `ports:` 和 `networks:` 换成 `network_mode: host`（`docker run` 用 `--network host`），然后重建容器。Docker Desktop 需要 4.34 以上版本，并在 设置 > Resources > Network 里打开 `Enable host networking`。同一个文件里的 NapCat 也要用主机网络，它的 WebSocket 地址就是 `ws://127.0.0.1:6199/ws`。
2. 给 personagent 一个 HTTPS 地址（反向代理或隧道），再运行 `personagent connect astrbot <data 文件夹> --url https://你的地址`。

### 别的聊天平台

Telegram、Discord、Slack、KOOK、飞书等走同样的路：`personagent connect astrbot <data 文件夹> --platform telegram --token <机器人 token>`。不同平台的支持情况见 [插件 README](../integrations/astrbot/astrbot_plugin_personagent/README.zh-CN.md)。

### NapCat 的 HTTP 服务

NapCat 的 HTTP 服务在这条路上是可选的。不开也能正常聊天；开了之后，personagent 还能补回它离线期间漏掉的 @。要开的话，在 NapCat 里打开 HTTP 服务，并在 `.env` 里写 `QQ_ONEBOT_URL=http://127.0.0.1:3000`（端口按 NapCat 里设的）。

### 旧的直连方式

NapCat 直接把事件发给 personagent 的 `/v1/onebot` 这条路已经不推荐，但在 1.x 里仍然能用。如果你以前用的是它，改成本文的方式后，要把 NapCat 里指向 `/v1/onebot` 的 HTTP 客户端关掉，否则每条消息会收到两遍。你学到的记忆会保留。

### 其他文档

- [英文版部署指南](deploy.md)：所有设置、对外暴露端口、错误码。
- [AstrBot 插件说明](../integrations/astrbot/astrbot_plugin_personagent/README.zh-CN.md)
- [免责声明](../DISCLAIMER.zh-CN.md)
