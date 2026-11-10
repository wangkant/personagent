"""The chat platforms the local page can connect.

QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK and Stoat are
connected by personagent itself (persona_agent.direct); the rest go through
the managed AstrBot. Each
platform asks only for what its owner must copy from the platform's own
console; for AstrBot every other adapter setting comes from its template for
that adapter, so a new AstrBot release brings its own defaults. Platforms
that need a public callback address are kept apart as advanced.
"""
from __future__ import annotations

import functools
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlsplit

from .astrbot_install import AstrBotInstallation

SCAN, KEY, ADVANCED = "scan", "key", "advanced"


@dataclass(frozen=True)
class Field:
    key: str
    label: tuple[str, str]          # en, zh
    secret: bool = True
    required: bool = True
    kind: str = "text"              # text, url, port
    default: str = ""


@dataclass(frozen=True)
class Platform:
    kind: str                       # AstrBot adapter type, also its id here
    name: tuple[str, str]
    group: str
    fields: tuple[Field, ...] = ()
    settings: dict = field(default_factory=dict)
    guide: str = ""
    note: tuple[str, str] = ("", "")
    # The platform delivers group chats to this kind of bot, not only DMs.
    groups: bool = True
    # Numbered how-to steps shown under the note, each (en, zh).
    steps: tuple[tuple[str, str], ...] = ()
    # "link": after the fields, the owner approves a sign-in through a link.
    sign_in: str = ""


def _token(key: str, en: str, zh: str) -> Field:
    return Field(key, (en, zh))


def _plain(key: str, en: str, zh: str, kind: str = "text", default: str = "") -> Field:
    return Field(key, (en, zh), secret=False, kind=kind, default=default)


def _port(default: int) -> Field:
    return Field("port", ("Callback port", "回调端口"), secret=False, required=False,
                 kind="port", default=str(default))


# Slack's documented pre-filled app link: Socket Mode on, and the scopes and
# events AstrBot's Slack adapter uses, so only the two tokens are left.
_SLACK_MANIFEST = {
    "display_information": {"name": "personagent"},
    "features": {"bot_user": {"display_name": "personagent", "always_online": True},
                 "app_home": {"messages_tab_enabled": True, "messages_tab_read_only_enabled": False}},
    "oauth_config": {"scopes": {"bot": [
        "app_mentions:read", "chat:write", "users:read", "files:read", "files:write",
        "channels:history", "groups:history", "im:history", "mpim:history",
        "channels:read", "groups:read", "im:read", "mpim:read", "im:write"]}},
    "settings": {"event_subscriptions": {"bot_events": [
        "app_mention", "message.channels", "message.groups", "message.im", "message.mpim"]},
        "socket_mode_enabled": True, "org_deploy_enabled": False, "token_rotation_enabled": False},
}
SLACK_NEW_APP = ("https://api.slack.com/apps?new_app=1&manifest_json="
                 + quote(json.dumps(_SLACK_MANIFEST, separators=(",", ":")), safe=""))

# Callbacks go to the adapter's own port: the unified mode would route them
# through the dashboard, which the managed AstrBot does not run.
_OWN_PORT = {"unified_webhook_mode": False, "callback_server_host": "0.0.0.0"}

PLATFORMS: tuple[Platform, ...] = (
    Platform("weixin_oc", ("WeChat", "个人微信"), SCAN,
             note=("Scan with WeChat to log in a personal WeChat bot. It chats one to one; "
                   "WeChat does not deliver group messages to it.",
                   "请使用微信扫码登录个人微信机器人。该机器人仅支持私聊，微信不会向其推送群消息。"),
             groups=False),
    # Scanned through QQ's bind flow; the fields are for a bot made elsewhere.
    Platform("qq_official", ("QQ", "QQ"), SCAN,
             (_plain("appid", "AppID", "AppID"), _token("secret", "AppSecret", "AppSecret")),
             guide="https://q.qq.com/qqbot/openclaw/login.html",
             note=("Scan with mobile QQ and confirm: it creates a bot, or uses one you made, and "
                   "personagent gets its keys by itself.",
                   "请使用手机 QQ 扫码并确认：将新建一个机器人或选用你已有的机器人，personagent 会自动获取其密钥。")),
    Platform("telegram", ("Telegram", "Telegram"), KEY,
             (_token("telegram_token", "Bot token", "机器人 Token"),),
             {"start_message": "", "telegram_command_register": False,
              "telegram_command_auto_refresh": False},
             guide="https://t.me/BotFather",
             note=("Create a bot with @BotFather and paste its token.",
                   "请通过 @BotFather 创建机器人，并粘贴其提供的 Token。")),
    Platform("discord", ("Discord", "Discord"), KEY,
             (_token("discord_token", "Bot token", "机器人 Token"),),
             {"discord_command_register": False},
             guide="https://discord.com/developers/applications",
             note=("Bot page: copy the token and turn on Message Content Intent.",
                   "请在 Bot 页面复制 Token，并开启 Message Content Intent。")),
    Platform("kook", ("KOOK", "KOOK"), KEY,
             (_token("kook_bot_token", "Bot token", "机器人 Token"),),
             guide="https://developer.kookapp.cn/app/index"),
    Platform("lark", ("Feishu / Lark", "飞书"), KEY,
             (_plain("app_id", "App ID", "App ID"),
              _token("app_secret", "App Secret", "App Secret")),
             {"lark_connection_mode": "socket"},
             guide="https://open.feishu.cn/app",
             note=("Use long-connection event subscription; no public address needed.",
                   "事件订阅方式请选择「长连接」，无需公网地址。")),
    Platform("dingtalk", ("DingTalk", "钉钉"), KEY,
             (_plain("client_id", "Client ID", "Client ID"),
              _token("client_secret", "Client Secret", "Client Secret")),
             guide="https://open-dev.dingtalk.com/",
             note=("Use Stream mode for the robot; no public address needed.",
                   "机器人消息接收方式请选择 Stream 模式，无需公网地址。")),
    Platform("slack", ("Slack", "Slack"), KEY,
             (_token("bot_token", "Bot token (xoxb-…)", "Bot Token（xoxb-…）"),
              _token("app_token", "App token (xapp-…)", "App Token（xapp-…）")),
             {"slack_connection_mode": "socket"},
             guide=SLACK_NEW_APP,
             note=("The link creates the app with Socket Mode, scopes and events set. Then add an "
                   "app-level token with connections:write, install the app, and paste both tokens.",
                   "以下链接将创建一个已配置 Socket Mode、权限和事件的 Slack 应用。随后请生成一个包含 "
                   "connections:write 权限的 App-Level Token，将应用安装到工作区，再粘贴这两个 Token。")),
    Platform("wecom_ai_bot", ("WeCom AI bot", "企业微信智能机器人"), KEY,
             (_plain("wecomaibot_ws_bot_id", "Bot ID", "Bot ID"),
              _token("wecomaibot_ws_secret", "Secret", "Secret")),
             {"wecom_ai_bot_connection_mode": "long_connection"},
             guide="https://work.weixin.qq.com/",
             note=("Choose long connection when creating the bot.",
                   "创建机器人时请选择「长连接」。")),
    Platform("mattermost", ("Mattermost", "Mattermost"), KEY,
             (_plain("mattermost_url", "Server address", "服务器地址", kind="url"),
              _token("mattermost_bot_token", "Bot token", "机器人 Token"))),
    Platform("misskey", ("Misskey", "Misskey"), KEY,
             (_plain("misskey_instance_url", "Instance address", "实例地址", kind="url"),
              _token("misskey_token", "Access token", "访问令牌"))),
    Platform("matrix", ("Matrix", "Matrix"), KEY,
             (_plain("matrix_homeserver", "Homeserver address", "服务器地址", kind="url",
                     default="https://matrix.org"),
              _token("matrix_token", "Access token of the bot account",
                     "机器人账号的访问令牌（Access Token）"),
              _plain("matrix_owner", "Your own Matrix ID, for example @you:matrix.org",
                     "你本人的 Matrix ID，例如 @you:matrix.org")),
             guide="https://docs.element.io/latest/element-support/frequently-asked-questions/",
             note=("Use a separate Matrix account for the bot. It joins only the rooms you invite it to, "
                   "and it cannot read end-to-end encrypted rooms, so invite it to a room with "
                   "encryption turned off.",
                   "请为机器人单独注册一个 Matrix 账号。它只加入你本人邀请的房间，且无法读取端到端加密的"
                   "房间，因此请将它邀请至未开启加密的房间。"),
             steps=(
                 ("Create a second Matrix account for the bot, for example at app.element.io. It may be "
                  "on matrix.org or on any other homeserver. Do not use your own account.",
                  "为机器人另行注册一个 Matrix 账号，例如在 app.element.io 注册，可使用 matrix.org "
                  "或其他任意服务器。请勿使用你本人的账号。"),
                 ("Open a private browser window, go to app.element.io and sign in with the bot account.",
                  "打开浏览器的无痕（隐私）窗口，进入 app.element.io，并以机器人账号登录。"),
                 ("Select the bot's avatar in the upper left corner, then choose All settings > Help & "
                  "About. Under Advanced at the bottom, select Access Token, copy it and paste it into "
                  "the access token field here.",
                  "点击左上角的机器人头像，依次选择「所有设置」>「帮助与关于」。在页面底部的「高级」中"
                  "点击「访问令牌（Access Token）」，复制后粘贴到此处的访问令牌一栏。"),
                 ("Close the private window without signing out. Signing out invalidates the token.",
                  "请直接关闭该无痕窗口，不要退出登录。退出登录会使该令牌失效。"),
                 ("In the homeserver field, keep https://matrix.org, or enter the address of the server "
                  "that hosts the bot account.",
                  "「服务器地址」保留 https://matrix.org，或填写机器人账号所在服务器的地址。"),
                 ("In the Matrix ID field, enter your personal Matrix ID, for example @you:matrix.org. "
                  "It is shown in your own Element under All settings > Account.",
                  "在「你本人的 Matrix ID」一栏填写你日常使用的 Matrix ID，例如 @you:matrix.org。"
                  "该 ID 可在你本人的 Element 中「所有设置」>「账户」处查看。"),
                 ("Select Connect. Then, in your own Element, create a new room with end-to-end "
                  "encryption turned off and invite the bot's Matrix ID. The bot accepts invitations "
                  "only from your ID and declines encrypted rooms.",
                  "点击「连接」。随后在你本人的 Element 中新建一个房间，创建时关闭「启用端到端加密」，"
                  "再邀请机器人的 Matrix ID。机器人只接受来自你本人 ID 的邀请，并会拒绝加密房间。"),
             )),
    Platform("twitch", ("Twitch", "Twitch"), KEY,
             (_plain("twitch_client_id", "Client ID of your Twitch application",
                     "Twitch 开发者应用的 Client ID"),
              _plain("twitch_channels", "Channels to chat in, separated by commas",
                     "要加入的频道（频道名，以逗号分隔）")),
             guide="https://dev.twitch.tv/console",
             note=("The character chats in text only, and only in the Twitch channels listed here; "
                   "Twitch whispers are not supported. Register a free application once to obtain its "
                   "Client ID, then approve the sign-in with the character's Twitch account.",
                   "角色只在此处填写的 Twitch 频道中以文字聊天，不支持 Twitch 私信（Whisper）。请先免费"
                   "注册一个开发者应用以获取 Client ID，再使用角色的 Twitch 账号批准登录。"),
             steps=(
                 ("Create a separate Twitch account for the character at twitch.tv. The account that "
                  "approves the sign-in in step 7 is the account that speaks. Verify its email address "
                  "and turn on two-factor authentication under Settings > Security and Privacy; Twitch "
                  "requires this before an application can be registered.",
                  "在 twitch.tv 为角色单独注册一个 Twitch 账号。第 7 步中批准登录的账号即为角色发言所用"
                  "的账号。请验证该账号的邮箱，并在「设置 > 安全和隐私」中开启两步验证；Twitch 要求开启"
                  "后才能注册开发者应用。"),
                 ("While signed in to that account, open https://dev.twitch.tv/console, go to "
                  "Applications and select Register Your Application.",
                  "登录该账号后打开 https://dev.twitch.tv/console，进入 Applications，点击 Register "
                  "Your Application。"),
                 ("Name: any name that is not yet taken on Twitch. OAuth Redirect URLs: enter "
                  "http://localhost and select Add. personagent does not use this address, but the form "
                  "requires one.",
                  "Name 填写一个在 Twitch 上尚未被占用的名称。OAuth Redirect URLs 填写 http://localhost "
                  "并点击 Add。personagent 不使用该地址，但表单要求填写。"),
                 ("Category: Chat Bot. Client Type: Public; a Confidential application is refused. "
                  "Complete the verification check and select Create.",
                  "Category 选择 Chat Bot，Client Type 选择 Public；选择 Confidential 将被拒绝。完成人机"
                  "验证后点击 Create。"),
                 ("Under Applications, select Manage next to the application, copy the Client ID and "
                  "paste it here. The Client ID is not a secret.",
                  "在 Applications 中点击该应用旁的 Manage，复制 Client ID 并粘贴到此处。Client ID "
                  "不属于密钥。"),
                 ("In the channels field, enter the names of the Twitch channels the character should "
                  "chat in, separated by commas, for example your own channel. The character joins only "
                  "these channels.",
                  "在「要加入的频道」一栏填写角色应加入的 Twitch 频道名，以逗号分隔，例如你本人的频道。"
                  "角色只会加入这些频道。"),
                 ("Select Connect. A Twitch link appears. Open it in a browser that is signed in to the "
                  "character's Twitch account, confirm that the code on the page matches, and select "
                  "Authorize.",
                  "点击「连接」，页面将显示一个 Twitch 链接。请在已登录角色 Twitch 账号的浏览器中打开"
                  "该链接，核对页面上的代码一致后点击 Authorize（授权）。"),
                 ("Recommended: in your channel's chat, enter /mod or /vip followed by the character's "
                  "name. This raises the character's message limit and lets it speak in slow mode and "
                  "follower-only mode.",
                  "建议在你频道的聊天中输入 /mod 或 /vip 加角色名。这样可提高角色的发言上限，并使其在"
                  "慢速模式和仅限关注者模式下仍可发言。"),
             ),
             sign_in="link"),
    # A registered nickname has a password; an unregistered one has none.
    Platform("irc", ("IRC (Libera.Chat, OFTC and others)", "IRC（Libera.Chat、OFTC 等）"), KEY,
             (_plain("irc_server", "Server", "服务器", default="irc.libera.chat"),
              Field("irc_port", ("TLS port", "TLS 端口"), secret=False, kind="port", default="6697"),
              _plain("irc_nick", "Bot nickname", "机器人昵称"),
              _plain("irc_channels", "Channels to join, separated by commas", "要加入的频道（以逗号分隔）"),
              Field("irc_password", ("NickServ password", "NickServ 密码"), required=False)),
             guide="https://libera.chat/guides/registration",
             note=("Text only. The bot joins only the channels listed here. Libera.Chat requires the "
                   "explicit permission of each channel's operators before an AI bot joins; obtain it "
                   "first.",
                   "仅支持文字。机器人只加入此处填写的频道。Libera.Chat 规定，AI 机器人加入频道前须获得"
                   "该频道管理员的明确许可，请事先取得许可。"),
             steps=(
                 ("Choose a network. The default, irc.libera.chat with port 6697, is Libera.Chat. For "
                  "OFTC, enter irc.oftc.net with port 6697.",
                  "选择 IRC 网络。默认的 irc.libera.chat、端口 6697 即为 Libera.Chat；如使用 OFTC，请"
                  "填写 irc.oftc.net、端口 6697。"),
                 ("Choose a nickname for the bot that no one else uses, for example NovaBot. Libera.Chat "
                  "requires a bot to have its own account, separate from yours.",
                  "为机器人选定一个无人使用的昵称，例如 NovaBot。Libera.Chat 要求机器人使用独立的账号，"
                  "不得使用你本人的账号。"),
                 ("Recommended: register the nickname. Open https://web.libera.chat, connect with the "
                  "bot's nickname and enter /msg NickServ REGISTER followed by a new password and your "
                  "email address. Within 24 hours, run the VERIFY command given in the email. On OFTC, "
                  "use https://webchat.oftc.net with the same REGISTER command, then open the link in "
                  "the email.",
                  "建议注册该昵称：打开 https://web.libera.chat，以机器人的昵称连接，输入 /msg NickServ "
                  "REGISTER 加新密码和你的邮箱，并在 24 小时内执行邮件中给出的 VERIFY 命令。OFTC 请使用 "
                  "https://webchat.oftc.net，注册命令相同，随后打开邮件中的链接。"),
                 ("Decide which channels the bot joins, for example #mychannel, and obtain the "
                  "permission of each channel's operators first. Libera.Chat rules allow AI bots in a "
                  "channel only with the operators' explicit permission.",
                  "确定机器人要加入的频道，例如 #mychannel，并事先征得每个频道管理员的同意。Libera.Chat "
                  "规定，AI 机器人须获得频道管理员的明确许可方可进入频道。"),
                 ("On this page, enter the server, the port, the bot's nickname, the channels separated "
                  "by commas and, if the nickname is registered, its password. Then select Connect.",
                  "在本页填写服务器、端口、机器人昵称、频道（以逗号分隔），如已注册昵称，再填写其密码，"
                  "然后点击「连接」。"),
                 ("Close any other IRC client that uses the same nickname; otherwise the network "
                  "reports that the nickname is in use.",
                  "请关闭其他正在使用该昵称的 IRC 客户端，否则网络会提示昵称已被占用。"),
             )),
    Platform("zulip", ("Zulip", "Zulip"), KEY,
             (_plain("zulip_site", "Organization address", "组织地址", kind="url"),
              _plain("zulip_email", "Bot email", "机器人邮箱"),
              _token("zulip_api_key", "API key", "API 密钥")),
             guide="https://zulip.com/help/add-a-bot-or-integration",
             note=("Add a Generic bot under Personal settings > Bots and subscribe it to the channels it "
                   "should read. Every member of the organization can send it direct messages, so use it "
                   "only in an organization whose members you trust.",
                   "请在「个人设置 > 机器人」中添加一个通用机器人（Generic bot），并将其订阅到需要读取的"
                   "频道。组织内的所有成员都可以向它发送私信，因此请仅在成员可信的组织中使用。"),
             steps=(
                 ("Open your Zulip organization in the web or desktop application and sign in. The "
                  "address shown in the browser, for example https://yourteam.zulipchat.com, is the "
                  "organization address.",
                  "在网页版或桌面版中打开你的 Zulip 组织并登录。浏览器中显示的地址（例如 "
                  "https://yourteam.zulipchat.com）即为组织地址。"),
                 ("Select the gear icon in the upper right corner and choose Personal settings.",
                  "点击右上角的齿轮图标，选择「个人设置（Personal settings）」。"),
                 ("On the left, select Bots, then select Add a new bot.",
                  "在左侧点击「机器人（Bots）」，再点击「添加新机器人（Add a new bot）」。"),
                 ("For Bot type, choose Generic bot, not Incoming webhook or Outgoing webhook. Enter a "
                  "name, for example the character's name, and a short email name, then select Add.",
                  "「机器人类型」选择「通用机器人（Generic bot）」，不要选择 Incoming webhook 或 Outgoing "
                  "webhook。填写名称（例如角色的名字）和一个简短的邮箱名，然后点击「添加（Add）」。"),
                 ("In the bot's row, select the manage bot icon. Copy the bot email, and copy the API "
                  "key with the copy icon. The Zuliprc configuration box at the bottom shows the email, "
                  "the key and the address together.",
                  "在该机器人所在行点击「管理机器人」图标，复制机器人邮箱，并使用复制按钮复制 API 密钥。"
                  "页面底部的 Zuliprc 配置框中也会同时显示邮箱、密钥和地址。"),
                 ("Paste the organization address, the bot email and the API key here, then select "
                  "Connect.",
                  "将组织地址、机器人邮箱和 API 密钥粘贴到此处，然后点击「连接」。"),
                 ("To let the bot read a channel, open that channel's settings in Zulip and subscribe "
                  "the bot to it. The bot sees only the channels it is subscribed to and the direct "
                  "messages sent to it. It answers when it is mentioned with @ or when one of its "
                  "messages is quoted.",
                  "如需让机器人读取某个频道，请在 Zulip 中打开该频道的设置，将机器人订阅到该频道。机器人"
                  "只能看到已订阅的频道和发给它的私信；当有人 @ 它或引用它的消息时，它会作答。"),
             )),
    Platform("vk", ("VK", "VK（VKontakte）"), KEY,
             (_token("vk_token", "Community access key", "社区访问密钥（Access key）"),),
             guide="https://dev.vk.com/ru/api/bots/getting-started",
             note=("A VK community answers as the character in its private messages and in the group "
                   "chats it has been added to. Turn on the Long Poll API and the message_new event in "
                   "the community settings first. Any VK user can write to a community whose messages "
                   "are on.",
                   "由一个 VK 社区以角色身份回复社区私信，以及它被添加进的群聊。请先在社区设置中开启 "
                   "Long Poll API 和 message_new 事件。社区开启消息功能后，任何 VK 用户都可以向它发送"
                   "消息。"),
             steps=(
                 ("Sign in to vk.com and open the community (a group or public page) that will speak as "
                  "the character. If there is none, create one with Communities > Create community. You "
                  "must be its owner or an administrator.",
                  "登录 vk.com，打开将以角色身份发言的社区（群组或公共主页）。如尚无社区，请通过「社区 > "
                  "创建社区」新建。你必须是该社区的所有者或管理员。"),
                 ("Open Manage (Управление) > Messages (Сообщения) and turn community messages on.",
                  "打开「管理（Управление）> 消息（Сообщения）」，开启社区消息。"),
                 ("In the same Messages section, open Bot settings (Настройки для бота) and turn on Bot "
                  "abilities (Возможности ботов). Tick Allow adding the community to chats (Разрешать "
                  "добавлять сообщество в чаты) only if the character should take part in group chats: "
                  "with it on, any VK user can add the community to their own chat.",
                  "在同一「消息」栏目中打开「机器人设置（Настройки для бота）」，开启「机器人功能"
                  "（Возможности ботов）」。仅当角色需要参与群聊时，才勾选「允许将社区添加到聊天"
                  "（Разрешать добавлять сообщество в чаты）」：开启后，任何 VK 用户都可以将该社区"
                  "添加到自己的群聊中。"),
                 ("Open Manage > API usage (Работа с API) > Access keys (Ключи доступа) and select "
                  "Create key. Tick the rights for community management, community messages and photos, "
                  "confirm, and copy the key.",
                  "打开「管理 > API 使用（Работа с API）> 访问密钥（Ключи доступа）」，点击「创建密钥」。"
                  "勾选社区管理、社区消息和照片三项权限，确认后复制密钥。"),
                 ("On the same API usage page, open the Long Poll API tab, set Long Poll API to Enabled "
                  "and choose the newest API version in the list (5.199).",
                  "在同一「API 使用」页面打开「Long Poll API」标签，将 Long Poll API 设为「开启」，"
                  "并在版本列表中选择最新版本（5.199）。"),
                 ("On the Event types (Типы событий) tab of that page, tick Incoming message "
                  "(message_new) and save.",
                  "在该页面的「事件类型（Типы событий）」标签中勾选「收到消息（message_new）」并保存。"),
                 ("Paste the key into the community access key field here and select Connect.",
                  "将密钥粘贴到此处的「社区访问密钥」一栏，然后点击「连接」。"),
                 ("To use the character in a group chat, add the community to the chat from the chat's "
                  "member list, then give the bot access to all messages in the chat settings. Without "
                  "that access, it receives only messages that mention it or reply to it.",
                  "如需在群聊中使用，请通过群聊的成员列表将社区添加进去，再在群聊设置中授予机器人读取"
                  "全部消息的权限。未获此权限时，机器人只能收到 @ 它或回复它的消息。"),
             )),
    Platform("stoat", ("Stoat (formerly Revolt)", "Stoat（原 Revolt）"), KEY,
             (_token("stoat_token", "Bot token", "机器人令牌（Bot token）"),
              _plain("stoat_api", "API address (change it only for a self-hosted server)",
                     "API 地址（仅自建服务器需要修改）", kind="url", default="https://api.stoat.chat")),
             guide="https://stoat.chat/app",
             note=("Create a bot under Settings > My Bots and paste its token. The bot answers every "
                   "direct message. In servers and groups it answers only where you are a member "
                   "yourself, and only when someone mentions it, replies to it or begins a message with "
                   "its name.",
                   "请在「设置 > 我的机器人」中创建机器人并粘贴其令牌。机器人会回复所有私信；在服务器和"
                   "群组中，它只在你本人也是成员的地方，且仅在有人 @ 它、回复它或以它的名字开头时作答。"),
             steps=(
                 ("Open stoat.chat in a browser, or open the Stoat application, and sign in with your "
                  "own account.",
                  "在浏览器中打开 stoat.chat（或打开 Stoat 客户端），并以你本人的账号登录。"),
                 ("Open Settings (the gear icon) and choose My Bots.",
                  "打开「设置」（齿轮图标），选择「我的机器人（My Bots）」。"),
                 ("Select Create a Bot, enter a name (other users see this name) and confirm.",
                  "点击「创建机器人（Create a Bot）」，填写名称（其他用户看到的即为此名称）并确认。"),
                 ("On the bot's page, copy its token and paste it into the bot token field here. Keep "
                  "the API address unchanged unless you run your own Stoat server.",
                  "在机器人页面复制其令牌（token），粘贴到此处的「机器人令牌」一栏。除非你自行架设了 "
                  "Stoat 服务器，否则请保留默认的 API 地址。"),
                 ("Keep the bot private (do not turn on the public bot option), so that only you can "
                  "add it to servers and groups.",
                  "请保持机器人为私有（不要开启「公开机器人」选项），以确保只有你能将它添加到服务器和"
                  "群组中。"),
                 ("To use it in a server, open the bot's page under My Bots, use the invite option, "
                  "choose a server you can manage or one of your groups, and confirm. The bot speaks "
                  "only in servers and groups that you are a member of.",
                  "如需在服务器中使用，请在「我的机器人」中打开该机器人页面，使用邀请功能，选择一个你有"
                  "管理权限的服务器或你的某个群组，然后确认。机器人只在你本人也是成员的服务器和群组中"
                  "发言。"),
                 ("To talk to the bot directly, open a direct message with it from its profile.",
                  "如需与机器人单独交谈，请从其资料页向它发送私信。"),
             )),
    Platform("wecom",("WeCom app", "企业微信应用"), ADVANCED,
             (_plain("corpid", "Corp ID", "企业 ID"), _token("secret", "Secret", "Secret"),
              _token("token", "Callback token", "回调 Token"),
              _token("encoding_aes_key", "EncodingAESKey", "EncodingAESKey"), _port(6195)),
             _OWN_PORT,
             note=("Needs a public address that forwards to the callback port.",
                   "需要一个可转发至回调端口的公网地址。")),
    Platform("weixin_official_account", ("WeChat Official Account", "微信公众号"), ADVANCED,
             (_plain("appid", "AppID", "AppID"), _token("secret", "AppSecret", "AppSecret"),
              _token("token", "Token", "Token"),
              _token("encoding_aes_key", "EncodingAESKey", "EncodingAESKey"), _port(6194)),
             _OWN_PORT,
             note=("Needs a public address that forwards to the callback port.",
                   "需要一个可转发至回调端口的公网地址。")),
    Platform("qq_official_webhook", ("QQ (webhook)", "QQ（Webhook）"), ADVANCED,
             (_plain("appid", "AppID", "AppID"), _token("secret", "AppSecret", "AppSecret"),
              _port(6196)),
             _OWN_PORT,
             note=("Needs a public address that forwards to the callback port.",
                   "需要一个可转发至回调端口的公网地址。")),
    Platform("aiocqhttp", ("OneBot v11 (NapCat)", "OneBot v11（NapCat）"), ADVANCED,
             (Field("ws_reverse_port", ("Reverse WebSocket port", "反向 WebSocket 端口"),
                    secret=False, required=False, kind="port", default="6199"),
              Field("ws_reverse_token", ("Access token", "访问令牌"), required=False)),
             {"ws_reverse_host": "127.0.0.1"},
             note=("Point NapCat on this computer at ws://127.0.0.1:<port>/ws.",
                   "请将本机的 NapCat 连接至 ws://127.0.0.1:<端口>/ws。")),
    Platform("satori", ("Satori", "Satori"), ADVANCED,
             (_plain("satori_api_base_url", "API address", "API 地址", kind="url",
                     default="http://localhost:5140/satori/v1"),
              _plain("satori_endpoint", "WebSocket address", "WebSocket 地址", kind="url",
                     default="ws://localhost:5140/satori/v1/events"),
              Field("satori_token", ("Token", "Token"), required=False))),
)
BY_KIND = {p.kind: p for p in PLATFORMS}

# Adapter types whose source folder in AstrBot is spelled differently; log
# lines name the folder (`[telegram.tg_adapter:275]`).
_SOURCES = {"qq_official": "qqofficial", "qq_official_webhook": "qqofficial_webhook"}


def failure_pattern(kind: str) -> re.Pattern:
    """An error AstrBot logs when this adapter is refused or cannot start."""
    source = re.escape(_SOURCES.get(kind, kind))
    return re.compile(rf"\[ERRO\].*(\[{source}\.|\[platform\.manager:\d+\]:.*\b{re.escape(kind)}\b)")

_TEMPLATE_CODE = (
    "import json, sys\n"
    "from astrbot.core.config.default import CONFIG_METADATA_2 as M\n"
    "found = [v for v in M['platform_group']['metadata']['platform']['config_template'].values()\n"
    "         if v.get('type') == sys.argv[1]]\n"
    "print(json.dumps(found[0] if found else {}))\n"
)


def is_direct(kind: str) -> bool:
    """Connected by personagent itself rather than through AstrBot."""
    from .direct import KINDS

    return kind in KINDS


def catalog() -> list[dict]:
    """What the page shows; no stored value is part of it."""
    return [{"id": p.kind, "name": list(p.name), "group": p.group, "guide": p.guide,
             "note": list(p.note), "direct": is_direct(p.kind), "groups": p.groups,
             "steps": [list(step) for step in p.steps], "signIn": p.sign_in,
             "fields": [{"key": f.key, "label": list(f.label), "secret": f.secret,
                         "required": f.required, "kind": f.kind, "default": f.default}
                        for f in p.fields]}
            for p in PLATFORMS]


def platform(kind: str) -> Platform:
    found = BY_KIND.get(str(kind))
    if found is None:
        raise ValueError("invalid_platform")
    return found


class FieldError(ValueError):
    """field_required or invalid_field, naming the field it is about."""

    def __init__(self, code: str, key: str = ""):
        super().__init__(code)
        self.key = key


def clean_field(item: Field, raw) -> str | int:
    """One submitted value, checked: its default when empty, a port as a number."""
    text = (str(raw) if isinstance(raw, (str, int)) else "").strip() or item.default
    if not text:
        if item.required:
            raise FieldError("field_required", item.key)
        return ""
    if len(text) > 4096 or any(c in text for c in "\r\n\0"):
        raise FieldError("invalid_field", item.key)
    if item.kind == "port":
        if not text.isdigit() or not 1 <= int(text) <= 65535:
            raise FieldError("invalid_field", item.key)
        return int(text)
    if item.kind == "url":
        parts = urlsplit(text)
        if parts.scheme not in ("https", "http", "wss", "ws") or not parts.hostname:
            raise FieldError("invalid_field", item.key)
        text = text.rstrip("/")
    return text


def clean_values(spec: Platform, values: dict) -> dict:
    """The submitted fields, checked; anything not asked for is dropped."""
    if not isinstance(values, dict):
        raise FieldError("invalid_field")
    return {item.key: clean_field(item, values.get(item.key)) for item in spec.fields}


_PAGE_I18N = Path(__file__).resolve().parent / "static" / "welcome" / "i18n"


@functools.lru_cache(maxsize=None)
def _page_catalog(lang: str) -> dict:
    try:
        return json.loads((_PAGE_I18N / f"{lang}.json").read_text(encoding="utf-8")).get("catalog", {})
    except (OSError, ValueError, AttributeError):
        return {}


def say(pair: tuple[str, str], lang: str) -> str:
    """A name, label, note or step of the catalog in `lang`, as the page shows it."""
    en, zh = pair
    if lang == "zh":
        return zh
    if lang == "en" or not en:
        return en
    return _page_catalog(lang).get(en, zh if lang == "zh-TW" else en)


def astrbot_template(installation: AstrBotInstallation, kind: str) -> dict:
    """AstrBot's own defaults for one adapter, read with AstrBot's Python;
    empty if this AstrBot no longer ships a template for it."""
    try:
        done = subprocess.run([str(installation.python), "-c", _TEMPLATE_CODE, kind],
                              cwd=installation.root, env=installation.environment(),
                              capture_output=True, timeout=120, check=True)
        value = json.loads(done.stdout.decode("utf-8", "replace").strip().splitlines()[-1])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return {}
    return value if isinstance(value, dict) else {}


def entry(template: dict, spec: Platform, values: dict) -> dict:
    """One item of AstrBot's `platform` list."""
    result = {k: v for k, v in template.items() if k != "hint"}
    result.update(spec.settings)
    result.update(values)
    result.update({"id": spec.kind, "type": spec.kind, "enable": True})
    return result


def _main_config(data: Path) -> tuple[Path, dict]:
    path = data / "cmd_config.json"
    return path, json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, cfg: dict) -> None:
    from .storage import atomic_write_text

    atomic_write_text(path, json.dumps(cfg, ensure_ascii=False, indent=4) + "\n")


def connected(data: Path) -> list[str]:
    """The catalog platforms switched on in AstrBot's config, in catalog order."""
    try:
        _, cfg = _main_config(data)
    except (OSError, ValueError):
        return []
    on = {p.get("type") for p in cfg.get("platform", [])
          if p.get("enable") and p.get("id") == p.get("type")}
    return [p.kind for p in PLATFORMS if p.kind in on]


def save_entry(data: Path, item: dict) -> None:
    """Add or replace the entry with this id, keeping every other one."""
    path, cfg = _main_config(data)
    platforms = cfg.get("platform", [])
    for i, existing in enumerate(platforms):
        if existing.get("id") == item["id"]:
            platforms[i] = item
            break
    else:
        platforms.append(item)
    cfg["platform"] = platforms
    _write(path, cfg)


def remove_entry(data: Path, kind: str) -> None:
    path, cfg = _main_config(data)
    cfg["platform"] = [p for p in cfg.get("platform", [])
                       if p.get("id") != kind]
    _write(path, cfg)


def scope(plugin_cfg: dict, kind: str, *, allow: bool) -> dict:
    """Open (or close) one platform's groups and DMs to the character, and
    only that platform: the plugin matches `<adapter type>:*`."""
    wanted = f"{kind}:*"
    for key in ("groups", "dm_users"):
        listed = [str(v) for v in plugin_cfg.get(key, []) if str(v) != wanted]
        plugin_cfg[key] = listed + [wanted] if allow else listed
    return plugin_cfg
