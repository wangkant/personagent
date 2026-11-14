# `tools/` 脚本

[English](tools.md) · 简体中文 · [繁體中文](tools.zh-TW.md) · [日本語](tools.ja.md) · [한국어](tools.ko.md) · [Español](tools.es.md) · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

`tools/` 中的脚本供从克隆运行 personagent 的用户使用。这些脚本不随安装包提供，并从克隆读取 `.env` 和 `runtime/`。请使用克隆中的解释器在仓库根目录运行：

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

日常工作请使用 `personagent` 子命令，而非脚本：`personagent doctor`、`personagent learned` 和 `personagent eval`。如需试验一处提示词改动，请使用 `personagent chat`；如需衡量其效果，请使用 `personagent eval`。`personagent eval --suite memory` 以预设的记忆整理回答离线运行，每种语言 21 个用例，无需密钥；在本版本中全部通过。其他测试集会调用模型。

| 脚本 | 作用 | 需要 | 是否调用模型 | 状态 |
|---|---|---|---|---|
| `import_stickers_folder.py` | 将一个图片文件夹导入表情包库并逐张添加标签，使新库不必从零开始。`--dry-run` 显示数量，`--no-tag` 只复制文件 | 一个图片文件夹；添加标签还需要 `VISION_MODEL`、`VISION_API_KEY` 和 `VISION_BASE_URL` | 是，每张图一次视觉调用，除非加 `--dry-run` 或 `--no-tag` | 受支持 |
| `bootstrap_from_history.py` | 用一个 QQ 群的历史记录为新部署一次性完成初始化。该脚本生成管理员的表情包和消息长度画像，并将读取到的表情包存入库中 | 第三方 QQ 客户端 NapCat 的 HTTP 服务，地址为 `QQ_ONEBOT_URL`（必填），以及 `ACCESS_GROUPS` 或 `--group` 中的 QQ 群 | 否。运行中的机器人之后会用视觉模型为存入的表情包添加标签 | 实验性，仅 QQ 和 NapCat |
| `sticker_holdout_eval.py` | 使用你手工标注的表情包衡量表情包审批门的稳定性和准确度 | `runtime/holdout.jsonl`（格式见 `tools/holdout.example.jsonl`）和三个 `VISION_*` 设置 | 是，图片数 × `--runs`（默认 5）次视觉调用，30 张图约 150 次 | 实验性 |
| `package_smoke.py` | 端到端检查已安装的 `personagent` 命令：版本、`init --no-input`、`chat`、带 `/health` 的 `run`，以及 `doctor --json` | 一个已安装的 `personagent`（`--personagent PATH`），无其他要求 | 否，由替身服务器应答 | 受支持。CI 在 Linux 和 Windows 上运行 |
| `welcome_smoke.py` | 端到端检查已安装的本地页面：`start --no-browser`、保存密钥、与真实角色进行一次聊天、第二次启动复用页面、正常退出 | 一个已安装的 `personagent`（`--personagent PATH`），无其他要求 | 否，由同一个替身服务器应答 | 受支持。CI 在 Linux 和 Windows 上运行 |
| `window_smoke.py` | 在临时主目录上打开真实的应用窗口，在窗口中完成页面设置并进行聊天，然后关闭窗口 | 在 macOS 和 Linux 上，须以应用扩展安装 `personagent`（`pip install "personagent[app]"`）；在 Linux 上还需要显示环境，例如 `xvfb-run` | 否，由同一个替身服务器应答 | 受支持。CI 在 Linux、macOS 和 Windows 上运行 |
| `release_notes.py` | 对照 `pyproject.toml` 检查发布标签，并打印该版本的 CHANGELOG 段落 | 标签，例如 `v1.1.0` | 否 | 受支持。发布工作流会运行它 |
| `locale_gaps.py` | 统计 `persona_agent/locales/` 中每种语言已翻译的句数，范围为终端设置向导、终端聊天和演示所用的句子。指定语言代码（例如 `ja`）时，列出尚未翻译、将以英文显示的句子 | 无 | 否 | 受支持。有缺漏时 `tests/test_locales.py` 会失败 |

实验性脚本是用于研究和维护的辅助工具，可能被修改或删除，不设弃用期。调用模型的脚本会消耗 `.env` 中所配置账户的额度；请先阅读 `--help`，支持 `--dry-run` 的脚本请先以该参数试运行。
