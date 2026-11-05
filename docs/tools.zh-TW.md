# `tools/` 指令碼

[English](tools.md) · [简体中文](tools.zh-CN.md) · 繁體中文 · [日本語](tools.ja.md) · [한국어](tools.ko.md) · [Español](tools.es.md) · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

`tools/` 裡的指令碼給從克隆執行 personagent 的人用。它們不隨安裝包提供，並從克隆讀取 `.env` 和 `runtime/`。用克隆的直譯器在倉庫根目錄執行：

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

日常工作用 `personagent` 子命令，不用指令碼：`personagent doctor`、`personagent learned` 和 `personagent eval`。要試一處提示詞改動，用 `personagent chat`；要衡量它，用 `personagent eval`。

| 指令碼 | 作用 | 需要 | 是否呼叫模型 | 狀態 |
|---|---|---|---|---|
| `import_stickers_folder.py` | 把一個圖片資料夾匯入表情包庫並逐張打標籤，這樣新庫不會從空開始。`--dry-run` 顯示數量，`--no-tag` 只複製檔案 | 一個圖片資料夾；打標籤還需要 `VISION_MODEL`、`VISION_API_KEY` 和 `VISION_BASE_URL` | 是，每張圖一次視覺呼叫，除非加 `--dry-run` 或 `--no-tag` | 受支援 |
| `bootstrap_from_history.py` | 用一個 QQ 群的歷史記錄讓新部署一次性起步。它生成管理員的表情包和訊息長度畫像，並把看到的表情包存入庫中 | 第三方 QQ 客戶端 NapCat 的 HTTP 服務，地址為 `QQ_ONEBOT_URL`（必填），以及 `ACCESS_GROUPS` 或 `--group` 裡的 QQ 群 | 否。執行中的機器人之後用視覺模型給存下的表情包打標籤 | 實驗性，僅 QQ 和 NapCat |
| `auto_reviewer.py` | 讀取 `runtime/eval.jsonl` 裡的低自評分，讓模型把每一條變成一對修改前後的對照。加 `--apply` 時會逐對詢問你是否加入共享反饋池 | `EVAL_ENABLED=true` 開一段時間，才有分數 | 是，每條審閱一次呼叫（`--limit`，預設 20）。`--dry-run` 不呼叫 | 實驗性。`--apply` 寫入所有聊天共用的池。只想為一個聊天批准修正，用 `personagent learned` |
| `evolution_benchmark.py` | 讓真實的 agent 在 `data/benchmark/` 的場景上跑幾輪，一次開啟自我改進迴圈，一次關閉，再比較兩者。`run` 負責執行，`ingest` 讀回評審分數 | `LLM_API_KEY`，以及一個不是被測模型的評審（`--judge export`、`openai` 或 `anthropic`，配 `BENCH_JUDGE_MODEL`） | 是，呼叫很多：每個場景、每輪、每組 | 實驗性 |
| `scenario_probe.py` | 用真實模型試驗候選基準場景，報告哪些能暴露基準需要的失敗 | `LLM_API_KEY`，一個形如 `data/benchmark/scenarios.train.en.jsonl` 的候選場景檔案，以及評審環節用的 `--judge-model` | 是，每個場景一次回覆、一次自評和一次評審呼叫 | 實驗性，用於構建基準 |
| `sticker_holdout_eval.py` | 用你手工標註的表情包衡量表情包審批門的穩定性和準確度 | `runtime/holdout.jsonl`（格式見 `tools/holdout.example.jsonl`）和三個 `VISION_*` 設定 | 是，圖片數 × `--runs`（預設 5）次視覺呼叫，30 張圖約 150 次 | 實驗性 |
| `package_smoke.py` | 端到端檢查已安裝的 `personagent` 命令：版本、`init --no-input`、`chat`、帶 `/health` 的 `run`，以及 `doctor --json` | 一個已安裝的 `personagent`（`--personagent PATH`），別的都不要 | 否，由替身伺服器應答 | 受支援。CI 在 Linux 和 Windows 上執行 |
| `welcome_smoke.py` | 端到端檢查已安裝的本地頁面：`start --no-browser`、儲存金鑰、和真實角色聊一次、第二次啟動複用頁面、乾淨退出 | 一個已安裝的 `personagent`（`--personagent PATH`），別的都不要 | 否，由同一個替身伺服器應答 | 受支援。CI 在 Linux 和 Windows 上執行 |
| `release_notes.py` | 對照 `pyproject.toml` 檢查釋出標籤，並列印該版本的 CHANGELOG 段落 | 標籤，比如 `v1.1.0` | 否 | 受支援。釋出工作流會執行它 |

實驗性指令碼是研究和維護用的輔助工具，可能改動或刪除，不設棄用期。呼叫模型的指令碼會花 `.env` 裡賬戶的額度；先讀 `--help`，有 `--dry-run` 的先試它。
