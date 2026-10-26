<p align="center"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%"></p>

<h3 align="center">一個知道什麼時候該安靜、能從別人的糾正中學習的群組聊天角色。</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="License: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <strong>繁體中文</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*本頁譯自英文版與簡體中文版，以英文版為準，英文版可能較新；文中連結的指南為英文或簡體中文。*

personagent 是放進群組聊天裡的一個角色：選一個現成的個性或自己寫一個，接上任何相容 OpenAI 的模型就能用。QQ、微信、Telegram、Discord 由它自己連接；KOOK、飛書、釘釘、Slack、企業微信、Mattermost、Misskey 在同一個頁面裡接入。

先在本機頁面裡聊天，填一個模型金鑰就能開始。想把角色帶進群組，掃描一次或填一兩項就行。

![本機頁面的「連接平台」：能接入的平台一目瞭然](https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.zh-CN.jpg)

<sub>「連接平台」和設定、角色聊天都在同一個本機頁面裡。截圖來自一個臨時環境，使用本機的模擬模型。</sub>

## 從這裡開始

從 PyPI 安裝後開啟：

```sh
python -m pip install personagent
personagent
```

如果裝了 [uv](https://docs.astral.sh/uv/)，`uvx personagent` 不必另外安裝就能執行。

瀏覽器會開啟一個本機頁面，分成三個分頁：「開始聊天」「連接平台」「角色與設定」。填入模型 API 金鑰，按下「驗證並開始聊天 →」，它會送出一次小請求來驗證金鑰。模型服務有 10 種預設，也可以選其他相容 OpenAI 的服務；角色有名字和個性的預設。「人設」框裡的內容就是 `persona.txt`，儲存後會重新啟動角色服務，學到的東西不會遺失。「更多功能」裡可以開啟網路搜尋、看圖和主動說話。再次執行 `personagent` 會沿用已經開啟的頁面。右上角的選單可以把頁面切換成英文、中文或另外八種語言。角色會用聊天裡的語言回覆；不過內建的提示詞和資料只有中文和英文，換成其他語言效果如何，取決於模型。

Windows 也可以下載原始碼 ZIP，解壓縮後雙擊 `start.bat`。需要 Python 3.10–3.14。詳見[簡明入門](https://github.com/wangkant/personagent/blob/main/docs/start.zh-CN.md)；命令列和連接器的用法在[完整手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)裡。

## 讓程式助手幫你安裝

能在你電腦上執行指令的 AI 程式助手，可以代你安裝和設定 personagent。把這句話傳給它：

```text
讀 https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md ，然後幫我把 personagent 安裝並設定好
```

它會先問你角色的語言、名字和個性、要用哪家模型服務、要接哪些聊天平台，然後安裝 personagent、建立主目錄、啟動本機頁面。模型金鑰由你自己在頁面裡填，不經過助手。它依循的[說明](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md)是英文的，你用中文和它溝通就行。

## 為什麼用它

<table>
  <tr>
    <td width="220"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="托著腮聽大家聊天" width="220"></td>
    <td>
      <b>知道什麼時候該安靜</b><br>
      叫它才回。沒人叫它時，由一個模型判斷真人這時會不會接話，而不是靠擲骰子。<br>
      有人連續洗版，它只回一則。
    </td>
  </tr>
  <tr>
    <td width="220"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/learned-notebook.webp" alt="筆記本上劃掉一句，換成更好的一句" width="220"></td>
    <td>
      <b>只從站得住腳的糾正中學習</b><br>
      糾正教會的事（例如群組裡怎麼稱呼健身房）會帶進這個聊天之後的每一則回覆。<br>
      一項變更需要同一個聊天裡兩則一致的反應，其中一則是強證據。<br>
      搗亂的人、旁觀者都教不壞它。<br>
      每一項變更都有紀錄，隨時可以撤回。
    </td>
  </tr>
  <tr>
    <td width="220"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="拿著筆記本準備聊天的兔子" width="220"></td>
    <td>
      <b>上手快，你的群組在哪它就去哪</b><br>
      在瀏覽器裡設定和聊天，頁面有中英文和另外八種語言，11 種模型服務可選。<br>
      QQ、微信、Telegram、Discord 由它自己連接，另外十幾個平台也在同一個頁面裡接入。<br>
      在「動態」裡能看到它做了什麼。
    </td>
  </tr>
</table>

- 每個聊天的記憶各自獨立，互不相通。
- 修改人設不會丟掉它學到的東西。
- 效果是實際量測過的，數字見[效果評測](https://github.com/wangkant/personagent/blob/main/README.zh-CN.md#效果评测)。

## 接進你的群組

在本機頁面開啟「連接平台」，平台分成三組：

| 頁面分組 | 平台 | 需要準備什麼 |
|---|---|---|
| 掃描即可連接 | QQ、個人微信 | 手機。微信這類機器人只能私訊 |
| 貼上一兩項 | Telegram、Discord、KOOK、飛書、釘釘、Slack、企業微信智慧機器人、Mattermost、Misskey | 從平台後台複製，頁面會說明要複製哪一項 |
| 進階 | 企業微信應用程式、微信公眾號、QQ（Webhook）、OneBot v11（NapCat）、Satori | 公開網址，或本機的其他軟體 |

填寫的內容會先經過驗證，通過才儲存；連好的平台之後每次啟動 personagent 都會自動連上。QQ、微信、Telegram、Discord 由 personagent 直接連接，其餘平台透過它在背景下載並執行的 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 接入，不必另外開啟什麼。在伺服器上不開瀏覽器的話，`personagent up` 會啟動角色和所有連好的平台。

**已經在用 AstrBot、Koishi 或 Matrix？** 如果 AstrBot 就在這台電腦上，執行 `personagent connect astrbot` 就會裝好外掛、設好通關密語。如果 AstrBot 在別台機器上，從[最新 Release](https://github.com/wangkant/personagent/releases/latest) 下載 `astrbot_plugin_personagent.zip`，在它外掛頁面的 **Install from File** 上傳，再依照下面的手冊填好通關密語和 personagent 的 HTTPS 位址。[Koishi](https://koishi.chat) 透過 [Satori 連接器](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md)（英文）接入，[Matrix](https://matrix.org)（可透過 mautrix 橋接 WhatsApp、Signal）透過 [Matrix 連接器](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md)（英文）接入。

具體做法見[使用手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#接进聊天平台)（簡體中文）和[部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.md)（英文）；[中文部署教學](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)（簡體中文）從零開始講解 QQ，每一步都寫明會看到什麼。

## 與同類專案比較

幾個常被拿來比較的專案，依據各自 2026 年 10 月的文件：

- **AstrBot**（AGPL-3.0）：機器人框架，能接 18 個以上的平台，有 WebUI 和龐大的外掛市集。可以開啟「主動回覆」按機率隨機插話（預設 10%，預設關閉），學習則交給外掛。
- **麥麥 MaiBot**（GPL-3.0）：QQ 上的角色機器人，透過 NapCat 接入，有 WebUI 和一鍵啟動器。由一個規劃模型決定多久說一次話，會從群組聊天裡學習表達方式和行話。
- **ChatLuna 偽裝群友**（AGPL-3.0）：Koishi 外掛，依規則插話：固定間隔、群組的活躍程度、冷場了多久。
- **ElizaOS**（MIT）：以 TypeScript 撰寫的 agent 框架，支援 Discord、Telegram、Slack 等，由模型決定要不要回覆。

personagent 內建、而它們交給外掛或文件裡沒有提到的：從別人對它回覆的反應中學習（糾正、否定、被接受的重答）；一項變更需要同一個聊天裡兩則一致的反應，其中一則是強證據；每項變更都有紀錄，可以撤回；行為有公開的評測（[見下文](https://github.com/wangkant/personagent/blob/main/README.zh-CN.md#效果评测)）。

它們比較強的地方：桌面程式、所有設定都能在 WebUI 裡點選、外掛生態豐富，還有學行話、貼圖、圖片記憶。已經在用 AstrBot 或 Koishi 也不必二選一：personagent 可以接在它們後面，只擔任那個角色。

## 效果評測

`personagent eval` 用標註好的聊天情境驅動真實的 agent。最近一次在 2026-10-18：隨套件附帶的角色、兩個模型（透過 OpenRouter），每個測試案例跑 3 次，由 Claude Opus 5.5 盲評。中文 / 英文：

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| 該不該開口，判斷正確的比例（60 個情境） | 80% / 83% | 91% / 93% |
| 比同一個模型直接貼上人設演得好（40 個情境） | 58% / 63% | 53% / 75% |
| 糾正教過的事，之後換個說法再問時能用上 | 56% / 76% | 67% / 71% |

- 該它回的話幾乎不會漏；出錯的大多是名字其實指別的東西，例如影城的名字、別人家的寵物。
- 中文相較直接貼上人設的優勢在誤差範圍之內。
- 當天第一輪時，糾正還不會單獨記下重點，之後換個說法再問，58 次裡只用上 2 次；修改後重跑才是上面的數字。
- 搗亂、旁觀、說完就走的糾正，84 次一次都沒有混進來。

[完整結果](https://github.com/wangkant/personagent/blob/main/docs/evals/2026-10-18/README.zh-CN.md)（簡體中文）裡有信賴區間、各類錯誤、測試方法、這些數字無法說明什麼，以及全部報告。

## 文件

- [使用手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)（簡體中文）：安裝、設定、終端機試聊、接入各平台、教它、「動態」頁、評測、疑難排解，README 沒寫的都在這裡
- [中文部署教學](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)（簡體中文）：安裝、掃描接上 QQ、排查問題，從零開始，每一步都寫明會看到什麼
- [部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.md)（英文）：長期執行要知道的事，包括連接器、多平台、對外公開、費用和排查
- [連接器協定](https://github.com/wangkant/personagent/blob/main/docs/connectors.md)（英文）：為其他平台自行撰寫連接器
- [工具腳本](https://github.com/wangkant/personagent/blob/main/docs/tools.md)（英文）：`tools/` 裡給原始碼版使用的腳本
- [更新日誌](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md)（英文），含[從 0.4 升級](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04)的完整清單
- [貢獻指南](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md)（英文）
- [安全性政策](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md)（英文）：如何私下回報漏洞
- [免責聲明](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.zh-CN.md)（簡體中文）

## 隱私

personagent 儲存的一切都在你自己機器上的一個主目錄裡：存放金鑰的 `.env`、`persona.txt`、`runtime/`，以及存放代管 AstrBot 和直連平台憑證的 `platforms/`。模型服務商會看到對話內容；personagent 每天會向 pypi.org 查詢一次有沒有新版本（設定 `UPDATE_CHECK_ENABLED=false` 可以關閉）；接入真實的群組之前，請告訴群組成員這是機器人，並徵得他們同意。哪些內容會傳送給誰，見[使用手冊的隱私一節](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md#隐私与知情同意)（簡體中文）。

## 專案狀態

1.3.0 已發布到 PyPI（2026-10-18）。QQ 是實際執行最多的平台，1.0 透過 AstrBot，1.1 起直接連接。微信、Telegram、Discord 的直連會在儲存前向真實服務驗證憑證，其餘部分在模擬環境中測試；Satori 和 Matrix 連接器目前只在模擬環境中測過。CI 在 Linux 上以 Python 3.10–3.14、在 Windows 上以 Python 3.12 執行測試，另有工作會安裝套件，執行指令和本機頁面。

## 授權條款

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang。

## 致謝

- 其餘平台的接入仰賴 [AstrBot](https://github.com/AstrBotDevs/AstrBot)、[NapCat](https://github.com/NapNeko/NapCatQQ)、[Koishi](https://koishi.chat) 與 [satori-python](https://github.com/RF-Tar-Railt/satori-python)、[matrix-nio](https://github.com/matrix-nio/matrix-nio) 與 [mautrix 橋接](https://docs.mau.fi/bridges/)；微信直連依據騰訊的 [openclaw-weixin 協定說明](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)。
- 從反應中學習借鑑了 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557) 和 [BlenderBot 3x](https://arxiv.org/abs/2306.04707)；世界書參考了 [SillyTavern](https://github.com/SillyTavern/SillyTavern) 的 World Info。
