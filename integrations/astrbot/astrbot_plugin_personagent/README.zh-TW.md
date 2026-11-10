# astrbot_plugin_personagent

[English](README.md) · [简体中文](README.zh-CN.md) · 繁體中文 · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


這個 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 外掛把 AstrBot 連線到 [personagent](https://github.com/wangkant/personagent)。它把每條允許的訊息轉發給 personagent，再把 personagent 的回覆發回聊天。

## 你需要它嗎

QQ、微信、Telegram、Discord 不需要這個外掛。personagent 會直接連線它們，不經過 AstrBot。執行 `personagent` 開啟本地頁面，在 **連接平台** 裡新增即可。

只有 AstrBot 負責收發訊息時才需要這個外掛，分兩種情況。

- **在 personagent 頁面裡新增其他平臺。** KOOK、飛書、釘釘、Slack、企業微信智慧機器人、Mattermost、Misskey，以及「高階」一欄裡的平臺，都經由 AstrBot 接入。頁面會替你下載並執行 AstrBot，並裝好這個外掛，你無需在這裡做任何操作。
- **你已經在執行 AstrBot**，它有自己的平臺和外掛。按下面的步驟安裝外掛。

## 它做什麼

- 接收 AstrBot 所有平臺介面卡（Telegram、Discord、Slack、QQ……）的群訊息和私聊，`excluded_platforms` 中的除外。
- 把白名單內的群和傳送者的訊息，以平臺中立的事件轉發到 personagent 的 `POST /v1/events`。它按各介面卡的實際交付方式讀取訊息，包括誰被 @、引用了什麼、表情、圖片、語音，以及平臺記錄的傳送時間。
- 經 AstrBot 把 personagent 的回覆按各平臺要求的形式發回。回覆可以包含文字和圖片，在群聊中可按 personagent 的要求帶上 @。
- 拉取 personagent 的 outbox，傳送它主動說的話，例如定時開場、追問，或模型不可用時在群裡的致歉。見 [Outbox](#outbox)。
- personagent 接管會話時停止 AstrBot 自身的流水線（`block_default`），這樣 AstrBot 自帶的模型不會代替角色回答。

人設、記憶、防抖和打字模擬都在 personagent 中執行。這個外掛是 personagent 的 [`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.zh-TW.md) 所定義的聯結器。

## 裝進你自己的 AstrBot

你需要 AstrBot（至少啟動過一次，讓它的 data 資料夾已經存在）和 personagent（`python -m pip install personagent`，見其 README）。

### 用 personagent 的設定流程

```bash
personagent connect astrbot
```

這條命令先查詢 AstrBot 的 data 資料夾，也就是存放 `cmd_config.json`、`plugins/` 和 `config/` 的資料夾。找不到時，它可以替你下載 AstrBot。接著它詢問 AstrBot 是否執行在 Docker 裡、機器人加入哪個聊天應用（AstrBot 還需要時會要該應用的 token）、哪些群、管理員是誰、允許哪些人私聊。經 NapCat 接 QQ 時還會詢問機器人賬號的 QQ 號。最後它複製這個外掛，生成共享 token 寫入兩邊，並寫好白名單。`personagent init --terminal` 的最後一步也提供同樣的流程。

如果不想逐項回答，可以直接指定 data 資料夾：

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

這樣執行時，首次連線的白名單為**空**，需要在外掛設定裡填寫。`personagent connect astrbot --help` 列出了同時在 AstrBot 中開啟平臺的引數。

這條命令隨時可以重複執行。它會保留白名單、其他被排除的平臺，以及外掛接受的 `personagent_url`（見[personagent 可以執行在哪裡](#personagent-可以執行在哪裡)）。外掛會拒絕的 `personagent_url` 則替換為預設的本機地址。只有傳 `--qq` 或 `--no-qq` 時 QQ 路由才會改變，personagent 的 `CONNECTOR_QQ_PLATFORMS` 隨之變化。詢問時，當前白名單就是預設值：按回車保留，輸入 `-` 清空。

然後重啟 AstrBot 並啟動 personagent（見[確認可以工作](#確認可以工作)）。

### 從 AstrBot 網頁安裝

1. 從 [personagent 最新 Release](https://github.com/wangkant/personagent/releases/latest) 下載 `astrbot_plugin_personagent.zip`。
2. 在 AstrBot 外掛頁的 **從檔案安裝** 上傳它。
3. 把 `connector_token` 設為 personagent 的 `.env` 中的 `CONNECTOR_TOKEN`，並按下文填寫白名單。
4. 如果 AstrBot 與 personagent 不在同一臺電腦上，把 `personagent_url` 設為 HTTPS 地址（見[personagent 可以執行在哪裡](#personagent-可以執行在哪裡)）。

升級時用同樣的方式上傳新版 zip。AstrBot 4.29 及以後的版本會替換已安裝的副本。更早的版本需要先解除安裝外掛，解除安裝時不要勾選 **同時刪除外掛配置檔案**。

### 手動安裝

1. 把本資料夾複製到 `<AstrBot data dir>/plugins/astrbot_plugin_personagent/`。
2. 重啟 AstrBot，或在網頁中重新載入外掛。AstrBot 會安裝 `requirements.txt`，其中只列了 `httpx`。
3. 在網頁中開啟外掛設定。設定儲存在 `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json`。
   - 把角色可以加入的群 ID 填入 `groups`。
   - 把允許私聊並得到回答的傳送者 ID 填入 `dm_users`。
   - 如果 personagent 的 `.env` 設定了 `CONNECTOR_TOKEN`，把相同的值填入 `connector_token`。personagent 在其他主機上時必須填寫。
   - personagent 在同一主機上且使用預設的 `SERVER_PORT=8080` 時，`personagent_url` 保持預設。

外掛**預設拒絕**。白名單為空時它不轉發任何訊息，AstrBot 的表現與未安裝外掛時相同。ID 按 AstrBot 顯示的格式填寫；在聊天中傳送 `/sid` 即可檢視。不帶字首的 ID 對所有介面卡生效。`qq_official:ID` 只對該介面卡生效，`qq_official:*` 轉發該介面卡上的全部同類會話。

`groups` 或 `dm_users` 中單獨的 `*` 轉發所有介面卡上的全部同類會話，並標記為 `prefiltered: false`。此時只由 personagent 自身的 `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 決定。沒有條目的平臺會被 personagent 拒絕，QQ 群除外：`ACCESS_GROUPS` 未列出任何 QQ 群時，它回應所有 QQ 群。

### 確認可以工作

1. 用 `personagent run` 啟動 personagent，它只啟動服務本身。啟動資訊應顯示 `agent: on`。
2. 在允許的群裡說出機器人的名字（personagent 的 `PERSONA_NAME`）。

如果沒有回覆，先在 AstrBot 日誌中找 `personagent:` 開頭的行，再看 `personagent run` 在啟動資訊之後列印的內容，並參見[出了問題](#出了問題)。

## 設定

| 設定 | 型別 | 預設值 | 說明 |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | personagent 的基礎地址。外掛會加上 `/v1/events` 和 `/v1/outbox`。必須是本機地址，或已設定 `connector_token` 的 HTTPS 地址。 |
| `connector_token` | string | `""` | 共享金鑰。必須與 personagent 的 `CONNECTOR_TOKEN` 一致。`personagent_url` 不是本機地址時必須填寫。 |
| `timeout_s` | int | `420` | 每次嘗試等待的秒數。見[超時](#超時)。 |
| `excluded_platforms` | list | `["aiocqhttp"]` | 永不轉發的介面卡名。刪除 `aiocqhttp` 後 QQ（NapCat）經這個外掛接入。見[經 NapCat 接 QQ](#經-napcat-接-qq)。 |
| `groups` | list | `[]` | 要轉發的群 ID。為空時不轉發任何群。`adapter:ID` 或 `adapter:*` 把條目限制到一個介面卡。單獨的 `*` 不加過濾地轉發所有群。 |
| `dm_users` | list | `[]` | 私聊會被轉發的傳送者 ID。為空時不轉發私聊。`adapter:ID` 或 `adapter:*` 把條目限制到一個介面卡。單獨的 `*` 不加過濾地轉發所有私聊。 |
| `block_default` | bool | `true` | personagent 接管會話時停止 AstrBot 的流水線。 |
| `forward_quoted_text` | bool | `true` | 平臺提供時，把被引用訊息的文字和作者連同其 id 一起傳送。開啟且 `quote_max_chars` 大於 0 時，每個事件都宣告 `quote_text` 能力。 |
| `quote_max_chars` | int | `200` | 傳送的被引用文字的最大長度。更長的引用會被截斷。 |
| `max_inline_image_bytes` | int | `4000000` | 內嵌傳送圖片的最大位元組數。personagent 無法自行獲取的圖片（Telegram、本地檔案、私有地址）會內嵌傳送。更大的圖片只以提示 `(sent an image)` 到達。應小於 personagent 的 `VISION_MAX_IMAGE_BYTES`。 |
| `outbox_enabled` | bool | `true` | 拉取併傳送 personagent 的 outbox。見 [Outbox](#outbox)。 |
| `outbox_wait_s` | int | `25` | 一次 outbox 拉取在 personagent 處最多等待多久，上限 30。 |
| `connector_id` | string | `""` | 這個 AstrBot 在 personagent 中的名字。留空時生成一次並儲存。兩臺 AstrBot 主機需要不同的名字。 |

### personagent 可以執行在哪裡

- **同一主機**，或與主機共享網路名稱空間、使用主機網路的容器：保持預設的本機 `personagent_url`。
- **其他容器或主機**：使用 HTTPS 的 `personagent_url`，並在 `connector_token` 和 personagent 的 `CONNECTOR_TOKEN` 中設定相同的非空金鑰。結束於 AstrBot 可見的本機地址的私有隧道也可以。這種情況下同樣要在兩邊設定相同的 token，因為 personagent 會拒絕經代理到達的無 token 請求。

外掛拒絕發往本機以外的明文 `http://`，例如 `http://host.docker.internal:8080`，即使有 token 也一樣。此時每條訊息都會記錄 `refusing unsafe personagent_url`，由 AstrBot 自帶的模型回答。

**AstrBot 在 Docker 裡。** 在容器內，`127.0.0.1` 指向容器自身，所以預設的 `personagent_url` 什麼也連不到。有兩種選擇：

- 讓 AstrBot 使用主機網路：在 compose 檔案中寫 `network_mode: host`，或使用 `docker run --network host`。Docker Desktop 需要 4.34 或更高版本並開啟 host networking。同一 compose 檔案中的 NapCat 容器也要使用主機網路。
- 把 personagent 放在 HTTPS 後面，並把該地址設為 `personagent_url`（`personagent connect astrbot <dir> --url https://...`）。

personagent 預設監聽 `127.0.0.1:8080`。如果把它的 `SERVER_HOST` 設為非本機地址，未設定 `CONNECTOR_TOKEN` 時它會拒絕啟動。在 personagent 前面放代理或隧道之前先設好 token，即使在同一主機上也一樣。

### 超時

每次請求持續到 personagent 完成一個回合，包括一小段防抖時間，以及每次模型呼叫和重試。`timeout_s` 用盡後，personagent 仍會完成這個回合並保留學到的內容，但回覆會丟失，AstrBot 自帶的模型轉而回答這條訊息。

讓 personagent 的 3 × `LLM_TIMEOUT_S` 低於 `timeout_s`。一個回合的所有模型呼叫（含重試）共用 1.5 × `LLM_TIMEOUT_S`，而且訊息要先等它到達時正在思考的那個回合結束。按 personagent 的預設值（`LLM_TIMEOUT_S=120`），這是 360 秒，預設的 `timeout_s` 420 足以覆蓋。如果調大 personagent 的 `LLM_TIMEOUT_S`，`timeout_s` 也要調大。

只要簽名後的請求還新鮮，外掛會對 personagent 返回的 429 或 500 最多重試兩次，429 時遵循 `Retry-After`。

### `block_default` 與會話歸屬

每當 personagent 報告會話歸它所有（`owned: true`），無論它是否回覆，外掛都會停止 AstrBot 的流水線，這樣角色不開口的回合裡 AstrBot 自帶的模型也不會插話。

傳輸錯誤、無效響應和 personagent 拒絕的會話會繼續走 AstrBot 的普通流水線。如果 personagent 的響應沒有 `owned` 欄位，外掛改用 `handled`。

## 經 NapCat 接 QQ

QQ 官方機器人由 personagent 直接連線，不需要 AstrBot。本節只適用於用 NapCat（或其他 OneBot v11 實現）執行 QQ 賬號、經 AstrBot 的 `aiocqhttp` 介面卡接入的情況。在 personagent 自己的頁面上新增 OneBot v11 時，頁面會替你從 `excluded_platforms` 刪除 `aiocqhttp` 並設定 `CONNECTOR_QQ_PLATFORMS`。

1. 從 `excluded_platforms` 刪除 `aiocqhttp`，並把 QQ 群加入 `groups`。
2. 在 personagent 的 `.env` 中設定 `CONNECTOR_QQ_PLATFORMS=aiocqhttp` 和 `QQ_BOT_ID`（機器人賬號的 QQ 號）。
3. 可選：把 personagent 的 `QQ_ONEBOT_URL` 設為 NapCat 的 HTTP 服務。這會開啟補回漏掉的 @ 的掃描，它同樣需要 `QQ_BOT_ID`。外掛拉取時，主動訊息、被拒絕後的追問和模型失敗時群裡的致歉都經這個外掛的 [outbox](#outbox) 傳送。否則在設定了該地址的前提下，直接經 NapCat 傳送。
4. 如果 NapCat 還在向 personagent 的 `/v1/onebot` 傳送事件，請關閉。這條路線已棄用，兩者同時執行會讓每條訊息送達兩次。

`personagent connect astrbot <data dir> --qq` 會從 `excluded_platforms` 刪除 `aiocqhttp` 並設定 `CONNECTOR_QQ_PLATFORMS`。不指定資料夾執行時，它還會詢問 `QQ_BOT_ID`。部署教程也講了這條路線：[docs/deploy.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-TW.md#第三方路線astrbot--napcat)。

不要省略 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。缺少它時，personagent 會把 QQ 會話記在帶 `aiocqhttp:` 字首的 ID 下，原有 QQ ID 下學到的內容不再匹配，而且賬本事後無法遷移。

由於 QQ ID 不帶字首，personagent 自身的 QQ 設定依然適用。`ACCESS_GROUPS` 中的 QQ 條目決定群（沒有條目表示所有 QQ 群），私聊只回應 `ADMIN_IDS` 中的管理員或 `ACCESS_DM_USERS` 中的人。設定嚮導會把你給的 QQ 群寫入 personagent 的 `.env`。以後要新增 QQ 群時，把它同時加入 `groups` 和 `ACCESS_GROUPS`，或在 `ACCESS_GROUPS` 中不列任何 QQ 群。

讓 AstrBot 接入訊息較多的 QQ 群之前，請檢查 AstrBot 的兩項設定。它們都在外掛處理之前執行。

- `platform_settings.rate_limit` 預設每 60 秒 30 條。超出的訊息會被延遲，而不是丟棄。請調高或關閉這個限制。
- `content_safety.internal_keywords` 預設開啟，會丟棄命中關鍵詞列表的訊息，包括角色本該回答的訊息。請檢查這個列表。

## 平臺

personagent 只使用一種中立格式，外掛在邊界處用各平臺自身的機制轉換。下表已對照 AstrBot 4.25.5 的介面卡核對。

在所有平臺上：

- 只轉發真人寫的訊息。QQ 通知（戳一戳、撤回、入群）和請求，以及 Slack 的入群和話題變更，都不算回合。
- 影片、檔案和語音訊息以角色可以反應的提示到達，例如 `(sent a video)`、`(sent a file: deck.pdf)` 或 `(sent a voice message)`，平臺有轉寫時附上轉寫。
- 平臺提供時，被引用的訊息帶有文字和作者（`forward_quoted_text`）。
- 只要介面卡保留，訊息時間就是平臺自己的時間，而不是 AstrBot 收到的時間。
- 回覆按低於平臺長度上限的長度拆分，@ 和轉義按平臺的演算法計數。回覆絕不會變成文字轉圖片，並按平臺的方式稱呼他人。
- 只有平臺能主動傳送時才使用 outbox。

| 平臺（介面卡） | 可用功能 | 平臺本身做不到的事 |
| --- | --- | --- |
| QQ 經 OneBot（`aiocqhttp`） | 群和私聊。@ 和回覆機器人，包括介面卡查不到被 @ 者時。表情名稱、商城表情（`mface`）和標記為表情的圖片。真正的 QQ @，後跟一個空格。長回覆按 AstrBot 的 `forward_threshold` 以下拆分，不會變成合並轉發卡片。Outbox。 | Markdown 按原樣顯示。 |
| QQ 官方（`qq_official`、`qq_official_webhook`） | @ 機器人的群訊息和私聊。表情顯示為 `[表情:name]`。回覆請求純文字，而不是介面卡的 markdown。 | 群裡只投遞 @ 機器人的訊息，所以角色無法跟上對話。沒有引用、沒有名字（只有 openid），回覆中不能 @。只能在訊息後 5 分鐘內回覆，所以沒有 outbox。 |
| Telegram（`telegram`） | 群、話題（`<chat>#<thread>`）和私聊。回覆機器人的任意型別訊息，並去掉介面卡的 `/@bot` 喚醒字首。貼紙表情，靜態貼紙還帶圖片。圖片經介面卡的機器人獲取，所以 bot token 不會離開 AstrBot。被提及的使用者名稱在此人發過言後變成數字 id。回覆用使用者名稱提及，沒有使用者名稱的人用 `tg://user` 連結，`*`、`_` 等字元按原樣顯示。Outbox。 | BotFather 的隱私模式開啟時（預設），群裡只投遞命令、@ 和回覆機器人的訊息。關閉它，角色才能跟上對話。動畫和影片貼紙無法檢視。 |
| Discord（`discord`） | 頻道和子區算群，還有私聊。開頭的 `@bot`（介面卡會去掉）、提及機器人的某個身份組、回覆機器人，都算對它說話。帶文字的引用。貼紙。語音和影片附件以提示到達。提及為 `<@id>`，`@everyone` 和 `@here` 保持無效。回覆按 2000 字元拆分。Outbox，包括私聊。 | 需要 Message Content intent。 |
| Slack（`slack`） | 頻道和私聊。在機器人訊息下的 thread 回覆算對它說話。連結展開。訊息 id 是 Slack 的 `ts`。提及為 `<@id>`。`&`、`<` 和 `>` 轉義，文字無法提及頻道。回覆按 3000 字元拆分。Outbox。 | thread 回覆不帶父訊息文字。機器人沒有輸入提示。回答落在頻道里，不在 thread 裡（介面卡）。 |
| KOOK（`kook`） | 頻道和私聊。@，以及提及機器人持有的角色。KOOK 附帶時的引用。`(emj)` 表情和真實傳送時間。提及寫在文字中，角色文字裡 `(met)` 式的標記保持無效。圖片作為檔案傳送，因為介面卡只上傳 JPEG base64。Outbox。 | AstrBot 的介面卡在任何外掛看到之前就丟棄純圖片、檔案、語音和影片訊息（卡片除外）。沒有輸入提示。 |
| Lark / 飛書（`lark`） | 群和私聊。@ 和回覆機器人（Lark 把應用標為傳送者）。帶文字的引用。表情以 emoji 到達。Outbox。 | 沒有「讀取群內所有訊息」許可權時，只收到 @ 訊息。每條回覆都引用它回答的訊息，markdown 會渲染（介面卡）。名字是 id 字首。 |
| 釘釘（`dingtalk`） | 群和私聊。介面卡以本地檔案交付的圖片會內嵌傳送。影片以提示到達。Outbox。私聊能到達給機器人寫過信的人。 | 群裡只投遞 @ 機器人的訊息。沒有引用，回覆中不能 @ 或引用回覆。每條回覆都是標題為 "AstrBot" 的 markdown（介面卡）。 |
| LINE（`line`） | 群、房間和私聊。@ 機器人。引用 id。貼圖關鍵詞。一個回合的氣泡一次呼叫傳送，每次五個，免費的 reply token 足以覆蓋。Outbox，計入推送配額。 | LINE 不傳送被引用的文字。回覆中不能提及（介面卡）。傳送圖片需要公開的 HTTPS `callback_api_base`。名字是 id 字首。 |
| Mattermost（`mattermost`） | 頻道和私聊。@ 機器人。thread 根訊息作為引用。圖片內嵌。此人發過言後可按使用者名稱提及。`@channel`、`@all` 和 `@here` 保持無效。回覆按 4000 字元拆分。Outbox。 | 被引用的文字需要一次外掛不做的查詢。沒有輸入提示。 |
| Misskey（`misskey`） | Chat 私聊和房間，房間訊息任意位置的 `@bot`。此人發過言後提及為 `@user@host`，角色文字中其他的 `@` 保持無效。回覆按 3000 字元拆分。聊天和房間的 Outbox。 | Note（公開帖子）不轉發，因為 AstrBot 把它們歸為系統事件，回覆也會公開。`unique_session` 會破壞房間（介面卡）。 |
| Satori（`satori`） | Satori 後端橋接的內容：群、私聊、@、回覆機器人、帶文字的引用。毫秒時間戳按秒讀取。Outbox。 | 群 id 是 guild，所以一個 guild 的頻道共用一個會話。被橋接平臺的限制同樣適用。 |
| WebChat（`webchat`） | 儀表盤聊天，算私聊。引用和圖片。Outbox，實時顯示或儲存到會話。 | 只有一對一。 |
| 企業微信應用（`wecom`） | 私聊、圖片，以及帶轉寫的語音。客服模式只轉發客戶的訊息，帶真實傳送時間。回覆按位元組拆分。應用模式的 Outbox，要求 AstrBot 啟動後有人寫過信。 | 只有私聊，沒有引用。客服模式不能主動傳送。Markdown 按原樣顯示。 |
| 企業微信智慧機器人（`wecom_ai_bot`） | 群（企業微信只在 @ 機器人時投遞群訊息）和私聊。語音、檔案和影片提示。一個回合以一條流式回答傳送。 | 只能在回答某條訊息時回覆，所以沒有 outbox，也不能提及。回答按 markdown 渲染。在 AstrBot 中設定 `wecom_ai_bot_name`，這樣 "@bot" 會從文字中去掉。 |
| 微信公眾號（`weixin_official_account`） | 私聊，以及帶轉寫的語音。一個回合以一條訊息傳送。 | 被動模式每條使用者訊息只能回覆一條，且在微信的 5 秒視窗內。其餘的等使用者下一條訊息，角色不開口的回合會讓使用者一直等（介面卡）。只有主動模式能發圖片。沒有 outbox。 |
| 個人微信（`weixin_oc`） | 私聊。帶文字的引用。圖片內嵌。帶轉寫的語音。輸入提示。Outbox。 | 沒有群。重新登入後，對方再次寫信之前都聯絡不到。 |
| 其他介面卡 | 按 AstrBot 的交付轉發。提及為 At。 | 不宣告 outbox。 |

## Outbox

有些訊息不回答任何內容：定時開場、被拒絕後的追問，或模型不可用時群裡的致歉。（私聊的致歉在事件自身的響應裡返回。）personagent 把這些訊息排入佇列，這個外掛用與事件相同的簽名從 `POST <personagent_url>/v1/outbox` 拉取，所以 personagent 從不需要訪問 AstrBot。Outbox 預設開啟（`outbox_enabled`）。

- 每次投遞都經該會話自己的 AstrBot session 按順序發出，每條訊息最多傳送一次。
- 投遞只發往外掛本身從同一會話的訊息中取得的 session。這些 session 儲存在 AstrBot 的外掛儲存中，所以重新載入後仍然存在。其他向 personagent 傳送事件的程式都不能把 outbox 指向別的聊天，外掛會拒絕這樣的投遞。
- 外掛在傳送時再次檢查白名單和 `excluded_platforms`，並拒絕已被移除的會話。
- 不能主動發言的平臺（見上表）絕不會收到 outbox 訊息，因為外掛不為其會話宣告 outbox。
- 沒有 outbox 的 personagent 返回 404。外掛每十分鐘再問一次。

personagent 透過 `connector_id` 識別這個 AstrBot，該 id 由外掛生成一次並儲存。連線同一個 personagent 的兩臺 AstrBot 主機需要不同的 id。

## 請求認證

設定了 `connector_token` 時，每個請求都帶四個請求頭：

- `X-Personagent-Token`：token。
- `X-Personagent-Timestamp`：Unix 秒。
- `X-Personagent-Nonce`：新生成的隨機值。
- `X-Personagent-Signature`：`sha256=` 後跟十六進位制 HMAC-SHA256，以 token 為金鑰，內容為 `timestamp + "." + nonce + "." + body`。

請求體是規範 JSON：UTF-8、鍵排序、緊湊分隔符、非 ASCII 字元不轉義。簽名覆蓋這些確切的位元組，所以代理不能改寫請求體。personagent 拒絕錯誤的簽名、重複的 nonce，以及與它自己的時鐘相差超過五分鐘的時間戳。請保持兩邊時鐘同步。

請求體還以 `sent_at` 攜帶介面卡記錄的訊息時間。personagent 單獨按 `CONNECTOR_MAX_EVENT_AGE_S`（預設 24 小時）檢查它，所以用新簽名重發的舊事件仍會被拒絕。介面卡沒有給出有效時間戳的訊息，外掛不轉發，由 AstrBot 照常處理。

## personagent 一側的身份

personagent 給每個轉發的 id 加上平臺字首，寫作 `<platform>:<raw id>`（例如 `telegram:12345`），所以不同平臺的 id 不會衝突。`CONNECTOR_QQ_PLATFORMS` 中列出的平臺保持不帶字首的 id。personagent 的 `ADMIN_IDS`、`ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 使用相同格式的 id。例如 `ADMIN_IDS=telegram:12345` 讓這個賬號成為 Telegram 上的管理員，群和私聊都是。在 `ACCESS_GROUPS` 或 `ACCESS_DM_USERS` 中有條目的平臺，既受 personagent 把關，也受這個外掛的白名單把關。

## 出了問題

外掛在 AstrBot 日誌中的行都以 `personagent:` 開頭。

| 日誌 | 處理方法 |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` 是發往其他主機的明文 HTTP，或沒有 `connector_token` 的 HTTPS。見[personagent 可以執行在哪裡](#personagent-可以執行在哪裡)。 |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` 為空或與 personagent 的 `CONNECTOR_TOKEN` 不一致，兩邊時鐘相差超過五分鐘，或代理改動了請求體。如果 personagent 的日誌顯示 `connector replay guard full`，等它清空。 |
| `agent refused the request (403): stale or invalid sent_at` | 訊息比 personagent 的 `CONNECTOR_MAX_EVENT_AGE_S` 更舊。通常發生在 AstrBot 一次性投遞積壓訊息之後。 |
| `agent refused the request (403): authentication required` 或 `... only local requests accepted` | personagent 沒有 `CONNECTOR_TOKEN`，而請求並非來自本機。在兩邊設定相同的 token。 |
| `agent at capacity (429)` | personagent 已在執行 `CONNECTOR_MAX_INFLIGHT` 個回合，重試後仍拒絕這條訊息，所以由 AstrBot 自帶的模型回答。如果經常發生，調大 `CONNECTOR_MAX_INFLIGHT`。 |
| `agent rejected the body as too large (413)` | 通常是內嵌圖片過大。調大 personagent 的 `SERVER_MAX_BODY_BYTES`。 |
| `agent rejected the event schema (400)` | 事件沒有訊息 id 或傳送者 id（某些介面卡會省略），或這個外掛有 bug。請附上這行日誌報告。 |
| `timed out waiting for the agent` | 見[超時](#超時)。 |
| `dropping event without a valid time the platform sent it` | 介面卡沒有給出時間戳。AstrBot 自行處理這條訊息。 |
| `agent request failed: ...` 或 `agent request failed (<status>)` | 通常是 personagent 沒有執行或 `personagent_url` 填錯。404 表示路徑錯誤：`personagent_url` 是基礎地址，不帶 `/v1/events`。500 表示 personagent 出錯，請看它的日誌。 |
| `outbox off: ...` | Outbox 遵循與事件相同的 `personagent_url` 規則。見第一行。 |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | personagent 的 `CONNECTOR_OUTBOX_ENABLED` 已關閉。 |
| `outbox: outbox pull refused (403)` 或 `outbox pull failed: ...` | 原因與事件相同：token、時鐘，或 personagent 沒有執行。外掛兩次嘗試之間最多退避一分鐘。 |
| `outbox: no running platform '<id>'` | 投遞對應的介面卡在 AstrBot 中已被禁用或改名。外掛向 personagent 報告投遞失敗。 |
| `could not store connector_id` | AstrBot 的外掛儲存失敗。自己設定 `connector_id`，否則每次重啟後 personagent 都會看到一個新的 AstrBot。 |

如果 AstrBot 自帶的模型突然以另一種口吻回覆，說明外掛沒有連上 personagent，或 personagent 沒有接管這個會話。對照上表排查，再執行 `personagent doctor`。如果 personagent 是由本地頁面啟動的，開啟頁面上的 **動態**，看訊息有沒有到達、角色為什麼沒開口。如果是用 `personagent run` 啟動的，看它的終端。

如果 personagent 自己的日誌說聯結器傳送了 `X-Personagent-Token` 但 `CONNECTOR_TOKEN` 為空，說明 personagent 忽略了 token。在它的 `.env` 中設定相同的值。

在 QQ、Telegram、Discord、KOOK、QQ 官方和 Misskey 上，訊息時間是平臺自己的時間，而不是 AstrBot 收到的時間。AstrBot 停機時間超過 personagent 的 `CONNECTOR_MAX_EVENT_AGE_S` 時，personagent 會把 AstrBot 投遞的積壓訊息作為過期訊息拒絕。

## 已知限制：Telegram 提及

AstrBot 的 Telegram 介面卡用數字使用者 id 標識傳送者（`telegram:<numeric id>`），但只用使用者名稱標識訊息中的 `@username` 提及。在此人於 AstrBot 啟動後發過言之後，外掛會把被提及的使用者名稱改寫成其數字 id。在那之前，提及以使用者名稱到達 personagent。

回覆按使用者名稱提及，沒有使用者名稱的人用 `tg://user` 連結。AstrBot 啟動後沒見過的人，外掛不會提及。
