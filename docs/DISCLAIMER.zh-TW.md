# 免責宣告

[English](DISCLAIMER.md) · [简体中文](DISCLAIMER.zh-CN.md) · 繁體中文 · [日本語](DISCLAIMER.ja.md) · [한국어](DISCLAIMER.ko.md) · [Español](DISCLAIMER.es.md) · [Français](DISCLAIMER.fr.md) · [Deutsch](DISCLAIMER.de.md) · [Português (Brasil)](DISCLAIMER.pt-BR.md) · [Русский](DISCLAIMER.ru.md) · 簡體中文 · [繁體中文](DISCLAIMER.zh-TW.md) · [日本語](DISCLAIMER.ja.md) · [한국어](DISCLAIMER.ko.md) · [Español](DISCLAIMER.es.md) · [Français](DISCLAIMER.fr.md) · [Deutsch](DISCLAIMER.de.md) · [Português (Brasil)](DISCLAIMER.pt-BR.md) · [Русский](DISCLAIMER.ru.md)

personagent 以 [PolyForm Noncommercial License 1.0.0](../LICENSE) 釋出：可免費用於非商業目的的使用、修改和分享，不得用於商業目的。它讓一個 AI 角色出現在你的聊天裡，而執行它的人是你。它說什麼、在哪裡說、使用哪些賬號，都由你負責。本頁不構成法律意見。

## 聊天平臺和你的賬號

personagent 接入聊天平臺有兩種方式。QQ 官方機器人、個人微信、Telegram 和 Discord 由它直接連線；其他平臺透過第三方橋接程式接入，通常是 personagent 替你下載並執行的 AstrBot。風險大小取決於連線以什麼身份登入。

- **官方機器人介面**本來就是為機器人設計的，包括 QQ 官方機器人介面、騰訊為個人微信提供的 iLink 機器人介面，以及 Telegram、Discord、Slack、KOOK、飛書、釘釘、企業微信等平臺的介面。使用時仍須遵守各平臺的開發者條款和頻率限制。
- **非官方客戶端**以普通使用者賬號登入，再由軟體代為操作。平臺不認可這種做法，條款中可能明令禁止，賬號可能因此被限制、凍結乃至永久封禁。這類方式包括：
  - **透過 NapCat、LLOneBot、Lagrange 或其他 OneBot 實現接入 QQ**，即高階選項中的 OneBot v11。使用 QQ 官方機器人則完全不需要它們。騰訊不認可這些實現，從雲伺服器或境外 IP 登入時風險最高。
  - **透過 mautrix 橋接接入 WhatsApp、Signal、Messenger、Instagram、Google Messages 等**，即 Matrix 聯結器的接入方式。橋接程式是這些網路的非官方客戶端，其中一些網路的條款對自動傳送訊息有專門規定。詳見 [Matrix 聯結器的說明](../integrations/matrix/README.zh-TW.md#各網路的條款)。
  - 其他任何以真人賬號登入的方式。

如果使用其中任何一種，請準備一個**專用的、丟失也無妨的小號**，不要用主號；條件允許時，在家庭網路中執行，不要部署在雲伺服器上。接入每個網路之前，請閱讀它現行的條款。personagent 的作者，以及與它配合使用的第三方專案（AstrBot、NapCat、Koishi、mautrix 等）的維護者，均不對賬號丟失或受限承擔責任。

## 讓大家知道這是機器人

- 告訴聊天中的人，他們正在與 AI 對話；把它加入群聊之前，先徵得群主或管理員同意。給賬號起一個一看便知是機器人的名字，平臺支援個人簡介的，也在簡介中註明。
- 當有人認真地問它是不是 AI 時，personagent 的設計是如實回答。不要透過修改人設讓它否認。
- 不要用它冒充真人，也不要讓任何人誤以為自己在和真人交談。一些平臺和國家要求標明機器人身份，或對自動化賬號有所限制，請查明適用於你的規定。
- 不要把它放進回覆可能造成傷害或誤導的群，例如討論醫療、法律、投資或心理危機的群，以及有未成年人的群。
- 有人要求它離開，或詢問它記錄了自己的哪些資訊時，請認真對待。管理員可以讓它忘掉某條記錄（`<名字> 忘掉 ...`），它儲存的所有內容都在它的資料資料夾中（見下文）。

## 立繪署名

DeepSeek 鯨魚娘、GPT 娘（白龍）和 Claude 娘的立繪是為 personagent 繪製的，參照的是社群裡已經在畫的形象。鯨魚娘源自 Bilibili 創作者上善无形的原創角色溟月（CC BY-NC-SA 4.0），穿的是 ZipZipPipe 為她設計的女僕裝。GPT 娘參照 ZipZipPipe 的白龍。Claude 娘參照一個社群形象，最初的繪師已不可考。這些立繪單獨採用 CC BY-NC-SA 4.0 許可：請保留署名，不得商用，修改後須以相同許可分享。詳見 `persona_agent/static/characters/LICENSE.md`。

## 模型服務商能看到什麼

每次回覆時，模型服務商都會收到一段提示詞，其中包括人設、聊天中最近的訊息（含暱稱）、機器人為這個聊天記下的筆記，以及它從已學內容中檢索出的部分。如果配置了視覺模型，圖片會傳送給該模型。你啟用的其他服務也會看到其中一部分，包括你配置的備用模型、評判模型、自評模型和向量模型，以及聯網搜尋。聯網搜尋會把一小段查詢傳送給 Tavily（填寫了金鑰時）或 DuckDuckGo。更新檢查每天最多一次，只向 pypi.org 傳送 personagent 的版本號；設定 `UPDATE_CHECK_ENABLED=false` 可以關閉。

使用前請閱讀每家服務商的資料保留政策。有的服務商會儲存提示詞，有的會用於訓練，除非你主動選擇退出。預設的 OpenRouter 免費模型可能用到這類服務商。本地模型（Ollama、llama.cpp）的提示詞只留在你自己的電腦上。聊天中的其他人並未同意任何服務商的條款，請告訴他們訊息會被髮送到哪裡。

## 它在你的電腦上存了什麼

它儲存的所有內容都在資料資料夾中。設定和 API Key 在 `.env` 裡，機器人憑據和替你執行的 AstrBot 在 `platforms/` 裡，`runtime/` 中則有聊天筆記、它判斷過的反應（原文照錄）、學習賬本和學到的示例。如果設定了 `SERVER_LOG_FILE`，日誌中也可能包含對話細節。請妥善保管這個資料夾，不要公開，也不要附在 issue 裡；如果在意它學到的內容，請做好備份。各國關於儲存和處理他人訊息的法律不盡相同，遵守所在地的法律是你自己的責任。

它可能學錯。一項改變需要同一個聊天中兩次一致的反應，其中至少一次來自被回覆的那個人。每項改變都記錄在只追加的賬本中，你可以用 `personagent learned` 或本地頁面的「動態」檢視和撤銷。請定期檢查。

## 不提供擔保

本軟體按「現狀」提供，不附帶任何明示或暗示的擔保。因使用本軟體產生的任何索賠、損害或損失，作者概不負責。詳見 [LICENSE](../LICENSE)。
