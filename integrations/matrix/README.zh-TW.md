# Matrix 聯結器

[English](README.md) · [简体中文](README.zh-CN.md) · 繁體中文 · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


這個聯結器把 [personagent](https://github.com/wangkant/personagent) 放進 Matrix 房間，並透過 [mautrix 橋](https://docs.mau.fi/bridges/)放到 WhatsApp、Signal、Messenger、Instagram、Google Messages 等網路上。Matrix 和這些橋是第三方軟體，由你自己執行。personagent 從本地頁面連線的平臺不需要它們。

聯結器是一個基於 [matrix-nio](https://github.com/matrix-nio/matrix-nio) 的獨立小程序，支援端到端加密，不需要 libolm。它以普通 Matrix 使用者身份登入主伺服器，把每條允許的房間訊息作為平臺中立的事件轉發到 agent 的 `POST /v1/events`（[docs/connectors.md](../../docs/connectors.zh-TW.md)），再把 agent 的回覆發回房間。它也輪詢 agent 的發件箱，所以定時開場、追問和致歉同樣能到達 Matrix。

## 它做什麼

收到訊息時，對允許房間裡的每條訊息：

- 事件使用平臺 `matrix` 和原始 Matrix id，所以 agent 存的是 `matrix:@alex:example.org` 和 `matrix:!room:example.org`。
- 房間在機器人的 `m.direct` 裡列出，或者除機器人和 `MATRIX_IGNORE_USERS` 裡的使用者之外只有一名成員時，算作私聊。私聊按人區分，群按房間區分。在 `MATRIX_GROUPS` 裡按 id 寫明的房間始終是群。
- 訊息提到機器人或回覆機器人的訊息時，`addressed` 為 true。提及指 `m.mentions`，或來自發不了 `m.mentions` 的舊客戶端的 pill 或文字里的機器人使用者 id。
- 回覆會帶上被引用訊息的傳送者和文字。聯結器從最近事件的快取裡取，或去拉取父事件。它會去掉舊客戶端加在前面的回覆回退內容（`> <@alex:example.org> ...`），所以 agent 不會把別人的話當成傳送者的話。
- 不超過 4 MB 的圖片和貼紙會被下載，在加密房間裡解密，再以位元組形式發給 agent。語音訊息、影片和檔案用文字描述。
- 一個房間的訊息按傳送順序到達 agent。圖片之後發的訊息要等圖片下載完。agent 仍可同時處理多輪。
- 時間戳是主伺服器的 `origin_server_ts`。
- 聯結器跳過機器人自己的訊息、`m.notice` 訊息（機器人發的型別）、編輯、反應、來自 `MATRIX_IGNORE_USERS` 的訊息、啟動時首次同步返回的積壓，以及早於 `MATRIX_MAX_EVENT_AGE_S` 的內容，比如橋回填到新房間的歷史。

傳送時：

- 文字回復是 `m.text`。當 agent 要求在群裡提及某人時，回覆以 pill 開頭，並在 `m.mentions` 裡列出此人。其他回覆都帶空的 `m.mentions`，所以任何客戶端都不會把文字里的名字變成提醒。
- 圖片回覆會上傳，在加密房間裡也會加密。
- agent 處理一輪時顯示正在輸入。
- 話題串裡的訊息在該話題串裡回覆。
- agent 接手會話後，機器人把訊息標為已讀（`MATRIX_READ_RECEIPTS_ENABLED`）。透過橋時，這在對方網路上顯示為已讀標記。
- 發件箱投遞發到會話最後所在的房間。事件的 `reply_handle` 就是房間 id。

## 安裝

你需要一個執行中的 personagent 和一個給機器人用的 Matrix 賬號。請建一個專用賬號，不要和真人共用。

聯結器是這個倉庫裡的指令碼，所以需要一份倉庫副本（克隆，或 GitHub 上的 ZIP）和它自己的 Python 環境，因為 `matrix-nio` 不是 personagent 的依賴。如果克隆裡已經有 personagent 的 `.venv`，就裝進這個環境：

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

如果你用 pip 從 PyPI 安裝了 personagent，或者用 uvx 執行，就在副本旁邊另建一個 venv：

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

在 Windows 上，直譯器是 `.venv\Scripts\python.exe` 或 `connector-venv\Scripts\python.exe`。接著複製配置檔案：

```bash
cp integrations/matrix/.env.example integrations/matrix/.env
```

編輯 `integrations/matrix/.env`：

```ini
MATRIX_URL=https://matrix.example.org
MATRIX_USER_ID=@nova:example.org
MATRIX_PASSWORD=...
MATRIX_GROUPS=!AbCdEf:example.org
MATRIX_DM_USERS=@alex:example.org
PERSONAGENT_URL=http://127.0.0.1:8080
```

然後用同一個直譯器，在 agent 旁邊啟動聯結器：

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

邀請機器人進入 `MATRIX_GROUPS` 列出的房間，它就會加入。在 Element 裡，房間 id 在房間設定的高階選項下。

### 登入

密碼登入是最簡單的開始方式。聯結器把得到的會話（使用者 id、裝置 id 和訪問令牌）儲存在 `MATRIX_STORE_DIR/session.json`，下次啟動時複用，所以重啟不會建立新裝置。刪掉這個檔案就會重新登入。

要改用已有的訪問令牌，設定 `MATRIX_ACCESS_TOKEN`。聯結器會詢問主伺服器這個令牌屬於哪個賬號。不要用你自己在用的會話的令牌，因為退出那個會話也會讓機器人退出。

主伺服器讓機器人退出登入時（`M_UNKNOWN_TOKEN`），聯結器會停止並報出這個錯誤。如果是密碼登入，再次啟動就會重新登入。如果用 `MATRIX_ACCESS_TOKEN`，先設定新令牌。其他同步失敗會延遲重試，延遲逐次翻倍，最長一分鐘。

### agent 可以執行在哪裡

規則由協議決定。`PERSONAGENT_URL` 必須是迴環地址，或是 `CONNECTOR_TOKEN` 設為 agent 的 `CONNECTOR_TOKEN` 的 HTTPS。否則聯結器拒絕啟動。即使只有一臺主機，也要在 agent 前面加代理或隧道之前，先在兩邊設好令牌。

## 配置項

[.env.example](.env.example) 列出了所有配置。列表用逗號分隔並支援萬用字元，所以 `@*:example.org` 匹配整個伺服器。空列表不回應任何人。單獨一個 `*` 匹配所有人，並把事件標記為 `prefiltered: false`。之後只由 agent 自己的 `ACCESS_GROUPS` / `ACCESS_DM_USERS` 決定，那裡沒有條目的平臺會被拒絕。

| 配置項 | 含義 |
|---|---|
| `MATRIX_GROUPS` | 要回應的群房間，寫房間 id。`*` 表示機器人加入的所有房間。 |
| `MATRIX_DM_USERS` | 可以和機器人私聊的人。`*` 表示所有人。 |
| `MATRIX_INVITE_FROM` | 機器人接受誰的邀請。`MATRIX_GROUPS` 裡房間的邀請和 `MATRIX_DM_USERS` 的私聊邀請總是接受。其他邀請留著不處理。 |
| `MATRIX_IGNORE_USERS` | 永不回應，判斷私聊還是群時也不算成員。 |
| `MATRIX_E2EE_ENABLED` | 端到端加密。見下文。 |
| `MATRIX_TIMEOUT_S` | 一輪最長可以花多久。要大於 agent 的 3 × `LLM_TIMEOUT_S`。 |
| `MATRIX_OUTBOX_ENABLED` | 輪詢 agent 的發件箱。 |

## 橋：WhatsApp、Signal、Messenger、Instagram 等

mautrix 橋以某網路賬號的身份登入該網路，把它的聊天映象到稱為門戶的 Matrix 房間。對面的每個人在 Matrix 裡都顯示為一個幽靈使用者，比如 `@whatsapp_4912345:example.org`。當登入橋的正是機器人的 Matrix 賬號時，角色就生活在那個網路上。WhatsApp 聯絡人給角色的號碼發訊息，橋把訊息發到門戶房間，這個聯結器轉發它，回覆再原路返回。

| 網路 | 橋 |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger、Instagram 私信 | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages（透過 Android 手機的 RCS 和簡訊） | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice、LinkedIn、Twitter/X 私信、Bluesky 私信、Google Chat、Zulip、IRC、iMessage | 其他 [mautrix 橋](https://github.com/mautrix) |
| Telegram、Discord、Slack | 有 mautrix 橋，但這些網路有官方機器人 API。personagent 自己連線 Telegram 和 Discord，Slack 則透過本地頁面執行的 AstrBot 連線。 |

配置步驟：

1. 執行一個你能控制的主伺服器（Synapse，或其他支援應用服務的伺服器），按[它的文件](https://docs.mau.fi/bridges/)安裝橋。在橋的 `permissions` 裡給機器人賬號 `user` 許可權級別。
2. 以機器人身份登入 Element，開啟與橋機器人的聊天（比如 `@whatsappbot:example.org`），傳送 `login`。關聯角色要用的網路賬號。WhatsApp、Signal 和 Google Messages 用角色的手機掃二維碼。Messenger 和 Instagram 提供 Meta 登入資訊。見[使用橋](https://docs.mau.fi/bridges/general/using-bridges.html)。
3. 讓聯結器加入門戶，並擋掉橋自己的訊息：

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   `MATRIX_IGNORE_USERS` 的第二項是角色自己號碼在橋上的幽靈使用者。沒有[雙重傀儡](https://docs.mau.fi/bridges/general/double-puppeting.html)時，在角色手機上打的訊息會以那個幽靈使用者的身份到達 Matrix，機器人就會回覆自己。`MATRIX_GROUPS=*` 轉發機器人所在的所有群門戶，personagent 隨後只在 `ACCESS_GROUPS` 以 `matrix:!room:server` 列出的房間回覆。在這裡寫房間 id，就能改在聯結器裡選房間。

### 傀儡賬號

- 橋是該網路的非官方客戶端，以普通使用者賬號登入（關聯裝置或網頁會話）。它不用機器人 API，網路上也沒有任何東西把這個賬號標記為機器人。
- 角色需要自己的賬號，通常有自己的手機號，手機也要保持可連線。手機離線約兩週後 WhatsApp 會斷開關聯裝置，Google Messages 只在 Android 手機線上時可用。
- 在群聊裡，角色的賬號看起來和其他成員一樣。請告訴大家他們在和機器人說話。
- 反應、編輯、刪除、投票和通話不會轉發給 agent。

### 各網路的條款

連線前請先讀每個網路的條款。

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) 把自動發訊息列為不允許的通訊，禁止未經授權的非個人使用，並可能封禁這樣做的賬號。它認可的自動化途徑是 WhatsApp Business Platform，橋並不使用它。
- [Signal](https://signal.org/legal/) 同樣把自動發訊息列為不允許。
- [Facebook](https://www.facebook.com/terms.php) 和 [Instagram](https://help.instagram.com/581066165581870) 禁止未經 Meta 許可的自動訪問，Meta 可能鎖定從它不認識的客戶端登入的賬號。
- Google Messages 受 [Google 條款](https://policies.google.com/terms)以及你的移動運營商關於簡訊和 RCS 的條款約束，運營商可能對自動訊息收費或加以限制。

請使用丟了也無所謂的專用賬號，只在大家知道自己在和機器人說話的會話裡使用，並閱讀 [DISCLAIMER.md](../../docs/DISCLAIMER.zh-TW.md)。

## 端到端加密

`MATRIX_E2EE_ENABLED=false`（預設）時，機器人只讀未加密房間。在加密房間裡，它會記錄無法解密，也絕不會在那裡發明文回覆。

`MATRIX_E2EE_ENABLED=true` 時：

- `MATRIX_STORE_DIR`（預設是指令碼旁邊的 `runtime/`，git 會忽略）儲存裝置金鑰和同步令牌。請保留這個目錄。如果丟了，機器人會變成一個新裝置，讀不了那之前的任何加密內容。
- 裝置在重啟前後必須保持不變。密碼登入透過儲存的會話保持裝置。用訪問令牌時，把 `MATRIX_DEVICE_ID` 設為該令牌的裝置。
- 機器人和房間裡的每臺裝置共享金鑰，不管是否已驗證。它無法互動式地驗證自己，所以大家看到它的裝置是未驗證的。它沒有金鑰備份，也沒有交叉簽名。
- 金鑰還沒到的訊息會記錄並跳過，不會重試。
- mautrix 橋可以加密門戶（[端到橋加密](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)）。這些金鑰由橋儲存在你的伺服器上，所以保護到此為止，另一網路用它自己的加密傳輸訊息。如果你的橋加密門戶，開啟 `MATRIX_E2EE_ENABLED`。

## 測試

`tests/test_matrix_connector.py` 模擬了 Matrix 客戶端和 agent，所以不需要 matrix-nio 和網路：

```bash
python -m pytest tests/test_matrix_connector.py
```
