# 部署 personagent：QQ 掃碼直連，以及排查

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · 繁體中文 · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md) · 簡體中文 · [繁體中文](deploy.zh-TW.md) · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

本文按順序介紹如何把角色接入 QQ 群：安裝、填寫 key、用手機 QQ 掃碼。QQ 官方機器人由 personagent 直接連線，不需要 AstrBot，也不需要 NapCat 和 QQ 小號。微信、Telegram、Discord 同樣由它直接連線。如果想用個人 QQ 小號，請看後面的[第三方路線：AstrBot + NapCat](#第三方路線astrbot--napcat)。

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

你應該看到瀏覽器開啟一個本地頁面，包含三個檢視：「開始聊天」「連線平臺」「角色與設定」。再次執行 `personagent` 會複用已經開啟的頁面。

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

- **personagent 直接連線**：QQ、個人微信、Telegram、Discord。個人微信用手機微信掃碼登入（使用騰訊的 iLink 機器人介面），只支援私聊，因為微信不會把群訊息交給這類機器人。Telegram 需要貼上 @BotFather 提供的 token；Discord 需要貼上機器人 token，並開啟 Message Content Intent。
- **經託管的 AstrBot 連線**：其餘平臺。第一次連線這類平臺時，personagent 會下載 AstrBot 和獨立的 Python 3.12，並在後臺執行。它沒有網頁後臺，也不需要再登入一個賬號。只需貼上一兩項就能連線的有：KOOK、飛書（長連線）、釘釘（Stream 模式）、Slack（Socket Mode，頁面上的連結會預填好應用）、企業微信智慧機器人（長連線）、Mattermost、Misskey。「高階」分組裡的平臺需要公網地址或本機的其他軟體：企業微信應用、微信公眾號、QQ（Webhook）、OneBot v11（NapCat）、Satori。暫不提供 LINE。

連線好的平臺預設回覆所有群聊和私聊。如果只想放行一部分，在 `.env` 裡寫 `ACCESS_GROUPS` 或 `ACCESS_DM_USERS`（格式為 `平臺:ID`，見[英文部署指南](deploy.md#through-an-astrbot-you-already-run)）。

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

- 在「動態」裡，「等你確認」下的每條改動都有「保留」和「不要」兩個按鈕。「保留」會讓它生效，如果同一條回覆已經有生效中的改寫，就替換掉那條。「學到的」下每一條都有「撤銷」按鈕。
- 也可以使用命令：`personagent learned list`、`personagent learned show <編號>`、`personagent learned rollback <編號>`。

如果希望它更保守，在 `.env` 里加上 `PROMOTE_MIN_SPEAKERS=2`，這樣需要兩個不同的人都認可才會改變。

在群裡對它說 `小夏 記住 …`、`小夏 忘掉 …`、`小夏 你都記得什麼`，可以直接管理它的記憶；`小夏 學到了什麼` 會列出它學到的內容。命令必須放在訊息開頭。以「嗎」「呢」「沒」等結尾的問句（比如 `小夏 記住了嗎`）只當作聊天處理；`小夏 忘掉這個` 的意思是「算了」，不會刪除任何內容。每條筆記都會記錄是誰記下的、內容涉及誰；不針對具體某人的筆記全群可見，列出時標註「來自某某」。

修改人設不會清空它學到的東西。

## 機器人不說話

請按順序排查，越靠前的原因越常見。角色服務由本地頁面啟動時，先看「動態」：聊天是否出現、有沒有收到訊息、它為什麼沒開口，都能在這裡看到。在伺服器上，看服務日誌，學到的東西用 `personagent learned` 檢視。再看主目錄下 `runtime/desktop/` 裡的日誌：`agent.log`（角色服務）、`direct.log`（QQ、微信、Telegram、Discord）、`astrbot.log`（其他平臺）。

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

AstrBot、NapCat（OneBot）、Koishi（經 Satori 聯結器）和 Matrix（經 mautrix 橋接 WhatsApp、Signal 等）是 personagent 可以配合使用的第三方橋接，連線 QQ、微信、Telegram、Discord 都用不到它們。只有在想用**個人 QQ 小號**而不是官方機器人時，才需要 NapCat。

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
   - `timed out waiting for the agent`：模型響應太慢。外掛的 `timeout_s` 預設為 420 秒，足以覆蓋 personagent 預設設定下最長的 360 秒；如果調大了 `LLM_TIMEOUT_S` 或 `LLM_MAX_RETRIES`，也要相應調大 `timeout_s`。
   - `agent request failed`：personagent 沒有執行，或者地址、埠填寫有誤。
3. **QQ 私聊被攔下。** 經 NapCat 進來的 QQ 私聊，必須來自管理員（`ADMIN_IDS`），或者在 `ACCESS_DM_USERS` 之中。
4. **`QQ_BOT_ID` 未填寫或填寫錯誤。** 這裡應填小號的 QQ 號。
5. **忘了學過的東西。** 經 NapCat 的 QQ 會話必須配置 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`，缺少這項時，所有 QQ 會話都會被當作新會話。

**NapCat 的 HTTP 服務**是可選的。開啟後，personagent 能補回它離線期間漏掉的 @ 訊息。做法是在 NapCat 裡開啟 HTTP 服務，並在 `.env` 裡寫上 `QQ_ONEBOT_URL=http://127.0.0.1:3000`（埠以 NapCat 中的設定為準）和 `QQ_BOT_ID`（小號的 QQ 號）。

**舊的直連方式。** NapCat 直接把事件發到 personagent 的 `/v1/onebot`，這種方式已不再推薦，但在 1.x 中仍然可用。它要求在 `.env` 裡寫上 `QQ_ONEBOT_URL`，否則機器人只收不回，`personagent doctor` 會對此給出提醒。改用 AstrBot 之後，要關閉 NapCat 裡指向 `/v1/onebot` 的 HTTP 客戶端，否則每條訊息都會收到兩遍。已經學到的記憶會保留。

## 其他文件

- [英文版部署指南](deploy.md)：全部設定、對外暴露埠、錯誤碼。
- [AstrBot 外掛說明](../integrations/astrbot/astrbot_plugin_personagent/README.zh-TW.md)
- [免責宣告](DISCLAIMER.zh-TW.md)
