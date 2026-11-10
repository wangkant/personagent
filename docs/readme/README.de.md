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
Eine Änderung braucht zwei übereinstimmende Reaktionen aus demselben Chat, eine davon deutlich.<br>
Ein Troll oder ein Unbeteiligter kann ihn nicht umerziehen.<br>
Jede Änderung wird festgehalten, und jede lässt sich zurücknehmen.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Er ist schnell gestartet und lebt dort, wo deine Gruppe ist.</strong></td>
<td valign="top">
Ein Befehl öffnet ihn auf deinem Rechner, auf Englisch, Chinesisch oder in acht weiteren Sprachen.<br>
Füge einen Modellschlüssel ein und chatte los: Zehn Modelldienste sind voreingestellt, und jeder andere OpenAI-kompatible funktioniert ebenfalls.<br>
Verbinde eine App per Handy-Scan oder mit ein, zwei eingefügten Werten. Die Ansicht Aktivität zeigt, was der Charakter dort getan hat.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Er kann ein fertiger Charakter sein oder dein eigener.</strong></td>
<td valign="top">
Sieben fertige Persönlichkeiten. Drei davon sind Figuren, die die Community längst zeichnet: das DeepSeek-Walmädchen, das GPT-Drachenmädchen und die Claude-Dame, mit Porträts, die blinzeln, nachdenken, während eine Antwort unterwegs ist, und sprechen, wenn sie ankommt.<br>
Schreib die Persona um, wann immer du willst. Was der Charakter gelernt hat, bleibt erhalten.
</td>
</tr>
</table>

- Jeder Chat hat sein eigenes Gedächtnis, und auf Wunsch vergisst er wieder: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian`, `Nova, what do you remember` ([Gedächtnis-Befehle](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#gedächtnis-befehle)). Was eine Gruppe über jemanden notiert hat, folgt dieser Person in ihren Direktchat mit ihm, aber nie umgekehrt.
- Er antwortet in der Sprache, die im Chat gesprochen wird. Start-Personas gibt es in jeder der zehn Sprachen der Seite; die mitgelieferten Beispiele, Filter und Prompts sind Englisch und Chinesisch.
- Er wird gemessen: `personagent eval` bewertet, wann er spricht, ob er in seiner Rolle bleibt und ob Korrekturen haften bleiben ([Ergebnisse](https://github.com/wangkant/personagent#measured)).

## Los geht's

```sh
python -m pip install personagent
personagent
```

Mit [uv](https://docs.astral.sh/uv/) startet `uvx personagent` es ohne separaten Installationsschritt. Unter Windows kannst du auch das Quellcode-ZIP herunterladen und `start.bat` doppelklicken; das legt auch ein personagent-Symbol auf deinen Desktop. personagent wird unter Linux mit Python 3.10–3.14 und unter Windows mit Python 3.12 getestet.

Unter Windows öffnet es sich in einem eigenen Fenster. Unter macOS und Linux öffnet es sich im Browser, nach `pip install "personagent[app]"` ebenfalls in einem Fenster. Füge einen API-Schlüssel für das Modell ein und klick auf **Prüfen & Chat starten**; eine kleine Anfrage prüft den Schlüssel. Noch keinen Schlüssel? Die kostenlosen Modelle von OpenRouter sind vorausgewählt, und ihr Schlüssel kostet nichts. Willst du ihn erst einmal sehen, bevor du dir überhaupt einen Schlüssel holst, spielt `personagent demo` kostenlos drei vorgefertigte Szenen ab. Die [Einstiegsanleitung](https://github.com/wangkant/personagent/blob/main/docs/start.de.md) führt Bildschirm für Bildschirm durch die Seite.

## Was es kostet

personagent ist kostenlos. Du bezahlst den Modelldienst, den du wählst, zu dessen eigenen Preisen.

- **Kostenlos loslegen.** Die kostenlosen Modelle von OpenRouter erlauben 50 Anfragen pro Tag; das Modell kann von Anfrage zu Anfrage wechseln, und manche kostenlosen Anbieter behalten, was sie erhalten. `glm-4.7-flash` von Zhipu ist ebenfalls kostenlos, und Ollama lässt ein Modell ganz ohne Schlüssel auf deinem eigenen Computer laufen.
- **Was das Modell aufruft.** Jede Antwort und zwei kleinere Schritte: die Entscheidung, ob er sich einklinkt, wenn ihn niemand gerufen hat, und die Einschätzung, wie Menschen auf seine Antworten reagieren. Auch `personagent doctor` und `personagent eval` senden Anfragen; den Rest findest du in der [Deployment-Anleitung](https://github.com/wangkant/personagent/blob/main/docs/deploy.de.md#kosten).
- **Was es nie tut.** `personagent demo` und die Gedächtnis-Befehle.

## Bring ihn in deine Gruppe

Öffne **Apps verbinden** auf der lokalen Seite. Dort sind die Apps so gruppiert:

| Auf der Seite | Apps | Was du brauchst |
|---|---|---|
| Per Scan verbinden | QQ, persönliches WeChat | Dein Handy. WeChat-Bots bekommen nur Einzelchats |
| Ein oder zwei Werte einfügen | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, WeCom-KI-Bot, Mattermost, Misskey | Werte aus der Konsole der App; die Seite sagt dir, welche |
| Erweitert | WeCom-App, Offizielles WeChat-Konto, QQ-Webhook, OneBot v11 (NapCat), Satori | Eine öffentliche Adresse oder andere Software auf diesem Computer |

Zugangsdaten werden vor dem Speichern geprüft, und verbundene Apps starten bei jedem Start von personagent wieder mit. Die Apps mit Scan-Verbindung, Telegram und Discord verbindet personagent selbst; der Rest läuft über ein [AstrBot](https://github.com/AstrBotDevs/AstrBot), das es herunterlädt und im Hintergrund betreibt, ohne dass du sonst etwas öffnen musst. Auf einem Server startet `personagent up` den Charakter und alle verbundenen Apps ohne Browser. Die Einrichtung für jede App steht im [Benutzerhandbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#in-einen-chat-bringen), und QQ von null an, Schritt für Schritt, in der [chinesischen Deployment-Anleitung](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

Du betreibst schon eine Brücke?

- **AstrBot**: `personagent connect astrbot` installiert das Plugin und das gemeinsame Token. Das [Handbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#brücken-die-du-selbst-betreibst) beschreibt auch ein AstrBot auf einem anderen Rechner.
- **[Koishi](https://koishi.chat)** oder ein beliebiger Satori-Server: der [Satori-Connector](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.de.md).
- **[Matrix](https://matrix.org)**, mit WhatsApp und Signal hinter mautrix-Bridges: der [Matrix-Connector](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.de.md).

## Coding-Agenten

**Lass einen die Einrichtung übernehmen.** Gib die Zeile unten einem Coding-Agenten, der auf deinem Computer Befehle ausführen kann. Er fragt, was du möchtest, installiert personagent und startet die lokale Seite. Deinen Modellschlüssel fügst du selbst in diese Seite ein, sodass er nie durch den Agenten läuft.

```text
Lies https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md und richte personagent für mich ein.
```

**Sprich mit deinem Charakter, während du arbeitest.** Sobald ein Modellschlüssel eingerichtet ist, erreichen Claude Code, Codex und DeepSeek Harness (`dsh`) den Charakter:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

Öffne dort eine neue Sitzung (DeepSeek Harness vorher neu starten) und bitte den Agenten, deinem Charakter etwas zu sagen. Es ist derselbe Einzelchat mit demselben Gedächtnis wie auf der lokalen Seite. In Claude Code und Codex lässt `--react` den Charakter am Ende eines Durchgangs einen Satz sagen. `--remove` nimmt alles wieder heraus. Das [Benutzerhandbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#coding-agenten) erklärt die Berechtigungen, was `--react` an deinen Modelldienst sendet, und andere MCP-fähige Werkzeuge.

## Gemessen

`personagent eval` schickt den echten Agenten durch gelabelte Chat-Momente. Der jüngste Durchlauf am 2026-10-18 wurde mit 1.3.0 gemessen: der mitgelieferte Charakter auf zwei Modellen über OpenRouter, jeder Fall dreimal probiert, mit Claude Opus 5.5 als blindem Richter. Englisch / Chinesisch:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Richtig darin, wann er spricht (60 Momente) | 83 % / 80 % | 93 % / 91 % |
| Spielt den Charakter besser als dasselbe Modell nur mit seinem Prompt (40 Momente) | 63 % / 58 % | 75 % / 53 % |
| Nutzt, was eine Korrektur gelehrt hat, in einer späteren, anders formulierten Nachricht | 76 % / 56 % | 71 % / 67 % |

- Er ignoriert selten eine Nachricht, die an ihn gerichtet ist. Die meisten Fehlgriffe sind Fälle, in denen sein Name etwas anderes meint, etwa ein Kino oder einen Welpen.
- Keine von 84 Korrekturen von Trollen, Unbeteiligten oder Leuten, die schon gegangen waren, kam durch.

Die [vollständigen Ergebnisse](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) enthalten die Intervalle, die Fehlgriffe nach Art, die Methode und jeden Bericht.

## Im Vergleich

Projekte, mit denen es oft verglichen wird, Stand November 2026:

- **AstrBot** (AGPL-3.0) ist ein Bot-Framework für mehr als ein Dutzend Plattformen, mit WebUI und großem Plugin-Marktplatz. Es kann ungefragt zufällig antworten (in 10 % der Fälle, standardmäßig aus) und überlässt das Lernen Plugins.
- **MaiBot** (GPL-3.0) ist ein Charakter-Bot für QQ über NapCat, mit WebUI und einem Ein-Klick-Starter. Ein Planer-Modell entscheidet, wie oft er spricht, und er übernimmt Ausdrücke und Slang aus dem Chat.
- **ChatLunas Charakter-Plugin** für Koishi (AGPL-3.0) klinkt sich nach Regeln ein: in festen Abständen, je nachdem, wie viel im Chat los ist, oder wie lange es still war.
- **ElizaOS** (MIT) ist ein Agenten-Framework in TypeScript für Discord, Telegram, Slack und mehr, bei dem ein Modell entscheidet, ob geantwortet wird.

Was personagent eingebaut hat: Es lernt daraus, wie Menschen auf seine Antworten reagieren (Korrekturen, Ablehnungen, akzeptierte Neuversuche), protokolliert jede Änderung so, dass sie sich zurücknehmen lässt, und veröffentlicht eine Evaluation seines Verhaltens.

Wo die anderen vorn liegen: Desktop-Apps mit allen Einstellungen in einer WebUI, große Plugin-Ökosysteme sowie Slang, Sticker-Pakete und Bildgedächtnis. Wenn du schon AstrBot oder Koishi betreibst, musst du dich nicht entscheiden: personagent kann hinter beiden als Charakter laufen.

## Aktualisieren und deinstallieren

Wenn auf PyPI eine neuere Version liegt, zeigt die Seite einen Hinweis mit dem Update-Befehl, der zu deiner Installationsart passt. Mit pip ist das `python -m pip install -U personagent`. Der Home-Ordner bleibt erhalten: Einstellungen, Charakter, Gelerntes und verbundene Apps.

Um es zu entfernen, nimm es zuerst aus jedem Coding-Agenten heraus, den du verbunden hast (`personagent connect claude-code --remove`, oder dasselbe mit `codex` oder `dsh`). Beende dann personagent und führe `python -m pip uninstall personagent` aus. Lösch zuletzt den Home-Ordner; bei einer Installation von PyPI ist das `~/personagent`, sofern du keinen anderen gewählt hast. Er enthält deinen Schlüssel, den Charakter und alles, was er gelernt hat, das lässt sich also nicht rückgängig machen. Die [vollständigen Schritte](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (auf Englisch) behandeln uv, pipx und was du widerrufen solltest.

## Datenschutz

Alles, was personagent speichert, bleibt auf deinem Rechner, in einem Home-Ordner: `.env` mit deinen Schlüsseln, `persona.txt`, `runtime/` und `platforms/` mit dem verwalteten AstrBot und den Zugangsdaten der direkten Verbindungen. Der Modellanbieter, den du wählst, sieht die Unterhaltungen, auf die er antwortet, und einmal am Tag fragt personagent bei pypi.org nach, ob es eine neuere Version gibt (`UPDATE_CHECK_ENABLED=false` schaltet das ab). Bevor du ihn mit echten Menschen verbindest, sag ihnen, dass es ein Bot ist, und hol ihre Einwilligung ein; das [Handbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md#datenschutz-und-einwilligung) listet auf, was wohin geht.

## Dokumentation

- [Benutzerhandbuch](https://github.com/wangkant/personagent/blob/main/docs/guide.de.md): Installation, Einrichtung, der Terminal-Chat, Connectoren, ihm etwas beibringen, die Ansicht Aktivität, Fehlerbehebung.
- [Deployment-Anleitung](https://github.com/wangkant/personagent/blob/main/docs/deploy.de.md): Betrieb im Ernstfall: Connectoren, QQ, die Endpunkte erreichbar machen, Kosten und was zu prüfen ist, wenn der Bot verstummt.
- [Connector-Protokoll](https://github.com/wangkant/personagent/blob/main/docs/connectors.de.md): eine signierte HTTP-Anfrage pro Nachricht, um einen eigenen Connector zu schreiben.
- [Tools](https://github.com/wangkant/personagent/blob/main/docs/tools.de.md): die Skripte in `tools/`, zum Ausführen aus einem Klon.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Mitwirken](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Sicherheitsrichtlinie](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Haftungsausschluss](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.de.md)

## Lizenz

Der Code steht unter [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang. Die drei Charakterporträts stehen unter CC BY-NC-SA 4.0; die Nachweise finden sich in [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Danksagungen

- Andere Chatplattformen werden über [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) mit [satori-python](https://github.com/RF-Tar-Railt/satori-python) sowie [matrix-nio](https://github.com/matrix-nio/matrix-nio) mit den [mautrix-Bridges](https://docs.mau.fi/bridges/) erreicht; die WeChat-Verbindung folgt Tencents [Protokollnotizen zu openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md).
- Das Lernen aus Reaktionen stützt sich auf [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) und [BlenderBot 3x](https://arxiv.org/abs/2306.04707); das Lorebook folgt der World Info von [SillyTavern](https://github.com/SillyTavern/SillyTavern).
