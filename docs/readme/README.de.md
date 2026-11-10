<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Ein Charakter für deine Gruppenchats, der weiß, wann er besser schweigt, und aus Korrekturen lernt.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-0969da?style=flat-square&labelColor=24292f" alt="Lizenz: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <strong>Deutsch</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Dies ist eine Übersetzung der englischen README, die maßgeblich ist und aktueller sein kann.*

personagent ist ein Charakter für deine Gruppenchats: Wähl einen fertigen aus oder schreib deinen eigenen und betreib ihn mit einem beliebigen OpenAI-kompatiblen Modell. Fang damit an, auf deinem eigenen Rechner mit ihm zu chatten, und hol ihn dann von derselben lokalen Seite aus in QQ, WeChat, Telegram, Discord und ein Dutzend weitere Apps.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="Die Ansicht Apps verbinden der lokalen Seite mit allen Plattformen, denen er beitreten kann" width="960">
</p>

<p align="center"><em>Apps verbinden, auf derselben lokalen Seite wie Einrichtung und Charakter-Chat.</em></p>

## Warum personagent

<table>
<tr>
<td width="220" valign="top"><strong>Er weiß, wann er besser schweigt.</strong></td>
<td valign="top">
Er antwortet, wenn er gerufen wird. Ansonsten beurteilt ein Modell, ob ein Mensch sich einklinken würde.<br>
Auf eine Flut von Nachrichten kommt eine einzige Antwort.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Er lernt aus Korrekturen, die Bestand haben.</strong></td>
<td valign="top">
Was eine Korrektur lehrt, etwa wie die Gruppe das Fitnessstudio nennt, fließt in jede spätere Antwort in diesem Chat ein.<br>
Ein Troll oder ein Unbeteiligter kann ihn nicht umerziehen.<br>
Jede Änderung wird festgehalten, und jede lässt sich zurücknehmen.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Er ist schnell gestartet und lebt dort, wo deine Gruppe ist.</strong></td>
<td valign="top">
Ein Befehl öffnet ihn auf deinem Rechner, auf Englisch, Chinesisch oder in acht weiteren Sprachen.<br>
Füge einen Modellschlüssel ein und chatte los, dann verbinde eine App per Handy-Scan oder mit ein, zwei eingefügten Werten.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Er kann ein fertiger Charakter sein oder dein eigener.</strong></td>
<td valign="top">
Sieben fertige Persönlichkeiten. Drei davon sind Figuren, die die Community längst zeichnet: das DeepSeek-Walmädchen, das GPT-Drachenmädchen und die Claude-Dame, mit Porträts, die blinzeln, nachdenken und sprechen.<br>
Schreib die Persona um, wann immer du willst. Was der Charakter gelernt hat, bleibt erhalten.
</td>
</tr>
</table>

Jeder Chat hat sein eigenes Gedächtnis, und auf Wunsch vergisst er wieder: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian` ([Gedächtnis-Befehle](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#gedächtnis-befehle)).

## Los geht's

```sh
python -m pip install personagent
personagent
```

Mit [uv](https://docs.astral.sh/uv/) startet `uvx personagent` es ohne separaten Installationsschritt. Unter Windows kannst du auch das Quellcode-ZIP herunterladen und `start.bat` doppelklicken.

Unter Windows öffnet es sich in einem eigenen Fenster, unter macOS und Linux im Browser. Füge einen API-Schlüssel für das Modell ein und klick auf **Prüfen & Chat starten**. Noch keinen Schlüssel? Die kostenlosen Modelle von OpenRouter sind vorausgewählt, und ihr Schlüssel kostet nichts. `personagent demo` spielt drei vorgefertigte Szenen ganz ohne Schlüssel ab. Die [Einstiegsanleitung](https://github.com/wangkant/personagent/blob/main/docs/start.de.md) führt Bildschirm für Bildschirm durch die Seite.

personagent ist kostenlos. Du bezahlst den Modelldienst, den du wählst, zu dessen eigenen Preisen. Die kostenlosen Modelle von OpenRouter erlauben 50 Anfragen pro Tag, und manche kostenlosen Anbieter behalten, was sie erhalten; Ollama lässt ein Modell ganz ohne Schlüssel auf deinem eigenen Computer laufen.

## Bring ihn in deine Gruppe

Öffne **Apps verbinden** auf der lokalen Seite:

| Auf der Seite | Apps | Was du brauchst |
|---|---|---|
| Per Scan verbinden | QQ, persönliches WeChat | Dein Handy. WeChat-Bots bekommen nur Einzelchats |
| Ein oder zwei Werte einfügen | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, WeCom-KI-Bot, Mattermost, Misskey | Werte aus der Konsole der App; die Seite sagt dir, welche |
| Erweitert | WeCom-App, Offizielles WeChat-Konto, QQ-Webhook, OneBot v11 (NapCat), Satori | Eine öffentliche Adresse oder andere Software auf diesem Computer |

Verbundene Apps starten bei jedem Start von personagent wieder mit. Die Apps mit Scan-Verbindung, Telegram und Discord verbindet personagent selbst; der Rest läuft über ein [AstrBot](https://github.com/AstrBotDevs/AstrBot), das es herunterlädt und im Hintergrund betreibt. Auf einem Server startet `personagent up` alles ohne Browser. Die Einrichtung für jede App steht im [Benutzerhandbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#in-einen-chat-bringen), und QQ von null an in der [chinesischen Deployment-Anleitung](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

Du betreibst schon AstrBot, Koishi oder Matrix? personagent kann als Charakter dahinter laufen: siehe [Brücken, die du selbst betreibst](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#brücken-die-du-selbst-betreibst), den [Satori-Connector](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.de.md) und den [Matrix-Connector](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.de.md).

## Coding-Agenten

**Lass einen die Einrichtung übernehmen.** Gib die Zeile unten einem Coding-Agenten, der auf deinem Computer Befehle ausführen kann. Deinen Modellschlüssel fügst du selbst in die lokale Seite ein, sodass er nie durch den Agenten läuft.

```text
Lies https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md und richte personagent für mich ein.
```

**Sprich mit deinem Charakter, während du arbeitest.** Claude Code, Codex und DeepSeek Harness (`dsh`) erreichen den Charakter, mit demselben Chat und demselben Gedächtnis wie auf der lokalen Seite:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove` nimmt es wieder heraus. Das [Benutzerhandbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#coding-agenten) erklärt die Berechtigungen und `--react`, das den Charakter am Ende eines Durchgangs einen Satz sagen lässt.

## Aktualisieren und deinstallieren

Wenn auf PyPI eine neuere Version liegt, zeigt die Seite einen Hinweis mit dem Update-Befehl. Mit pip ist das `python -m pip install -U personagent`. Einstellungen, Charakter, Gelerntes und verbundene Apps bleiben erhalten. Um es zu entfernen, folge den [Schritten zur Deinstallation](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (auf Englisch).

## Datenschutz

Alles, was personagent speichert, bleibt auf deinem Rechner, in einem Home-Ordner. Der Modellanbieter, den du wählst, sieht die Unterhaltungen, auf die er antwortet, und einmal am Tag fragt personagent bei pypi.org nach, ob es eine neuere Version gibt (`UPDATE_CHECK_ENABLED=false` schaltet das ab). Bevor du ihn mit echten Menschen verbindest, sag ihnen, dass es ein Bot ist, und hol ihre Einwilligung ein; das [Handbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#datenschutz-und-einwilligung) listet auf, was wohin geht.

## Dokumentation

- [Benutzerhandbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md): Einrichtung, Connectoren, ihm etwas beibringen, die Ansicht Aktivität, Fehlerbehebung.
- [Deployment-Anleitung](https://github.com/wangkant/personagent/blob/main/docs/deploy.de.md): Betrieb im Ernstfall, Kosten und was zu prüfen ist, wenn der Bot verstummt.
- [Connector-Protokoll](https://github.com/wangkant/personagent/blob/main/docs/connectors.de.md): um einen eigenen Connector zu schreiben.
- [Tools](https://github.com/wangkant/personagent/blob/main/docs/tools.de.md): die Skripte in `tools/`, zum Ausführen aus einem Klon.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Mitwirken](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Sicherheitsrichtlinie](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Haftungsausschluss](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.de.md)

## Lizenz

Der Code steht unter [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang. Die drei Charakterporträts stehen unter CC BY-NC-SA 4.0; die Nachweise finden sich in [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Danksagungen

- Andere Chatplattformen werden über [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) mit [satori-python](https://github.com/RF-Tar-Railt/satori-python) sowie [matrix-nio](https://github.com/matrix-nio/matrix-nio) mit den [mautrix-Bridges](https://docs.mau.fi/bridges/) erreicht; die WeChat-Verbindung folgt Tencents [Protokollnotizen zu openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md).
- Das Lernen aus Reaktionen stützt sich auf [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) und [BlenderBot 3x](https://arxiv.org/abs/2306.04707); das Lorebook folgt der World Info von [SillyTavern](https://github.com/SillyTavern/SillyTavern).
