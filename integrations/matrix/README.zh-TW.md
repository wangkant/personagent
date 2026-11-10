# Matrix 聯結器

[English](README.md) · [简体中文](README.zh-CN.md) · 繁體中文 · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


此聯結器將 [personagent](https://github.com/wangkant/personagent) 接入 Matrix 聊天室，並透過 [mautrix 橋接](https://docs.mau.fi/bridges/)接入 WhatsApp、Signal、Messenger、Instagram、Google Messages 等網路。Matrix 和這些橋接程式都是第三方軟體，由你自行執行。personagent 從本機頁面連接的平台不需要它們。

聯結器是一個以 [matrix-nio](https://github.com/matrix-nio/matrix-nio) 為基礎的獨立小型程式，支援端對端加密，不需要 libolm。它以一般 Matrix 使用者的身分登入主伺服器，將每則獲准的聊天室訊息以平台中立的事件格式轉送至 agent 的 `POST /v1/events`（[docs/connectors.md](../../docs/connectors.zh-TW.md)），再將 agent 的回覆傳回聊天室。它也會輪詢 agent 的 outbox，因此定時開場、追問和致歉同樣能送達 Matrix。

## 功能

收到訊息時，對獲准聊天室中的每則訊息：

- 事件使用平台 `matrix` 和原始的 Matrix id，因此 agent 儲存的是 `matrix:@alex:example.org` 和 `matrix:!room:example.org`。
- 聊天室列於機器人的 `m.direct` 中，或除機器人和 `MATRIX_IGNORE_USERS` 中的使用者之外只有一名成員時，視為私訊。私訊依個人區分，群組依聊天室區分。在 `MATRIX_GROUPS` 中以 id 明確列出的聊天室一律視為群組。
- 訊息提及機器人或回覆機器人的訊息時，`addressed` 為 true。提及是指 `m.mentions`，或來自無法傳送 `m.mentions` 之舊版用戶端的 pill 或文字中的機器人使用者 id。
- 回覆會附帶被引用訊息的傳送者和文字。聯結器會從最近事件的快取中取得，或另行拉取上層事件。它會移除舊版用戶端加在前面的回覆後備內容（`> <@alex:example.org> ...`），使 agent 不會將他人的話誤認為傳送者的話。
- 不超過 4 MB 的圖片和貼圖會被下載，在加密聊天室中會先解密，再以位元組形式傳給 agent。語音訊息、影片和檔案則以文字描述。
- 同一聊天室的訊息依傳送順序送達 agent。圖片之後傳送的訊息須等待圖片下載完成。agent 仍可同時處理多個回合。
- 時間戳記為主伺服器的 `origin_server_ts`。
- 聯結器會略過機器人本身的訊息、`m.notice` 訊息（機器人傳送的類型）、編輯、反應、來自 `MATRIX_IGNORE_USERS` 的訊息、啟動時首次同步傳回的積壓訊息，以及早於 `MATRIX_MAX_EVENT_AGE_S` 的內容，例如橋接程式回填至新聊天室的歷史訊息。

傳送時：

- 文字回覆為 `m.text`。agent 要求在群組中提及某人時，回覆會以 pill 開頭，並在 `m.mentions` 中列出此人。其他回覆都帶有空的 `m.mentions`，因此任何用戶端都不會將文字中的名稱轉為通知。
- 圖片回覆會上傳，在加密聊天室中也會加密。
- agent 處理回合期間會顯示輸入中狀態。
- 討論串中的訊息會在該討論串中回覆。
- agent 接管對話後，機器人會將訊息標為已讀（`MATRIX_READ_RECEIPTS_ENABLED`）。經由橋接時，對方網路上會顯示為已讀標記。
- outbox 的傳遞會送往該對話最近所在的聊天室。事件的 `reply_handle` 即為聊天室 id。

## 安裝

你需要一個執行中的 personagent，以及一個供機器人使用的 Matrix 帳號。請建立專用帳號，勿與真人共用。

聯結器是本儲存庫中的腳本，因此需要一份儲存庫副本（Git 複製，或 GitHub 上的 ZIP）及其專用的 Python 環境，因為 `matrix-nio` 並非 personagent 的相依套件。如果複製的儲存庫中已有 personagent 的 `.venv`，請安裝至該環境：

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

如果你以 pip 從 PyPI 安裝了 personagent，或以 uvx 執行，請在副本旁另行建立一個 venv：

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

在 Windows 上，直譯器為 `.venv\Scripts\python.exe` 或 `connector-venv\Scripts\python.exe`。接著複製設定檔：

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

然後以同一個直譯器，在 agent 旁啟動聯結器：

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

邀請機器人進入 `MATRIX_GROUPS` 所列的聊天室，它即會加入。在 Element 中，聊天室 id 位於聊天室設定的進階選項中。

### 登入

以密碼登入是最簡單的起步方式。聯結器會將取得的工作階段（使用者 id、裝置 id 和存取權杖）儲存於 `MATRIX_STORE_DIR/session.json`，下次啟動時沿用，因此重新啟動不會建立新的裝置。刪除此檔案即會重新登入。

如需改用既有的存取權杖，請設定 `MATRIX_ACCESS_TOKEN`。聯結器會向主伺服器查詢此權杖所屬的帳號。請勿使用你本人正在使用之工作階段的權杖，因為登出該工作階段也會使機器人登出。

主伺服器使機器人登出時（`M_UNKNOWN_TOKEN`），聯結器會停止並回報此錯誤。如果使用密碼登入，再次啟動即會重新登入。如果使用 `MATRIX_ACCESS_TOKEN`，請先設定新的權杖。其他同步失敗會延遲重試，延遲時間逐次加倍，最長一分鐘。

### agent 的執行位置

規則由協定決定。`PERSONAGENT_URL` 必須是迴路位址，或是將 `CONNECTOR_TOKEN` 設為 agent 之 `CONNECTOR_TOKEN` 的 HTTPS 位址。否則聯結器會拒絕啟動。即使只有一台主機，在 agent 前方加入代理伺服器或通道之前，也請先在兩端設定權杖。

## 設定項目

[.env.example](.env.example) 列出了所有設定。清單以逗號分隔並支援萬用字元，因此 `@*:example.org` 會比對整個伺服器。空清單不回應任何人。單獨一個 `*` 會比對所有人，並將事件標記為 `prefiltered: false`。此後僅由 agent 本身的 `ACCESS_GROUPS` / `ACCESS_DM_USERS` 決定，在其中沒有項目的平台會被拒絕。

| 設定項目 | 說明 |
|---|---|
| `MATRIX_GROUPS` | 要回應的群組聊天室，填寫聊天室 id。`*` 表示機器人加入的所有聊天室。 |
| `MATRIX_DM_USERS` | 可以私訊機器人的人。`*` 表示所有人。 |
| `MATRIX_INVITE_FROM` | 機器人接受哪些人的邀請。`MATRIX_GROUPS` 中聊天室的邀請，以及 `MATRIX_DM_USERS` 的私訊邀請一律接受。其他邀請則保留不處理。 |
| `MATRIX_IGNORE_USERS` | 永不回應，判斷私訊或群組時也不計為成員。 |
| `MATRIX_E2EE_ENABLED` | 端對端加密。請參閱下文。 |
| `MATRIX_TIMEOUT_S` | 一個回合可花費的最長時間。須大於 agent 的 3 × `LLM_TIMEOUT_S`。 |
| `MATRIX_OUTBOX_ENABLED` | 輪詢 agent 的 outbox。 |

## 橋接：WhatsApp、Signal、Messenger、Instagram 等

mautrix 橋接程式以某個網路帳號的身分登入該網路，將其聊天鏡像至稱為入口（portal）的 Matrix 聊天室。對方的每個人在 Matrix 中都顯示為一個虛擬使用者，例如 `@whatsapp_4912345:example.org`。當登入橋接程式的正是機器人的 Matrix 帳號時，角色就存在於該網路上。WhatsApp 聯絡人傳訊息給角色的號碼，橋接程式將訊息傳至入口聊天室，此聯結器將其轉送，回覆再循原路傳回。

| 網路 | 橋接程式 |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger、Instagram 私訊 | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages（透過 Android 手機的 RCS 和簡訊） | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice、LinkedIn、Twitter/X 私訊、Bluesky 私訊、Google Chat、Zulip、IRC、iMessage | 其他 [mautrix 橋接程式](https://github.com/mautrix) |
| Telegram、Discord、Slack | 有 mautrix 橋接程式，但這些網路提供官方機器人 API。personagent 會自行連線 Telegram 和 Discord，Slack 則透過本機頁面執行的 AstrBot 連線。 |

設定步驟：

1. 執行一個由你管理的主伺服器（Synapse，或其他支援應用程式服務的伺服器），並依[其文件](https://docs.mau.fi/bridges/)安裝橋接程式。在橋接程式的 `permissions` 中為機器人帳號設定 `user` 權限等級。
2. 以機器人身分登入 Element，開啟與橋接機器人的聊天（例如 `@whatsappbot:example.org`），傳送 `login`。連結角色要使用的網路帳號。WhatsApp、Signal 和 Google Messages 須以角色的手機掃描 QR 碼。Messenger 和 Instagram 須提供 Meta 的登入資訊。請參閱[使用橋接程式](https://docs.mau.fi/bridges/general/using-bridges.html)。
3. 讓聯結器加入入口聊天室，並攔下橋接程式本身的訊息：

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   `MATRIX_IGNORE_USERS` 的第二項是角色本身號碼在橋接程式上的虛擬使用者。未設定[雙重傀儡](https://docs.mau.fi/bridges/general/double-puppeting.html)時，在角色手機上輸入的訊息會以該虛擬使用者的身分送達 Matrix，機器人便會回覆自己。`MATRIX_GROUPS=*` 會轉送機器人所在的所有群組入口，personagent 隨後只在 `ACCESS_GROUPS` 以 `matrix:!room:server` 列出的聊天室中回覆。若在此處填寫聊天室 id，則改由聯結器選擇聊天室。

### 傀儡帳號

- 橋接程式是該網路的非官方用戶端，以一般使用者帳號登入（連結裝置或網頁工作階段）。它不使用機器人 API，網路上也沒有任何標示會將此帳號註明為機器人。
- 角色需要專屬的帳號，通常也需要專屬的手機號碼，且手機須保持可連線狀態。手機離線約兩週後，WhatsApp 會解除連結裝置；Google Messages 只在 Android 手機連線時可用。
- 在群組中，角色的帳號看起來與其他成員相同。請告知成員他們是在與機器人對話。
- 反應、編輯、刪除、投票和通話不會轉送給 agent。

### 各網路的條款

連線之前，請先閱讀各網路的條款。

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) 將自動傳送訊息列為不允許的通訊方式，禁止未經授權的非個人使用，並可能停用此類帳號。其認可的自動化途徑為 WhatsApp Business Platform，而橋接程式並未使用此途徑。
- [Signal](https://signal.org/legal/) 同樣將自動傳送訊息列為不允許。
- [Facebook](https://www.facebook.com/terms.php) 和 [Instagram](https://help.instagram.com/581066165581870) 禁止未經 Meta 許可的自動存取，Meta 可能鎖定從其無法辨識之用戶端登入的帳號。
- Google Messages 受 [Google 條款](https://policies.google.com/terms)以及你的電信業者關於簡訊和 RCS 的條款約束，電信業者可能對自動訊息收費或加以限制。

請使用即使遺失也無妨的專用帳號，只在成員知道自己正與機器人對話的聊天中使用，並閱讀 [DISCLAIMER.md](../../docs/DISCLAIMER.zh-TW.md)。

## 端對端加密

`MATRIX_E2EE_ENABLED=false`（預設）時，機器人只讀取未加密的聊天室。在加密聊天室中，它會記錄無法解密，且絕不會在其中傳送明文回覆。

`MATRIX_E2EE_ENABLED=true` 時：

- `MATRIX_STORE_DIR`（預設為腳本旁的 `runtime/`，git 會忽略）儲存裝置金鑰和同步權杖。請保留此目錄。一旦遺失，機器人會成為一個新的裝置，無法讀取在此之前的任何加密內容。
- 裝置在重新啟動前後必須保持不變。密碼登入會透過儲存的工作階段保持同一裝置。使用存取權杖時，請將 `MATRIX_DEVICE_ID` 設為該權杖所屬的裝置。
- 機器人會與聊天室中的每台裝置共用金鑰，無論其是否已驗證。它無法以互動方式驗證自己，因此其他人看到它的裝置為未驗證狀態。它沒有金鑰備份，也沒有交叉簽署。
- 金鑰尚未送達的訊息會被記錄並略過，不會重試。
- mautrix 橋接程式可以加密入口聊天室（[端對橋接加密](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)）。這些金鑰由橋接程式儲存在你的伺服器上，因此保護範圍僅止於此，另一個網路會以其本身的加密方式傳輸訊息。如果你的橋接程式會加密入口聊天室，請開啟 `MATRIX_E2EE_ENABLED`。

## 測試

`tests/test_matrix_connector.py` 模擬了 Matrix 用戶端和 agent，因此不需要 matrix-nio，也不需要網路連線：

```bash
python -m pytest tests/test_matrix_connector.py
```
