# `tools/` 腳本

[English](tools.md) · [简体中文](tools.zh-CN.md) · 繁體中文 · [日本語](tools.ja.md) · [한국어](tools.ko.md) · [Español](tools.es.md) · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

`tools/` 中的腳本供以 Git 複製的原始碼執行 personagent 的使用者使用。這些腳本不隨安裝套件提供，並從複製的儲存庫讀取 `.env` 和 `runtime/`。請在儲存庫根目錄以該複製環境的直譯器執行：

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

日常操作請使用 `personagent` 的子指令，而非腳本：`personagent doctor`、`personagent learned` 和 `personagent eval`。如需試用某項提示詞修改，請使用 `personagent chat`；如需衡量其效果，請使用 `personagent eval`。

| 腳本 | 用途 | 需求 | 是否呼叫模型 | 狀態 |
|---|---|---|---|---|
| `import_stickers_folder.py` | 將一個圖片資料夾匯入貼圖庫，並逐張加上標籤，使新的貼圖庫不必從零開始。`--dry-run` 只顯示數量，`--no-tag` 只複製檔案 | 一個圖片資料夾；加上標籤另需 `VISION_MODEL`、`VISION_API_KEY` 和 `VISION_BASE_URL` | 是，每張圖片呼叫一次視覺模型，加上 `--dry-run` 或 `--no-tag` 時除外 | 受支援 |
| `bootstrap_from_history.py` | 以一個 QQ 群組的歷史訊息，為新部署進行一次性的初始化。它會產生管理員的貼圖使用與訊息長度概況，並將出現過的貼圖存入貼圖庫 | 第三方 QQ 用戶端 NapCat 的 HTTP 服務，位址為 `QQ_ONEBOT_URL`（必填），以及 `ACCESS_GROUPS` 或 `--group` 中的 QQ 群組 | 否。執行中的機器人之後會以視覺模型為存入的貼圖加上標籤 | 實驗性，僅限 QQ 與 NapCat |
| `auto_reviewer.py` | 讀取 `runtime/eval.jsonl` 中自評分數偏低的項目，由模型將每一項改寫為一組修改前後的對照。加上 `--apply` 時，會逐組詢問你是否加入共用回饋池 | 須先開啟 `EVAL_ENABLED=true` 一段時間，以累積分數 | 是，每個項目審閱時呼叫一次（`--limit`，預設 20）。`--dry-run` 不呼叫模型 | 實驗性。`--apply` 會寫入所有聊天共用的回饋池。如只需為單一聊天核准修正，請使用 `personagent learned` |
| `evolution_benchmark.py` | 讓實際的 agent 在 `data/benchmark/` 的場景上執行數輪，一次開啟自我改進迴圈，一次關閉，再比較兩者的結果。`run` 負責執行，`ingest` 讀回裁判的評分 | `LLM_API_KEY`，以及一個不同於受測模型的裁判（`--judge export`、`openai` 或 `anthropic`，搭配 `BENCH_JUDGE_MODEL`） | 是，呼叫次數很多：每個場景、每一輪、每一組都會呼叫 | 實驗性 |
| `scenario_probe.py` | 以實際模型試驗候選的基準場景，報告哪些場景能引發基準測試所需的失敗 | `LLM_API_KEY`、一個格式同 `data/benchmark/scenarios.train.en.jsonl` 的候選場景檔案，以及裁判環節使用的 `--judge-model` | 是，每個場景各呼叫一次回覆、一次自評和一次裁判 | 實驗性，用於建立基準測試 |
| `sticker_holdout_eval.py` | 以你手動標註的貼圖，衡量貼圖審核關卡的穩定性與準確度 | `runtime/holdout.jsonl`（格式請參閱 `tools/holdout.example.jsonl`）及三項 `VISION_*` 設定 | 是，視覺模型呼叫次數為圖片數 × `--runs`（預設 5），30 張圖片約 150 次 | 實驗性 |
| `package_smoke.py` | 端對端檢查已安裝的 `personagent` 指令：版本、`init --no-input`、`chat`、帶 `/health` 的 `run`，以及 `doctor --json` | 一個已安裝的 `personagent`（`--personagent PATH`），無其他需求 | 否，由模擬伺服器回應 | 受支援。CI 在 Linux 和 Windows 上執行 |
| `welcome_smoke.py` | 端對端檢查已安裝的本機頁面：`start --no-browser`、儲存金鑰、與實際角色聊天一次、第二次啟動時沿用頁面，以及正常結束 | 一個已安裝的 `personagent`（`--personagent PATH`），無其他需求 | 否，由同一個模擬伺服器回應 | 受支援。CI 在 Linux 和 Windows 上執行 |
| `window_smoke.py` | 在臨時主目錄上開啟實際的應用程式視窗，在視窗中完成頁面設定並進行聊天，然後關閉視窗 | 在 macOS 和 Linux 上，須以應用程式擴充功能安裝 `personagent`（`pip install "personagent[app]"`）；在 Linux 上還需要顯示環境，例如 `xvfb-run` | 否，由同一個模擬伺服器回應 | 受支援。CI 在 Linux、macOS 和 Windows 上執行 |
| `release_notes.py` | 對照 `pyproject.toml` 檢查發布標籤，並輸出該版本的 CHANGELOG 段落 | 標籤，例如 `v1.1.0` | 否 | 受支援。發布工作流程會執行此腳本 |
| `locale_gaps.py` | 統計 `persona_agent/locales/` 中每種語言已翻譯的句子數量，範圍涵蓋終端機設定精靈、終端機聊天及示範所用的句子。指定語言代碼（例如 `ja`）時，會列出尚未翻譯、將以英文顯示的句子 | 無 | 否 | 受支援。有缺漏時 `tests/test_locales.py` 會失敗 |

實驗性腳本是供研究和維護使用的輔助工具，可能變更或移除，不另設棄用期。呼叫模型的腳本會消耗 `.env` 中帳戶的額度；請先閱讀 `--help`，提供 `--dry-run` 的腳本請先以此試用。
