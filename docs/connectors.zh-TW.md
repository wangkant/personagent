# 聯結器協定

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · 繁體中文 · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · [Español](connectors.es.md) · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

agent 本身從不直接與聊天平台互動，這項工作由聯結器負責。聯結器登入一個平台，或登入一個涵蓋多個平台的框架，將收到的每則訊息轉換為中立的事件並傳送給 personagent，再將傳回的內容送出。所有與平台相關的處理都留在聯結器中，因此 agent 在每個平台上看到的格式都相同。

本儲存庫內建四個聯結器：

| 聯結器 | 可連接的對象 | 路徑 |
|---|---|---|
| 直連 | QQ 官方機器人、個人微信（iLink）、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat，不需要其他軟體。本機頁面和 `personagent up` 以單一處理程序執行它：`python -m persona_agent.direct`。 | `persona_agent/direct/` |
| AstrBot 外掛程式 | 第三方橋接程式 AstrBot 支援的平台。personagent 為 KOOK、飛書/Lark、釘釘、Slack、企業微信、Mattermost、Misskey、OneBot v11 等平台所管理的 AstrBot 會自動安裝外掛程式。已在執行的 AstrBot 請以 `personagent connect astrbot` 設定。也可以使用 AstrBot 的「從檔案安裝」上傳 GitHub Release 中的 `astrbot_plugin_personagent.zip`，再自行設定 `connector_token`。 | `integrations/astrbot/` |
| Satori | 所有 Satori 實作（Koishi 等第三方軟體）：QQ、Telegram、Discord、KOOK、Lark、釘釘、LINE、WhatsApp、Matrix、Zulip、電子郵件等。 | `integrations/satori/` |
| Matrix | Matrix 聊天室，並可透過第三方 mautrix 橋接連接至 WhatsApp、Signal、Messenger、Instagram、Google Messages 等。 | `integrations/matrix/` |

程式設計助理並非聊天平台，因此採用獨立的方式：一個 MCP 伺服器 `personagent mcp`，詳見[使用手冊](guide.zh-TW.md#程式設計助理)。

這四個聯結器都使用本頁所述的協定。撰寫新的聯結器時，只需要本頁和一個 HTTP 用戶端。`integrations/sdk/personagent_connector.py` 中的 Python 輔助工具會代為簽署請求並執行 outbox 迴圈。它接受基礎 URL、權杖和聯結器的 `connector_id`，並需要 `httpx`。其 [README](../integrations/sdk/README.zh-TW.md) 提供了一個完整範例。

## 在本機試用

```
personagent run --port 8080
curl http://127.0.0.1:8080/health
```

`personagent run` 會在 `127.0.0.1` 上提供下文的兩個端點。它從啟動橫幅所示主目錄的 `.env` 中讀取 `CONNECTOR_TOKEN`；`--home DIR` 可指定其他主目錄。

- `CONNECTOR_TOKEN` 為空時，agent 只接受本機上呼叫 `127.0.0.1` 或 `localhost` 的程式，這些程式不需傳送驗證標頭。`personagent init` 不會設定它。本機頁面、`personagent up` 和 `personagent connect astrbot` 會在它為空時寫入一個隨機值。
- 如需設定，請在 `.env` 中寫入一個足夠長的隨機值，例如 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 的輸出，為聯結器設定相同的值，然後重新啟動 agent。
- `GET /health` 傳回 `{"status": "ok", "agent_enabled": true}`，不產生任何費用。`"agent_enabled": false` 表示 agent 無法回覆（未設定 `LLM_API_KEY`，或 `AGENT_ENABLED=false`），此時每個事件都會得到 `owned: false`。`GET /health/details` 還會檢查模型和其他服務，可能產生少量費用。設定了權杖時，它要求帶上 `X-Personagent-Token` 標頭；未設定時只接受本機請求；其他請求會得到 `403` 和錯誤碼 `forbidden`。

## 設定

直連聯結器由本機頁面負責設定。另外三個聯結器使用相同的名稱，因此同一項設定在三者中的意義相同：

| 意義 | Satori | Matrix | AstrBot 外掛程式鍵 |
|---|---|---|---|
| personagent 的基礎 URL，例如 `http://127.0.0.1:8080`。聯結器會在其後加上 `/v1/events` 和 `/v1/outbox`。 | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| 共用權杖，與 agent 的 `CONNECTOR_TOKEN` 相同 | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| 此聯結器的 id（即下文的 `connector_id`） | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| 單一請求的最長時間，單位為秒 | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| 拉取 outbox | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| 要轉送的群組 | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| 要轉送其私訊的使用者 | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| 平台的伺服器 | `SATORI_URL` | `MATRIX_URL` | AstrBot 本身的設定 |

群組或私訊清單為空時，該類別一律不轉送。`*` 會轉送該類別的全部內容，並將事件標記為 `"prefiltered": false`，交由 agent 的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 決定。其餘設定請參閱各聯結器的 README。

## 位址

personagent 將每個 id 儲存為 `<platform>:<id>`，例如群組 `telegram:-1001234` 或使用者 `discord:4242`。`platform` 是聯結器為平台指定的名稱，使用小寫，且不含 `:`。

QQ 是唯一的例外，為了相容性而保留。其 id 儲存時不帶前綴（`123456`），在任何設定中寫成 `qq:123456` 意義都相同。如果聯結器接入 QQ，且希望學到的狀態與既有的 QQ 部署一致，請將其平台名稱加入 `CONNECTOR_QQ_PLATFORMS`。AstrBot 外掛程式的 QQ 配接器是 `aiocqhttp`。此處列出的平台，其 id 同樣以不帶前綴的形式儲存。

## 驗證

下列兩個端點使用同一套機制。agent 設定了 `CONNECTOR_TOKEN` 時，每個請求都須帶有四個請求標頭：

- `X-Personagent-Token`：權杖。
- `X-Personagent-Timestamp`：unix 秒數。與 agent 時鐘相差超過五分鐘的值會被拒絕。
- `X-Personagent-Nonce`：一個新的隨機值。重複使用的 nonce 會被拒絕。
- `X-Personagent-Signature`：`sha256=` 後接 `timestamp + "." + nonce + "." + body` 的十六進位 HMAC-SHA256，以權杖為金鑰。

簽章涵蓋實際傳送的請求本文位元組，因此任何以 UTF-8 編碼的有效 JSON 都能通過。建議使用標準化 JSON（鍵依序排列、使用緊湊分隔符號，非 ASCII 字元不跳脫），本儲存庫內附的聯結器也如此傳送，但 agent 並不要求。權杖同時也是簽署金鑰，因此不得寫入記錄檔。

未設定權杖時，agent 只接受直接呼叫 `127.0.0.1` 或 `localhost` 的本機程式。聯結器必須拒絕傳送至迴路 URL 以外的位址，除非是帶有權杖的 HTTPS URL。

## 傳入：`POST /v1/events`

每個請求帶來一則訊息，並傳回對該訊息的回覆。

```json
{
  "platform": "telegram",
  "conversation_type": "group",
  "conversation_id": "-1001234",
  "sender_id": "42",
  "sender_name": "Alex",
  "bot_id": "7000",
  "message_id": "881",
  "sent_at": 1790320000,
  "addressed": true,
  "text": "Nova, how was your day?",
  "segments": [
    {"type": "text", "text": "Nova, how was your day?"}
  ],
  "connector_id": "astrbot-7f3c",
  "reply_handle": "tg-bot:GroupMessage:-1001234",
  "capabilities": ["outbox", "quote_text"]
}
```

必填欄位為 `platform`、`conversation_type`（`group` 或 `dm`）、`sender_id`、`message_id` 和 `sent_at`，群組另需 `conversation_id`。`sent_at` 是平台為訊息標記的時間，單位為 unix 秒數，取整數（也接受純數字字串）。角色看到的每則訊息都附有這一時間。agent 啟動後，在某個平台的第一則訊息到達起兩分鐘內，如果群組訊息到達時已超過 10 分鐘，即視為重新啟動後補送的積壓訊息：只作為上下文保留，不予回覆。兩分鐘之後，較早的 `sent_at` 不再使訊息被擱下，因此時鐘偏慢的聯結器傳來的訊息仍會得到回覆。請傳送平台的原始 id，前綴由 agent 加上。

`addressed` 由聯結器設定。訊息提及機器人、回覆機器人的某則訊息，或依平台本身的規則屬於對機器人發言時，其值為 true。agent 本身也會留意文字中出現的名稱。它會將對自己訊息的引用或對機器人的 @ 視為可供學習的反應，因此回覆機器人的訊息須設定 `addressed`。對其他成員訊息的引用一律不視為對機器人的反應。轉傳訊息中對機器人的提及不算對機器人發言，因此請勿為此設定 `addressed`。

`sender_id` 等於 `bot_id` 的事件，表示機器人自己的訊息被回傳。agent 會直接捨棄而不讀取，並回應 `{"handled": false, "owned": true, "replies": []}`，讓聯結器本身的機器人邏輯也保持沉默。請在聯結器中略過這類事件。

片段依序排列：

| 類型 | 欄位 | 說明 |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | 提及某人。`user_id` 等於 `bot_id` 時，即為提及機器人。角色讀到的是 `name` 而非 id，因此請傳送 `name`。`name` 交給模型時標明為並非傳送者所寫的名字，因此永遠不會點名角色或構成指令。`forward` 片段之後對機器人的提及不算點名。 |
| `image` | `url` 或 `b64`，`sticker`（布林值） | `sticker` 標記以圖片形式傳送的貼圖。以 `b64` 傳送或標有 `sticker` 的群組圖片可收入貼圖庫；僅以 `url` 傳送的照片則不會收入。 |
| `emoji` | `name`, `id` | agent 無法看見的平台貼圖或自訂表情符號。`name` 是一般人對它的稱呼。 |
| `media` | `kind`, `name`, `transcript`, `emoji` | agent 無法看見的內容。`kind` 為 `voice`、`video`、`file`、`photo`（無法取得的圖片）或 `sticker`。檔案請附上 `name`，平台已轉寫的語音請附上 `transcript`，貼圖請附上 `emoji`。 |
| `forward` | `name` | 其後的片段轉傳自 `name`，而非傳送者本人所寫。`name` 可以為空。這些片段中的文字視為被轉傳者的話：其中的名字不算點名，也不會執行記憶指令。傳送者自己的評論請放在 `forward` 片段之前，或作為單獨的訊息傳送。 |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | 此訊息所引用的訊息。平台提供 `text` 時一律傳送。 |

媒體內容請以 `media` 片段傳送，不要寫成 `(sent a voice message)` 這類文字：角色會將這些文字視為傳送者本人輸入的內容。agent 會捨棄未知類型的片段。

下列選用欄位可啟用 agent 的更多功能：

| 欄位 | 意義 |
|---|---|
| `connector_id` | 此聯結器執行個體的固定 id。outbox 需要此欄位。 |
| `reply_handle` | 聯結器日後在未收到訊息的情況下聯繫此對話所需的任何資訊：AstrBot 的 `unified_msg_origin`、Matrix 聊天室 id，或 Satori 登入資訊加頻道 id。agent 將其視為不透明的值，依對話儲存，並在 outbox 投遞時交回。 |
| `capabilities` | 聯結器支援的功能。`outbox` 表示它會輪詢 outbox，並可主動傳送訊息。`quote_text` 表示回覆片段帶有被引用的文字。 |
| `prefiltered` | 聯結器已套用自己的允許清單時為 `true`（預設）。`false` 會讓 agent 的清單成為唯一的篩選條件。 |
| `proactive` | 將私訊事件標記為聯結器撰寫的提示，而非該使用者所說的話。請參閱「不經 outbox 主動發言」。 |

回應格式如下：

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`：依序傳送，每一項作為一則獨立的訊息。存在 `mention_user_id` 時，它是要提及的帶前綴 id。請以平台的方式呈現提及。帶有 `"reason": "excuse"` 的項目是模型出錯時角色在私訊中傳送的簡短說明，而非回覆；可以照常傳送，也可以作為錯誤處理。
- `owned`：agent 已接管此訊息，即此訊息已通過 agent 的允許清單，無論人設接下來如何應對。為 true 時，即使 `replies` 為空，也必須阻止其他機器人邏輯回覆，因為人設可能選擇了沉默。為 false 時，agent 未參與此訊息：此對話不在 agent 的允許清單中，或 agent 根本無法回覆（未設定 `LLM_API_KEY`，或 `AGENT_ENABLED=false`）。agent 無法回覆時，其記錄檔中會有一行 ERROR 註明原因。重複的 `message_id` 仍由 agent 接管（見下文「重複訊息」）。
- `handled`：本請求自身的這一輪送出了內容（回覆或記憶指令的回覆）時為 true，用於記錄與統計。請依據 `owned` 判斷，且無論 `handled` 為何值，都傳送 `replies` 中的全部內容：例如簡短說明就隨 `handled: false` 傳回。

聯結器會遇到以下組合：

| 回應 | 情形 | 聯結器的處理 |
|---|---|---|
| `handled: true`、`owned: true`、有回覆 | 正常回覆。 | 傳送 `replies`，並讓其他機器人邏輯保持沉默。 |
| `handled: false`、`owned: true`、`replies: []` | 人設保持沉默；事件是機器人自身訊息的回傳；此訊息已併入後一則訊息的一輪（見「連續傳送的訊息」）；記憶指令的回覆稍後經 outbox 送達；帶有 `proactive` 的群組事件；重複的 `message_id`（重新投遞）。 | 不傳送任何內容，並讓其他機器人邏輯保持沉默。 |
| `handled: false`、`owned: true`、一則帶 `"reason": "excuse"` 的回覆 | 私訊中模型出錯。 | 傳送它，或作為錯誤處理。 |
| `handled: false`、`owned: false`、`replies: []` | 此對話不在允許清單中，或 agent 無法回覆。 | 此訊息由你處理。 |

其他規則：

- **重複訊息。** agent 會記住它最近接納的 2,000 則訊息，不分對話。鍵由 `platform`、對話（群組為 `conversation_id`，私訊為 `sender_id`）和 `message_id` 組成；`CONNECTOR_QQ_PLATFORMS` 中的平台只使用不帶前綴的 `message_id`。此清單會不時儲存到主目錄的 `runtime/` 資料夾，關閉時也會儲存，因此重新啟動後依然有效。再次傳送的訊息（例如平台重新投遞，或逾時後的重試）會立即得到 `{"handled": false, "owned": true, "replies": []}`，即使第一次請求仍在進行。對此請勿傳送任何內容；其回覆只會出現在第一次請求的回應中。呼叫端放棄後，這一輪仍會繼續，因此逾時後回覆即會遺失；請預留足夠的時間，而不要重試。被允許清單拒絕的訊息不會被記住，再次傳送時會重新判斷。
- **連續傳送的訊息。** 同一對話中在短暫防彈跳時間內抵達的訊息（2.5 秒；群組中只喊人設名字的訊息之後為 5 秒）會合併為一輪，一併回覆。在進行中的一輪之後等候的訊息，同樣會併入下一輪。只有最新一則訊息的請求會帶回回覆；之前的每個請求都傳回 `{"handled": false, "owned": true, "replies": []}`。在群組中，回覆的 `mention_user_id` 指向人設所回覆的人，此人傳送的可能是較早的訊息，而不是帶回回覆的那個請求的訊息。記憶指令不會合併，見最後一條。
- 請求會持續到這一輪結束為止，也就是一小段防彈跳時間加上模型的處理時間。無論群組或私訊，一輪中所有的模型呼叫（含重試）共用 1.5 × `LLM_TIMEOUT_S` 的時間預算；如果訊息抵達時，同一對話的上一輪仍在思考，它會先等候該輪結束，再開始處理。請至少預留 3 × `LLM_TIMEOUT_S` 秒（預設為 360 秒）。
- 如果記憶指令（例如「記住……」）抵達時，同一對話的某一輪仍在思考，它會等候該輪結束後才取得回覆。宣告了 `outbox` 的聯結器會立即收到 `{"handled": false, "owned": true, "replies": []}`，回覆稍後以 `follow_up` 投遞送達。未宣告 `outbox` 時，回覆會隨某個回應傳回：可能是該請求本身的回應，也可能是同一對話中另一個正在等候的請求的回應，因此一個回應中可能包含提及事件傳送者以外之人的回覆。

## Outbox：`POST /v1/outbox`

有些訊息並非對請求的回覆，例如定時的開場白、被否定後的追問、排在某一輪之後的記憶指令回覆，以及群組中模型無法使用時的說明。agent 依對話將它們排入佇列，由宣告了 `outbox` 的聯結器拉取，因此位於 NAT 或防火牆後方的聯結器也能正常運作。以不帶前綴的 QQ id 儲存的對話（請參閱「位址」）在其聯結器拉取期間也使用 outbox。否則，設定了 `QQ_ONEBOT_URL` 時，它們會透過 NapCat 的 HTTP API 傳送。

請求：

```json
{
  "kind": "outbox.pull",
  "connector_id": "astrbot-7f3c",
  "wait_s": 25,
  "max_deliveries": 10,
  "acks": [
    {"delivery_id": "d_5c1f...", "status": "sent", "sent_items": 2}
  ]
}
```

agent 最多會將請求保留 `wait_s` 秒（上限為 30），直到有內容排入佇列，然後回應：

```json
{
  "deliveries": [
    {
      "delivery_id": "d_9a07...",
      "conversation_key": "telegram:-1001234",
      "reply_handle": "tg-bot:GroupMessage:-1001234",
      "platform": "telegram",
      "conversation_type": "group",
      "conversation_id": "-1001234",
      "reason": "proactive",
      "expires_in_s": 300,
      "items": [{"type": "text", "text": "anyone still up?"}]
    }
  ],
  "next_wait_s": 25
}
```

`items` 的格式與 `replies` 相同。`reason` 為 `proactive`、`follow_up` 或 `excuse`，`conversation_type` 為 `group` 或 `dm`。`conversation_key` 是 agent 儲存此對話所用的鍵，例如私訊的 `private:telegram:42`。`conversation_id` 是事件帶來的原始 id，私訊時即為使用者 id。agent 會記住每個對話中最近一則被接受事件的 `reply_handle`、`connector_id` 和 `capabilities`，因此對話只要傳送過一則訊息，即可聯繫。有一項例外，用於保留拉取 outbox 的聯結器：來自不具備 `outbox` 能力之聯結器的事件，不會取代另一個具備此能力的聯結器為同一對話儲存的資訊。因此，即使其他程式（例如程式設計助理）曾在該對話中發言，拉取 outbox 的聯結器仍可聯繫該對話。來自同一聯結器的事件，或來自任何宣告了 `outbox` 之聯結器的事件，仍照常取代已儲存的資訊。

本機頁面本身也是一個 outbox 聯結器，其 `connector_id` 為 `local-welcome`。它只接收送往本頁面對話的投遞，並將其顯示在「開始聊天」檢視中。

請在下一次拉取的 `acks` 中回報每次投遞：

| `status` | 意義 |
|---|---|
| `sent` | 所有項目均已送出。 |
| `partial` | 前 `sent_items` 項已送出。 |
| `failed` | 未送出任何內容。 |
| `expired` | 未在 `expires_in_s` 內開始傳送。 |
| `refused` | 聯結器不再允許此對話。 |
| `unsupported` | 平台無法主動向此對話傳送訊息。 |

規則：

- **最多一次。** 無論 ack 結果如何，agent 對每次投遞只交出一次，絕不重送。請保留最近數百個 `delivery_id`，同一個絕不傳送兩次。
- **依序傳送。** 同一對話的投遞依收到的順序傳送。不同對話可以平行傳送。
- **僅計入已確認的投遞。** agent 將未確認的投遞視為未傳送，只將已確認的記為已傳送。它會等候 ack 直到你下一次拉取，且在交出投遞後最多等候 `expires_in_s` 再加 60 秒。請在一批傳送完畢後再拉取。
- **存活。** 90 秒內未拉取的聯結器會被視為已離線。在它再次拉取之前，不會為其對話排入佇列，已排入佇列或已交給它但未確認的內容均以未傳送結束。一批送達後請立即再次拉取，並在該次拉取中附上這一批的確認。
- **`unsupported` 會持續生效。** 收到此確認後，agent 會停止為該對話排入佇列，直到某個事件帶來不同的 `reply_handle`。
- **請求本文類型。** 簽章不涵蓋 URL 路徑。因此，agent 會拒絕傳送至 outbox 端點的事件請求本文，以及傳送至事件端點的 `outbox.pull` 請求本文，並傳回 `400` 和錯誤碼 `invalid_schema`。事件可以帶有 `"kind": "event"`。帶有其他 `kind` 的事件會被拒絕。

不含 `code` 的 404 表示 agent 不提供 outbox。帶有錯誤碼 `outbox_disabled` 的 `404` 表示營運者已透過 `CONNECTOR_OUTBOX_ENABLED` 將其關閉。兩種情況下都應間隔較長時間再拉取。

## 錯誤

發生錯誤時傳回 `{"error": "...", "code": "..."}`。`code` 保持穩定，請依據它分支處理。`error` 是供查看記錄檔的人閱讀的句子，措辭可能變更。

| 狀態碼 | `code` | 端點 | 原因 |
|---|---|---|---|
| 400 | `invalid_schema` | 兩者 | 請求本文不是 JSON 物件；缺少必填欄位或欄位為空；`conversation_type` 既不是 `group` 也不是 `dm`；`segments` 不是清單；請求本文類型錯誤（見「請求本文類型」）；拉取請求沒有可用的 `connector_id`（最多 128 個字元），`wait_s` 或 `max_deliveries` 不是數字，或 ack 超過 1,000 筆。 |
| 400 | `client_disconnected` | 兩者 | 呼叫端在傳送請求本文時中斷了連線。 |
| 403 | `unauthenticated` | 兩者 | 未設定 `CONNECTOR_TOKEN`，且呼叫端不在 agent 所在的電腦上。 |
| 403 | `non_local_request` | 兩者 | 未設定 `CONNECTOR_TOKEN`，且請求帶有本機程式不會傳送的標頭：`Origin`、值不為 `none` 的 `Sec-Fetch-Site`、`localhost`、`127.0.0.1` 和 `::1` 以外的 `Host`，或 `X-Forwarded-For` 之類的代理標頭。 |
| 403 | `invalid_envelope` | 兩者 | 已設定 `CONNECTOR_TOKEN`，而權杖或某個標頭缺失或錯誤、簽章不符、時間戳記相差超過五分鐘、nonce 已用過，或重送防護已滿。 |
| 403 | `stale_event` | events | `sent_at` 不是整數秒，或與 agent 的時鐘相差超過 `CONNECTOR_MAX_EVENT_AGE_S`（24 小時），無論偏早或偏晚。以毫秒為單位的值會落在遙遠的未來。 |
| 404 | `outbox_disabled` | outbox | `CONNECTOR_OUTBOX_ENABLED=false`，或 agent 已關閉（`AGENT_ENABLED=false`）。 |
| 408 | `body_timeout` | 兩者 | 請求本文超過 30 秒仍未送達。 |
| 413 | `body_too_large` | 兩者 | 請求本文大於 `SERVER_MAX_BODY_BYTES`（8,000,000 位元組），通常是內嵌圖片所致。 |
| 429 | `capacity_exceeded` | 兩者 | 同時請求過多：事件端點進行中的輪次超過 `CONNECTOR_MAX_INFLIGHT`（預設 64），或 outbox 的拉取超過 16 個。`Retry-After` 回應標頭指出需等候的秒數：3，outbox 為 5。 |

路徑錯誤會得到 `404 {"detail": "Not Found"}`，方法錯誤（例如 `GET /v1/events`）會得到 `405 {"detail": "Method Not Allowed"}`。這兩種回應來自 Web 框架，不含 `code`。

## 不經 outbox 主動發言

無法輪詢的聯結器也可以主動發起私訊。由它自己的排程器，例如 AstrBot 外掛程式任務或 cron 項目，向 `/v1/events` 傳送一個帶有 `"proactive": true` 的一般私訊事件。agent 會將文字視為提供給人設的提示（「對方已沉默一整天；今天早上有考試」），截斷至 500 字元，且絕不將其儲存為該使用者所說的話。這一輪仍由引擎的主動發言指令決定，人設也可能保持沉默。如果人設開口，回覆會在回應中傳回，由排程器轉送。

此事件需要聯結器一般事件所帶的全部內容：簽章請求標頭、所有必填欄位、與聯結器傳送給該使用者時相同的 `platform` 和原始 `sender_id`、非空白的文字，以及每次都不同的 `message_id`。`message_id` 重複的事件不會再次處理，並會得到 `owned: true` 且沒有回覆。此提示與 agent 自己的開場白共用同一個私訊冷卻時間（`PROACTIVE_DM_COOLDOWN_S`），且不計為該使用者的活動。

務必設定此標記；未設定時，agent 會將提示儲存為該使用者所說的話。帶有此標記的群組事件會被接管（`owned: true`，因此聯結器會讓自己的機器人保持沉默），並直接捨棄而不讀取。

## 功能與降級

| 缺少 | 影響 |
|---|---|
| `outbox` | 沒有定時開場白、沒有追問，群組中模型呼叫失敗時也沒有說明訊息。設定了 `QQ_ONEBOT_URL` 且可連線時，QQ id 仍可透過 NapCat 取得這些功能。私訊的說明訊息會在回應的 `replies` 中傳回，不需要 outbox。 |
| `quote_text` | agent 只能理解對它自己看過之訊息的引用。 |
| `reply_handle` | 與缺少 `outbox` 相同。 |
| `addressed` 錯誤 | 人設會將對它說的話當成背景閒聊。 |

## 撰寫聯結器

1. 從平台接收訊息。略過機器人自己的訊息和非訊息事件（加入群組、收回訊息、戳一戳）。
2. 建立上述格式的事件。依平台本身的提及與回覆規則設定 `addressed`。
3. 簽署並傳送事件。依序傳送 `replies`，`owned` 為 true 時讓其他機器人邏輯保持沉默。
4. 如果平台支援主動傳送，請加上 `connector_id`、`reply_handle` 和 `capabilities: ["outbox"]`，然後執行拉取迴圈：拉取，透過 `reply_handle` 送出每次投遞，並在下一次拉取時確認。

`integrations/sdk/personagent_connector.py` 負責第 3 和第 4 步。其 [README](../integrations/sdk/README.zh-TW.md) 以一個簡短的程式示範這兩步。
