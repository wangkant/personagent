"""The chat platforms the local page can connect.

QQ, WeChat, Telegram and Discord are connected by personagent itself
(persona_agent.direct); the rest go through the managed AstrBot. Each
platform asks only for what its owner must copy from the platform's own
console; for AstrBot every other adapter setting comes from its template for
that adapter, so a new AstrBot release brings its own defaults. Platforms
that need a public callback address are kept apart as advanced.
"""
from __future__ import annotations

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
                   "用微信扫码，登录一个个人微信机器人。它只能私聊，微信不会把群消息交给它。"),
             groups=False),
    # Scanned through QQ's bind flow; the fields are for a bot made elsewhere.
    Platform("qq_official", ("QQ", "QQ"), SCAN,
             (_plain("appid", "AppID", "AppID"), _token("secret", "AppSecret", "AppSecret")),
             guide="https://q.qq.com/qqbot/openclaw/login.html",
             note=("Scan with mobile QQ and confirm: it creates a bot, or uses one you made, and "
                   "personagent gets its keys by itself.",
                   "用手机 QQ 扫码并确认：会新建一个机器人，或用你已有的，密钥由 personagent 自动取回。")),
    Platform("telegram", ("Telegram", "Telegram"), KEY,
             (_token("telegram_token", "Bot token", "机器人 Token"),),
             {"start_message": "", "telegram_command_register": False,
              "telegram_command_auto_refresh": False},
             guide="https://t.me/BotFather",
             note=("Create a bot with @BotFather and paste its token.",
                   "找 @BotFather 创建机器人，粘贴它给的 Token。")),
    Platform("discord", ("Discord", "Discord"), KEY,
             (_token("discord_token", "Bot token", "机器人 Token"),),
             {"discord_command_register": False},
             guide="https://discord.com/developers/applications",
             note=("Bot page: copy the token and turn on Message Content Intent.",
                   "在 Bot 页面复制 Token，并打开 Message Content Intent。")),
    Platform("kook", ("KOOK", "KOOK"), KEY,
             (_token("kook_bot_token", "Bot token", "机器人 Token"),),
             guide="https://developer.kookapp.cn/app/index"),
    Platform("lark", ("Feishu / Lark", "飞书"), KEY,
             (_plain("app_id", "App ID", "App ID"),
              _token("app_secret", "App Secret", "App Secret")),
             {"lark_connection_mode": "socket"},
             guide="https://open.feishu.cn/app",
             note=("Use long-connection event subscription; no public address needed.",
                   "事件订阅选“长连接”，不需要公网地址。")),
    Platform("dingtalk", ("DingTalk", "钉钉"), KEY,
             (_plain("client_id", "Client ID", "Client ID"),
              _token("client_secret", "Client Secret", "Client Secret")),
             guide="https://open-dev.dingtalk.com/",
             note=("Use Stream mode for the robot; no public address needed.",
                   "机器人消息接收选 Stream 模式，不需要公网地址。")),
    Platform("slack", ("Slack", "Slack"), KEY,
             (_token("bot_token", "Bot token (xoxb-…)", "Bot Token（xoxb-…）"),
              _token("app_token", "App token (xapp-…)", "App Token（xapp-…）")),
             {"slack_connection_mode": "socket"},
             guide=SLACK_NEW_APP,
             note=("The link creates the app with Socket Mode, scopes and events set. Then add an "
                   "app-level token with connections:write, install the app, and paste both tokens.",
                   "下面的链接会创建一个已设好 Socket Mode、权限和事件的应用。之后生成一个带 "
                   "connections:write 的 App-Level Token，安装到工作区，再把两个 Token 粘贴过来。")),
    Platform("wecom_ai_bot", ("WeCom AI bot", "企业微信智能机器人"), KEY,
             (_plain("wecomaibot_ws_bot_id", "Bot ID", "Bot ID"),
              _token("wecomaibot_ws_secret", "Secret", "Secret")),
             {"wecom_ai_bot_connection_mode": "long_connection"},
             guide="https://work.weixin.qq.com/",
             note=("Choose long connection when creating the bot.",
                   "创建机器人时选择“长连接”。")),
    Platform("mattermost", ("Mattermost", "Mattermost"), KEY,
             (_plain("mattermost_url", "Server address", "服务器地址", kind="url"),
              _token("mattermost_bot_token", "Bot token", "机器人 Token"))),
    Platform("misskey", ("Misskey", "Misskey"), KEY,
             (_plain("misskey_instance_url", "Instance address", "实例地址", kind="url"),
              _token("misskey_token", "Access token", "访问令牌"))),
    Platform("wecom", ("WeCom app", "企业微信应用"), ADVANCED,
             (_plain("corpid", "Corp ID", "企业 ID"), _token("secret", "Secret", "Secret"),
              _token("token", "Callback token", "回调 Token"),
              _token("encoding_aes_key", "EncodingAESKey", "EncodingAESKey"), _port(6195)),
             _OWN_PORT,
             note=("Needs a public address that forwards to the callback port.",
                   "需要一个能转发到回调端口的公网地址。")),
    Platform("weixin_official_account", ("WeChat Official Account", "微信公众号"), ADVANCED,
             (_plain("appid", "AppID", "AppID"), _token("secret", "AppSecret", "AppSecret"),
              _token("token", "Token", "Token"),
              _token("encoding_aes_key", "EncodingAESKey", "EncodingAESKey"), _port(6194)),
             _OWN_PORT,
             note=("Needs a public address that forwards to the callback port.",
                   "需要一个能转发到回调端口的公网地址。")),
    Platform("qq_official_webhook", ("QQ (webhook)", "QQ（Webhook）"), ADVANCED,
             (_plain("appid", "AppID", "AppID"), _token("secret", "AppSecret", "AppSecret"),
              _port(6196)),
             _OWN_PORT,
             note=("Needs a public address that forwards to the callback port.",
                   "需要一个能转发到回调端口的公网地址。")),
    Platform("aiocqhttp", ("OneBot v11 (NapCat)", "OneBot v11（NapCat）"), ADVANCED,
             (Field("ws_reverse_port", ("Reverse WebSocket port", "反向 WebSocket 端口"),
                    secret=False, required=False, kind="port", default="6199"),
              Field("ws_reverse_token", ("Access token", "访问令牌"), required=False)),
             {"ws_reverse_host": "127.0.0.1"},
             note=("Point NapCat on this computer at ws://127.0.0.1:<port>/ws.",
                   "让本机的 NapCat 连接 ws://127.0.0.1:<端口>/ws。")),
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
             "fields": [{"key": f.key, "label": list(f.label), "secret": f.secret,
                         "required": f.required, "kind": f.kind, "default": f.default}
                        for f in p.fields]}
            for p in PLATFORMS]


def platform(kind: str) -> Platform:
    found = BY_KIND.get(str(kind))
    if found is None:
        raise ValueError("invalid_platform")
    return found


def clean_values(spec: Platform, values: dict) -> dict:
    """The submitted fields, checked; anything not asked for is dropped."""
    if not isinstance(values, dict):
        raise ValueError("invalid_field")
    clean = {}
    for item in spec.fields:
        raw = values.get(item.key)
        text = (str(raw) if isinstance(raw, (str, int)) else "").strip() or item.default
        if not text:
            if item.required:
                raise ValueError("field_required")
            clean[item.key] = ""
            continue
        if len(text) > 4096 or any(c in text for c in "\r\n\0"):
            raise ValueError("invalid_field")
        if item.kind == "port":
            if not text.isdigit() or not 1 <= int(text) <= 65535:
                raise ValueError("invalid_field")
            clean[item.key] = int(text)
            continue
        if item.kind == "url":
            parts = urlsplit(text)
            if parts.scheme not in ("https", "http", "wss", "ws") or not parts.hostname:
                raise ValueError("invalid_field")
            text = text.rstrip("/")
        clean[item.key] = text
    return clean


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
