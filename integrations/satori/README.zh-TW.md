# Satori 聯結器

[English](README.md) · [简体中文](README.zh-CN.md) · 繁體中文 · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


這個聯結器把 [personagent](https://github.com/wangkant/personagent) 接到 [Satori](https://satori.chat) 伺服器。Satori 是一種跨平臺聊天協議。[Koishi](https://koishi.chat)（配合它的 `server-satori` 外掛）、Chronocat 或 LLOneBot 這樣的伺服器負責登入各聊天平臺，這個客戶端則透過一條 websocket 收到所有登入賬號的每條訊息。所以一個聯結器程序就能把角色帶到伺服器有介面卡的每個平臺。

Satori 和 Koishi 是第三方軟體。QQ、微信、Telegram、Discord 由 personagent 自己連線，本地頁面透過 AstrBot 配置的平臺也一樣，這些都不需要它們。如果你已經在跑 Koishi，或者想要只有 Koishi 能連的平臺，再用這個聯結器。

聯結器把每條允許的訊息作為中立事件發到 agent 的 `POST /v1/events`（[docs/connectors.md](../../docs/connectors.zh-TW.md)），再把回覆透過 Satori 發回去。它也會拉取 agent 的發件箱，所以定時開場、追問和致歉都能送到聊天裡。

[satori-python](https://github.com/RF-Tar-Railt/satori-python) 負責 Satori 這一側：websocket、登入列表和 HTTP API。這個聯結器負責在 Satori 和 personagent 的事件格式之間轉換，並用 [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py) 處理簽名和發件箱迴圈。

## 配置（以 Koishi 為例）

1. **Koishi。** 用桌面啟動器或 `npm init koishi@latest` 安裝 Koishi。在它的控制檯裡新增並配置你的平臺介面卡，比如 `adapter-telegram` 或 `adapter-discord`，並確認機器人線上。啟用 `server` 和 `server-satori` 外掛。Koishi 隨後會在 `http://127.0.0.1:5140/satori` 提供 Satori 服務。如果這臺機器以外的東西能訪問那個埠，給 `server-satori` 設一個 `token`。

   Koishi 的其他外掛會繼續執行。如果其中有也會回訊息的，比如聊天模型或回覆外掛，它會和角色一起回覆，聯結器沒法讓它閉嘴。把那個外掛關掉，或者把它的範圍限制在你轉發的會話之外。

2. **Agent。** 執行 personagent（`personagent run`，見它的 README）。如果聯結器和 agent 不在同一臺主機上，在 agent 的 `.env` 裡設定 `CONNECTOR_TOKEN`，並把 agent 放到 HTTPS 後面。即使只有一臺主機，也要在加代理或隧道之前先設好令牌。

3. **聯結器。** 聯結器是這個倉庫裡的指令碼，所以需要一份倉庫副本（克隆，或 GitHub 上的 ZIP）和它自己的 Python 環境，因為 `satori-python` 不是 personagent 的依賴。如果克隆裡已經有 personagent 的 `.venv`，就裝進這個環境：

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   如果你用 pip 從 PyPI 安裝了 personagent，或者用 uvx 執行，就在副本旁邊另建一個 venv：

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   在 Windows 上，直譯器是 `.venv\Scripts\python.exe` 或 `connector-venv\Scripts\python.exe`。接著複製配置檔案：

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   在 `integrations/satori/.env` 裡設定 Satori 伺服器的 URL 和令牌、agent 的基礎 URL 和 `CONNECTOR_TOKEN`，以及要轉發的會話（見[允許名單](#允許名單)）。然後用同一個直譯器啟動聯結器：

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE` 讀取另一個配置檔案。每項配置也可以用環境變數給出，環境變數優先於檔案。

4. **確認能用。** 伺服器上的每個機器人都會在日誌裡顯示一行，比如 `Satori login telegram:7000 is ONLINE`。在轉發的群裡提到機器人。agent 的日誌會顯示這一輪，回覆會出現在聊天裡。如果什麼都沒發生，設定 `SATORI_LOG_LEVEL=DEBUG`。

## 配置項

| 配置項 | 預設值 | 含義 |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | Satori 伺服器。末尾的 `/v1` 可有可無。 |
| `SATORI_TOKEN` | | 伺服器的令牌（在 Koishi 裡是 `server-satori` → `token`）。 |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | agent 的基礎 URL。會自動追加 `/v1/events` 和 `/v1/outbox`。 |
| `CONNECTOR_TOKEN` | | agent 的 `CONNECTOR_TOKEN`。 |
| `SATORI_GROUPS` | | 要轉發的群，寫頻道或伺服器 id，可以寫成 `platform:id`。留空不轉發，`*` 全部轉發。 |
| `SATORI_DM_USERS` | | 轉發哪些人的私聊，寫使用者 id，可以寫成 `platform:id`。留空不轉發，`*` 全部轉發。 |
| `SATORI_PLATFORMS` | 全部 | 把聯結器限制在這些 Satori 平臺。 |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | 改寫 agent 看到的平臺名：`satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | 拉取 agent 的發件箱。 |
| `SATORI_CONNECTOR_ID` | 由 `SATORI_URL` 得出 | 這個聯結器在 agent 那邊的 id。請保持不變。 |
| `SATORI_TIMEOUT_S` | `420` | 一輪最長可以花多久。要大於 agent 的 3 × `LLM_TIMEOUT_S`。 |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | 在聯結器裡下載公開圖片 URL，而不是把 URL 傳給 agent。 |
| `SATORI_LOG_LEVEL` | `INFO` | |

agent 的 URL 必須是迴環地址，或是設定了 `CONNECTOR_TOKEN` 的 HTTPS，否則聯結器拒絕啟動。如果 `SATORI_TOKEN` 會透過明文 `http` 發往其他主機，聯結器會記一條警告。

## 允許名單

聯結器預設拒絕。名單為空就什麼都不轉發。

- 群就是 Satori 頻道。它的頻道 id 或伺服器 id 在 `SATORI_GROUPS` 裡時才轉發。所以在 Discord 或 KOOK 上，一個伺服器 id 會放行該伺服器的所有頻道，每個頻道仍是單獨的會話。
- 傳送者的使用者 id 在 `SATORI_DM_USERS` 裡時，才轉發私聊。
- 條目可以寫明平臺，比如 `telegram:-1001234` 或 `discord:4242`，這樣只在該平臺匹配。不帶平臺的條目在所有平臺匹配。
- `*` 轉發所有群（或所有私聊），並把事件標記為 `prefiltered: false`。之後由 agent 自己的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 決定，那裡沒有條目的平臺會被拒絕。

Koishi 的 `inspect` 外掛會列印一條訊息的平臺、頻道、伺服器和使用者 id。

## 平臺名和 QQ

personagent 把 id 存成 `<platform>:<id>`，平臺就是 Satori 登入賬號的平臺（`telegram`、`discord`、`onebot` 等）。第 4 步的日誌行會顯示它。有兩種特殊情況：

- **透過 OneBot 的 QQ**（Koishi 的 `adapter-onebot`，後面接 NapCat 或 LLOneBot）用 QQ 號作為 id。要保留 agent 在已有 QQ 部署上學到的東西，把這個平臺加到 agent 的 `CONNECTOR_QQ_PLATFORMS`（`CONNECTOR_QQ_PLATFORMS=onebot`）。這樣它的 id 會不帶字首地儲存，就像 NapCat 的 QQ 號一樣，`ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 裡的 QQ 條目也適用。只有 id 確實是 QQ 號的平臺才能這樣做。
- **QQ 官方機器人 API**（Koishi 的 `adapter-qq`）把平臺叫作 `qq`，但它的 id 是 openid，不是 QQ 號。聯結器把平臺改名為 `qqbot`。`SATORI_PLATFORM_NAMES` 可以覆蓋這個改名。personagent 也能不經 Koishi 自己連線 QQ 官方機器人。

## 支援情況

| 功能 | 狀態 |
|---|---|
| 群聊和私聊 | 支援。私聊是 `DIRECT` 頻道，或沒有伺服器的訊息。 |
| 被叫到的判斷（`addressed`） | 對機器人的 `<at>`（按 id，伺服器不給 id 時按機器人的名字），以及回覆機器人的訊息。`@all` 算文字，不算提及。 |
| 引用訊息 | 引用的文字、傳送者和 id，取自 `<quote>` 元素或 `message.quote`。 |
| 收到的圖片 | `data:` 和 `internal:` 圖片以及 Satori 伺服器上的圖片會內聯。公開 URL 傳給 agent 自己獲取。內網 URL 描述為 `(sent an image)`。每條訊息最多下載 4 張，每張 4 MB。 |
| 貼紙和表情 | `<emoji>` 和 QQ 的 `<face>` 作為表情到達，角色知道自己看不見它們。 |
| 語音、影片、檔案 | 用文字描述：`(sent a voice message)`、`(sent a video)`、`(sent a file: deck.pdf)`。 |
| 回覆 | 文字，以及作為 `data:` URI 的圖片，分別作為單獨訊息發出，中間有短暫間隔。在群裡，agent 要求的提及會變成 `<at>`。 |
| 被動回覆的平臺 | 回覆帶上事件的 `referrer`，QQ 官方機器人 API 回覆訊息時需要它。 |
| 發件箱 | 定時開場、追問和致歉透過收到該會話的登入賬號發到頻道。聯結器用由 `SATORI_TOKEN` 和 `CONNECTOR_TOKEN` 派生的金鑰給每個回覆控制代碼簽名，只發給自己簽過的控制代碼。改了其中任何一個令牌後，會話要再發一條訊息才能重新送達。設定了 `CONNECTOR_OUTBOX_ENABLED=false` 的 agent 會回 404，聯結器每 10 分鐘重試一次。 |
| 正在輸入提示 | 不支援。Satori 沒有輸入狀態 API。 |
| `owned` | 遵守：聯結器不再傳送別的內容。但它攔不住 Koishi 的其他外掛（見第 1 步）。 |

平臺規則依然適用。比如 QQ 官方機器人 API 嚴格限制機器人主動發訊息，所以那裡的發件箱投遞可能返回 `failed`。

## 測試

`tests/test_satori_connector.py` 不需要 satori-python 和網路。它模擬了元素物件、賬號和 agent。
