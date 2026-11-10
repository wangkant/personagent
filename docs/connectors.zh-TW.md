# 聯結器協議

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · 繁體中文 · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · [Español](connectors.es.md) · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

agent 自己從不和聊天平臺打交道，這件事由聯結器來做。聯結器登入一個平臺，或登入一個覆蓋多個平臺的框架，把每條收到的訊息轉成中立的事件，發給 personagent，再把返回的內容送出去。所有平臺相關的東西都留在聯結器裡，所以 agent 看到的格式在每個平臺上都一樣。

這個倉庫自帶四個聯結器：

| 聯結器 | 能連到 | 路徑 |
|---|---|---|
| 直連 | QQ 官方機器人、個人微信（iLink）、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat，不需要其他軟體。本地頁面和 `personagent up` 用一個程序執行它：`python -m persona_agent.direct`。 | `persona_agent/direct/` |
| AstrBot 外掛 | 第三方橋接 AstrBot 支援的平臺。personagent 為 KOOK、飛書/Lark、釘釘、Slack、企業微信、Mattermost、Misskey、OneBot v11 等管理的 AstrBot 會自動裝好外掛。已經在執行的 AstrBot 用 `personagent connect astrbot` 設定。也可以用 AstrBot 的“從檔案安裝”上傳 GitHub Release 裡的 `astrbot_plugin_personagent.zip`，再自己設定 `connector_token`。 | `integrations/astrbot/` |
| Satori | 所有 Satori 實現（Koishi 等第三方）：QQ、Telegram、Discord、KOOK、Lark、釘釘、LINE、WhatsApp、Matrix、Zulip、電子郵件等。 | `integrations/satori/` |
| Matrix | Matrix 房間，並可透過第三方 mautrix 橋接連到 WhatsApp、Signal、Messenger、Instagram、Google Messages 等。 | `integrations/matrix/` |

程式設計 agent 不是聊天平臺，所以走自己的路線：一個 MCP 伺服器 `personagent mcp`，詳見[使用手冊](guide.zh-TW.md#程式設計助手)。

這四個聯結器都使用本頁描述的協議。寫一個新的聯結器，只需要本頁和一個 HTTP 客戶端。`integrations/sdk/personagent_connector.py` 裡的 Python 輔助工具會替你簽名請求並執行 outbox 迴圈。它接收基礎 URL、令牌和聯結器的 `connector_id`，並依賴 `httpx`。

## 配置

本地頁面負責配置直連聯結器。另外三個使用相同的名稱，所以同一個設定在它們之中含義相同：

| 含義 | Satori | Matrix | AstrBot 外掛鍵 |
|---|---|---|---|
| personagent 的基礎 URL，比如 `http://127.0.0.1:8080`。聯結器會追加 `/v1/events` 和 `/v1/outbox`。 | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| 共享令牌，等於 agent 的 `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| 這個聯結器的 id（即下文的 `connector_id`） | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| 一次請求最長耗時，單位秒 | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| 拉取 outbox | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| 要轉發的群 | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| 要轉發其私聊的人 | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| 平臺的伺服器 | `SATORI_URL` | `MATRIX_URL` | AstrBot 自身的設定 |

群或私聊列表為空時，這一類都不轉發。`*` 轉發這一類的全部內容，並把事件標記為 `"prefiltered": false`，交由 agent 的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 決定。其餘設定見各聯結器的 README。

## 地址

personagent 把每個 id 存成 `<platform>:<id>`，比如群 `telegram:-1001234` 或使用者 `discord:4242`。`platform` 是聯結器給平臺起的名字，用小寫，不含 `:`。

QQ 是唯一的例外，為了相容而保留。它的 id 儲存時不帶字首（`123456`），在任何設定裡寫 `qq:123456` 都是同一個意思。如果聯結器接入 QQ，又想讓學到的狀態和已有的 QQ 部署對上，就把它的平臺名寫進 `CONNECTOR_QQ_PLATFORMS`。AstrBot 外掛的 QQ 介面卡是 `aiocqhttp`。這裡列出的平臺，其 id 同樣不帶字首儲存。

## 認證

下面兩個端點使用同一套方案。agent 設定了 `CONNECTOR_TOKEN` 時，每個請求都帶四個請求頭：

- `X-Personagent-Token`：令牌。
- `X-Personagent-Timestamp`：unix 秒。和 agent 時鐘相差超過五分鐘的值會被拒絕。
- `X-Personagent-Nonce`：一個新的隨機值。重複使用的 nonce 會被拒絕。
- `X-Personagent-Signature`：`sha256=` 後接 `timestamp + "." + nonce + "." + body` 的十六進位制 HMAC-SHA256，以令牌為金鑰。

請求體是規範 JSON：UTF-8、鍵排序、緊湊分隔符，非 ASCII 字元不轉義。令牌同時是簽名金鑰，所以不要讓它進入日誌。

沒有令牌時，agent 只接受直接呼叫 `127.0.0.1` 或 `localhost` 的本地程式。聯結器必須拒絕傳送到迴環 URL 以外的地址，除非是帶令牌的 HTTPS URL。

## 入站：`POST /v1/events`

每個請求帶來一條訊息，並返回對它的回覆。

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

必填欄位是 `platform`、`conversation_type`（`group` 或 `dm`）、`sender_id`、`message_id` 和 `sent_at`，群聊還要加 `conversation_id`。`sent_at` 是平臺給訊息打上的時間，單位是 unix 秒。傳送平臺原始 id，字首由 agent 新增。

`addressed` 由聯結器設定。訊息提及機器人、回覆機器人的某條訊息，或按平臺自身規則是對機器人說的，它就為 true。agent 自己也會注意文字里出現的名字。它把對自己訊息的引用或對機器人的 @ 視為可以學習的反應，所以回覆機器人的訊息要設定 `addressed`。對其他成員訊息的引用從來不算對機器人的反應。

`sender_id` 等於 `bot_id` 的事件，是機器人自己的訊息被回傳。agent 不讀就丟棄，並回答 `{"handled": false, "owned": true, "replies": []}`，這樣聯結器自己的機器人邏輯也保持安靜。請在聯結器裡跳過這類事件。

片段按順序排列：

| 型別 | 欄位 | 說明 |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | 提及某人。`user_id` 等於 `bot_id` 時，就是提及機器人。 |
| `image` | `url` 或 `b64`，`sticker`（布林值） | `sticker` 標記以圖片形式傳送的表情包。 |
| `emoji` | `name`, `id` | agent 看不到的平臺貼紙或自定義表情。`name` 是人會怎樣稱呼它。 |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | 這條訊息引用的訊息。平臺提供 `text` 時一律傳送。 |

其他內容用文字描述，作為 `text` 片段，比如 `(sent a voice message)` 或 `(sent a file: deck.pdf)`。agent 會丟棄未知型別的片段。

下面這些可選欄位能啟用 agent 的更多功能：

| 欄位 | 含義 |
|---|---|
| `connector_id` | 這個聯結器例項的穩定 id。outbox 需要它。 |
| `reply_handle` | 聯結器以後沒有收到訊息也能聯絡到這個會話所需的任何東西：AstrBot 的 `unified_msg_origin`、Matrix 房間 id，或 Satori 登入加頻道 id。agent 把它當作不透明的值，按會話儲存，並在 outbox 投遞中交回。 |
| `capabilities` | 聯結器能做什麼。`outbox` 表示它輪詢 outbox，並且可以主動傳送。`quote_text` 表示回覆片段帶有被引用的文字。 |
| `prefiltered` | 聯結器應用了自己的允許列表時為 `true`（預設）。`false` 讓 agent 的列表成為唯一的過濾器。 |
| `proactive` | 把私聊事件標記為聯結器寫的提示，而不是這個人說的話。見“不用 outbox 先開口”。 |

響應是這樣的：

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`：按順序傳送，每條作為單獨的訊息。`mention_user_id` 存在時，它是要提及的帶字首 id。按平臺的方式呈現提及。
- `owned`：agent 已經接管這個會話。為 true 時，即使 `replies` 為空也要阻止其他機器人邏輯回答，因為這是人設選擇了沉默。為 false 時，這條訊息歸你處理。要麼這個會話不在 agent 的允許列表上，要麼 agent 根本無法回答（沒有 `LLM_API_KEY`，或 `AGENT_ENABLED=false`）。第二種情況下，agent 的日誌裡有一行 ERROR 寫明原因。
- 請求會一直持續到這一輪結束，也就是一小段防抖加上模型的用時。不論群聊還是私聊，一輪的所有模型呼叫（含重試）共用一份 1.5 × `LLM_TIMEOUT_S` 的時間預算；如果訊息到達時同一會話的上一輪還在思考，它會先等那一輪結束，再輪到自己。至少留出 3 × `LLM_TIMEOUT_S` 秒（預設是 360 秒）。
- 如果記憶命令（比如“記住……”）到達時，同一會話的某一輪還在思考，它會等那一輪結束後才得到回答。宣告了 `outbox` 的聯結器會立刻收到 `{"handled": false, "owned": true, "replies": []}`，回答稍後作為 `follow_up` 投遞送達。沒有 `outbox` 時，回答隨某個響應返回：可能是它自己的響應，也可能是同一會話裡另一個正在等待的請求的響應，所以一個響應裡可能有提及事件傳送者以外的人的回覆。

## Outbox：`POST /v1/outbox`

有些訊息不是對請求的回答，比如定時的開場白、被拒絕後的追問、排在一輪後面的記憶命令的回答，以及群裡模型不可用時的託詞。agent 按會話把它們排隊，宣告瞭 `outbox` 的聯結器來拉取，所以 NAT 或防火牆後面的聯結器也能照常工作。以不帶字首的 QQ id 儲存的會話（見“地址”）在其聯結器拉取期間也使用 outbox。否則，設定了 `QQ_ONEBOT_URL` 時，它們走 NapCat 的 HTTP API。

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

agent 最多把請求掛起 `wait_s` 秒（上限 30），直到有內容排隊，然後回答：

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

`items` 的形狀和 `replies` 相同。`reason` 是 `proactive`、`follow_up` 或 `excuse`，`conversation_type` 是 `group` 或 `dm`。`conversation_key` 是 agent 儲存這個會話用的鍵，比如私聊的 `private:telegram:42`。`conversation_id` 是事件帶來的原始 id，私聊時就是使用者 id。agent 記住每個會話最新一條被接納事件裡的 `reply_handle`、`connector_id` 和 `capabilities`，所以會話只要發過一條訊息就可以聯絡到。

在下一次拉取的 `acks` 裡報告每次投遞：

| `status` | 含義 |
|---|---|
| `sent` | 所有專案都發出去了。 |
| `partial` | 前 `sent_items` 項發出去了。 |
| `failed` | 什麼都沒發出去。 |
| `expired` | 沒有在 `expires_in_s` 內開始傳送。 |
| `refused` | 聯結器不再允許這個會話。 |
| `unsupported` | 平臺無法主動向這個會話傳送。 |

規則：

- **最多一次。** 無論 ack 發生什麼，agent 只交出一次投遞，絕不重發。保留最近幾百個 `delivery_id`，同一個絕不發兩次。
- **按順序。** 一個會話的投遞按收到的順序傳送。不同會話可以並行傳送。
- **只有確認過的投遞才算。** agent 把未確認的投遞視為未傳送，只把確認過的記為已傳送。它等待 ack 直到你下一次拉取，並且交出投遞後最多等 `expires_in_s` 再加 60 秒。發完一批再拉取。
- **存活。** 90 秒沒有拉取的聯結器視為已離開。在它再次拉取之前，不為它的會話排隊，已排隊或已交給它但沒有確認的內容都以未傳送結束。一批送達後立刻再拉取。這次拉取也帶上這批的確認。
- **`unsupported` 會保持。** 收到這個確認後，agent 停止為這個會話排隊，直到某個事件帶來不同的 `reply_handle`。
- **請求體型別。** 簽名不覆蓋 URL 路徑。因此，agent 拒絕發到 outbox 端點的事件請求體和發到事件端點的 `outbox.pull` 請求體，返回 `400` 和程式碼 `invalid_schema`。事件可以帶 `"kind": "event"`。帶其他 `kind` 的事件會被拒絕。

沒有 `code` 的 404 表示 agent 不提供 outbox。帶程式碼 `outbox_disabled` 的 `404` 表示運營者用 `CONNECTOR_OUTBOX_ENABLED` 關閉了它。兩種情況都要等很久再拉取。

## 不用 outbox 先開口

不能輪詢的聯結器也可以開啟私聊。它自己的排程器，比如 AstrBot 外掛任務或 cron 條目，向 `/v1/events` 傳送一個帶 `"proactive": true` 的普通私聊事件。agent 把文字當作給人設的提示（“他們安靜一天了；今天早上有考試”），截斷到 500 字元，絕不把它存成這個人說的話。引擎的主動發言指令仍然決定這一輪，也可能讓人設保持沉默。如果人設開口，回覆會在響應裡返回，由排程器轉發。

這個事件需要聯結器普通事件帶的所有內容：簽名請求頭、所有必填欄位、聯結器給這個人傳送時相同的 `platform` 和原始 `sender_id`、非空文字，以及每次新的 `message_id`。`message_id` 重複的事件會被靜默丟棄。這個提示和 agent 自己的開場白計入同一個私聊冷卻（`PROACTIVE_DM_COOLDOWN_S`），並且不算這個人的活動。

一定要設定這個標記；沒有它，agent 會把提示存成這個人說的話。帶這個標記的群事件會被接管（`owned: true`，所以聯結器讓自己的機器人保持安靜），並且不讀就丟棄。

## 能力和降級

| 缺少 | 影響 |
|---|---|
| `outbox` | 沒有定時開場白、沒有追問，群裡模型呼叫失敗時也沒有託詞。設定了 `QQ_ONEBOT_URL` 且可達時，QQ id 仍能透過 NapCat 得到這些。私聊的託詞在響應的 `replies` 裡返回，不需要 outbox。 |
| `quote_text` | 只有 agent 自己見過的訊息，它才能理解對該訊息的引用。 |
| `reply_handle` | 和缺少 `outbox` 相同。 |
| `addressed` 錯誤 | 人設把對它說的話當成背景閒聊。 |

## 編寫聯結器

1. 從平臺接收訊息。跳過機器人自己的訊息和不是訊息的事件（入群、撤回、戳一戳）。
2. 構造上面描述的事件。根據平臺自身的提及和回覆規則設定 `addressed`。
3. 簽名併傳送事件。按順序傳送 `replies`，`owned` 為 true 時讓其他機器人邏輯保持安靜。
4. 如果平臺可以主動傳送，加上 `connector_id`、`reply_handle` 和 `capabilities: ["outbox"]`，然後執行拉取迴圈：拉取，透過 `reply_handle` 送出每次投遞，在下一次拉取時確認。

`integrations/sdk/personagent_connector.py` 負責第 3 和第 4 步。
