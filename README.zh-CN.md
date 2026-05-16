# qq-persona-agent

[English](README.md) | **中文**

一个用来在 QQ 群里跑**人设型 LLM agent** 的模板 —— 目标是发出来的消息像真人闲聊，而不是客服机器人。

> **部署之前先看 [DISCLAIMER.md](DISCLAIMER.md)。** 第三方 QQ 协议端没有腾讯背书，建议用小号 + 家庭/居民 IP 跑。

## 仓库结构

| 模块 | 作用 |
|---|---|
| `agent.py` | Hermes 风格的两段式输出（`<reasoning>` + `<intent>` + `<reply>`）；6 个 intent 标签驱动不同子风格；按用户做 RAG 记忆；针对 `examples.jsonl` / `feedback.jsonl` 的动态 few-shot 检索；正则前置过滤剥掉 markdown / emoji / 动作描写；异步自评对每条回复打 1-5 分写入 `eval.jsonl` |
| `stickers.py` | md5 去重的表情包库；自动收录群里见过的新表情；上下文够了再用视觉模型打标签；模型用 `[STICKER:<tag>]` 标记发送表情 |
| `main.py` | FastAPI webhook 接收端。NapCat 把群事件 POST 到 `/webhook/qq`，agent 处理后再 POST 回 NapCat 的 HTTP API |
| `tools/bootstrap_from_history.py` | 一次性 bootstrap：拉群历史，计算主人发言频率画像，初始化表情包库 |
| `tools/auto_reviewer.py` | 扫 `eval.jsonl` 里低分条目，自动生成 `failure_mode + constraint + BAD/OK 草稿` 用于打补丁 |
| `tools/prompt_lab.py` | 离线交互调优：让 agent 跑 `fixtures.jsonl`，人工打分，通过的回复流到 `examples.jsonl` |
| `tools/import_stickers_folder.py` | 从本地文件夹批量导入表情包，自动调视觉模型打标 |

## 快速开始

依赖：Python 3.10+、NapCat（或任意 OneBot v11 实现）、一个 OpenAI 兼容的 chat completions API key。

```powershell
# 1. 装依赖
pip install -r requirements.txt

# 2. 配环境变量（默认全部留空，自己填）
copy .env.example .env
notepad .env

# 3. 写人设
copy persona.example.txt persona.txt
notepad persona.txt        # 描述你的 bot 是个什么样的人

# 4. 启动
$env:PYTHONIOENCODING='utf-8'
python main.py
```

看到 `bot started on 0.0.0.0:8080 (agent=True)` 就是起来了。

NapCat / OneBot 客户端这边把 webhook 指过来：

```json
{
  "http": { "enable": true, "host": "0.0.0.0", "port": 3000 },
  "webhook": {
    "enable": true,
    "url": "http://127.0.0.1:8080/webhook/qq",
    "timeout": 5000
  }
}
```

## 配置

所有配置走 `.env`，关键项：

| 变量 | 说明 |
|---|---|
| `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` | 主对话模型。任何 OpenAI 兼容端点都行 |
| `ANTHROPIC_*` | 可选；走 Anthropic 兼容端点的私聊路径 |
| `BOT_QQ` / `BOT_NAME` | bot 自己的 QQ 号 + 显示名 |
| `OWNER_QQ` / `OWNER_NAME` / `OWNER_RELATIONSHIP` | 一个 bot 关系特别近的"主人"（可选） |
| `QQ_GROUPS` | 监听的群号，逗号分隔 |
| `VISION_MODEL` + `GLM_API_KEY` / `GLM_BASE_URL` | 图片/表情理解用的视觉模型，不填就退化成 OCR-only |
| `PERSONA_FILE` | 人设 prompt 文件路径（默认 `persona.txt`） |
| `FALLBACK_MODEL` + `RATE_THRESHOLD` | 高并发时自动降级到便宜模型 |

完整列表见 `.env.example`。

## 迭代循环（Hermes 风格）

prompt 结构是为了**让失败可调试**而设计的：

```
观察到 bad case
  ↓
定位是哪个 block 没管住（STYLE_GUIDE / REASONING_PROTOCOL / INTENT_RULES）
  ↓
在同类规则旁边加硬约束 + 反例
  ↓
往 feedback.jsonl 补一条 BAD/OK 对
  ↓
下次类似输入进来，动态 few-shot 检索会把这条捞出来塞进 prompt
```

`examples.jsonl` + `feedback.jsonl` 的检索用 2-char 中文 ngram + scenario tag + 时间衰减，所以哪怕每种失败模式只有 5-10 条样本也立刻能起作用。

## 隐私

可能含真实聊天内容的文件已经 gitignore：

```
.env                      # API key
eval.jsonl                # 自评原始轨迹
memory.json               # 长期记忆抽取结果
stickers.json             # 表情包索引（含样例聊天上下文）
stickers/auto/            # 下载下来的表情包二进制
owner_profile.json        # 主人发言频率画像
unknown_stickers.jsonl    # 待下载的表情 URL
candidates.jsonl          # auto-reviewer 产出
```

不要 push 这些。本仓库里提交的 `examples.jsonl` / `feedback.jsonl` / `tools/fixtures.jsonl` 都是**纯虚构样例**，只展示格式。

## License

[MIT](LICENSE)。

## 致谢

- Hermes 3 (NousResearch) —— "先思考再回复"的输出格式
- NapCat / OneBot v11 生态 —— QQ 协议层
- 开发过程中用到的若干 OpenAI 兼容模型供应商
