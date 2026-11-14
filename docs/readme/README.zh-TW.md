<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">像人一樣的 AI 代理，可連接你使用的所有平台。<br>它擁有自己的個性與記憶，從與人的交流中學習，並自行判斷何時發言。</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-0969da?style=flat-square&labelColor=24292f" alt="License: PolyForm Noncommercial"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <strong>繁體中文</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*本頁譯自英文版與簡體中文版，以英文版為準，英文版可能較新。*

personagent 是一個像人一樣的 AI 代理（agent）：它擁有自己的個性與記憶，從與人的交流中學習，並自行判斷何時發言。它可在你使用的各處運作：QQ、微信、Telegram、Discord 及另外十八個平台的群組與私訊，你電腦上的視窗，以及 Claude Code、Codex 等程式設計助理。角色可選用現成的，也可自行撰寫；接上任何相容 OpenAI 的模型即可使用。

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.zh-CN.jpg" alt="本機頁面的「連接平台」：可掃描連接或填寫幾項即可連接的平台、已收合的進階平台，以及可接入的程式設計助理" width="960">
</p>

<p align="center"><em>「連接平台」、設定與角色聊天均位於同一個本機頁面中。</em></p>

## 為何選用

<table>
<tr>
<td width="220" valign="top"><strong>擁有自己的個性</strong></td>
<td valign="top">
提供七種現成個性。其中三個是社群中早已有人繪製的角色：DeepSeek 鯨魚娘、GPT 娘（白龍）和 Claude 娘，立繪會眨眼、思考與開口說話。<br>
人設可隨時改寫，角色學到的內容會予以保留。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>像人一樣說話</strong></td>
<td valign="top">
它像人在聊天時那樣寫字：用對話所使用的語言，句子短而平實，不列清單、不加標題、不說客服套話，不知道的事會直說。<br>
在多數平台上，回覆會分成幾則短訊息，每則之間留出打字的間隔；Telegram、Discord 與 Matrix 還會同步顯示輸入狀態。<br>
它會收集大家傳過的貼圖並在合適時使用；深夜裡除非被叫到，通常不參與對話。<br>
開啟後，它會在長時間無人發言時主動開啟話題，也會回頭跟進大家提過的安排。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>有記憶</strong></td>
<td valign="top">
每個聊天都有獨立的記憶：重新啟動後仍在的近期訊息、此前對話的摘要、附日期的事件，以及關於成員的事實，均由它自行保持最新。<br>
它記住的全部內容都列在「動態」中，其中任何一項都可以刪除或還原。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>只從有充分依據的糾正中學習</strong></td>
<td valign="top">
從糾正中學到的事（例如群組中如何稱呼健身房）會套用於該聊天此後的每一則回覆。<br>
蓄意搗亂者或旁觀者都無法讓它學壞。<br>
反應無法確定的變更由角色自行判斷並記錄理由，任何內容都無須他人核准。<br>
每一項變更都有紀錄，且均可撤回。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>懂得適時保持安靜</strong></td>
<td valign="top">
在群組中，被點名時即會回覆；無人點名時，由一個模型判斷真人此時是否會接話。<br>
有人連續洗版時，它只回覆一則。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>連接你的所有平台</strong></td>
<td valign="top">
二十二個聊天平台都能在同一個頁面中連接，只需以手機掃描一次或填寫幾項；其中多數同時支援群組與私訊。<br>
同一個 AI 代理也會在你電腦上的視窗中回覆，並可在 Claude Code、Codex 和 DeepSeek Harness 中使用。<br>
其他平台可透過 AstrBot、Koishi 或 Matrix 橋接接入，也可自行撰寫聯結器。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>沿用你現有的資源</strong></td>
<td valign="top">
可使用任何相容 OpenAI 的模型：OpenRouter 的免費模型、付費服務，或以 Ollama 在你電腦上執行的模型。<br>
一行指令即可開啟，頁面提供中文、英文及另外八種語言；填入一個模型金鑰即可開始聊天。
</td>
</tr>
</table>

也可以在聊天中要求它記住或忘記指定的內容：`小夏，記住 阿傑不吃辣`、`小夏 忘掉 不吃辣`（[記憶指令](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#教導角色)）。會保存哪些內容、保存多久，請參閱使用手冊的[記憶](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#記憶)一節。

## 從這裡開始

```sh
python -m pip install personagent
personagent
```

若已安裝 [uv](https://docs.astral.sh/uv/)，`uvx personagent` 無須另行安裝即可執行。在 Windows 上，也可以下載原始碼 ZIP，再按兩下 `start.bat`。

在 Windows 上，它會在獨立的視窗中開啟；在 macOS 和 Linux 上則在瀏覽器中開啟。貼上模型 API 金鑰，再點選「驗證並開始聊天」。尚未取得金鑰時，可使用預設選取的 OpenRouter 免費模型，其金鑰無須付費。`personagent demo` 無須金鑰，會播放三段預先編寫的場景。[入門指南](https://github.com/wangkant/personagent/blob/main/docs/start.zh-TW.md)逐一說明了頁面中的各個畫面。

personagent 本身免費。費用支付給你選擇的模型服務，依該服務的價格計算。一則訊息可能產生不只一次模型請求：除了回覆本身，角色有時還會判斷是否在群組中發言、評估回覆得到的反應，或整理記憶。OpenRouter 的免費模型每天可請求 50 次，部分免費服務商會保留收到的內容；Ollama 在你自己的電腦上執行模型，不需要金鑰。

## 連接你的平台

在本機頁面開啟「連接平台」：

| 頁面分組 | 平台 | 需要準備的項目 |
|---|---|---|
| 掃描連接 | QQ、個人微信 | 手機。微信機器人僅限一對一聊天 |
| 填寫幾項 | Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK、Stoat、KOOK、飛書、釘釘、Slack、企業微信智慧機器人、Mattermost、Misskey | 從平台後台複製，頁面會註明需要複製的項目 |
| 進階 | 企業微信應用、微信公眾號、QQ（Webhook）、OneBot v11（NapCat）、Satori | 公開網址，或本機的其他軟體 |

已連接的平台在此後每次啟動 personagent 時都會自動連線。掃描連接的平台，以及 Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK 和 Stoat 由 personagent 直接連線；其餘平台透過它在背景下載並執行的 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 接入。在沒有顯示器的伺服器上，可以在終端機中執行 `personagent connect <平台>`，連接上述十個平台中的任何一個，操作步驟和驗證方式與頁面相同；執行 `personagent up` 即可在不開啟瀏覽器的情況下全部啟動。各平台的設定方式請參閱[使用手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#接入聊天平台)；從頭接入 QQ 的步驟請參閱[部署教學](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-TW.md)。

若已在執行 AstrBot、Koishi 或 Matrix，personagent 可以接在其後方，僅作為 AI 代理運作：請參閱[你自己執行的橋接](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#你自己執行的橋接)、[Satori 聯結器](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.zh-TW.md)和 [Matrix 聯結器](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.zh-TW.md)。

## 程式設計助理

**由程式設計助理代為安裝。** 將下列這句話傳送給能在你的電腦上執行指令的 AI 程式設計助理。模型金鑰由你自行填入本機頁面，不經過助理。

```text
讀 https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md ，然後幫我把 personagent 安裝並設定好
```

**撰寫程式時與角色對話。** Claude Code、Codex 和 DeepSeek Harness（`dsh`）都能找到你的角色，聊天內容與記憶和本機頁面共用同一份：

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove` 可將其移除；在頁面「連接平台」的「程式設計助理」中，也可以完成串接與移除。權限，以及讓角色在每輪結束時發表一句評論的 `--react`，請參閱[手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#程式設計助理)。

## 更新與解除安裝

PyPI 上有新版本時，頁面會顯示提示和對應的更新指令。以 pip 安裝時，指令為 `python -m pip install -U personagent`。對於大多數安裝方式，頁面「應用程式」檢視中的「更新並重新開啟」可代為執行。設定、角色、學到的內容和已連接的平台都會保留。如需解除安裝，請依照[解除安裝步驟](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it)（英文）操作。

## 隱私

personagent 儲存的所有內容都位於你自己電腦上的一個主目錄中。你選擇的模型服務商會看到它所回覆的對話；personagent 每天會向 pypi.org 查詢一次是否有新版本（設定 `UPDATE_CHECK_ENABLED=false` 即可關閉）。與真人互動之前，請告知對方這是機器人，並徵得其同意；哪些內容會傳送至何處，[手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md#隱私與知情同意)中均有列出。

## 文件

- [使用手冊](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-TW.md)：設定、聯結器、教導角色、「動態」頁面、疑難排解。
- [部署指南](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-TW.md)：正式上線須知、費用，以及機器人沒有回應時的檢查項目。
- [聯結器協定](https://github.com/wangkant/personagent/blob/main/docs/connectors.zh-TW.md)：供自行撰寫聯結器的開發者參考。
- [工具腳本](https://github.com/wangkant/personagent/blob/main/docs/tools.zh-TW.md)：`tools/` 中的腳本，從複製的原始碼執行時使用。
- [更新紀錄](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md)（英文） · [貢獻指南](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md)（英文） · [安全性政策](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md)（英文） · [免責宣告](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.zh-TW.md)

## 授權條款

personagent 以 [PolyForm Noncommercial License 1.0.0](https://github.com/wangkant/personagent/blob/main/LICENSE) 發布，© 2026 Qiankang (Kant) Wang：可免費用於非商業目的的使用、修改和分享，不得用於商業目的。`integrations/` 下的聯結器仍採用 MIT 授權，1.4.0 及更早的版本亦然。三張角色立繪採用 CC BY-NC-SA 4.0 授權，姓名標示見 [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md)。

## 致謝

- 其他聊天平台的接入仰賴 [AstrBot](https://github.com/AstrBotDevs/AstrBot)、[NapCat](https://github.com/NapNeko/NapCatQQ)、[Koishi](https://koishi.chat) 與 [satori-python](https://github.com/RF-Tar-Railt/satori-python)、[matrix-nio](https://github.com/matrix-nio/matrix-nio) 與 [mautrix 橋接](https://docs.mau.fi/bridges/)；微信連接依據騰訊的 [openclaw-weixin 協定說明](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)。
- 從反應中學習借鑑了 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557) 和 [BlenderBot 3x](https://arxiv.org/abs/2306.04707)；世界書參考了 [SillyTavern](https://github.com/SillyTavern/SillyTavern) 的 World Info。
