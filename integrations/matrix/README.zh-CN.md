# Matrix 连接器

[English](README.md) · 简体中文 · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


本连接器将 [personagent](https://github.com/wangkant/personagent) 接入 Matrix 房间，并通过 [mautrix 桥](https://docs.mau.fi/bridges/)接入 WhatsApp、Signal、Messenger、Instagram、Google Messages 等网络。Matrix 和这些桥是第三方软件，由你自行运行。personagent 从本地页面连接的平台无需使用它们。

连接器是一个基于 [matrix-nio](https://github.com/matrix-nio/matrix-nio) 的独立小进程，支持端到端加密，不需要 libolm。它以普通 Matrix 用户身份登录主服务器，将每条允许的房间消息作为平台中立的事件转发到 agent 的 `POST /v1/events`（[docs/connectors.md](../../docs/connectors.zh-CN.md)），再将 agent 的回复发回房间。它也轮询 agent 的发件箱，因此定时开场、追问和致歉同样能送达 Matrix。

## 功能

接收消息时，对允许房间中的每条消息：

- 事件使用平台 `matrix` 和原始 Matrix id，因此 agent 存储的是 `matrix:@alex:example.org` 和 `matrix:!room:example.org`。
- 房间在机器人的 `m.direct` 中列出，或者除机器人和 `MATRIX_IGNORE_USERS` 中的用户之外只有一名成员时，视为私聊。私聊按人区分，群按房间区分。在 `MATRIX_GROUPS` 中按 id 写明的房间始终视为群。
- 消息提到机器人或回复机器人的消息时，`addressed` 为 true。提及指 `m.mentions`，或来自无法发送 `m.mentions` 的旧客户端的 pill 或文本中的机器人用户 id。
- 回复会带上被引用消息的发送者和文本。连接器从最近事件的缓存中读取，或拉取父事件。它会去除旧客户端添加在前面的回复回退内容（`> <@alex:example.org> ...`），因此 agent 不会将他人的话误认为发送者的话。
- 不超过 4 MB 的图片和贴纸会被下载，在加密房间里解密，再以字节形式发给 agent。语音消息、视频和文件用文字描述。
- 一个房间的消息按发送顺序到达 agent。图片之后发送的消息须等待图片下载完成。agent 仍可同时处理多轮。
- 时间戳是主服务器的 `origin_server_ts`。
- 连接器跳过机器人自身的消息、`m.notice` 消息（机器人发送的类型）、编辑、反应、来自 `MATRIX_IGNORE_USERS` 的消息、启动时首次同步返回的积压，以及早于 `MATRIX_MAX_EVENT_AGE_S` 的内容，例如桥回填到新房间的历史。

发送时：

- 文本回复是 `m.text`。当 agent 要求在群中提及某人时，回复以 pill 开头，并在 `m.mentions` 中列出此人。其他回复都带空的 `m.mentions`，因此任何客户端都不会将文本中的名字变为提醒。
- 图片回复会上传，在加密房间中也会加密。
- agent 处理一轮时显示正在输入。
- 话题串中的消息在该话题串中回复。
- agent 接管会话后，机器人将消息标为已读（`MATRIX_READ_RECEIPTS_ENABLED`）。通过桥时，这在对方网络上显示为已读标记。
- 发件箱投递发送到会话最后所在的房间。事件的 `reply_handle` 即为房间 id。

## 安装

你需要一个正在运行的 personagent 和一个供机器人使用的 Matrix 账号。请创建一个专用账号，不要与真人共用。

连接器是本仓库中的脚本，因此需要一份仓库副本（克隆，或 GitHub 上的 ZIP）和独立的 Python 环境，因为 `matrix-nio` 不是 personagent 的依赖。如果克隆中已有 personagent 的 `.venv`，请安装到该环境中：

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

如果你使用 pip 从 PyPI 安装了 personagent，或者使用 uvx 运行，请在副本旁边另建一个 venv：

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

在 Windows 上，解释器是 `.venv\Scripts\python.exe` 或 `connector-venv\Scripts\python.exe`。接着复制配置文件：

```bash
cp integrations/matrix/.env.example integrations/matrix/.env
```

编辑 `integrations/matrix/.env`：

```ini
MATRIX_URL=https://matrix.example.org
MATRIX_USER_ID=@nova:example.org
MATRIX_PASSWORD=...
MATRIX_GROUPS=!AbCdEf:example.org
MATRIX_DM_USERS=@alex:example.org
PERSONAGENT_URL=http://127.0.0.1:8080
```

然后用同一个解释器，在 agent 旁边启动连接器：

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

邀请机器人进入 `MATRIX_GROUPS` 列出的房间，机器人即会加入。在 Element 中，房间 id 位于房间设置的高级选项下。

### 登录

密码登录是最简单的入门方式。连接器将获得的会话（用户 id、设备 id 和访问令牌）保存在 `MATRIX_STORE_DIR/session.json`，下次启动时复用，因此重启不会创建新设备。删除该文件即会重新登录。

如需改用已有的访问令牌，请设置 `MATRIX_ACCESS_TOKEN`。连接器会向主服务器查询该令牌所属的账号。请勿使用你本人正在使用的会话的令牌，因为退出该会话也会使机器人退出。

主服务器让机器人退出登录时（`M_UNKNOWN_TOKEN`），连接器会停止并报告该错误。如果使用密码登录，再次启动即会重新登录。如果使用 `MATRIX_ACCESS_TOKEN`，请先设置新令牌。其他同步失败会延迟重试，延迟逐次翻倍，最长一分钟。

### agent 可以运行在哪里

规则由协议决定。`PERSONAGENT_URL` 必须是回环地址，或是 `CONNECTOR_TOKEN` 设为 agent 的 `CONNECTOR_TOKEN` 的 HTTPS。否则连接器拒绝启动。即使只有一台主机，在 agent 前部署代理或隧道之前，也须先在两边设置令牌。

## 配置项

[.env.example](.env.example) 列出了所有配置。列表用逗号分隔并支持通配符，因此 `@*:example.org` 匹配整个服务器。空列表不回应任何人。单独一个 `*` 匹配所有人，并将事件标记为 `prefiltered: false`。此后仅由 agent 自身的 `ACCESS_GROUPS` / `ACCESS_DM_USERS` 决定，那里没有条目的平台会被拒绝。

| 配置项 | 含义 |
|---|---|
| `MATRIX_GROUPS` | 需要回应的群房间，填写房间 id。`*` 表示机器人加入的所有房间。 |
| `MATRIX_DM_USERS` | 可以与机器人私聊的用户。`*` 表示所有人。 |
| `MATRIX_INVITE_FROM` | 机器人接受谁的邀请。`MATRIX_GROUPS` 中房间的邀请和 `MATRIX_DM_USERS` 的私聊邀请始终接受。其他邀请保留不处理。 |
| `MATRIX_IGNORE_USERS` | 永不回应，判断私聊或群时也不计为成员。 |
| `MATRIX_E2EE_ENABLED` | 端到端加密。见下文。 |
| `MATRIX_TIMEOUT_S` | 一轮的最长耗时。须大于 agent 的 3 × `LLM_TIMEOUT_S`。 |
| `MATRIX_OUTBOX_ENABLED` | 轮询 agent 的发件箱。 |

## 桥：WhatsApp、Signal、Messenger、Instagram 等

mautrix 桥以某网络账号的身份登录该网络，将其聊天镜像到称为门户的 Matrix 房间。对方的每个人在 Matrix 中都显示为一个幽灵用户，例如 `@whatsapp_4912345:example.org`。当登录桥的正是机器人的 Matrix 账号时，角色即可在该网络上活动。WhatsApp 联系人向角色的号码发送消息，桥将消息发送到门户房间，本连接器将其转发，回复再沿原路返回。

| 网络 | 桥 |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger、Instagram 私信 | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages（通过 Android 手机的 RCS 和短信） | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice、LinkedIn、Twitter/X 私信、Bluesky 私信、Google Chat、Zulip、IRC、iMessage | 其他 [mautrix 桥](https://github.com/mautrix) |
| Telegram、Discord、Slack | 有 mautrix 桥，但这些网络有官方机器人 API。personagent 直接连接 Telegram 和 Discord，Slack 则通过本地页面运行的 AstrBot 连接。 |

配置步骤：

1. 运行一个由你控制的主服务器（Synapse，或其他支持应用服务的服务器），按[其文档](https://docs.mau.fi/bridges/)安装桥。在桥的 `permissions` 中为机器人账号授予 `user` 权限级别。
2. 以机器人身份登录 Element，打开与桥机器人的聊天（例如 `@whatsappbot:example.org`），发送 `login`。关联角色要使用的网络账号。WhatsApp、Signal 和 Google Messages 使用角色的手机扫描二维码。Messenger 和 Instagram 需提供 Meta 登录信息。见[使用桥](https://docs.mau.fi/bridges/general/using-bridges.html)。
3. 让连接器加入门户，并屏蔽桥自身的消息：

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   `MATRIX_IGNORE_USERS` 的第二项是角色本身号码在桥上的幽灵用户。未启用[双重傀儡](https://docs.mau.fi/bridges/general/double-puppeting.html)时，在角色手机上输入的消息会以该幽灵用户的身份到达 Matrix，机器人就会回复自己。`MATRIX_GROUPS=*` 转发机器人所在的所有群门户，personagent 随后只在 `ACCESS_GROUPS` 以 `matrix:!room:server` 列出的房间回复。在此处填写房间 id，即可改为在连接器中选择房间。

### 傀儡账号

- 桥是该网络的非官方客户端，以普通用户账号登录（关联设备或网页会话）。它不使用机器人 API，网络上也没有任何标识将该账号标记为机器人。
- 角色需要独立的账号，通常有独立的手机号，手机也须保持可连接。手机离线约两周后 WhatsApp 会断开关联设备，Google Messages 只在 Android 手机在线时可用。
- 在群聊中，角色的账号看起来与其他成员相同。请告知大家，他们正在与机器人对话。
- 反应、编辑、删除、投票和通话不会转发给 agent。

### 各网络的条款

连接前请先阅读每个网络的条款。

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) 将自动发送消息列为不允许的通信，禁止未经授权的非个人使用，并可能封禁这样做的账号。其认可的自动化途径是 WhatsApp Business Platform，桥并不使用该途径。
- [Signal](https://signal.org/legal/) 同样将自动发送消息列为不允许。
- [Facebook](https://www.facebook.com/terms.php) 和 [Instagram](https://help.instagram.com/581066165581870) 禁止未经 Meta 许可的自动访问，Meta 可能锁定从其无法识别的客户端登录的账号。
- Google Messages 受 [Google 条款](https://policies.google.com/terms)以及你的移动运营商关于短信和 RCS 的条款约束，运营商可能对自动消息收费或加以限制。

请使用即使丢失也无妨的专用账号，仅在所有人都知道自己正在与机器人对话的会话中使用，并阅读 [DISCLAIMER.md](../../docs/DISCLAIMER.zh-CN.md)。

## 端到端加密

`MATRIX_E2EE_ENABLED=false`（默认）时，机器人只读取未加密房间。在加密房间中，它会记录无法解密，且绝不会在其中发送明文回复。

`MATRIX_E2EE_ENABLED=true` 时：

- `MATRIX_STORE_DIR`（默认是脚本旁边的 `runtime/`，git 会忽略）保存设备密钥和同步令牌。请保留该目录。如果丢失，机器人会成为一个新设备，无法读取此前的任何加密内容。
- 设备在重启前后必须保持不变。密码登录通过保存的会话保持设备。使用访问令牌时，请将 `MATRIX_DEVICE_ID` 设为该令牌对应的设备。
- 机器人与房间中的每台设备共享密钥，无论是否已验证。它无法以交互方式验证自身，因此其他成员看到其设备为未验证状态。它没有密钥备份，也没有交叉签名。
- 密钥尚未到达的消息会被记录并跳过，不会重试。
- mautrix 桥可以加密门户（[端到桥加密](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)）。这些密钥由桥保存在你的服务器上，因此保护至此为止，另一网络使用其自身的加密传输消息。如果你的桥加密门户，请开启 `MATRIX_E2EE_ENABLED`。

## 测试

`tests/test_matrix_connector.py` 模拟了 Matrix 客户端和 agent，因此无需 matrix-nio 和网络：

```bash
python -m pytest tests/test_matrix_connector.py
```
