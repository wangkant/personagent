<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Eine Figur für Ihre Gruppenchats, die weiß, wann sie besser schweigt, und aus Korrekturen lernt.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-0969da?style=flat-square&labelColor=24292f" alt="Lizenz: PolyForm Noncommercial"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <strong>Deutsch</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Dies ist eine Übersetzung der englischen README, die maßgeblich ist und aktueller sein kann.*

personagent ist eine Figur für Ihre Gruppenchats: Wählen Sie eine fertige aus oder schreiben Sie Ihre eigene, und betreiben Sie sie mit einem beliebigen OpenAI-kompatiblen Modell. Chatten Sie zunächst auf Ihrem eigenen Rechner mit ihr, und holen Sie sie dann von derselben lokalen Seite aus in QQ, WeChat, Telegram, Discord und achtzehn weitere Apps.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="Die Ansicht Apps verbinden der lokalen Seite mit allen Plattformen, denen die Figur beitreten kann" width="960">
</p>

<p align="center"><em>Apps verbinden, auf derselben lokalen Seite wie Einrichtung und Chat mit der Figur.</em></p>

## Warum personagent

<table>
<tr>
<td width="220" valign="top"><strong>Die Figur weiß, wann sie besser schweigt.</strong></td>
<td valign="top">
Die Figur antwortet, wenn sie angesprochen wird. Andernfalls beurteilt ein Modell, ob sich ein Mensch an dieser Stelle beteiligen würde.<br>
Auf eine Flut von Nachrichten kommt eine einzige Antwort.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Die Figur lernt aus Korrekturen, die Bestand haben.</strong></td>
<td valign="top">
Was eine Korrektur lehrt, etwa wie die Gruppe das Fitnessstudio nennt, fließt in jede spätere Antwort in diesem Chat ein.<br>
Ein Störer oder ein Unbeteiligter kann sie nicht umerziehen.<br>
Jede Änderung wird festgehalten, und jede lässt sich zurücknehmen.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Die Figur ist schnell gestartet und dort präsent, wo Ihre Gruppe ist.</strong></td>
<td valign="top">
Ein Befehl öffnet sie auf Ihrem Rechner, auf Englisch, Chinesisch oder in acht weiteren Sprachen.<br>
Fügen Sie einen Modellschlüssel ein, beginnen Sie den Chat und verbinden Sie anschließend eine App per Scan mit dem Smartphone oder mit ein bis zwei eingefügten Werten.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Die Figur kann eine fertige sein oder Ihre eigene.</strong></td>
<td valign="top">
Sieben fertige Persönlichkeiten. Drei davon sind Figuren, die die Community längst zeichnet: das DeepSeek-Walmädchen, das GPT-Drachenmädchen und die Claude-Dame, mit Porträts, die blinzeln, nachdenken und sprechen.<br>
Sie können die Persona jederzeit umschreiben. Was die Figur gelernt hat, bleibt erhalten.
</td>
</tr>
</table>

Jeder Chat hat sein eigenes Gedächtnis, und auf Wunsch vergisst die Figur Gespeichertes wieder: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian` ([Gedächtnis-Befehle](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#gedächtnis-befehle)).

## Erste Schritte

```sh
python -m pip install personagent
personagent
```

Mit [uv](https://docs.astral.sh/uv/) startet `uvx personagent` das Programm ohne gesonderten Installationsschritt. Unter Windows können Sie auch das Quellcode-ZIP herunterladen und `start.bat` doppelklicken.

Unter Windows öffnet es sich in einem eigenen Fenster, unter macOS und Linux im Browser. Fügen Sie einen API-Schlüssel für das Modell ein und klicken Sie auf **Prüfen & Chat starten**. Sie haben noch keinen Schlüssel? Die kostenlosen Modelle von OpenRouter sind vorausgewählt, und ihr Schlüssel ist kostenlos. `personagent demo` spielt drei vorgefertigte Szenen ganz ohne Schlüssel ab. Die [Einstiegsanleitung](https://github.com/wangkant/personagent/blob/main/docs/start.de.md) erläutert die Seite Ansicht für Ansicht.

personagent ist kostenlos. Sie bezahlen den gewählten Modelldienst zu dessen eigenen Preisen. Die kostenlosen Modelle von OpenRouter erlauben 50 Anfragen pro Tag, und manche kostenlosen Anbieter speichern, was sie erhalten; Ollama führt ein Modell ganz ohne Schlüssel auf Ihrem eigenen Computer aus.

## In Ihre Gruppe einbinden

Öffnen Sie **Apps verbinden** auf der lokalen Seite:

| Auf der Seite | Apps | Voraussetzung |
|---|---|---|
| Per Scan verbinden | QQ, persönliches WeChat | Ihr Smartphone. WeChat-Bots erhalten nur Einzelchats |
| Ein bis zwei Werte einfügen | Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat, KOOK, Feishu/Lark, DingTalk, Slack, WeCom-KI-Bot, Mattermost, Misskey | Werte aus der Konsole der App; die Seite gibt an, welche |
| Erweitert | WeCom-App, Offizielles WeChat-Konto, QQ-Webhook, OneBot v11 (NapCat), Satori | Eine öffentliche Adresse oder zusätzliche Software auf diesem Computer |

Verbundene Apps werden bei jedem Start von personagent automatisch mitgestartet. Die Apps mit Scan-Verbindung sowie Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK und Stoat verbindet personagent selbst; die übrigen laufen über ein [AstrBot](https://github.com/AstrBotDevs/AstrBot), das personagent herunterlädt und im Hintergrund betreibt. Auf einem Server startet `personagent up` alles ohne Browser. Die Einrichtung für jede App steht im [Benutzerhandbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#in-einen-chat-bringen), und die vollständige Einrichtung von QQ in der [chinesischen Deployment-Anleitung](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

Sie betreiben bereits AstrBot, Koishi oder Matrix? personagent kann als Figur dahinter laufen: siehe [Brücken, die Sie selbst betreiben](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#brücken-die-sie-selbst-betreiben), den [Satori-Konnektor](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.de.md) und den [Matrix-Konnektor](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.de.md).

## Programmierassistenten

**Einrichtung durch einen Programmierassistenten.** Geben Sie die folgende Zeile einem Programmierassistenten, der auf Ihrem Computer Befehle ausführen kann. Ihren Modellschlüssel fügen Sie selbst in die lokale Seite ein, sodass er nie über den Assistenten läuft.

```text
Lies https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md und richte personagent für mich ein.
```

**Mit Ihrer Figur sprechen, während Sie arbeiten.** Claude Code, Codex und DeepSeek Harness (`dsh`) erreichen die Figur, mit demselben Chat und demselben Gedächtnis wie auf der lokalen Seite:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove` entfernt die Verbindung wieder; **Programmierassistenten** unter **Apps verbinden** erledigt beides auch auf der Seite. Das [Benutzerhandbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#programmierassistenten) erklärt die Berechtigungen und `--react`, mit dem die Figur am Ende eines Durchgangs eine kurze Bemerkung macht.

## Aktualisieren und deinstallieren

Wenn auf PyPI eine neuere Version verfügbar ist, zeigt die Seite einen Hinweis mit dem Update-Befehl. Mit pip ist das `python -m pip install -U personagent`. Bei den meisten Installationen führt **Aktualisieren und neu öffnen** in der Ansicht **App** der Seite diesen Befehl für Sie aus. Einstellungen, Figur, Gelerntes und verbundene Apps bleiben erhalten. Um personagent zu entfernen, folgen Sie den [Schritten zur Deinstallation](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (auf Englisch).

## Datenschutz

Alles, was personagent speichert, bleibt auf Ihrem Rechner, in einem Home-Ordner. Der von Ihnen gewählte Modellanbieter sieht die Unterhaltungen, auf die er antwortet, und einmal täglich fragt personagent bei pypi.org nach, ob eine neuere Version vorliegt (`UPDATE_CHECK_ENABLED=false` deaktiviert dies). Bevor Sie die Figur mit echten Menschen verbinden, teilen Sie ihnen mit, dass es sich um einen Bot handelt, und holen Sie ihre Einwilligung ein; das [Handbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#datenschutz-und-einwilligung) listet auf, was wohin geht.

## Dokumentation

- [Benutzerhandbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md): Einrichtung, Konnektoren, Anleitung der Figur, die Ansicht Aktivität, Fehlerbehebung.
- [Deployment-Anleitung](https://github.com/wangkant/personagent/blob/main/docs/deploy.de.md): dauerhafter Betrieb, Kosten und was zu prüfen ist, wenn der Bot verstummt.
- [Konnektor-Protokoll](https://github.com/wangkant/personagent/blob/main/docs/connectors.de.md): zum Schreiben eines eigenen Konnektors.
- [Werkzeuge](https://github.com/wangkant/personagent/blob/main/docs/tools.de.md): die Skripte in `tools/` zur Ausführung aus einem Klon.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Mitwirken](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Sicherheitsrichtlinie](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Haftungsausschluss](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.de.md)

## Lizenz

personagent wird unter der [PolyForm Noncommercial License 1.0.0](https://github.com/wangkant/personagent/blob/main/LICENSE) veröffentlicht, © 2026 Qiankang (Kant) Wang: Nutzung, Änderung und Weitergabe sind für nichtkommerzielle Zwecke kostenlos, für kommerzielle Zwecke nicht gestattet. Die Konnektoren unter `integrations/` bleiben unter der MIT-Lizenz, ebenso die Versionen bis 1.4.0. Die drei Porträts der Figuren stehen unter CC BY-NC-SA 4.0; die Nachweise finden sich in [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Danksagungen

- Andere Chatplattformen werden über [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) mit [satori-python](https://github.com/RF-Tar-Railt/satori-python) sowie [matrix-nio](https://github.com/matrix-nio/matrix-nio) mit den [mautrix-Bridges](https://docs.mau.fi/bridges/) erreicht; die WeChat-Verbindung folgt Tencents [Protokollnotizen zu openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md).
- Das Lernen aus Reaktionen stützt sich auf [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) und [BlenderBot 3x](https://arxiv.org/abs/2306.04707); das Lorebook folgt der World Info von [SillyTavern](https://github.com/SillyTavern/SillyTavern).
