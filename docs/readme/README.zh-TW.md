<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">一個知道什麼時候該安靜、能從別人的糾正中學習的群組聊天角色。</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-0969da?style=flat-square&labelColor=24292f" alt="License: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <strong>繁體中文</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*本頁譯自英文版與簡體中文版，以英文版為準，英文版可能較新。*

personagent 是放進群組聊天裡的一個角色：選一個現成的或自己寫一個，接上任何相容 OpenAI 的模型就能用。先在瀏覽器裡和它聊，再從同一個本機頁面把它帶進 QQ、微信、Telegram、Discord 和另外十幾個平台。

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.zh-CN.jpg" alt="本機頁面的「連接平台」：能接入的平台一目瞭然" width="960">
</p>

<p align="center"><em>「連接平台」和設定、角色聊天都在同一個本機頁面裡。</em></p>

## 為什麼用它

<table>
<tr>
<td width="220" valign="top"><strong>知道什麼時候該安靜</strong></td>
<td valign="top">
叫它就回。沒人叫它時，由一個模型判斷真人這時會不會接話。<br>
有人連續洗版，它只回一則。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>只從站得住腳的糾正中學習</strong></td>
<td valign="top">
糾正教會的事（例如群組裡怎麼稱呼健身房）會帶進這個聊天之後的每一則回覆。<br>
一項變更需要同一個聊天裡兩則一致的反應，其中一則是強證據。<br>
搗亂的人、旁觀者都教不壞它。<br>
每一項變更都有紀錄，哪一項都可以撤回。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>上手快，你的群組在哪它就去哪</strong></td>
<td valign="top">
一行指令就在瀏覽器裡開啟本機頁面，頁面有中文、英文和另外八種語言。<br>
填一個模型金鑰就能聊：預設了十家模型服務，其他相容 OpenAI 的服務也能用。<br>
接入一個平台，用手機掃描一次或貼上一兩項就行。在「動態」裡能看到角色在那邊做了什麼。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>現成角色可以挑，也能自己寫</strong></td>
<td valign="top">
七個現成個性。其中三個是社群裡早就有人畫的角色：DeepSeek 鯨魚娘、GPT 娘（白龍）和 Claude 娘，立繪會眨眼，等回覆時在思考，回覆到了就開口說話。<br>
人設隨時可以改寫，角色學到的東西會留著。
</td>
</tr>
</table>

- 每個聊天有自己的記憶，叫它忘它就忘：`小夏 記住 阿傑喜歡貓`、`小夏 忘掉 喜歡貓`、`小夏 你都記得什麼`（[記憶指令](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#教它)）。群組裡記下的關於某人的事，會跟到對方和角色的私訊裡，反過來不會。
- 聊天用什麼語言，它就用什麼語言回。入門人設在頁面的十種語言裡都有；內建的範例、過濾規則和提示詞是中文和英文。
- 效果是實際量測過的：`personagent eval` 會替它評分，看它開口的時機對不對、有沒有守住人設、糾正有沒有留下來（[結果](https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md#效果評測)）。

## 從這裡開始

```sh
python -m pip install personagent
personagent
```

如果裝了 [uv](https://docs.astral.sh/uv/)，`uvx personagent` 不必另外安裝就能執行。Windows 也可以下載原始碼 ZIP，雙擊 `start.bat`。personagent 在 Linux 上以 Python 3.10–3.14、在 Windows 上以 Python 3.12 測試過。

瀏覽器會開啟一個本機頁面。貼上模型 API 金鑰，按下「驗證並開始聊天」，它會送出一次小請求來驗證金鑰。還沒有金鑰？預設選中的是 OpenRouter 的免費模型，它的金鑰不用付費。想在拿到金鑰之前先看看效果，`personagent demo` 會免費播放三段寫好的場景。[簡明入門](https://github.com/wangkant/personagent/blob/main/docs/start.zh-TW.md)把頁面一個畫面一個畫面講了一遍。

## 要花多少錢

personagent 本身免費。錢付給你選的模型服務，依它自己的價格計算。

- **免費起步。** OpenRouter 的免費模型每天可以請求 50 次；每次請求用的模型可能不同，有些免費服務商會保留收到的內容。智譜的 `glm-4.7-flash` 也免費；Ollama 在你自己的電腦上跑模型，不需要金鑰。
- **哪些會呼叫模型。** 每一則回覆，外加兩個小步驟：沒人叫它時判斷要不要接話，以及判斷大家對它回覆的反應。`personagent doctor` 和 `personagent eval` 也會送出請求；其餘的見[部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-TW.md#費用)。
- **哪些從不呼叫。** `personagent demo` 和記憶指令。

## 接進你的群組

在本機頁面開啟「連接平台」，平台是這樣分組的：

| 頁面分組 | 平台 | 需要準備什麼 |
|---|---|---|
| 掃描即可連接 | QQ、個人微信 | 手機。微信機器人只能一對一聊天 |
| 貼上一兩項 | Telegram、Discord、KOOK、飛書、釘釘、Slack、企業微信智慧機器人、Mattermost、Misskey | 從平台後台複製，頁面會說明要複製哪一項 |
| 進階 | 企業微信應用程式、微信公眾號、QQ（Webhook）、OneBot v11（NapCat）、Satori | 公開網址，或本機的其他軟體 |

填寫的憑證會先經過驗證，通過才儲存；連好的平台之後每次啟動 personagent 都會自動連上。掃描連接的平台、Telegram 和 Discord 由 personagent 自己連接；其餘平台透過它在背景下載並執行的 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 接入，不必另外開啟什麼。在伺服器上，`personagent up` 不開瀏覽器就能啟動角色和所有連好的平台。各平台的設定方法見[使用手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#接進聊天平臺)；從零接上 QQ，一步一步的做法見[部署教學](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-TW.md)。

已經在跑橋接了？

- **AstrBot**：`personagent connect astrbot` 會裝好外掛、設好共用的通關密語。AstrBot 在另一台機器上的做法見[手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#你自己執行的橋接)。
- **[Koishi](https://koishi.chat)** 或任何 Satori 伺服器：用 [Satori 連接器](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.zh-TW.md)。
- **[Matrix](https://matrix.org)**（可透過 mautrix 橋接 WhatsApp、Signal）：用 [Matrix 連接器](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.zh-TW.md)。

## 程式助手

**讓程式助手幫你安裝。** 把下面這句話傳給能在你電腦上執行指令的 AI 程式助手。它會先問你想要什麼，然後安裝 personagent、啟動本機頁面。模型金鑰由你自己填進那個頁面，不經過助手。

```text
讀 https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md ，然後幫我把 personagent 安裝並設定好
```

**寫程式時和角色說話。** 設定好模型金鑰之後，Claude Code、Codex 和 DeepSeek Harness（`dsh`）都能找到你的角色：

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

在那邊開一個新工作階段（DeepSeek Harness 要先重新啟動），請它對你的角色說句話。這和本機頁面是同一個一對一聊天，記憶也相同。在 Claude Code 和 Codex 上加 `--react`，角色可以在一輪結束時說一句話。`--remove` 會把這些全部移除。權限、`--react` 會把什麼傳給你的模型服務、其他 MCP 工具怎麼接，見[手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#程式設計助手)。

## 效果評測

`personagent eval` 用標註好的聊天情境驅動真實的 agent。最近一次在 2026-10-18，測的是 1.3.0：隨套件附帶的角色、兩個模型（透過 OpenRouter），每個測試案例跑 3 次，由 Claude Opus 5.5 盲評。中文 / 英文：

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| 該不該開口，判斷正確的比例（60 個情境） | 80% / 83% | 91% / 93% |
| 比同一個模型直接貼上人設演得好（40 個情境） | 58% / 63% | 53% / 75% |
| 糾正教過的事，之後換個說法再問時能用上 | 56% / 76% | 67% / 71% |

- 該它回的話幾乎不會漏；出錯的大多是它的名字其實指別的東西，例如一家影城、一隻小狗。
- 搗亂的人、旁觀者、說完就走的人做的 84 次糾正，一次都沒有混進來。

[完整結果](https://github.com/wangkant/personagent/blob/main/docs/evals/2026-10-18/README.zh-TW.md)裡有信賴區間、各類錯誤、測試方法和全部報告。

## 與同類專案比較

幾個常被拿來比較的專案（截至 2026 年 11 月）：

- **AstrBot**（AGPL-3.0）：機器人框架，能接十多個平台，有 WebUI 和龐大的外掛市集。沒人叫它時可以隨機回覆（10% 的機率，預設關閉），學習則交給外掛。
- **麥麥 MaiBot**（GPL-3.0）：QQ 上的角色機器人，透過 NapCat 接入，有 WebUI 和一鍵啟動器。由一個規劃模型決定多久說一次話，會從群組聊天裡學習表達方式和行話。
- **ChatLuna 偽裝群友**（AGPL-3.0）：Koishi 外掛，依規則插話：固定間隔、群組的活躍程度、冷場了多久。
- **ElizaOS**（MIT）：以 TypeScript 撰寫的 agent 框架，支援 Discord、Telegram、Slack 等，由模型決定要不要回覆。

personagent 內建的：從別人對它回覆的反應中學習（糾正、否定、被接受的重答），每項變更都有紀錄、可以撤回，還公開了一份行為評測。

它們比較強的地方：所有設定都能在 WebUI 裡完成的桌面程式、龐大的外掛生態，還有行話、貼圖和圖片記憶。已經在用 AstrBot 或 Koishi 的話不必二選一：personagent 可以接在任何一個後面，只擔任那個角色。

## 更新與解除安裝

PyPI 上有新版本時，頁面會顯示一則提示，並附上和你的安裝方式對應的更新指令。用 pip 安裝的話是 `python -m pip install -U personagent`。主目錄原樣保留：設定、角色、它學到的東西和連好的平台都在。

要解除安裝的話，先把它從你接過的程式助手裡移除（`personagent connect claude-code --remove`，`codex` 和 `dsh` 也一樣）。然後結束 personagent，執行 `python -m pip uninstall personagent`。最後刪掉主目錄：從 PyPI 安裝的話是 `~/personagent`，除非你選了別的位置。裡面有你的金鑰、角色和它學到的一切，刪了就找不回來。uv、pipx 的做法和該撤銷什麼，見[完整步驟](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it)（英文）。

## 隱私

personagent 儲存的一切都在你自己機器上的一個主目錄裡：存放金鑰的 `.env`、`persona.txt`、`runtime/`，以及存放代管 AstrBot 和直連平台憑證的 `platforms/`。你選的模型服務商會看到它回覆的對話；personagent 每天會向 pypi.org 查詢一次有沒有新版本（設定 `UPDATE_CHECK_ENABLED=false` 可以關閉）。接入真人之前，請告訴他們這是機器人，並徵得他們同意；哪些內容會傳到哪裡，[手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#隱私與知情同意)裡都列著。

## 文件

- [使用手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md)：安裝、設定、終端機聊天、連接器、教它、「動態」頁、疑難排解。
- [部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-TW.md)：真正上線要知道的事：連接器、QQ、對外公開介面、費用，以及機器人不說話時該查什麼。
- [連接器協定](https://github.com/wangkant/personagent/blob/main/docs/connectors.zh-TW.md)：每則訊息一個帶簽章的 HTTP 請求，給想自己寫連接器的人看。
- [工具腳本](https://github.com/wangkant/personagent/blob/main/docs/tools.zh-TW.md)：`tools/` 裡的腳本，從複製下來的原始碼執行時使用。
- [更新日誌](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md)（英文） · [貢獻指南](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md)（英文） · [安全性政策](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md)（英文） · [免責聲明](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.zh-TW.md)

## 授權條款

程式碼以 [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) 授權釋出，© 2026 Qiankang (Kant) Wang。三張角色立繪採用 CC BY-NC-SA 4.0 授權，姓名標示見 [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md)。

## 致謝

- 其他聊天平台的接入仰賴 [AstrBot](https://github.com/AstrBotDevs/AstrBot)、[NapCat](https://github.com/NapNeko/NapCatQQ)、[Koishi](https://koishi.chat) 與 [satori-python](https://github.com/RF-Tar-Railt/satori-python)、[matrix-nio](https://github.com/matrix-nio/matrix-nio) 與 [mautrix 橋接](https://docs.mau.fi/bridges/)；微信連接依據騰訊的 [openclaw-weixin 協定說明](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)。
- 從反應中學習借鑑了 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557) 和 [BlenderBot 3x](https://arxiv.org/abs/2306.04707)；世界書參考了 [SillyTavern](https://github.com/SillyTavern/SillyTavern) 的 World Info。
