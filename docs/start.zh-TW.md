# 開始使用 personagent

[English](start.md) · [简体中文](start.zh-CN.md) · 繁體中文 · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · [Français](start.fr.md) · [Deutsch](start.de.md) · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · 簡體中文 · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · [Français](start.fr.md) · [Deutsch](start.de.md) · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · [完整手冊](guide.zh-TW.md)

## 開啟應用

從 PyPI 安裝後開啟：

```sh
python -m pip install personagent
personagent
```

裝了 [uv](https://docs.astral.sh/uv/) 的話，`uvx personagent` 無需單獨安裝即可執行。

在 Windows 上，頁面開在獨立的視窗裡。在 macOS 和 Linux 上在瀏覽器裡開啟；執行 `pip install "personagent[app]"` 之後也能開視窗。

也可以讓 AI 程式設計助手代勞：讓它讀 [setup-for-agents.md](setup-for-agents.md)，然後幫你把 personagent 裝好並設定好。

在 Windows 上也可以下載原始碼 ZIP，解壓後雙擊 `start.bat`。它會在資料夾裡建好自己的 Python 環境，再開啟同一個本地頁面。第一次執行時，還會在桌面和開始功能表裡放一個 personagent 圖示。

從 Git 倉庫執行時，請為它單獨建一個虛擬環境：先執行 `python -m venv .venv`，再執行 `.venv/bin/python -m pip install -e .` 和 `.venv/bin/python -m persona_agent`。Windows 上的直譯器是 `.venv\Scripts\python.exe`，也可以直接雙擊 `start.bat`。

## 填 Key，開始聊天

選擇模型服務，填入 API 金鑰，點「驗證並開始聊天」。預設選中的是 OpenRouter 的免費模型和溫柔傾聽者這個角色。金鑰不花錢，每天限 50 次請求。模型名稱和介面地址在「更多設定」裡，角色的名字和性格在「給角色換個名字或性格」裡。

金鑰只儲存在本機，點「顯示」可以核對。聊天訊息會傳送給你選擇的模型服務，按該服務的正常價格計費。

角色直接在頁面裡回覆。設定會儲存下來，下次開啟就直接進入聊天。

設定完成後，「角色與設定」裡有一個「人設」框，內容就是角色當前使用的人設。改寫它是誰、怎麼說話，然後點「儲存人設」，修改立即生效，角色學到的東西也會保留。

再往下是「更多功能」，可以開啟聯網搜尋、看懂圖片和偶爾主動說話。聯網搜尋預設使用 DuckDuckGo，填入 Tavily 的金鑰會更穩定。連線第一個平臺之前，「開始聊天」頁面上方會顯示一條「開始使用」提示。

## 帶到其他平臺

1. 點「連線平臺」，選擇一個平臺。連線後，角色會回覆這個平臺上的群聊和私聊。
   - **掃描即可連接**：QQ 和個人微信。點「獲取二維碼」，然後在手機上確認。
     - QQ：用手機 QQ 掃碼。QQ 會新建一個機器人，或讓你選一個已有的，金鑰由 personagent 自動取回。如果機器人是你自己在 [QQ 官方頁面](https://q.qq.com/qqbot/openclaw/login.html)建立的，點「改為手動填寫」，填入 AppID 和 AppSecret。
     - 微信：用微信掃碼。微信不會把群訊息轉給這類機器人，所以它只能私聊。
   - **貼上一兩項**：Telegram（向 @BotFather 申請 Token）、Discord（機器人 Token，並開啟 Message Content Intent）、KOOK、飛書、釘釘、Slack、企業微信智慧機器人、Mattermost 和 Misskey。頁面會寫明要從平臺後臺複製哪幾項，其餘設定都用預設值。
   - **高階**：企業微信應用、微信公眾號和 QQ（Webhook）需要一個能轉發到回撥埠的公網地址；OneBot v11（NapCat）和 Satori 需要在本機另外執行相應的軟體。
2. QQ、微信、Telegram 和 Discord 由 personagent 直接連線。其他平臺透過第三方橋接程式 AstrBot 接入。第一次連線這類平臺時，personagent 會下載 AstrBot 和一個獨立的 Python 3.12 執行環境，下載完成前請保持頁面開啟。之後 AstrBot 在後臺執行，沒有需要另外登入的管理後臺。
3. 儲存之前，personagent 會先向平臺核驗憑據。平臺拒絕時，頁面會給出提示，不儲存任何內容。
4. 已連線的平臺列在「連線平臺」頁面頂部，可以在那裡重新設定或斷開。

QQ 機器人連好後，在手機 QQ 的「聯絡人 → 機器人」裡找到它，可以私聊，也可以把它加到你擔任群主的群裡。這條路線使用 QQ 官方機器人平臺，不需要個人 QQ 小號，也不需要安裝其他軟體。機器人能進哪些群由 QQ 決定：透過認證之前，它只能加入管理員擔任群主的群，也不需要配置沙箱。在群裡它預設只收到 @ 它的訊息，群主可以在這個群裡機器人的資料頁開啟「接收全量訊息」。認證和其他賬號方面的事項見 [QQ 機器人官方指南](https://bot.q.qq.com/wiki/bot_new_product-intro/)。

二維碼過期後可以重新獲取；下載失敗可以重試，不必重新填寫模型設定。連線某個平臺時，只會對這個平臺的群聊和私聊放行，其他介面卡仍沿用原有的群和私聊限制。目前不提供 LINE，因為 AstrBot 只能透過它的管理後臺接收 LINE 回撥，而 personagent 不執行這個後臺。

## 下次使用

再次開啟 personagent 即可。配置會保留，已連線的平臺會自動恢復。如果它已經在執行，再次開啟會把它的視窗叫到前面。使用期間請保持它開著：無論是點「退出」還是關閉視窗，它啟動的程序都會一起結束；意外崩潰後殘留的程序會在下次啟動時清理。在 Windows 上，`personagent shortcut` 會在桌面和開始功能表裡放一個圖示，點它就能開啟，不用終端機。

PyPI 上有新版本時，「開始聊天」頁面會顯示一條提示，給出更新內容的連結和與當前安裝方式對應的更新命令；解壓原始碼 ZIP 執行的，提示會讓你到釋出頁下載新版原始碼。personagent 每天最多向 pypi.org 查詢一次，請求中只包含它的版本號。在 `.env` 中設定 `UPDATE_CHECK_ENABLED=false` 可以關閉這項檢查。

習慣命令列的使用者可以使用 `personagent start --terminal`、`personagent init --terminal`、`personagent up`，以及 `chat`、`demo`（不需要金鑰）、`run` 和 `connect` 命令。這些命令會保留已有的 `.env`、修改過的人設和學到的記憶。其他平臺的接入方法見[完整手冊](guide.zh-TW.md)。
