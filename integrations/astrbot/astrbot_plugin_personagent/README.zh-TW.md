# astrbot_plugin_personagent

[English](README.md) · [简体中文](README.zh-CN.md) · 繁體中文 · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


此 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 外掛程式將 AstrBot 連線至 [personagent](https://github.com/wangkant/personagent)。它將每則獲准的訊息轉送給 personagent，再將 personagent 的回覆傳回聊天。

## 是否需要此外掛程式

QQ、微信、Telegram、Discord 不需要此外掛程式。personagent 會直接連線這些平台，不經過 AstrBot。執行 `personagent` 開啟本機頁面，在 **連接平台** 中新增即可。

只有由 AstrBot 負責收發訊息時才需要此外掛程式，分為兩種情況。

- **在 personagent 頁面中新增其他平台。** KOOK、飛書、釘釘、Slack、企業微信智慧機器人、Mattermost、Misskey，以及「進階」分組中的平台，都經由 AstrBot 接入。頁面會代為下載並執行 AstrBot，並安裝此外掛程式，你無須在此進行任何操作。
- **你已在執行 AstrBot**，且它有自己的平台和外掛程式。請依下列步驟安裝此外掛程式。

## 功能

- 接收 AstrBot 所有平台配接器（Telegram、Discord、Slack、QQ 等）的群組訊息和私訊，`excluded_platforms` 中所列者除外。
- 將允許清單中的群組和傳送者的訊息，以平台中立的事件格式轉送至 personagent 的 `POST /v1/events`。它依各配接器實際的交付方式讀取訊息，包括誰被 @、引用了什麼、表情符號、圖片、語音，以及平台記錄的傳送時間。
- 經由 AstrBot，依各平台要求的形式傳回 personagent 的回覆。回覆可以包含文字和圖片，在群組中可依 personagent 的要求附上 @。
- 拉取 personagent 的 outbox，傳送它主動發出的訊息，例如定時開場、追問，或模型無法使用時在群組中的致歉。請參閱 [Outbox](#outbox)。
- personagent 接管對話時，停止 AstrBot 本身的處理流程（`block_default`），使 AstrBot 內建的模型不會代替角色回答。

人設、記憶、防彈跳和輸入模擬都在 personagent 中執行。此外掛程式是 personagent 的 [`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.zh-TW.md) 所定義的聯結器。

## 安裝至你自己的 AstrBot

你需要 AstrBot（至少啟動過一次，使其 data 資料夾已經存在）和 personagent（`python -m pip install personagent`，請參閱其 README）。

### 使用 personagent 的設定流程

```bash
personagent connect astrbot
```

此指令會先尋找 AstrBot 的 data 資料夾，也就是存放 `cmd_config.json`、`plugins/` 和 `config/` 的資料夾。找不到時，它可以代為下載 AstrBot。接著它會詢問 AstrBot 是否在 Docker 中執行、機器人要加入哪個聊天應用程式（AstrBot 尚需該應用程式的 token 時會一併詢問）、哪些群組、管理員是誰，以及允許哪些人私訊。經由 NapCat 接入 QQ 時，還會詢問機器人帳號的 QQ 號碼。最後它會複製此外掛程式，產生共用權杖並寫入兩端，再寫入允許清單。`personagent init --terminal` 的最後一步也提供相同的流程。

如果不想逐項回答，可以直接指定 data 資料夾：

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

以此方式執行時，首次連線的允許清單為**空**，須在外掛程式設定中填寫。`personagent connect astrbot --help` 列出了可同時在 AstrBot 中開啟平台的參數。

此指令可隨時重複執行。它會保留允許清單、其他已排除的平台，以及外掛程式可接受的 `personagent_url`（請參閱[personagent 的執行位置](#personagent-的執行位置)）。外掛程式會拒絕的 `personagent_url` 則會替換為預設的本機位址。只有傳入 `--qq` 或 `--no-qq` 時，QQ 路由才會改變，personagent 的 `CONNECTOR_QQ_PLATFORMS` 也隨之變更。詢問時，目前的允許清單即為預設值：按 Enter 鍵保留，輸入 `-` 清空。

接著重新啟動 AstrBot 並啟動 personagent（請參閱[確認運作正常](#確認運作正常)）。

### 從 AstrBot 網頁介面安裝

1. 從 [personagent 最新 Release](https://github.com/wangkant/personagent/releases/latest) 下載 `astrbot_plugin_personagent.zip`。
2. 在 AstrBot 外掛程式頁面的 **從檔案安裝** 中上傳。
3. 將 `connector_token` 設為 personagent 的 `.env` 中的 `CONNECTOR_TOKEN`，並依下文填寫允許清單。
4. 如果 AstrBot 與 personagent 不在同一台電腦上，請將 `personagent_url` 設為 HTTPS 位址（請參閱[personagent 的執行位置](#personagent-的執行位置)）。

升級時，請以相同方式上傳新版 zip。AstrBot 4.29 及以後的版本會取代已安裝的副本。更早的版本須先解除安裝外掛程式，解除安裝時請勿勾選 **同時刪除外掛程式設定檔**。

### 手動安裝

1. 將本資料夾複製至 `<AstrBot data dir>/plugins/astrbot_plugin_personagent/`。
2. 重新啟動 AstrBot，或在網頁介面中重新載入外掛程式。AstrBot 會安裝 `requirements.txt`，其中只列出 `httpx`。
3. 在網頁介面中開啟外掛程式設定。設定儲存於 `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json`。
   - 將角色可以加入的群組 ID 填入 `groups`。
   - 將允許私訊並獲得回覆的傳送者 ID 填入 `dm_users`。
   - 如果 personagent 的 `.env` 設定了 `CONNECTOR_TOKEN`，請將相同的值填入 `connector_token`。personagent 位於其他主機時必須填寫。
   - personagent 位於同一主機且使用預設的 `SERVER_PORT=8080` 時，`personagent_url` 維持預設值即可。

外掛程式**預設拒絕**。允許清單為空時，它不轉送任何訊息，AstrBot 的行為與未安裝外掛程式時相同。ID 請依 AstrBot 顯示的格式填寫；在聊天中傳送 `/sid` 即可查看。不帶前綴的 ID 適用於所有配接器。`qq_official:ID` 只適用於該配接器，`qq_official:*` 轉送該配接器上所有同類對話。

`groups` 或 `dm_users` 中單獨的 `*` 會轉送所有配接器上所有同類對話，並標記為 `prefiltered: false`。此時僅由 personagent 本身的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 決定。沒有項目的平台會被 personagent 拒絕，QQ 群組除外：`ACCESS_GROUPS` 未列出任何 QQ 群組時，它會回應所有 QQ 群組。

### 確認運作正常

1. 以 `personagent run` 啟動 personagent，此指令只啟動服務本身。啟動資訊應顯示 `agent: on`。
2. 在獲准的群組中提及機器人的名稱（personagent 的 `PERSONA_NAME`）。

如果沒有回覆，請先在 AstrBot 記錄檔中尋找以 `personagent:` 開頭的行，再查看 `personagent run` 在啟動資訊之後輸出的內容，並參閱[疑難排解](#疑難排解)。

## 設定

| 設定 | 型別 | 預設值 | 說明 |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | personagent 的基礎位址。外掛程式會加上 `/v1/events` 和 `/v1/outbox`。必須是本機位址，或已設定 `connector_token` 的 HTTPS 位址。 |
| `connector_token` | string | `""` | 共用金鑰。必須與 personagent 的 `CONNECTOR_TOKEN` 一致。`personagent_url` 不是本機位址時必須填寫。 |
| `timeout_s` | int | `420` | 每次嘗試等待的秒數。請參閱[逾時](#逾時)。 |
| `excluded_platforms` | list | `["aiocqhttp"]` | 永不轉送的配接器名稱。移除 `aiocqhttp` 後，QQ（NapCat）會經由此外掛程式接入。請參閱[透過 NapCat 接入 QQ](#透過-napcat-接入-qq)。 |
| `groups` | list | `[]` | 要轉送的群組 ID。為空時不轉送任何群組。`adapter:ID` 或 `adapter:*` 將項目限定於一個配接器。單獨的 `*` 不經篩選地轉送所有群組。 |
| `dm_users` | list | `[]` | 其私訊會被轉送的傳送者 ID。為空時不轉送私訊。`adapter:ID` 或 `adapter:*` 將項目限定於一個配接器。單獨的 `*` 不經篩選地轉送所有私訊。 |
| `block_default` | bool | `true` | personagent 接管對話時，停止 AstrBot 的處理流程。 |
| `forward_quoted_text` | bool | `true` | 平台有提供時，將被引用訊息的文字和作者連同其 id 一併傳送。開啟且 `quote_max_chars` 大於 0 時，每個事件都會宣告 `quote_text` 功能。 |
| `quote_max_chars` | int | `200` | 傳送的被引用文字的最大長度。更長的引用會被截斷。 |
| `max_inline_image_bytes` | int | `4000000` | 內嵌傳送之圖片的最大位元組數。personagent 無法自行取得的圖片（Telegram、本機檔案、私人位址）會以內嵌方式傳送。更大的圖片只會以提示 `(sent an image)` 送達。此值應小於 personagent 的 `VISION_MAX_IMAGE_BYTES`。 |
| `outbox_enabled` | bool | `true` | 拉取並傳送 personagent 的 outbox。請參閱 [Outbox](#outbox)。 |
| `outbox_wait_s` | int | `25` | 每次拉取 outbox 時在 personagent 端最多等待的秒數，上限為 30。 |
| `connector_id` | string | `""` | 此 AstrBot 在 personagent 中的名稱。留空時會產生一次並儲存。兩台 AstrBot 主機須使用不同的名稱。 |

### personagent 的執行位置

- **同一主機**，或與主機共用網路命名空間、使用主機網路的容器：維持預設的本機 `personagent_url`。
- **其他容器或主機**：使用 HTTPS 的 `personagent_url`，並在 `connector_token` 和 personagent 的 `CONNECTOR_TOKEN` 中設定相同的非空金鑰。終點為 AstrBot 可存取之本機位址的私人通道也可以使用。此時同樣須在兩端設定相同的權杖，因為 personagent 會拒絕經由代理伺服器傳入、未帶權杖的請求。

外掛程式會拒絕傳送至本機以外的明文 `http://`，例如 `http://host.docker.internal:8080`，即使設定了權杖亦然。此時每則訊息都會記錄 `refusing unsafe personagent_url`，並由 AstrBot 內建的模型回答。

**AstrBot 在 Docker 中執行。** 在容器內，`127.0.0.1` 指向容器本身，因此預設的 `personagent_url` 無法連線至任何服務。可擇一處理：

- 讓 AstrBot 使用主機網路：在 compose 檔案中寫入 `network_mode: host`，或使用 `docker run --network host`。Docker Desktop 須為 4.34 或更新版本，並開啟 host networking。同一 compose 檔案中的 NapCat 容器也須使用主機網路。
- 將 personagent 置於 HTTPS 之後，並將該位址設為 `personagent_url`（`personagent connect astrbot <dir> --url https://...`）。

personagent 預設監聽 `127.0.0.1:8080`。如果將其 `SERVER_HOST` 設為非本機位址，在未設定 `CONNECTOR_TOKEN` 時它會拒絕啟動。在 personagent 前方加入代理伺服器或通道之前，請先設定權杖，即使位於同一主機上亦然。

### 逾時

每個請求會持續到 personagent 完成一個回合為止，其中包括一小段防彈跳時間，以及每次模型呼叫和重試。`timeout_s` 用盡後，personagent 仍會完成該回合並保留學到的內容，但回覆會遺失，改由 AstrBot 內建的模型回答此訊息。

請讓 personagent 的 3 × `LLM_TIMEOUT_S` 低於 `timeout_s`。一個回合的所有模型呼叫（含重試）共用 1.5 × `LLM_TIMEOUT_S`，而且訊息須先等待其抵達時正在思考的那一回合結束。依 personagent 的預設值（`LLM_TIMEOUT_S=120`），此值為 360 秒，預設的 `timeout_s` 420 足以涵蓋。如果調高 personagent 的 `LLM_TIMEOUT_S`，也須一併調高 `timeout_s`。

只要經簽章的請求仍在有效期限內，外掛程式會對 personagent 傳回的 429 或 500 最多重試兩次，遇到 429 時會遵循 `Retry-After`。

### `block_default` 與對話歸屬

每當 personagent 回報對話由它接管（`owned: true`），無論它是否回覆，外掛程式都會停止 AstrBot 的處理流程，使 AstrBot 內建的模型在角色不發言的回合中也不會插話。

傳輸錯誤、無效的回應，以及 personagent 拒絕的對話，會繼續交由 AstrBot 的一般處理流程。如果 personagent 的回應沒有 `owned` 欄位，外掛程式會改用 `handled`。

## 透過 NapCat 接入 QQ

QQ 官方機器人由 personagent 直接連線，不需要 AstrBot。本節僅適用於以 NapCat（或其他 OneBot v11 實作）執行 QQ 帳號、經由 AstrBot 的 `aiocqhttp` 配接器接入的情況。在 personagent 本身的頁面上新增 OneBot v11 時，頁面會代為從 `excluded_platforms` 中移除 `aiocqhttp`，並設定 `CONNECTOR_QQ_PLATFORMS`。

1. 從 `excluded_platforms` 中移除 `aiocqhttp`，並將 QQ 群組加入 `groups`。
2. 在 personagent 的 `.env` 中設定 `CONNECTOR_QQ_PLATFORMS=aiocqhttp` 和 `QQ_BOT_ID`（機器人帳號的 QQ 號碼）。
3. 選用：將 personagent 的 `QQ_ONEBOT_URL` 設為 NapCat 的 HTTP 服務。這會開啟補回遺漏之 @ 的掃描，此功能同樣需要 `QQ_BOT_ID`。外掛程式拉取 outbox 時，主動訊息、被否定後的追問和模型失敗時在群組中的致歉，都會經由此外掛程式的 [outbox](#outbox) 傳送。否則，在設定了該位址的前提下，會直接經由 NapCat 傳送。
4. 如果 NapCat 仍在向 personagent 的 `/v1/onebot` 傳送事件，請將其關閉。此方式已棄用，兩者同時執行會使每則訊息送達兩次。

`personagent connect astrbot <data dir> --qq` 會從 `excluded_platforms` 中移除 `aiocqhttp`，並設定 `CONNECTOR_QQ_PLATFORMS`。未指定資料夾執行時，它還會詢問 `QQ_BOT_ID`。部署教學也說明了此方式：[docs/deploy.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-TW.md#第三方路線astrbot--napcat)。

請勿省略 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。缺少此項時，personagent 會將 QQ 對話記錄於帶有 `aiocqhttp:` 前綴的 ID 之下，原有 QQ ID 下學到的內容將不再相符，且學習紀錄事後無法遷移。

由於 QQ ID 不帶前綴，personagent 本身的 QQ 設定依然適用。`ACCESS_GROUPS` 中的 QQ 項目決定開放的群組（沒有項目表示所有 QQ 群組），私訊只回應 `ADMIN_IDS` 中的管理員或 `ACCESS_DM_USERS` 中所列的人。設定精靈會將你提供的 QQ 群組寫入 personagent 的 `.env`。日後新增 QQ 群組時，請將其同時加入 `groups` 和 `ACCESS_GROUPS`，或在 `ACCESS_GROUPS` 中不列出任何 QQ 群組。

讓 AstrBot 接入訊息量較大的 QQ 群組之前，請檢查 AstrBot 的兩項設定。兩者都在外掛程式處理之前執行。

- `platform_settings.rate_limit` 預設為每 60 秒 30 則。超出的訊息會被延遲，而非捨棄。請調高或關閉此限制。
- `content_safety.internal_keywords` 預設開啟，會捨棄命中關鍵字清單的訊息，包括角色原本應回答的訊息。請檢查此清單。

## 平台

personagent 只使用一種中立格式，外掛程式在邊界處以各平台本身的機制進行轉換。下表已對照 AstrBot 4.25.5 的配接器核對。

在所有平台上：

- 只轉送真人撰寫的訊息。QQ 通知（戳一戳、收回、入群）和請求，以及 Slack 的入群和主題變更，均不計為回合。
- 影片、檔案和語音訊息會以角色可以回應的提示送達，例如 `(sent a video)`、`(sent a file: deck.pdf)` 或 `(sent a voice message)`，平台提供轉寫時會一併附上。
- 平台有提供時，被引用的訊息會附帶文字和作者（`forward_quoted_text`）。
- 只要配接器有保留，訊息時間即為平台本身記錄的時間，而非 AstrBot 收到的時間。
- 回覆會依低於平台長度上限的長度拆分，@ 和跳脫字元依平台的演算法計數。回覆絕不會轉為文字圖片，並依平台的方式提及他人。
- 只有在平台能主動傳送訊息時才使用 outbox。

| 平台（配接器） | 可用功能 | 平台本身無法支援的功能 |
| --- | --- | --- |
| QQ 經由 OneBot（`aiocqhttp`） | 群組和私訊。@ 和回覆機器人，包括配接器查不到被 @ 者時。表情名稱、商城表情（`mface`）和標記為表情的圖片。真正的 QQ @，後接一個空格。長回覆依 AstrBot 的 `forward_threshold` 以下的長度拆分，不會轉為合併轉發卡片。Outbox。 | Markdown 會按原樣顯示。 |
| QQ 官方（`qq_official`、`qq_official_webhook`） | @ 機器人的群組訊息和私訊。表情顯示為 `[表情:name]`。回覆要求純文字，而非配接器的 markdown。 | 群組中只會傳遞 @ 機器人的訊息，因此角色無法掌握對話脈絡。沒有引用、沒有名稱（只有 openid），回覆中無法 @。只能在訊息後 5 分鐘內回覆，因此沒有 outbox。 |
| Telegram（`telegram`） | 群組、主題（`<chat>#<thread>`）和私訊。回覆機器人的任何類型訊息，並移除配接器的 `/@bot` 喚醒前綴。貼圖表情，靜態貼圖還會附上圖片。圖片經由配接器的機器人取得，因此 bot token 不會離開 AstrBot。被提及的使用者名稱在該使用者發言後會轉為數字 id。回覆以使用者名稱提及，沒有使用者名稱的人則使用 `tg://user` 連結，`*`、`_` 等字元按原樣顯示。Outbox。 | BotFather 的隱私模式開啟時（預設），群組中只會傳遞指令、@ 和回覆機器人的訊息。須關閉此模式，角色才能掌握對話脈絡。動態貼圖和影片貼圖無法檢視。 |
| Discord（`discord`） | 頻道和討論串視為群組，另有私訊。開頭的 `@bot`（配接器會移除）、提及機器人所屬的某個身分組、回覆機器人，都視為對它說話。附帶文字的引用。貼圖。語音和影片附件以提示送達。提及格式為 `<@id>`，`@everyone` 和 `@here` 維持無效。回覆依 2000 字元拆分。Outbox，包括私訊。 | 須開啟 Message Content intent。 |
| Slack（`slack`） | 頻道和私訊。在機器人訊息下的 thread 回覆視為對它說話。連結會展開。訊息 id 為 Slack 的 `ts`。提及格式為 `<@id>`。`&`、`<` 和 `>` 會跳脫，文字無法提及頻道。回覆依 3000 字元拆分。Outbox。 | thread 回覆不附帶上層訊息的文字。機器人沒有輸入中提示。回答會出現在頻道中，而非 thread 中（配接器限制）。 |
| KOOK（`kook`） | 頻道和私訊。@，以及提及機器人所擁有的角色。KOOK 有附帶時的引用。`(emj)` 表情和實際傳送時間。提及寫在文字中，角色文字中的 `(met)` 式標記維持無效。圖片以檔案形式傳送，因為配接器只上傳 JPEG base64。Outbox。 | AstrBot 的配接器會在任何外掛程式處理之前，捨棄純圖片、檔案、語音和影片訊息（卡片除外）。沒有輸入中提示。 |
| Lark / 飛書（`lark`） | 群組和私訊。@ 和回覆機器人（Lark 將應用程式標示為傳送者）。附帶文字的引用。表情以 emoji 送達。Outbox。 | 沒有「讀取群組內所有訊息」權限時，只會收到 @ 訊息。每則回覆都會引用其所回答的訊息，markdown 會被轉譯（配接器限制）。名稱為 id 前綴。 |
| 釘釘（`dingtalk`） | 群組和私訊。配接器以本機檔案交付的圖片會以內嵌方式傳送。影片以提示送達。Outbox。私訊可送達曾傳訊息給機器人的人。 | 群組中只會傳遞 @ 機器人的訊息。沒有引用，回覆中無法 @ 或引用回覆。每則回覆都是標題為 "AstrBot" 的 markdown（配接器限制）。 |
| LINE（`line`） | 群組、聊天室和私訊。@ 機器人。引用 id。貼圖關鍵字。一個回合的對話框以一次呼叫傳送，每次五個，免費的 reply token 足以涵蓋。Outbox，計入推播配額。 | LINE 不傳送被引用的文字。回覆中無法提及（配接器限制）。傳送圖片需要公開的 HTTPS `callback_api_base`。名稱為 id 前綴。 |
| Mattermost（`mattermost`） | 頻道和私訊。@ 機器人。thread 的起始訊息作為引用。圖片內嵌。該使用者發言後可依使用者名稱提及。`@channel`、`@all` 和 `@here` 維持無效。回覆依 4000 字元拆分。Outbox。 | 被引用的文字需要一次外掛程式不會執行的查詢。沒有輸入中提示。 |
| Misskey（`misskey`） | Chat 私訊和聊天室，聊天室訊息中任何位置的 `@bot`。該使用者發言後提及格式為 `@user@host`，角色文字中其他的 `@` 維持無效。回覆依 3000 字元拆分。聊天和聊天室的 Outbox。 | Note（公開貼文）不轉送，因為 AstrBot 將其歸為系統事件，且回覆也會公開。`unique_session` 會破壞聊天室（配接器限制）。 |
| Satori（`satori`） | Satori 後端所橋接的內容：群組、私訊、@、回覆機器人、附帶文字的引用。毫秒時間戳記依秒讀取。Outbox。 | 群組 id 為 guild，因此同一 guild 的各頻道共用一個對話。被橋接平台的限制同樣適用。 |
| WebChat（`webchat`） | 儀表板聊天，視為私訊。引用和圖片。Outbox，即時顯示或儲存至對話。 | 僅限一對一。 |
| 企業微信應用（`wecom`） | 私訊、圖片，以及附帶轉寫的語音。客服模式只轉送客戶的訊息，並附帶實際傳送時間。回覆依位元組拆分。應用模式的 Outbox，要求 AstrBot 啟動後曾有人傳訊息過來。 | 僅限私訊，沒有引用。客服模式無法主動傳送。Markdown 會按原樣顯示。 |
| 企業微信智慧機器人（`wecom_ai_bot`） | 群組（企業微信只在 @ 機器人時傳遞群組訊息）和私訊。語音、檔案和影片提示。一個回合以一則串流回答傳送。 | 只能在回答某則訊息時回覆，因此沒有 outbox，也無法提及。回答會以 markdown 轉譯。請在 AstrBot 中設定 `wecom_ai_bot_name`，使 "@bot" 從文字中移除。 |
| 微信公眾號（`weixin_official_account`） | 私訊，以及附帶轉寫的語音。一個回合以一則訊息傳送。 | 被動模式下，每則使用者訊息只能回覆一則，且須在微信的 5 秒時限內。其餘內容須等待使用者的下一則訊息，角色不發言的回合會讓使用者持續等待（配接器限制）。只有主動模式能傳送圖片。沒有 outbox。 |
| 個人微信（`weixin_oc`） | 私訊。附帶文字的引用。圖片內嵌。附帶轉寫的語音。輸入中提示。Outbox。 | 沒有群組。重新登入後，在對方再次傳訊息之前都無法聯絡對方。 |
| 其他配接器 | 依 AstrBot 的交付方式轉送。提及以 At 表示。 | 不宣告 outbox。 |

## Outbox

有些訊息並非回答任何內容：定時開場、被否定後的追問，或模型無法使用時在群組中的致歉。（私訊的致歉會隨事件本身的回應傳回。）personagent 將這些訊息排入佇列，此外掛程式以與事件相同的簽章方式從 `POST <personagent_url>/v1/outbox` 拉取，因此 personagent 從不需要存取 AstrBot。Outbox 預設開啟（`outbox_enabled`）。

- 每次傳遞都經由該對話本身的 AstrBot session 依序送出，每則訊息最多傳送一次。
- 傳遞只會送往外掛程式本身從同一對話的訊息中取得的 session。這些 session 儲存在 AstrBot 的外掛程式儲存空間中，因此重新載入後仍會保留。其他向 personagent 傳送事件的程式都無法將 outbox 導向其他聊天，外掛程式會拒絕這類傳遞。
- 外掛程式在傳送時會再次檢查允許清單和 `excluded_platforms`，並拒絕已被移除的對話。
- 無法主動發言的平台（請參閱上表）絕不會收到 outbox 訊息，因為外掛程式不會為其對話宣告 outbox。
- 沒有 outbox 的 personagent 會傳回 404。外掛程式每十分鐘再查詢一次。

personagent 透過 `connector_id` 識別此 AstrBot，該 id 由外掛程式產生一次並儲存。連線至同一個 personagent 的兩台 AstrBot 主機須使用不同的 id。

## 請求驗證

設定了 `connector_token` 時，每個請求都會帶有四個請求標頭：

- `X-Personagent-Token`：權杖。
- `X-Personagent-Timestamp`：Unix 秒數。
- `X-Personagent-Nonce`：新產生的隨機值。
- `X-Personagent-Signature`：`sha256=` 後接十六進位的 HMAC-SHA256，以權杖為金鑰，內容為 `timestamp + "." + nonce + "." + body`。

請求本文為標準化 JSON：UTF-8、鍵已排序、使用緊湊分隔符號、非 ASCII 字元不跳脫。簽章涵蓋這些確切的位元組，因此代理伺服器無法改寫請求本文。personagent 會拒絕錯誤的簽章、重複的 nonce，以及與其本身時鐘相差超過五分鐘的時間戳記。請保持兩端時鐘同步。

請求本文還會以 `sent_at` 附帶配接器記錄的訊息時間。personagent 會另外依 `CONNECTOR_MAX_EVENT_AGE_S`（預設 24 小時）檢查此值，因此以新簽章重新傳送的舊事件仍會被拒絕。配接器未提供有效時間戳記的訊息，外掛程式不會轉送，而是交由 AstrBot 照常處理。

## personagent 端的身分

personagent 會為每個轉送的 id 加上平台前綴，寫作 `<platform>:<raw id>`（例如 `telegram:12345`），使不同平台的 id 不會衝突。`CONNECTOR_QQ_PLATFORMS` 中所列的平台則維持不帶前綴的 id。personagent 的 `ADMIN_IDS`、`ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 使用相同格式的 id。例如 `ADMIN_IDS=telegram:12345` 會使該帳號成為 Telegram 上的管理員，群組和私訊皆然。在 `ACCESS_GROUPS` 或 `ACCESS_DM_USERS` 中有項目的平台，同時受 personagent 和此外掛程式之允許清單的管控。

## 疑難排解

外掛程式在 AstrBot 記錄檔中的每一行都以 `personagent:` 開頭。

| 記錄 | 處理方式 |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` 是傳送至其他主機的明文 HTTP，或未設定 `connector_token` 的 HTTPS。請參閱[personagent 的執行位置](#personagent-的執行位置)。 |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` 為空或與 personagent 的 `CONNECTOR_TOKEN` 不一致、兩端時鐘相差超過五分鐘，或代理伺服器改動了請求本文。如果 personagent 的記錄檔顯示 `connector replay guard full`，請等待其清空。 |
| `agent refused the request (403): stale or invalid sent_at` | 訊息早於 personagent 的 `CONNECTOR_MAX_EVENT_AGE_S`。通常發生在 AstrBot 一次傳遞大量積壓訊息之後。 |
| `agent refused the request (403): authentication required` 或 `... only local requests accepted` | personagent 未設定 `CONNECTOR_TOKEN`，而請求並非來自本機。請在兩端設定相同的權杖。 |
| `agent at capacity (429)` | personagent 已在處理 `CONNECTOR_MAX_INFLIGHT` 個回合，重試後仍拒絕此訊息，因此改由 AstrBot 內建的模型回答。如果經常發生，請調高 `CONNECTOR_MAX_INFLIGHT`。 |
| `agent rejected the body as too large (413)` | 通常是內嵌圖片過大。請調高 personagent 的 `SERVER_MAX_BODY_BYTES`。 |
| `agent rejected the event schema (400)` | 事件缺少訊息 id 或傳送者 id（部分配接器會省略），或此外掛程式有錯誤。請附上此行記錄回報問題。 |
| `timed out waiting for the agent` | 請參閱[逾時](#逾時)。 |
| `dropping event without a valid time the platform sent it` | 配接器未提供時間戳記。AstrBot 會自行處理此訊息。 |
| `agent request failed: ...` 或 `agent request failed (<status>)` | 通常是 personagent 未在執行，或 `personagent_url` 填寫有誤。404 表示路徑錯誤：`personagent_url` 是基礎位址，不含 `/v1/events`。500 表示 personagent 發生錯誤，請查看其記錄檔。 |
| `outbox off: ...` | Outbox 遵循與事件相同的 `personagent_url` 規則。請參閱第一列。 |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | personagent 的 `CONNECTOR_OUTBOX_ENABLED` 已關閉。 |
| `outbox: outbox pull refused (403)` 或 `outbox pull failed: ...` | 原因與事件相同：權杖、時鐘，或 personagent 未在執行。外掛程式兩次嘗試之間的退避時間最長為一分鐘。 |
| `outbox: no running platform '<id>'` | 傳遞所對應的配接器在 AstrBot 中已停用或已更名。外掛程式會向 personagent 回報傳遞失敗。 |
| `could not store connector_id` | AstrBot 的外掛程式儲存空間寫入失敗。請自行設定 `connector_id`，否則每次重新啟動後，personagent 都會將其視為一個新的 AstrBot。 |

如果 AstrBot 內建的模型突然以另一種語氣回覆，表示外掛程式未連線至 personagent，或 personagent 未接管此對話。請對照上表排查，再執行 `personagent doctor`。如果 personagent 是由本機頁面啟動的，請開啟頁面上的 **動態**，查看訊息是否送達、角色為何沒有發言。如果是以 `personagent run` 啟動的，請查看其終端機輸出。

如果 personagent 本身的記錄檔指出聯結器傳送了 `X-Personagent-Token`，但 `CONNECTOR_TOKEN` 為空，表示 personagent 忽略了該權杖。請在其 `.env` 中設定相同的值。

在 QQ、Telegram、Discord、KOOK、QQ 官方和 Misskey 上，訊息時間為平台本身記錄的時間，而非 AstrBot 收到的時間。AstrBot 停止執行的時間超過 personagent 的 `CONNECTOR_MAX_EVENT_AGE_S` 時，personagent 會將 AstrBot 傳遞的積壓訊息視為過期訊息而拒絕。

## 已知限制：Telegram 提及

AstrBot 的 Telegram 配接器以數字使用者 id 識別傳送者（`telegram:<numeric id>`），但訊息中的 `@username` 提及只以使用者名稱表示。該使用者在 AstrBot 啟動後發言過之後，外掛程式會將被提及的使用者名稱改寫為其數字 id。在此之前，提及會以使用者名稱的形式送達 personagent。

回覆以使用者名稱提及，沒有使用者名稱的人則使用 `tg://user` 連結。AstrBot 啟動後未曾見過的人，外掛程式不會提及。
