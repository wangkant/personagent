"""`personagent init` and `personagent connect`: set up a home, in English or Chinese."""
from __future__ import annotations

import argparse
import functools
import getpass
import hashlib
import json
import locale
import os
import re
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from persona_agent.config_env import DEFAULT_LLM_BASE_URL
from persona_agent.endpoints import chat_completions_url as completions_url, has_scheme
from persona_agent import connections
from persona_agent import home as homes
from persona_agent import langs
from persona_agent.prompts import render_persona_template
from persona_agent.storage import PRIVATE_FILE_MODE

LANGS = langs.CODES
DEFAULT_NAMES = langs.DEFAULT_NAMES

SECRET_FILE_MODE = PRIVATE_FILE_MODE


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------

_lang = "en"


def set_lang(lang: str) -> None:
    global _lang
    _lang = langs.normalize(lang) or "en"


_TRADITIONAL_WORDS = ("traditional", "taiwan", "hong kong", "macao", "macau")
# The primary language in the low byte of a Windows LANGID, and the LANGIDs of
# traditional Chinese.
_WINDOWS_LANGS = {0x04: "zh", 0x11: "ja", 0x12: "ko", 0x0A: "es", 0x0C: "fr",
                  0x07: "de", 0x16: "pt-BR", 0x19: "ru"}
_WINDOWS_TRADITIONAL = (0x0404, 0x0C04, 0x1404)


def _lang_of(tag: str) -> str:
    """A language code for a locale name such as zh_CN.UTF-8 or 'Chinese (Simplified)_China'."""
    tag = (tag or "").strip().lower().split(".")[0]
    if not tag or tag in ("c", "posix"):
        return ""
    if "chinese" in tag:
        return "zh-TW" if any(word in tag for word in _TRADITIONAL_WORDS) else "zh"
    return langs.normalize(tag) or "en"


def detect_lang() -> str:
    """The system's language, en when personagent does not have it."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        found = _lang_of(os.environ.get(var, "").split(":")[0])
        if found:
            return found
    if os.name == "nt":
        import ctypes

        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if langid in _WINDOWS_TRADITIONAL:
            return "zh-TW"
        if langid & 0xFF in _WINDOWS_LANGS:
            return _WINDOWS_LANGS[langid & 0xFF]
    return _lang_of(locale.getlocale()[0] or "") or "en"


def lang_option(value: str) -> str:
    """An argparse type for --lang: any spelling of a language personagent has;
    anything else is refused as init refuses a choice it does not have."""
    code = langs.normalize(value)
    if not code:
        raise argparse.ArgumentTypeError(langs.term("invalid choice: %(value)r (choose from %(choices)s)") % {
            "value": value, "choices": ", ".join(repr(c) for c in LANGS)})
    return code


def t(key: str, **values) -> str:
    """The text for `key` in the current language."""
    text = langs.say(*_TEXT[key], _lang)
    return text.format(**values) if values else text


_TEXT: dict[str, tuple[str, str]] = {
    # header and flow
    "title_first": ("First-time setup", "首次设置"),
    "title_again": ("Reconfigure", "重新配置"),
    "folder": ("Settings are saved in {path}", "设置保存在 {path}"),
    "enter_hint": ("Press Enter to accept the value in [brackets].",
                   "按回车键即采用方括号中的值。"),
    "step": ("Step {n} of 3: {what}", "第 {n} 步（共 3 步）：{what}"),
    "step_model": ("the AI model", "AI 模型"),
    "step_character": ("the character", "角色"),
    "step_chat": ("chat apps (optional)", "聊天平台（可选）"),
    "required": ("(required, please enter a value)", "（必填，请输入一个值）"),
    "yes_no": ("Y/n", "Y/n"),
    "no_yes": ("y/N", "y/N"),
    "bad_number": ("Enter a number from 1 to {n}.", "请输入 1 至 {n} 之间的数字。"),
    "saved": ("Saved to {path}", "已保存到 {path}"),
    # model
    "provider_intro": (
        "The bot talks through an AI service with an OpenAI-compatible API.\n"
        "You sign up with one of these and create an API key (a password for programs).",
        "机器人通过兼容 OpenAI 接口的 AI 服务进行对话。\n"
        "请从以下服务中任选一家注册，并创建一个 API key（供程序使用的密码）。"),
    "provider_choose": ("Service", "选择服务"),
    "base_url_explain": (
        "Base URL = the API address on your provider's page, such as https://api.deepseek.com",
        "Base URL 即服务商文档中注明的 API 地址，例如 https://api.deepseek.com"),
    "base_url": ("Base URL", "Base URL（API 地址）"),
    "base_url_scheme": ("Start the address with https:// (or http:// for a server on this computer).",
                        "地址须以 https:// 开头（本机上的服务可使用 http://）。"),
    "model_explain": ("Model = the model's id at that service, such as {example}",
                      "模型名称即该服务中模型的 ID，例如 {example}"),
    "model": ("Model", "模型名称"),
    "ollama_model": ("Use a model you have pulled; `ollama list` shows them.",
                     "请填写已下载的模型，可通过 `ollama list` 查看。"),
    "key_where": ("Create an API key here: {url}", "请在此处创建 API key：{url}"),
    "key_prompt": ("API key (paste it, then press Enter)",
                   "API key（粘贴后按回车键）"),
    "key_visible": ("Show the API key in this terminal?", "是否在此终端中显示 API Key？"),
    "key_current": ("Current API key: {value}", "当前 API Key：{value}"),
    "key_keep": ("API key (Enter keeps {masked})",
                 "API key（按回车键保留 {masked}）"),
    "key_got": ("key {masked}", "已记录 {masked}"),
    "testing": ("Testing the key with one tiny request to {url}",
                "正在通过一个很小的请求测试密钥：{url}"),
    "test_ok": ("It works.", "测试通过。"),
    "test_failed": ("It did not work ({what}).", "测试未通过（{what}）。"),
    "test_unreachable": ("no answer", "无法连接"),
    "retry": ("Change the answers and try again?", "是否修改后重试？"),
    "kept_anyway": ("Saved anyway. Fix it later by running this setup again.",
                    "设置已照常保存。之后可重新运行本设置进行修正。"),
    "fix_401": ("The service refused the key. Check that you copied all of it and that it\n"
                "belongs to this service.",
                "服务商拒绝了该密钥。请确认密钥已完整复制，且属于该服务。"),
    "key_page": ("Keys: {url}", "密钥页面：{url}"),
    "fix_402": ("The account has no balance or free quota left. Top it up in the service's console.",
                "账户余额或免费额度已用完，请前往服务商控制台充值。"),
    "fix_404": ("Nothing answers at that address, or the model name is unknown.\n"
                "Check the Base URL (it usually looks like {example}) and the model name.",
                "该地址没有对应的接口，或模型名称不存在。\n"
                "请检查 Base URL（通常形如 {example}）和模型名称。"),
    "fix_400": ("The service rejected the request. Its answer: {detail}\n"
                "Usually the model name is wrong, or the model is not enabled for your account.",
                "服务商拒绝了该请求，返回内容为：{detail}\n"
                "通常是由于模型名称有误，或账户尚未开通该模型。"),
    "fix_429": ("Too many requests or no quota right now. Wait a minute, or check your plan.",
                "请求过于频繁或额度不足。请等待一分钟后重试，或检查你的套餐。"),
    "fix_429_free": ("OpenRouter's free models stop at 50 requests a day, until midnight UTC.",
                     "OpenRouter 的免费模型每天限 50 次请求，于 UTC 零点重置。"),
    "fix_5xx": ("The service had an internal error. Try again in a few minutes.",
                "服务商内部出错，请几分钟后重试。"),
    "fix_net": ("Could not reach {host}: {detail}\n"
                "Check the address and your network or proxy.",
                "无法连接 {host}：{detail}\n"
                "请检查地址、网络或代理设置。"),
    "fix_ollama": ("Is Ollama running? Start it with `ollama serve`.",
                   "请确认 Ollama 正在运行，可使用 `ollama serve` 启动。"),
    # character
    "name_explain": ("Name = what people in the chat call the bot. It answers when its name comes up.",
                     "名称即群成员对机器人的称呼。消息中出现该名称时，机器人会作出回应。"),
    "name": ("Bot name", "机器人名称"),
    "renamed": ("(a new name starts a new character: what {old} learned does not carry over)",
                "（更改名称即创建新角色：{old}学到的内容不会沿用）"),
    "name_follows": ("(the name follows the character: {name})", "（名称已随角色更改为{name}）"),
    "lang_switched": ("(the examples, filters and checks switch to {lang} as well)",
                      "（示例、过滤规则和检查也将一并切换为{lang}）"),
    "char_intro": ("Pick a character. It is written to persona.txt, which you can edit any time.",
                   "请选择一种性格。该设置将写入 persona.txt，之后可随时修改。"),
    "char_choose": ("Character", "性格"),
    "char_keep": ("Character (Enter keeps the current one)", "性格（按回车键保留当前设置）"),
    "char_custom": ("persona.txt has your own edits, so it is left as it is.",
                    "persona.txt 已包含你的修改，因此保持不变。"),
    "persona_written": ("persona.txt written ({what})", "已写入 persona.txt（{what}）"),
    # chat apps / AstrBot
    "connect_intro": (
        "Optional: put the bot on a chat platform.\n"
        "personagent connects QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK and Stoat itself.\n"
        "To connect one of them, run `{cmd} <platform>` after this setup; the next steps show how.\n"
        "Other platforms, such as Slack, KOOK or Feishu, are connected through AstrBot, which this step\n"
        "can connect, and download and install if it is not installed yet.",
        "可选：将机器人接入聊天平台。\n"
        "personagent 可直接连接 QQ、微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat。\n"
        "如需连接其中之一，请在完成本设置后运行 `{cmd} <平台>`；后续步骤中会说明具体方法。\n"
        "其他平台（如 Slack、KOOK 或飞书）需通过 AstrBot 接入。本步骤可连接 AstrBot，\n"
        "如尚未安装，也可自动下载并安装。"),
    "astrbot_install_q": ("Download and install AstrBot now? (includes Python 3.12 if needed)",
                          "是否立即自动下载并安装 AstrBot？（如有需要，将一并下载 Python 3.12）"),
    "astrbot_installing": ("Installing AstrBot in {path}. The first download may take a few minutes.",
                           "正在将 AstrBot 安装到 {path}，首次下载可能需要几分钟。"),
    "astrbot_install_failed": ("AstrBot installation failed: {error}\n"
                               "Your agent settings are saved. Retry with `{cmd}`.",
                               "AstrBot 安装未完成：{error}\n"
                               "已保留机器人设置。可运行 `{cmd}` 重试。"),
    "astrbot_menu_intro": ("AstrBot connects personagent to platforms that it does not connect itself, such as "
                           "Slack, KOOK or Feishu. This step uses an existing AstrBot installation or installs "
                           "one, and then connects it to personagent.",
                           "AstrBot 可将 personagent 接入其不直接连接的平台，例如 Slack、KOOK 或飞书。"
                           "此步骤将使用已有的 AstrBot 安装或新建安装，然后将其与 personagent 连接。"),
    "astrbot_menu_q": ("Connect AstrBot now?", "是否立即连接 AstrBot？"),
    "astrbot_menu_skipped": ("AstrBot was not connected. Nothing was changed.", "未连接 AstrBot，未作任何更改。"),
    "astrbot_start": ("Start the installed AstrBot in another terminal:",
                      "请在另一个终端中启动已安装的 AstrBot："),
    "start_title": ("personagent · Start", "personagent · 开始使用"),
    "start_status": ("Character: {name}  |  API key: {masked}", "角色：{name}  |  API Key：{masked}"),
    "start_no_name": ("not yet chosen", "尚未选择"),
    "start_no_key": ("not yet entered", "尚未填写"),
    "start_bad_choice": ('"{choice}" is not one of the options. Enter a number from 0 to 6.',
                         "「{choice}」不是可选项。请输入 0 至 6 之间的数字。"),
    "start_menu": ("1. Chat (first time: set up your model and character)\n"
                   "2. Model, API key and character settings\n"
                   "3. Connect a chat platform (QQ, WeChat, Telegram, Discord, Matrix and others)\n"
                   "4. Start the installed AstrBot\n"
                   "5. Start personagent with the connected chat platforms\n"
                   "6. Watch the offline demo (no API key needed)\n"
                   "0. Exit",
                   "1. 开始聊天（首次使用会先配置模型和角色）\n"
                   "2. 设置模型、API Key 和角色\n"
                   "3. 连接聊天平台（QQ、微信、Telegram、Discord、Matrix 等）\n"
                   "4. 启动已安装的 AstrBot\n"
                   "5. 启动 personagent 及已连接的聊天平台\n"
                   "6. 观看离线演示（无需 API Key）\n"
                   "0. 退出"),
    "start_choose": ("Choose 0–6", "请选择 0–6"),
    "start_failed": ("The command exited with code {code}. You can retry from this menu.",
                     "命令已退出，状态码为 {code}。可在菜单中重新操作。"),
    "connect_q": ("Connect to AstrBot now? (No = skip AstrBot)",
                  "是否立即连接 AstrBot？（否 = 跳过 AstrBot）"),
    "astrbot_explain": ("AstrBot folder = the one holding cmd_config.json: AstrBot's data folder or the one above it.",
                        "AstrBot 文件夹即存放 cmd_config.json 的文件夹：AstrBot 的 data 文件夹或其上一级文件夹。"),
    "astrbot_dir": ("AstrBot folder", "AstrBot 文件夹"),
    "astrbot_bad": ("No cmd_config.json in {path}. Start AstrBot once so it creates one, or give its data folder.",
                    "{path} 中没有 cmd_config.json。请先启动一次 AstrBot 以生成该文件，或填写其 data 文件夹。"),
    "docker_q": ("Does AstrBot run in Docker?", "AstrBot 是否在 Docker 中运行？"),
    "docker_fix": (
        "Inside Docker, 127.0.0.1 is the container itself, so the plugin cannot reach\n"
        "personagent at {url}, and it refuses plain http:// to any other address. Either:\n"
        "  1. Host networking: in AstrBot's compose file replace `ports:` and `networks:`\n"
        "     with `network_mode: host` (docker run: --network host), then recreate it.\n"
        "     Docker Desktop (Windows/macOS) needs version 4.34 or later with\n"
        "     Settings > Resources > Network > Enable host networking turned on.\n"
        "     A NapCat container in the same file needs host networking too; its\n"
        "     WebSocket address becomes ws://127.0.0.1:6199/ws.\n"
        "  2. An HTTPS address for personagent (a reverse proxy or a tunnel), entered below.",
        "在 Docker 中，127.0.0.1 指向容器自身，因此插件无法访问 {url} 上的 personagent，\n"
        "且插件会拒绝发往其他地址的明文 http:// 请求。请选择以下方式之一：\n"
        "  1. 主机网络：在 AstrBot 的 compose 文件中将 `ports:` 和 `networks:` 替换为\n"
        "     `network_mode: host`（docker run 使用 --network host），然后重建容器。\n"
        "     Docker Desktop（Windows/macOS）须为 4.34 或更高版本，并开启\n"
        "     设置 > Resources > Network > Enable host networking。\n"
        "     同一文件中的 NapCat 容器也须使用主机网络，其 WebSocket 地址改为\n"
        "     ws://127.0.0.1:6199/ws。\n"
        "  2. 为 personagent 配置 HTTPS 地址（反向代理或隧道），并在下方填写。"),
    "docker_url": ("personagent's HTTPS address (Enter = keep {url} and use host networking)",
                   "personagent 的 HTTPS 地址（按回车键 = 保留 {url} 并使用主机网络）"),
    "url_refused": ("The plugin only accepts a 127.0.0.1 / localhost address or an https:// one.",
                    "插件仅接受 127.0.0.1 / localhost 地址或 https:// 地址。"),
    "coding_connected": ("{name} is in {target}. Start a new session there and ask it to talk to {name}.",
                         "{name} 已接入 {target}。请在其中新建会话，并让其与 {name} 对话。"),
    "coding_removed": ("personagent is out of {target}.", "personagent 已从 {target} 移除。"),
    "coding_no_cli": ("`{command}` is not on PATH. Install it first, then run this again.",
                      "PATH 中未找到 `{command}`。请先安装，然后重新运行此命令。"),
    "coding_no_key": ("No model key yet: run personagent and paste it into the page first.",
                      "尚未设置模型密钥：请先运行 personagent，并在页面中填写。"),
    "coding_dsh_restart": ("Restart DeepSeek Harness first. A way of running it you have not started yet "
                           "has no profile: start it once and run this again.",
                           "请先重启 DeepSeek Harness。尚未启动过的运行方式没有配置文件：请先启动一次，再运行此命令。"),
    "coding_react": ("When a turn ends the character may say a line. The folder's name and the start of the "
                     "coding agent's last message go to your model service, at most once per "
                     "CODING_REACT_COOLDOWN_S.",
                     "每轮结束时，角色可能会发表一句评论。文件夹名称及编程助手最后一条消息的开头将发送至你的模型服务，"
                     "每个 CODING_REACT_COOLDOWN_S 周期内最多一次。"),
    "coding_no_dsh": ("No DeepSeek Harness profile under {path}. Start it once, then run this again.",
                      "{path} 下没有 DeepSeek Harness 配置。请先启动一次，再运行此命令。"),
    "coding_no_react_dsh": ("--react is for claude-code and codex: DeepSeek Harness has no way yet to "
                            "show a hook's message to you.",
                            "--react 仅支持 claude-code 和 codex：DeepSeek Harness 目前无法向你显示 hook 的消息。"),
    "coding_react_trust": ("Codex runs a new hook only after you trust it: type /hooks in a Codex session.",
                           "Codex 仅运行你已信任的 hook：请在 Codex 会话中输入 /hooks 进行确认。"),
    "platform_intro": ("Which chat app should the bot join?", "请选择机器人要加入的聊天平台。"),
    "platform_choose": ("Chat app", "聊天平台"),
    "platform_other": ("Another app, already set up in AstrBot", "其他平台（已在 AstrBot 中配置）"),
    "qq_via": ("QQ (through NapCat)", "QQ（通过 NapCat）"),
    "qq_id": ("The bot's own QQ number (the account NapCat logs in with)",
              "机器人自身的 QQ 号（即 NapCat 登录的账号）"),
    "qq_groups": ("QQ group numbers it should join, comma-separated",
                  "要加入的 QQ 群号，多个群号以逗号分隔"),
    "groups_other": ("Group ids it should join, comma-separated (send /sid in the group to see its id)",
                     "要加入的群 ID，多个 ID 以逗号分隔（在群聊中发送 /sid 即可查看）"),
    "ids_keep": ("Enter keeps these, '-' clears them", "按回车键保留，输入 - 清空"),
    "ids_none": ("Enter = none yet", "按回车键 = 暂不设置"),
    "admin_explain": ("Admin = you. The bot is closest to you, you can always message it privately,\n"
                      "and you can manage what it remembers.",
                      "管理员即你本人。机器人与你关系最近，你可随时与其私聊，并管理其记住的内容。"),
    "admin_qq": ("Your own QQ number (Enter = no admin)", "你本人的 QQ 号（按回车键 = 不设管理员）"),
    "admin_other": ("Your user id on {platform} (send /sid to the bot to see it; Enter = no admin)",
                    "你在 {platform} 上的用户 ID（私聊机器人并发送 /sid 即可查看；按回车键 = 不设管理员）"),
    "admin_any": ("Your account as platform:id, such as wecom:alice (send /sid to the bot; Enter = no admin)",
                  "你的账号，格式为 平台:ID，例如 wecom:alice（私聊机器人并发送 /sid 即可查看；按回车键 = 不设管理员）"),
    "admin_name": ("What should the bot call you?", "机器人应如何称呼你？"),
    "dm_users": ("Who else may message the bot privately? Comma-separated ids",
                 "还允许哪些用户私聊机器人？请填写 ID，以逗号分隔"),
    "token_skip": ("Enter = already set up in AstrBot", "按回车键 = 已在 AstrBot 中配置"),
    "platform_written": ("{kind} switched on in AstrBot's settings; it starts with AstrBot.",
                         "已在 AstrBot 的设置中启用 {kind}，将随 AstrBot 一同启动。"),
    "plugin_installed": ("AstrBot plugin installed: {path}", "AstrBot 插件已安装：{path}"),
    "plugin_config": ("Plugin settings written: {path}", "插件设置已写入：{path}"),
    "write_failed": ("Could not write to {path}: {error}", "无法写入 {path}：{error}"),
    "url_replaced": ("personagent_url {old} would be refused by the plugin; it is now {new}",
                     "插件会拒绝 personagent_url {old}，已改为 {new}"),
    "url_kept": ("Keeping personagent_url {url} (personagent listens on port {port})",
                 "保留 personagent_url {url}（personagent 监听端口 {port}）"),
    "retired_removed": ("Removed {path}: the same plugin under an older name, which would forward every message twice",
                        "已删除 {path}：这是同一插件的旧名称，保留会导致每条消息被转发两次"),
    "retired_config": ("Removed {path}, the older plugin's settings. QQ routing came across;\n"
                       "set groups and dm_users again in AstrBot's WebUI.",
                       "已删除旧插件的设置 {path}。QQ 转发设置已沿用；\n"
                       "请在 AstrBot 的 WebUI 中重新设置 groups 和 dm_users。"),
    "allowlists_empty": ("The plugin forwards no group or DM yet: add groups / dm_users in AstrBot's WebUI.",
                         "插件尚未放行任何群聊或私聊：请在 AstrBot 的 WebUI 中填写 groups / dm_users。"),
    "allowlists_kept": ("Kept the plugin's groups and dm_users.", "已保留插件现有的 groups 和 dm_users。"),
    # platforms personagent connects itself
    "direct_list_title": ("Chat platforms that personagent connects itself:",
                          "personagent 可直接连接的聊天平台："),
    "direct_on": ("connected", "已连接"),
    "direct_off": ("not connected", "未连接"),
    "direct_via_astrbot": ("connected through AstrBot", "已通过 AstrBot 连接"),
    "direct_list_how": ("To connect one, run `{cmd} <platform>`, for example "
                        "`{cmd} telegram`. To disconnect it, add --remove.",
                        "如需连接，请运行 `{cmd} <平台>`，例如 "
                        "`{cmd} telegram`。如需断开连接，请加上 --remove。"),
    "direct_list_more": ("Other platforms, such as Slack, KOOK or Feishu, are connected through AstrBot: "
                         "`{cmd} astrbot`. Coding assistants: `{cmd} claude-code`, "
                         "`codex` or `dsh`.",
                         "其他平台（如 Slack、KOOK 或飞书）需通过 AstrBot 接入：`{cmd} astrbot`。"
                         "编程助手：`{cmd} claude-code`、`codex` 或 `dsh`。"),
    "direct_unknown": ("personagent cannot connect \"{name}\". Run `{cmd}` to list the "
                       "platforms it can connect.",
                       "personagent 无法连接“{name}”。请运行 `{cmd}` 查看可连接的平台。"),
    "direct_no_input_qq": ("With --no-input, QQ is connected with the values of a bot created on the QQ Open "
                           "Platform: give --appid and --secret. Scanning a code requires a terminal without "
                           "--no-input.",
                           "使用 --no-input 时，需通过在 QQ 开放平台创建的机器人信息连接 QQ：请提供 --appid 和 "
                           "--secret。扫码连接须在终端中运行且不使用 --no-input。"),
    "direct_no_input_wechat": ("WeChat is connected by scanning a code, which --no-input does not allow. Run "
                               "this command in a terminal without --no-input, or connect WeChat in the "
                               "personagent window.",
                               "微信需扫码连接，而 --no-input 不允许等待扫码。请在终端中不加 --no-input 运行此命令，"
                               "或在 personagent 窗口中连接微信。"),
    "direct_guide": ("Guide: {url}", "说明：{url}"),
    "direct_steps": ("Steps:", "操作步骤："),
    "direct_steps_here": ("Where a step mentions this page or the Connect button, enter the values below "
                          "instead. They are checked with {name} before anything is saved.",
                          "步骤中提到本页或「连接」按钮之处，请改为在下方填写各项。所有内容将先经 {name} "
                          "核验，然后才会保存。"),
    "direct_optional": ("{label} (optional)", "{label}（可选）"),
    "direct_required": ("This value is required.", "此项为必填项。"),
    "direct_invalid": ("This value is not valid. An address must be complete and begin with https://, "
                       "and a port must be a number from 1 to 65535.",
                       "此项格式不正确。地址须完整并以 https:// 开头，端口须为 1 至 65535 之间的数字。"),
    "direct_missing": ("The required value {flag} ({label}) was not given.",
                       "未提供必填项 {flag}（{label}）。"),
    "direct_bad_flag": ("The value given with {flag} ({label}) is not valid.",
                        "通过 {flag} 提供的值（{label}）格式不正确。"),
    "direct_nothing_saved": ("Nothing was saved.", "未保存任何内容。"),
    "direct_qq_ways": ("QQ can be connected in two ways:\n"
                       "  1. Scan a code with mobile QQ, which creates a bot or selects one of yours\n"
                       "  2. Enter the AppID and AppSecret of a bot you created on the QQ Open Platform",
                       "QQ 可通过以下两种方式连接：\n"
                       "  1. 使用手机 QQ 扫码，新建一个机器人或选用你已有的机器人\n"
                       "  2. 填写你在 QQ 开放平台创建的机器人的 AppID 和 AppSecret"),
    "direct_way": ("Method", "连接方式"),
    "direct_scan_qq": ("Scan this code with mobile QQ and confirm:", "请使用手机 QQ 扫描以下二维码并确认："),
    "direct_scan_wechat": ("Scan this code with WeChat and confirm the login:",
                           "请使用微信扫描以下二维码并确认登录："),
    "direct_scan_address": ("The code contains this address: {url}", "该二维码对应的地址为：{url}"),
    "direct_scan_fallback": ("If the code cannot be scanned in this terminal, connect {name} in the "
                             "personagent window instead, which the command below opens:",
                             "如无法扫描终端中显示的二维码，请改在 personagent 窗口中连接 {name}。"
                             "该窗口可通过以下命令打开："),
    "direct_link": ("Open this link in a browser that is signed in to the character's {name} account, "
                    "check that the page shows the code below, and approve the sign-in:",
                    "请在已登录角色 {name} 账号的浏览器中打开以下链接，核对页面显示的代码与下方一致后，"
                    "批准登录："),
    "direct_code": ("Code: {code}", "代码：{code}"),
    "direct_waiting": ("Waiting for the approval. Press Ctrl+C to stop.", "正在等待批准。按 Ctrl+C 可中止。"),
    "direct_checking": ("Checking the values with {name}.", "正在向 {name} 核验所填内容。"),
    "direct_failed": ("{name} was not connected, and nothing was saved.", "{name} 未能连接，未保存任何内容。"),
    "direct_stopped": ("Stopped. Nothing was saved.", "已中止，未保存任何内容。"),
    "direct_unexpected": ("An unexpected error ({error}) stopped the connection. Run the command again; if the "
                          "error recurs, connect the platform from the personagent window.",
                          "连接因意外错误（{error}）而中止。请重新运行此命令；如该错误再次出现，请改在 "
                          "personagent 窗口中连接该平台。"),
    "direct_saved": ("{name} is connected. Its values are saved in {path}.",
                     "{name} 已连接，相关信息已保存至 {path}。"),
    "direct_released": ("{name} was also connected through AstrBot. That connection has been removed, "
                        "so that the bot is not served twice.",
                        "{name} 此前也已通过 AstrBot 连接。该连接已移除，以免同一机器人被重复接入。"),
    "direct_next": ("The connection is active while personagent runs: start it with the command below and "
                    "keep the terminal open, or restart it if it is already running. {log} records the "
                    "connection.",
                    "personagent 运行期间，该连接保持有效：请使用以下命令启动 personagent 并保持终端开启；"
                    "如其已在运行，请重新启动。{log} 会记录该连接的情况。"),
    "direct_restart": ("If personagent is already running, restart it so that it applies this change.",
                       "如 personagent 已在运行，请重新启动，以使此项更改生效。"),
    "direct_no_key": ("Set up the AI model first, otherwise the character cannot answer:",
                      "请先设置 AI 模型，否则角色无法回复："),
    "direct_removed": ("{name} is disconnected, and its saved values have been deleted.",
                       "{name} 已断开连接，已保存的信息已删除。"),
    "direct_not_connected": ("{name} is not connected. Nothing was changed.", "{name} 未连接，未作任何更改。"),
    "menu_platforms": ("Which chat platform should the character join?", "请选择角色要加入的聊天平台。"),
    "menu_astrbot": ("Another platform through AstrBot (Slack, KOOK, Feishu and others)",
                     "通过 AstrBot 接入的其他平台（Slack、KOOK、飞书等）"),
    "menu_back": ("Back", "返回"),
    "menu_platform_choose": ("Choose 0–{n}", "请选择 0–{n}"),
    "menu_platform_bad": ('"{choice}" is not one of the options. Enter a number from 0 to {n}.',
                          "「{choice}」不是可选项。请输入 0 至 {n} 之间的数字。"),
    # why a platform refused; `<code>_<platform>` is one platform's own wording
    "refused_platform_rejected": ("{name} refused the connection. Check the values and the platform's own "
                                  "settings, then try again.",
                                  "{name} 拒绝了此次连接。请检查所填内容及平台后台的设置，然后重试。"),
    "refused_network_failed": ("The servers of {name} could not be reached. Check the network connection "
                               "and any proxy settings, then try again.",
                               "无法连接 {name} 的服务器。请检查网络连接及代理设置，然后重试。"),
    "refused_display_failed": ("This terminal could not display the sign-in for {name}. Connect {name} in the "
                               "personagent window instead.",
                               "此终端无法显示 {name} 的登录信息。请改在 personagent 窗口中连接 {name}。"),
    "refused_scan_failed": ("The scan did not complete, or the code expired. Run the command again to "
                            "receive a new code.",
                            "扫码未完成或二维码已过期。请重新运行此命令以获取新的二维码。"),
    "refused_scan_failed_twitch": ("The Twitch sign-in did not finish, was declined, or the link expired. "
                                   "Run the command again to receive a new link.",
                                   "Twitch 登录未完成、已被拒绝或链接已过期。请重新运行此命令以获取新的链接。"),
    "refused_token_rejected": ("{name} did not accept this token. Copy the complete token again.",
                               "{name} 未接受该令牌。请重新复制完整的令牌。"),
    "refused_token_rejected_zulip": ("Zulip does not accept this bot email and API key. Copy both again "
                                     "from the bot's row under Personal settings > Bots.",
                                     "Zulip 不接受该机器人邮箱和 API 密钥。请在「个人设置 > 机器人」中该机器人"
                                     "所在行重新复制这两项。"),
    "refused_token_rejected_vk": ("VK does not accept this key. Create a community access key under Manage > "
                                  "API usage > Access keys and enter the whole key.",
                                  "VK 不接受该密钥。请在「管理 > API 使用 > 访问密钥」中创建社区访问密钥，"
                                  "并完整填写。"),
    "refused_token_rejected_twitch": ("The Twitch sign-in did not grant the chat permissions. Run the command "
                                      "again and approve the sign-in again.",
                                      "此次 Twitch 登录未授予聊天权限。请重新运行此命令并再次批准登录。"),
    "refused_app_rejected": ("QQ did not accept the AppID or AppSecret. Copy them again from the QQ console.",
                             "QQ 未接受该 AppID 或 AppSecret。请到 QQ 开放平台重新复制。"),
    "refused_app_rejected_twitch": ("Twitch does not accept this Client ID for this sign-in. Check that the "
                                    "application exists and that its Client Type is Public, then copy the "
                                    "Client ID again.",
                                    "Twitch 不接受此 Client ID 用于本次登录。请确认该开发者应用存在且 Client "
                                    "Type 为 Public，然后重新复制 Client ID。"),
    "refused_bot_in_use": ("Another program is using this bot, or a webhook is set for it. Stop that program, "
                           "then connect again.",
                           "该机器人正被其他程序使用，或已设置 Webhook。请先停止该程序，然后重新连接。"),
    "refused_message_content_intent_off": ("Discord refused the connection. Turn on Message Content Intent on "
                                           "the Bot page of the developer portal, save, and try again.",
                                           "Discord 拒绝了连接。请在开发者后台的 Bot 页面开启 Message Content "
                                           "Intent，保存后重试。"),
    "refused_intents_not_allowed": ("QQ has not given this bot permission to receive group and direct "
                                    "messages.",
                                    "QQ 未授予该机器人接收群聊和私聊消息的权限。"),
    "refused_session_expired": ("The login has expired. Run the command again.", "登录已失效，请重新运行此命令。"),
    "refused_session_expired_twitch": ("The Twitch sign-in has ended. Run the command again and approve the "
                                       "sign-in again.",
                                       "Twitch 登录已失效。请重新运行此命令并再次批准登录。"),
    "refused_bot_offline": ("This QQ bot has been taken offline.", "该 QQ 机器人已下架。"),
    "refused_bot_banned": ("This QQ bot has been banned.", "该 QQ 机器人已被封禁。"),
    "refused_bot_banned_irc": ("The network has banned this connection (a K-line or another ban).",
                               "该 IRC 网络已封禁此连接（K-line 或其他封禁）。"),
    "refused_bot_banned_vk": ("VK has blocked or deactivated this community.", "VK 已封禁或停用该社区。"),
    "refused_account_deactivated": ("The platform has deactivated this bot account or its organization. "
                                    "Reactivate it on the platform, or create a new bot account and connect "
                                    "again.",
                                    "平台已停用该机器人账号或其所在组织。请在平台上重新启用，或新建一个机器人"
                                    "账号后重新连接。"),
    "refused_insecure_address": ("The server address must begin with https://. A plain http address is "
                                 "accepted only for a server on this computer.",
                                 "服务器地址必须以 https:// 开头。仅本机上的服务器可以使用 http 地址。"),
    "refused_homeserver_invalid": ("This address is not a Matrix homeserver that accepts secure connections. "
                                   "Check the address, for example https://matrix.org. A plain http address "
                                   "is accepted only for a server on this computer.",
                                   "该地址不是可用的 Matrix 服务器，或未使用安全连接（https）。请检查地址，例如 "
                                   "https://matrix.org。仅本机上的服务器可以使用 http 地址。"),
    "refused_owner_invalid": ("Enter your own Matrix ID, for example @you:matrix.org. It must be your "
                              "personal account, not the bot account.",
                              "请填写你本人的 Matrix ID，例如 @you:matrix.org。该 ID 必须是你本人的账号，"
                              "而不是机器人账号。"),
    "refused_channel_not_found": ("One of the listed Twitch channels does not exist, or no channel was "
                                  "entered. Check the channel names and try again.",
                                  "所填写的 Twitch 频道中有一个不存在，或未填写任何频道。请检查频道名后重试。"),
    "refused_nick_in_use": ("This nickname is already in use on the network. Close the other IRC client "
                            "that uses it, or choose another nickname.",
                            "该昵称在此网络上已被占用。请关闭正在使用该昵称的其他 IRC 客户端，或改用其他昵称。"),
    "refused_nick_invalid": ("The network does not accept this nickname. Use only letters, digits and the "
                             "characters - _ [ ] {{ }} | ^, and begin with a letter.",
                             "该网络不接受此昵称。昵称只能包含字母、数字及 - _ [ ] {{ }} | ^，且须以字母开头。"),
    "refused_password_rejected": ("The network reports that the nickname's password is incorrect. Check the "
                                  "NickServ password for this nickname.",
                                  "网络提示该昵称的密码不正确。请检查该昵称在 NickServ 中的密码。"),
    "refused_sasl_required": ("This network accepts only registered nicknames from your network address. "
                              "Register the nickname with NickServ and enter its password.",
                              "该网络只允许已注册的昵称从你的网络地址连接。请先通过 NickServ 注册昵称，"
                              "再填写其密码。"),
    "refused_long_poll_off": ("The Long Poll API is turned off for this community. In the community, open "
                              "Manage > API usage > Long Poll API, set it to Enabled, and connect again.",
                              "该社区未开启 Long Poll API。请在社区中打开「管理 > API 使用 > Long Poll API」，"
                              "将其设为「开启」，然后重新连接。"),
    "refused_message_events_off": ("The community does not yet send new messages to the bot. Under Manage > "
                                   "API usage > Long Poll API > Event types, tick Incoming message "
                                   "(message_new) and save.",
                                   "该社区尚未向机器人推送新消息。请在「管理 > API 使用 > Long Poll API > 事件"
                                   "类型」中勾选「收到消息（message_new）」并保存。"),
    "refused_token_rights_missing": ("This key lacks a required right. Create a new key under Manage > API "
                                     "usage with community management, messages and photos ticked, then "
                                     "enter it here.",
                                     "该密钥缺少必需的权限。请在「管理 > API 使用」中新建密钥，勾选社区管理、"
                                     "消息和照片权限，再在此处填写。"),
    "refused_not_a_bot": ("These are the details of a personal account, not of a bot. Add a Generic bot "
                          "under Personal settings > Bots and enter its email and API key.",
                          "这是个人账号的信息，而非机器人的信息。请在「个人设置 > 机器人」中添加一个通用"
                          "机器人，并填写其邮箱和 API 密钥。"),
    "refused_wrong_bot_type": ("This bot cannot read messages. In Zulip, add a bot of the type Generic bot "
                               "and use its details.",
                               "该机器人无法读取消息。请在 Zulip 中添加类型为「通用机器人（Generic bot）」的"
                               "机器人，并使用其信息。"),
    "refused_not_zulip_site": ("This address does not respond as a Zulip organization. Copy the address from "
                               "the browser while Zulip is open, for example https://yourteam.zulipchat.com.",
                               "该地址不是 Zulip 组织的地址。请在打开 Zulip 时从浏览器地址栏复制，例如 "
                               "https://yourteam.zulipchat.com。"),
    # finish
    "done": ("Setup complete", "设置完成"),
    "next": ("Next:", "接下来："),
    "next_demo": ("Watch it stay quiet and learn from a correction (a minute, no chat account needed):",
                  "观察角色如何判断是否发言、如何从纠正中学习（约一分钟，无需聊天账号）："),
    "next_chat": ("Chat with {name} in this terminal:", "在终端中与{name}聊天："),
    "next_run": ("Start personagent and keep it running (AstrBot talks to it):",
                 "启动 personagent 并保持运行（AstrBot 将与其连接）："),
    "next_restart": ("Restart AstrBot, or reload plugins in its WebUI, so it loads the plugin.",
                     "重启 AstrBot，或在其 WebUI 中重新加载插件，使插件生效。"),
    "next_qq": ("In AstrBot's WebUI add the QQ (OneBot v11 / aiocqhttp) platform, and point NapCat's\n"
                "     reverse WebSocket at ws://127.0.0.1:6199/ws. Guide: https://docs.astrbot.app",
                "在 AstrBot 的 WebUI 中添加 QQ（OneBot v11 / aiocqhttp）平台，再将 NapCat 的\n"
                "     反向 WebSocket 指向 ws://127.0.0.1:6199/ws。教程：https://docs.astrbot.app"),
    "next_say": ("Say \"{name}, hi\" in one of those groups.", "在其中一个群聊中发送「{name}，你好」。"),
    "next_platform": ("Connect a chat platform that personagent connects itself, such as Telegram, Discord, "
                      "Matrix or IRC. Without a platform name, the command lists them all:",
                      "接入 personagent 可直接连接的聊天平台，例如 Telegram、Discord、Matrix 或 IRC。"
                      "不指定平台名称时，该命令将列出全部平台："),
    "next_persona": ("Edit {path} to change who {name} is, then restart.",
                     "修改 {path} 即可调整{name}的人设，修改后请重新启动。"),
    "next_key": ("Add your API key: run this setup again, or set LLM_API_KEY in {path}.",
                 "请填写 API key：重新运行本设置，或在 {path} 中设置 LLM_API_KEY。"),
    "chat_now": ("Chat with the bot in this terminal now?", "是否立即在终端中与机器人聊天？"),
    "skipped": ("Setup questions skipped: {why}. Run `{cmd}` in a terminal, or pass "
                "--no-input with --provider, --key-env and --name.",
                "已跳过设置问答：{why}。请在终端中运行 `{cmd}`，或使用 --no-input 并指定 "
                "--provider、--key-env、--name 等参数。"),
    "key_cleared": ("The API key saved for the previous AI service was cleared, so it is not sent to the new one. "
                    "Pass --key-env VAR to set a key for this service.",
                    "原 AI 服务的 API key 已清除，不会发送至新服务。"
                    "请使用 --key-env VAR 为新服务设置 key。"),
    "skip_tty": ("input is not a terminal", "输入不是终端"),
    "key_env_empty": ("--key-env {name}: that environment variable is empty, so there is no API key to save. "
                      "Nothing was changed.",
                      "--key-env {name}：该环境变量为空，没有可保存的 API key。未作任何更改。"),
    "home_diverges": ("AGENT_HOME in {env} points at {other}, so personagent reads its settings there,\n"
                      "not here. Move the files there, or remove that line.",
                      "{env} 中的 AGENT_HOME 指向 {other}，personagent 将从该位置读取设置，\n"
                      "而非此处。请将文件移至该位置，或删除该行。"),
    "home_unresolved": ("AGENT_HOME is {value}, which cannot be resolved; check it before starting.",
                        "AGENT_HOME 为 {value}，无法解析；请在启动前检查。"),
}


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Provider:
    key: str
    name: tuple[str, str]
    base_url: str
    model: str
    key_url: str
    note: tuple[str, str] = ("", "")

    @property
    def label(self) -> str:
        return langs.say(*self.name, _lang)

    @property
    def hint(self) -> str:
        return langs.say(*self.note, _lang)

    @property
    def needs_key(self) -> bool:
        return self.key != "ollama"


# Base URLs as each vendor documents them for OpenAI-compatible chat.
PROVIDERS: tuple[Provider, ...] = (
    Provider("openrouter", ("OpenRouter", "OpenRouter"), "https://openrouter.ai/api/v1",
             "openrouter/free", "https://openrouter.ai/keys",
             ("openrouter/free picks one of OpenRouter's free models for each request. The key costs "
              "nothing and the limit is 50 requests a day. Some free providers keep what they receive.",
              "openrouter/free 会为每次请求选用一个 OpenRouter 免费模型。密钥本身不收费，每天限 50 次请求。"
              "部分免费服务商会保留收到的内容。")),
    Provider("deepseek", ("DeepSeek", "DeepSeek 深度求索"), "https://api.deepseek.com",
             "deepseek-flash", "https://platform.deepseek.com/api_keys"),
    Provider("siliconflow", ("SiliconFlow", "硅基流动 SiliconFlow"), "https://api.siliconflow.cn/v1",
             "deepseek-ai/DeepSeek-V3.2", "https://cloud.siliconflow.cn/account/ak"),
    Provider("bailian", ("Alibaba Bailian / Qwen", "阿里云百炼（通义千问）"),
             "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus",
             "https://bailian.console.aliyun.com/",
             ("Outside mainland China use https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
              "中国大陆以外地区请使用 https://dashscope-intl.aliyuncs.com/compatible-mode/v1")),
    Provider("zhipu", ("Zhipu GLM", "智谱 GLM"), "https://open.bigmodel.cn/api/paas/v4",
             "glm-4.7-flash", "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
             ("glm-4.7-flash is free to use.", "glm-4.7-flash 可免费使用。")),
    Provider("moonshot", ("Moonshot / Kimi", "月之暗面 Kimi"), "https://api.moonshot.cn/v1",
             "kimi-k2.6", "https://platform.kimi.com/console/api-keys"),
    Provider("ark", ("Volcengine Ark / Doubao", "火山方舟（豆包）"),
             "https://ark.cn-beijing.volces.com/api/v3", "doubao-seed-2-1-lite-260915",
             "https://console.volcengine.com/ark/region:ark+cn-beijing/apikey",
             ("Enable the model in the Ark console first.", "请先在方舟控制台的「开通管理」中开通该模型。")),
    Provider("openai", ("OpenAI", "OpenAI"), "https://api.openai.com/v1", "gpt-6-luna",
             "https://platform.openai.com/api-keys"),
    Provider("gemini", ("Google Gemini", "Google Gemini"),
             "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.8-flash",
             "https://aistudio.google.com/apikey"),
    Provider("ollama", ("Ollama (on this computer)", "Ollama（本机运行）"),
             "http://localhost:11434/v1", "qwen3", ""),
    Provider("other", ("Other OpenAI-compatible service", "其他兼容 OpenAI 的服务"), "", "", ""),
)
PROVIDER_KEYS = tuple(p.key for p in PROVIDERS)


def provider_named(key: str) -> Provider:
    for provider in PROVIDERS:
        if provider.key == key:
            return provider
    raise ValueError(f"unknown provider {key!r}; one of {', '.join(PROVIDER_KEYS)}")


def _same_url(a: str, b: str) -> bool:
    return bool(a) and a.strip().rstrip("/").lower() == b.strip().rstrip("/").lower()


def provider_for_base(base_url: str) -> Provider | None:
    """The preset serving `base_url`, also when it was written without /v1."""
    base_url = base_url.strip().rstrip("/")
    for provider in PROVIDERS:
        if provider.base_url and (
                _same_url(base_url, provider.base_url)
                or _same_url(base_url + "/v1", provider.base_url)
                or _same_url(base_url, provider.base_url + "/v1")):
            return provider
    return None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def _read_secret(prompt: str) -> str:
    """getpass in a terminal; a plain read otherwise (tests, IDE consoles)."""
    if langs.interactive():
        return getpass.getpass(prompt)
    return input(prompt)


def ask(prompt: str, default: str = "", required: bool = False,
        shown_default: str | None = None, secret: bool = False) -> str:
    """One answer; Enter takes `default`, shown as `shown_default` when given."""
    shown = default if shown_default is None else shown_default
    suffix = f" [{shown}]" if shown else ""
    while True:
        line = f"  {prompt}{suffix}: "
        answer = (_read_secret(line) if secret else input(line)).strip()
        if not answer:
            answer = default
        if answer or not required:
            return answer
        print(f"    {t('required')}")


# How "yes" starts in each language: y, 是, 好, はい, 네, 예, sí, sim, oui, ja, да.
_YES_INITIALS = frozenset("y是好は네예sojд")


def ask_yn(prompt: str, default_yes: bool = True) -> bool:
    answer = input(f"  {prompt} [{t('yes_no') if default_yes else t('no_yes')}]: ").strip().lower()
    if not answer:
        return default_yes
    return answer[0] in _YES_INITIALS


def ask_number(prompt: str, count: int, default: int | None = None) -> int:
    """A 1-based menu choice; with no default, an answer is required."""
    while True:
        raw = ask(prompt, default=str(default) if default else "", required=default is None)
        if raw.isdigit() and 1 <= int(raw) <= count:
            return int(raw)
        print(f"    {t('bad_number', n=count)}")


def mask_secret(value: str) -> str:
    """Enough of a key to recognise it, never enough to use it."""
    if len(value) >= 12:
        return f"{value[:3]}…{value[-4:]}"
    return "…"


def split_ids(raw: str) -> list[str]:
    return [x.strip() for x in str(raw or "").replace("，", ",").split(",") if x.strip()]


def _clean_ids(ids) -> list[str]:
    return [str(i).strip() for i in ids if str(i).strip()]


def ask_ids(label: str, current) -> list[str]:
    """A comma-separated id list; Enter keeps `current`, '-' empties it."""
    current = _clean_ids(current or [])
    hint = t("ids_keep") if current else t("ids_none")
    raw = ask(f"{label}（{hint}）" if langs.content(_lang) == "zh" else f"{label} ({hint})",
              default=",".join(current))
    return [] if raw.strip() == "-" else split_ids(raw)


def _say(text: str = "") -> None:
    print("\n".join(f"  {line}" if line else "" for line in text.split("\n")))


# ---------------------------------------------------------------------------
# .env
# ---------------------------------------------------------------------------

def env_literal(value) -> str:
    """`value` as one .env right-hand side that dotenv reads back unchanged.

    Single quotes keep it whole: a '#' after any whitespace would start a
    comment, and a line break of any kind (U+2028 included) must not let a
    value write a line of its own. dotenv expands ${VAR} even inside quotes,
    so callers taking values from outside refuse it."""
    text = str(value)
    if (text != text.strip() or text.startswith("#")
            or re.search(r"\s#", text)
            or any(ch in "\"'" or (ch.isspace() and ch != " ") or not ch.isprintable() and ch != " "
                   for ch in text)):
        return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return text


def set_env_values(env_text: str, values: dict) -> str:
    """`env_text` with every uncommented KEY= line of a key in `values`
    rewritten (dotenv reads the last one, so all of them); keys not present
    are appended. Comments and order are kept."""
    # Lines as dotenv splits them; str.splitlines also breaks at U+2028 and
    # friends, which would turn part of a quoted value into a line of its own.
    lines = re.split(r"\r\n|\n|\r", env_text) if env_text else []
    if lines and lines[-1] == "":
        lines.pop()
    found = set()
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if m and m.group(1) in values:
            key = m.group(1)
            lines[i] = f"{key}={env_literal(values[key])}"
            found.add(key)
    for key, value in values.items():
        if key not in found:
            lines.append(f"{key}={env_literal(value)}")
    out = "\n".join(lines)
    if env_text.endswith("\n") and not out.endswith("\n"):
        out += "\n"
    return out


def _replace(source, target) -> None:
    # Imported here: this module is read before any home is chosen.
    from persona_agent.storage import replace
    replace(source, target)


def write_env(env_path: Path, values: dict) -> None:
    """Merge `values` into .env through a 0600 temp file and an atomic replace,
    so an interrupted run never leaves a truncated or world-readable .env."""
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    updated = set_env_values(text, values)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = env_path.with_name(env_path.name + ".tmp")
    # The mode applies only when the file is created, so start fresh.
    tmp.unlink(missing_ok=True)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, SECRET_FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(updated)
    # Keep a stricter mode the operator chose, never a wider one.
    if env_path.exists():
        os.chmod(tmp, env_path.stat().st_mode & SECRET_FILE_MODE)
    _replace(tmp, env_path)


def secure_env_file(env_path: Path) -> None:
    """Narrow .env to its user (0600); a copy of the template starts at 0644."""
    os.chmod(env_path, SECRET_FILE_MODE)


def env_get(env_path: Path, key: str) -> str:
    """The value of `key` in .env exactly as the agent loads it ('' if blank or missing)."""
    if not env_path.exists():
        return ""
    from dotenv import dotenv_values

    return str(dotenv_values(env_path).get(key) or "").strip()


def copy_env_template(home: Path) -> Path:
    """<home>/.env, copied from the shipped template when missing, narrowed to 0600."""
    env_path = home / ".env"
    if not env_path.exists():
        home.mkdir(parents=True, exist_ok=True)
        template = homes.resource(".env.example")
        if template.is_file():
            shutil.copyfile(template, env_path)
        else:
            env_path.write_text("", encoding="utf-8")
    secure_env_file(env_path)
    return env_path


def configured_agent_home(env_path: Path) -> str:
    """AGENT_HOME as the agent will see it: the shell's, else the one in .env."""
    return os.environ.get("AGENT_HOME", "").strip() or env_get(env_path, "AGENT_HOME")


def warn_if_agent_home_diverges(env_path: Path, home: Path) -> None:
    """Flag an AGENT_HOME that sends the agent to another folder than this one."""
    configured = configured_agent_home(env_path)
    if not configured:
        return
    try:
        resolved = Path(configured).expanduser().resolve()
    except (OSError, RuntimeError):
        # expanduser() raises when no home directory can be determined.
        _say(t("home_unresolved", value=configured))
        return
    if resolved != home.resolve():
        _say(t("home_diverges", env=env_path, other=resolved))


# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Character:
    key: str
    title: tuple[str, str]
    # The character's own name, which a name nobody chose follows.
    name: str = ""

    @property
    def label(self) -> str:
        return langs.say(*self.title, _lang)


TEMPLATE = "template"
CHARACTERS: tuple[Character, ...] = (
    Character("dry-wit", ("Dry-witted friend: deadpan, short replies, teases lightly",
                          "冷面损友：冷幽默，回复简短，调侃适可而止")),
    Character("warm-listener", ("Warm listener: asks how you are, remembers the small things",
                                "温和的倾听者：关心你的近况，记得生活中的细节")),
    Character("gamer", ("Gamer: co-op shooters and roguelikes, friendly trash talk",
                        "游戏伙伴：喜爱合作射击和 Roguelike 游戏，常以玩笑互相调侃")),
    Character("bookworm", ("Bookworm: careful words, recommends books when asked",
                           "爱书人：措辞考究，仅在被问及时推荐书籍")),
    Character("chatgpt", ("The GPT dragon girl: proud, well-read, fond of treasure",
                          "GPT 娘（白龙）：骄傲自信，学识广博，喜爱财宝"), name="ChatGPT"),
    Character("deepseek", ("The DeepSeek whale girl: clever, a bit lazy, lives on white rice",
                           "DeepSeek 鲸鱼娘：聪明而略显懒散，言语讨喜，以白米饭为主食"), name="DeepSeek"),
    Character("claude", ("The Claude lady: well-bred, gentle and candid, strict house rules",
                         "Claude 娘（豪门圣女）：温柔端庄，坦诚直率，家规严格"), name="Claude"),
    Character(TEMPLATE, ("Write my own later: a plain starting character to edit",
                         "稍后自行编写：先使用一个基础角色，之后再修改")),
)
PERSONA_KEYS = tuple(c.key for c in CHARACTERS)
# The local page's portrait sprites, <key>.webp.
PORTRAITS = Path(__file__).with_name("static") / "characters"


def character_for(key: str) -> Character:
    return CHARACTERS[PERSONA_KEYS.index(key)]


def portrait(key: str) -> Path | None:
    """The portrait sprite of character `key`, when it ships one."""
    path = PORTRAITS / f"{key}.webp"
    return path if key in PERSONA_KEYS and path.is_file() else None


def avatar_for(key: str) -> str:
    """PERSONA_AVATAR for a persona written as character `key`."""
    return key if portrait(key) else ""


OWN_NAMES = frozenset(c.name for c in CHARACTERS if c.name)


def name_for(key: str, name: str, lang: str) -> str:
    """`name`, unless nobody chose it (the default, or a character's own):
    then character `key`'s own name, or the default when it has none."""
    if name == DEFAULT_NAMES[lang] or name in OWN_NAMES:
        return character_for(key).name or DEFAULT_NAMES[lang]
    return name

NAME_LINE = {"en": "Your name is {name}.", "zh": "你叫{name}。", "zh-TW": "你叫{name}。",
             "ja": "あなたの名前は{name}です。", "ko": "당신의 이름은 {name}입니다.",
             "es": "Te llamas {name}.", "fr": "Tu t'appelles {name}.",
             "de": "Du heißt {name}.", "pt-BR": "Seu nome é {name}.",
             "ru": "Тебя зовут {name}."}

# Earlier releases' templates, copied verbatim: still counted as unmodified.
_LEGACY_PERSONA_SHA256 = frozenset({
    "d5521d29275b4bbb8fe51190b02e03bca854df89698f44bab21996c72574601a",
    "e6194054243ae9d37feed2409c2a07906b072d1f61dd8f8eb9422503a93ff357",
    "46856227a6901dd3299b5a57b1d2b7d45075a0fba3aa545d58158c0b991d65b0",
    "85383ff3974a7c57ae6474ff482f342ad746457a3903367c0c8d30aebdb52bad",
    "c357d226d8daf47583942be31e70cbce77d6efb2a592dc78ae703f3934aebca2",
})


def _normal(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def persona_source(key: str, lang: str) -> Path:
    if key == TEMPLATE:
        return homes.resource("data", f"persona.example.{lang}.txt")
    return homes.resource("data", "personas", lang, f"{key}.txt")


def render_persona(text: str, *, name: str, lang: str, admin_name: str = "",
                   admin_relationship: str = "") -> str:
    """A persona document ready for the model, rendered as the agent renders
    it, plus a name line when the text never names the character."""
    out = render_persona_template(_normal(text), bot_name=name, admin_name=admin_name,
                                  admin_relationship=admin_relationship, lang=lang)
    if "{bot_name}" not in text:
        out = NAME_LINE.get(lang, NAME_LINE["en"]).format(name=name) + "\n" + out
    return out + "\n"


def shipped_persona(text: str) -> tuple[str, str, str] | None:
    """(key, lang, name) when `text` is a shipped character as this setup
    writes it, ('legacy', '', '') for an earlier release's template, or None
    when someone has edited it."""
    norm = _normal(text)
    if hashlib.sha256(norm.encode("utf-8")).hexdigest() in _LEGACY_PERSONA_SHA256:
        return ("legacy", "", "")
    for key, lang, raw, pattern in _shipped_shapes(str(homes.resource("data"))):
        if norm == raw:
            return (key, lang, "")
        found = pattern.fullmatch(norm)
        if found:
            return (key, lang, found.group(1))
    return None


@functools.lru_cache(maxsize=2)
def _shipped_shapes(data_dir: str) -> tuple:
    """Every shipped character under `data_dir` as (key, lang, its text, its
    text with a name slot). Read once: the local page asks on every poll."""
    sentinel = "\x00NAME\x00"
    shapes = []
    for lang in LANGS:
        for character in CHARACTERS:
            source = persona_source(character.key, lang)
            if not source.is_file():
                continue
            raw = source.read_text(encoding="utf-8")
            shape = _normal(render_persona(raw, name=sentinel, lang=lang))
            pattern = re.escape(shape).replace(re.escape(sentinel), r"(.+?)", 1)
            pattern = pattern.replace(re.escape(sentinel), r"\1")
            shapes.append((character.key, lang, _normal(raw), re.compile(pattern)))
    return tuple(shapes)


def short_label(character: Character) -> str:
    return re.split(r"[:：]", character.label, maxsplit=1)[0]


def persona_text(key: str, *, name: str, lang: str, admin_name: str = "",
                 admin_relationship: str = "") -> str:
    source = persona_source(key, lang)
    if not source.is_file():
        source = persona_source(key, "en")
    return render_persona(source.read_text(encoding="utf-8"), name=name, lang=lang,
                          admin_name=admin_name, admin_relationship=admin_relationship)


def default_character(origin: tuple[str, str, str] | None) -> str:
    """The menu default: the character persona.txt already is, else the first."""
    if origin and origin[0] in PERSONA_KEYS:
        return origin[0]
    return TEMPLATE if origin and origin[0] == "legacy" else CHARACTERS[0].key


def write_persona(home: Path, key: str, *, name: str, lang: str, admin_name: str = "",
                  admin_relationship: str = "") -> bool:
    """Write persona.txt as `key` for this name; False when it already is that."""
    text = persona_text(key, name=name, lang=lang, admin_name=admin_name,
                        admin_relationship=admin_relationship)
    path = home / "persona.txt"
    if path.is_file() and _normal(path.read_text(encoding="utf-8")) == _normal(text):
        return False
    home.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    _replace(tmp, path)
    return True


# ---------------------------------------------------------------------------
# Key probe
# ---------------------------------------------------------------------------

@dataclass
class Probe:
    url: str
    status: int          # 0 when nothing answered
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == 200


def _is_loopback(url: str) -> bool:
    return (urllib.parse.urlsplit(url).hostname or "").lower() in ("localhost", "127.0.0.1", "::1")


def _post(url: str, api_key: str, payload: dict, timeout: float) -> tuple[int, str]:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    # A loopback server (Ollama, a test server) must not go through a proxy.
    handlers = [urllib.request.ProxyHandler({})] if _is_loopback(url) else []
    opener = urllib.request.build_opener(*handlers)
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, ""
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")
        except OSError:
            body = ""
        return exc.code, " ".join(body.split())[:240]
    except (urllib.error.URLError, OSError, ValueError) as exc:
        reason = getattr(exc, "reason", exc)
        return 0, str(reason)[:240]


def probe_key(base_url: str, api_key: str, model: str, timeout: float = 30) -> Probe:
    """One tiny chat completion at the URL the agent will use."""
    url = completions_url(base_url)
    messages = [{"role": "user", "content": "Reply with OK."}]
    status, detail = _post(url, api_key, {"model": model, "max_tokens": 1,
                                          "messages": messages}, timeout)
    if status == 400 and "max_tokens" in detail:
        # Reasoning models refuse max_tokens; ask again without a limit.
        status, detail = _post(url, api_key, {"model": model, "messages": messages}, timeout)
    return Probe(url, status, detail)


def explain_probe(probe: Probe, provider: Provider | None) -> str:
    """A likely fix for a failed probe, in the current language."""
    status = probe.status
    key_url = provider.key_url if provider and provider.key_url else ""
    example = provider.base_url if provider and provider.base_url else "https://api.deepseek.com"
    if status in (401, 403):
        return t("fix_401") + ("\n" + t("key_page", url=key_url) if key_url else "")
    if status == 402:
        return t("fix_402")
    if status == 404:
        return t("fix_404", example=example)
    if status == 429:
        return t("fix_429") + ("\n" + t("fix_429_free") if provider and provider.key == "openrouter" else "")
    if status >= 500:
        return t("fix_5xx")
    if status == 0:
        host = urllib.parse.urlsplit(probe.url).hostname or probe.url
        text = t("fix_net", host=host, detail=probe.detail or "-")
        if provider and provider.key == "ollama":
            text += "\n" + t("fix_ollama")
        return text
    text = t("fix_400", detail=probe.detail or "-")
    if "balance" in probe.detail.lower() or "quota" in probe.detail.lower():
        text = t("fix_402") + "\n" + text
    return text


# ---------------------------------------------------------------------------
# AstrBot: finding it, the plugin, its config, the shared token
# ---------------------------------------------------------------------------

PLUGIN_NAME = "astrbot_plugin_personagent"
# The plugin's former name; left beside the new one it would forward every
# message a second time.
RETIRED_PLUGIN_NAME = "astrbot_plugin_llm_persona_gateway"
# The former config's keys that kept their names.
RETIRED_CONFIG_KEPT = ("excluded_platforms", "timeout_s", "block_default",
                       "forward_quoted_text", "quote_max_chars",
                       "max_inline_image_bytes", "outbox_enabled", "outbox_wait_s")
ASTRBOT_MAIN_CONFIG = "cmd_config.json"
# AstrBot's own variable for its root folder, not a personagent setting.
ASTRBOT_ROOT_VAR = "ASTRBOT_ROOT"


def plugin_source() -> Path:
    return homes.resource("integrations", "astrbot", PLUGIN_NAME)


def resolve_astrbot_data(path: Path) -> Path | None:
    """AstrBot's data folder for a path naming it, its root, or the folder
    holding an AstrBot/ checkout; recognised by cmd_config.json."""
    path = Path(path).expanduser()
    for cand in (path, path / "data", path / "AstrBot" / "data", path / "astrbot" / "data"):
        if (cand / ASTRBOT_MAIN_CONFIG).is_file():
            return cand
    return None


def astrbot_roots() -> list[Path]:
    """Where AstrBot keeps its root: ASTRBOT_ROOT, the desktop app's
    ~/.astrbot, or a folder its launcher, source checkout or `astrbot init` made."""
    user = Path.home()
    from persona_agent.astrbot_install import AstrBotInstallation

    roots = []
    configured = os.environ.get(ASTRBOT_ROOT_VAR, "").strip()
    if configured:
        roots.append(Path(configured).expanduser())
    roots.append(AstrBotInstallation(homes.find_home()).root)
    roots.append(user / ".astrbot")
    for base in (homes.find_home().parent, homes.CHECKOUT.parent, Path.cwd(), user,
                 user / "Desktop", user / "Documents"):
        roots += [base / "AstrBot", base / "astrbot"]
    roots.append(Path.cwd())
    return roots


def find_astrbot_data() -> Path | None:
    for root in astrbot_roots():
        try:
            found = resolve_astrbot_data(root)
        except OSError:
            continue
        if found:
            return found
    return None


def astrbot_in_docker(data_dir: Path) -> bool:
    """A compose file beside AstrBot's data folder means it runs in Docker."""
    names = ("compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml")
    return any((data_dir.parent / name).is_file() for name in names)


def install_astrbot_plugin(data_dir: Path) -> Path:
    """Copy the plugin into <data>/plugins/ (safe to repeat) and remove the
    plugin under its former name."""
    dest = data_dir / "plugins" / PLUGIN_NAME
    shutil.copytree(plugin_source(), dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    retired = data_dir / "plugins" / RETIRED_PLUGIN_NAME
    if retired.is_dir():
        shutil.rmtree(retired)
        _say(t("retired_removed", path=retired))
    return dest


def personagent_url_accepted(url: str, token: str) -> bool:
    """The plugin's own rule (its `_endpoint_is_allowed`): a loopback URL, or
    HTTPS elsewhere with a token."""
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if not host or parsed.scheme not in ("http", "https"):
        return False
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    return parsed.scheme == "https" and bool(token)


def _excluded_as_plugin_reads_it(value) -> list[str]:
    # The plugin iterates whatever is stored, so a string is a list of letters.
    return [str(p) for p in (value or [])]


def astrbot_qq_routed(cfg: dict) -> bool:
    """Whether a plugin config forwards QQ (aiocqhttp) to the agent."""
    return "aiocqhttp" not in _excluded_as_plugin_reads_it(cfg.get("excluded_platforms"))


def astrbot_plugin_config(existing: dict | None, *, personagent_url: str, token: str,
                          qq: bool | None, groups: list[str] | None,
                          dm_users: list[str] | None, url_override: str = "") -> dict:
    """The plugin's config document. None keeps the operator's value and other
    keys are kept, so re-running never undoes a setup."""
    cfg = dict(existing or {})
    if url_override:
        cfg["personagent_url"] = url_override
    # Only a URL the plugin would refuse is replaced; any other was chosen by
    # the operator, an SSH tunnel on another loopback port included.
    elif not personagent_url_accepted(str(cfg.get("personagent_url") or "").strip(), token):
        cfg["personagent_url"] = personagent_url
    cfg["connector_token"] = token
    if "excluded_platforms" not in cfg:
        cfg["excluded_platforms"] = [] if qq else ["aiocqhttp"]
    elif qq is not None:
        excluded = cfg["excluded_platforms"]
        excluded = (_clean_ids(excluded) if isinstance(excluded, list)
                    else split_ids(str(excluded or "")))
        excluded = [p for p in excluded if p != "aiocqhttp"]
        cfg["excluded_platforms"] = excluded if qq else excluded + ["aiocqhttp"]
    if groups is not None:
        cfg["groups"] = _clean_ids(groups)
    cfg.setdefault("groups", [])
    if dm_users is not None:
        cfg["dm_users"] = _clean_ids(dm_users)
    cfg.setdefault("dm_users", [])
    cfg.setdefault("timeout_s", 420)
    cfg.setdefault("block_default", True)
    return cfg


def astrbot_config_path(data_dir: Path) -> Path:
    return data_dir / "config" / f"{PLUGIN_NAME}_config.json"


def retired_astrbot_config_path(data_dir: Path) -> Path:
    return data_dir / "config" / f"{RETIRED_PLUGIN_NAME}_config.json"


def _write_json(path: Path, data: dict) -> Path:
    from persona_agent.storage import atomic_write_text

    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=4) + "\n")
    return path


def write_astrbot_config(data_dir: Path, cfg: dict) -> Path:
    return _write_json(astrbot_config_path(data_dir), cfg)


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))  # AstrBot writes a BOM
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def read_astrbot_config(data_dir: Path) -> dict:
    """The plugin's config; before its first run under the current name, the
    former config's keys that kept their names, so QQ routing carries over."""
    path = astrbot_config_path(data_dir)
    if path.exists():
        return _read_json(path)
    retired = _read_json(retired_astrbot_config_path(data_dir))
    return {k: retired[k] for k in RETIRED_CONFIG_KEPT if k in retired}


def connect_astrbot(env_path: Path, values: dict, *, data_dir: Path, qq: bool | None,
                    groups: list[str] | None, dm_users: list[str] | None,
                    url_override: str = "") -> Path:
    """Install the plugin and write both halves of the handshake: the shared
    token into `values` (for .env) and the plugin config into AstrBot.
    `qq`, `groups` and `dm_users` left as None keep their current values."""
    existing = read_astrbot_config(data_dir)
    plugin_token = str(existing.get("connector_token") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9._~+/=-]+", plugin_token):
        plugin_token = ""     # would not survive a round trip through .env
    token = (values.get("CONNECTOR_TOKEN") or env_get(env_path, "CONNECTOR_TOKEN")
             or plugin_token or secrets.token_urlsafe(32))
    values["CONNECTOR_TOKEN"] = token
    port = env_get(env_path, "SERVER_PORT") or "8080"
    local_url = f"http://127.0.0.1:{port}"
    install_astrbot_plugin(data_dir)
    cfg = astrbot_plugin_config(existing, personagent_url=local_url, token=token, qq=qq,
                                groups=groups, dm_users=dm_users, url_override=url_override)
    old_url = str(existing.get("personagent_url") or "").strip()
    if old_url and old_url != cfg["personagent_url"] and not url_override:
        _say(t("url_replaced", old=old_url, new=cfg["personagent_url"]))
    elif cfg["personagent_url"] != local_url and not url_override:
        _say(t("url_kept", url=cfg["personagent_url"], port=port))
    # .env follows the plugin: QQ forwarded without bare ids would file every
    # QQ conversation under a new name.
    current = env_get(env_path, "CONNECTOR_QQ_PLATFORMS")
    native = [p for p in _clean_ids(current.split(",")) if p != "aiocqhttp"]
    if astrbot_qq_routed(cfg):
        native = ["aiocqhttp"] + native
    if ",".join(native) != ",".join(_clean_ids(current.split(","))):
        values["CONNECTOR_QQ_PLATFORMS"] = ",".join(native)
    path = write_astrbot_config(data_dir, cfg)
    retired = retired_astrbot_config_path(data_dir)
    if retired.exists():
        retired.unlink()
        _say(t("retired_config", path=retired))
    return path


# The AstrBot adapters this setup can switch on: how a terminal, with no card
# around a field, asks for each field connections.py lists, in that order.
_PLATFORM_PROMPTS = {
    "qq_official": (("QQ bot AppID", "QQ 官方机器人 AppID"),
                    ("QQ bot AppSecret", "QQ 官方机器人 AppSecret")),
    "telegram": (("Telegram bot token (from @BotFather)",
                  "Telegram 机器人 token（通过 @BotFather 创建）"),),
    "discord": (("Discord bot token (Developer Portal > Bot)",
                 "Discord 机器人 token（Developer Portal > Bot）"),),
    "slack": (("Slack bot token (xoxb-...)", "Slack bot token（xoxb-...）"),
              ("Slack app-level token (xapp-..., Socket Mode)",
               "Slack app-level token（xapp-...，Socket Mode）")),
    "kook": (("KOOK bot token", "KOOK 机器人 token"),),
    "lark": (("Lark / Feishu app id", "飞书 / Lark App ID"),
             ("Lark / Feishu app secret", "飞书 / Lark App Secret")),
}
# kind -> ((field key, its prompt), ...)
PLATFORMS = {
    kind: tuple(zip((f.key for f in connections.platform(kind).fields), prompts, strict=True))
    for kind, prompts in _PLATFORM_PROMPTS.items()}
# The menu also lists QQ through NapCat, and names Lark before Feishu.
_OWN_LABELS = {"qq_official": ("QQ official bot", "QQ 官方机器人"),
               "lark": ("Lark / Feishu", "Lark / Feishu")}


def platform_label(kind: str) -> str:
    return langs.say(*(_OWN_LABELS.get(kind) or connections.platform(kind).name), _lang)


# AstrBot's own config shape (its 4.x template) around the credential fields.
_PLATFORM_DEFAULTS = {
    "qq_official": {"enable_group_c2c": True, "enable_guild_direct_message": True,
                    "use_markdown": True},
    "telegram": {"start_message": "", "telegram_api_base_url": "https://api.telegram.org/bot",
                 "telegram_file_base_url": "https://api.telegram.org/file/bot",
                 "telegram_command_register": False, "telegram_command_auto_refresh": False,
                 "telegram_command_register_interval": 300, "telegram_polling_restart_delay": 5.0},
    "discord": {"discord_proxy": "", "discord_command_register": False,
                "discord_activity_name": "", "discord_allow_bot_messages": False},
    "slack": {"signing_secret": "", "slack_connection_mode": "socket", "unified_webhook_mode": True,
              "webhook_uuid": "", "slack_webhook_host": "0.0.0.0", "slack_webhook_port": 6197,
              "slack_webhook_path": "/astrbot-slack-webhook/callback"},
    "kook": {"kook_reconnect_delay": 1, "kook_max_reconnect_delay": 60, "kook_max_retry_delay": 60,
             "kook_heartbeat_interval": 30, "kook_heartbeat_timeout": 6,
             "kook_max_heartbeat_failures": 3, "kook_max_consecutive_failures": 5},
    "lark": {"domain": "https://open.feishu.cn", "lark_connection_mode": "socket",
             "webhook_uuid": "", "lark_encrypt_key": "", "lark_verification_token": ""},
}


def astrbot_platform_entry(kind: str, creds: dict) -> dict:
    """One entry for AstrBot's `platform` list."""
    if kind not in PLATFORMS:
        raise ValueError(f"unknown platform {kind!r}; one of {', '.join(PLATFORMS)}")
    missing = [key for key, _ in PLATFORMS[kind] if not creds.get(key)]
    if missing:
        raise ValueError(f"{kind} needs {', '.join(missing)}")
    entry = {"id": kind, "type": kind, "enable": True}
    entry.update(_PLATFORM_DEFAULTS[kind])
    entry.update({key: creds[key] for key, _ in PLATFORMS[kind]})
    return entry


def astrbot_main_config_path(data_dir: Path) -> Path:
    return data_dir / ASTRBOT_MAIN_CONFIG


def write_astrbot_platform(data_dir: Path, entry: dict) -> Path:
    """Add an entry to AstrBot's cmd_config.json, which AstrBot reads when it
    starts. An entry with the same id keeps its other settings and gets the new credentials."""
    path = astrbot_main_config_path(data_dir)
    cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    platforms = cfg["platform"]
    for i, existing in enumerate(platforms):
        if existing.get("id") == entry["id"]:
            # Keep the user's own adapter settings (proxy, base URL, ...): only the credentials change.
            fields = ["enable"] + [key for key, _ in PLATFORMS.get(entry.get("type"), ())]
            same_kind = existing.get("type") == entry.get("type")
            platforms[i] = ({**existing, **{k: entry[k] for k in fields if k in entry}}
                            if same_kind else entry)
            break
    else:
        platforms.append(entry)
    return _write_json(path, cfg)


def flag_platform_creds(kind: str, token: str = "", app_token: str = "", app_id: str = "",
                        app_secret: str = "") -> dict:
    """The credential fields of `kind` from the command-line flags."""
    return {"qq_official": {"appid": app_id, "secret": app_secret},
            "telegram": {"telegram_token": token}, "discord": {"discord_token": token},
            "slack": {"bot_token": token, "app_token": app_token},
            "kook": {"kook_bot_token": token},
            "lark": {"app_id": app_id, "app_secret": app_secret}}.get(kind, {})


# ---------------------------------------------------------------------------
# How to run personagent on this machine
# ---------------------------------------------------------------------------

@dataclass
class Launcher:
    """The interpreter that has personagent's dependencies, and how to spell
    its commands for the person reading the next steps."""
    python: str
    home: Path

    @property
    def in_checkout(self) -> bool:
        return homes.is_checkout()

    def _home_args(self) -> list[str]:
        # A home other than the one a bare command finds needs saying.
        usual = homes.CHECKOUT if self.in_checkout else homes.default_home()
        if os.environ.get("AGENT_HOME", "").strip() or _resolved(self.home) != _resolved(usual):
            return ["--home", str(self.home)]
        return []

    def argv(self, sub: str) -> list[str]:
        return [self.python, "-m", "persona_agent", *self._home_args(), sub]

    def cwd(self) -> str | None:
        # `-m persona_agent` finds the package from a checkout's root.
        return str(homes.CHECKOUT) if self.in_checkout else None

    def shown(self, sub: str) -> list[str]:
        """The lines to type, ready to copy."""
        extra = " ".join(_quote(a) for a in self._home_args())
        tail = f"{extra} {sub}" if extra else sub
        if self.in_checkout:
            python = Path(self.python)
            try:
                python = python.relative_to(homes.CHECKOUT)
            except ValueError:
                pass
            return [f"cd {_quote(str(homes.CHECKOUT))}",
                    f"{_program(str(python))} -m persona_agent {tail}"]
        if langs.under_uvx():
            return [f"uvx personagent {tail}"]
        if shutil.which("personagent"):
            return [f"personagent {tail}"]
        return [f"{_program(self.python)} -m persona_agent {tail}"]


def command(sub: str, home: Path | None = None) -> str:
    """`sub` as this install spells it, on one line, for a hint inside a sentence."""
    return Launcher(python=sys.executable, home=home or homes.find_home()).shown(sub)[-1]


def _resolved(path: Path) -> Path:
    return Path(path).expanduser().resolve()


def _quote(text: str) -> str:
    return f'"{text}"' if " " in text else text


def _program(path: str) -> str:
    """`path` as the first word of a command; PowerShell needs `&` to run a quoted path."""
    if " " in path and os.name == "nt" and "PROMPT" not in os.environ:
        return f'& "{path}"'
    return _quote(path)


# ---------------------------------------------------------------------------
# The wizard
# ---------------------------------------------------------------------------

def _header(text: str) -> None:
    print()
    print(f"-- {text} " + "-" * max(4, 60 - langs.width(text)))


def ask_language(default: str) -> str:
    print()
    print("  Language / 语言")
    for i, code in enumerate(LANGS, 1):
        print(f"   {i:>2}. {langs.NAMES[code]}")
    choice = ask_number("Choose / 选择", len(LANGS), default=LANGS.index(default) + 1)
    return LANGS[choice - 1]


def _current(env_path: Path) -> dict:
    keys = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "PERSONA_NAME", "AGENT_LANG",
            "QQ_BOT_ID", "ADMIN_IDS", "ADMIN_NAME", "ADMIN_RELATIONSHIP",
            "ACCESS_GROUPS", "ACCESS_DM_USERS")
    return {key: env_get(env_path, key) for key in keys}


# `init`'s flags with none given: every question is asked.
_NO_FLAGS = argparse.Namespace(provider=None, base_url=None, model=None, key_env=None,
                               name=None, lang=None, persona=None)


def _from_flag(label: str, value: str, flag: str) -> None:
    """Say the answer a flag already gave, in place of asking its question."""
    _say(f"{label}: {value} ({flag})")


def _key_from_env(variable: str) -> str:
    """The key `--key-env` names; an empty variable is refused, never skipped."""
    key = os.environ.get(variable, "").strip()
    if not key:
        raise SystemExit(t("key_env_empty", name=variable))
    return key


def _require_scheme(base_url: str) -> None:
    if not has_scheme(base_url):
        raise SystemExit(langs.term("--base-url needs https:// or http:// in front, such as https://api.deepseek.com"))


def _ask_key(provider: Provider, current: dict, same: bool) -> str:
    visible = provider.needs_key and ask_yn(t("key_visible"), default_yes=False)
    if not provider.needs_key:
        return current["LLM_API_KEY"] if same and current["LLM_API_KEY"] else "ollama"
    if same and current["LLM_API_KEY"]:
        masked = mask_secret(current["LLM_API_KEY"])
        if visible:
            _say(t("key_current", value=current["LLM_API_KEY"]))
        api_key = ask(t("key_keep", masked=masked), default=current["LLM_API_KEY"],
                      shown_default="", secret=not visible)
    else:
        if provider.key_url:
            _say(t("key_where", url=provider.key_url))
        api_key = ask(t("key_prompt"), required=True, secret=not visible)
    _say(t("key_got", masked=mask_secret(api_key)))
    return api_key


def step_model(current: dict, retry: bool = False,
               flags: argparse.Namespace | None = None) -> dict:
    """Provider, model and key. A flag answers its own question; on a retry
    every question is asked, the Base URL too, with the last answers as defaults."""
    given = _NO_FLAGS if flags is None or retry else flags
    known = provider_for_base(current["LLM_BASE_URL"]) if current["LLM_BASE_URL"] else None
    if current["LLM_BASE_URL"] and known is None:
        known = provider_named("other")
    if current["LLM_API_KEY"] and not current["LLM_BASE_URL"]:
        known = provider_for_base(DEFAULT_LLM_BASE_URL)
    if given.provider:
        provider = provider_named(given.provider)
        _from_flag(t("provider_choose"), provider.label, "--provider")
    elif given.base_url:
        # The address says which service it is.
        provider = provider_for_base(given.base_url) or provider_named("other")
    else:
        if not retry:
            _say(t("provider_intro"))
        for i, provider in enumerate(PROVIDERS, 1):
            where = urllib.parse.urlsplit(provider.base_url).hostname or ""
            print(f"   {i:>2}. {provider.label}{' ' * max(1, 36 - langs.width(provider.label))}{where}")
        default = PROVIDERS.index(known) + 1 if known else 1
        provider = PROVIDERS[ask_number(t("provider_choose"), len(PROVIDERS), default) - 1]
    same = known is not None and known.key == provider.key
    if provider.hint:
        _say(provider.hint)

    # The same service keeps its address as written (a region, a proxy).
    base_url = current["LLM_BASE_URL"] if same and current["LLM_BASE_URL"] else provider.base_url
    if given.base_url:
        base_url = given.base_url
        _from_flag(t("base_url"), base_url, "--base-url")
    elif not base_url or retry:
        _say(t("base_url_explain"))
        base_url = ask(t("base_url"), default=base_url, required=True)
        while not has_scheme(base_url):
            _say(t("base_url_scheme"))
            base_url = ask(t("base_url"), required=True)
    if given.model:
        model = given.model
        _from_flag(t("model"), model, "--model")
    else:
        if provider.key == "ollama":
            _say(t("ollama_model"))
        elif not provider.model:
            _say(t("model_explain", example="deepseek-flash"))
        model = ask(t("model"), default=(current["LLM_MODEL"] if same and current["LLM_MODEL"]
                                         else provider.model), required=True)

    if given.key_env:
        api_key = _key_from_env(given.key_env)
        _say(f"{t('key_got', masked=mask_secret(api_key))} (--key-env {given.key_env})")
    else:
        api_key = _ask_key(provider, current, same)
    return {"LLM_BASE_URL": base_url, "LLM_MODEL": model, "LLM_API_KEY": api_key,
            "_provider": provider.key}


def check_key(values: dict) -> bool:
    provider = provider_named(values["_provider"])
    probe_url = completions_url(values["LLM_BASE_URL"])
    _say(t("testing", url=probe_url))
    probe = probe_key(values["LLM_BASE_URL"], values["LLM_API_KEY"], values["LLM_MODEL"])
    if probe.ok:
        _say("  " + t("test_ok"))
        return True
    what = f"HTTP {probe.status}" if probe.status else t("test_unreachable")
    _say("  " + t("test_failed", what=what))
    for line in explain_probe(probe, provider).split("\n"):
        _say("  " + line)
    return False


def step_character(home: Path, current: dict, lang: str,
                   flags: argparse.Namespace | None = None) -> tuple[str, str]:
    """The bot's name and which persona to write ('' = leave persona.txt alone).
    --name and --persona answer their own questions."""
    given = _NO_FLAGS if flags is None else flags
    old = current["PERSONA_NAME"]
    if given.name:
        name = given.name
        _from_flag(t("name"), name, "--name")
    else:
        _say(t("name_explain"))
        name = ask(t("name"), default=old or DEFAULT_NAMES[lang], required=True)

    persona_path = home / "persona.txt"
    origin = shipped_persona(persona_path.read_text(encoding="utf-8")) if persona_path.is_file() else None
    key = ""
    if persona_path.is_file() and origin is None:
        _say(t("char_custom"))
    else:
        if given.persona:
            key = given.persona
            _from_flag(t("char_choose"), short_label(character_for(key)), "--persona")
        else:
            print()
            _say(t("char_intro"))
            for i, character in enumerate(CHARACTERS, 1):
                print(f"    {i}. {character.label}")
            default = PERSONA_KEYS.index(default_character(origin)) + 1
            prompt = t("char_keep") if origin and origin[0] in PERSONA_KEYS else t("char_choose")
            key = CHARACTERS[ask_number(prompt, len(CHARACTERS), default=default) - 1].key
        # A name given as a flag stays, as it does with --no-input.
        if not given.name and name_for(key, name, lang) != name:
            name = name_for(key, name, lang)
            _say(t("name_follows", name=name))
    if old and name != old:
        _say(t("renamed", old=old))
    return name, key


PLATFORM_MENU = ("qq", "telegram", "discord", "slack", "kook", "lark", "other")


def _platform_label(kind: str) -> str:
    if kind == "qq":
        return t("qq_via")
    if kind == "other":
        return t("platform_other")
    return platform_label(kind)


def _entries_on(ids: list[str], platform: str) -> list[str]:
    """Entries of an identity list on one platform (QQ's are bare or qq:)."""
    if platform == "qq":
        return [i for i in ids if ":" not in i or i.startswith("qq:")]
    return [i for i in ids if i.startswith(platform + ":")]


def _raw_id(entry: str) -> str:
    return entry.split(":", 1)[1] if ":" in entry else entry


def _install_astrbot(home: Path) -> Path:
    from persona_agent.astrbot_install import AstrBotInstallation, install_astrbot

    _say(t("astrbot_installing", path=AstrBotInstallation(home).root))
    return install_astrbot(home)


def _astrbot_start_steps(launcher: Launcher, data_dir: Path) -> None:
    from persona_agent.astrbot_install import AstrBotInstallation

    managed = AstrBotInstallation(launcher.home).root / "data"
    if _resolved(data_dir) == _resolved(managed):
        _say(t("astrbot_start"))
        for line in launcher.shown("connect astrbot --start"):
            _say(f"     {line}")
    else:
        _say(t("next_restart"))


def step_astrbot(env_path: Path, current: dict, values: dict, *,
                 standalone: bool = False) -> dict | None:
    """Connect to AstrBot. Writes the plugin and its config; returns what the
    next steps need, or None when skipped. `standalone`: asked on its own, not
    as the setup's third step."""
    home = env_path.parent
    if standalone:
        _say(t("astrbot_menu_intro"))
        if not ask_yn(t("astrbot_menu_q"), default_yes=True):
            _say(t("astrbot_menu_skipped"))
            return None
    else:
        _say(t("connect_intro", cmd=command("connect", home)))
        if not ask_yn(t("connect_q"), default_yes=False):
            return None
    guess = find_astrbot_data()
    data_dir = None
    if guess is None and ask_yn(t("astrbot_install_q"), default_yes=True):
        try:
            data_dir = _install_astrbot(home)
        except (OSError, subprocess.CalledProcessError) as exc:
            _say(t("astrbot_install_failed", error=exc, cmd=command("connect astrbot --install", home)))
            return None
    if data_dir is None:
        _say(t("astrbot_explain"))
        while True:
            raw = ask(t("astrbot_dir"), default=str(guess) if guess else "", required=True)
            data_dir = resolve_astrbot_data(Path(raw))
            if data_dir:
                break
            _say(t("astrbot_bad", path=Path(raw).expanduser()))
    existing = read_astrbot_config(data_dir)

    url_override = ""
    port = env_get(env_path, "SERVER_PORT") or "8080"
    local_url = f"http://127.0.0.1:{port}"
    docker = ask_yn(t("docker_q"), default_yes=astrbot_in_docker(data_dir))
    if docker:
        for line in t("docker_fix", url=local_url).split("\n"):
            _say(line)
        chosen = str(existing.get("personagent_url") or "")
        while True:
            url = ask(t("docker_url", url=local_url),
                      default=chosen if chosen.startswith("https://") else "")
            if not url or personagent_url_accepted(url, "token"):
                url_override = url
                break
            _say(t("url_refused"))

    print()
    _say(t("platform_intro"))
    for i, kind in enumerate(PLATFORM_MENU, 1):
        print(f"    {i}. {_platform_label(kind)}")
    # No default on a first connection: QQ is one choice among several.
    default = None
    if existing:
        default = 1 if astrbot_qq_routed(existing) else len(PLATFORM_MENU)
    kind = PLATFORM_MENU[ask_number(t("platform_choose"), len(PLATFORM_MENU), default) - 1]

    admins_all = split_ids(current["ADMIN_IDS"])
    access_groups = split_ids(current["ACCESS_GROUPS"])
    access_dms = split_ids(current["ACCESS_DM_USERS"])
    qq = True if kind == "qq" else None
    creds: dict = {}
    if kind == "qq":
        values["QQ_BOT_ID"] = ask(t("qq_id"), default=current["QQ_BOT_ID"], required=True)
        groups = ask_ids(t("qq_groups"), existing.get("groups"))
        _say(t("admin_explain"))
        mine = _entries_on(admins_all, "qq")
        admin = ask(t("admin_qq"), default=_raw_id(mine[0]) if mine else "")
        if admin.startswith("qq:"):
            admin = admin[3:]
    else:
        if kind in PLATFORMS:
            _say(t("token_skip"))
            secret = {f.key: f.secret for f in connections.platform(kind).fields}
            for key, prompts in PLATFORMS[kind]:
                creds[key] = ask(langs.say(*prompts, _lang), secret=secret[key])
            if not all(creds.values()):
                creds = {}
        groups = ask_ids(t("groups_other"), existing.get("groups"))
        _say(t("admin_explain"))
        if kind == "other":
            mine = []
            admin = ask(t("admin_any"))
            while admin and ":" not in admin and not admin.isdigit():
                admin = ask(t("admin_any"))
        else:
            mine = _entries_on(admins_all, kind)
            admin = ask(t("admin_other", platform=platform_label(kind)),
                        default=_raw_id(mine[0]) if mine else "")
            if admin and not admin.startswith(kind + ":"):
                admin = f"{kind}:{admin}"
    admins = [a for a in admins_all if a not in mine] + ([admin] if admin else [])
    values["ADMIN_IDS"] = ",".join(admins)
    if admin:
        values["ADMIN_NAME"] = ask(t("admin_name"), default=current["ADMIN_NAME"], required=True)
    current_dms = [d for d in _clean_ids(existing.get("dm_users") or [])
                   if not admin or d != _raw_id(admin)]
    dm_others = ask_ids(t("dm_users"), current_dms)
    dm_users = list(dict.fromkeys(dm_others + ([_raw_id(admin)] if admin else [])))
    if kind == "qq":
        # QQ entries follow this answer; other platforms' entries are kept.
        others = [g for g in access_groups if ":" in g and not g.startswith("qq:")]
        values["ACCESS_GROUPS"] = ",".join(others + [g for g in groups if g.isdigit()])
        others = [d for d in access_dms if ":" in d and not d.startswith("qq:")]
        values["ACCESS_DM_USERS"] = ",".join(others + [d for d in dm_others if d.isdigit()])

    try:
        cfg_path = connect_astrbot(env_path, values, data_dir=data_dir, qq=qq, groups=groups,
                                   dm_users=dm_users, url_override=url_override)
        # Written now, so an interrupted run cannot leave the plugin forwarding
        # QQ to an agent that does not expect it.
        write_env(env_path, {k: v for k, v in values.items() if not k.startswith("_")})
        _say(t("plugin_installed", path=data_dir / "plugins" / PLUGIN_NAME))
        _say(t("plugin_config", path=cfg_path))
        if creds and kind in PLATFORMS:
            write_astrbot_platform(data_dir, astrbot_platform_entry(kind, creds))
            _say(t("platform_written", kind=platform_label(kind)))
    except OSError as exc:
        _say(t("write_failed", path=data_dir, error=exc))
        return None
    return {"kind": kind, "docker": docker, "data_dir": data_dir}


def finish(launcher: Launcher, home: Path, *, name: str, has_key: bool,
           astrbot: dict | None, offer_chat: bool) -> None:
    _header(t("done"))
    _say(t("next"))
    n = 1
    if not has_key:
        _say(f"{n}. " + t("next_key", path=home / ".env"))
        n += 1
    if astrbot:
        _say(f"{n}. " + t("next_run"))
        for line in launcher.shown("run"):
            _say(f"     {line}")
        n += 1
        _say(f"{n}.")
        _astrbot_start_steps(launcher, astrbot["data_dir"])
        n += 1
        if astrbot["kind"] == "qq":
            _say(f"{n}. " + t("next_qq"))
            n += 1
        _say(f"{n}. " + t("next_say", name=name))
        n += 1
    _say(f"{n}. " + t("next_platform"))
    for line in launcher.shown("connect"):
        _say(f"     {line}")
    n += 1
    _say(f"{n}. " + t("next_demo"))
    for line in launcher.shown("demo"):
        _say(f"     {line}")
    n += 1
    _say(f"{n}. " + t("next_chat", name=name))
    for line in launcher.shown("chat"):
        _say(f"     {line}")
    _say(t("next_persona", path=home / "persona.txt", name=name))
    if offer_chat and has_key and ask_yn(t("chat_now"), default_yes=astrbot is None):
        print()
        subprocess.call(launcher.argv("chat"), cwd=launcher.cwd())


def run_wizard(home: Path, launcher: Launcher, *,
               flags: argparse.Namespace | None = None) -> None:
    """The interactive setup. Answers are written to <home>/.env and persona.txt.
    A question `init`'s flags already answered is not asked: its answer is shown."""
    flags = _NO_FLAGS if flags is None else flags
    set_lang(flags.lang or os.environ.get("AGENT_LANG", "") or env_get(home / ".env", "AGENT_LANG") or detect_lang())
    # Refused before the first question, not after the last.
    if flags.base_url:
        _require_scheme(flags.base_url)
    if flags.key_env:
        _key_from_env(flags.key_env)
    env_path = copy_env_template(home)
    rerun = bool(env_get(env_path, "LLM_API_KEY"))
    current = _current(env_path) if rerun else {k: "" for k in _current(env_path)}
    current_lang = langs.normalize(current["AGENT_LANG"]) if rerun else ""
    if flags.lang:
        lang = flags.lang
        print()
        _from_flag("Language / 语言", langs.NAMES[lang], "--lang")
    else:
        # The start menu passes the language it is already shown in.
        lang = ask_language(current_lang or langs.normalize(os.environ.get("AGENT_LANG")) or detect_lang())
    set_lang(lang)
    _header(t("title_again") if rerun else t("title_first"))
    _say(t("folder", path=home))
    _say(t("enter_hint"))
    warn_if_agent_home_diverges(env_path, home)
    if current_lang and langs.content(lang) != langs.content(current_lang):
        _say(t("lang_switched", lang=langs.NAMES[langs.content(lang)]))

    _header(t("step", n=1, what=t("step_model")))
    retry = False
    while True:
        values = step_model(current, retry=retry, flags=flags)
        if check_key(values):
            break
        if not ask_yn(t("retry"), default_yes=True):
            _say(t("kept_anyway"))
            break
        current = {**current, **{k: v for k, v in values.items() if not k.startswith("_")}}
        retry = True
    write_env(env_path, {"LLM_BASE_URL": values["LLM_BASE_URL"],
                         "LLM_MODEL": values["LLM_MODEL"],
                         "LLM_API_KEY": values["LLM_API_KEY"], "AGENT_LANG": lang})

    _header(t("step", n=2, what=t("step_character")))
    name, persona = step_character(home, current, lang, flags)
    write_env(env_path, {"PERSONA_NAME": name})

    _header(t("step", n=3, what=t("step_chat")))
    answers: dict = {}
    astrbot = step_astrbot(env_path, current, answers)
    if persona:
        admin_name = answers.get("ADMIN_NAME", current["ADMIN_NAME"])
        write_persona(home, persona, name=name, lang=lang, admin_name=admin_name,
                      admin_relationship=current["ADMIN_RELATIONSHIP"])
        write_env(env_path, {"PERSONA_AVATAR": avatar_for(persona)})
        _say(t("persona_written", what=short_label(character_for(persona))))
    finish(launcher, home, name=name, has_key=True, astrbot=astrbot, offer_chat=True)


# ---------------------------------------------------------------------------
# Without questions
# ---------------------------------------------------------------------------

def apply_flags(home: Path, args: argparse.Namespace) -> str:
    """Write the templates and flags; returns the bot's name. An unedited
    shipped persona.txt follows the flags; an edited one is never touched."""
    if args.provider == "other" and not args.base_url:
        raise SystemExit(langs.term("--provider other needs --base-url"))
    if args.base_url:
        _require_scheme(args.base_url)
    existed = (home / ".env").exists()
    lang = langs.normalize(args.lang or os.environ.get("AGENT_LANG", "").strip()
                           or env_get(home / ".env", "AGENT_LANG")
                           or detect_lang()) or "en"
    set_lang(lang)
    # Refused before anything is written, as the questions do.
    api_key = _key_from_env(args.key_env) if args.key_env else ""
    # A key does not say whose it is, and a key alone used to mean DeepSeek.
    if (os.environ.get(args.key_env or "LLM_API_KEY", "").strip()
            and not (existed or args.provider or args.base_url)):
        raise SystemExit(langs.term("Which service is this key for? Add --provider, such as --provider openrouter"))
    env_path = copy_env_template(home)
    values: dict = {"AGENT_LANG": lang}
    keyless = False
    if args.provider and args.provider != "other":
        provider = provider_named(args.provider)
        values["LLM_BASE_URL"] = provider.base_url
        values["LLM_MODEL"] = provider.model
        keyless = not provider.needs_key
        if keyless and not env_get(env_path, "LLM_API_KEY"):
            values["LLM_API_KEY"] = "ollama"
    if args.base_url:
        values["LLM_BASE_URL"] = args.base_url
    old_url = (env_get(env_path, "LLM_BASE_URL")
               or (DEFAULT_LLM_BASE_URL if env_get(env_path, "LLM_API_KEY") else "")).rstrip("/")
    new_url = str(values.get("LLM_BASE_URL", old_url)).rstrip("/")
    if (existed and old_url and new_url != old_url and not args.key_env
            and env_get(env_path, "LLM_API_KEY") and "LLM_API_KEY" not in values):
        # The saved key belongs to the service being replaced; never send it to the new one.
        values["LLM_API_KEY"] = "ollama" if keyless else ""
        if not keyless:
            print(t("key_cleared"))
    if args.model:
        values["LLM_MODEL"] = args.model
    if args.key_env:
        values["LLM_API_KEY"] = api_key
    persona_path = home / "persona.txt"
    origin = (shipped_persona(persona_path.read_text(encoding="utf-8"))
              if persona_path.is_file() else ("", "", ""))
    key = ""
    if origin is not None:
        key = args.persona or (default_character(origin) if origin[0] else TEMPLATE)
        values["PERSONA_AVATAR"] = avatar_for(key)
    saved = env_get(env_path, "PERSONA_NAME")
    if args.name:
        name = args.name
    elif saved:
        # A saved name stays, unless it is only the last character's own.
        name = name_for(key, saved, lang) if key and saved in OWN_NAMES else saved
    else:
        name = (character_for(key).name if key else "") or DEFAULT_NAMES[lang]
    values["PERSONA_NAME"] = name
    write_env(env_path, values)
    if key:
        write_persona(home, key, name=name, lang=lang,
                      admin_name=env_get(env_path, "ADMIN_NAME"),
                      admin_relationship=env_get(env_path, "ADMIN_RELATIONSHIP"))
    return name


def setup_without_questions(home: Path, args: argparse.Namespace, launcher: Launcher) -> int:
    """`init --no-input`: templates in place, flags applied, nothing asked."""
    name = apply_flags(home, args)
    print(t("saved", path=home))
    env_path = home / ".env"
    finish(launcher, home, name=name, has_key=bool(env_get(env_path, "LLM_API_KEY")),
           astrbot=None, offer_chat=False)
    return 0


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def init_parser(prog: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=prog,
        description=langs.term("Set up personagent: the AI service, the character, and "
                    "optionally AstrBot. In a terminal it opens the welcome page; --terminal asks "
                    "the questions here instead, and --no-input uses only the flags below."))
    p.add_argument("--no-input", action="store_true",
                   help=langs.term("ask nothing; use the flags below and keep everything else"))
    p.add_argument("--terminal", action="store_true", help=langs.term("use the terminal setup wizard instead of the welcome page"))
    p.add_argument("--provider", choices=PROVIDER_KEYS, help=langs.term("an AI service preset"))
    p.add_argument("--base-url", help=langs.term("the service's API address (needed with --provider other)"))
    p.add_argument("--model", help=langs.term("the model id (default: the preset's)"))
    p.add_argument("--key-env", metavar="VAR",
                   help=langs.term("read the API key from this environment variable"))
    p.add_argument("--name", help=langs.term("the bot's name (default: one in the chosen language)"))
    p.add_argument("--lang", choices=LANGS, help=langs.term("the language (default: the system's)"))
    p.add_argument("--persona", choices=PERSONA_KEYS,
                   help=langs.term("a ready character for persona.txt (written only while it is unedited)"))
    return p


def run(argv: list[str] | None, prog: str) -> int:
    args = init_parser(prog).parse_args(argv)
    home = homes.find_home()
    launcher = Launcher(python=sys.executable, home=home)
    tty = langs.interactive()
    flagged = any((args.provider, args.base_url, args.model, args.key_env,
                   args.name, args.lang, args.persona))
    if tty and not args.no_input and not getattr(args, "terminal", False) and not flagged:
        from persona_agent.welcome import main as welcome_main
        return welcome_main([], prog)
    if args.no_input or not tty:
        if args.no_input:
            return setup_without_questions(home, args, launcher)
        again = launcher.shown("init --terminal" if getattr(args, "terminal", False) else "init")[-1]
        if flagged:
            set_lang(args.lang or detect_lang())
            print(t("skipped", why=t("skip_tty"), cmd=again))
            return setup_without_questions(home, args, launcher)
        # Piped without flags: nothing is written, no "Setup complete", and a script must be able to tell.
        set_lang(langs.terminal_lang())
        print(t("skipped", why=t("skip_tty"), cmd=again))
        return 2
    run_wizard(home, launcher, flags=args)
    return 0


def main(argv: list[str] | None = None, prog: str = "personagent init") -> int:
    try:
        return run(argv, prog)
    except (KeyboardInterrupt, EOFError):
        print()
        return 130


CODING_TARGETS = ("claude-code", "codex", "dsh")
# The words typed after `personagent connect` for two catalog ids; the ids work too.
DIRECT_WORDS = {"qq_official": "qq", "weixin_oc": "wechat"}


def direct_targets() -> dict[str, str]:
    """What may follow `personagent connect` for each directly connected platform."""
    from persona_agent.direct import KINDS

    found = {DIRECT_WORDS.get(kind, kind): kind for kind in KINDS}
    found.update({kind: kind for kind in KINDS})
    return found


def _flag(key: str) -> str:
    return "--" + key.replace("_", "-")


def _shown(pair: tuple[str, str]) -> str:
    return connections.say(pair, _lang)


def _via_astrbot(home: Path) -> list[str]:
    from persona_agent.astrbot_install import AstrBotInstallation

    return connections.connected(AstrBotInstallation(home).root / "data")


def list_platforms(home: Path) -> int:
    """`personagent connect`: which platforms are connected and which can be."""
    from persona_agent import direct_setup

    from persona_agent.direct import KINDS

    saved, via = direct_setup.stored(home), _via_astrbot(home)
    words = {p.kind: DIRECT_WORDS.get(p.kind, p.kind) for p in connections.PLATFORMS if p.kind in KINDS}
    rows = [(word, _shown(connections.platform(kind).name),
             t("direct_on") if kind in saved else t("direct_via_astrbot") if kind in via else t("direct_off"))
            for kind, word in words.items()]
    print()
    _say(t("direct_list_title"))
    first = max(len(word) for word, _, _ in rows)
    second = max(langs.width(name) for _, name, _ in rows)
    for word, name, state in rows:
        _say(f"  {word:<{first}}  {name}{' ' * (second - langs.width(name))}  {state}")
    others = [kind for kind in via if kind not in words]
    if others:
        _say(t("direct_via_astrbot") + ": " + ", ".join(_shown(connections.platform(k).name) for k in others))
    print()
    _say(t("direct_list_how", cmd=command("connect", home)))
    _say(t("direct_list_more", cmd=command("connect", home)))
    return 0


def _ask_field(item: connections.Field) -> str | int:
    label = _shown(item.label)
    prompt = label if item.required else t("direct_optional", label=label)
    while True:
        raw = ask(prompt, default=item.default, required=item.required and not item.default,
                  secret=item.secret)
        try:
            return connections.clean_field(item, raw)
        except connections.FieldError as exc:
            _say("  " + t("direct_required" if str(exc) == "field_required" else "direct_invalid"))


def _direct_values(spec: connections.Platform, given: dict, asking: bool) -> dict | None:
    """Every field of `spec`: from its option, else asked, else its default;
    None, with each missing or refused value named, when one cannot be had."""
    values, problems = {}, []
    for item in spec.fields:
        label = _shown(item.label)
        if item.key in given:
            try:
                values[item.key] = connections.clean_field(item, given[item.key])
                continue
            except connections.FieldError as exc:
                if not asking or str(exc) != "field_required":
                    problems.append(t("direct_bad_flag", flag=_flag(item.key), label=label)
                                    if str(exc) == "invalid_field" else
                                    t("direct_missing", label=label, flag=_flag(item.key)))
                    continue
        if asking:
            values[item.key] = _ask_field(item)
            continue
        try:
            values[item.key] = connections.clean_field(item, "")
        except connections.FieldError:
            problems.append(t("direct_missing", label=label, flag=_flag(item.key)))
    sys.stdout.flush()
    for line in problems:
        print(line, file=sys.stderr)
    return None if problems else values


def _enable_ansi() -> bool:
    """Whether this console draws colour codes; Windows needs them switched on."""
    if not sys.stdout.isatty():
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, OSError):
        return False


def print_qr(content: str) -> None:
    """A QR code in the terminal: light on dark, which phones read in any theme
    once the colours are set; without colour codes, for a dark background."""
    import qrcode

    code = qrcode.QRCode(border=2)
    code.add_data(content)
    code.make(fit=True)
    sys.stdout.flush()
    try:
        "▀▄█".encode(sys.stdout.encoding or "ascii")
    except (UnicodeEncodeError, LookupError):
        # A legacy code page has no block characters: two plain ones per module.
        for row in code.get_matrix():
            print("".join("  " if dark else "##" for dark in row))
        return
    code.print_ascii(out=sys.stdout, tty=_enable_ansi(), invert=True)


def _shower(spec: connections.Platform, name: str, launcher: Launcher):
    """How the terminal shows what a sign-in asks to show."""
    def show(content: str) -> None:
        print()
        if spec.sign_in == "link":
            _say(t("direct_link", name=name))
            _say(f"  {content}")
            code = urllib.parse.parse_qs(urllib.parse.urlsplit(content).query).get("device-code", [""])[0]
            if code:
                _say(t("direct_code", code=code))
        else:
            _say(t("direct_scan_qq" if spec.kind == "qq_official" else "direct_scan_wechat"))
            print_qr(content)
            _say(t("direct_scan_address", url=content))
            _say(t("direct_scan_fallback", name=name))
            for line in launcher.shown("start"):
                _say(f"     {line}")
        _say(t("direct_waiting"))
        sys.stdout.flush()
    return show


def refusal(code: str, spec: connections.Platform, name: str) -> str:
    """Why a platform was not connected, in words."""
    short = spec.kind.split("_")[0]
    for key in (f"refused_{code}_{short}", f"refused_{code}", "refused_platform_rejected"):
        if key in _TEXT:
            return t(key, name=name)
    return t("refused_platform_rejected", name=name)


def _introduce(spec: connections.Platform, name: str, scan: bool) -> None:
    print()
    _header(name)
    if spec.note[0]:
        _say(_shown(spec.note))
    if spec.guide and not scan:
        _say(t("direct_guide", url=spec.guide))
    if spec.steps and not scan:
        print()
        _say(t("direct_steps"))
        for i, step in enumerate(spec.steps, 1):
            _say(f"  {i}. {_shown(step)}")
        _say(t("direct_steps_here", name=name))
    print()


def connect_platform(home: Path, kind: str, given: dict, *, remove: bool = False,
                     no_input: bool = False, launcher: Launcher | None = None) -> int:
    """`personagent connect <platform>`: what the page's Connect and
    Disconnect do, with the same checks and the same saved form."""
    from persona_agent import direct_setup
    from persona_agent.direct import base as direct_base

    spec = connections.platform(kind)
    name = _shown(spec.name)
    launcher = launcher or Launcher(python=sys.executable, home=home)
    try:
        if remove:
            if kind not in direct_setup.stored(home) and kind not in _via_astrbot(home):
                _say(t("direct_not_connected", name=name))
                return 0
            direct_setup.remove(home, spec)
            direct_setup.clear_state(home, kind)
            _say(t("direct_removed", name=name))
            _say(t("direct_restart"))
            return 0
        asking = not no_input and langs.interactive()
        scan = spec.group == connections.SCAN and not given
        if scan and no_input:
            # A scan waits for a phone, which --no-input promises never to do.
            print(t("direct_no_input_qq" if spec.fields else "direct_no_input_wechat"), file=sys.stderr)
            print(t("direct_nothing_saved"), file=sys.stderr)
            return 2
        if scan and spec.fields and asking:
            _say(t("direct_qq_ways"))
            scan = ask_number(t("direct_way"), 2, 1) == 1
        if asking or scan:
            _introduce(spec, name, scan)
        values: dict = {}
        if not scan:
            found = _direct_values(spec, given, asking)
            if found is None:
                print(t("direct_nothing_saved"), file=sys.stderr)
                return 2
            values = found
        try:
            if scan or spec.sign_in:
                values = direct_setup.sign_in(spec, values, _shower(spec, name, launcher))
            if not scan:
                _say(t("direct_checking", name=name))
                direct_setup.check(home, spec, values)
        except RuntimeError as exc:
            sys.stdout.flush()
            print(t("direct_failed", name=name), file=sys.stderr)
            print(refusal(str(exc), spec, name), file=sys.stderr)
            return 1
        except Exception as exc:
            # Only the error's type: its message may quote a credential.
            sys.stdout.flush()
            print(t("direct_failed", name=name), file=sys.stderr)
            print(t("direct_unexpected", error=type(exc).__name__), file=sys.stderr)
            return 1
        released = direct_setup.store(home, spec, values)
        direct_setup.clear_state(home, kind)
    except (KeyboardInterrupt, EOFError):
        print()
        _say(t("direct_stopped"))
        return 130
    except OSError as exc:
        print(t("write_failed", path=home, error=exc), file=sys.stderr)
        return 1
    print()
    _say(t("direct_saved", name=name, path=direct_base.credentials_path(home)))
    if released:
        _say(t("direct_released", name=name))
    if not env_get(home / ".env", "LLM_API_KEY"):
        _say(t("direct_no_key"))
        for line in launcher.shown("init --terminal"):
            _say(f"     {line}")
    _say(t("direct_next", log=home / "runtime" / "desktop" / "direct.log"))
    for line in launcher.shown("up"):
        _say(f"     {line}")
    return 0


def connect_parser(prog: str) -> argparse.ArgumentParser:
    from persona_agent.direct import KINDS

    p = argparse.ArgumentParser(
        prog=prog, description=langs.term("Connect a chat platform that personagent connects itself, "
                               "such as telegram, discord, matrix, twitch, irc, zulip, vk, stoat, qq or "
                               "wechat; without a target, list them. Or connect AstrBot: copy the plugin, "
                               "share a token, write the allowlists; with DATA_DIR nothing is asked. Or put "
                               "the character into a coding agent: claude-code, codex or dsh (DeepSeek "
                               "Harness)."),
        epilog=langs.term("AstrBot in Docker cannot reach 127.0.0.1 on this machine: give it host "
               "networking, or put personagent behind HTTPS and pass that address as --url."))
    p.add_argument("target", nargs="?", metavar="TARGET",
                   help=langs.term("a chat platform, astrbot, claude-code, codex or dsh; "
                                   "omit it to list the chat platforms"))
    react = p.add_argument("--react", action="store_true",
                           help=langs.term("claude-code, codex: also let the character react when a turn ends; "
                                "sends the folder's name and the start of the coding agent's last message to your model service"))
    p.add_argument("--remove", action="store_true",
                   help=langs.term("a chat platform, claude-code, codex or dsh: disconnect it again"))
    p.add_argument("--no-input", action="store_true",
                   help=langs.term("a chat platform: ask nothing; give every required value as an option"))
    p.add_argument("--lang", choices=LANGS,
                   help=langs.term("the language of this command's messages (default: the saved one)"))
    values = p.add_argument_group(langs.term("values of a chat platform (asked in a terminal when not given)"))
    shown = langs.terminal_lang()
    for kind in KINDS:
        spec = connections.platform(kind)
        for item in spec.fields:
            label = f"{connections.say(spec.name, shown)}: {connections.say(item.label, shown)}"
            values.add_argument(_flag(item.key), dest=f"field_{item.key}", metavar="VALUE",
                                help=label.replace("%", "%%"))
    own = [react, p.add_argument("data_dir", nargs="?", metavar="DATA_DIR",
                                 help=langs.term("AstrBot's folder (its data folder or the one above it)"))]
    action = p.add_mutually_exclusive_group()
    own.append(action.add_argument("--install", action="store_true",
                                   help=langs.term("download and initialise AstrBot under this agent home, "
                                                   "then connect it")))
    own.append(action.add_argument("--start", action="store_true",
                                   help=langs.term("start the AstrBot installed under this agent home")))
    qq = p.add_mutually_exclusive_group()
    own.append(qq.add_argument("--qq", dest="qq", action="store_const", const=True,
                               help=langs.term("route QQ through AstrBot too")))
    own.append(qq.add_argument("--no-qq", dest="qq", action="store_const", const=False,
                               help=langs.term("stop routing QQ through AstrBot (without either, it is left as it is)")))
    own.append(p.add_argument("--platform", choices=tuple(PLATFORMS),
                              help=langs.term("also switch on this adapter in AstrBot's own config")))
    own.append(p.add_argument("--token", default="", help=langs.term("the adapter's bot token")))
    own.append(p.add_argument("--app-token", default="", help=langs.term("Slack's app-level token")))
    own.append(p.add_argument("--app-id", default="", help=langs.term("Lark / Feishu app id")))
    own.append(p.add_argument("--app-secret", default="", help=langs.term("Lark / Feishu app secret")))
    own.append(p.add_argument("--url", default="",
                              help=langs.term("the address the plugin posts to, such as an https:// one "
                                   "(default http://127.0.0.1:<SERVER_PORT>)")))
    # Read only for astrbot or a coding agent; a chat platform refuses them by name.
    p.set_defaults(not_for_platforms=tuple(own))
    return p


def _given(args: argparse.Namespace, actions) -> list[str]:
    """The options among `actions` that the command line set."""
    used = []
    for item in actions:
        value = getattr(args, item.dest)
        if value != item.default and (item.const is None or value == item.const):
            used.append(item.option_strings[0] if item.option_strings else item.metavar)
    return used


def connect_without_questions(home: Path, data_dir: Path, *, qq: bool | None,
                              platform: str = "", creds: dict | None = None,
                              url: str = "", launcher: Launcher | None = None) -> int:
    """`connect astrbot DATA_DIR`: the handshake from flags, nothing asked."""
    found = resolve_astrbot_data(data_dir)
    if found is None:
        raise SystemExit(t("astrbot_bad", path=Path(data_dir).expanduser()))
    env_path = copy_env_template(home)
    values: dict = {}
    token = env_get(env_path, "CONNECTOR_TOKEN") or "token"
    if url and not personagent_url_accepted(url, token):
        raise SystemExit(t("url_refused"))
    try:
        cfg_path = connect_astrbot(env_path, values, data_dir=found, qq=qq, groups=None,
                                   dm_users=None, url_override=url)
        write_env(env_path, values)
        if platform:
            try:
                entry = astrbot_platform_entry(platform, creds or {})
            except ValueError as exc:
                raise SystemExit(langs.term(f"platform not written: {exc}")) from None
            write_astrbot_platform(found, entry)
            print(t("platform_written", kind=platform_label(platform)))
    except OSError as exc:
        raise SystemExit(t("write_failed", path=found, error=exc)) from None
    print(t("plugin_installed", path=found / "plugins" / PLUGIN_NAME))
    print(t("plugin_config", path=cfg_path))
    cfg = read_astrbot_config(found)
    print(t("allowlists_kept") if cfg.get("groups") or cfg.get("dm_users")
          else t("allowlists_empty"))
    launcher = launcher or Launcher(python=sys.executable, home=home)
    print(t("next"))
    print("  1. " + t("next_run"))
    for line in launcher.shown("run"):
        print(f"       {line}")
    print("  2.")
    _astrbot_start_steps(launcher, found)
    return 0


def _lang_option(argv: list[str]) -> str:
    """The language `--lang` names, read before the help is built in it."""
    for i, word in enumerate(argv):
        if word == "--":
            break
        if word == "--lang" and i + 1 < len(argv):
            return langs.normalize(argv[i + 1])
        if word.startswith("--lang="):
            return langs.normalize(word.split("=", 1)[1])
    return ""


def connect_main(argv: list[str] | None = None, prog: str = "personagent connect") -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    chosen = _lang_option(argv)
    before = os.environ.get("AGENT_LANG")
    if chosen:
        os.environ["AGENT_LANG"] = chosen
    try:
        return _connect_main(argv, prog, chosen)
    finally:
        if chosen and before is None:
            os.environ.pop("AGENT_LANG", None)
        elif chosen:
            os.environ["AGENT_LANG"] = before


def _connect_main(argv: list[str], prog: str, chosen: str) -> int:
    args = connect_parser(prog).parse_args(argv)
    home = homes.find_home()
    env_path = home / ".env"
    set_lang(chosen or os.environ.get("AGENT_LANG", "") or env_get(env_path, "AGENT_LANG") or detect_lang())
    fields = {name[len("field_"):]: value for name, value in vars(args).items()
              if name.startswith("field_") and value is not None}
    kind = direct_targets().get(args.target or "")
    if args.target is None or kind:
        used = _given(args, args.not_for_platforms)
        if used:
            coding = [option for option in used if option == "--react"]
            astrbot = [option for option in used if option != "--react"]
            lines = ([f"{', '.join(astrbot)}: used only with astrbot, not with a chat platform"] if astrbot else []) + \
                    ([f"{', '.join(coding)}: used only with claude-code and codex, not with a chat platform"]
                     if coding else [])
            raise SystemExit("\n".join(langs.term(line) for line in lines))
    if args.target is None:
        if fields or args.remove or args.no_input:
            raise SystemExit(langs.term(f"Name the chat platform, for example: {command('connect telegram', home)}"))
        return list_platforms(home)
    if kind:
        own = {item.key for item in connections.platform(kind).fields}
        stray = [_flag(key) for key in fields if key not in own]
        if stray:
            raise SystemExit(langs.term(f"{', '.join(stray)}: not a value of the platform {args.target}"))
        if args.remove and fields:
            raise SystemExit(langs.term("--remove does not accept platform values"))
        return connect_platform(home, kind, fields, remove=args.remove, no_input=args.no_input)
    if args.target not in ("astrbot", *CODING_TARGETS):
        print(t("direct_unknown", name=args.target, cmd=command("connect", home)), file=sys.stderr)
        return 2
    if fields or args.no_input:
        raise SystemExit(langs.term("--no-input and the platform values apply only to the chat platforms"))
    if args.target != "astrbot":
        if args.data_dir:
            raise SystemExit(langs.term(f"{args.target} takes no folder"))
        from persona_agent import coding

        return coding.connect(home, args.target, react=args.react, remove=args.remove)
    if args.react or args.remove:
        raise SystemExit(langs.term("--react applies only to claude-code and codex, and --remove does not apply to astrbot"))
    if args.data_dir and (args.install or args.start):
        raise SystemExit(langs.term("--install and --start use the managed folder; omit DATA_DIR"))
    if args.start:
        if args.qq is not None or args.platform or args.url or any(
                (args.token, args.app_token, args.app_id, args.app_secret)):
            raise SystemExit(langs.term("--start cannot be combined with connection settings"))
        from persona_agent.astrbot_install import start_astrbot

        try:
            return start_astrbot(home)
        except OSError as exc:
            raise SystemExit(str(exc)) from None
    if args.install:
        # Validate adapter flags before a potentially large download.
        creds = flag_platform_creds(args.platform or "", args.token, args.app_token,
                                    args.app_id, args.app_secret)
        if args.platform:
            try:
                astrbot_platform_entry(args.platform, creds)
            except ValueError as exc:
                raise SystemExit(langs.term(f"platform not written: {exc}")) from None
        if args.url and not personagent_url_accepted(args.url, "token"):
            raise SystemExit(t("url_refused"))
        try:
            args.data_dir = str(_install_astrbot(home))
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SystemExit(t("astrbot_install_failed", error=exc,
                               cmd=command("connect astrbot --install", home))) from None
    if args.data_dir:
        creds = flag_platform_creds(args.platform or "", args.token, args.app_token,
                                    args.app_id, args.app_secret)
        return connect_without_questions(home, Path(args.data_dir), qq=args.qq,
                                         platform=args.platform or "", creds=creds,
                                         url=args.url)
    if args.qq is not None or args.platform or args.url:
        raise SystemExit(langs.term("--qq, --no-qq, --platform and --url need DATA_DIR"))
    if not langs.interactive():
        raise SystemExit(langs.term(f"{prog}: give AstrBot's folder (DATA_DIR), or run this in a terminal"))
    try:
        env_path = copy_env_template(home)
        answers: dict = {}
        astrbot = step_astrbot(env_path, _current(env_path), answers, standalone=True)
        if astrbot:
            launcher = Launcher(python=sys.executable, home=home)
            name = env_get(env_path, "PERSONA_NAME") or DEFAULT_NAMES.get(_lang, "Nova")
            finish(launcher, home, name=name, has_key=bool(env_get(env_path, "LLM_API_KEY")),
                   astrbot=astrbot, offer_chat=False)
    except (KeyboardInterrupt, EOFError):
        print()
        return 130
    return 0


def choose_platform() -> list[str]:
    """The menu's platform list; the `connect` command to run, or [] for back."""
    from persona_agent.direct import KINDS

    kinds = [p.kind for p in connections.PLATFORMS if p.kind in KINDS]
    print()
    _say(t("menu_platforms"))
    for i, kind in enumerate(kinds, 1):
        print(f"    {i}. {_shown(connections.platform(kind).name)}")
    print(f"    {len(kinds) + 1}. {t('menu_astrbot')}")
    print(f"    0. {t('menu_back')}")
    while True:
        choice = ask(t("menu_platform_choose", n=len(kinds) + 1), default="0")
        if choice == "0":
            return []
        if choice.isdigit() and 1 <= int(choice) <= len(kinds):
            return ["connect", DIRECT_WORDS.get(kinds[int(choice) - 1], kinds[int(choice) - 1])]
        if choice == str(len(kinds) + 1):
            return ["connect", "astrbot"]
        _say(t("menu_platform_bad", choice=choice, n=len(kinds) + 1))


def start_main(argv: list[str] | None = None, prog: str = "personagent start") -> int:
    """A small front door; each action runs in a fresh process to reload settings."""
    argparse.ArgumentParser(prog=prog, description=langs.term("Open the personagent start menu")).parse_args(argv)
    if not langs.interactive():
        print(langs.term(f"Open this menu in a terminal: {command('start --terminal')}"))
        return 2
    home = homes.find_home()
    launcher = Launcher(python=sys.executable, home=home)
    try:
        while True:
            env = home / ".env"
            set_lang(env_get(env, "AGENT_LANG") or os.getenv("AGENT_LANG") or detect_lang())
            # What the menu runs speaks the menu's language until setup saves one.
            child_env = {**os.environ, "AGENT_LANG": _lang}
            _header(t("start_title"))
            _say(t("folder", path=home))
            key = env_get(env, "LLM_API_KEY")
            _say(t("start_status", name=env_get(env, "PERSONA_NAME") or t("start_no_name"),
                   masked=mask_secret(key) if key else t("start_no_key")))
            _say(t("start_menu"))
            choice = ask(t("start_choose"), default="1")
            if choice == "0":
                return 0
            commands = {"1": ["chat"], "2": ["init", "--terminal"], "3": [],
                        "4": ["connect", "astrbot", "--start"], "5": ["up"],
                        "6": ["demo", "--offline", "--lang", _lang]}
            if choice not in commands:
                _say(t("start_bad_choice", choice=choice))
                continue
            if choice == "3":
                commands["3"] = choose_platform()
                if not commands["3"]:
                    continue
            if choice in ("1", "5") and not key:
                code = subprocess.call([*launcher.argv("init"), "--terminal"], cwd=launcher.cwd(), env=child_env)
                if code or not env_get(env, "LLM_API_KEY"):
                    continue
            sub, *extra = commands[choice]
            code = subprocess.call([*launcher.argv(sub), *extra], cwd=launcher.cwd(), env=child_env)
            if code:
                _say(t("start_failed", code=code))
    except (KeyboardInterrupt, EOFError):
        print()
        return 130
