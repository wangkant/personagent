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

這四個聯結器都使用本頁所述的協定。撰寫新的聯結器時，只需要本頁和一個 HTTP 用戶端。`integrations/sdk/personagent_connector.py` 中的 Python 輔助工具會代為簽署請求並執行 outbox 迴圈。它接受基礎 URL、權杖和聯結器的 `connector_id`，並需要 `httpx`。

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

請求本文為標準化 JSON：UTF-8、鍵依序排列、使用緊湊分隔符號，非 ASCII 字元不跳脫。權杖同時也是簽署金鑰，因此不得寫入記錄檔。

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

必填欄位為 `platform`、`conversation_type`（`group` 或 `dm`）、`sender_id`、`message_id` 和 `sent_at`，群組另需 `conversation_id`。`sent_at` 是平台為訊息標記的時間，單位為 unix 秒數。請傳送平台的原始 id，前綴由 agent 加上。

`addressed` 由聯結器設定。訊息提及機器人、回覆機器人的某則訊息，或依平台本身的規則屬於對機器人發言時，其值為 true。agent 本身也會留意文字中出現的名稱。它會將對自己訊息的引用或對機器人的 @ 視為可供學習的反應，因此回覆機器人的訊息須設定 `addressed`。對其他成員訊息的引用一律不視為對機器人的反應。

`sender_id` 等於 `bot_id` 的事件，表示機器人自己的訊息被回傳。agent 會直接捨棄而不讀取，並回應 `{"handled": false, "owned": true, "replies": []}`，讓聯結器本身的機器人邏輯也保持沉默。請在聯結器中略過這類事件。

片段依序排列：

| 類型 | 欄位 | 說明 |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | 提及某人。`user_id` 等於 `bot_id` 時，即為提及機器人。 |
| `image` | `url` 或 `b64`，`sticker`（布林值） | `sticker` 標記以圖片形式傳送的貼圖。 |
| `emoji` | `name`, `id` | agent 無法看見的平台貼圖或自訂表情符號。`name` 是一般人對它的稱呼。 |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | 此訊息所引用的訊息。平台提供 `text` 時一律傳送。 |

其他內容以文字描述，作為 `text` 片段，例如 `(sent a voice message)` 或 `(sent a file: deck.pdf)`。agent 會捨棄未知類型的片段。

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

- `replies`：依序傳送，每一項作為一則獨立的訊息。存在 `mention_user_id` 時，它是要提及的帶前綴 id。請以平台的方式呈現提及。
- `owned`：agent 已接管此對話。為 true 時，即使 `replies` 為空，也必須阻止其他機器人邏輯回覆，因為這是人設選擇了沉默。為 false 時，此訊息由你處理。原因可能是此對話不在 agent 的允許清單中，也可能是 agent 根本無法回覆（未設定 `LLM_API_KEY`，或 `AGENT_ENABLED=false`）。後者的情況下，agent 的記錄檔中會有一行 ERROR 註明原因。
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

`items` 的格式與 `replies` 相同。`reason` 為 `proactive`、`follow_up` 或 `excuse`，`conversation_type` 為 `group` 或 `dm`。`conversation_key` 是 agent 儲存此對話所用的鍵，例如私訊的 `private:telegram:42`。`conversation_id` 是事件帶來的原始 id，私訊時即為使用者 id。agent 會記住每個對話中最近一則被接受事件的 `reply_handle`、`connector_id` 和 `capabilities`，因此對話只要傳送過一則訊息，即可聯繫。

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

## 不經 outbox 主動發言

無法輪詢的聯結器也可以主動發起私訊。由它自己的排程器，例如 AstrBot 外掛程式任務或 cron 項目，向 `/v1/events` 傳送一個帶有 `"proactive": true` 的一般私訊事件。agent 會將文字視為提供給人設的提示（「對方已沉默一整天；今天早上有考試」），截斷至 500 字元，且絕不將其儲存為該使用者所說的話。這一輪仍由引擎的主動發言指令決定，人設也可能保持沉默。如果人設開口，回覆會在回應中傳回，由排程器轉送。

此事件需要聯結器一般事件所帶的全部內容：簽章請求標頭、所有必填欄位、與聯結器傳送給該使用者時相同的 `platform` 和原始 `sender_id`、非空白的文字，以及每次都不同的 `message_id`。`message_id` 重複的事件會被靜默捨棄。此提示與 agent 自己的開場白共用同一個私訊冷卻時間（`PROACTIVE_DM_COOLDOWN_S`），且不計為該使用者的活動。

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

`integrations/sdk/personagent_connector.py` 負責第 3 和第 4 步。
