# `tools/` 脚本

[English](tools.md) · 简体中文 · [繁體中文](tools.zh-TW.md) · [日本語](tools.ja.md) · [한국어](tools.ko.md) · [Español](tools.es.md) · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

`tools/` 里的脚本给从克隆运行 personagent 的人用。它们不随安装包提供，并从克隆读取 `.env` 和 `runtime/`。用克隆的解释器在仓库根目录运行：

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

日常工作用 `personagent` 子命令，不用脚本：`personagent doctor`、`personagent learned` 和 `personagent eval`。要试一处提示词改动，用 `personagent chat`；要衡量它，用 `personagent eval`。

| 脚本 | 作用 | 需要 | 是否调用模型 | 状态 |
|---|---|---|---|---|
| `import_stickers_folder.py` | 把一个图片文件夹导入表情包库并逐张打标签，这样新库不会从空开始。`--dry-run` 显示数量，`--no-tag` 只复制文件 | 一个图片文件夹；打标签还需要 `VISION_MODEL`、`VISION_API_KEY` 和 `VISION_BASE_URL` | 是，每张图一次视觉调用，除非加 `--dry-run` 或 `--no-tag` | 受支持 |
| `bootstrap_from_history.py` | 用一个 QQ 群的历史记录让新部署一次性起步。它生成管理员的表情包和消息长度画像，并把看到的表情包存入库中 | 第三方 QQ 客户端 NapCat 的 HTTP 服务，地址为 `QQ_ONEBOT_URL`（必填），以及 `ACCESS_GROUPS` 或 `--group` 里的 QQ 群 | 否。运行中的机器人之后用视觉模型给存下的表情包打标签 | 实验性，仅 QQ 和 NapCat |
| `auto_reviewer.py` | 读取 `runtime/eval.jsonl` 里的低自评分，让模型把每一条变成一对修改前后的对照。加 `--apply` 时会逐对询问你是否加入共享反馈池 | `EVAL_ENABLED=true` 开一段时间，才有分数 | 是，每条审阅一次调用（`--limit`，默认 20）。`--dry-run` 不调用 | 实验性。`--apply` 写入所有聊天共用的池。只想为一个聊天批准修正，用 `personagent learned` |
| `evolution_benchmark.py` | 让真实的 agent 在 `data/benchmark/` 的场景上跑几轮，一次打开自我改进循环，一次关闭，再比较两者。`run` 负责运行，`ingest` 读回评审分数 | `LLM_API_KEY`，以及一个不是被测模型的评审（`--judge export`、`openai` 或 `anthropic`，配 `BENCH_JUDGE_MODEL`） | 是，调用很多：每个场景、每轮、每组 | 实验性 |
| `scenario_probe.py` | 用真实模型试验候选基准场景，报告哪些能暴露基准需要的失败 | `LLM_API_KEY`，一个形如 `data/benchmark/scenarios.train.en.jsonl` 的候选场景文件，以及评审环节用的 `--judge-model` | 是，每个场景一次回复、一次自评和一次评审调用 | 实验性，用于构建基准 |
| `sticker_holdout_eval.py` | 用你手工标注的表情包衡量表情包审批门的稳定性和准确度 | `runtime/holdout.jsonl`（格式见 `tools/holdout.example.jsonl`）和三个 `VISION_*` 设置 | 是，图片数 × `--runs`（默认 5）次视觉调用，30 张图约 150 次 | 实验性 |
| `package_smoke.py` | 端到端检查已安装的 `personagent` 命令：版本、`init --no-input`、`chat`、带 `/health` 的 `run`，以及 `doctor --json` | 一个已安装的 `personagent`（`--personagent PATH`），别的都不要 | 否，由替身服务器应答 | 受支持。CI 在 Linux 和 Windows 上运行 |
| `welcome_smoke.py` | 端到端检查已安装的本地页面：`start --no-browser`、保存密钥、和真实角色聊一次、第二次启动复用页面、干净退出 | 一个已安装的 `personagent`（`--personagent PATH`），别的都不要 | 否，由同一个替身服务器应答 | 受支持。CI 在 Linux 和 Windows 上运行 |
| `release_notes.py` | 对照 `pyproject.toml` 检查发布标签，并打印该版本的 CHANGELOG 段落 | 标签，比如 `v1.1.0` | 否 | 受支持。发布工作流会运行它 |

实验性脚本是研究和维护用的辅助工具，可能改动或删除，不设弃用期。调用模型的脚本会花 `.env` 里账户的额度；先读 `--help`，有 `--dry-run` 的先试它。
