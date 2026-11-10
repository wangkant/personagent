# 部署 personagent：QQ 掃碼直連，以及排查

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · 繁體中文 · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md) · 簡體中文 · [繁體中文](deploy.zh-TW.md) · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

本文按順序介紹如何把角色接入 QQ 群：安裝、填寫 key、用手機 QQ 掃碼。QQ 官方機器人由 personagent 直接連線，不需要 AstrBot，也不需要 NapCat 和 QQ 小號。微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 同樣由它直接連線。如果想用個人 QQ 小號，請看後面的[第三方路線：AstrBot + NapCat](#第三方路線astrbot--napcat)。

```text
QQ 群  ⇄  personagent（直連程序 + 角色服務）  ⇄  AI 模型
```

每一步都寫明瞭「你應該看到」的結果。如果對不上，先不要繼續，直接檢視[機器人不說話](#機器人不說話)。

## 開始之前

- 一臺能長期開機的電腦（Windows、macOS 或 Linux），裝有 Python 3.10 到 3.14。personagent 關閉後，機器人也隨之停止。
- 一個 AI 服務的 API key。DeepSeek、矽基流動、阿里雲百鍊、智譜、Kimi、火山方舟等均可，在各自的控制檯裡建立。
- 一部登入了你自己 QQ 的手機，用來掃碼。

## 第一步：安裝並開啟

```sh
python -m pip install personagent
personagent
```

如果裝了 [uv](https://docs.astral.sh/uv/)，可以用 `uvx personagent` 免安裝執行。在 Windows 上也可以下載原始碼 ZIP，解壓後雙擊 `start.bat`。從 Git 倉庫執行的方法見[簡明入門](start.zh-TW.md)。

你應該看到一個本地頁面：在 Windows 上顯示於獨立的視窗中，在 macOS 和 Linux 上則在瀏覽器中開啟。頁面側欄有六個檢視：「開始聊天」「動態」「連接平台」「角色與設定」「演練」「應用程式」。再次執行 `personagent` 會複用已經開啟的頁面。

> 如果想把資料放在別的盤，執行 `personagent --home D:\personagent`，之後每條命令都帶上同樣的 `--home`。不指定時，資料存放在使用者目錄下的 `personagent` 資料夾。

## 第二步：填 key，選角色

在「角色與設定」裡選擇模型服務（共 10 個預設，另有「其他」，可填寫任何相容 OpenAI 的地址），貼上 API key，再選定名字和性格。儲存時，程式會傳送一個很小的請求來驗證 key，驗證不透過則不儲存任何內容。

你應該能在「開始聊天」裡和角色聊幾句，它會以你選的性格回覆。

「人設」框裡是 `persona.txt` 的內容，也就是角色當前使用的人設。修改後點選儲存，角色服務會重啟，已經學到的東西會保留。

「角色與設定」裡的「更多功能」可以開啟聯網搜尋、看圖和主動發言。

## 第三步：掃碼連線 QQ

1. 開啟「連線平臺」，選擇 **QQ**。
2. 頁面會顯示二維碼。用手機 QQ 掃碼並確認，可以新建一個機器人，也可以選擇一個已有的機器人，金鑰由 personagent 自動取回。如果無法掃碼，也可以在 [QQ 開放平臺](https://q.qq.com/qqbot/openclaw/login.html)建立機器人，再把 AppID 和 AppSecret 貼上進來。
3. 程式確認 QQ 接受了這個機器人之後才會儲存。如果 QQ 拒絕，頁面會給出提示，不儲存任何內容。

你應該看到 QQ 出現在頁面上方，狀態為已連線。

**把機器人拉進群。** 在手機 QQ 裡找到這個機器人，私聊它或把它加進群。機器人能進哪些群由 QQ 決定：透過認證之前，QQ 只允許它加入你擔任群主的群。它在群裡能收到哪些訊息，也在 QQ 裡設定。認證等賬號相關事項見 [QQ 機器人官方指南](https://bot.q.qq.com/wiki/bot_new_product-intro/)。

**測試。** 在群裡發一句帶機器人名字的話（比如 `小夏，你好`），或者 @ 它。幾秒到十幾秒內應該能看到回覆。

## 其他平臺

所有平臺都在「連線平臺」裡新增。憑據會先交給平臺驗證，透過後才儲存。

- **personagent 直接連線**：QQ、個人微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat。個人微信用手機微信掃碼登入（使用騰訊的 iLink 機器人介面），只支援私聊，因為微信不會把群訊息交給這類機器人。Telegram 需要貼上 @BotFather 提供的 token；Discord 需要貼上機器人 token，並開啟 Message Content Intent。其餘六個平台需要填寫的內容與使用限制，見[使用手冊](guide.zh-TW.md#personagent-直接連線的平台)。
- **經託管的 AstrBot 連線**：其餘平臺。第一次連線這類平臺時，personagent 會下載 AstrBot 和獨立的 Python 3.12，並在後臺執行。它沒有網頁後臺，也不需要再登入一個賬號。只需貼上一兩項就能連線的有：KOOK、飛書（長連線）、釘釘（Stream 模式）、Slack（Socket Mode，頁面上的連結會預填好應用）、企業微信智慧機器人（長連線）、Mattermost、Misskey。「高階」分組裡的平臺需要公網地址或本機的其他軟體：企業微信應用、微信公眾號、QQ（Webhook）、OneBot v11（NapCat）、Satori。暫不提供 LINE。

連線好的平臺預設回覆所有群聊和私聊。如果只想放行一部分，在 `.env` 裡寫 `ACCESS_GROUPS` 或 `ACCESS_DM_USERS`（格式為 `平臺:ID`，見[下文](#經你已經在執行的-astrbot)）。

## 日常使用

- 每次開機後執行 `personagent`。頁面開啟期間，角色服務、直連程序和託管的 AstrBot 都在執行，已經連好的平臺會自動恢復連線。如果不想開啟瀏覽器，可以用 `personagent up`，效果相同。
- 由它啟動的程序會隨它一起結束，無論它以何種方式退出。上次異常退出遺留的程序，會在下次啟動時先被停止。
- 所有資料都在一個主目錄裡：`.env`（設定）、`persona.txt`（人設）、`runtime/`（學到的東西和日誌）、`platforms/`（託管的 AstrBot，以及直連平臺的憑據 `direct.json`）。key 只儲存在這臺電腦上，對話內容會傳送給你選的模型服務。
- 如果要直接修改 `.env`，可以用記事本編輯，儲存為 UTF-8（不帶 BOM），然後重啟 `personagent`。
- 有新版本時，「開始聊天」頁面和終端會給出對應你安裝方式的更新命令。頁面和 `personagent up` 每天最多向 pypi.org 查詢一次，請求裡只帶版本號；在 `.env` 裡設定 `UPDATE_CHECK_ENABLED=false` 可以關閉這項檢查。
- 手動更新：`python -m pip install -U personagent`（用 uv 安裝的，執行 `uv tool upgrade personagent`）。從 0.x 升級上來時，如果啟動提示存在舊設定名，執行 `personagent doctor --fix`，它會把 `.env` 裡的舊名稱改成新名稱，並把原檔案另存為 `.env.bak`。
- 命令列：`personagent init --terminal`（終端設定嚮導）、`chat`（在終端裡聊天）、`demo`（無需 key 的演示）、`run`（只啟動角色服務）、`doctor`（檢查設定和各項服務）、`learned`（檢視和撤回學到的東西）、`eval`（評測）。

## 動態

本地頁面側邊欄裡的「動態」列出角色所在的每個群聊和私聊。選中一個聊天，可以看到等你確認的改動、它學到的東西、記住的事，以及最近的訊息：它每次開口的原因，和沒開口時的理由。詳見[使用指南](guide.zh-TW.md#動態)。

「動態」的資料來自本地頁面所啟動的角色服務，取自它在 `/api/dashboard/` 下的 JSON 介面。只用 `personagent run` 啟動服務時，請看服務日誌，並用 `personagent learned` 檢視學到的東西。每次呼叫都要帶 `X-Personagent-Dashboard-Token` 請求頭，值是執行目錄（預設 `<主目錄>/runtime/`，可用 `AGENT_RUNTIME_DIR` 修改）裡 `dashboard.token` 檔案的內容。這個檔案在服務啟動時生成，只有本人能讀。修改操作還要帶 `X-Personagent-Dashboard: 1` 和 `Content-Type: application/json`，請求如果帶了 `Origin`，必須是服務自己的地址。跨站的瀏覽器請求一律拒絕，`CONNECTOR_TOKEN` 也打不開這個介面。返回內容裡的金鑰都會被遮住。指令碼也可以按同樣的方式呼叫。設定 `DASHBOARD_ENABLED=false` 會關閉這個介面，「動態」隨之不顯示內容，`personagent doctor` 會列印 `activity: off (...)`。

角色服務本身不提供網頁，訪問 `http://127.0.0.1:8080/` 只會看到一段說明，指向本地頁面和 `personagent learned`，以前的 `?token=` 連結現在也只開啟這段說明。本地頁面只監聽 127.0.0.1。在沒有本地頁面的伺服器上，用 `personagent learned` 檢視和推翻它學到的東西。

## 它怎麼學習

機器人不會因為一句話就改變。一項改變要同時滿足兩個條件：同一個聊天裡出現兩次一致的反應，並且其中至少一次足夠「強」，即**被回覆的那個人用自己的話糾正了它，或者接受了它的第二次回答**。一聲「哈哈」、旁觀者的糾正（即使機器人回頭問了他）、陌生人的指令、有人直接換了話題，都不算數。因此在預設設定下，一個人只能教它如何回答自己，而且只在他自己所在的聊天裡生效。旁觀者的抱怨也撤不掉它學到的東西，只有原回覆的物件或管理員才能撤回。

學到的所有內容都記錄在只追加的賬本里，隨時可以撤銷：

- 在「動態」中，「待你確認」下的每條改動都有「保留」和「捨棄」兩個按鈕。「保留」會讓它生效，如果同一條回覆已經有生效中的改寫，就替換掉那條。「學習紀錄」下每一條都有「復原」按鈕。下方的「角色學到的內容」列出全部學到的內容，角色未執行時也可以在此處理。
- 也可以使用命令：`personagent learned list`、`personagent learned show <編號>`、`personagent learned rollback <編號>`。

如果希望它更保守，在 `.env` 里加上 `PROMOTE_MIN_SPEAKERS=2`，這樣需要兩個不同的人都認可才會改變。

在群裡對它說 `小夏 記住 …`、`小夏 忘掉 …`、`小夏 你都記得什麼`，可以直接管理它的記憶；`小夏 學到了什麼` 會列出它學到的內容。命令必須放在訊息開頭。以「嗎」「呢」「沒」等結尾的問句（比如 `小夏 記住了嗎`）只當作聊天處理；`小夏 忘掉這個` 的意思是「算了」，不會刪除任何內容。每條筆記都會記錄是誰記下的、內容涉及誰；不針對具體某人的筆記全群可見，列出時標註「來自某某」。

修改人設不會清空它學到的東西。

## 機器人不說話

請按順序排查，越靠前的原因越常見。角色服務由本地頁面啟動時，先看「動態」：聊天是否出現、有沒有收到訊息、它為什麼沒開口，都能在這裡看到。在伺服器上，看服務日誌，學到的東西用 `personagent learned` 檢視。再看主目錄下 `runtime/desktop/` 裡的日誌：`agent.log`（角色服務）、`direct.log`（personagent 直接連線的平台）、`astrbot.log`（其他平臺）。

1. **訊息沒有送達。** 在「連線平臺」裡確認該平臺顯示為已連線。QQ 機器人必須已經在群裡，群裡能收到哪些訊息由 QQ 的設定決定；個人微信只支援私聊。使用第三方 AstrBot 的，見[第三方路線排查](#第三方路線排查)。
2. **角色服務沒有開啟，或者缺少 key。** 在「角色與設定」裡重新填寫 key 並儲存。如果 `.env` 裡寫了 `AGENT_ENABLED=false`，改為 `true` 後重啟。
3. **沒有叫到它。** 在群裡，它只回應帶它名字（`PERSONA_NAME`）或 @ 它的訊息。其他情況下，它要等群裡聊滿 `CHAT_TRIGGER_COUNT` 條（預設 30 條）才會考慮插話，考慮之後也可能選擇不說。凌晨 2 點到 7 點它更少插話。`AGENT_LANG` 為 `zh` 或 `zh-TW` 時按北京時間計算，如需換時區，在 `.env` 裡設定 `PERSONA_TZ_OFFSET_HOURS`。測試時先用名字叫它。
4. **被 personagent 自己的白名單攔下。** `.env` 裡的 `ACCESS_GROUPS`、`ACCESS_DM_USERS` 一旦寫了某個平臺的條目，這個平臺就只放行列出的條目。被攔下的會話會在 `agent.log` 裡記錄一行。
5. **模型呼叫失敗。** key 無效或餘額用完時，`agent.log` 裡會有一行 ERROR，寫明是哪個服務、該修改哪項設定。執行 `personagent doctor` 會向每個模型傳送一個很小的請求，直接顯示狀態碼。
6. **設定名寫錯。** 寫錯的設定名不會報錯，程式只是繼續使用預設值。`personagent doctor` 和啟動日誌會列出不認識的設定名。
7. **`.env` 帶有 BOM。** 用記事本另存時選錯編碼，會導致第一行設定失效。`personagent doctor` 會報告這個問題，改用「UTF-8」（不帶 BOM）重新儲存即可。
8. **能回覆，但忘了學過的東西。** 修改 `PERSONA_NAME` 或 `PERSONA_VERSION` 會讓它被當作新角色；在「人設」框裡修改人設則不會。

如果仍然無法解決，請到 [Issues](https://github.com/wangkant/personagent/issues) 提問，並附上 `personagent doctor` 的輸出（先遮蓋 key 和賬號）。

## 第三方路線：AstrBot + NapCat

AstrBot、NapCat（OneBot）、Koishi（經 Satori 聯結器）和 Matrix（經 mautrix 橋接 WhatsApp、Signal 等）是 personagent 可以配合使用的第三方橋接，連接 personagent 直接連線的平台都用不到它們。只有在想用**個人 QQ 小號**而不是官方機器人時，才需要 NapCat。

注意：NapCat 不是騰訊官方客戶端，小號有被限制甚至封禁的風險。不要使用你自己的主號，詳見 [DISCLAIMER.zh-CN.md](DISCLAIMER.zh-TW.md)。

### 用託管的 AstrBot（推薦）

1. 按 [NapCat 文件](https://napneko.github.io/)安裝 NapCat，用手機上的**小號**掃碼登入。
2. 在 personagent 頁面的「連線平臺」裡選擇「高階 → OneBot v11（NapCat）」，埠預設為 `6199`。
3. 在 NapCat 的網頁裡依次點選「網路配置」→「新建」→「WebSockets 客戶端」，勾選「啟用」，URL 填 `ws://127.0.0.1:6199/ws`，然後儲存。

託管的 AstrBot 會自動安裝 personagent 外掛，並寫好 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。走這條路線時，NapCat 也需要一直執行。

### 用你自己的 AstrBot

外掛 `astrbot_plugin_personagent` 是 AstrBot 把訊息交給 personagent 的途徑。有兩種安裝方式：

- 執行 `personagent connect astrbot`，按提示選擇 QQ（透過 NapCat），填寫小號的 QQ 號、群號和你自己的 QQ 號。它會把外掛複製到 AstrBot 的 `plugins` 資料夾，在兩邊寫入同一個 `CONNECTOR_TOKEN`，並寫好白名單和 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。如果不確定 AstrBot 的 `data` 資料夾在哪裡，可以搜尋 `cmd_config.json`。
- 也可以從 personagent 的[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下載 `astrbot_plugin_personagent.zip`，在 AstrBot 外掛頁的「從檔案安裝」中上傳，再把外掛設定裡的 `connector_token` 填為 personagent `.env` 裡的 `CONNECTOR_TOKEN`。AstrBot 不在這臺電腦上時使用這種方式，此時外掛的 `personagent_url` 還需要填寫 personagent 的 HTTPS 地址（見下文 Docker 一段）。

升級 personagent 後，重新執行 `personagent connect astrbot` 或上傳新的 zip。AstrBot 4.29 及以後的版本會直接替換已安裝的外掛；更早的版本需要先解除安裝外掛，解除安裝時不要勾選刪除外掛配置檔案。

安裝完成後，重啟 AstrBot（或在外掛頁過載外掛），然後用 `personagent run` 啟動角色服務並保持執行。在 AstrBot 裡新增 OneBot v11 機器人（反向 WebSocket 埠 `6199`），再按上一節第 3 步讓 NapCat 指向它。AstrBot 的介面以[其官方文件](https://docs.astrbot.app)為準。

如果 AstrBot 執行在 Docker 裡，`127.0.0.1` 指的是容器本身，而外掛會拒絕發往其他地址的明文 `http://`。可以二選一：給 AstrBot（以及同一個 compose 裡的 NapCat）使用主機網路（`network_mode: host`，`docker run` 時用 `--network host`；Docker Desktop 需要 4.34 及以上版本，並開啟 `Enable host networking`）；或者為 personagent 提供一個 HTTPS 地址，再執行 `personagent connect astrbot <data 資料夾> --url https://你的地址`。

### 第三方路線排查

1. **AstrBot 沒有把訊息交出來。** 在外掛設定裡確認 `groups` 包含這個群號；私聊需要在 `dm_users` 裡填寫傳送者的 QQ 號。再確認 `excluded_platforms` 裡沒有 `aiocqhttp`。
2. **回覆來自 AstrBot 自帶的模型（語氣突然變了）。** 檢視 AstrBot 的日誌：
   - `refusing unsafe personagent_url`：外掛裡的 `personagent_url` 不正確。在同一臺電腦上應填 `http://127.0.0.1:8080`。
   - `agent refused the request (403)`：兩邊的 `CONNECTOR_TOKEN` 不一致，或者兩臺電腦的時鐘相差超過五分鐘。重新執行 `personagent connect astrbot` 會把兩邊改成同一個令牌。
   - `timed out waiting for the agent`：模型響應太慢。外掛的 `timeout_s` 預設為 420 秒，足以覆蓋 personagent 預設設定下最長的 360 秒；如果調大了 `LLM_TIMEOUT_S`，也要相應調大 `timeout_s`。
   - `agent request failed`：personagent 沒有執行，或者地址、埠填寫有誤。
3. **QQ 私聊被攔下。** 經 NapCat 進來的 QQ 私聊，必須來自管理員（`ADMIN_IDS`），或者在 `ACCESS_DM_USERS` 之中。
4. **`QQ_BOT_ID` 未填寫或填寫錯誤。** 這裡應填小號的 QQ 號。
5. **忘了學過的東西。** 經 NapCat 的 QQ 會話必須配置 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`，缺少這項時，所有 QQ 會話都會被當作新會話。

**NapCat 的 HTTP 服務**是可選的。開啟後，personagent 能補回它離線期間漏掉的 @ 訊息。做法是在 NapCat 裡開啟 HTTP 服務，並在 `.env` 裡寫上 `QQ_ONEBOT_URL=http://127.0.0.1:3000`（埠以 NapCat 中的設定為準）和 `QQ_BOT_ID`（小號的 QQ 號）。

**舊的直連方式。** NapCat 直接把事件發到 personagent 的 `/v1/onebot`，這種方式已不再推薦，但在 1.x 中仍然可用。它要求在 `.env` 裡寫上 `QQ_ONEBOT_URL`，否則機器人只收不回，`personagent doctor` 會對此給出提醒。改用 AstrBot 之後，要關閉 NapCat 裡指向 `/v1/onebot` 的 HTTP 客戶端，否則每條訊息都會收到兩遍。已經學到的記憶會保留。

## 部署參考

前面的教程帶你跑起來。這一部分是長期執行要知道的全部內容：設定、程序、介面、錯誤碼和費用。

### 能執行的最短配置

本地頁面（`personagent`，或用 `personagent init --terminal` 走終端嚮導）會發一個很小的請求驗證 key，然後把 `.env` 寫到主目錄。聊天需要 key，`.env.example` 預設使用 OpenRouter 的免費模型：

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

`.env` 裡只寫 key 時，地址和模型是 `https://api.deepseek.com` 和 `deepseek-flash`。它們可以指向任何相容 OpenAI 的介面，託管的或本地的（Ollama、llama.cpp）都行。API 地址按服務商文件貼上，根地址或 `.../v1`、`.../api/paas/v4` 這樣帶版本的地址都可以。在你寫好 `persona.txt` 之前，用的是隨包附帶的 `data/persona.example.<lang>.txt`。在設定 `PERSONA_NAME` 之前（設定流程會寫好），角色叫 "bot"。

頁面還會寫入 `PERSONA_NAME`、`AGENT_LANG` 和一個 `CONNECTOR_TOKEN`。從頁面連線的平臺不需要在 `.env` 裡再寫任何內容。它們的憑據放在 `<home>/platforms/`：`direct.json` 儲存 personagent 直接連線的平臺，其餘平臺由託管的 AstrBot 儲存在它自己的配置裡。可選的補充：

```
ADMIN_IDS=telegram:12345             # 管理員的賬號，<platform>:<id>
# 只有經 NapCat（OneBot）接 QQ 時才需要
QQ_BOT_ID=...                        # 機器人賬號的號碼
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

key 只留在這臺電腦上，對話內容會發給你選的模型服務。`.env.example` 裡的其他設定都有可用的預設值。`SERVER_HOST` 和 `SERVER_PORT` 是 `127.0.0.1:8080`，`QQ_ONEBOT_URL` 為空（沒有 NapCat HTTP 服務），`ACCESS_GROUPS` 為空表示所有群交給聯結器決定。

### 執行

`personagent` 開啟本地頁面。頁面開啟期間，它執行角色服務、直連平臺的程序，以及已安裝的託管 AstrBot。再次執行 `personagent` 會複用已經開啟的頁面。`personagent up` 啟動同樣的程序，但不開啟瀏覽器。

兩種方式下，這些程序都隨它結束，無論它以何種方式退出。上次崩潰遺留的程序會在下次啟動時被停止。每個程序把日誌寫到 `<home>/runtime/desktop/`（`agent.log`、`direct.log`、`astrbot.log`）。

本地頁面和 `personagent up` 每天最多向 pypi.org 查詢一次是否有新版本。有新版本時，「開始聊天」頁面和終端會顯示更新這份安裝的命令。請求只帶版本號，`UPDATE_CHECK_ENABLED=false` 可以關閉這項檢查。

`personagent run` 只啟動角色服務，見[只啟動服務](guide.zh-TW.md#只啟動服務)。你自己的聯結器（你執行的 AstrBot、Satori、Matrix）連線它時用這條命令。`personagent doctor` 檢查設定，並探測每個上游服務。

**1.0 改了設定名。** 只要還設定著 1.0 廢棄的設定名，啟動就會以退出碼 2 拒絕，並逐個列出 `OLD -> NEW`。`personagent doctor --fix` 會改掉 `<home>/.env` 裡的名字。它保留值和註釋，把舊檔案存為 `.env.bak`，如果新名字已經設定，就把舊的那行註釋掉。寫在環境變數而不是 `.env` 裡的廢棄名字，要到設定它的地方去改。只要還有殘留，`personagent doctor` 就以 1 退出，`--json` 把它們列在 `retired_settings` 下。`HOST`、`PORT` 和 `LOG_FILE` 只有寫在 `.env` 裡才算。

#### 動態介面

[動態](guide.zh-TW.md#動態)是本地頁面裡的一個檢視。它不需要額外安裝，不從網際網路載入任何內容，也從不顯示 key 或 token。它讀取本地頁面所啟動的角色服務的 JSON 介面。只用 `personagent run` 時，請讀服務日誌，並用 `personagent learned`。`DASHBOARD_ENABLED=false` 會關閉這個介面，此時檢視會說明情況，`personagent doctor` 列印 `activity: off (...)`。

介面位於角色服務的 `/api/dashboard/` 下：

- `GET conversations` 和 `GET conversation?id=<chat id>` 讀取服務知道的聊天，以及某個聊天的詳情。
- `POST candidates/<id>/promote`、`replace`、`reject` 和 `rollback` 修改它學到的內容。每次修改都和 `personagent learned` 進同一個賬本，操作者記為 `dashboard`。
- `POST memory/forget` 帶上請求體 `{"conv": "<chat id>", "note": "<note id>"}`，刪除一條記憶筆記，`conv` 和 id 取自 `GET conversation` 返回的 `memories` 裡的那一條。不帶 `note` 時刪除這個聊天的核心筆記。

每次呼叫都要帶 `X-Personagent-Dashboard-Token` 請求頭，值是執行目錄（預設 `<home>/runtime/`，除非 `AGENT_RUNTIME_DIR` 改了它）裡 `dashboard.token` 檔案中的 token。這個檔案只有本人能讀，服務啟動時生成。不帶這個請求頭的呼叫得到 401（`dashboard_token`），token 錯誤得到 403（`wrong_token`）。`CONNECTOR_TOKEN` 和 `X-Personagent-Token` 打不開它，它們只用於聯結器和 `/health/details`。

- 寫操作還要帶 `X-Personagent-Dashboard: 1` 和 `Content-Type: application/json`。請求帶 `Origin` 時，必須是服務自己的地址。
- 跨站的瀏覽器請求一律拒絕。
- 響應裡的所有憑據都替換成 `***`。啟動檢查中的 URL 還會遮住使用者名稱、密碼和查詢串。
- 同一臺電腦上的指令碼可以用本地頁面的方式呼叫這個介面。

服務本身不提供頁面。`GET /` 返回一段簡短說明，指向本地頁面和 `personagent learned`，以前的 `?token=` 連結現在也開啟這段說明。本地頁面只繫結 127.0.0.1。在沒有本地頁面的伺服器上，用 `personagent learned` 檢視和推翻學到的內容。

### 主機必須提供什麼

1. **可寫的主目錄。** 啟動時會在 `<home>/.personagent.instance.lock` 上加鎖，它在 `runtime/` 之外。主目錄只讀時無法啟動。
2. **每個主目錄一個程序。** 同一主目錄上的第二個 `personagent run` 會退出，並用一句話說明。
3. **空閒的埠。** 埠被佔用或被禁止時也會退出，並用一句話說明。用 `--port` 或 `SERVER_PORT` 換一個。

`AGENT_RUNTIME_DIR` 必須解析到主目錄之內，否則啟動失敗。相對路徑的 `PERSONA_FILE` 或 `PERSONA_CARD_FILE` 也按主目錄解析，所以放在別處的人設要寫絕對路徑。

### 連線平臺

在本地頁面的「連線平臺」裡新增平臺。personagent 在儲存之前先向平臺驗證憑據。平臺拒絕時，頁面顯示拒絕原因，不保留任何內容。

**由 personagent 直接連線。** QQ、個人微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 執行於同一個「直連」程序中，不需要 AstrBot 和 NapCat。某個平台無法載入時會被略過，其餘平台仍會正常啟動。下表列出前四個平台；其餘六個平台需要填寫的內容與使用限制，見使用手冊中的[personagent 直接連線的平台](guide.zh-TW.md#personagent-直接連線的平台)。

| 平臺 | 你要做的 | 限制 |
|---|---|---|
| QQ（官方機器人） | 用手機 QQ 掃碼，新建機器人或選擇你建好的機器人。備用辦法是貼上 AppID 和 AppSecret。 | 透過認證之前，QQ 只允許它加入你擔任群主的群。群訊息許可權在 QQ 裡設定。 |
| 個人微信 | 用微信掃碼（騰訊的 iLink 機器人介面）。 | 只有一對一聊天。微信不把群訊息交給這類機器人。 |
| Telegram | 貼上 @BotFather 提供的 token。 | |
| Discord | 貼上機器人 token，並開啟 Message Content Intent。 | |

**經託管的 AstrBot。** 其他平臺都經由 personagent 下載的 AstrBot（連同它自己的 Python 3.12 執行環境），在後臺執行。它沒有網頁後臺，也不需要再登入。KOOK、飛書（長連線）、釘釘（Stream 模式）、Slack（Socket Mode，指南連結會預填應用）、企業微信智慧機器人（長連線）、Mattermost 和 Misskey 只要填一兩項。「高階」分組需要公網地址或其他軟體：企業微信應用、微信公眾號、QQ Webhook、OneBot v11（NapCat）和 Satori。不提供 LINE。

兩條路徑下，連線好的平臺都會回應平臺交給機器人的每個群和私聊。一旦 `ACCESS_GROUPS` 或 `ACCESS_DM_USERS` 列出了該平臺的條目，情況就變了（見[personagent 自己的白名單](#經你已經在執行的-astrbot)）。ID 以 `<platform>:<id>` 形式到達，例如 `qq_official:<openid>`、`weixin_oc:<id>`、`telegram:<id>` 和 `discord:<id>`。QQ 官方機器人看到的是 openid，不是 QQ 號。直接連線某個平臺時，會移除同一平臺的 AstrBot 連線。

### 經你已經在執行的 AstrBot

AstrBot、NapCat（OneBot）、Koishi（經 [Satori 聯結器](../integrations/satori/README.zh-TW.md)）和 Matrix（經 [Matrix 聯結器](../integrations/matrix/README.zh-TW.md)和 mautrix 橋接）是 personagent 可以配合使用的第三方橋接。連接 personagent 直接連線的平台都用不到它們。

AstrBot 透過 `integrations/astrbot/astrbot_plugin_personagent/` 裡的外掛把訊息交給 personagent。外掛把每條訊息發到 `POST /v1/events`，並轉發響應中的回覆。它還拉取 personagent 的 outbox（`outbox_enabled`，預設開啟），所以在平臺允許機器人主動發言的地方，角色可以先開口。外掛說明裡有詳細的表格。託管的 AstrBot 會自動裝好外掛。使用你自己的 AstrBot 時，先啟動一次讓它生成 data 資料夾（其中有 `cmd_config.json`、`plugins/` 和 `config/`），然後執行：

```
personagent connect astrbot                       # 詢問，並自行查詢 AstrBot 的資料夾
personagent connect astrbot <AstrBot data dir>    # 不詢問
```

這條命令把外掛複製到 `<data dir>/plugins/`，並把同一個 `CONNECTOR_TOKEN` 寫入 `.env` 和外掛配置。它把 `personagent_url` 設為 `http://127.0.0.1:<SERVER_PORT>`，除非外掛已有它接受的地址（本機地址，包括隧道，或 HTTPS）。

AstrBot 在另一臺機器上時，從[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下載 `astrbot_plugin_personagent.zip`，在 AstrBot 外掛頁的「從檔案安裝」中上傳。把它的 `connector_token` 設為 personagent `.env` 中的 `CONNECTOR_TOKEN`，並把 `personagent_url` 設為 personagent 的 HTTPS 地址（見[對外暴露介面](#對外暴露介面)）。

升級 personagent 後，重新執行 `connect astrbot` 或上傳新的 zip。AstrBot 4.29 及以後的版本會替換已安裝的副本。更早的版本需要先解除安裝，解除安裝時不要勾選「同時刪除外掛配置檔案」。

`connect astrbot` 的選項：

- `--qq` 把 `aiocqhttp` 從 `excluded_platforms` 中移除，`--no-qq` 把它加回去。兩者都不傳時，QQ 路由保持原樣。`CONNECTOR_QQ_PLATFORMS` 跟隨外掛的最終行為。
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>` 同時在 AstrBot 自己的配置裡開啟該介面卡。Slack 還要 `--app-token`，飛書和 QQ 要 `--app-id` 和 `--app-secret`。已有的介面卡條目保留其他設定（代理、基礎地址、輪詢），只更新憑據。
- `--url https://...` 設定外掛傳送請求的 HTTPS 地址。
- `--install` 改為下載託管的 AstrBot，`--start` 啟動它。

首次執行時白名單為空。重複執行會保留白名單，以及其他被排除的平臺。

外掛預設拒絕。在 AstrBot 網頁裡填寫 `groups`，私聊填寫 `dm_users`，或者回答 `connect` 的提問。`dm_users` 不為空後才轉發私聊。[外掛說明](../integrations/astrbot/astrbot_plugin_personagent/README.zh-TW.md)列出了所有設定項。託管的 AstrBot 會用 `<platform>:*` 開啟你連線的每個平臺。安裝外掛後，重啟 AstrBot 或在網頁中重新載入外掛。在 personagent 這邊：

- `CONNECTOR_TOKEN` 認證每個請求。請求帶 `X-Personagent-Token` 請求頭，外加以 token 為金鑰、對 `timestamp.nonce.body` 計算的 HMAC-SHA256，防重放機制會拒絕重複的 nonce。截獲的請求無法重放或篡改。token 同時也是簽名金鑰，所以不要讓它進入日誌，洩露後要更換。同一主機上可選，跨主機時必須設定。
- `ADMIN_IDS` 以 `<platform>:<id>` 列出管理員的賬號（`telegram:12345`、`discord:4242`）。不帶字首的 ID 或 `qq:<id>` 是 QQ 號。`ADMIN_NAME` 設定管理員的名字。列出的所有賬號都屬於同一個人，這個人在群聊和私聊中得到更親近的人設，可以管理機器人記住的群內容，也可以獨自教它。經 AstrBot 時，平臺名是 AstrBot 顯示的介面卡名，在聊天中傳送 `/sid` 可以看到 ID。
- `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 讓 personagent 自己把關平臺，格式同為 `<platform>:<id>`。每個平臺單獨把關。沒有條目的平臺交給聯結器決定，只要有一條，該平臺就只放行列出的條目。personagent 拒絕的回合不會被接管，所以 AstrBot 自帶的模型可能回答。

AstrBot 在 Docker 裡或另一臺主機上時，見[使用指南](guide.zh-TW.md#你自己執行的橋接)。

#### 經 NapCat（OneBot）接 QQ

這條路徑用個人 QQ 賬號代替官方機器人。你需要一個在目標群裡的 QQ 小號，不要用自己的主號（見 [DISCLAIMER.zh-CN.md](DISCLAIMER.zh-TW.md)）。它登入（通常掃碼，會話在重啟後保留）一個 OneBot v11 實現，後者連線 AstrBot 的 `aiocqhttp` 介面卡。[NapCat](https://github.com/NapNeko/NapCatQQ) 經過測試，它附著在 QQ NT 桌面客戶端上。LLOneBot 和 Lagrange 是其他 OneBot v11 實現。

使用託管的 AstrBot 時，在本地頁面新增「高階 → OneBot v11（NapCat）」，並讓 NapCat 指向 `ws://127.0.0.1:6199/ws`。[第三方路線](#第三方路線astrbot--napcat)一節有分步說明。使用你自己的 AstrBot 時，從外掛的 `excluded_platforms` 移除 `aiocqhttp`，設定 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`（`--qq` 兩件事都做），並設定 `QQ_BOT_ID`（`personagent connect astrbot` 會詢問）。

**這裡必須設定 `CONNECTOR_QQ_PLATFORMS`。** 沒有它，QQ ID 會帶名稱空間（`aiocqhttp:123456`）到達，每個會話看起來都是新的。記憶、歷史和學到的樣例都以不帶字首的 ID 為鍵，賬本的行 ID 也由會話 ID 派生，所以這種分裂事後無法修復。

不帶字首的 ID 具有 QQ 許可權，所以 `ADMIN_IDS`、`ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 的 QQ 條目在外掛白名單之上繼續生效。QQ 私聊必須在 `dm_users` 中，*並且*來自管理員或 `ACCESS_DM_USERS` 的條目。`ACCESS_GROUPS` 列出 QQ 群時，QQ 群必須同時在兩邊。只有信任某個聯結器擁有這種許可權時，才把它的平臺列入 `CONNECTOR_QQ_PLATFORMS`。

**NapCat 的 HTTP 服務**（`QQ_ONEBOT_URL`，預設為空）在這條路徑上是可選的。personagent 還會主動傳送訊息：

- 主動訊息（`PROACTIVE_ENABLED`，預設關閉）；
- 被否定兩分鐘後的追問（`REACT_ELICIT_ENABLED`）；
- 模型呼叫失敗時在群裡發的致歉。

外掛在拉取 outbox 時，這些訊息經外掛的 outbox 發回。沒有拉取時，如果設定了 `QQ_ONEBOT_URL`，就發到這個地址。只有補回離線期間漏掉的 @ 才需要這個服務，同時需要 `QQ_BOT_ID`。這項掃描在啟動時執行，之後每 30 分鐘執行一次。它覆蓋 `ACCESS_GROUPS` 中的 QQ 群，以及上次重啟後有訊息的群，並重放一小時內的 @。地址為空時，`personagent doctor` 把 OneBot 橋接顯示為 "not configured"。

**所有聯結器路徑都沒有的功能**（直連、AstrBot 或其他聯結器），沒有設定能恢復：

- 沒有視覺模型描述的圖片的 OCR 備用方案；
- 經 NapCat 查詢引用。引用從 personagent 自己的近期訊息索引，以及聯結器隨引用傳送的被引用文字中解析；
- 從群裡發的圖片收集新表情。

### 同時接多個平臺

多個聯結器可以同時連線一個 personagent，因為每個聯結器都標明自己的平臺（`telegram:-1001234`、`matrix:!room:example.org`）。直連程序、AstrBot、Satori 和 Matrix 可以同時執行。不要讓同一個聊天經兩個聯結器進來，否則每條訊息都會到兩次。帶名稱空間的 ID 不會與不帶字首的 QQ 號衝突。

沒人要求的訊息經拉取 personagent outbox 的聯結器到達平臺。這些訊息是主動開場、被否定後的追問，以及群裡模型呼叫失敗時的致歉。私聊的致歉隨帶來該訊息的請求的響應返回。

直連程序和這裡的三個聯結器都會拉取 outbox，前提是平臺允許機器人先發言。QQ 會限制官方機器人主動發訊息的頻率，使用者也可以關閉這類訊息。你自己的聯結器在事件中傳送 `connector_id`、`reply_handle` 和 `"capabilities": ["outbox"]`，並長輪詢 `/v1/outbox`（見[聯結器協議](connectors.zh-TW.md)）。沒有這樣的聯結器時，personagent 只能在帶來訊息的請求內說話。主動發言迴圈會跳過這些會話，追問和致歉也不會傳送。

`PROACTIVE_PLATFORMS` 限制主動發言迴圈可以在哪裡先開口。`PROACTIVE_PLATFORMS=qq_official` 限定在 QQ 官方機器人，`qq` 限定在經 NapCat 的 QQ。`CONNECTOR_OUTBOX_ENABLED=false` 徹底關閉 outbox。

如果想不經 outbox 在私聊中先開口，你自己的排程程式（AstrBot 外掛任務、cron 條目）可以傳送標記了 `"proactive": true` 的私聊事件。見[不用 outbox 先開口](connectors.zh-TW.md#不用-outbox-先開口)。

### 對外暴露介面

聯結器和 personagent 在同一臺機器上時，保持 `SERVER_HOST=127.0.0.1`。容器只有共享主機的網路名稱空間或使用主機網路時，才算同一臺機器。本地頁面和 `personagent up` 始終繫結 `127.0.0.1`。其他情況下：

1. 設定 `SERVER_HOST=0.0.0.0`（或 `--host 0.0.0.0`）和 `CONNECTOR_TOKEN`。沒有 token 時，啟動會拒絕繫結網路地址。這裡不要求 `QQ_ONEBOT_SECRET`，但沒有它時，已棄用的 `/v1/onebot` 在網路繫結下是關閉的。發往它的每個請求都得到 403 `onebot_disabled`，日誌會說明一次原因。
2. 在前面放 HTTPS 反向代理或私有隧道。這裡的每個聯結器都只向本機地址或設定了 token 的 HTTPS 傳送。AstrBot 外掛把其他情況記錄為 `refusing unsafe personagent_url`，Satori 和 Matrix 聯結器拒絕啟動。
3. 保持請求體逐位元組不變，因為簽名覆蓋它；並讓兩邊時鐘相差不超過五分鐘。

憑據為空時，對應介面只服務直接呼叫 `http://127.0.0.1` 或 `http://localhost` 的本地程式。請求只要帶有下列任何一項，就得到 403 `non_local_request`：

- `Origin` 請求頭；
- 不是 `none` 的 `Sec-Fetch-Site`；
- 不是 `localhost`、`127.0.0.1` 或 `::1` 的 `Host`；
- 代理請求頭：`X-Forwarded-For`、`Forwarded`、`X-Real-IP`、`CF-Connecting-IP`、`Via`、`X-Forwarded-Host`、`X-Forwarded-Proto`、`X-Forwarded-Port`、`True-Client-IP`、`X-Client-IP` 或 `X-Original-Forwarded-For`。

同一主機上不新增這些請求頭的代理仍然看起來像本地請求。在新增任何代理或隧道之前，先設定 `CONNECTOR_TOKEN`（使用 `/v1/onebot` 時還有 `QQ_ONEBOT_SECRET`），即使在同一臺主機上。

### 健康檢查介面

- `GET /health` 免費、公開，不呼叫任何服務。
- `GET /health/details` 探測上游服務（快取 60 秒）。`CONNECTOR_TOKEN` 為空時，只回應本地請求。設定了 token 時，它**只**回應帶匹配 `X-Personagent-Token` 請求頭的請求，本機來的也一樣。關鍵探測失敗或無法執行時返回 503。關鍵探測是聊天模型，以及 QQ 使用 OneBot 直連入口時的 OneBot 橋接（設定了 `QQ_BOT_ID` 和 `QQ_ONEBOT_URL`，未設定 `CONNECTOR_QQ_PLATFORMS`）。
- `personagent doctor [--json]` 執行同樣的探測和設定檢查，在同樣的情況下以非零退出。上次更新檢查已過一天時，它還會向 pypi.org 查詢最新版本（`UPDATE_CHECK_ENABLED=false` 可跳過）。

### 費用

- **探測要花錢。** `personagent doctor` 和 `/health/details` 向每個配置的模型介面（聊天、私聊、評測和視覺）傳送一個很小的聊天請求。設定了 `EMBEDDING_MODEL` 時還發一次嵌入請求，設定了 `TAVILY_API_KEY` 時還發一次 Tavily 搜尋。`/health` 以及設定和賬本檢查是免費的。
- **`tools/` 裡的指令碼**各不相同，有的免費，有的呼叫模型。[tools.zh-CN.md](tools.zh-TW.md) 的表格寫明瞭哪些是哪些。
- **`personagent eval`** 對每個用例都呼叫模型。人設和學習兩套用例還需要第二個模型做評判（`BENCH_JUDGE_MODEL`）。
- **記憶。** 帶名稱空間（非 QQ）的會話超過 256 個時，最久沒有活動的空閒會話會失去近期歷史和待處理的反應。長期記憶、核心筆記和賬本保留。正在處理請求的會話不會被清除。長期記憶在啟動時從磁碟載入，不受這個上限限制。
- **磁碟。** `runtime/` 中的證據日誌和候選賬本只追加，從不截斷。任何一個超過 50 MB 時，`personagent doctor` 會標記（`LEDGER_EVIDENCE_WARN_BYTES`、`LEDGER_CANDIDATES_WARN_BYTES`）。請備份 `runtime/`，因為機器人學到的一切都在裡面。

### 完整排查清單

這是[機器人不說話](#機器人不說話)的完整版，最常見的原因在前。本地頁面執行角色服務時，[動態](guide.zh-TW.md#動態)顯示訊息是否到達、它為什麼沒開口。在伺服器上，讀服務日誌，學到的內容用 `personagent learned` 檢視。

1. **訊息沒有送達。** 在本地頁面確認平臺顯示為已連線，並讀 `runtime/desktop/direct.log` 或 `astrbot.log`。QQ 官方機器人必須在群裡，QQ 決定它能收到哪些群訊息。個人微信機器人收不到群訊息。在你執行的 AstrBot 中，填寫外掛的 `groups`（私聊填 `dm_users`），NapCat 還要把 `aiocqhttp` 從 `excluded_platforms` 中移除。Satori 和 Matrix 聯結器在各自的 `.env` 裡有自己的白名單，見它們的 README。這種情況下，聊天不會出現在「動態」裡。
2. **角色服務沒開。** `personagent run` 的啟動資訊顯示 `agent: OFF`，並給出原因和解決辦法。沒有 `LLM_API_KEY` 時，在本地頁面新增 key（或設定 `LLM_API_KEY`）並重啟。`AGENT_ENABLED=false` 時，在 `<home>/.env` 裡改為 `true` 並重啟。在此之前，每個事件都得到 `owned: false`，第一個事件會記錄一行內容相同的 ERROR。
3. **AstrBot 自帶的模型代為回答。** 外掛回退了，因為請求失敗、personagent 拒絕了這條訊息（第 5 項），或角色服務沒開（第 2 項）。AstrBot 的日誌顯示 `refusing unsafe personagent_url`、`agent refused the request (403): <message>`（或其他狀態，見下表）或 `timed out waiting for the agent`。`timeout_s` 必須覆蓋防抖和回合內的模型呼叫，還要算上訊息到達時仍在思考的那個回合。不論群聊還是私聊，一個回合的所有模型呼叫共用 1.5 × `LLM_TIMEOUT_S`，所以讓 3 × `LLM_TIMEOUT_S` 低於它。它的預設值（420）覆蓋角色服務的預設值（3 × 120 = 360 秒）。調大 `LLM_TIMEOUT_S` 時也要調大它。
4. **沒有叫到它。** 在群裡，它回應自己的名字（`PERSONA_NAME`）或 @。其他情況下，它等到聊夠（`CHAT_TRIGGER_COUNT`，預設 30 條）才考慮，也可能仍然不說。在它所在時區的 02:00 到 07:00，它大多不參與沒有叫它的聊天。時區是 `PERSONA_TZ_OFFSET_HOURS`。留空時，`AGENT_LANG` 為 `zh` 或 `zh-TW` 按 UTC+8，其他語言按本機時區。「動態」顯示最近每個回合的原因。要離線觀察同樣的判斷，執行 `personagent chat --trigger 4`。
5. **personagent 自己的白名單。** `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 在每條路徑上都生效，不帶字首 ID 的 QQ 私聊還需要是管理員或有條目。被它們攔下的訊息不會被接管，所以經 AstrBot 時，它自帶的模型可能回答。personagent 對每個被拒絕的會話以 INFO 記錄一次，並寫明拒絕它的設定。
6. **模型呼叫失敗。** key 被拒（401 或 403）或餘額耗盡（402 或配額用完）時，記錄一行 ERROR，寫明服務商主機和要修改的設定。執行 `personagent doctor`，它向每個模型介面發一個很小的請求並顯示狀態，也能查出錯誤的 `LLM_BASE_URL` 或 `LLM_MODEL`。模型不可用期間，被叫到時角色會發一句符合人設的簡短致歉，每個會話每五分鐘最多一次。
7. **設定名寫錯。** 啟動日誌和 `personagent doctor` 列出 `.env.example` 不認識的所有鍵，以及任何以 `#` 開頭的值。
8. **`.env` 帶有 BOM。** 第一個設定的名字帶上了 BOM，到不了程序。啟動和 `personagent doctor` 都會報告。把檔案重新儲存為不帶 BOM 的 UTF-8。
9. **使用 NapCat 時 `QQ_BOT_ID` 未設定或有誤。** 經 AstrBot 時 @ 仍然有效，但補回漏掉的 @ 要靠它匹配。在 OneBot 直連入口上，@ 永遠不會被識別：機器人正常啟動，不記錄任何內容，也從不回應。`QQ_BOT_ID` 為空而設定了其他 QQ 設定時，`personagent doctor` 會警告。QQ 官方機器人不使用它。
10. **能回答，但忘了學過的東西。** 要麼 NapCat 的 QQ 訊息到達時沒有 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`，要麼 `PERSONA_NAME` 或 `PERSONA_VERSION` 變了，這會開始一個新角色。舊角色已生效的內容被整體拒絕時，日誌會警告。修改 `persona.txt`（包括在頁面的「人設」框裡）不會開始新角色。同一 `PERSONA_VERSION` 下的修訂共享學習範圍（`runtime/persona_lineage.json`）。要併入在譜系未列出的人設雜湊下學到的行，執行 `personagent learned lineage adopt <hash>`，再執行 `personagent learned rebuild`。雜湊在 `personagent learned show <id>` 顯示的候選範圍裡。在中文和其他語言之間切換 `AGENT_LANG`，也會切換到 `runtime/` 裡另一組學習檔案。

下面列出 `/v1/events` 的錯誤。AstrBot 外掛記錄訊息，`code` 是客戶端可以據以分支的穩定欄位。

| 狀態 | `code` | AstrBot 日誌中的訊息 | 原因 |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | 沒有 `CONNECTOR_TOKEN`，呼叫方不在這臺機器上 |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | 沒有 `CONNECTOR_TOKEN`，請求來自瀏覽器、代理或其他主機名 |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | token、請求頭或簽名缺失或錯誤，時鐘相差超過 5 分鐘，nonce 重複，或防重放已滿（角色服務日誌中有 `connector replay guard full`） |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` 與當前時間相差超過 `CONNECTOR_MAX_EVENT_AGE_S`（24 小時），包括未來或毫秒時間戳 |
| 400 | `invalid_schema` | invalid event schema | 缺少必填欄位：`platform`、`conversation_type`、`sender_id`、`message_id`、`sent_at`，群聊還有 `conversation_id` |
| 400 | `client_disconnected` | client disconnected | 呼叫方在傳送時斷開 |
| 408 | `body_timeout` | request body not received in time | 請求體超過 30 秒才到達 |
| 413 | `body_too_large` | request body too large | 超過 `SERVER_MAX_BODY_BYTES`（8 MB），通常是內嵌圖片 |
| 429 | `capacity_exceeded` | webhook capacity exceeded | 進行中的回合超過 `CONNECTOR_MAX_INFLIGHT`；3 秒後重試 |

### 舊方式：OneBot 直連入口

NapCat 的 webhook 仍然可以把事件發到 `POST /v1/onebot`，personagent 經 `QQ_ONEBOT_URL` 回覆。這條路線已棄用，在 1.x 中保留。請改用 QQ 官方機器人連線，或經 AstrBot 使用 NapCat 並設定 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。這條路線在首次使用時警告一次，並在每個響應中標記 `Deprecation: true`。

要遷移到經 AstrBot 的 NapCat，在本地頁面新增 OneBot v11（NapCat），或者為你自己的 AstrBot 執行 `personagent connect astrbot <AstrBot data dir> --qq` 並填寫白名單。讓 NapCat 的 WebSocket 客戶端指向它，並關閉 NapCat 的 HTTP 客戶端（保留 HTTP 服務）。記憶和學習內容會延續，因為 `CONNECTOR_QQ_PLATFORMS` 保持 ID 不變。

如果還在執行舊路線：

- 按 [NapCat 文件](https://napneko.github.io/)配置兩個方向。你需要一個位於 `QQ_ONEBOT_URL` 的 **HTTP 服務**用於傳送，以及一個向 `http://127.0.0.1:8080/v1/onebot`（`SERVER_HOST`、`SERVER_PORT`）傳送的 **HTTP 客戶端**。`QQ_ONEBOT_URL` 預設為空，所以要寫進 `.env`，否則機器人只收不回。這條路線看起來已配置（設定了 `QQ_BOT_ID` 或 `QQ_ONEBOT_SECRET`，`CONNECTOR_QQ_PLATFORMS` 為空）而 `QQ_ONEBOT_URL` 為空時，啟動檢查和 `personagent doctor` 會警告。
- NapCat 在另一臺機器上時，把 `QQ_ONEBOT_SECRET` 設為 HTTP 客戶端的 `secret`。否則任何能訪問這個埠的人都能偽造事件。請求體必須帶 `x-signature: sha1=<hex>`（否則 403 `bad_signature`），時間戳偏差超過五分鐘的事件得到 403 `stale_event`。沒有這個金鑰時，這條路線只回應本機程式，在網路繫結下是關閉的（403 `onebot_disabled`）。
- 同一賬號上還有 AstrBot 時，把 `aiocqhttp` 留在 `excluded_platforms` 裡，否則每條訊息都會到兩次。

用 `curl http://127.0.0.1:3000/get_login_info` 檢查傳送。給機器人發群訊息，同時觀察 personagent 的日誌，以檢查接收。

## 其他文件

- [AstrBot 外掛說明](../integrations/astrbot/astrbot_plugin_personagent/README.zh-TW.md)
- [免責宣告](DISCLAIMER.zh-TW.md)
