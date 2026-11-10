# Satori 聯結器

[English](README.md) · [简体中文](README.zh-CN.md) · 繁體中文 · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


此聯結器將 [personagent](https://github.com/wangkant/personagent) 連接至 [Satori](https://satori.chat) 伺服器。Satori 是一種跨平台的聊天協定。[Koishi](https://koishi.chat)（搭配其 `server-satori` 外掛程式）、Chronocat 或 LLOneBot 等伺服器負責登入各聊天平台，此用戶端則透過一條 websocket 接收所有已登入帳號的每則訊息。因此，只需一個聯結器處理程序，即可將角色接入伺服器具有配接器的每個平台。

Satori 和 Koishi 是第三方軟體。QQ、微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK、Stoat 由 personagent 自行連線，本機頁面透過 AstrBot 設定的平台亦然，這些都不需要它們。如果你已在執行 Koishi，或需要只有 Koishi 能連接的平台，再使用此聯結器。

聯結器將每則獲准的訊息以中立事件格式傳送至 agent 的 `POST /v1/events`（[docs/connectors.md](../../docs/connectors.zh-TW.md)），再透過 Satori 將回覆傳回。它也會拉取 agent 的 outbox，因此定時開場、追問和致歉都能送達聊天。

[satori-python](https://github.com/RF-Tar-Railt/satori-python) 負責 Satori 端：websocket、登入清單和 HTTP API。此聯結器負責在 Satori 與 personagent 的事件格式之間轉換，並以 [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py) 處理簽章和 outbox 迴圈。

## 設定（以 Koishi 為例）

1. **Koishi。** 以桌面啟動器或 `npm init koishi@latest` 安裝 Koishi。在其主控台中新增並設定你的平台配接器，例如 `adapter-telegram` 或 `adapter-discord`，並確認機器人已上線。啟用 `server` 和 `server-satori` 外掛程式。Koishi 隨後會在 `http://127.0.0.1:5140/satori` 提供 Satori 服務。如果這台機器以外的程式能存取該連接埠，請為 `server-satori` 設定一個 `token`。

   Koishi 的其他外掛程式會繼續執行。如果其中有同樣會回覆訊息的外掛程式，例如聊天模型或自動回覆外掛程式，它會與角色一起回覆，聯結器無法使其停止。請關閉該外掛程式，或將其適用範圍限制在你所轉送的對話之外。

2. **Agent。** 執行 personagent（`personagent run`，請參閱其 README）。如果聯結器和 agent 不在同一台主機上，請在 agent 的 `.env` 中設定 `CONNECTOR_TOKEN`，並將 agent 置於 HTTPS 之後。即使只有一台主機，在加入代理伺服器或通道之前，也請先設定權杖。

3. **聯結器。** 聯結器是本儲存庫中的腳本，因此需要一份儲存庫副本（Git 複製，或 GitHub 上的 ZIP）及其專用的 Python 環境，因為 `satori-python` 並非 personagent 的相依套件。如果複製的儲存庫中已有 personagent 的 `.venv`，請安裝至該環境：

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   如果你以 pip 從 PyPI 安裝了 personagent，或以 uvx 執行，請在副本旁另行建立一個 venv：

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   在 Windows 上，直譯器為 `.venv\Scripts\python.exe` 或 `connector-venv\Scripts\python.exe`。接著複製設定檔：

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   在 `integrations/satori/.env` 中設定 Satori 伺服器的 URL 和權杖、agent 的基礎 URL 和 `CONNECTOR_TOKEN`，以及要轉送的對話（請參閱[允許清單](#允許清單)）。然後以同一個直譯器啟動聯結器：

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE` 可讀取另一個設定檔。每項設定也可以透過環境變數提供，環境變數優先於檔案。

4. **確認運作正常。** 伺服器上的每個機器人都會在記錄檔中顯示一行，例如 `Satori login telegram:7000 is ONLINE`。在轉送的群組中提及機器人。agent 的記錄檔會顯示此回合，回覆會出現在聊天中。如果沒有任何反應，請設定 `SATORI_LOG_LEVEL=DEBUG`。

## 設定項目

| 設定項目 | 預設值 | 說明 |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | Satori 伺服器。結尾的 `/v1` 可加可不加。 |
| `SATORI_TOKEN` | | 伺服器的權杖（在 Koishi 中為 `server-satori` → `token`）。 |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | agent 的基礎 URL。會自動加上 `/v1/events` 和 `/v1/outbox`。 |
| `CONNECTOR_TOKEN` | | agent 的 `CONNECTOR_TOKEN`。 |
| `SATORI_GROUPS` | | 要轉送的群組，填寫頻道或伺服器 id，可以寫成 `platform:id`。留空則不轉送，`*` 則全部轉送。 |
| `SATORI_DM_USERS` | | 轉送哪些人的私訊，填寫使用者 id，可以寫成 `platform:id`。留空則不轉送，`*` 則全部轉送。 |
| `SATORI_PLATFORMS` | 全部 | 將聯結器限定於這些 Satori 平台。 |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | 改寫 agent 看到的平台名稱：`satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | 拉取 agent 的 outbox。 |
| `SATORI_CONNECTOR_ID` | 由 `SATORI_URL` 推導 | 此聯結器在 agent 端的 id。請保持不變。 |
| `SATORI_TIMEOUT_S` | `420` | 一個回合可花費的最長時間。須大於 agent 的 3 × `LLM_TIMEOUT_S`。 |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | 由聯結器下載公開的圖片 URL，而非將 URL 傳給 agent。 |
| `SATORI_LOG_LEVEL` | `INFO` | |

agent 的 URL 必須是迴路位址，或已設定 `CONNECTOR_TOKEN` 的 HTTPS 位址，否則聯結器會拒絕啟動。如果 `SATORI_TOKEN` 會透過明文 `http` 傳送至其他主機，聯結器會記錄一則警告。

## 允許清單

聯結器預設拒絕。清單為空時不轉送任何內容。

- 群組即為 Satori 頻道。只有其頻道 id 或伺服器 id 列於 `SATORI_GROUPS` 中時才會轉送。因此在 Discord 或 KOOK 上，一個伺服器 id 會放行該伺服器的所有頻道，每個頻道仍是獨立的對話。
- 只有傳送者的使用者 id 列於 `SATORI_DM_USERS` 中時，才會轉送私訊。
- 項目可以註明平台，例如 `telegram:-1001234` 或 `discord:4242`，如此只會在該平台上比對。未註明平台的項目會在所有平台上比對。
- `*` 會轉送所有群組（或所有私訊），並將事件標記為 `prefiltered: false`。此後由 agent 本身的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 決定，在其中沒有項目的平台會被拒絕。

Koishi 的 `inspect` 外掛程式會輸出一則訊息的平台、頻道、伺服器和使用者 id。

## 平台名稱與 QQ

personagent 將 id 儲存為 `<platform>:<id>`，平台即為 Satori 登入帳號的平台（`telegram`、`discord`、`onebot` 等）。第 4 步的記錄行會顯示此平台。有兩種特殊情況：

- **透過 OneBot 的 QQ**（Koishi 的 `adapter-onebot`，後端為 NapCat 或 LLOneBot）以 QQ 號碼作為 id。如需保留 agent 在既有 QQ 部署中學到的內容，請將此平台加入 agent 的 `CONNECTOR_QQ_PLATFORMS`（`CONNECTOR_QQ_PLATFORMS=onebot`）。如此其 id 會以不帶前綴的形式儲存，與 NapCat 的 QQ 號碼相同，`ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 中的 QQ 項目也會適用。只有 id 確實為 QQ 號碼的平台才能如此設定。
- **QQ 官方機器人 API**（Koishi 的 `adapter-qq`）將平台稱為 `qq`，但其 id 是 openid，而非 QQ 號碼。聯結器會將此平台更名為 `qqbot`。`SATORI_PLATFORM_NAMES` 可以覆寫此更名。personagent 也能不經 Koishi 自行連線 QQ 官方機器人。

## 支援狀況

| 功能 | 狀態 |
|---|---|
| 群組聊天和私訊 | 支援。私訊是指 `DIRECT` 頻道，或沒有伺服器的訊息。 |
| 是否被點名的判斷（`addressed`） | 對機器人的 `<at>`（依 id 判斷，伺服器未提供 id 時依機器人的名稱），以及回覆機器人的訊息。`@all` 視為文字，不視為提及。 |
| 引用訊息 | 被引用的文字、傳送者和 id，取自 `<quote>` 元素或 `message.quote`。 |
| 收到的圖片 | `data:` 和 `internal:` 圖片，以及 Satori 伺服器上的圖片會以內嵌方式傳送。公開 URL 會傳給 agent 自行取得。內部網路的 URL 會描述為 `(sent an image)`。每則訊息最多下載 4 張，每張最大 4 MB。 |
| 貼圖和表情 | `<emoji>` 和 QQ 的 `<face>` 會以表情的形式送達，角色知道自己無法看見它們。 |
| 語音、影片、檔案 | 以文字描述：`(sent a voice message)`、`(sent a video)`、`(sent a file: deck.pdf)`。 |
| 回覆 | 文字，以及以 `data:` URI 表示的圖片，會分別以獨立的訊息傳送，其間有短暫間隔。在群組中，agent 要求的提及會轉為 `<at>`。 |
| 被動回覆的平台 | 回覆會附帶事件的 `referrer`，QQ 官方機器人 API 回覆訊息時需要此項。 |
| Outbox | 定時開場、追問和致歉會透過收到該對話的登入帳號傳送至頻道。聯結器以由 `SATORI_TOKEN` 和 `CONNECTOR_TOKEN` 衍生的金鑰為每個回覆控制代碼簽章，且只傳送至自己簽章過的控制代碼。變更其中任何一個權杖後，該對話須再傳來一則訊息，才能重新送達。設定了 `CONNECTOR_OUTBOX_ENABLED=false` 的 agent 會傳回 404，聯結器每 10 分鐘重試一次。 |
| 輸入中提示 | 不支援。Satori 沒有輸入狀態 API。 |
| `owned` | 遵循：聯結器不會再傳送其他內容。但它無法阻止 Koishi 的其他外掛程式（請參閱第 1 步）。 |

平台規則依然適用。例如 QQ 官方機器人 API 嚴格限制機器人主動傳送訊息，因此該平台上的 outbox 傳遞可能傳回 `failed`。

## 測試

`tests/test_satori_connector.py` 不需要 satori-python，也不需要網路連線。它模擬了元素物件、帳號和 agent。
