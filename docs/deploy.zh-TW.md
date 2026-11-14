# 部署 personagent：以掃描直接連接 QQ，以及疑難排解

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · 繁體中文 · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

本文依序說明如何將角色接入 QQ 群組：安裝、填寫金鑰、以手機 QQ 掃描。QQ 官方機器人由 personagent 直接連線，不需要 AstrBot，也不需要 NapCat 和 QQ 次要帳號。微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 同樣由它直接連線。如需使用個人 QQ 次要帳號，請參閱後文的[第三方路線：AstrBot + NapCat](#第三方路線astrbot--napcat)。

```text
QQ 群  ⇄  personagent（直連處理程序 + 角色服務）  ⇄  AI 模型
```

每一步都註明了「你應該看到」的結果。如果結果不符，請勿繼續，直接參閱[機器人未回覆](#機器人未回覆)。

## 開始之前

- 一台可長時間開機的電腦（Windows、macOS 或 Linux），已安裝 Python 3.10 至 3.14。personagent 關閉後，機器人也會隨之停止。
- 一個 AI 服務的 API 金鑰。DeepSeek、矽基流動、阿里雲百鍊、智譜、Kimi、火山方舟等均可，請在各服務的主控台中建立。
- 一支已登入你本人 QQ 帳號的手機，用於掃描。

## 第一步：安裝並開啟

```sh
python -m pip install personagent
personagent
```

若已安裝 [uv](https://docs.astral.sh/uv/)，可以使用 `uvx personagent` 免安裝執行。在 Windows 上，也可以下載原始碼 ZIP，解壓縮後按兩下 `start.bat`。從 Git 儲存庫執行的方式請參閱[入門指南](start.zh-TW.md)。

你應該看到一個本機頁面：在 Windows 上顯示於獨立的視窗中，在 macOS 和 Linux 上則在瀏覽器中開啟。頁面側欄有六個檢視：「開始聊天」「動態」「連接平台」「角色與設定」「演練」「應用程式」。再次執行 `personagent` 會沿用已開啟的頁面。

> 如需將資料存放在其他磁碟，請執行 `personagent --home D:\personagent`，之後的每個指令都須加上相同的 `--home`。未指定時，資料會存放在使用者目錄下的 `personagent` 資料夾。

## 第二步：填入金鑰並選擇角色

第一次開啟頁面時，設定表單會直接顯示在「開始聊天」中；之後可在「角色與設定」中修改。在表單中選擇模型服務（共有 10 個預設選項，另有「其他」，可填寫任何相容 OpenAI 的位址），貼上 API 金鑰，再選定名稱和個性。儲存時，程式會傳送一個很小的請求以驗證金鑰，驗證未通過時不會儲存任何內容。

你應該能在「開始聊天」中與角色對話，它會以你選擇的個性回覆。

「人設」欄位中是 `persona.txt` 的內容，即角色目前使用的人設。修改後點選「儲存人設」，角色服務會重新啟動，已學到的內容會保留。

「角色與設定」中的「更多功能」可以開啟網路搜尋、辨識圖片和偶爾主動發言。未開啟「辨識圖片」時，角色看不到經各平台收到的圖片內容，圖片中的文字也不例外。

## 第三步：掃描連接 QQ

1. 開啟「連接平台」，選擇 **QQ**。
2. 頁面會顯示 QR 碼。使用手機 QQ 掃描並確認，可以新建一個機器人，也可以選擇既有的機器人，金鑰由 personagent 自動取回。如果無法掃描，也可以在 [QQ 開放平台](https://q.qq.com/qqbot/openclaw/login.html)建立機器人，再點選「改為手動填寫」並貼上 AppID 和 AppSecret。
3. 程式確認 QQ 接受此機器人之後才會儲存。如果 QQ 拒絕，頁面會顯示提示，且不會儲存任何內容。

你應該會看到 QQ 出現在頁面上方，狀態為「已連接」。

**將機器人加入群組。** 在手機 QQ 中找到此機器人，私訊它或將它加入群組。機器人可以加入哪些群組由 QQ 決定：通過認證之前，QQ 只允許它加入你擔任群主的群組。在群組中，它預設只會收到 @ 它的訊息，因此不會主動插話；如需讓角色跟上群組中的對話，請由群主在該群組的機器人資料頁開啟「接收全量訊息」。認證等帳號相關事項請參閱 [QQ 機器人官方指南](https://bot.q.qq.com/wiki/bot_new_product-intro/)。

**測試。** 在群組中傳送一則包含機器人名稱的訊息（例如 `小夏，你好`），或 @ 它。數秒至十餘秒內應會看到回覆。

## 其他平台

所有平台都在「連接平台」中新增。憑證會先交由平台驗證，通過後才會儲存。

- **personagent 直接連線**：QQ、個人微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat。個人微信以手機微信掃描登入（使用騰訊的 iLink 機器人介面），僅支援私訊，因為微信不會將群組訊息轉交給這類機器人。Telegram 需要貼上 @BotFather 提供的 Token；Discord 需要貼上機器人 Token，並開啟 Message Content Intent。其餘六個平台需要填寫的內容與使用限制，請參閱[使用手冊](guide.zh-TW.md#personagent-直接連線的平台)。
- **透過託管的 AstrBot 連線**：其餘平台。首次連接這類平台時，personagent 會下載 AstrBot 和獨立的 Python 3.12，並在背景執行。它沒有網頁管理後台，也不需要另外登入帳號。只需貼上一至兩項即可連接的平台有：KOOK、飛書（長連線）、釘釘（Stream 模式）、Slack（Socket Mode，頁面上的連結會預先填好應用程式設定）、企業微信智慧機器人（長連線）、Mattermost、Misskey。「進階」分組中的平台需要公開網址或本機的其他軟體：企業微信應用、微信公眾號、QQ（Webhook）、OneBot v11（NapCat）、Satori。暫不提供 LINE。

已連接的平台預設會回覆所有群組與私訊。如果只想在部分群組中回覆，請在「角色與設定」→「進階設定」→「管理員與回覆範圍」中點選「從最近的聊天中選擇」，為要保留的群組勾選「在此群組中回覆」，或直接在「僅在以下群組中回覆」中填寫，然後儲存，詳見[管好它](#管好它)。頁面會將其儲存為 `.env` 中的 `ACCESS_GROUPS`，私訊則對應 `ACCESS_DM_USERS`（格式均為 `平台:ID`）。

## 管好它

以下操作都在本機頁面中完成。相關設定位於「角色與設定」→「進階設定」，點選「儲存」後生效。

- **將自己設為管理員。** 先私訊角色一次，再在「管理員與回覆範圍」中點選「從最近的聊天中選擇」，在自己的帳號旁點選「這是我」。以掃描連接的 QQ 官方機器人看到的是 openid，而非 QQ 號碼，因此請以這種方式設定。
- **只在部分群組中回覆。** 在同一清單中為要保留的群組勾選「在此群組中回覆」，或在「僅在以下群組中回覆」中填寫群組編號。某個平台一旦列出任一群組，角色在該平台的其他群組中便不再回覆。
- **暫停全部回覆。** 在「其他設定」中關閉「回覆訊息」。角色仍保持連線，但在重新開啟之前不會回覆任何訊息。
- **復原學到的內容。** 在「動態」中選取該聊天，點選項目旁的「復原」，或執行 `personagent learned rollback <編號>`。
- **將機器人移出群組。** 請在平台中將機器人移出群組。在「連接平台」中中斷連線只會結束 personagent 的連線，機器人仍是群組成員。
- **被移出群組或受到限制時。** 機器人被移出的群組只是不再有訊息送達，不需要重新連線。平台封鎖機器人或將其下架時，personagent 直接連線的平台會停止連線，「連接平台」中會顯示原因。

## 日常使用

- 每次開機後執行 `personagent`。頁面開啟期間，角色服務、直連處理程序和託管的 AstrBot 都會持續執行，已連接的平台會自動恢復連線。如果不想開啟瀏覽器，可以使用 `personagent up`，效果相同。
- 由它啟動的處理程序會隨它一併結束，無論它以何種方式結束。上次異常結束時遺留的處理程序，會在下次啟動時先行停止。
- 所有資料都位於一個主目錄中：`.env`（設定）、`persona.txt`（人設）、`runtime/`（學到的內容和記錄檔）、`platforms/`（託管的 AstrBot，以及直連平台的憑證 `direct.json`）。金鑰只儲存在這台電腦上，對話內容會傳送給你選擇的模型服務。
- 如需直接修改 `.env`，可以使用記事本編輯，儲存為 UTF-8（不含 BOM），然後重新啟動 `personagent`。
- 有新版本時，「開始聊天」頁面和終端機會顯示與你的安裝方式對應的更新指令。頁面和 `personagent up` 每天最多向 pypi.org 查詢一次，請求中只包含版本號；在 `.env` 中設定 `UPDATE_CHECK_ENABLED=false` 即可關閉此項檢查。
- 手動更新：`python -m pip install -U personagent`（以 uv 安裝時，請執行 `uv tool upgrade personagent`）。從 0.x 升級時，如果啟動時提示存在舊的設定名稱，請執行 `personagent doctor --fix`，它會將 `.env` 中的舊名稱改為新名稱，並將原檔案另存為 `.env.bak`。
- 命令列：`personagent init --terminal`（終端機設定精靈）、`chat`（在終端機中聊天）、`demo`（無須金鑰的示範）、`run`（只啟動角色服務）、`doctor`（檢查設定和各項服務）、`learned`（檢視學到的內容，必要時介入）、`memory`（檢視記住的內容，刪除或還原某一項）、`eval`（評測）。

## 動態

本機頁面側欄中的「動態」會列出角色所在的每個群組與私訊。選取一個聊天後，可以看到它學到的內容及各自的投入使用方式、仍在觀察的內容及各自的進展、它記住的內容，以及近期的訊息：包括它每次發言的原因，以及未發言時的理由。這裡沒有任何內容需要你確認。詳見[使用手冊](guide.zh-TW.md#動態)。

「動態」的資料來自本機頁面所啟動的角色服務，取自它在 `/api/dashboard/` 下的 JSON 介面。僅以 `personagent run` 啟動服務時，請查看服務記錄檔，並使用 `personagent learned` 檢視學到的內容、`personagent memory` 檢視記住的內容。每次呼叫都須帶有 `X-Personagent-Dashboard-Token` 請求標頭，其值為執行目錄（預設 `<主目錄>/runtime/`，可用 `AGENT_RUNTIME_DIR` 修改）中 `dashboard.token` 檔案的內容。此檔案在服務啟動時產生，僅限本人讀取。修改操作還須帶有 `X-Personagent-Dashboard: 1` 和 `Content-Type: application/json`；如果請求帶有 `Origin`，則必須是服務本身的位址。跨站的瀏覽器請求一律拒絕，`CONNECTOR_TOKEN` 也無法存取此介面。傳回內容中的金鑰都會被遮蔽。腳本也可以依相同方式呼叫。設定 `DASHBOARD_ENABLED=false` 會關閉此介面，「動態」也將不顯示內容，`personagent doctor` 會輸出 `activity: off (...)`。

角色服務本身不提供網頁，存取 `http://127.0.0.1:8080/` 只會看到一段說明，指向本機頁面和 `personagent learned`；以往的 `?token=` 連結現在也只會開啟這段說明。本機頁面只監聽 127.0.0.1。在沒有本機頁面的伺服器上，可使用 `personagent learned` 檢視角色學到的內容、正在觀察的內容及原因，並可立即啟用、擱置、撤回某項，或恢復由角色或時限擱置、由角色或規則停止使用的內容；`personagent memory` 可列出角色記住的內容，並刪除或還原某一項。

## 學習方式

一聲「哈哈」或單獨一句話不會改變機器人。同一聊天中出現兩次一致的反應，且其中至少一次足夠「明確」時，反應即可讓變更投入使用。「明確」是指**被回覆者以自己的話糾正了它，或接受了它的第二次回答**。旁觀者的糾正（即使機器人回頭詢問了對方）、陌生人的指示，或有人直接轉換話題，都不予計入。因此在預設設定下，一個人只能教它如何回覆自己，且僅在其本人所在的聊天中生效。

後續反應無法確定的項目，由角色自行判斷：例如兩人的糾正互相矛盾、同一則回覆的兩種改寫並存，或被回覆者作了糾正但無人確認。角色每次判斷呼叫一次模型，決定投入使用、擱置或繼續觀察，並記錄理由。旁觀者對學到內容的抱怨，同樣由角色權衡後決定是否繼續使用。連續 30 天（`PROMOTE_OBSERVE_MAX_DAYS`）沒有新反應的項目會被擱置。任何內容都無須你確認。

學到的所有內容都記錄在僅可追加的學習紀錄中，可隨時介入：

- 在「動態」中，「學習紀錄」下的每一項都說明了其投入使用的方式，並附有「復原」按鈕；「仍在觀察」下的每一項都說明了目前的進展，沒有按鈕。下方的「角色學到的內容」列出全部學到的內容，並可選擇「立即投入使用」「擱置」「復原」，或對由角色或時限擱置、由角色或規則停止使用的項目選擇「恢復使用」；角色未執行時也可以在此操作。
- 也可以使用指令：`personagent learned`（正在觀察的內容）、`personagent learned show <編號>`、`personagent learned rollback <編號>`、`personagent learned restore <編號>`。

如果希望它更加保守，請在 `.env` 中加入 `PROMOTE_MIN_SPEAKERS=2`，如此一來，須經兩位不同的人認可，反應才會讓變更投入使用；在此之前角色會繼續觀察。設定 `PROMOTE_JUDGE_ENABLED=false` 後，角色不再自行判斷，反應無法確定的項目維持觀察中；設定 `PROMOTE_AUTO_ENABLED=false` 後，不會再有新的內容投入使用。

在群組中對它傳送 `小夏 記住 …`、`小夏 忘掉 …`、`小夏 你都記得什麼`，即可直接管理它的記憶；`小夏 學到了什麼` 會列出它學到的內容。指令必須位於訊息開頭。以「嗎」「呢」「沒」等結尾的問句（例如 `小夏 記住了嗎`）只會被當作一般聊天；`小夏 忘掉這個` 的意思是「算了」，不會刪除任何內容。每則筆記都會記錄由誰記下、內容涉及何人；未針對特定人物的筆記全群組可見，列出時會標註「來自某某」。

修改人設不會清空它學到的內容。

## 記憶

角色會為每個聊天保存近期訊息（在 `runtime/recent.json` 中保留 72 小時，重新啟動不會遺失）、此前對話的摘要、附日期的事件、關於成員和群組的事實，以及常駐記憶。較早的訊息離開近期訊息的範圍時，會呼叫一次判斷模型進行記憶整理，更新摘要、事件和事實，每項變更都單獨檢查。每個聊天每天最多整理 16 次，所有聊天合計不超過 `MEMORY_CALLS_PER_DAY`（預設 40）次；設為 0 即關閉。角色自行移除的內容可在 30 天內還原，在頁面或終端機中刪除的內容可在 24 小時內還原；在聊天中要求忘記的內容和「清除此聊天的記憶」都無法還原。在「動態」中選取一個聊天，「記憶」區塊會列出全部內容；在終端機中可使用 `personagent memory`。詳見[使用手冊的記憶一節](guide.zh-TW.md#記憶)。

## 機器人未回覆

請依序排查，越前面的原因越常見。角色服務由本機頁面啟動時，請先查看「動態」：聊天是否出現、是否收到訊息、它為何沒有發言，都可以在此查看。在伺服器上，請查看服務記錄檔，學到的內容請以 `personagent learned` 檢視，記住的內容請以 `personagent memory` 檢視。接著查看主目錄下 `runtime/desktop/` 中的記錄檔：`agent.log`（角色服務）、`direct.log`（personagent 直接連線的平台）、`astrbot.log`（其他平台）。

1. **訊息未送達。** 在「連接平台」中確認該平台顯示為「已連接」。QQ 機器人必須已在群組中，它在群組中可收到哪些訊息由 QQ 的設定決定；個人微信僅支援私訊。使用第三方 AstrBot 時，請參閱[第三方路線排查](#第三方路線排查)。
2. **角色服務未啟動，或缺少金鑰。** 在「角色與設定」中重新填寫金鑰並儲存。如果 `.env` 中設定了 `AGENT_ENABLED=false`，請改為 `true` 後重新啟動。
3. **未點名它。** 在群組中，它只回應包含其名稱（`PERSONA_NAME`）或 @ 它的訊息。其他情況下，它要等群組中累計 `CHAT_TRIGGER_COUNT` 則訊息（預設 30 則）才會考慮加入對話，考慮後也可能選擇不發言。凌晨 2 點至 7 點它較少主動發言。`AGENT_LANG` 為 `zh` 或 `zh-TW` 時以 UTC+8 計算，如需變更時區，請在 `.env` 中設定 `PERSONA_TZ_OFFSET_HOURS`。測試時請先以名稱點名它。
4. **被 personagent 本身的允許清單攔下。** `.env` 中的 `ACCESS_GROUPS`、`ACCESS_DM_USERS` 一旦列出某個平台的項目，該平台就只會開放所列的項目。被攔下的對話會在 `agent.log` 中記錄一行。
5. **模型呼叫失敗。** 金鑰無效或餘額用盡時，`agent.log` 中會有一行 ERROR，註明是哪個服務、應修改哪項設定。執行 `personagent doctor` 會向每個模型傳送一個很小的請求，並直接顯示狀態碼。主模型逾時或連線中斷，且 `LLM_FALLBACK_MODEL` 指定了不同的模型時，本次呼叫會立即改用備用模型；服務方在正常回應中傳回的錯誤（如 OpenRouter 的上游故障）依相應的 HTTP 錯誤處理。「動態」會將這一回合標為「模型未作出回應」。
6. **設定名稱有誤。** 寫錯的設定名稱不會產生錯誤，程式只會繼續使用預設值。`personagent doctor` 和啟動記錄檔會列出無法識別的設定名稱。
7. **`.env` 含有 BOM。** 以記事本另存時選錯編碼，會導致第一行設定失效。`personagent doctor` 會回報此問題，改以「UTF-8」（不含 BOM）重新儲存即可。
8. **可以回覆，但遺失了學過的內容。** 修改 `PERSONA_NAME` 或 `PERSONA_VERSION` 會使它被視為新角色；在「人設」欄位中修改人設則不會。

如果仍無法解決，請至 [Issues](https://github.com/wangkant/personagent/issues) 提問，並附上 `personagent doctor` 的輸出（請先遮蓋金鑰和帳號）。

## 第三方路線：AstrBot + NapCat

AstrBot、NapCat（OneBot）、Koishi（經 Satori 聯結器）和 Matrix（經 mautrix 橋接 WhatsApp、Signal 等）是 personagent 可以搭配使用的第三方橋接程式，連接 personagent 直接連線的平台時均不需要它們。只有在希望使用**個人 QQ 次要帳號**而非官方機器人時，才需要 NapCat。

注意：NapCat 並非騰訊官方用戶端，次要帳號有遭到限制甚至停權的風險。請勿使用你本人的主要帳號，詳見 [DISCLAIMER.zh-TW.md](DISCLAIMER.zh-TW.md)。

### 使用託管的 AstrBot（建議）

1. 按 [NapCat 文件](https://napneko.github.io/)安裝 NapCat，以手機上的**次要帳號**掃描登入。
2. 在 personagent 頁面的「連接平台」中選擇「進階 → OneBot v11（NapCat）」，連接埠預設為 `6199`。
3. 在 NapCat 的網頁中依序點選「網路設定」→「新建」→「WebSockets 客戶端」，勾選「啟用」，URL 填入 `ws://127.0.0.1:6199/ws`，然後儲存。

託管的 AstrBot 會自動安裝 personagent 外掛程式，並寫入 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。採用此方式時，NapCat 也需要持續執行。

### 使用你自己的 AstrBot

AstrBot 透過外掛程式 `astrbot_plugin_personagent` 將訊息交給 personagent。安裝方式有兩種：

- 執行 `personagent connect astrbot`，依提示選擇 QQ（透過 NapCat），填寫次要帳號的 QQ 號碼、群號和你本人的 QQ 號碼。它會將外掛程式複製到 AstrBot 的 `plugins` 資料夾，在兩端寫入同一個 `CONNECTOR_TOKEN`，並寫入允許清單和 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。如果不確定 AstrBot 的 `data` 資料夾位置，可以搜尋 `cmd_config.json`。
- 也可以從 personagent 的[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下載 `astrbot_plugin_personagent.zip`，在 AstrBot 外掛程式頁面的「從檔案安裝」中上傳，再將外掛程式設定中的 `connector_token` 設為 personagent `.env` 中的 `CONNECTOR_TOKEN`。AstrBot 不在這台電腦上時請使用此方式，此時外掛程式的 `personagent_url` 還須填寫 personagent 的 HTTPS 位址（請參閱下文關於 Docker 的段落）。

升級 personagent 後，請重新執行 `personagent connect astrbot` 或上傳新的 zip。AstrBot 4.29 及以後的版本會直接取代已安裝的外掛程式；更早的版本須先解除安裝外掛程式，解除安裝時請勿勾選刪除外掛程式設定檔。

安裝完成後，請重新啟動 AstrBot（或在外掛程式頁面重新載入外掛程式），然後以 `personagent run` 啟動角色服務並保持執行。在 AstrBot 中新增 OneBot v11 機器人（反向 WebSocket 連接埠 `6199`），再依上一節第 3 步讓 NapCat 指向它。AstrBot 的介面以[其官方文件](https://docs.astrbot.app)為準。

如果 AstrBot 在 Docker 中執行，`127.0.0.1` 指的是容器本身，而外掛程式會拒絕傳送至其他位址的明文 `http://`。可擇一處理：讓 AstrBot（以及同一個 compose 中的 NapCat）使用主機網路（`network_mode: host`，`docker run` 時使用 `--network host`；Docker Desktop 需要 4.34 以上版本，並開啟 `Enable host networking`）；或為 personagent 提供一個 HTTPS 位址，再執行 `personagent connect astrbot <data 資料夾> --url https://你的位址`。

### 第三方路線排查

1. **AstrBot 未轉交訊息。** 在外掛程式設定中確認 `groups` 包含該群號；私訊須在 `dm_users` 中填寫傳送者的 QQ 號碼。再確認 `excluded_platforms` 中沒有 `aiocqhttp`。
2. **回覆來自 AstrBot 內建的模型（語氣明顯改變）。** 請檢視 AstrBot 的記錄檔：
   - `refusing unsafe personagent_url`：外掛程式中的 `personagent_url` 不正確。在同一台電腦上應填入 `http://127.0.0.1:8080`。
   - `agent refused the request (403)`：兩端的 `CONNECTOR_TOKEN` 不一致，或兩台電腦的時鐘相差超過五分鐘。重新執行 `personagent connect astrbot` 會將兩端改為同一個權杖。
   - `timed out waiting for the agent`：模型回應過慢。外掛程式的 `timeout_s` 預設為 420 秒，足以涵蓋 personagent 預設設定下最長的 360 秒；如果調高了 `LLM_TIMEOUT_S`，也須相應調高 `timeout_s`。
   - `agent request failed`：personagent 未在執行，或位址、連接埠填寫有誤。
3. **QQ 私訊被攔下。** 經由 NapCat 傳入的 QQ 私訊，必須來自管理員（`ADMIN_IDS`），或列於 `ACCESS_DM_USERS` 之中。
4. **`QQ_BOT_ID` 未填寫或填寫錯誤。** 此處應填入次要帳號的 QQ 號碼。
5. **遺失了學過的內容。** 經由 NapCat 的 QQ 對話必須設定 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`，缺少此項時，所有 QQ 對話都會被視為新對話。

**NapCat 的 HTTP 服務**為選用項目。開啟後，personagent 可以補回它離線期間遺漏的 @ 訊息。做法是在 NapCat 中開啟 HTTP 服務，並在 `.env` 中寫入 `QQ_ONEBOT_URL=http://127.0.0.1:3000`（連接埠以 NapCat 中的設定為準）和 `QQ_BOT_ID`（次要帳號的 QQ 號碼）。

**舊版直連方式。** NapCat 直接將事件傳送至 personagent 的 `/v1/onebot`，此方式已不再建議使用，但在 1.x 中仍可使用。它要求在 `.env` 中寫入 `QQ_ONEBOT_URL`，否則機器人只能接收而無法回覆，`personagent doctor` 會對此提出提醒。改用 AstrBot 之後，須關閉 NapCat 中指向 `/v1/onebot` 的 HTTP 用戶端，否則每則訊息都會收到兩次。已學到的記憶會保留。

## 部署參考

前文的教學協助你完成初次執行。本節涵蓋長期執行所需的全部資訊：設定、處理程序、介面、錯誤碼和費用。

### 最精簡的可執行設定

本機頁面（`personagent`，或使用 `personagent init --terminal` 的終端機設定精靈）會傳送一個很小的請求以驗證金鑰，然後將 `.env` 寫入主目錄。聊天需要金鑰，`.env.example` 預設使用 OpenRouter 的免費模型：

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

`.env` 中只寫入金鑰時，位址和模型為 `https://api.deepseek.com` 和 `deepseek-flash`。兩者可以指向任何相容 OpenAI 的介面，無論是託管服務或本機服務（Ollama、llama.cpp）皆可。API 位址請依服務商文件貼上，根位址或 `.../v1`、`.../api/paas/v4` 這類帶版本的位址皆可。在你寫好 `persona.txt` 之前，使用的是套件內附的 `data/persona.example.<lang>.txt`。在設定 `PERSONA_NAME` 之前（設定流程會寫入），角色名稱為 "bot"。

頁面還會寫入 `PERSONA_NAME`、`AGENT_LANG` 和一個 `CONNECTOR_TOKEN`。從頁面連接的平台不需要在 `.env` 中另外寫入任何內容。其憑證存放於 `<home>/platforms/`：`direct.json` 儲存 personagent 直接連線的平台，其餘平台由託管的 AstrBot 儲存在其本身的設定中。選用的補充設定：

```
ADMIN_IDS=telegram:12345             # 管理員的帳號，<platform>:<id>
# 只有經 NapCat（OneBot）接 QQ 時才需要
QQ_BOT_ID=...                        # 機器人帳號的號碼
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

金鑰只留在這台電腦上，對話內容會傳送給你選擇的模型服務。`.env.example` 中的其他設定都有可用的預設值。`SERVER_HOST` 和 `SERVER_PORT` 是 `127.0.0.1:8080`，`QQ_ONEBOT_URL` 為空（沒有 NapCat HTTP 服務），`ACCESS_GROUPS` 為空表示所有群組均交由聯結器決定。

### 執行

`personagent` 會開啟本機頁面。頁面開啟期間，它會執行角色服務、直連平台的處理程序，以及已安裝的託管 AstrBot。再次執行 `personagent` 會沿用已開啟的頁面。`personagent up` 會啟動相同的處理程序，但不開啟瀏覽器。

兩種方式下，這些處理程序都會隨它一併結束，無論它以何種方式結束。上次當機遺留的處理程序會在下次啟動時停止。每個處理程序會將記錄檔寫入 `<home>/runtime/desktop/`（`agent.log`、`direct.log`、`astrbot.log`）。

本機頁面和 `personagent up` 每天最多向 pypi.org 查詢一次是否有新版本。有新版本時，「開始聊天」頁面和終端機會顯示適用於目前安裝的更新指令。請求中只包含版本號，`UPDATE_CHECK_ENABLED=false` 可關閉此項檢查。

`personagent run` 只啟動角色服務，見[只啟動服務](guide.zh-TW.md#只啟動服務)。你自己的聯結器（你自行執行的 AstrBot、Satori、Matrix）連接它時請使用此指令。`personagent doctor` 會檢查設定，並探測每個上游服務。

**1.0 變更了設定名稱。** 只要仍設定 1.0 已廢棄的設定名稱，啟動時就會以結束代碼 2 拒絕執行，並逐一列出 `OLD -> NEW`。`personagent doctor --fix` 會修改 `<home>/.env` 中的名稱。它會保留值和註解，將舊檔案儲存為 `.env.bak`；如果新名稱已設定，則將舊的那一行改為註解。寫在環境變數而非 `.env` 中的已廢棄名稱，須至其設定處修改。只要仍有殘留，`personagent doctor` 就會以 1 結束，`--json` 會將其列於 `retired_settings` 之下。`HOST`、`PORT` 和 `LOG_FILE` 僅在寫於 `.env` 中時才會計入。

#### 動態介面

[動態](guide.zh-TW.md#動態)是本機頁面中的一個檢視。它不需要額外安裝，不從網際網路載入任何內容，也從不顯示金鑰或權杖。它讀取本機頁面所啟動之角色服務的 JSON 介面。僅使用 `personagent run` 時，請查看服務記錄檔，並使用 `personagent learned` 和 `personagent memory`。`DASHBOARD_ENABLED=false` 會關閉此介面，此時檢視會說明情況，`personagent doctor` 會輸出 `activity: off (...)`。

介面位於角色服務的 `/api/dashboard/` 下：

- `GET conversations` 和 `GET conversation?id=<chat id>` 讀取服務已知的聊天，以及特定聊天的詳細資料。`conversations` 中的每個聊天帶有 `learned`、`observing`（觀察中的項目數）和 `latest`（最近一次有內容投入使用的時間）。`conversation` 傳回 `learned` 和 `observing` 兩份清單：觀察中的項目帶有 `standing`（所處階段、尚缺的條件、角色的理由，以及將被擱置的日期）；使用中的項目帶有 `by`（`reactions`、`character` 或 `person`）和 `why`。它還會傳回該聊天記住的內容：`memories`、`core_note` 與 `core_at`、`thread`、`episodes`、`removed` 和 `memory_status`。
- `POST candidates/<id>/promote`、`replace`、`reject`、`rollback` 和 `restore` 是人工可選的操作。每次操作都與 `personagent learned` 寫入同一份學習紀錄，操作者記為 `dashboard`。`restore` 可以恢復由角色或時限擱置的內容，以及由角色或規則停止使用的內容；由人工撤銷或擱置的內容、被內容規則捨棄的內容維持不變；`promote` 不能恢復已復原的內容。
- `POST memory/forget` 帶上請求本文 `{"conv": "<chat id>", "kind": "note", "id": "<id>"}`，刪除一項記憶，並傳回 `tid`；將 `{"tid": "<tid>"}` 傳送給 `POST memory/restore` 即可還原。`kind` 可以是 `note`、`episode`、`thread` 或 `core`。原有的請求本文 `{"conv": "<chat id>", "note": "<note id>"}` 仍然可用，未帶 `note` 時刪除該聊天的核心筆記。
- `POST memory/forget_chat` 帶上 `{"conv": "<chat id>"}`，清除該聊天記住的全部內容，無法復原。
- `GET memory/list?conv=<chat id>` 列出各聊天記住的內容以及仍可還原的內容；服務執行時，`personagent memory` 透過它讀取。

每次呼叫都須帶有 `X-Personagent-Dashboard-Token` 請求標頭，其值為執行目錄（預設為 `<home>/runtime/`，除非已由 `AGENT_RUNTIME_DIR` 變更）中 `dashboard.token` 檔案內的權杖。此檔案僅限本人讀取，於服務啟動時產生。未帶此請求標頭的呼叫會收到 401（`dashboard_token`），權杖錯誤則收到 403（`wrong_token`）。`CONNECTOR_TOKEN` 和 `X-Personagent-Token` 無法存取此介面，兩者僅用於聯結器和 `/health/details`。

- 寫入操作還須帶有 `X-Personagent-Dashboard: 1` 和 `Content-Type: application/json`。請求帶有 `Origin` 時，必須是服務本身的位址。
- 跨站的瀏覽器請求一律拒絕。
- 回應中的所有憑證都會替換為 `***`。啟動檢查中的 URL 還會遮蔽使用者名稱、密碼和查詢字串。
- 同一台電腦上的腳本可以採用與本機頁面相同的方式呼叫此介面。

服務本身不提供頁面。`GET /` 會傳回一段簡短說明，指向本機頁面和 `personagent learned`；以往的 `?token=` 連結現在也會開啟這段說明。本機頁面只繫結 127.0.0.1。在沒有本機頁面的伺服器上，可使用 `personagent learned` 檢視角色學到的內容、正在觀察的內容及原因，並可立即啟用、擱置、撤回某項，或恢復由角色或時限擱置、由角色或規則停止使用的內容；`personagent memory` 可列出角色記住的內容，並刪除或還原某一項。

### 主機需求

1. **可寫入的主目錄。** 啟動時會鎖定 `<home>/.personagent.instance.lock`，該檔案位於 `runtime/` 之外。主目錄為唯讀時無法啟動。
2. **每個主目錄僅一個處理程序。** 同一主目錄上的第二個 `personagent run` 會結束，並以一句話說明原因。
3. **可用的連接埠。** 連接埠已被佔用或遭到禁止時也會結束，並以一句話說明原因。請以 `--port` 或 `SERVER_PORT` 改用其他連接埠。

`AGENT_RUNTIME_DIR` 必須解析至主目錄之內，否則啟動失敗。相對路徑的 `PERSONA_FILE` 或 `PERSONA_CARD_FILE` 也以主目錄為基準解析，因此存放於其他位置的人設須使用絕對路徑。

`memory.json`、`core_memory.json` 或 `episodes.json` 損毀時，啟動會以結束代碼 2 停止，並以一句話指出損毀的檔案，以及應換上的 `.bak` 副本。損毀的檔案維持原樣。

### 連接平台

在本機頁面的「連接平台」中新增平台。personagent 在儲存之前會先向平台驗證憑證。平台拒絕時，頁面會顯示拒絕原因，且不保留任何內容。

在沒有顯示器的伺服器上，可以在終端機中使用 `personagent connect <平台>` 連接 personagent 直接連線的平台，例如 `personagent connect telegram`。此指令執行與頁面相同的步驟和驗證，並以相同的格式儲存。QQ 和微信會在終端機中顯示 QR 碼，Twitch 會顯示一個連結和一組代碼。加上 `--no-input` 並以參數提供全部內容時，指令不會提出任何詢問；缺少必填項目時以結束代碼 2 結束。接著執行 `personagent up`，即可啟動 personagent 及其已連接的平台。[此指令及其參數](guide.zh-TW.md#在終端機中連接平台)的說明請參閱使用手冊。

**由 personagent 直接連線。** QQ、個人微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 執行於同一個「直連」處理程序中，不需要 AstrBot 和 NapCat。某個平台無法載入時會被略過，其餘平台仍會正常啟動。下表列出前四個平台；其餘六個平台需要填寫的內容與使用限制，請參閱使用手冊中的[personagent 直接連線的平台](guide.zh-TW.md#personagent-直接連線的平台)。

| 平台 | 操作方式 | 限制 |
|---|---|---|
| QQ（官方機器人） | 使用手機 QQ 掃描，新建機器人或選擇你已建立的機器人。替代方式是貼上 AppID 和 AppSecret。 | 通過認證之前，QQ 只允許它加入你擔任群主的群組。在群組中預設只會收到 @ 它的訊息，群主可以在該群組的機器人資料頁開啟「接收全量訊息」；開啟之前它無法主動插話。 |
| 個人微信 | 使用微信掃描（騰訊的 iLink 機器人介面）。 | 僅限一對一聊天。微信不會將群組訊息轉交給這類機器人。 |
| Telegram | 貼上 @BotFather 提供的 Token。 | |
| Discord | 貼上機器人 Token，並開啟 Message Content Intent。 | |

**透過託管的 AstrBot。** 其他平台都經由 personagent 下載的 AstrBot（連同其專用的 Python 3.12 執行環境）連接，並在背景執行。它沒有網頁管理後台，也不需要另外登入。KOOK、飛書（長連線）、釘釘（Stream 模式）、Slack（Socket Mode，指南連結會預先填好應用程式設定）、企業微信智慧機器人（長連線）、Mattermost 和 Misskey 只需填寫一至兩項。「進階」分組需要公開網址或其他軟體：企業微信應用、微信公眾號、QQ Webhook、OneBot v11（NapCat）和 Satori。不提供 LINE。

兩種方式下，已連接的平台都會回應平台轉交給機器人的每個群組與私訊。一旦 `ACCESS_GROUPS` 或 `ACCESS_DM_USERS` 列出該平台的項目，情況即有所不同（請參閱[personagent 本身的允許清單](#透過你已在執行的-astrbot)）。ID 以 `<platform>:<id>` 的形式傳入，例如 `qq_official:<openid>`、`weixin_oc:<id>`、`telegram:<id>` 和 `discord:<id>`。QQ 官方機器人看到的是 openid，而非 QQ 號碼。直接連線某個平台時，會移除同一平台的 AstrBot 連線。

### 透過你已在執行的 AstrBot

AstrBot、NapCat（OneBot）、Koishi（經 [Satori 聯結器](../integrations/satori/README.zh-TW.md)）和 Matrix（經 [Matrix 聯結器](../integrations/matrix/README.zh-TW.md)和 mautrix 橋接）是 personagent 可以搭配使用的第三方橋接程式。連接 personagent 直接連線的平台時均不需要它們。

AstrBot 透過 `integrations/astrbot/astrbot_plugin_personagent/` 中的外掛程式將訊息交給 personagent。外掛程式將每則訊息傳送至 `POST /v1/events`，並轉送回應中的回覆。它也會拉取 personagent 的 outbox（`outbox_enabled`，預設開啟），因此在平台允許機器人主動發言之處，角色可以先開口。外掛程式說明中有詳細的表格。託管的 AstrBot 會自動安裝外掛程式。使用你自己的 AstrBot 時，請先啟動一次以產生 data 資料夾（其中包含 `cmd_config.json`、`plugins/` 和 `config/`），然後執行：

```
personagent connect astrbot                       # 詢問，並自行查詢 AstrBot 的資料夾
personagent connect astrbot <AstrBot data dir>    # 不詢問
```

此指令會將外掛程式複製到 `<data dir>/plugins/`，並將同一個 `CONNECTOR_TOKEN` 寫入 `.env` 和外掛程式設定。它會將 `personagent_url` 設為 `http://127.0.0.1:<SERVER_PORT>`，除非外掛程式已有可接受的位址（本機位址，包括通道，或 HTTPS）。

AstrBot 位於另一台機器時，請從[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下載 `astrbot_plugin_personagent.zip`，在 AstrBot 外掛程式頁面的「從檔案安裝」中上傳。將其 `connector_token` 設為 personagent `.env` 中的 `CONNECTOR_TOKEN`，並將 `personagent_url` 設為 personagent 的 HTTPS 位址（請參閱[對外開放服務位址](#對外開放服務位址)）。

升級 personagent 後，請重新執行 `connect astrbot` 或上傳新的 zip。AstrBot 4.29 及以後的版本會取代已安裝的副本。更早的版本須先解除安裝，解除安裝時請勿勾選「同時刪除外掛程式設定檔」。

`connect astrbot` 的選項：

- `--qq` 把 `aiocqhttp` 從 `excluded_platforms` 中移除，`--no-qq` 會將其加回。兩者皆未指定時，QQ 路由維持不變。`CONNECTOR_QQ_PLATFORMS` 會依外掛程式的最終行為設定。
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>` 會同時在 AstrBot 本身的設定中開啟該配接器。Slack 另需 `--app-token`，飛書和 QQ 需要 `--app-id` 和 `--app-secret`。既有的配接器項目會保留其他設定（代理伺服器、基礎位址、輪詢），只更新憑證。
- `--url https://...` 設定外掛程式傳送請求時使用的 HTTPS 位址。
- `--install` 改為下載託管的 AstrBot，`--start` 則將其啟動。

首次執行時允許清單為空。再次執行會保留允許清單，以及其他已排除的平台。

外掛程式預設拒絕所有訊息。請在 AstrBot 網頁中填寫 `groups`，私訊則填寫 `dm_users`，或回答 `connect` 的提問。`dm_users` 不為空時才會轉送私訊。[外掛程式說明](../integrations/astrbot/astrbot_plugin_personagent/README.zh-TW.md)列出了所有設定項目。託管的 AstrBot 會以 `<platform>:*` 開放你連接的每個平台。安裝外掛程式後，請重新啟動 AstrBot 或在網頁中重新載入外掛程式。在 personagent 端：

- `CONNECTOR_TOKEN` 用於驗證每個請求。請求帶有 `X-Personagent-Token` 請求標頭，另附以權杖為金鑰、對 `timestamp.nonce.body` 計算的 HMAC-SHA256，防重送機制會拒絕重複的 nonce。遭攔截的請求無法重送或竄改。權杖同時也是簽章金鑰，因此不得寫入記錄檔，外洩後須更換。同一主機上為選用，跨主機時必須設定。
- `ADMIN_IDS` 以 `<platform>:<id>` 列出管理員的帳號（`telegram:12345`、`discord:4242`）。不帶前綴的 ID 或 `qq:<id>` 為 QQ 號碼。`ADMIN_NAME` 設定管理員的稱呼。所列的帳號均屬於同一人，此人在群組與私訊中會得到較親近的對待，可以管理機器人記住的群組內容，也可以獨自教導它。經由 AstrBot 時，平台名稱為 AstrBot 顯示的配接器名稱，在聊天中傳送 `/sid` 即可查看 ID。
- `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 讓 personagent 自行管控各平台，格式同為 `<platform>:<id>`。每個平台分別管控。沒有項目的平台交由聯結器決定；只要有一個項目，該平台就只開放所列的項目。personagent 拒絕的回合不會被接管，因此 AstrBot 內建的模型可能會回覆。

AstrBot 位於 Docker 中或另一台主機上時，請參閱[使用手冊](guide.zh-TW.md#你自己執行的橋接)。

#### 透過 NapCat（OneBot）接入 QQ

此方式以個人 QQ 帳號取代官方機器人。你需要一個已在目標群組中的 QQ 次要帳號，請勿使用自己的主要帳號（請參閱 [DISCLAIMER.zh-TW.md](DISCLAIMER.zh-TW.md)）。該帳號登入一個 OneBot v11 實作（通常以掃描登入，工作階段在重新啟動後仍會保留），該實作再連接 AstrBot 的 `aiocqhttp` 配接器。[NapCat](https://github.com/NapNeko/NapCatQQ) 已經過測試，它附加於 QQ NT 桌面用戶端之上。LLOneBot 和 Lagrange 是其他的 OneBot v11 實作。

使用託管的 AstrBot 時，請在本機頁面新增「進階 → OneBot v11（NapCat）」，並讓 NapCat 指向 `ws://127.0.0.1:6199/ws`。[第三方路線](#第三方路線astrbot--napcat)一節有逐步說明。使用你自己的 AstrBot 時，請從外掛程式的 `excluded_platforms` 移除 `aiocqhttp`，設定 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`（`--qq` 會同時完成這兩項），並設定 `QQ_BOT_ID`（`personagent connect astrbot` 會詢問）。

**此處必須設定 `CONNECTOR_QQ_PLATFORMS`。** 未設定時，QQ ID 會帶著命名空間（`aiocqhttp:123456`）傳入，每個對話都會被視為新對話。記憶、歷史和學到的範例都以不帶前綴的 ID 為鍵，學習紀錄的資料列 ID 也由對話 ID 衍生，因此這種分裂事後無法修復。

不帶前綴的 ID 具有 QQ 權限，因此 `ADMIN_IDS`、`ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 的 QQ 項目會在外掛程式允許清單之外繼續生效。QQ 私訊必須列於 `dm_users` 中，*且*來自管理員或 `ACCESS_DM_USERS` 的項目。`ACCESS_GROUPS` 列出 QQ 群組時，該群組必須同時列於兩端。只有在信任某個聯結器擁有此權限時，才將其平台列入 `CONNECTOR_QQ_PLATFORMS`。

**NapCat 的 HTTP 服務**（`QQ_ONEBOT_URL`，預設為空）在此方式下為選用項目。personagent 也會主動傳送訊息：

- 主動訊息（`PROACTIVE_ENABLED`，預設關閉）；
- 被否定兩分鐘後的追問（`REACT_ELICIT_ENABLED`）；
- 模型呼叫失敗時在群組中傳送的致歉。

外掛程式拉取 outbox 時，這些訊息會經由外掛程式的 outbox 送出。未拉取時，如果設定了 `QQ_ONEBOT_URL`，則傳送至該位址。只有補回離線期間遺漏的 @ 才需要此服務，且同時需要 `QQ_BOT_ID`。此項掃描在啟動時執行，之後每 30 分鐘執行一次。它涵蓋 `ACCESS_GROUPS` 中的 QQ 群組，以及上次重新啟動後有訊息的群組，並重新處理一小時內的 @。位址為空時，`personagent doctor` 會將 OneBot 橋接顯示為 "not configured"。

**所有聯結器方式均不提供的功能**（直連、AstrBot 或其他聯結器），無法透過任何設定恢復：

- 針對未經視覺模型描述之圖片的 OCR 備用方案；
- 經由 NapCat 查詢引用。引用改由 personagent 本身的近期訊息索引，以及聯結器隨引用傳送的被引用文字解析。

所有路徑都會收集新的表情圖片，與 QQ 相同：來源是群組中傳送、直接附帶圖片或標為表情的圖片。聯結器僅以連結形式傳送的照片不會被收集。

### 同時連接多個平台

多個聯結器可以同時連接同一個 personagent，因為每個聯結器都會標明自己的平台（`telegram:-1001234`、`matrix:!room:example.org`）。直連處理程序、AstrBot、Satori 和 Matrix 可以同時執行。請勿讓同一個聊天經由兩個聯結器傳入，否則每則訊息都會收到兩次。帶命名空間的 ID 不會與不帶前綴的 QQ 號碼衝突。

非由請求觸發的訊息，會經由拉取 personagent outbox 的聯結器送達平台。這些訊息包括主動開場、被否定後的追問，以及群組中模型呼叫失敗時的致歉。私訊的致歉則隨帶來該訊息之請求的回應傳回。

直連處理程序和此處的三個聯結器都會拉取 outbox，前提是平台允許機器人主動發言。QQ 會限制官方機器人主動傳送訊息的頻率，使用者也可以關閉這類訊息。你自己的聯結器應在事件中傳送 `connector_id`、`reply_handle` 和 `"capabilities": ["outbox"]`，並長輪詢 `/v1/outbox`（請參閱[聯結器協定](connectors.zh-TW.md)）。沒有此類聯結器時，personagent 只能在帶來訊息的請求中回覆。主動發言迴圈會略過這些對話，追問和致歉也不會傳送。

本機頁面也會拉取 outbox，但僅限其自身的對話。不拉取 outbox 的程式（例如在某個對話中發言的程式設計助理）所傳送的事件，不會使拉取 outbox 的聯結器失去該對話（請參閱[聯結器協定](connectors.zh-TW.md#outboxpost-v1outbox)）。

`PROACTIVE_PLATFORMS` 限制主動發言迴圈可以主動開口的平台。`PROACTIVE_PLATFORMS=qq_official` 限定於 QQ 官方機器人，`qq` 限定於經由 NapCat 的 QQ。`CONNECTOR_OUTBOX_ENABLED=false` 會完全關閉 outbox。

如需不經 outbox 在私訊中主動開口，你自己的排程程式（AstrBot 外掛程式任務、cron 項目）可以傳送標記了 `"proactive": true` 的私訊事件。請參閱[不經 outbox 主動發言](connectors.zh-TW.md#不經-outbox-主動發言)。

### 對外開放服務位址

聯結器和 personagent 位於同一台機器時，請保持 `SERVER_HOST=127.0.0.1`。容器只有在共用主機的網路命名空間或使用主機網路時，才視為同一台機器。本機頁面和 `personagent up` 一律繫結 `127.0.0.1`。其他情況下：

1. 設定 `SERVER_HOST=0.0.0.0`（或 `--host 0.0.0.0`）和 `CONNECTOR_TOKEN`。未設定權杖時，啟動會拒絕繫結網路位址。此處不要求 `QQ_ONEBOT_SECRET`，但未設定時，已棄用的 `/v1/onebot` 在網路繫結下會關閉。傳送至該端點的每個請求都會收到 403 `onebot_disabled`，記錄檔會說明一次原因。
2. 在前端部署 HTTPS 反向代理伺服器或私人通道。此處的每個聯結器都只會向本機位址或已設定權杖的 HTTPS 位址傳送。AstrBot 外掛程式會將其他情況記錄為 `refusing unsafe personagent_url`，Satori 和 Matrix 聯結器則會拒絕啟動。
3. 保持請求本文逐位元組不變，因為簽章涵蓋請求本文；並讓兩端時鐘相差不超過五分鐘。

憑證為空時，對應的介面只為直接呼叫 `http://127.0.0.1` 或 `http://localhost` 的本機程式提供服務。請求只要帶有下列任何一項，就會收到 403 `non_local_request`：

- `Origin` 請求標頭；
- 不是 `none` 的 `Sec-Fetch-Site`；
- 不是 `localhost`、`127.0.0.1` 或 `::1` 的 `Host`；
- 代理伺服器請求標頭：`X-Forwarded-For`、`Forwarded`、`X-Real-IP`、`CF-Connecting-IP`、`Via`、`X-Forwarded-Host`、`X-Forwarded-Proto`、`X-Forwarded-Port`、`True-Client-IP`、`X-Client-IP` 或 `X-Original-Forwarded-For`。

同一主機上不加入這些請求標頭的代理伺服器，其請求看起來仍與本機請求相同。在加入任何代理伺服器或通道之前，請先設定 `CONNECTOR_TOKEN`（使用 `/v1/onebot` 時還需 `QQ_ONEBOT_SECRET`），即使位於同一台主機上亦然。

### 健康檢查介面

- `GET /health` 免費、公開，不呼叫任何服務。
- `GET /health/details` 探測上游服務（快取 60 秒）。`CONNECTOR_TOKEN` 為空時，只回應本機請求。設定了權杖時，它**只**回應帶有相符 `X-Personagent-Token` 請求標頭的請求，來自本機的請求亦然。關鍵探測失敗或無法執行時傳回 503。關鍵探測包括聊天模型，以及 QQ 使用 OneBot 直連入口時的 OneBot 橋接（設定了 `QQ_BOT_ID` 和 `QQ_ONEBOT_URL`，未設定 `CONNECTOR_QQ_PLATFORMS`）。
- `personagent doctor [--json]` 執行相同的探測和設定檢查，並在相同情況下以非零代碼結束。距上次更新檢查已超過一天時，它還會向 pypi.org 查詢最新版本（`UPDATE_CHECK_ENABLED=false` 可跳過）。

### 費用

- **探測會產生費用。** `personagent doctor` 和 `/health/details` 會向角色實際呼叫的每個模型傳送一個很小的聊天請求：群組和私訊回覆、網路搜尋判斷、反應判斷（`REACT_LEARN_ENABLED` 開啟時）、自我審查（`EVAL_ENABLED` 開啟時）和視覺。設定了 `EMBEDDING_MODEL` 時還會傳送一次嵌入請求，設定了 `TAVILY_API_KEY` 時還會進行一次 Tavily 搜尋。`/health` 以及設定和學習紀錄檢查均為免費。
- **模型用量會被統計。** 每次模型請求都按模型、按日統計，依據是服務方回傳的用量，服務方提供費用時一併記錄。`personagent doctor` 輸出今日與近 7 日的用量，本機頁面的「應用程式」頁面也顯示相同的數據。統計檔案在背景寫入，每分鐘最多一次，停止執行時再寫入一次。
- **學習與記憶。** 角色每次自行判斷學習項目時，呼叫一次 `PROMOTE_JUDGE_MODEL`，每隔 `PROMOTE_JUDGE_INTERVAL_S` 最多 `PROMOTE_JUDGE_BATCH` 次。記憶整理每處理一段聊天呼叫一次 `LLM_JUDGE_MODEL`，每個聊天每天最多 16 次，所有聊天合計每天不超過 `MEMORY_CALLS_PER_DAY`（40）次。設定 `PROMOTE_JUDGE_ENABLED=false` 和 `MEMORY_CALLS_PER_DAY=0` 即可分別關閉。
- **`tools/` 中的腳本**各不相同，部分免費，部分會呼叫模型。[tools.zh-TW.md](tools.zh-TW.md) 的表格逐一註明。
- **`personagent eval`** 對每個測試案例都會呼叫模型，`memory` 測試集除外：它以預設的回答離線執行。人設和學習兩組測試案例還需要第二個模型擔任裁判（`BENCH_JUDGE_MODEL`）。
- **記憶。** 帶命名空間（非 QQ）的對話超過 256 個時，閒置最久的對話會從記憶體中移除，並失去待處理的反應。移除前會先整理其尚未整理的訊息；除非設定 `MEMORY_KEEP_RECENT=false`，其近期訊息會在 `runtime/recent.json` 中保留 72 小時。事實、事件、核心筆記和學習紀錄會保留。正在處理請求的對話不會被清除。長期記憶在啟動時從磁碟載入，不受此上限限制。
- **磁碟。** `runtime/` 中的證據記錄檔和候選項目記錄檔只會追加，從不截斷。任一檔案超過 50 MB 時，`personagent doctor` 會加以標示（`LEDGER_EVIDENCE_WARN_BYTES`、`LEDGER_CANDIDATES_WARN_BYTES`）。記憶檔案始終較小：`recent.json` 只保存最近 72 小時內活躍的聊天，`memory_trash.jsonl` 中被移除的內容最多保留 30 天。每天第一次修改之前，`memory.json`、`core_memory.json` 和 `episodes.json` 會複製為同名的 `.bak` 檔案；本版本首次啟動時，會將舊的記憶檔案保留為 `memory.json.pre-v2`。使用「清除此聊天的記憶」或在聊天中要求忘記之後，`.bak` 副本會依目前的檔案重新寫入，`memory.json.pre-v2` 也會刪去被忘記的內容，因此 `runtime/` 中不會留下任何副本；但先前製作的備份仍保有這些內容。請備份 `runtime/`，因為機器人學到和記住的所有內容都在其中。

### 完整排查清單

這是[機器人未回覆](#機器人未回覆)的完整版，最常見的原因列於前面。本機頁面執行角色服務時，[動態](guide.zh-TW.md#動態)會顯示訊息是否送達、它為何沒有發言。在伺服器上，請查看服務記錄檔，學到的內容請以 `personagent learned` 檢視，記住的內容請以 `personagent memory` 檢視。

1. **訊息未送達。** 在本機頁面確認平台顯示為「已連接」，並查看 `runtime/desktop/direct.log` 或 `astrbot.log`。QQ 官方機器人必須在群組中，它可收到哪些群組訊息由 QQ 決定。個人微信機器人無法接收群組訊息。在你自行執行的 AstrBot 中，請填寫外掛程式的 `groups`（私訊填寫 `dm_users`），使用 NapCat 時還須將 `aiocqhttp` 從 `excluded_platforms` 中移除。Satori 和 Matrix 聯結器在各自的 `.env` 中有獨立的允許清單，請參閱其 README。在此情況下，聊天不會出現在「動態」中。
2. **角色服務未啟動。** `personagent run` 的啟動資訊會顯示 `agent: OFF`，並說明原因和解決方式。未設定 `LLM_API_KEY` 時，請在本機頁面新增金鑰（或設定 `LLM_API_KEY`）並重新啟動。`AGENT_ENABLED=false` 時，請在 `<home>/.env` 中改為 `true` 並重新啟動。在此之前，每個事件都會收到 `owned: false`，第一個事件會記錄一行內容相同的 ERROR。
3. **AstrBot 內建的模型代為回覆。** 外掛程式已改用備用方式，原因是請求失敗、personagent 拒絕了此訊息（第 5 項），或角色服務未啟動（第 2 項）。AstrBot 的記錄檔會顯示 `refusing unsafe personagent_url`、`agent refused the request (403): <message>`（或其他狀態，請參閱下表）或 `timed out waiting for the agent`。`timeout_s` 必須涵蓋防彈跳時間和回合內的模型呼叫，還須計入訊息抵達時仍在思考的那一回合。無論群組或私訊，一個回合的所有模型呼叫共用 1.5 × `LLM_TIMEOUT_S`，因此請讓 3 × `LLM_TIMEOUT_S` 低於此值。其預設值（420）涵蓋角色服務的預設值（3 × 120 = 360 秒）。調高 `LLM_TIMEOUT_S` 時也須一併調高此值。
4. **未點名它。** 在群組中，它會回應自己的名稱（`PERSONA_NAME`）或 @。其他情況下，它要等訊息累積足夠（`CHAT_TRIGGER_COUNT`，預設 30 則）才會考慮發言，且仍可能不發言。在其所在時區的 02:00 至 07:00，它大多不參與未點名它的聊天。時區由 `PERSONA_TZ_OFFSET_HOURS` 設定。留空時，`AGENT_LANG` 為 `zh` 或 `zh-TW` 時採用 UTC+8，其他語言採用本機時區。personagent 啟動後，在某個平台的第一則訊息到達起兩分鐘內，距傳送時已超過 10 分鐘才到達的群組訊息視為積壓訊息：只作為上下文保留，不予回覆，服務記錄檔會加以記錄。「動態」會顯示近期每個回合的原因。如需離線觀察相同的判斷，請執行 `personagent chat --trigger 4`。
5. **personagent 本身的允許清單。** `ACCESS_GROUPS` 和 `ACCESS_DM_USERS` 在每種方式下均會生效，不帶前綴 ID 的 QQ 私訊還須來自管理員或列有項目。被攔下的訊息不會被接管，因此經由 AstrBot 時，其內建的模型可能會回覆。personagent 會對每個被拒絕的對話以 INFO 記錄一次，並註明拒絕它的設定。
6. **模型呼叫失敗。** 金鑰遭拒（401 或 403）或餘額耗盡（402 或配額用盡）時，會記錄一行 ERROR，註明服務商主機和應修改的設定。執行 `personagent doctor`，它會向每個模型介面傳送一個很小的請求並顯示狀態，也能找出錯誤的 `LLM_BASE_URL` 或 `LLM_MODEL`。主模型逾時或連線中斷，且 `LLM_FALLBACK_MODEL` 指定了不同的模型時，本次呼叫會立即改用備用模型，因此本回合仍能在時限內作答。服務方在正常回應中傳回的錯誤（如 OpenRouter 的上游故障）依相應的 HTTP 錯誤處理。模型無法使用期間，角色被點名時會傳送一句符合人設的簡短致歉，每個對話每五分鐘最多一次；「動態」會將這一回合標為「模型未作出回應」。
7. **設定名稱有誤。** 啟動記錄檔和 `personagent doctor` 會列出 `.env.example` 無法識別的所有鍵，以及任何以 `#` 開頭的值。
8. **`.env` 含有 BOM。** 第一項設定的名稱帶有 BOM，因此程式無法讀取該設定。啟動時和 `personagent doctor` 都會回報此問題。請將檔案重新儲存為不含 BOM 的 UTF-8。
9. **使用 NapCat 時 `QQ_BOT_ID` 未設定或有誤。** 經由 AstrBot 時 @ 仍然有效，但補回遺漏的 @ 需要依靠它比對。在 OneBot 直連入口上，@ 永遠無法被識別：機器人正常啟動，不記錄任何內容，也從不回應。`QQ_BOT_ID` 為空但設定了其他 QQ 設定時，`personagent doctor` 會發出警告。QQ 官方機器人不使用此設定。
10. **可以回覆，但遺失了學過的內容。** 原因可能是 NapCat 的 QQ 訊息傳入時未設定 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`，或 `PERSONA_NAME`、`PERSONA_VERSION` 已變更，後者會建立一個新角色。舊角色已生效的內容被整體拒絕時，記錄檔會發出警告。修改 `persona.txt`（包括在頁面的「人設」欄位中修改）不會建立新角色。同一 `PERSONA_VERSION` 下的各次修訂共用學習範圍（`runtime/persona_lineage.json`）。如需併入在譜系未列出之人設雜湊下學到的資料列，請執行 `personagent learned lineage adopt <hash>`，再執行 `personagent learned rebuild`。雜湊位於 `personagent learned show <id>` 所顯示的候選範圍中。在中文和其他語言之間切換 `AGENT_LANG`，也會切換至 `runtime/` 中的另一組學習檔案。

下表列出 `/v1/events` 的錯誤。AstrBot 外掛程式會記錄訊息，`code` 是用戶端可據以判斷處理方式的固定欄位。

| 狀態 | `code` | AstrBot 記錄檔中的訊息 | 原因 |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | 未設定 `CONNECTOR_TOKEN`，且呼叫端不在這台機器上 |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | 未設定 `CONNECTOR_TOKEN`，且請求來自瀏覽器、代理伺服器或其他主機名稱 |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | 權杖、請求標頭或簽章缺漏或錯誤，時鐘相差超過 5 分鐘，nonce 重複，或防重送機制已滿（角色服務記錄檔中有 `connector replay guard full`） |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` 與目前時間相差超過 `CONNECTOR_MAX_EVENT_AGE_S`（24 小時），包括未來時間或以毫秒表示的時間戳記 |
| 400 | `invalid_schema` | invalid event schema | 缺少必填欄位：`platform`、`conversation_type`、`sender_id`、`message_id`、`sent_at`，群組另需 `conversation_id` |
| 400 | `client_disconnected` | client disconnected | 呼叫端在傳送時中斷連線 |
| 408 | `body_timeout` | request body not received in time | 請求本文超過 30 秒仍未送達 |
| 413 | `body_too_large` | request body too large | 超過 `SERVER_MAX_BODY_BYTES`（8 MB），通常是因為內嵌圖片 |
| 429 | `capacity_exceeded` | webhook capacity exceeded | 進行中的回合超過 `CONNECTOR_MAX_INFLIGHT`；請於 3 秒後重試 |

### 舊版方式：OneBot 直連入口

NapCat 的 webhook 仍可將事件傳送至 `POST /v1/onebot`，personagent 再經由 `QQ_ONEBOT_URL` 回覆。此方式已棄用，於 1.x 中保留。請改用 QQ 官方機器人連線，或經由 AstrBot 使用 NapCat 並設定 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`。此方式在首次使用時會發出一次警告，並在每個回應中標記 `Deprecation: true`。

如需遷移至經由 AstrBot 的 NapCat，請在本機頁面新增 OneBot v11（NapCat），或為你自己的 AstrBot 執行 `personagent connect astrbot <AstrBot data dir> --qq` 並填寫允許清單。讓 NapCat 的 WebSocket 用戶端指向它，並關閉 NapCat 的 HTTP 用戶端（保留 HTTP 服務）。記憶和學習內容會延續，因為 `CONNECTOR_QQ_PLATFORMS` 會維持 ID 不變。

如果仍在使用舊版方式：

- 按 [NapCat 文件](https://napneko.github.io/)設定雙向連線。你需要一個位於 `QQ_ONEBOT_URL` 的 **HTTP 服務**用於傳送，以及一個向 `http://127.0.0.1:8080/v1/onebot`（`SERVER_HOST`、`SERVER_PORT`）傳送的 **HTTP 用戶端**。`QQ_ONEBOT_URL` 預設為空，因此須寫入 `.env`，否則機器人只能接收而無法回覆。此方式看似已設定（設定了 `QQ_BOT_ID` 或 `QQ_ONEBOT_SECRET`，`CONNECTOR_QQ_PLATFORMS` 為空）但 `QQ_ONEBOT_URL` 為空時，啟動檢查和 `personagent doctor` 會發出警告。
- NapCat 位於另一台機器時，請將 `QQ_ONEBOT_SECRET` 設為 HTTP 用戶端的 `secret`。否則任何能存取此連接埠的人都能偽造事件。請求本文必須帶有 `x-signature: sha1=<hex>`（否則 403 `bad_signature`），時間戳記偏差超過五分鐘的事件會收到 403 `stale_event`。未設定此金鑰時，此方式只回應本機程式，在網路繫結下會關閉（403 `onebot_disabled`）。
- 同一帳號同時連接 AstrBot 時，請將 `aiocqhttp` 保留在 `excluded_platforms` 中，否則每則訊息都會收到兩次。

用 `curl http://127.0.0.1:3000/get_login_info` 檢查傳送功能。向機器人所在的群組傳送訊息，同時觀察 personagent 的記錄檔，以檢查接收功能。

## 其他文件

- [AstrBot 外掛程式說明](../integrations/astrbot/astrbot_plugin_personagent/README.zh-TW.md)
- [免責宣告](DISCLAIMER.zh-TW.md)
