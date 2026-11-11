# 開始使用 personagent

[English](start.md) · [简体中文](start.zh-CN.md) · 繁體中文 · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · [Français](start.fr.md) · [Deutsch](start.de.md) · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · [完整手冊](guide.zh-TW.md)

## 開啟應用程式

從 PyPI 安裝後開啟：

```sh
python -m pip install personagent
personagent
```

若已安裝 [uv](https://docs.astral.sh/uv/)，`uvx personagent` 無須另行安裝即可執行。

在 Windows 上，頁面會在獨立的視窗中開啟。在 macOS 和 Linux 上，頁面會在瀏覽器中開啟；執行 `pip install "personagent[app]"` 之後，也可以在視窗中開啟。

也可以交由 AI 程式設計助理處理：請它閱讀 [setup-for-agents.md](setup-for-agents.md)，再由它完成 personagent 的安裝與設定。

在 Windows 上，也可以下載原始碼 ZIP，解壓縮後按兩下 `start.bat`。它會在資料夾中建立專用的 Python 環境，再開啟同一個本機頁面。首次執行時，還會在桌面和「開始」功能表中新增 personagent 圖示。

從 Git 儲存庫執行時，請為它另建一個虛擬環境：先執行 `python -m venv .venv`，再執行 `.venv/bin/python -m pip install -e .` 和 `.venv/bin/python -m persona_agent`。Windows 上的直譯器是 `.venv\Scripts\python.exe`，也可以直接按兩下 `start.bat`。

## 填入金鑰，開始聊天

選擇模型服務，填入 API 金鑰，再點選「驗證並開始聊天」。預設選取的是 OpenRouter 的免費模型和「溫和的傾聽者」這個角色。此金鑰不需付費，每天限 50 次請求。模型名稱和服務位址位於「進階設定」中，角色的名稱和個性位於「變更角色名稱或個性」中。

金鑰只儲存在本機，點選「顯示」即可核對。聊天訊息會傳送至你選擇的模型服務，並依該服務的一般價格計費。

角色會直接在頁面中回覆，其傳送的貼圖和圖片也會顯示在頁面中。角色之後傳送的訊息（例如其主動發起的訊息）會在數秒內顯示在對話中。設定會自動儲存，下次開啟時將直接進入聊天。

設定完成後，「角色與設定」中有一個「人設」欄位，內容即為角色目前使用的人設。修改角色的身分與說話方式後點選「儲存人設」，變更將立即生效，角色已學到的內容也會保留。

其下方是「更多功能」，可以開啟網路搜尋、辨識圖片和偶爾主動發言。網路搜尋預設使用 DuckDuckGo，填入 Tavily 的金鑰可提升穩定性。再往下的「進階設定」集中了以往只能在 `.env` 中修改的設定。連接第一個平台之前，「開始聊天」頁面上方會顯示「開始使用」提示。

另有兩個檢視無須連接平台即可使用。「演練」會播放預先編寫的示範，並提供一個模擬群組，讓你查看角色回覆或保持沉默的原因。「應用程式」會逐項檢查角色所依賴的服務、顯示執行記錄，並提供版本更新、備份與桌面圖示等功能。

「動態」顯示角色所在的聊天、近期的發言、記住的內容以及學到的內容。學習什麼由角色自行決定，記憶也由角色自行保持最新，其中沒有任何內容需要你處理。你仍然可以撤銷角色學到的任何內容，也可以刪除或還原它記住的任何內容。

## 接入其他平台

1. 點選「連接平台」，選擇一個平台。連接後，角色會回覆該平台上的群組與私訊。
   - **掃描連接**：QQ 和個人微信。點選「取得 QR 碼」，然後在手機上確認。
     - QQ：使用手機 QQ 掃描。QQ 會新建一個機器人，或讓你選擇既有的機器人，金鑰由 personagent 自動取回。如果機器人是你自行在 [QQ 官方頁面](https://q.qq.com/qqbot/openclaw/login.html)建立的，請點選「改為手動填寫」，填入 AppID 和 AppSecret。
     - 微信：使用微信掃描。微信不會將群組訊息轉送給這類機器人，因此它僅限私訊。
   - **填寫一至兩項**：Telegram（向 @BotFather 申請 Token）、Discord（機器人 Token，並開啟 Message Content Intent）、KOOK、飛書、釘釘、Slack、企業微信智慧機器人、Mattermost、Misskey、Matrix、Twitch、IRC、Zulip、VK 和 Stoat。頁面會註明需要從平台後台複製哪幾項，其餘設定均使用預設值。Twitch 另需透過一個連結核准登入。
   - **進階**：企業微信應用、微信公眾號和 QQ（Webhook）需要一個可轉送至回呼連接埠的公開網址；OneBot v11（NapCat）和 Satori 需要在本機另外執行相應的軟體。
2. QQ、微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 由 personagent 直接連線。其他平台透過第三方橋接程式 AstrBot 接入。首次連接這類平台時，personagent 會下載 AstrBot 和一個獨立的 Python 3.12 執行環境，下載完成前請保持頁面開啟。之後 AstrBot 會在背景執行，不需要另外登入管理後台。
3. 儲存之前，personagent 會先向平台驗證憑證。平台拒絕時，頁面會顯示提示，且不會儲存任何內容。
4. 已連接的平台會列在「連接平台」頁面頂端，可在該處重新設定或中斷連線。
5. 不使用頁面時（例如在沒有顯示器的伺服器上），可以在終端機中執行 `personagent connect <平台>`，連接 QQ、微信、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 或 Stoat，操作步驟和驗證方式與頁面相同。單獨執行 `personagent connect` 會列出這些平台。此指令的說明請參閱[完整手冊](guide.zh-TW.md#在終端機中連接平台)。

QQ 機器人連接完成後，可在手機 QQ 的「聯絡人 → 機器人」中找到它，既可以私訊，也可以將它加入你擔任群主的群組。此方式使用 QQ 官方機器人平台，不需要個人 QQ 次要帳號，也不需要安裝其他軟體。機器人可以加入哪些群組由 QQ 決定：通過認證之前，它只能加入管理員擔任群主的群組，也不需要設定沙箱。在群組中，它預設只會收到 @ 它的訊息，群主可以在該群組的機器人資料頁開啟「接收全量訊息」。認證及其他帳號相關事項，請參閱 [QQ 機器人官方指南](https://bot.q.qq.com/wiki/bot_new_product-intro/)。

QR 碼過期後可以重新取得；下載失敗時可以重試，無須重新填寫模型設定。連接某個平台時，只會對該平台的群組與私訊開放，其他配接器仍沿用原有的群組與私訊限制。目前不提供 LINE，因為 AstrBot 只能透過其管理後台接收 LINE 的回呼，而 personagent 不會執行該後台。

## 再次使用

再次開啟 personagent 即可。設定會保留，已連接的平台會自動恢復。如果它已在執行，再次開啟會將其視窗移至最前方。使用期間請保持它開啟：無論是點選「結束」還是關閉視窗，它啟動的處理程序都會一併結束；意外當機後殘留的處理程序會在下次啟動時清除。在 Windows 上，`personagent shortcut` 會在桌面和「開始」功能表中新增圖示，點選即可開啟，無須使用終端機。同樣在 Windows 上，「應用程式」頁面的「背景執行」可讓 personagent 在關閉視窗後繼續以通知區域圖示的形式執行，角色照常回覆。

PyPI 上有新版本時，「開始聊天」頁面會顯示提示，並提供更新說明的連結，以及與目前安裝方式對應的更新指令；若是解壓縮原始碼 ZIP 後執行，提示會引導你前往發布頁面下載新版原始碼。對於大多數安裝方式，「應用程式」頁面的「更新並重新開啟」可以直接完成更新。personagent 每天最多向 pypi.org 查詢一次，請求中只包含其版本號。在 `.env` 中設定 `UPDATE_CHECK_ENABLED=false` 即可關閉此項檢查。

習慣使用命令列的使用者可以使用 `personagent start --terminal`、`personagent init --terminal`、`personagent up`，以及 `chat`、`demo`（不需要金鑰）、`run` 和 `connect` 指令。這些指令會保留既有的 `.env`、修改過的人設和學到的記憶。其他平台的接入方式請參閱[完整手冊](guide.zh-TW.md)。
