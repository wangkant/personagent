# astrbot_plugin_personagent

[English](README.md) · **簡體中文**

這是連線 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 與 [personagent](https://github.com/wangkant/personagent) 的外掛。它把允許的訊息轉發給 personagent，再把 personagent 的回覆發回聊天。

## 你需要它嗎

QQ、微信、Telegram、Discord 不需要這個外掛，personagent 會直接連線它們，不經過 AstrBot。執行 `personagent` 開啟本地頁面，在「連線平臺」裡新增即可。

只有 AstrBot 負責收發訊息時才需要這個外掛，分兩種情況：

- **在 personagent 頁面裡新增其他平臺**：KOOK、飛書、釘釘、Slack、企業微信智慧機器人、Mattermost、Misskey，以及「高階」一欄裡的平臺，都經由 AstrBot 接入。頁面會替你下載並執行 AstrBot，並裝好這個外掛，你無需在這裡做任何操作。
- **使用你已有的 AstrBot**，保留它原有的平臺和外掛。按下面的步驟安裝。

## 功能

- 把白名單內群聊和私聊的訊息轉發到 personagent 的 `POST /v1/events`，再把回覆發回聊天。回覆可以包含文字和圖片，群聊中按 personagent 的要求 @ 對方。
- 按各平臺介面卡的實際格式解析訊息，包括誰被 @、引用了哪條訊息、表情和圖片、語音，以及訊息的實際傳送時間。
- 拉取 personagent 的 outbox，傳送它主動說的話，例如定時開場、追問，以及模型不可用時在群裡的致歉。
- personagent 接管某個會話後，阻止 AstrBot 自帶的模型繼續回答（`block_default`），避免兩個聲音同時回覆。

人設、記憶、防抖和「打字」節奏都由 personagent 處理。外掛只負責格式轉換。

## 裝進你自己的 AstrBot

先啟動一次 AstrBot，讓它生成 data 資料夾（其中有 `cmd_config.json`、`plugins`、`config`），再安裝 personagent（`python -m pip install personagent`）。然後執行：

```bash
personagent connect astrbot
```

這條命令會自動查詢 AstrBot 的 data 資料夾，找不到時可以替你下載 AstrBot。接著它會詢問 AstrBot 是否執行在 Docker 裡、機器人加入哪個平臺（AstrBot 裡尚未配置時還會要該平臺的 Token）、哪些群、管理員是誰、允許哪些人私聊；經 NapCat 接 QQ 時還會詢問機器人賬號的 QQ 號。最後它複製外掛，生成同一個 `CONNECTOR_TOKEN` 寫入兩邊，並寫好白名單。`personagent init --terminal` 的最後一步也提供同樣的流程。完成後重啟 AstrBot，再執行 `personagent run`（只啟動服務本身）。

如果不想逐項回答，可以直接指定資料夾：`personagent connect astrbot <data 資料夾>`，要經 NapCat 接 QQ 時再加 `--qq`。這種方式首次連線時白名單為空，需要在 AstrBot 網頁的外掛設定裡填寫 `groups`（群）和 `dm_users`（允許私聊的人）。這條命令可以重複執行，已有的白名單會保留。

也可以從 personagent 的[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下載 `astrbot_plugin_personagent.zip`，在 AstrBot 外掛頁透過「從檔案安裝」上傳。之後把 `connector_token` 設為 personagent 的 `.env` 中的 `CONNECTOR_TOKEN`，並填好白名單。AstrBot 與 personagent 不在同一臺電腦上時，`personagent_url` 必須是 HTTPS 地址（見下文「AstrBot 在 Docker 裡」）。升級時用同樣的方式上傳新版 zip。AstrBot 4.29 及以後的版本會直接替換舊版；更早的版本需要先解除安裝舊外掛，解除安裝時不要勾選「同時刪除外掛配置檔案」。

手動安裝：把本資料夾複製到 `<AstrBot data>/plugins/astrbot_plugin_personagent/`，重啟 AstrBot，然後在網頁裡填寫設定。

外掛**預設不轉發任何訊息**：白名單為空時，AstrBot 的表現與未安裝外掛時相同。群號和使用者 ID 按 AstrBot 顯示的格式填寫，在聊天中傳送 `/sid` 即可檢視。不帶字首的 ID 對所有介面卡生效；`qq_official:ID` 只對該介面卡生效，`qq_official:*` 放行該介面卡上的全部同類會話。

## 設定

| 設定 | 預設值 | 說明 |
| --- | --- | --- |
| `personagent_url` | `http://127.0.0.1:8080` | personagent 的基礎地址，外掛會自動加上 `/v1/events` 和 `/v1/outbox`。只能是本機地址，或已設定 `connector_token` 的 HTTPS 地址。 |
| `connector_token` | 空 | 共享金鑰，必須與 personagent 的 `CONNECTOR_TOKEN` 一致。地址不是本機時必須填寫。 |
| `timeout_s` | `420` | 每次請求最多等待的秒數。應大於 personagent 的 `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`，見下文「超時」。 |
| `excluded_platforms` | `["aiocqhttp"]` | 不轉發的介面卡。要經 NapCat 接 QQ，需從中刪除 `aiocqhttp`，見下文「經 NapCat 接 QQ」。 |
| `groups` | 空 | 要轉發的群 ID。為空時不轉發任何群；`介面卡:ID` 或 `介面卡:*` 只對一個介面卡生效；單獨的 `*` 表示全部轉發，由 personagent 的 `ACCESS_GROUPS` 決定是否回應。 |
| `dm_users` | 空 | 允許私聊的傳送者 ID。為空時不轉發私聊；`介面卡:ID` 或 `介面卡:*` 只對一個介面卡生效；單獨的 `*` 表示全部轉發，由 personagent 的 `ACCESS_DM_USERS` 決定是否回應。 |
| `block_default` | 開 | personagent 接管會話後，不再讓 AstrBot 自帶的模型回答。 |
| `forward_quoted_text` | 開 | 有人引用訊息時，把被引用的文字和作者一併發給 personagent（平臺提供時）。 |
| `quote_max_chars` | `200` | 被引用文字的最大長度，超出部分截斷。 |
| `max_inline_image_bytes` | `4000000` | 內嵌傳送圖片的最大位元組數，超過時只傳送 `(sent an image)` 提示。應小於 personagent 的 `VISION_MAX_IMAGE_BYTES`。 |
| `outbox_enabled` | 開 | 拉取併傳送 personagent 主動說的話。 |
| `outbox_wait_s` | `25` | 每次拉取 outbox 最多等待的秒數，上限 30。 |
| `connector_id` | 空 | 這個 AstrBot 在 personagent 中的標識。留空時自動生成並儲存；兩個 AstrBot 連線同一個 personagent 時，標識必須不同。 |

## 經 NapCat 接 QQ

QQ 官方機器人由 personagent 直接連線，不需要 AstrBot。本節只適用於用 NapCat（或其他 OneBot v11 實現）登入 QQ 賬號、經 AstrBot 的 `aiocqhttp` 介面卡接入的情況。在 personagent 頁面裡新增 OneBot v11 時，頁面會自動從 `excluded_platforms` 刪除 `aiocqhttp` 並設定 `CONNECTOR_QQ_PLATFORMS`。

1. 從 `excluded_platforms` 刪除 `aiocqhttp`，把 QQ 群號填入 `groups`。
2. 在 personagent 的 `.env` 中設定 `CONNECTOR_QQ_PLATFORMS=aiocqhttp` 和 `QQ_BOT_ID`（機器人賬號的 QQ 號）。`CONNECTOR_QQ_PLATFORMS` **不能省略**：缺少它時，personagent 會把所有 QQ 會話記在帶 `aiocqhttp:` 字首的 ID 下，原有 QQ ID 下學到的內容不再匹配，而且事後無法遷移。`personagent connect astrbot <data 資料夾> --qq` 會刪除 `aiocqhttp` 並設定 `CONNECTOR_QQ_PLATFORMS`；不指定資料夾執行時，它還會詢問 `QQ_BOT_ID`。
3. 如果 NapCat 還在把事件直接發給 personagent 的 `/v1/onebot`，請關閉。這條路線已棄用，兩者同時開啟會讓每條訊息被處理兩次。
4. 由於 QQ 的 ID 不帶字首，personagent 自身的 QQ 設定依然生效：`ACCESS_GROUPS` 中列出了 QQ 群時，只回應列出的群（未列出任何 QQ 群則回應所有 QQ 群）；QQ 私聊只回應 `ADMIN_IDS` 中的管理員或 `ACCESS_DM_USERS` 中的人。以後新增 QQ 群時，要同時加入外掛的 `groups` 和 `ACCESS_GROUPS`。

NapCat 的 HTTP 服務是可選的。開啟後把它的地址填入 `QQ_ONEBOT_URL`，personagent 就能補回離線期間漏掉的 @（這同樣需要 `QQ_BOT_ID`）。外掛在拉取 outbox 時，主動訊息、追問和群裡的致歉都經外掛傳送；否則在設定了該地址的前提下，直接經 NapCat 傳送。

這條路線的簡要步驟見 [docs/deploy.zh-CN.md 的「第三方路線：AstrBot + NapCat」](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md#第三方路線astrbot--napcat)。

讓 AstrBot 接入訊息較多的 QQ 群之前，請檢查 AstrBot 自身的兩項設定，它們在外掛之前生效：`platform_settings.rate_limit` 預設每 60 秒 30 條，超出的訊息會被延遲處理，可以調高或關閉；`content_safety.internal_keywords` 預設開啟，會丟棄命中關鍵詞的訊息，包括角色本該回答的訊息。

## AstrBot 在 Docker 裡

在容器內，`127.0.0.1` 指向容器自身，外掛無法訪問宿主機上的 personagent；而發往其他地址的明文 `http://` 請求會被外掛拒絕。可以任選一種方式解決：

- 讓 AstrBot 使用主機網路：在 compose 檔案中寫 `network_mode: host`，或使用 `docker run --network host`。Docker Desktop 需要 4.34 或更高版本，並開啟 host networking。同一 compose 檔案中的 NapCat 也要使用主機網路。
- 為 personagent 提供一個 HTTPS 地址（反向代理或隧道），再用 `personagent connect astrbot <data 資料夾> --url https://你的地址` 寫入外掛設定。

personagent 執行在另一臺機器上時，同樣需要 HTTPS 地址，並在兩邊設定相同的 token。在 personagent 前面加反向代理或隧道之前，請先在兩邊設好 token。

## 超時

每次請求都要等 personagent 完成一個完整的回合，包括一小段防抖時間，以及每次模型呼叫和重試。`timeout_s` 用盡後，personagent 仍會完成這個回合並保留學到的內容，但這條回覆不會被任何人看到，AstrBot 自帶的模型還會以另一種口吻回答同一條訊息。

personagent 的預設值為 `LLM_TIMEOUT_S=120`、`LLM_MAX_RETRIES=2`，最壞情況下一個回合超過 360 秒，外掛預設的 420 秒足以覆蓋。如果在 personagent 中調大了這兩項，`timeout_s` 也要相應調大。

## 出了問題

外掛在 AstrBot 日誌中的訊息都以 `personagent:` 開頭。

| 日誌 | 處理方法 |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` 是發往其他主機的明文 HTTP，或未設定 token 的 HTTPS。見上文「AstrBot 在 Docker 裡」。 |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` 為空或與 personagent 的 `CONNECTOR_TOKEN` 不一致；兩臺機器的時鐘相差超過 5 分鐘；或中間的代理改動了請求內容。 |
| `agent refused the request (403): stale or invalid sent_at` | 訊息太舊，通常是 AstrBot 恢復連線後一次性補發了積壓的訊息。 |
| `agent refused the request (403): authentication required` 或 `only local requests accepted` | personagent 未設定 `CONNECTOR_TOKEN`，而請求並非來自本機。在兩邊設定相同的 token。 |
| `agent at capacity (429)` | personagent 同時處理的回合已達上限。如果經常出現，可調大它的 `CONNECTOR_MAX_INFLIGHT`。 |
| `agent rejected the body as too large (413)` | 通常是圖片過大。調大 personagent 的 `SERVER_MAX_BODY_BYTES`。 |
| `timed out waiting for the agent` | 見上文「超時」。 |
| `agent request failed ...` | 通常是 personagent 沒有執行，或 `personagent_url` 填錯了。它是基礎地址，不要帶 `/v1/events`。 |
| `outbox: agent has no outbox ...` | personagent 關閉了 `CONNECTOR_OUTBOX_ENABLED`。 |

如果 AstrBot 自帶的模型突然以另一種口吻回覆，說明外掛沒有連上 personagent，或 personagent 沒有接管這個會話。請先對照上表排查，再執行 `personagent doctor`。如果 personagent 是由本地頁面啟動的，開啟頁面上的「動態」，看訊息有沒有到達、它為什麼沒開口；用 `personagent run` 啟動的，看它的終端輸出。更多排查步驟見 [docs/deploy.zh-CN.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md#機器人不說話)。

各平臺的支援情況、outbox 和請求籤名的完整說明見英文版 [README.md](README.md)。
