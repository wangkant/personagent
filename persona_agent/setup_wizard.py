"""`personagent init` and `personagent connect`: set up a home, in English or Chinese.

Stdlib only, so quickstart.py can run it before the dependencies are installed.
"""
from __future__ import annotations

import argparse
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
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from persona_agent import home as homes

LANGS = ("en", "zh")
DEFAULT_NAMES = {"en": "Nova", "zh": "小夏"}

# Readable by its user only, as `persona_agent.storage.PRIVATE_FILE_MODE`;
# that module needs dependencies this one must run without.
SECRET_FILE_MODE = 0o600


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------

_lang = "en"


def set_lang(lang: str) -> None:
    global _lang
    _lang = lang if lang in LANGS else "en"


def _lang_of(tag: str) -> str:
    """'zh' or 'en' for a locale name such as zh_CN.UTF-8 or 'Chinese (Simplified)_China'."""
    tag = (tag or "").strip().lower().split(".")[0]
    if not tag or tag in ("c", "posix"):
        return ""
    return "zh" if tag.startswith("zh") or "chinese" in tag else "en"


def detect_lang() -> str:
    """The system's language: zh for a Chinese locale, else en."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        found = _lang_of(os.environ.get(var, "").split(":")[0])
        if found:
            return found
    if os.name == "nt":
        try:
            import ctypes

            # The low byte of a LANGID is the primary language; 0x04 is Chinese.
            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF == 0x04:
                return "zh"
        except (AttributeError, OSError):
            pass
    try:
        return _lang_of(locale.getlocale()[0] or "") or "en"
    except ValueError:
        return "en"


def t(key: str, **values) -> str:
    """The text for `key` in the current language."""
    en, zh = _TEXT[key]
    text = zh if _lang == "zh" else en
    return text.format(**values) if values else text


_TEXT: dict[str, tuple[str, str]] = {
    # header and flow
    "title_first": ("First-time setup", "首次设置"),
    "title_again": ("Reconfigure", "重新配置"),
    "folder": ("Settings are saved in {path}", "设置保存在 {path}"),
    "enter_hint": ("Press Enter to accept the value in [brackets].",
                   "直接回车 = 使用方括号里的值。"),
    "step": ("Step {n} of 3: {what}", "第 {n} 步（共 3 步）：{what}"),
    "step_model": ("the AI model", "AI 模型"),
    "step_character": ("the character", "角色"),
    "step_chat": ("chat apps (optional)", "聊天平台（可选）"),
    "required": ("(required, please enter a value)", "（必填，请输入）"),
    "yes_no": ("Y/n", "Y/n"),
    "no_yes": ("y/N", "y/N"),
    "bad_number": ("Enter a number from 1 to {n}.", "请输入 1 到 {n} 的数字。"),
    "saved": ("Saved to {path}", "已保存到 {path}"),
    # model
    "provider_intro": (
        "The bot talks through an AI service with an OpenAI-compatible API.\n"
        "You sign up with one of these and create an API key (a password for programs).",
        "机器人通过一个兼容 OpenAI 接口的 AI 服务说话。\n"
        "在下面任选一家注册，创建一个 API key（给程序用的密码）。"),
    "provider_choose": ("Service", "选择服务"),
    "base_url_explain": (
        "Base URL = the API address on your provider's page, such as https://api.deepseek.com",
        "Base URL = 服务商文档里写的 API 地址，例如 https://api.deepseek.com"),
    "base_url": ("Base URL", "Base URL（API 地址）"),
    "model_explain": ("Model = the model's id at that service, such as {example}",
                      "模型名 = 这家服务里模型的 ID，例如 {example}"),
    "model": ("Model", "模型名"),
    "ollama_model": ("Use a model you have pulled; `ollama list` shows them.",
                     "填已经下载好的模型，`ollama list` 可以查看。"),
    "key_where": ("Create an API key here: {url}", "在这里创建 API key：{url}"),
    "key_prompt": ("API key (hidden while you type or paste; then press Enter)",
                   "API key（输入或粘贴时不显示，完成后回车）"),
    "key_keep": ("API key (Enter keeps {masked}; hidden while you type)",
                 "API key（回车保留 {masked}；输入时不显示）"),
    "key_got": ("key {masked}", "已记下 {masked}"),
    "testing": ("Testing the key with one tiny request to {url}",
                "用一个很小的请求测试密钥：{url}"),
    "test_ok": ("It works.", "可以用。"),
    "test_failed": ("It did not work ({what}).", "没有成功（{what}）。"),
    "test_unreachable": ("no answer", "连接不上"),
    "retry": ("Change the answers and try again?", "修改后再试一次吗？"),
    "kept_anyway": ("Saved anyway. Fix it later by running this setup again.",
                    "仍然保存了。之后可以重新运行本设置来修正。"),
    "fix_401": ("The service refused the key. Check that you copied all of it and that it\n"
                "belongs to this service.",
                "服务商拒绝了这个密钥。确认复制完整，并且是这家服务的密钥。"),
    "key_page": ("Keys: {url}", "密钥页面：{url}"),
    "fix_402": ("The account has no balance or free quota left. Top it up in the service's console.",
                "账户余额或免费额度用完了，请到服务商控制台充值。"),
    "fix_404": ("Nothing answers at that address, or the model name is unknown.\n"
                "Check the Base URL (it usually looks like {example}) and the model name.",
                "这个地址没有对应的接口，或者模型名不存在。\n"
                "检查 Base URL（一般类似 {example}）和模型名。"),
    "fix_400": ("The service rejected the request. Its answer: {detail}\n"
                "Usually the model name is wrong, or the model is not enabled for your account.",
                "服务商拒绝了请求，返回：{detail}\n"
                "通常是模型名写错了，或者账户还没开通这个模型。"),
    "fix_429": ("Too many requests or no quota right now. Wait a minute, or check your plan.",
                "请求太频繁或额度不足。稍等一分钟，或检查你的套餐。"),
    "fix_5xx": ("The service had an internal error. Try again in a few minutes.",
                "服务商内部出错，过几分钟再试。"),
    "fix_net": ("Could not reach {host}: {detail}\n"
                "Check the address and your network or proxy.",
                "连接不上 {host}：{detail}\n"
                "检查地址、网络或代理设置。"),
    "fix_ollama": ("Is Ollama running? Start it with `ollama serve`.",
                   "Ollama 在运行吗？用 `ollama serve` 启动。"),
    # character
    "name_explain": ("Name = what people in the chat call the bot. It answers when its name comes up.",
                     "名字 = 群友怎么称呼它。消息里出现这个名字时，它会回应。"),
    "name": ("Bot name", "机器人名字"),
    "renamed": ("(a new name starts a new character: what {old} learned does not carry over)",
                "（改名等于换一个新角色：{old}学到的东西不会带过来）"),
    "lang_switched": ("(the examples, filters and checks switch to {lang} as well)",
                      "（示例、过滤规则和检查也会一起切换到{lang}）"),
    "char_intro": ("Pick a character. It is written to persona.txt, which you can edit any time.",
                   "选一个性格。会写进 persona.txt，以后随时可以改。"),
    "char_choose": ("Character", "性格"),
    "char_keep": ("Character (Enter keeps the current one)", "性格（回车保留现在的）"),
    "char_custom": ("persona.txt has your own edits, so it is left as it is.",
                    "persona.txt 已经被你改过，保持不变。"),
    "persona_written": ("persona.txt written ({what})", "已写入 persona.txt（{what}）"),
    # chat apps / AstrBot
    "connect_intro": (
        "Optional: put the bot in groups on QQ, Telegram, Discord and more. That goes\n"
        "through AstrBot, a separate chat-bot program you install first: https://docs.astrbot.app",
        "可选：让机器人进 QQ、Telegram、Discord 等平台的群。这需要先装好\n"
        "AstrBot（另一个聊天机器人程序）：https://docs.astrbot.app"),
    "connect_q": ("Connect to AstrBot now? (No = chat in this terminal only)",
                  "现在连接 AstrBot 吗？（否 = 只在终端里聊天）"),
    "astrbot_explain": ("AstrBot folder = the one holding cmd_config.json: AstrBot's data folder or the one above it.",
                        "AstrBot 文件夹 = 放 cmd_config.json 的那个：AstrBot 的 data 文件夹，或者它的上一级。"),
    "astrbot_dir": ("AstrBot folder", "AstrBot 文件夹"),
    "astrbot_bad": ("No cmd_config.json in {path}. Start AstrBot once so it creates one, or give its data folder.",
                    "{path} 里没有 cmd_config.json。先启动一次 AstrBot 让它生成，或者填它的 data 文件夹。"),
    "docker_q": ("Does AstrBot run in Docker?", "AstrBot 是在 Docker 里运行的吗？"),
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
        "在 Docker 里，127.0.0.1 指的是容器自己，插件访问不到 {url} 上的 personagent，\n"
        "而发往其他地址的明文 http:// 会被插件拒绝。二选一：\n"
        "  1. 主机网络：在 AstrBot 的 compose 文件里把 `ports:` 和 `networks:` 换成\n"
        "     `network_mode: host`（docker run 用 --network host），然后重建容器。\n"
        "     Docker Desktop（Windows/macOS）需要 4.34 以上，并打开\n"
        "     设置 > Resources > Network > Enable host networking。\n"
        "     同一个文件里的 NapCat 容器也要用主机网络，它的 WebSocket 地址改成\n"
        "     ws://127.0.0.1:6199/ws。\n"
        "  2. 给 personagent 一个 HTTPS 地址（反向代理或隧道），在下面填写。"),
    "docker_url": ("personagent's HTTPS address (Enter = keep {url} and use host networking)",
                   "personagent 的 HTTPS 地址（回车 = 保留 {url}，使用主机网络）"),
    "url_refused": ("The plugin only accepts a 127.0.0.1 / localhost address or an https:// one.",
                    "插件只接受 127.0.0.1 / localhost 地址，或者 https:// 地址。"),
    "platform_intro": ("Which chat app should the bot join?", "机器人要进哪个聊天平台？"),
    "platform_choose": ("Chat app", "聊天平台"),
    "platform_other": ("Another app, already set up in AstrBot", "其他平台（已在 AstrBot 里配好）"),
    "qq_via": ("QQ (through NapCat)", "QQ（通过 NapCat）"),
    "qq_id": ("The bot's own QQ number (the account NapCat logs in with)",
              "机器人自己的 QQ 号（NapCat 登录的那个号）"),
    "qq_groups": ("QQ group numbers it should join, comma-separated",
                  "要加入的 QQ 群号，多个用逗号隔开"),
    "groups_other": ("Group ids it should join, comma-separated (send /sid in the group to see its id)",
                     "要加入的群 ID，多个用逗号隔开（在群里发 /sid 可以看到）"),
    "ids_keep": ("Enter keeps these, '-' clears them", "回车保留，输入 - 清空"),
    "ids_none": ("Enter = none yet", "回车 = 暂不设置"),
    "admin_explain": ("Admin = you. The bot is closest to you, you can always message it privately,\n"
                      "and you can manage what it remembers.",
                      "管理员 = 你自己。机器人和你最熟，你随时可以私聊它，也可以管理它记住的内容。"),
    "admin_qq": ("Your own QQ number (Enter = no admin)", "你自己的 QQ 号（回车 = 不设管理员）"),
    "admin_other": ("Your user id on {platform} (send /sid to the bot to see it; Enter = no admin)",
                    "你在 {platform} 上的用户 ID（私聊机器人发 /sid 可以看到；回车 = 不设管理员）"),
    "admin_any": ("Your account as platform:id, such as wecom:alice (send /sid to the bot; Enter = no admin)",
                  "你的账号，格式 平台:ID，例如 wecom:alice（私聊机器人发 /sid 可以看到；回车 = 不设管理员）"),
    "admin_name": ("What should the bot call you?", "机器人怎么称呼你？"),
    "dm_users": ("Who else may message the bot privately? Comma-separated ids",
                 "还允许谁私聊机器人？填 ID，逗号隔开"),
    "token_skip": ("Enter = already set up in AstrBot", "回车 = 已经在 AstrBot 里配好"),
    "platform_written": ("{kind} switched on in AstrBot's settings; it starts with AstrBot.",
                         "已在 AstrBot 的设置里开启 {kind}，随 AstrBot 一起启动。"),
    "plugin_installed": ("AstrBot plugin installed: {path}", "AstrBot 插件已安装：{path}"),
    "plugin_config": ("Plugin settings written: {path}", "插件设置已写入：{path}"),
    "write_failed": ("Could not write to {path}: {error}", "无法写入 {path}：{error}"),
    "url_replaced": ("personagent_url {old} would be refused by the plugin; it is now {new}",
                     "插件会拒绝 personagent_url {old}，已改为 {new}"),
    "url_kept": ("Keeping personagent_url {url} (personagent listens on port {port})",
                 "保留 personagent_url {url}（personagent 监听端口 {port}）"),
    "retired_removed": ("Removed {path}: the same plugin under an older name, which would forward every message twice",
                        "已删除 {path}：这是同一个插件的旧名字，留着会把每条消息转发两遍"),
    "retired_config": ("Removed {path}, the older plugin's settings. QQ routing came across;\n"
                       "set groups and dm_users again in AstrBot's WebUI.",
                       "已删除旧插件的设置 {path}。QQ 转发设置已沿用；\n"
                       "groups 和 dm_users 请在 AstrBot 的 WebUI 里重新设置。"),
    "allowlists_empty": ("The plugin forwards no group or DM yet: add groups / dm_users in AstrBot's WebUI.",
                         "插件还没有放行任何群或私聊：在 AstrBot 的 WebUI 里填 groups / dm_users。"),
    "allowlists_kept": ("Kept the plugin's groups and dm_users.", "保留了插件已有的 groups 和 dm_users。"),
    # finish
    "done": ("Setup complete", "设置完成"),
    "next": ("Next:", "接下来："),
    "next_demo": ("Watch it stay quiet and learn from a correction (a minute, no chat account needed):",
                  "看它如何判断该不该开口、如何从纠正中学习（一分钟，不需要聊天账号）："),
    "next_chat": ("Chat with {name} in this terminal:", "在终端里和{name}聊天："),
    "next_run": ("Start personagent and keep it running (AstrBot talks to it):",
                 "启动 personagent 并保持运行（AstrBot 会连接它）："),
    "next_restart": ("Restart AstrBot, or reload plugins in its WebUI, so it loads the plugin.",
                     "重启 AstrBot，或在它的 WebUI 里重载插件，让插件生效。"),
    "next_qq": ("In AstrBot's WebUI add the QQ (OneBot v11 / aiocqhttp) platform, and point NapCat's\n"
                "     reverse WebSocket at ws://127.0.0.1:6199/ws. Guide: https://docs.astrbot.app",
                "在 AstrBot 的 WebUI 里添加 QQ（OneBot v11 / aiocqhttp）平台，再把 NapCat 的\n"
                "     反向 WebSocket 指向 ws://127.0.0.1:6199/ws。教程：https://docs.astrbot.app"),
    "next_say": ("Say \"{name}, hi\" in one of those groups.", "在其中一个群里说「{name}，你好」。"),
    "next_persona": ("Edit {path} to change who {name} is, then restart.",
                     "修改 {path} 可以调整{name}的人设，改完重启。"),
    "next_key": ("Add your API key: run this setup again, or set LLM_API_KEY in {path}.",
                 "填上 API key：重新运行本设置，或在 {path} 里设置 LLM_API_KEY。"),
    "chat_now": ("Chat with the bot in this terminal now?", "现在就在终端里和机器人聊聊吗？"),
    "skipped": ("Setup questions skipped: {why}. Run `{cmd}` in a terminal, or pass "
                "--no-input with --provider, --key-env and --name.",
                "已跳过设置问答：{why}。请在终端里运行 `{cmd}`，或加 --no-input 和 "
                "--provider、--key-env、--name 等参数。"),
    "key_cleared": ("The API key saved for the previous AI service was cleared, so it is not sent to the new one. "
                    "Pass --key-env VAR to set a key for this service.",
                    "原来那个 AI 服务的 API key 已清除，不会发给新服务。"
                    "请用 --key-env VAR 为新服务设置 key。"),
    "skip_tty": ("input is not a terminal", "输入不是终端"),
    "rerun_q": ("personagent is already set up. Run the setup questions again?",
                "personagent 已经设置过了。要重新回答设置问题吗？"),
    "kept_config": ("Keeping the current setup.", "保留现有设置。"),
    "home_diverges": ("AGENT_HOME in {env} points at {other}, so personagent reads its settings there,\n"
                      "not here. Move the files there, or remove that line.",
                      "{env} 里的 AGENT_HOME 指向 {other}，personagent 会从那里读设置，\n"
                      "而不是这里。把文件挪过去，或者删掉那一行。"),
    "home_unresolved": ("AGENT_HOME is {value}, which cannot be resolved; check it before starting.",
                        "AGENT_HOME 是 {value}，无法解析；启动前请检查。"),
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
        return self.name[1] if _lang == "zh" else self.name[0]

    @property
    def hint(self) -> str:
        return self.note[1] if _lang == "zh" else self.note[0]

    @property
    def needs_key(self) -> bool:
        return self.key != "ollama"


# Base URLs as each vendor documents them for OpenAI-compatible chat.
PROVIDERS: tuple[Provider, ...] = (
    Provider("deepseek", ("DeepSeek", "DeepSeek 深度求索"), "https://api.deepseek.com",
             "deepseek-flash", "https://platform.deepseek.com/api_keys"),
    Provider("siliconflow", ("SiliconFlow", "硅基流动 SiliconFlow"), "https://api.siliconflow.cn/v1",
             "deepseek-ai/DeepSeek-V3.2", "https://cloud.siliconflow.cn/account/ak"),
    Provider("bailian", ("Alibaba Bailian / Qwen", "阿里云百炼（通义千问）"),
             "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus",
             "https://bailian.console.aliyun.com/",
             ("Outside mainland China use https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
              "国际站的密钥要用 https://dashscope-intl.aliyuncs.com/compatible-mode/v1")),
    Provider("zhipu", ("Zhipu GLM", "智谱 GLM"), "https://open.bigmodel.cn/api/paas/v4",
             "glm-4.7-flash", "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
             ("glm-4.7-flash is free to use.", "glm-4.7-flash 可以免费使用。")),
    Provider("moonshot", ("Moonshot / Kimi", "月之暗面 Kimi"), "https://api.moonshot.cn/v1",
             "kimi-k2.6", "https://platform.kimi.com/console/api-keys"),
    Provider("ark", ("Volcengine Ark / Doubao", "火山方舟（豆包）"),
             "https://ark.cn-beijing.volces.com/api/v3", "doubao-seed-2-1-lite-260915",
             "https://console.volcengine.com/ark/region:ark+cn-beijing/apikey",
             ("Enable the model in the Ark console first.", "先在方舟控制台的开通管理里开通这个模型。")),
    Provider("openrouter", ("OpenRouter", "OpenRouter"), "https://openrouter.ai/api/v1",
             "deepseek/deepseek-v4.1-flash", "https://openrouter.ai/keys"),
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
    if sys.stdin is not None and sys.stdin.isatty():
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


def ask_yn(prompt: str, default_yes: bool = True) -> bool:
    answer = input(f"  {prompt} [{t('yes_no') if default_yes else t('no_yes')}]: ").strip().lower()
    if not answer:
        return default_yes
    return answer[0] in ("y", "是", "好")


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
    current = _clean_ids(current) if isinstance(current, (list, tuple)) else []
    hint = t("ids_keep") if current else t("ids_none")
    raw = ask(f"{label}（{hint}）" if _lang == "zh" else f"{label} ({hint})",
              default=",".join(current))
    return [] if raw.strip() == "-" else split_ids(raw)


def _say(text: str = "") -> None:
    print("\n".join(f"  {line}" if line else "" for line in text.split("\n")))


# ---------------------------------------------------------------------------
# .env
# ---------------------------------------------------------------------------

def env_literal(value) -> str:
    """`value` as one .env right-hand side that dotenv reads back unchanged."""
    text = str(value)
    if (text != text.strip() or text.startswith("#") or " #" in text
            or any(ch in text for ch in "\"'\n\r")):
        return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return text


def set_env_values(env_text: str, values: dict) -> str:
    """`env_text` with every uncommented KEY= line of a key in `values`
    rewritten (dotenv reads the last one, so all of them); keys not present
    are appended. Comments and order are kept."""
    lines = env_text.splitlines()
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
    try:
        # Keep a stricter mode the operator chose, never a wider one.
        if env_path.exists():
            os.chmod(tmp, env_path.stat().st_mode & SECRET_FILE_MODE)
    except OSError:
        pass  # Windows ACLs do not map onto POSIX mode bits
    os.replace(tmp, env_path)


def secure_env_file(env_path: Path) -> None:
    """Narrow .env to its user (0600); a copy of the template starts at 0644."""
    try:
        os.chmod(env_path, SECRET_FILE_MODE)
    except OSError:
        pass  # Windows ACLs do not map onto POSIX mode bits


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

    @property
    def label(self) -> str:
        return self.title[1] if _lang == "zh" else self.title[0]


TEMPLATE = "template"
CHARACTERS: tuple[Character, ...] = (
    Character("dry-wit", ("Dry-witted friend: deadpan, short replies, teases lightly",
                          "毒舌损友：冷幽默，回得短，调侃点到为止")),
    Character("warm-listener", ("Warm listener: asks how you are, remembers the small things",
                                "温柔倾听者：会问近况，记得小事")),
    Character("gamer", ("Gamer: co-op shooters and roguelikes, friendly trash talk",
                        "游戏搭子：合作射击和肉鸽，爱互相嘴几句")),
    Character("bookworm", ("Bookworm: careful words, recommends books when asked",
                           "文艺书虫：用词讲究，被问到才推荐书")),
    Character(TEMPLATE, ("Write my own later: a plain starting character to edit",
                         "以后自己写：先放一个朴素的起步角色，之后再改")),
)
PERSONA_KEYS = tuple(c.key for c in CHARACTERS)

NAME_LINE = {"en": "Your name is {name}.", "zh": "你叫{name}。"}

# Earlier releases' templates, copied verbatim: still counted as unmodified.
_LEGACY_PERSONA_SHA256 = frozenset({
    "d5521d29275b4bbb8fe51190b02e03bca854df89698f44bab21996c72574601a",
    "e6194054243ae9d37feed2409c2a07906b072d1f61dd8f8eb9422503a93ff357",
    "46856227a6901dd3299b5a57b1d2b7d45075a0fba3aa545d58158c0b991d65b0",
    "85383ff3974a7c57ae6474ff482f342ad746457a3903367c0c8d30aebdb52bad",
    "c357d226d8daf47583942be31e70cbce77d6efb2a592dc78ae703f3934aebca2",
})
_NOTE_RULE = re.compile(r"\n[ \t]*[—-]{2,}[ \t]*\n")


def _normal(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def persona_source(key: str, lang: str) -> Path:
    if key == TEMPLATE:
        return homes.resource("data", f"persona.example.{lang}.txt")
    return homes.resource("data", "personas", lang, f"{key}.txt")


def render_persona(text: str, *, name: str, lang: str, admin_name: str = "",
                   admin_relationship: str = "") -> str:
    """A persona document ready for the model: placeholders filled, the admin
    line dropped when there is no admin, notes after a rule line removed, and
    a name line added when the text never names the character."""
    body = _NOTE_RULE.split(_normal(text), maxsplit=1)[0]
    lines = []
    for line in body.split("\n"):
        if "{admin_name}" in line or "{admin_relationship}" in line:
            if not admin_name:
                continue
            if not admin_relationship:
                line = re.sub(r"\s*[(（]\{admin_relationship\}[)）]", "", line)
            line = (line.replace("{admin_name}", admin_name)
                    .replace("{admin_relationship}", admin_relationship))
        lines.append(line)
    out = "\n".join(lines).strip()
    if "{bot_name}" in out:
        out = out.replace("{bot_name}", name)
    else:
        out = NAME_LINE.get(lang, NAME_LINE["en"]).format(name=name) + "\n" + out
    return out + "\n"


def shipped_persona(text: str) -> tuple[str, str, str] | None:
    """(key, lang, name) when `text` is a shipped character as this setup
    writes it, ('legacy', '', '') for an earlier release's template, or None
    when someone has edited it."""
    norm = _normal(text)
    if hashlib.sha256(norm.encode("utf-8")).hexdigest() in _LEGACY_PERSONA_SHA256:
        return ("legacy", "", "")
    sentinel = "\x00NAME\x00"
    for lang in LANGS:
        for character in CHARACTERS:
            source = persona_source(character.key, lang)
            if not source.is_file():
                continue
            raw = source.read_text(encoding="utf-8")
            if norm == _normal(raw):
                return (character.key, lang, "")
            shape = _normal(render_persona(raw, name=sentinel, lang=lang))
            pattern = re.escape(shape).replace(re.escape(sentinel), r"(.+?)", 1)
            pattern = pattern.replace(re.escape(sentinel), r"\1")
            found = re.fullmatch(pattern, norm)
            if found:
                return (character.key, lang, found.group(1))
    return None


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
    os.replace(tmp, path)
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


def completions_url(base_url: str) -> str:
    """The URL the agent posts chat completions to for `base_url`."""
    try:
        from persona_agent.endpoints import chat_completions_url
    except ImportError:  # the bootstrap runs without the dependencies
        return base_url.rstrip("/") + "/chat/completions"
    return chat_completions_url(base_url)


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
        return t("fix_429")
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
    roots = []
    configured = os.environ.get(ASTRBOT_ROOT_VAR, "").strip()
    if configured:
        roots.append(Path(configured).expanduser())
    roots.append(user / ".astrbot")
    for base in (homes.find_home().parent, homes.CHECKOUT.parent, Path.cwd(), user,
                 user / "Desktop", user / "Documents"):
        roots += [base / "AstrBot", base / "astrbot"]
    roots.append(Path.cwd())
    return roots


def find_astrbot_data() -> Path | None:
    try:
        roots = astrbot_roots()
    except (OSError, RuntimeError):
        return None
    for root in roots:
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
    """The plugin's config document. A value passed as None keeps what the
    operator set, and keys this does not manage are kept: re-running must not
    undo a setup."""
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
    cfg.setdefault("timeout_s", 180)
    cfg.setdefault("block_default", True)
    return cfg


def astrbot_config_path(data_dir: Path) -> Path:
    return data_dir / "config" / f"{PLUGIN_NAME}_config.json"


def retired_astrbot_config_path(data_dir: Path) -> Path:
    return data_dir / "config" / f"{RETIRED_PLUGIN_NAME}_config.json"


def _write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    os.replace(tmp, path)
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


# AstrBot platform adapters this setup can switch on, in AstrBot's own config
# shape (its 4.x template); only the credential fields are filled in.
PLATFORMS = {
    "telegram": (("telegram_token", ("Telegram bot token (from @BotFather)",
                                     "Telegram 机器人 token（找 @BotFather 创建）")),),
    "discord": (("discord_token", ("Discord bot token (Developer Portal > Bot)",
                                   "Discord 机器人 token（Developer Portal > Bot）")),),
    "slack": (("bot_token", ("Slack bot token (xoxb-...)", "Slack bot token（xoxb-...）")),
              ("app_token", ("Slack app-level token (xapp-..., Socket Mode)",
                             "Slack app-level token（xapp-...，Socket Mode）"))),
    "kook": (("kook_bot_token", ("KOOK bot token", "KOOK 机器人 token")),),
    "lark": (("app_id", ("Lark / Feishu app id", "飞书 / Lark App ID")),
             ("app_secret", ("Lark / Feishu app secret", "飞书 / Lark App Secret"))),
}
PLATFORM_LABELS = {"telegram": "Telegram", "discord": "Discord", "slack": "Slack",
                   "kook": "KOOK", "lark": "Lark / Feishu"}
_PLATFORM_DEFAULTS = {
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
    platforms = cfg.get("platform")
    if not isinstance(platforms, list):
        platforms = []
    for i, existing in enumerate(platforms):
        if isinstance(existing, dict) and existing.get("id") == entry["id"]:
            # Keep the user's own adapter settings (proxy, base URL, ...): only the credentials change.
            fields = ["enable"] + [key for key, _ in PLATFORMS.get(entry.get("type"), ())]
            same_kind = existing.get("type") == entry.get("type")
            platforms[i] = ({**existing, **{k: entry[k] for k in fields if k in entry}}
                            if same_kind else entry)
            break
    else:
        platforms.append(entry)
    cfg["platform"] = platforms
    return _write_json(path, cfg)


def flag_platform_creds(kind: str, token: str = "", app_token: str = "", app_id: str = "",
                        app_secret: str = "") -> dict:
    """The credential fields of `kind` from the command-line flags."""
    return {"telegram": {"telegram_token": token}, "discord": {"discord_token": token},
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
        prefix = sys.prefix.replace("\\", "/").lower()
        if "/archive-v" in prefix and "/uv/" in prefix:
            return [f"uvx personagent {tail}"]
        if shutil.which("personagent"):
            return [f"personagent {tail}"]
        return [f"{_program(self.python)} -m persona_agent {tail}"]


def _resolved(path: Path) -> Path:
    try:
        return Path(path).expanduser().resolve()
    except OSError:
        return Path(path)


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

def _width(text: str) -> int:
    """Columns `text` takes in a terminal: CJK characters take two."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _header(text: str) -> None:
    print()
    print(f"-- {text} " + "-" * max(4, 60 - _width(text)))


def ask_language(default: str) -> str:
    print()
    print("  Language / 语言")
    print("    1. English")
    print("    2. 中文")
    choice = ask_number("Choose / 选择", 2, default=LANGS.index(default) + 1)
    return LANGS[choice - 1]


def _current(env_path: Path) -> dict:
    keys = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "PERSONA_NAME", "AGENT_LANG",
            "QQ_BOT_ID", "ADMIN_IDS", "ADMIN_NAME", "ADMIN_RELATIONSHIP",
            "ACCESS_GROUPS", "ACCESS_DM_USERS")
    return {key: env_get(env_path, key) for key in keys}


def step_model(current: dict, retry: bool = False) -> dict:
    """Provider, model and key; on a retry the Base URL is asked too."""
    if not retry:
        _say(t("provider_intro"))
    for i, provider in enumerate(PROVIDERS, 1):
        where = urllib.parse.urlsplit(provider.base_url).hostname or ""
        print(f"   {i:>2}. {provider.label}{' ' * max(1, 36 - _width(provider.label))}{where}")
    known = provider_for_base(current["LLM_BASE_URL"]) if current["LLM_BASE_URL"] else None
    if current["LLM_BASE_URL"] and known is None:
        known = provider_named("other")
    default = PROVIDERS.index(known) + 1 if known else 1
    provider = PROVIDERS[ask_number(t("provider_choose"), len(PROVIDERS), default) - 1]
    same = known is not None and known.key == provider.key
    if provider.hint:
        _say(provider.hint)

    # The same service keeps its address as written (a region, a proxy).
    base_url = current["LLM_BASE_URL"] if same and current["LLM_BASE_URL"] else provider.base_url
    if not base_url or retry:
        _say(t("base_url_explain"))
        base_url = ask(t("base_url"), default=base_url, required=True)
    if provider.key == "ollama":
        _say(t("ollama_model"))
    elif not provider.model:
        _say(t("model_explain", example="deepseek-flash"))
    model = ask(t("model"), default=(current["LLM_MODEL"] if same and current["LLM_MODEL"]
                                     else provider.model), required=True)

    if not provider.needs_key:
        api_key = current["LLM_API_KEY"] if same and current["LLM_API_KEY"] else "ollama"
    elif same and current["LLM_API_KEY"]:
        masked = mask_secret(current["LLM_API_KEY"])
        api_key = ask(t("key_keep", masked=masked), default=current["LLM_API_KEY"],
                      shown_default="", secret=True)
        _say(t("key_got", masked=mask_secret(api_key)))
    else:
        if provider.key_url:
            _say(t("key_where", url=provider.key_url))
        api_key = ask(t("key_prompt"), required=True, secret=True)
        _say(t("key_got", masked=mask_secret(api_key)))
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


def step_character(home: Path, current: dict, lang: str) -> tuple[str, str]:
    """The bot's name and which persona to write ('' = leave persona.txt alone)."""
    default_name = current["PERSONA_NAME"] or DEFAULT_NAMES[lang]
    _say(t("name_explain"))
    name = ask(t("name"), default=default_name, required=True)
    if current["PERSONA_NAME"] and name != current["PERSONA_NAME"]:
        _say(t("renamed", old=current["PERSONA_NAME"]))

    persona_path = home / "persona.txt"
    origin = None
    if persona_path.is_file():
        origin = shipped_persona(persona_path.read_text(encoding="utf-8"))
        if origin is None:
            _say(t("char_custom"))
            return name, ""
    print()
    _say(t("char_intro"))
    for i, character in enumerate(CHARACTERS, 1):
        print(f"    {i}. {character.label}")
    default = PERSONA_KEYS.index(default_character(origin)) + 1
    prompt = t("char_keep") if origin and origin[0] in PERSONA_KEYS else t("char_choose")
    return name, CHARACTERS[ask_number(prompt, len(CHARACTERS), default=default) - 1].key


PLATFORM_MENU = ("qq", "telegram", "discord", "slack", "kook", "lark", "other")


def _platform_label(kind: str) -> str:
    if kind == "qq":
        return t("qq_via")
    if kind == "other":
        return t("platform_other")
    return PLATFORM_LABELS[kind]


def _entries_on(ids: list[str], platform: str) -> list[str]:
    """Entries of an identity list on one platform (QQ's are bare or qq:)."""
    if platform == "qq":
        return [i for i in ids if ":" not in i or i.startswith("qq:")]
    return [i for i in ids if i.startswith(platform + ":")]


def _raw_id(entry: str) -> str:
    return entry.split(":", 1)[1] if ":" in entry else entry


def step_astrbot(env_path: Path, current: dict, values: dict) -> dict | None:
    """Connect to AstrBot. Writes the plugin and its config; returns what the
    next steps need, or None when skipped."""
    _say(t("connect_intro"))
    if not ask_yn(t("connect_q"), default_yes=False):
        return None
    guess = find_astrbot_data()
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
            for key, prompts in PLATFORMS[kind]:
                prompt = prompts[1] if _lang == "zh" else prompts[0]
                creds[key] = ask(prompt, secret="token" in key or "secret" in key)
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
            admin = ask(t("admin_other", platform=PLATFORM_LABELS[kind]),
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
            _say(t("platform_written", kind=PLATFORM_LABELS[kind]))
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
        _say(f"{n}. " + t("next_restart"))
        n += 1
        if astrbot["kind"] == "qq":
            _say(f"{n}. " + t("next_qq"))
            n += 1
        _say(f"{n}. " + t("next_say", name=name))
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


def run_wizard(home: Path, launcher: Launcher, *, lang_default: str = "") -> None:
    """The interactive setup. Answers are written to <home>/.env and persona.txt."""
    env_path = copy_env_template(home)
    rerun = bool(env_get(env_path, "LLM_API_KEY"))
    current = _current(env_path) if rerun else {k: "" for k in _current(env_path)}
    current_lang = current["AGENT_LANG"].lower() if rerun else ""
    lang = ask_language(current_lang if current_lang in LANGS else (lang_default or detect_lang()))
    set_lang(lang)
    _header(t("title_again") if rerun else t("title_first"))
    _say(t("folder", path=home))
    _say(t("enter_hint"))
    warn_if_agent_home_diverges(env_path, home)
    if current_lang in LANGS and lang != current_lang:
        _say(t("lang_switched", lang="中文" if lang == "zh" else "English"))

    _header(t("step", n=1, what=t("step_model")))
    retry = False
    while True:
        values = step_model(current, retry=retry)
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
    name, persona = step_character(home, current, lang)
    write_env(env_path, {"PERSONA_NAME": name})

    _header(t("step", n=3, what=t("step_chat")))
    answers: dict = {}
    astrbot = step_astrbot(env_path, current, answers)
    if persona:
        admin_name = answers.get("ADMIN_NAME", current["ADMIN_NAME"])
        write_persona(home, persona, name=name, lang=lang, admin_name=admin_name,
                      admin_relationship=current["ADMIN_RELATIONSHIP"])
        character = CHARACTERS[PERSONA_KEYS.index(persona)]
        _say(t("persona_written", what=short_label(character)))
    finish(launcher, home, name=name, has_key=True, astrbot=astrbot, offer_chat=True)


# ---------------------------------------------------------------------------
# Without questions
# ---------------------------------------------------------------------------

def apply_flags(home: Path, args: argparse.Namespace) -> str:
    """Templates in place and the flags written; returns the bot's name.

    An unedited shipped persona.txt follows the name, the language and
    --persona; an edited one is never touched."""
    if args.provider == "other" and not args.base_url:
        raise SystemExit("--provider other needs --base-url")
    existed = (home / ".env").exists()
    env_path = copy_env_template(home)
    lang = (args.lang or os.environ.get("AGENT_LANG", "").strip().lower()
            or (env_get(env_path, "AGENT_LANG") if existed else "") or detect_lang())
    lang = lang if lang in LANGS else "en"
    set_lang(lang)
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
    old_url = env_get(env_path, "LLM_BASE_URL").rstrip("/")
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
        key = os.environ.get(args.key_env, "").strip()
        if not key:
            raise SystemExit(f"--key-env {args.key_env}: that environment variable is empty")
        values["LLM_API_KEY"] = key
    name = args.name or env_get(env_path, "PERSONA_NAME") or DEFAULT_NAMES[lang]
    values["PERSONA_NAME"] = name
    write_env(env_path, values)

    persona_path = home / "persona.txt"
    origin = (shipped_persona(persona_path.read_text(encoding="utf-8"))
              if persona_path.is_file() else ("", "", ""))
    if origin is not None:
        key = args.persona or (default_character(origin) if origin[0] else TEMPLATE)
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

def init_parser(prog: str, add_help: bool = True) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=prog, add_help=add_help,
        description="Set up personagent: the AI service, the character, and "
                    "optionally AstrBot. Asks questions in a terminal.")
    p.add_argument("--no-input", action="store_true",
                   help="ask nothing; use the flags below and keep everything else")
    p.add_argument("--provider", choices=PROVIDER_KEYS, help="an AI service preset")
    p.add_argument("--base-url", help="the service's API address (needed with --provider other)")
    p.add_argument("--model", help="the model id (default: the preset's)")
    p.add_argument("--key-env", metavar="VAR",
                   help="read the API key from this environment variable")
    p.add_argument("--name", help="the bot's name (default: Nova, or a Chinese name with --lang zh)")
    p.add_argument("--lang", choices=LANGS, help="en or zh (default: the system language)")
    p.add_argument("--persona", choices=PERSONA_KEYS,
                   help="a ready character for persona.txt (written only while it is unedited)")
    return p


def _prepare_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def run(argv: list[str] | None, prog: str, *, python: str | None = None,
        confirm_rerun: bool = False, args: argparse.Namespace | None = None,
        strict_skip: bool = False) -> int:
    """`init` with an interpreter of choice: quickstart passes its .venv's,
    and the flags it has already parsed."""
    _prepare_output()
    args = args if args is not None else init_parser(prog).parse_args(argv)
    home = homes.find_home()
    launcher = Launcher(python=python or sys.executable, home=home)
    tty = sys.stdin is not None and sys.stdin.isatty()
    if args.no_input or not tty:
        if not args.no_input:
            set_lang(args.lang or detect_lang())
            print(t("skipped", why=t("skip_tty"), cmd=prog))
        done = setup_without_questions(home, args, launcher)
        flagged = any((args.provider, args.base_url, args.model, args.key_env,
                       args.name, args.lang, args.persona))
        # Piped without flags nothing was configured, and a script must be able to tell.
        return 2 if strict_skip and not args.no_input and not flagged else done
    env_path = home / ".env"
    if confirm_rerun and env_get(env_path, "LLM_API_KEY"):
        set_lang(env_get(env_path, "AGENT_LANG") or detect_lang())
        if not ask_yn(t("rerun_q"), default_yes=False):
            print(t("kept_config"))
            return 0
    run_wizard(home, launcher, lang_default=args.lang or "")
    return 0


def main(argv: list[str] | None = None, prog: str = "personagent init") -> int:
    try:
        return run(argv, prog, strict_skip=True)
    except (KeyboardInterrupt, EOFError):
        print()
        return 130


def connect_parser(prog: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=prog, description="Connect personagent to AstrBot: copy the plugin, share a "
                               "token, write the allowlists. With DATA_DIR nothing is asked.",
        epilog="AstrBot in Docker cannot reach 127.0.0.1 on this machine: give it host "
               "networking, or put personagent behind HTTPS and pass that address as --url.")
    p.add_argument("target", choices=("astrbot",))
    p.add_argument("data_dir", nargs="?", metavar="DATA_DIR",
                   help="AstrBot's folder (its data folder or the one above it)")
    qq = p.add_mutually_exclusive_group()
    qq.add_argument("--qq", dest="qq", action="store_const", const=True,
                    help="route QQ through AstrBot too")
    qq.add_argument("--no-qq", dest="qq", action="store_const", const=False,
                    help="stop routing QQ through AstrBot (without either, it is left as it is)")
    p.add_argument("--platform", choices=tuple(PLATFORMS),
                   help="also switch on this adapter in AstrBot's own config")
    p.add_argument("--token", default="", help="the adapter's bot token")
    p.add_argument("--app-token", default="", help="Slack's app-level token")
    p.add_argument("--app-id", default="", help="Lark / Feishu app id")
    p.add_argument("--app-secret", default="", help="Lark / Feishu app secret")
    p.add_argument("--url", default="",
                   help="the address the plugin posts to, such as an https:// one "
                        "(default http://127.0.0.1:<SERVER_PORT>)")
    return p


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
                raise SystemExit(f"platform not written: {exc}") from None
            write_astrbot_platform(found, entry)
            print(t("platform_written", kind=PLATFORM_LABELS[platform]))
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
    print("  2. " + t("next_restart"))
    return 0


def connect_main(argv: list[str] | None = None, prog: str = "personagent connect") -> int:
    _prepare_output()
    args = connect_parser(prog).parse_args(argv)
    home = homes.find_home()
    env_path = home / ".env"
    set_lang(env_get(env_path, "AGENT_LANG") or detect_lang())
    if args.data_dir:
        creds = flag_platform_creds(args.platform or "", args.token, args.app_token,
                                    args.app_id, args.app_secret)
        return connect_without_questions(home, Path(args.data_dir), qq=args.qq,
                                         platform=args.platform or "", creds=creds,
                                         url=args.url)
    if args.qq is not None or args.platform or args.url:
        raise SystemExit("--qq, --no-qq, --platform and --url need DATA_DIR")
    if not (sys.stdin is not None and sys.stdin.isatty()):
        raise SystemExit(f"{prog}: give AstrBot's folder (DATA_DIR), or run this in a terminal")
    try:
        env_path = copy_env_template(home)
        answers: dict = {}
        astrbot = step_astrbot(env_path, _current(env_path), answers)
        if astrbot:
            launcher = Launcher(python=sys.executable, home=home)
            name = env_get(env_path, "PERSONA_NAME") or DEFAULT_NAMES.get(_lang, "Nova")
            finish(launcher, home, name=name, has_key=bool(env_get(env_path, "LLM_API_KEY")),
                   astrbot=astrbot, offer_chat=False)
    except (KeyboardInterrupt, EOFError):
        print()
        return 130
    return 0
