<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent: illustrierte Unterhaltungen" width="100%">
</p>

<h3 align="center">Ein Charakter für deine Gruppenchats, der weiß, wann er besser schweigt, und aus Korrekturen lernt.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="Lizenz: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <strong>Deutsch</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Dies ist eine Übersetzung der englischen README, die maßgeblich ist und aktueller sein kann. Die verlinkten Anleitungen sind auf Englisch.*

personagent ist ein Charakter für deine Gruppenchats: Wähl einen aus oder schreib deinen eigenen und betreib ihn mit einem beliebigen OpenAI-kompatiblen Modell. Mit QQ, WeChat, Telegram und Discord verbindet er sich selbst, mit KOOK, Feishu, DingTalk, Slack, WeCom, Mattermost und Misskey über dieselbe Seite.

Fang in einem lokalen Browser-Chat an: Füge einen Modellschlüssel hinzu und sag Hallo. Wenn du den Charakter in einer Gruppe haben willst, verbinde eine App per Handy-Scan oder mit ein, zwei Werten.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="Die Ansicht Apps verbinden der lokalen Seite mit allen Plattformen, denen er beitreten kann" width="960">
</p>

<p align="center"><em>Apps verbinden, auf derselben lokalen Seite wie Einrichtung und Charakter-Chat. Screenshot aus einer Wegwerf-Installation mit einem lokalen Testmodell.</em></p>

## Los geht's

Installiere es von PyPI und starte es:

```sh
python -m pip install personagent
personagent
```

Mit [uv](https://docs.astral.sh/uv/) startet `uvx personagent` es ohne separaten Installationsschritt.

Der Browser öffnet eine lokale Seite mit drei Ansichten: **Chat**, **Apps verbinden** und **Charakter & Einstellungen**. Füge deinen API-Schlüssel für das Modell ein und klick auf **Prüfen & Chat starten**; eine kleine Anfrage prüft ihn. Es gibt 10 Voreinstellungen für Modelldienste plus jeden anderen OpenAI-kompatiblen Dienst sowie Voreinstellungen für Namen und Persönlichkeit des Charakters. Das Feld **Persona** enthält `persona.txt`; Speichern startet den Agenten neu und behält, was er gelernt hat. **Weitere Funktionen** schaltet Websuche, Bildverständnis und das Von-sich-aus-Ansprechen ein. Ein erneuter Aufruf von `personagent` verwendet eine bereits offene Seite weiter. Über das Menü oben rechts zeigst du die Seite auf Englisch, Chinesisch oder in acht weiteren Sprachen an. Die eingebauten Prompts des Charakters sind Englisch oder Chinesisch; ob er in einer anderen Sprache antwortet, hängt vom Modell ab.

Unter Windows kannst du auch das Quellcode-ZIP herunterladen und `start.bat` doppelklicken. Python 3.10–3.14. Siehe die [kurze Einstiegsanleitung](https://github.com/wangkant/personagent/blob/main/docs/start.md); Terminalbefehle und Connectoren stehen in der [vollständigen Anleitung](https://github.com/wangkant/personagent/blob/main/docs/guide.md).

## Lass deinen Coding-Agenten es einrichten

Ein Coding-Agent, der auf deinem Computer Befehle ausführen kann, kann personagent für dich installieren und einrichten. Gib ihm das hier:

```text
Lies https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md und richte personagent für mich ein.
```

Er fragt nach Sprache, Namen und Persönlichkeit des Charakters, deinem Modelldienst und den gewünschten Chat-Apps, installiert dann personagent, legt den Home-Ordner an und startet die lokale Seite. Deinen Modellschlüssel fügst du selbst in diese Seite ein, sodass er nie durch den Agenten läuft. Die [Anweisungen, denen er folgt](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md), sind schlichtes Markdown, das du ebenfalls lesen kannst.

## Warum personagent

<table>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="" width="220"></td>
<td valign="top">
<strong>Er weiß, wann er besser schweigt.</strong><br>
Er antwortet, wenn er gerufen wird. Ansonsten beurteilt ein Modell, ob ein Mensch sich einklinken würde: kein Würfelwurf.<br>
Auf eine Flut von Nachrichten kommt eine Antwort, nicht eine pro Nachricht.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/learned-notebook.webp" alt="" width="220"></td>
<td valign="top">
<strong>Er lernt aus Korrekturen, die Bestand haben.</strong><br>
Was eine Korrektur lehrt, etwa wie die Gruppe das Fitnessstudio nennt, fließt in jede spätere Antwort in diesem Chat ein.<br>
Eine Änderung braucht zwei übereinstimmende Reaktionen aus demselben Chat, eine davon deutlich.<br>
Ein Troll oder ein Unbeteiligter kann ihn nicht umerziehen.<br>
Jede Änderung wird festgehalten, und jede lässt sich zurücknehmen.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="" width="220"></td>
<td valign="top">
<strong>Er ist schnell gestartet und lebt dort, wo deine Gruppe ist.</strong><br>
Einrichtung und Chat im Browser auf Englisch, Chinesisch oder in acht weiteren Sprachen, mit 11 Modelldiensten und optionalen erweiterten Einstellungen.<br>
Er tritt QQ, WeChat, Telegram und Discord selbst bei und einem Dutzend weiterer Apps über dieselbe Seite; seine Ansicht Aktivität zeigt, was er getan hat.
</td>
</tr>
</table>

- Jeder Chat hat sein eigenes Gedächtnis.
- Wenn du den Charakter bearbeitest, bleibt erhalten, was er gelernt hat.
- Er wird gemessen: `personagent eval` bewertet, wann er spricht, ob er in seiner Rolle bleibt und ob Korrekturen haften bleiben ([Ergebnisse](https://github.com/wangkant/personagent#measured)).

## Bring ihn in deine Gruppe

Öffne **Apps verbinden** auf der lokalen Seite. Dort sind die Apps so gruppiert:

| Auf der Seite | Apps | Was du brauchst |
|---|---|---|
| Per Scan verbinden | QQ, persönliches WeChat | Dein Handy. WeChat-Bots bekommen nur Einzelchats |
| Ein oder zwei Werte einfügen | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, WeCom-KI-Bot, Mattermost, Misskey | Werte aus der Konsole der App; die Seite sagt dir, welche |
| Erweitert | WeCom-App, Offizielles WeChat-Konto, QQ-Webhook, OneBot v11 (NapCat), Satori | Eine öffentliche Adresse oder andere Software auf diesem Computer |

Zugangsdaten werden vor dem Speichern geprüft, und verbundene Apps starten bei jedem Start von personagent wieder mit. personagent verbindet QQ, WeChat, Telegram und Discord selbst; der Rest läuft über ein [AstrBot](https://github.com/AstrBotDevs/AstrBot), das es herunterlädt und im Hintergrund betreibt, ohne dass du sonst etwas öffnen musst. Auf einem Server startet `personagent up` den Charakter und alle verbundenen Apps ohne Browser.

**Du nutzt schon AstrBot, Koishi oder Matrix?** Für ein AstrBot auf diesem Computer installiert `personagent connect astrbot` das Plugin und das gemeinsame Token. Für eines auf einem anderen Rechner lädst du `astrbot_plugin_personagent.zip` aus dem [neuesten Release](https://github.com/wangkant/personagent/releases/latest) auf dessen Plugin-Seite unter **Install from File** hoch und setzt dann sein Token und die HTTPS-Adresse von personagent, wie es die Anleitungen unten beschreiben. [Koishi](https://koishi.chat) wird über den [Satori-Connector](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md) angebunden, und [Matrix](https://matrix.org), mit WhatsApp und Signal hinter mautrix-Bridges, über den [Matrix-Connector](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md).

Die Einrichtung für jede App steht in der [Benutzeranleitung](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat) und der [Deployment-Anleitung](https://github.com/wangkant/personagent/blob/main/docs/deploy.md); die [chinesische Schritt-für-Schritt-Anleitung](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md) behandelt QQ von Grund auf.

## Im Vergleich

Die Projekte, mit denen man es üblicherweise vergleicht, jeweils nach ihrer eigenen Dokumentation im Oktober 2026:

- **AstrBot** (AGPL-3.0) ist ein Bot-Framework für 18+ Plattformen, mit WebUI und großem Plugin-Marktplatz. Es kann ungefragt zufällig antworten (in 10 % der Fälle, standardmäßig aus) und überlässt das Lernen Plugins.
- **MaiBot** (GPL-3.0) ist ein Charakter-Bot für QQ über NapCat, mit WebUI und einem Ein-Klick-Starter. Ein Planer-Modell entscheidet, wie oft er spricht, und er übernimmt Ausdrücke und Slang aus dem Chat.
- **ChatLunas Charakter-Plugin** für Koishi (AGPL-3.0) klinkt sich nach Regeln ein: in festen Abständen, je nachdem, wie viel im Chat los ist, oder wie lange es still war.
- **ElizaOS** (MIT) ist ein Agenten-Framework in TypeScript für Discord, Telegram, Slack und mehr, bei dem ein Modell entscheidet, ob geantwortet wird.

Was personagent eingebaut hat, wo die anderen es Plugins überlassen oder nicht beschreiben: Es lernt daraus, wie Menschen auf seine Antworten reagieren (Korrekturen, Ablehnungen, akzeptierte Neuversuche); eine Änderung braucht zwei übereinstimmende Reaktionen aus demselben Chat, eine davon deutlich; jede Änderung wird protokolliert und lässt sich zurücknehmen; und sein Verhalten wird in einer veröffentlichten Evaluation gemessen ([unten](https://github.com/wangkant/personagent#measured)).

Wo die anderen vorn liegen: Desktop-Apps mit allen Einstellungen in einer WebUI, große Plugin-Ökosysteme sowie Slang, Sticker-Pakete und Bildgedächtnis. Wenn du schon AstrBot oder Koishi betreibst, musst du dich nicht entscheiden: personagent kann hinter beiden als Charakter laufen.

## Gemessen

`personagent eval` schickt den echten Agenten durch gelabelte Chat-Momente. Der jüngste Durchlauf am 2026-10-18 testete den mitgelieferten Charakter auf zwei Modellen über OpenRouter, probierte jeden Fall dreimal und ließ Claude Opus 5.5 blind urteilen. Englisch / Chinesisch:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Richtig darin, wann er spricht (60 Momente) | 83 % / 80 % | 93 % / 91 % |
| Spielt den Charakter besser als dasselbe Modell nur mit seinem Prompt (40 Momente) | 63 % / 58 % | 75 % / 53 % |
| Nutzt, was eine Korrektur gelehrt hat, in einer späteren, anders formulierten Nachricht | 76 % / 56 % | 71 % / 67 % |

- Er ignoriert selten eine Nachricht, die an ihn gerichtet ist. Die meisten Fehlgriffe sind Fälle, in denen sein Name etwas anderes meint, etwa ein Kino oder einen Welpen.
- Auf Chinesisch liegt sein Vorsprung gegenüber dem bloßen Prompt im Rauschen.
- Bevor Korrekturen ihre Lektion behielten, was nach dem ersten Durchlauf an jenem Tag behoben wurde, nutzten nur 2 von 58 späteren Nachrichten sie.
- Keine Korrektur von Trollen, Unbeteiligten oder Leuten, die schon gegangen waren, kam durch, in 84 Versuchen.

Die [vollständigen Ergebnisse](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) enthalten die Intervalle, die Fehlgriffe nach Art, die Methode, was die Zahlen nicht zeigen, und jeden Bericht.

## Dokumentation

- [Benutzeranleitung](https://github.com/wangkant/personagent/blob/main/docs/guide.md) ([中文](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)): Installation, Einrichtung, der Terminal-Chat, Connectoren, ihm etwas beibringen, die Ansicht Aktivität, Fehlerbehebung.
- [Deployment-Anleitung](https://github.com/wangkant/personagent/blob/main/docs/deploy.md): Betrieb im Ernstfall: Connectoren, QQ, die Endpunkte erreichbar machen, Kosten und was zu prüfen ist, wenn der Bot verstummt.
- [中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md): QQ von Grund auf, Schritt für Schritt.
- [Connector-Protokoll](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): eine signierte HTTP-Anfrage pro Nachricht, um einen eigenen Connector zu schreiben.
- [Tools](https://github.com/wangkant/personagent/blob/main/docs/tools.md): die Skripte in `tools/`, zum Ausführen aus einem Klon.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md), einschließlich [Upgrade von 0.4](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04).
- [Mitwirken](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Sicherheitsrichtlinie](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Haftungsausschluss](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## Datenschutz

Alles, was personagent speichert, bleibt auf deinem Rechner, in einem Home-Ordner: `.env` mit deinen Schlüsseln, `persona.txt`, `runtime/` und `platforms/` mit dem verwalteten AstrBot und den Zugangsdaten der direkten Verbindungen. Der Modellanbieter, den du wählst, sieht die Unterhaltungen, auf die er antwortet, und einmal am Tag fragt personagent bei pypi.org nach, ob es eine neuere Version gibt (`UPDATE_CHECK_ENABLED=false` schaltet das ab). Bevor du ihn mit echten Menschen verbindest, sag ihnen, dass es ein Bot ist, und hol ihre Einwilligung ein; die [Anleitung](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) listet genau auf, was wohin geht.

## Status

1.3.0 ist auf PyPI, veröffentlicht am 2026-10-18. QQ ist die am meisten erprobte Plattform, in 1.0 über AstrBot und seit 1.1 direkt. Die Verbindungen zu WeChat, Telegram und Discord prüfen Zugangsdaten vor dem Speichern gegen die echten Dienste und sind ansonsten gegen Attrappen getestet; die Satori- und Matrix-Connectoren sind gegen Attrappen getestet. Die CI führt die Tests unter Linux mit Python 3.10–3.14 und unter Windows mit Python 3.12 aus, dazu Jobs, die das Paket installieren und den Befehl sowie die lokale Seite steuern.

## Lizenz

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## Danksagungen

- Andere Chatplattformen werden über [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) mit [satori-python](https://github.com/RF-Tar-Railt/satori-python) sowie [matrix-nio](https://github.com/matrix-nio/matrix-nio) mit den [mautrix-Bridges](https://docs.mau.fi/bridges/) erreicht; die WeChat-Verbindung folgt Tencents [Protokollnotizen zu openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md).
- Das Lernen aus Reaktionen stützt sich auf [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) und [BlenderBot 3x](https://arxiv.org/abs/2306.04707); das Lorebook folgt der World Info von [SillyTavern](https://github.com/SillyTavern/SillyTavern).
