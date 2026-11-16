# personagent-Benutzerhandbuch

[English](guide.md) · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · [日本語](guide.ja.md) · [한국어](guide.ko.md) · [Español](guide.es.md) · [Français](guide.fr.md) · Deutsch · [Português (Brasil)](guide.pt-BR.md) · [Русский](guide.ru.md)

Dieses Handbuch erklärt, wie Sie personagent einrichten, in Ihre Chats einbinden, ihm etwas beibringen und es betreuen. Das [README](readme/README.de.md) ist die Kurzfassung, und [Erste Schritte](start.de.md) erläutert die lokale Seite Ansicht für Ansicht.

1. [Installation und der personagent-Ordner](#installation-und-der-personagent-ordner)
2. [Die lokale Seite](#die-lokale-seite): [Erweiterte Einstellungen](#erweiterte-einstellungen) · [Die Ansicht App](#die-ansicht-app)
3. [Erst ansehen: die Demo](#erst-ansehen-die-demo)
4. [Terminal-Befehle](#terminal-befehle): [Einrichtung](#im-terminal-einrichten) · [Plattform verbinden](#eine-plattform-im-terminal-verbinden) · [Chat](#im-terminal-chatten) · [den Dienst ausführen](#den-dienst-ausführen)
5. [Die eigene Figur gestalten](#die-eigene-figur-gestalten)
6. [In einen Chat bringen](#in-einen-chat-bringen): [Freigabe neuer Chats](#wem-die-figur-antwortet-freigabe-neuer-chats) · [Plattformen, die personagent selbst verbindet](#plattformen-die-personagent-selbst-verbindet) · [Andere Plattformen](#andere-plattformen-über-das-verwaltete-astrbot) · [Brücken, die Sie selbst betreiben](#brücken-die-sie-selbst-betreiben) · [Zuerst sprechen](#zuerst-sprechen)
7. [Werkzeuge](#werkzeuge)
8. [Programmierassistenten](#programmierassistenten)
9. [Andere Software](#andere-software)
10. [Der Figur etwas beibringen](#der-figur-etwas-beibringen)
11. [Gedächtnis](#gedächtnis)
12. [Aktivität](#aktivität)
13. [Messen](#messen)
14. [Wie es funktioniert](#wie-es-funktioniert)
15. [Datenschutz und Einwilligung](#datenschutz-und-einwilligung)
16. [Fehlerbehebung](#fehlerbehebung)
17. [Upgrade von 0.x](#upgrade-von-0x)
18. [Status und weitere Dokumente](#status-und-weitere-dokumente)

## Installation und der personagent-Ordner

```sh
python -m pip install personagent
personagent
```

`personagent` öffnet [die lokale Seite](#die-lokale-seite). Sie können es auch auf folgende Arten installieren oder starten:

| Weg | Befehl |
|---|---|
| Ohne Installation ausführen | `uvx personagent` (Teil von [uv](https://docs.astral.sh/uv/), das bei Bedarf auch Python bereitstellt) |
| Ein dauerhafter `personagent`-Befehl | `uv tool install personagent` oder `pipx install personagent` |
| Windows, aus dem Quellcode-ZIP | entpacken und `start.bat` doppelklicken |
| Aus einem Klon | `git clone https://github.com/wangkant/personagent.git`, `cd personagent`, `python -m venv .venv`, dann `.venv/bin/python -m pip install -e .` und `.venv/bin/python -m persona_agent` (unter Windows `.venv\Scripts\python.exe`) |

personagent läuft auf Python 3.10–3.14. `start.bat` erstellt `.venv`, installiert die Abhängigkeiten und öffnet dieselbe Seite; beim ersten Start legt es außerdem ein personagent-Symbol auf dem Desktop und im Startmenü an. Die Abhängigkeiten werden neu installiert, sobald sich die Abhängigkeitsliste in `pyproject.toml` ändert.

Der **personagent-Ordner** enthält die Einstellungen (`.env`), die Figur (`persona.txt`), was sie lernt (`runtime/`) und die Chat-Plattformen (`platforms/`). `platforms/` enthält das verwaltete AstrBot und `direct.json`, das die Zugangsdaten der Plattformen speichert, die personagent selbst verbindet. personagent verwendet den ersten der folgenden Ordner:

1. den Ordner aus `--home DIR` oder `AGENT_HOME`. `--home` kann vor oder nach dem Befehl stehen, wie bei `personagent chat --home D:\bot`.
2. den Klon, wenn Sie personagent aus einem Klon starten.
3. den aktuellen Ordner, wenn er sowohl `.env` als auch `persona.txt` enthält.
4. `~/personagent`, das bei der ersten Einrichtung angelegt wird.

Um mehrere Figuren aus einer Installation zu betreiben, geben Sie jedem einen eigenen personagent-Ordner.

Dieses Handbuch gibt Befehle als `personagent ...` an. Wenn Sie personagent nicht installiert haben, stellen Sie `uvx` voran. In einem Klon bewirkt `.venv/bin/python -m persona_agent ...` dasselbe (unter Windows `.venv\Scripts\python.exe -m persona_agent ...`).

## Die lokale Seite

`personagent` (oder `personagent start`) stellt eine Seite bereit, die nur von diesem Computer erreichbar ist. Unter Windows öffnet sie sich in einem eigenen Fenster. Unter macOS und Linux öffnet sie sich im Browser oder ebenfalls in einem Fenster, sobald `pip install "personagent[app]"` [pywebview](https://pywebview.flowrl.com/) hinzugefügt hat, unter Linux zusammen mit Qt. Die Seite hat sechs Ansichten, die in der Seitenleiste in dieser Reihenfolge stehen:

- **Chat** ist ein Einzelgespräch mit der Figur auf der Seite. Derselbe Agent, der Ihre Chat-Plattformen bedient, antwortet hier. In diesem Chat sind Sie der Administrator. Sticker und Bilder, die die Figur sendet, erscheinen im Chat; an der Stelle eines Bildes, das nicht mehr gespeichert ist, steht ein kurzer Hinweis. Nachrichten, die die Figur nach ihrer Antwort sendet, etwa die Antwort auf einen Gedächtnis-Befehl, der während ihrer Antwort gesendet wurde, oder eine Nachricht, die sie von sich aus beginnt, erscheinen innerhalb weniger Sekunden, solange die Ansicht **Chat** geöffnet ist. Beides bleibt im Verlauf des Chats erhalten. Antwortet das Modell nicht, weist die Seite an der Stelle der Antwort darauf hin und bietet **Erneut senden** an. **Gedächtnisbefehle** unterhalb des Eingabefelds listet die [Gedächtnis-Befehle](#gedächtnis-befehle) auf; wenn Sie einen davon auswählen, wird er in das Eingabefeld eingefügt. **Chats dieser Seite vergessen** vergisst alles, was sich die Figur aus diesem Chat und den früheren Chats der Seite merkt, und beginnt einen neuen Chat; was sie sich aus Chats in verbundenen Apps merkt, bleibt erhalten, und das Vergessen lässt sich nicht rückgängig machen. Dafür sind die Daten hinter [Aktivität](#aktivität) erforderlich. **Neuer Chat** beginnt einen neuen Chat und behält, was sich die Figur merkt.
- **Aktivität** zeigt die Chats, in denen die Figur aktiv ist, was sie zuletzt gesagt hat, was sie sich merkt und was sie gelernt hat. Siehe [Aktivität](#aktivität).
- **Plattformen verbinden** bringt die Figur in QQ, WeChat, Telegram, Discord und weitere Plattformen. Siehe [In einen Chat bringen](#in-einen-chat-bringen). Ganz unten verbindet **Programmierassistenten** die Figur mit den [Programmierassistenten](#programmierassistenten) auf diesem Computer.
- **Figur & Einstellungen** ist der Ort, an dem Sie einen Modelldienst auswählen (OpenRouter, DeepSeek, SiliconFlow, Alibaba Bailian, Zhipu GLM, Moonshot, Volcengine Ark, OpenAI, Google Gemini, Ollama oder jeden anderen OpenAI-kompatiblen Dienst), den API-Schlüssel einfügen und einen Namen und eine fertige Persönlichkeit wählen. **Prüfen & Chat starten** testet den Schlüssel mit einer kleinen Anfrage und speichert ihn nur, wenn sie gelingt. Ist OpenRouter gewählt, holt **Mit OpenRouter anmelden** den Schlüssel stattdessen ab: Der Browser zeigt die Freigabe von OpenRouter, OpenRouter leitet den Browser zurück an die eigene Adresse der Seite auf diesem Computer (`http://localhost:<port>/signin/openrouter`), und personagent tauscht den einmaligen Code gegen einen Schlüssel ein, prüft ihn auf dieselbe Weise und speichert ihn mit den übrigen Angaben des Formulars. Der Schlüssel durchläuft nie die Seite selbst. Sobald ein Schlüssel funktioniert, bietet der Modellname die Modelle an, die der Dienst auflistet (mit dem gespeicherten Schlüssel unter `<API-Adresse>/models` gelesen und fünf Minuten lang vorgehalten); bei einem Dienst, der keine auflistet, bleibt das Feld unverändert. Nach der Einrichtung zeigt das Feld **Persona** `persona.txt`. **Persona speichern** startet den Agenten mit dem neuen Text neu und behält, was er gelernt hat. **Weitere Funktionen** schaltet die Websuche über Tavily (DuckDuckGo ist die kostenlose Voreinstellung), die Bilderkennung und eigene Gesprächsanstöße auf den von Ihnen gewählten Plattformen ein. **Werkzeuge** darunter fügt [Werkzeuge von MCP-Servern](#werkzeuge) hinzu. Darauf folgen die [Erweiterten Einstellungen](#erweiterte-einstellungen).
- **Übung** spielt die vorgefertigte Demo ab und stellt einen Übungsgruppenchat bereit. Siehe [Erst ansehen: die Demo](#erst-ansehen-die-demo).
- **App** prüft die Dienste, auf die die Figur angewiesen ist, und bündelt die Protokolle, die Ausführung im Hintergrund, die Updates und Ihre Daten. Siehe [Die Ansicht App](#die-ansicht-app).

**Übung** und **App** lassen sich bereits öffnen, bevor ein Modell eingerichtet ist. Solange Sie keine Plattform verbunden haben, zeigt die Ansicht **Chat** eine kurze Leiste **Erste Schritte**.

Ein erneuter Aufruf von `personagent` holt die bereits geöffnete Seite wieder in den Vordergrund. `--browser` öffnet die Seite im Browser statt in einem Fenster, und `--no-browser` gibt den Link aus und öffnet nichts. Unter Windows legt `personagent shortcut` ein Symbol auf den Desktop und ins Startmenü, das das Fenster ohne Terminal dahinter öffnet, und `personagent shortcut --remove` entfernt es wieder. Die Ansicht **App** bietet dieselbe Funktion.

Wenn auf PyPI eine neuere Version von personagent verfügbar ist, zeigt die Ansicht **Chat** einen Hinweis mit dem Befehl, der Ihre Installation aktualisiert, ob sie aus pip, uvx, uv tool, pipx oder einem Git-Klon stammt. Bei einem entpackten Quellcode-ZIP verweist der Hinweis stattdessen auf die Release-Seite. Das Terminal gibt denselben Befehl aus. Das Schließen des Hinweises blendet ihn für diese Version aus, und **N verfügbar** unter der Versionsnummer zeigt ihn wieder an. `personagent up` und `personagent doctor` melden ebenfalls eine neue Version. Die Seite und `up` fragen pypi.org höchstens einmal täglich im Hintergrund ab. `doctor` fragt sofort ab, wenn die letzte Antwort älter als ein Tag ist. Setzen Sie `UPDATE_CHECK_ENABLED=false`, um die Prüfung zu deaktivieren. Die Ansicht **App** kann das Update auch selbst installieren; siehe [Version und Updates](#version-und-updates).

Die Seite startet den Agenten und die verbundenen Plattformen im Hintergrund; lassen Sie ihr Fenster daher geöffnet, während Sie sie verwenden. Alles, was sie gestartet hat, wird mit ihr beendet, unabhängig davon, ob Sie auf **Beenden** klicken, Strg+C drücken oder das Fenster schließen. Solange eine Plattform verbunden ist, erfolgt vor dem Schließen des Fensters eine Rückfrage. Unter Windows lässt sich stattdessen festlegen, dass personagent nach dem Schließen des Fensters weiterläuft; siehe [Im Hintergrund ausführen](#im-hintergrund-ausführen). Wenn ein früherer Lauf abgestürzt ist und Prozesse hinterlassen hat, beendet der nächste Start sie zuerst.

### Erweiterte Einstellungen

Sobald ein Modell eingerichtet ist, endet **Figur & Einstellungen** mit **Erweiterte Einstellungen**. Dieser Bereich enthält in sechs Abschnitten Einstellungen, die bisher nur in `.env` verfügbar waren. Alle sind optional und haben einen Standardwert; ein leeres Feld verwendet den Standardwert.

| Abschnitt | Einstellungen |
|---|---|
| **Antworten, Administrator und Zugriff** | **Auf Nachrichten antworten** (`AGENT_ENABLED`); **In diesen Gruppen schweigen** (`ACCESS_PAUSED_GROUPS`); Wie die Figur Sie nennt und in welcher Beziehung Sie zu ihr stehen (`ADMIN_NAME`, `ADMIN_RELATIONSHIP`); **Ihre Konten** (`ADMIN_IDS`); **Nur in diesen Gruppen antworten** (`ACCESS_GROUPS`); **Weitere Personen mit Erlaubnis für Direktnachrichten** (`ACCESS_DM_USERS`); **Plattformen, auf denen neue Chats eine Freigabe benötigen** (`ACCESS_APPROVAL_PLATFORMS`). **Aus letzten Chats auswählen** listet die Personen und Gruppen aus Aktivität auf, sodass Sie deren Kennungen hinzufügen können, ohne sie einzutippen. |
| **Sprechen und Antwortstil** | **Zeitzone** (`PERSONA_TZ_OFFSET_HOURS`); **In Gruppen nur antworten, wenn angesprochen** (`CHAT_ONLY_WHEN_CALLED`); **Nachrichten vor einer Beteiligung** (`CHAT_TRIGGER_COUNT`); **Häufigkeit eigener Gesprächsanstöße**, womit die sieben `PROACTIVE_*`-Zeitwerte auf einmal festgelegt werden; **Antwortstil**: Emojis, drei Sonderzeichen und die maximale Antwortlänge, gespeichert in `persona.card.json`. |
| **Modelle** | Ein Ersatzmodell mit eigener Dienstadresse und eigenem Schlüssel (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`), das Modell für schnelle Entscheidungen (`LLM_JUDGE_MODEL`) und das Modell für Direktnachrichten (`LLM_DM_MODEL`). Das Ersatzmodell wird vor dem Speichern getestet. |
| **Lernen** | `REACT_LEARN_ENABLED`, `REACT_LEARN_ADMIN_ONLY`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED`, `PROMOTE_MIN_SPEAKERS` (1 oder 2), `PROMOTE_JUDGE_ENABLED` (die Figur entscheidet, was Reaktionen nicht klären können) und `PROMOTE_OBSERVE_MAX_DAYS` (Tage ohne neue Reaktion, nach denen ein Eintrag in Beobachtung zurückgestellt wird). **Lernen neu beginnen** schreibt eine neue `PERSONA_VERSION`, sodass das bisher Gelernte nicht mehr verwendet wird. Gelöscht wird nichts. |
| **Gedächtnis** | `MEMORY_CALLS_PER_DAY`, `MEMORY_TIDY_EVERY`, `CHAT_CONTEXT_MESSAGES`, `MEMORY_PROMPT_CHARS`, `MEMORY_EPISODES_MAX`, `MEMORY_KEEP_RECENT` und `MEMORY_LOG_DAYS`. Siehe [Gedächtnis](#gedächtnis). |
| **Weitere Einstellungen** | `DASHBOARD_ENABLED`, `UPDATE_CHECK_ENABLED`, die sieben `PROACTIVE_*`-Zeitwerte, `CHAT_FOLLOWUP_WINDOW_S`, die Grenzwerte für `REACT_*` und `PROMOTE_*`, `REACT_MODEL`, das Modell, das Intervall und die Stapelgröße der eigenen Entscheidungen der Figur (`PROMOTE_JUDGE_MODEL`, `PROMOTE_JUDGE_INTERVAL_S`, `PROMOTE_JUDGE_BATCH`) und `PERSONA_VERSION`. |

**Erweiterte Einstellungen speichern** schreibt nur die geänderten Einstellungen und lässt den Rest von `.env` unverändert. Anschließend wird die Figur neu gestartet, außer wenn `UPDATE_CHECK_ENABLED` die einzige Änderung ist. Vor dem Abschalten der Antworten (`AGENT_ENABLED`) erfolgt eine Rückfrage. Dasselbe gilt für das Umbenennen der Figur unter **Name der Figur**, denn ein neuer Name beginnt eine neue Figur. **Erweiterte Einstellungen speichern** lehnt unter **Ihre Konten**, **Nur in diesen Gruppen antworten**, **In diesen Gruppen schweigen** oder **Weitere Personen mit Erlaubnis für Direktnachrichten** einen Eintrag ab, der kein Konto bezeichnet: Ein Eintrag ohne Präfix muss eine QQ-Nummer sein, und vor dem Doppelpunkt muss der Name einer Plattform stehen, wie in `telegram:-1001234567890`.

### Die Ansicht App

**App** trägt einen roten Punkt, wenn etwas Ihre Aufmerksamkeit erfordert: Ein Dienst konnte nicht starten, eine Einstellung hat einen alten Namen oder einen Fehler, eine Plattformverbindung ist fehlgeschlagen, oder die letzte Prüfung ist fehlgeschlagen.

**Systemprüfung.** **Prüfung starten** testet jeden Dienst, auf den die Figur angewiesen ist: das Chatmodell für Antworten in Gruppen und Direktnachrichten, die Entscheidung über die Websuche, die Bewertung von Reaktionen, die Lernentscheidungen, die Überprüfung eigener Antworten, die Bilderkennung, das Modell für die Selbstbewertung, die Gedächtnissuche, die Websuche, die QQ-Brücke (NapCat) und das Lernprotokoll. Auf der Seite haben Antworten in Direktnachrichten und im Gruppenchat je eine eigene Zeile, ebenso die Lorebook-, Beispiel- und Wortfilterdateien (**Lorebook, Beispieldialoge und Wortfilter**), und nicht eingerichtete Dienste sind unter **N nicht eingerichtete Dienste anzeigen** zusammengefasst. Jede Modellzeile testet das Modell, das die jeweilige Arbeit erledigt. **Entscheidung über die Websuche** testet das Entscheidungsmodell (`LLM_JUDGE_MODEL`, sonst das Ersatzmodell, sonst das Hauptmodell) und schlägt fehl, wenn dieses Modell das Suchwerkzeug nicht aufruft, weil die Websuche dann nie ausgeführt würde. **Bewertung von Reaktionen** testet `REACT_MODEL`, sonst das Entscheidungsmodell, und wird übersprungen, solange `REACT_LEARN_ENABLED` ausgeschaltet ist. **Lernentscheidungen** testet das Modell, mit dem die Figur entscheidet, was Reaktionen nicht klären können (`PROMOTE_JUDGE_MODEL`, sonst das Modell der Bewertung von Reaktionen), und wird übersprungen, solange `PROMOTE_JUDGE_ENABLED` oder `PROMOTE_AUTO_ENABLED` ausgeschaltet ist. **Überprüfung eigener Antworten** testet `EVOLVE_MODEL` (sonst `EVAL_MODEL`, sonst das Ersatzmodell, sonst das Hauptmodell) und wird übersprungen, solange `EVOLVE_AUTO_ENABLED` ausgeschaltet ist. Würde eine dieser beiden Zeilen ein Modell testen, das bereits eine frühere Zeile testet, wird dieses Modell nicht erneut angefragt, und die Zeile übernimmt das Ergebnis jener Zeile. **Modell zur Selbstbewertung** wird übersprungen, solange `EVAL_ENABLED` ausgeschaltet ist. Jeder Dienst erhält eine Zeile mit der Kennzeichnung **Funktioniert**, **Funktioniert nicht** oder **Nicht eingerichtet**, und eine Gesamtbewertung über den Zeilen nennt, was zu beheben ist. Läuft die Figur, erfolgt die Prüfung über sie. Andernfalls führt ein separater Testlauf dieselben Prüfungen aus wie `personagent doctor`. Eine Prüfung sendet einige kurze Anfragen und verbraucht einen kleinen Teil des Kontingents Ihres Modelldienstes. Ein Ergebnis, das weniger als eine Minute alt ist, wird wiederverwendet, solange sich die Einstellungen nicht geändert haben. Derselbe Teil der Ansicht zeigt außerdem:

- warum die Figur, AstrBot oder die Plattformverbindung nicht starten konnte, mit der betreffenden Protokollzeile, **Protokoll anzeigen** und **Neu starten**;
- **Einstellungen mit alten Namen**: in 1.0 umbenannte Einstellungen. **Einstellungen umbenennen** bewirkt dasselbe wie `personagent doctor --fix`. Vorher erfolgt eine Rückfrage; die bisherige Datei wird als `.env.bak` aufbewahrt, und die Figur wird erneut gestartet, falls sie den Start verweigert hatte;
- **Plattformverbindungen**: den Zustand jeder Plattform, die personagent selbst verbindet, und bei einem Fehlschlag den Grund;
- **Zu prüfende Einstellungen**: in `.env` gefundene Probleme, etwa ein fehlender Modellschlüssel, eine Einstellung, die personagent nicht liest, ein leerer Wert oder eine Byte-Order-Mark;
- **Protokolle**: die letzten Zeilen jedes Protokolls in `runtime/desktop/` (Figur, AstrBot, Plattformverbindungen, Downloads und Installation, App, Übung und letztes Update). Erkennbare Schlüssel und Tokens werden ausgeblendet, Chatinhalte können jedoch erscheinen. **Weitere Zeilen anzeigen** zeigt bis zu 200 Zeilen an, und **Protokollordner öffnen** öffnet den Ordner.

**Modellnutzung.** personagent zählt jede Modellanfrage, die es stellt, pro Modell und pro Tag anhand der Nutzung, die der Modelldienst meldet: Anfragen, Tokens und die Kosten, sofern der Dienst sie meldet, wie es OpenRouter tut. Die Ansicht **App** zeigt den heutigen Tag und die letzten 7 Tage und schlüsselt die heutigen Anfragen nach Zweck auf, etwa Antworten, Lernen, Aufräumen des Gedächtnisses und Modellprüfung beim Start. `personagent doctor` gibt die Summen aus, und `doctor --json` ergänzt sie als `model_use`. Die Zählungen werden 8 Tage lang in `runtime/model_usage.json` aufbewahrt. personagent schreibt diese Datei im Hintergrund, höchstens einmal pro Minute und ein weiteres Mal beim Beenden, sodass das Zählen keine Antwort verzögert. Eine Anfrage ist ein Aufruf des Modelldienstes, und eine Nachricht führt meist zu mehreren: die Antwort selbst, mitunter die Entscheidung über eine Websuche, in Gruppen mitunter die Entscheidung, ob die Figur sich äußert, und später die Bewertung der Reaktion auf die Antwort. Jeder Start der Figur, auch der Neustart nach dem Speichern, fügt eine Modellprüfung hinzu. Da die Datei höchstens einmal pro Minute geschrieben wird, kann ein erzwungenes Beenden die Zählungen der letzten Minute verlieren.

#### Im Hintergrund ausführen

Dieser Teil steht unter Windows im App-Fenster zur Verfügung. Ist **Nach dem Schließen des Fensters weiter ausführen** aktiviert, wird personagent beim Schließen des Fensters in ein Symbol im Infobereich unten rechts auf dem Bildschirm verschoben, und die Figur antwortet weiterhin. Über das Menü des Symbols lässt sich personagent wieder öffnen oder beenden; ein Doppelklick auf das Symbol öffnet es ebenfalls. **Jetzt in den Hintergrund verschieben** blendet das Fenster sofort aus. `personagent start --background` startet personagent hinter dem Symbol, ohne das Fenster anzuzeigen, sofern diese Option aktiviert ist.

#### Version und Updates

Dieser Teil zeigt die laufende Version und den Zeitpunkt der letzten Prüfung. **Nach Updates suchen** fragt sofort bei pypi.org nach, auch wenn die tägliche Prüfung abgeschaltet ist. Liegt eine neuere Version vor, fragt **Aktualisieren und neu öffnen** zunächst nach, schließt personagent, führt den Update-Befehl für diese Installation aus und öffnet personagent wieder. Das dauert etwa eine Minute; in dieser Zeit antwortet die Figur nicht. Ein Klon wird mit `git pull --ff-only` und anschließendem `pip install -e` aktualisiert. Schlägt das Update fehl, öffnet sich wieder die vorherige Version, und **Protokoll anzeigen** zeigt, was geschehen ist. In vier Fällen kann sich die App nicht selbst aktualisieren und zeigt stattdessen den Befehl oder die Release-Seite an:

- bei einer aus dem Quellcode-ZIP entpackten Kopie, die Sie von Hand durch den neuen Quellcode ersetzen;
- bei einer Kopie, die über uvx läuft und die neue Version beim nächsten Start mit `uvx personagent@latest` lädt;
- bei einer Installation, deren Werkzeug (`git`, `uv` oder `pipx`) nicht gefunden wird;
- bei einem Klon mit lokalen Änderungen.

#### Dieser Computer und Ihre Daten

- **Symbol auf dem Desktop und im Startmenü** (Windows): **Symbol hinzufügen** und **Symbol entfernen** bewirken dasselbe wie `personagent shortcut`. Eine Kopie, die über uvx läuft, kann kein Symbol erhalten, weil sie aus einem temporären Ordner ausgeführt wird.
- **personagent nach der Anmeldung bei Windows starten** legt eine Verknüpfung im Autostart-Ordner an. Ist personagent für die Ausführung im Hintergrund eingerichtet, startet es dann hinter seinem Symbol, ohne das Fenster zu öffnen.
- **Ihre Daten** öffnet den personagent-Ordner, die Persona-Datei, die Protokolle, das Gedächtnis und die gelernten Inhalte, den Sticker-Ordner sowie den Ordner `data/` für Ihr eigenes Lorebook, Ihre Beispiele und Ihre Ausgabefilter.
- **Jetzt sichern** speichert eine einzelne ZIP-Datei auf dem Desktop, unter Dokumente oder im Ordner `backups` im personagent-Ordner. Sie enthält die Einstellungen mit Ihren API-Schlüsseln, die Persona, das Gedächtnis und die gelernten Inhalte, die Lorebook-Dateien, die Sticker und die Plattform-Anmeldungen. Protokolle und heruntergeladene Komponenten sind nicht enthalten. Bewahren Sie die Datei vertraulich auf. Zum Gedächtnis gehören die letzten Nachrichten der vergangenen 72 Stunden (`runtime/recent.json`) und die Antworten, die auf eine Reaktion warten, beide mit Chattext; das Chatprotokoll (`runtime/log/`) und der eigene Chat der Seite sind nie enthalten.
- **Aus Sicherung wiederherstellen** listet die Sicherungen an diesen drei Orten auf. **Wiederherstellen** fragt zunächst nach, pausiert die Figur, sichert die aktuellen Daten, ersetzt sie durch die Daten der Sicherung und leert den Chat dieser Seite. Das Chatprotokoll auf dem Datenträger bleibt erhalten, da eine Sicherung keines enthält.
- **Löschen und zurücksetzen** speichert zunächst eine Sicherung im Ordner `backups` und pausiert die Figur. **Gedächtnis löschen** entfernt die Notizen der Figur über Personen, die gelernten Antworten und deren Verlauf, die Übungsdaten und den Chat dieser Seite; Einstellungen, Persona, verbundene Plattformen und Sticker bleiben erhalten. **Alles zurücksetzen** versetzt personagent in den Zustand vor der ersten Einrichtung: Die Einstellungen und API-Schlüssel, die Persona, das Gedächtnis und die gelernten Inhalte werden gelöscht, und alle Plattformen werden getrennt. Sticker, der Ordner `data/` und das heruntergeladene AstrBot bleiben erhalten.

## Erst ansehen: die Demo

`personagent demo` spielt drei Szenen mit einem vorgegebenen Modell ab und benötigt daher keinen Schlüssel. Die Szenen zeigen, welche Gruppennachrichten die Figur auslässt und warum, wie sie aus einer Korrektur lernt und wie ein Fremder vergeblich versucht, ihr eine Anweisung unterzuschieben. Um nur eine Szene abzuspielen, geben Sie ihren Namen an (`quiet`, `teach` oder `troll`). Für eine andere Sprache fügen Sie `--lang` und einen Sprachcode hinzu, etwa `--lang ja`.

Es folgt ein gekürzter Lauf von `personagent demo teach`. Die Zeilen des Modells sind vorgegeben, das Lernprotokoll und die Beförderungsregel entsprechen jedoch dem tatsächlichen Code:

```text
  Alex: Nova, der Deploy ist schon wieder fehlgeschlagen
  Nova: hast du die Logs angeschaut? erst zurückrollen, dann die Configs vergleichen
  Alex: Nova, ich wollte nur Dampf ablassen
      bewertet: Ablehnung, akzeptiert: „Alex wollte Dampf ablassen, nicht um eine Lösung bitten“
      Lernprotokoll: nur negativ (sagt, dass die Antwort danebenlag, nicht, was zu sagen wäre)
      die nächste Antwort von Nova an Alex zählt als zweiter Versuch
  Nova: stimmt. harter Tagesabschluss
  Alex: haha ja genau, danke Nova
      bewertet: positiv, akzeptiert: „Alex stimmte dem zweiten Versuch zu und dankte Nova“
      Lernprotokoll: schwach (ein Lachen oder Danke ändert allein nie etwas)
      Lernprotokoll: Alex hat den zweiten Versuch akzeptiert: stark (die Antwort war für Alex)

  Korrektur: „hast du die Logs angeschaut? erst zurückr...“ -> „stimmt. harter Tagesabschluss“
    [x] übereinstimmende Reaktionen: 2 von 2
    [x] starke Reaktionen: 1 von 1
    [x] gleicher Chat
    [x] 1 von 1 Person (PROMOTE_MIN_SPEAKERS)
    [x] kein Widerspruch, keine konkurrierende Korrektur
    jetzt übernommen: 2 übereinstimmende Reaktionen, davon stark: 1, gleicher Chat
```

Die Szene sendet außerdem dieselbe Nachricht vor und nach der Lektion: Jemandes Laptop ist mitten in der Demo ausgefallen. Vor der Korrektur bietet Nova eine Lösung an. Danach zeigt Nova Mitgefühl. Die Demo bleibt auch mit gesetztem Schlüssel vorgegeben, sodass jeder Lauf identisch und kostenlos ist. `personagent demo --online` spielt sie stattdessen mit Ihrem eigenen Modell ab; dies verbraucht Token und variiert von Lauf zu Lauf.

Die Ansicht **Übung** der lokalen Seite spielt dieselben drei Szenen ab. Wählen Sie unter **Demo** eine Szene und dann **Abspielen**. Jeder Schritt zeigt, was die Teilnehmenden und was die Figur gesagt haben, warum sie geschwiegen oder sich beteiligt hat, wie die Reaktionen beurteilt wurden, und die Lern-Checkliste.

**Übungsgruppe** in derselben Ansicht ist die Seitenfassung von [`personagent chat`](#im-terminal-chatten) und setzt ein eingerichtetes Modell voraus. **Schreiben als** legt fest, wer die nächste Nachricht sendet: Sie als Administrator oder eines von drei fiktiven Mitgliedern. **Grund anzeigen** an einer Zeile zeigt, warum die Figur geantwortet oder geschwiegen hat, was sie gelernt hat und welches früher Gelernte sie verwendet hat. **Antworten** zitiert eine Zeile der Figur, sodass die nächste Nachricht als Reaktion darauf zählt. **Gelerntes anzeigen** listet auf, was sie in dieser Gruppe gelernt hat. Die Übungsgruppe speichert ihren Zustand in `runtime/trial/`, demselben Ordner wie `personagent chat`, und wirkt sich nicht auf Ihre echten Chats aus. **Übungsgruppe zurücksetzen** löscht diesen Zustand.

## Terminal-Befehle

Alle Funktionen der Seite stehen auch im Terminal zur Verfügung, was sich für Server und Skripte eignet.

| Befehl | Funktion |
|---|---|
| `personagent start` | öffnet die lokale Seite (`--terminal` für ein Menü im Terminal) |
| `personagent init` | richtet einen personagent-Ordner ein; `--terminal` stellt die Fragen im Terminal, `--no-input` übernimmt die Angaben aus Optionen |
| `personagent chat` | ein simulierter Gruppenchat im Terminal |
| `personagent demo` | die geskriptete Demo oben |
| `personagent run` | nur der Dienst, für Konnektoren, die Sie selbst betreiben |
| `personagent up` | der Dienst, die Plattformen, die personagent selbst verbindet, und das verwaltete AstrBot zusammen (`--page` stellt zusätzlich die Seite bereit) |
| `personagent page password` | legt das Passwort fest, mit dem sich andere Geräte bei der Seite anmelden (`--random` gibt einmalig ein neues aus) |
| `personagent service install` | hält `personagent up` nach einem Neustart in Betrieb (`restart`, `remove`, `status`; `--dry-run` gibt aus, was geschehen würde) |
| `personagent connect <platform>` | verbindet eine der [Plattformen, die personagent selbst verbindet](#eine-plattform-im-terminal-verbinden) (`--remove` trennt sie); ohne Plattform listet der Befehl sie auf |
| `personagent connect astrbot` | verbindet ein AstrBot (`--install`, um ein verwaltetes herunterzuladen, `--start`, um es zu starten) |
| `personagent connect claude-code`, `personagent connect codex`, `personagent connect dsh` | bindet die Figur in einen [Programmierassistenten](#programmierassistenten) ein (`--react` für Bemerkungen am Ende eines Durchgangs bei den ersten beiden, `--remove` zum Rückgängigmachen) |
| `personagent tools` | [Werkzeuge von MCP-Servern](#werkzeuge): `list`, `add`, `remove`, `check`, `call`, `set` |
| `personagent mcp` | der MCP-Server, den ein Programmierassistent startet; Sie führen ihn nicht selbst aus |
| `personagent doctor` | prüft die Konfiguration und jeden Dienst, von dem er abhängt |
| `personagent learned` | zeigt, was die Figur gelernt hat und was sie noch beobachtet, und ermöglicht bei Bedarf ein Eingreifen |
| `personagent memory` | listet auf, was die Figur sich merkt, vergisst einen Eintrag oder stellt ihn wieder her |
| `personagent access` | listet die [neuen Chats, die auf Freigabe warten](#wem-die-figur-antwortet-freigabe-neuer-chats), und gibt sie per Code frei oder lehnt sie ab (`approve`, `admin`, `decline`, `undo`, `policy <platform> approve\|open`) |
| `personagent eval` | misst Sprechen, Persona, Lernen und Gedächtnis |
| `personagent character` | [importiert eine Charakterkarte](#charakterkarten-und-entwürfe) (`import FILE`), speichert die Figur als Karte (`export FILE.png` oder `.json`) oder gibt eine aus einer Beschreibung entworfene Persona aus (`draft "..."`) |

Alle Befehle akzeptieren `--help`.

### Im Terminal einrichten

`personagent init --terminal` stellt dieselben Fragen wie die Seite, in der Sprache, die Sie zu Beginn wählen, und erklärt jeden Begriff in einer Zeile:

- **Der KI-Dienst.** Die Voreinstellungen entsprechen denen der Seite. Standard ist `openrouter/free` von OpenRouter, das jede Anfrage an eines seiner kostenlosen Modelle weiterleitet. Der Schlüssel ist kostenlos. Ein Schlüssel aus **Mit OpenRouter anmelden** (oder der Code-Anmeldung im Terminal) ist ein gewöhnlicher OpenRouter-Schlüssel mit der Bezeichnung `personagent`: Er wird wie ein eingefügter in `.env` gespeichert und kann, bis Sie ihn unter [openrouter.ai/keys](https://openrouter.ai/keys) entfernen, das Guthaben dieses Kontos verbrauchen, auch wenn die kostenlosen Modelle keines benötigen. Das Limit beträgt 20 Anfragen pro Minute und 50 pro Tag, oder 1000 pro Tag, sobald Sie mindestens 10 Credits erworben haben. Jeder Modellaufruf zählt, nicht nur die Antworten, und der Tag beginnt um Mitternacht UTC neu. Ist das Limit erreicht, teilt die Figur mit, dass sie gerade nicht antworten kann, und `runtime/desktop/agent.log` enthält den Grund von OpenRouter. Das Modell wechselt von Anfrage zu Anfrage, sodass die Ausdrucksweise der Figur stärker schwankt als mit einem fest gewählten Modell, und manche kostenlosen Anbieter speichern, was sie erhalten. Für eine beständigere Figur wählen Sie ein kostenpflichtiges Modell mit demselben Schlüssel. Wenn OpenRouter für Sie schwer erreichbar ist, ist `glm-4.7-flash` von Zhipu ebenfalls kostenlos. Für Ollama geben Sie ein Modell an, das Sie bereits heruntergeladen haben. Ollama benötigt keinen Schlüssel.
- **Der Schlüssel.** Die Eingabe ist standardmäßig verborgen. Sie können sie anzeigen lassen; bei einer Neukonfiguration wird dann auch der gespeicherte Schlüssel angezeigt. Der Assistent testet den Schlüssel mit einer kleinen Anfrage. Schlägt sie fehl, zeigt er die aufgerufene Adresse, den HTTP-Status und eine wahrscheinliche Abhilfe.
- **Die Figur.** Ein Name und eine von sieben fertigen Figuren (trockener Freund, aufmerksamer Zuhörer, Gamer, Bücherwurm sowie drei, die die Community bereits zeichnet: DeepSeek-chan, GPT-chan und Claude-chan) oder eine schlichte Figur, die Sie selbst beschreiben. Wählen Sie eine der letzten drei, ohne einen Namen festzulegen, trägt die Figur deren Namen. Die lokale Seite zeigt ihr animiertes Porträt. Sobald Sie eine eigene Persona geschrieben haben, ändert ein Klick auf ein Porträt unter **Figur & Einstellungen** nur das Bild. Dort nimmt **Eigenes Bild verwenden** eine PNG-, JPEG- oder WebP-Datei bis 2 MB an, legt sie im personagent-Ordner als `avatar.png` (oder `.jpg`, `.webp`) ab und zeigt sie nur auf der lokalen Seite.
- **Chatplattformen.** Optional; Sie können diesen Schritt beim ersten Mal überspringen. Die Einrichtung nennt die zehn Plattformen, die personagent selbst verbindet; diese verbinden Sie anschließend mit [`personagent connect <platform>`](#eine-plattform-im-terminal-verbinden). Für die übrigen Plattformen kann sie AstrBot verbinden und es zuvor herunterladen und installieren. Siehe [Brücken, die Sie selbst betreiben](#brücken-die-sie-selbst-betreiben).

Um ohne Rückfragen einzurichten, etwa in einem Skript, führen Sie `personagent init --no-input` mit `--provider`, `--model`, `--key-env VAR`, `--name`, `--lang` und `--persona` aus. In einem neuen personagent-Ordner erfordert ein Schlüssel aus `--key-env` oder aus dem `LLM_API_KEY` der Shell `--provider` oder `--base-url`, um anzugeben, zu welchem Dienst er gehört. `--provider other` erfordert außerdem `--base-url`. `personagent init --help` listet alle Optionen auf. Läuft `personagent init` ohne Terminal und ohne eine dieser Optionen, überspringt es die Fragen, weist darauf hin und beendet sich mit Code 2.

### Eine Plattform im Terminal verbinden

`personagent connect <platform>` verbindet ohne die Seite eine der [Plattformen, die personagent selbst verbindet](#plattformen-die-personagent-selbst-verbindet). Als Plattform geben Sie `qq`, `wechat`, `telegram`, `discord`, `matrix`, `twitch`, `irc`, `zulip`, `vk` oder `stoat` an. Der Befehl zeigt dieselben Schritte wie **Plattformen verbinden**, fragt jeden Wert ab, prüft die Werte bei der Plattform und speichert sie in derselben Form wie die Seite, die die Plattform anschließend als verbunden anzeigt. Lehnt die Plattform die Werte ab, nennt der Befehl den Grund und speichert nichts. `personagent connect` ohne Plattform listet die zehn Plattformen auf und gibt für jede an, ob sie verbunden ist.

- QQ und WeChat geben im Terminal einen QR-Code aus, den Sie mit Ihrem Smartphone scannen. Für QQ können Sie stattdessen AppID und AppSecret eines Bots eingeben, den Sie erstellt haben. Lässt sich der Code in Ihrem Terminal nicht scannen, verbinden Sie die Plattform im personagent-Fenster; der Befehl gibt aus, wie Sie es öffnen.
- Twitch gibt einen Link und einen Code aus. Öffnen Sie den Link in einem Browser, der beim Twitch-Konto der Figur angemeldet ist, prüfen Sie, ob die Seite denselben Code anzeigt, und bestätigen Sie die Anmeldung. Bis dahin wartet der Befehl.
- Jeder Wert kann auch als Option angegeben werden, etwa `--telegram-token` oder `--irc-server`; `personagent connect --help` listet alle Optionen auf. Ein als Option angegebener Wert kann im Verlauf der Shell verbleiben. Mit `--no-input` stellt der Befehl keine Fragen; fehlt ein erforderlicher Wert, nennt er die Option und beendet sich mit Code 2.
- `--remove` trennt die Plattform und löscht ihre gespeicherten Werte.
- Eine Plattform, die zum ersten Mal verbunden wird, verlangt eine [Freigabe neuer Chats](#wem-die-figur-antwortet-freigabe-neuer-chats); der Befehl weist darauf hin und gibt `personagent access policy <platform> open` aus, womit sich das abschalten lässt.

Die Verbindung ist aktiv, solange personagent läuft. `personagent up` startet personagent mit seinen verbundenen Plattformen; läuft personagent bereits, starten Sie es neu. Im Menü von `personagent start --terminal` verbindet Option 3 diese Plattformen, und Option 5 startet personagent mit ihnen.

### Im Terminal chatten

`personagent chat` versetzt Sie mit der Figur in einen simulierten Gruppenchat. Eine normale Zeile gilt als gewöhnliches Gruppengespräch, und der Testlauf zeigt an, ob die Figur sich beteiligen würde und warum. Eine Zeile mit ihrem Namen spricht sie an:

```text
Alex> ist heute Abend jemand da?
  (Nova schweigt: nicht angesprochen, 1 von 4 Nachrichten)

Alex> Nova, der Deploy ist schon wieder fehlgeschlagen
  Nova > hast du die Logs angeschaut? erst zurückrollen, dann die Configs vergleichen
```

| Eingabe | Zweck |
|---|---|
| `/reply <text>` | ihre letzte Antwort zitieren; dies zählt als Reaktion, aus der sie lernen kann |
| `/as Sam <text>` | als eine andere Person schreiben: `/as Sam Nova, you free tonight?` |
| `/admin <text>` | einmal als Administrator schreiben: `/admin Nova, how was your day?` |
| `/why` | anzeigen, warum sie ihre letzte Antwort gegeben hat und was das Lernprotokoll dazu enthält |
| `/learned` | anzeigen, was sie in diesem Chat gelernt hat |
| `/reset` | den Chat und das im Testlauf Gelernte löschen |
| `/help` | die Befehle erneut anzeigen |
| `/quit` | beenden |

`/as`- und `/admin`-Zeilen folgen ebenfalls den Gruppenregeln; nennen Sie also den Namen, um eine Antwort zu erhalten. Eine Zeile unter vier Zeichen, die die Figur nicht nennt, zählt nicht für die Beteiligung. Die [Gedächtnis-Befehle](#gedächtnis-befehle) funktionieren hier auch.

| Option | Funktion |
|---|---|
| `--name Alex` | legt Ihren Namen fest |
| `--admin` | ordnet jede Zeile dem Administrator zu |
| `--dm` | macht daraus ein Einzelgespräch |
| `--lang <code>` | überschreibt `AGENT_LANG`, wie `--lang ja` |
| `--trigger N` | Nachrichten, bevor die Figur eine Beteiligung erwägt (Standard 4) |

Der Testlauf führt die tatsächliche Entscheidung über Sprechen oder Schweigen aus, dazu die Ausgabeprüfungen, die Gedächtnis-Befehle und das Lernen. Er erwägt eine Beteiligung nach 4 Nachrichten, wo der laufende Bot auf 30 wartet. Was er lernt, bleibt in `runtime/trial/` im personagent-Ordner, getrennt vom laufenden Bot. `personagent learned` zeigt es nicht, und `/reset` löscht es. Der Testlauf überspringt die Zulassungslisten und die echte Zustellung. Außerdem schaltet er die Selbstbewertung, das Sehen, die Nachfrage und die Nachrichten aus, die die Figur von sich aus beginnen würde. Wenn ein Modellaufruf fehlschlägt, gibt er eine Zeile aus, die angibt, was zu prüfen ist:

```text
Alex> Nova, bist du da?
  [Fehler: der Modellanbieter hat den Schlüssel oder das Konto abgelehnt (HTTP 401); prüfen Sie LLM_API_KEY und führen Sie dann `personagent doctor` aus]
```

### Den Dienst ausführen

`personagent run` startet nur den Dienst, mit dem die Konnektoren sprechen, unter `http://127.0.0.1:8080`. Beim Start gibt er die Version, die Adresse und den personagent-Ordner aus sowie, ob der Agent aktiv ist. `--host` und `--port` überschreiben `SERVER_HOST` und `SERVER_PORT`. Verwenden Sie diesen Befehl, wenn Sie den Konnektor selbst betreiben.

`personagent up` startet den Dienst mit allen Plattformen, die über die Seite, mit `personagent connect <platform>` oder mit `connect astrbot --install` verbunden wurden. Es öffnet keinen Browser. Strg+C beendet alles, und jeder Prozess schreibt sein Log nach `runtime/desktop/` im personagent-Ordner.

Auf einem Server oder NAS kann `personagent up` auch die Seite bereitstellen, sodass Sie personagent nach der Anmeldung mit einem Seitenpasswort von einem Smartphone oder einem anderen Computer aus einrichten und betreuen; `personagent service install` hält es nach einem Neustart in Betrieb, und ein offizielles Docker-Image erledigt beides. [Auf einem Server, einem NAS oder in Docker](deploy.de.md#auf-einem-server-einem-nas-oder-in-docker) behandelt alle drei Wege und die sicheren Zugänge zur Seite.

## Die eigene Figur gestalten

`persona.txt` im personagent-Ordner legt die Figur fest. Bearbeiten Sie die Datei im Feld **Persona** der Seite oder in einem beliebigen Editor und starten Sie anschließend neu. Beschreiben Sie, wer die Figur ist, wie sie gewöhnlich spricht und wie sie sich in den Situationen verhält, die Ihnen wichtig sind. Konkrete Gewohnheiten wirken besser als die Bitte an das Modell, „natürlich zu klingen“: Wählen Sie auf der Seite eine fertige Persönlichkeit, wird `persona.txt` ersetzt. Eine selbst geschriebene Persona wird vorher nach `persona.txt.bak` und in eine datierte Kopie daneben kopiert, etwa `persona.txt.20261115-123456.bak`, die spätere Ersetzungen nicht überschreiben.

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG` ist eines von `en`, `zh`, `zh-TW`, `ja`, `ko`, `es`, `fr`, `de`, `pt-BR` und `ru`. Es legt die Startpersona, die Einrichtung im Terminal, den Testlauf und die Demo, `--help` und `doctor`, die Gedächtnis-Befehle und die festen Antworten fest. Das mitgelieferte Lorebook, die Beispiele, Filter und Prüfungen gibt es nur auf Chinesisch und Englisch: `zh` und `zh-TW` verwenden die chinesischen Dateien, alle anderen Sprachen die englischen. Die Einträge des mitgelieferten chinesischen Lorebooks sind als Anweisungen an das Modell auf Englisch geschrieben; nur ihre Schlüsselwörter sind chinesisch. Ihre Persona wird nicht übersetzt. [.env.example](../.env.example) beschreibt jede Einstellung.

Das Sprachmenü oben rechts auf der lokalen Seite bietet English, 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil) und Русский. Es ändert nur die Anzeige der Seite, und der Browser speichert die Auswahl. Die Sprache der Figur selbst wählen Sie unter **Figur & Einstellungen** in **Namen, Persönlichkeit oder Sprache wählen** im Feld **Sprache der Figur**; sie wird als `AGENT_LANG` gespeichert. Die Figur antwortet in der Sprache, die im Chat verwendet wird. Die Prompts der Figur sind englisch und chinesisch. Die [Gedächtnis-Befehle](#gedächtnis-befehle) und die wenigen festen Antworten, die nicht durchs Modell gehen, funktionieren in allen zehn Sprachen.

Um eine mitgelieferte Datei zu ersetzen, legen Sie eine Datei gleichen Namens in `data/` im personagent-Ordner ab. Dateien, die Sie nicht ersetzen, kommen aus der mit personagent gelieferten Kopie.

| Datei | Inhalt |
|---|---|
| `data/examples.<lang>.jsonl` | Beispielgespräche, die das Modell nachahmen kann |
| `data/feedback.<lang>.jsonl` | Antworten, gepaart mit besseren Fassungen |
| `data/lorebook.<lang>.json` | Hintergrundnotizen, die hinzukommen, wenn ein Schlüsselwort fällt |
| `data/output_filter.<lang>.json` | Ersetzungs- und Ablehnungsregeln für laufende Antworten |
| `persona.card.json` | Optionale Spitznamen sowie Einstellungen für Emojis, Sonderzeichen und Länge, wie `{ "aliases": ["Lu"], "reply_style": { "emoji": true, "max_chars": 320 } }`. Ein Spitzname in `aliases` spricht die Figur ebenso an wie ihr Name. Namen werden ohne Rücksicht auf Groß- und Kleinschreibung, Buchstaben voller Breite und Akzente verglichen, sodass `sofia` Sofía anspricht. In einer Nachricht gelten ñ, ã, õ und й als eigene Buchstaben, sodass `niña` keine Figur namens Nina anspricht; im eigenen Namen der Figur darf ein solches Zeichen fehlen, sodass `nina` Niña anspricht. Innerhalb eines längeren Wortes spricht ein Name die Figur nicht an: Ein Katakana-Name in einem längeren Katakana-Wort spricht sie nicht an, ebenso wenig ein koreanischer Name in der Mitte eines Wortes. Mit `"emoji": true` darf die Figur Emoji so verwenden, wie sie es gewohnt ist, und ein `max_chars` unter 800 wird dem Modell als Längengrenze mitgeteilt |

In diesen Dateinamen steht `<lang>` für `zh` bei vereinfachtem und traditionellem Chinesisch und für `en` bei allen anderen Sprachen. Eine Datei in `data/` ersetzt die mitgelieferte Datei derselben Art vollständig, und eine neue Datei wird nach einem Neustart der Figur wirksam. Die Ansicht App nennt diese Dateien **Lorebook, Beispieldialoge und Wortfilter**. Die Formate, jeweils mit einem Minimalbeispiel:

- Lorebook (`lorebook.<lang>.json`): Ein Eintrag wird dem Prompt hinzugefügt, wenn eines seiner `keywords` in den letzten zehn Nachrichten vorkommt. `keywords` und `content` sind Pflicht; `name` ist optional, und `priority` (Standard 100) legt fest, welche Einträge zuerst kommen, höchstens fünf pro Runde.

  ```json
  {"entries": [
    {"name": "gym", "keywords": ["gym", "the cave"], "content": "The group calls the gym on Fifth Street the cave.", "priority": 100}
  ]}
  ```

  Unter **Figur & Einstellungen** zeigt der Abschnitt **Lorebook** die verwendeten Einträge; dort lassen sie sich hinzufügen, bearbeiten und löschen. **Datei importieren** übernimmt eine Datei in diesem Format oder einen World-Info-Export aus SillyTavern und überspringt deaktivierte Einträge sowie Einträge ohne Schlüsselwörter oder Text. Beim ersten Speichern einer Änderung wird das integrierte Lorebook nach `data/lorebook.<lang>.json` kopiert, und **Integriertes Lorebook wiederherstellen** benennt diese Datei in `.bak` um und legt daneben eine datierte Kopie wie `lorebook.en.json.20261115-123456.bak` ab, die eine spätere Wiederherstellung nicht überschreibt; derselbe Abschnitt zeigt, ob Ihre eigenen Wortfilter- und Beispieldateien verwendet werden oder welche nicht gelesen werden kann, und `personagent doctor` führt alle drei Dateien auf, wenn sie lesbar sind, und nennt sonst nur die Datei, die nicht gelesen werden kann.
- Wortfilter (`output_filter.<lang>.json`): Jedes `pattern` ist ein regulärer Ausdruck in Python-Syntax, der ohne Beachtung der Groß- und Kleinschreibung verglichen wird. `"action": "reject"` verwirft die gesamte Antwort, sodass nichts gesendet wird; `"replace"` setzt `replacement` an die Stelle des Treffers und sendet den Rest.

  ```json
  {"filters": [
    {"name": "service_opener", "pattern": "^(hi|hello)\\W*how can i help", "action": "reject", "reason": "customer-service opener"},
    {"name": "no_em_dash", "pattern": "—", "action": "replace", "replacement": ", "}
  ]}
  ```
- Beispieldialoge (`examples.<lang>.jsonl`): ein JSON-Objekt pro Zeile; die Nachrichten vor der Antwort stehen in `context`, jeweils als `Name: Text`.

  ```json
  {"scenario": "a friend shares a video", "context": ["alex: the most cursed way to make instant noodles"], "reply": "watching cooking crimes at midnight is a choice"}
  ```

**Länge der Persona und der `[style]`-Block.** Das Feld **Persona** nimmt bis zu 16.000 Zeichen auf; jede Antwort sendet die gesamte Persona, eine kürzere kostet daher weniger. Ein `[style]`-Block in `persona.txt` ändert sechs Regeln für Einzelchats; Gruppenchats beachten ihn nicht. Jede Zeile hat die Form `Name: Wert`. Ein nicht aufgeführter Wert lässt den Standardwert, jeweils den ersten unten, bestehen, und das Protokoll vermerkt dies:

```text
[style]
length: medium
vent: ask
[/style]
```

Die Namen und Werte sind `length` (short, medium, long), `vent` für den Fall, dass jemand seinem Ärger Luft macht (hold, ask, solve), `recs` für die Bitte um eine Empfehlung (ask_back, offer), `good_news` (cheer, deadpan), `particles` für Füllwörter (capped, free, none) und `fatigue` (stock, own).

Damit die Figur Bilder erkennt, setzen Sie `VISION_MODEL`, `VISION_API_KEY` und `VISION_BASE_URL`, oder aktivieren Sie die Bilderkennung unter **Weitere Funktionen**. Kann das gewählte Modell keine Bilder lesen, weist die Seite beim Speichern darauf hin. Ein Bild, das die Figur nicht sehen kann, weil die Bilderkennung ausgeschaltet ist oder fehlgeschlagen ist, erreicht sie in Gruppen wie in Direktnachrichten als Bild, das sie nicht sehen kann; sie fragt daher nach dem Bild, statt es zu beschreiben. Sprachnachrichten, Videos, Dateien und weitergeleitete Nachrichten erreichen sie als das, was sie sind, eine Sprachnachricht mit ihrer Abschrift, sofern die Plattform eine liefert. Der Text einer weitergeleiteten Nachricht gilt als Äußerung der Person, von der sie weitergeleitet wurde: Er spricht niemanden mit Namen an und führt keinen Gedächtnis-Befehl aus. Eine Erwähnung einer anderen Person erreicht die Figur mit dem Namen, den diese Person selbst gewählt hat. Dieser Name gilt nie als Äußerung des Absenders; er spricht die Figur daher weder an, noch erteilt er einen Befehl.

### Charakterkarten und Entwürfe

**Entwurf aus einem Satz.** Beschreiben Sie oberhalb des Feldes **Persona** die Figur in einem oder zwei Sätzen und klicken Sie auf **Entwurf schreiben**. personagent sendet eine Anfrage an Ihren Modelldienst, die in der Ansicht **App** unter der Modellnutzung als **Persona-Entwürfe** gezählt wird, und setzt einen Entwurf in das Feld, geschrieben in der Sprache der Figur und als konkrete Gewohnheiten. Der Entwurf wird erst gespeichert, wenn Sie auf **Persona speichern** klicken; **Vorherigen Text wiederherstellen** stellt den vorherigen Inhalt des Feldes wieder her. `personagent character draft "a retired lighthouse keeper who loves crosswords"` gibt einen Entwurf im Terminal aus und speichert nichts.

**Eine Charakterkarte importieren.** **Charakterkarte** unterhalb des Feldes Persona nimmt eine Tavern-Charakterkarte an, das Format von SillyTavern und den Websites, auf denen Figuren geteilt werden: eine PNG-Karte (V2-Daten `chara` oder V3-Daten `ccv3`; sind beide vorhanden, gilt V3), eine JSON-Karte (V1, V2 oder V3) oder eine CHARX-Datei. Es ändert sich nichts, bis Sie eine Vorschau geprüft haben, die jeden Teil mit einem Kontrollkästchen zeigt:

- **Name**: Der Name der Karte wird zu `PERSONA_NAME`, und ein V3-Spitzname wird in `persona.card.json` zu `aliases` hinzugefügt. Was die Figur gelernt hat, bleibt erhalten, gilt aber nur unter dem Namen, unter dem es gelernt wurde; ein neuer Name beginnt also neu zu lernen, und wird der Name zurückgeändert, gilt das Gelernte wieder. Die Erinnerungen an Personen und Chats bleiben in beiden Fällen erhalten.
- **Persona**: zusammengesetzt aus Beschreibung, Persönlichkeit, Szenario und den Anweisungen der Karte (Systemprompt und Post-History-Anweisungen), wobei `{{char}}` und `<BOT>` durch den Namen und `{{user}}` und `<USER>` durch **Ihr Name** aus den erweiterten Einstellungen oder durch „the user“ ersetzt werden. Sie können die Persona in der Vorschau bearbeiten. Platzhalter, die sich nicht füllen lassen, werden aufgelistet. Die Anweisungen der Karte stehen in einem letzten, gekennzeichneten Abschnitt: Sie sind für Rollenspielprogramme geschrieben und verlangen oft Erzähltext oder Handlungen in Sternchen, die Sie möglicherweise löschen möchten. Das Feld Persona nimmt bis zu 16.000 Zeichen auf, und jede Antwort sendet die gesamte Persona an das Modell; eine lange Persona kostet daher pro Antwort mehr.
- **Beispieldialoge**: `mes_example` der Karte wird zu `data/examples.<lang>.jsonl` und ersetzt die mitgelieferten Beispieldialoge vollständig, wie es eine dort abgelegte eigene Datei tut.
- **Lorebook**: Das Lorebook der Karte durchläuft denselben Import wie **Datei importieren** im Abschnitt Lorebook, mit denselben Gründen für übersprungene Einträge; Einträge mit Abgleich über reguläre Ausdrücke werden ebenfalls übersprungen. Es wird zu `data/lorebook.<lang>.json`.
- **Bild**: Das PNG selbst oder das Hauptsymbol der CHARX-Datei wird zum eigenen Bild der Figur, bei Bedarf verkleinert.

Die Begrüßung der Karte (`first_mes` und die alternativen Begrüßungen) wird angezeigt, aber nicht verwendet: Die Figur hat keine feste Begrüßung und beginnt Unterhaltungen auf ihre eigene Weise. Eine von Ihnen geschriebene Persona sowie Ihre eigenen Beispiel- und Lorebook-Dateien werden vor dem Ersetzen als `.bak`-Dateien mit einer datierten Kopie aufbewahrt. Karten werden mit Grenzen für jede Größe gelesen: höchstens 16 MB je Datei und 2 MB Kartentext, eine begrenzte Zahl von PNG-Chunks und Archivmitgliedern, kein Mitgliedspfad, der aus dem Archiv hinausführt, und Bilder mit höchstens 40 Megapixeln. Nichts, worauf eine Karte verweist, wird heruntergeladen. `personagent character import FILE` erledigt dasselbe im Terminal: Es gibt die Vorschau aus und fragt, bevor etwas geändert wird; `--yes` überspringt die Frage, und `--only name,persona` übernimmt nur einige Teile.

**Als Charakterkarte speichern.** **Als PNG-Karte speichern** oder **Als JSON-Karte speichern** schreibt die Figur als V2-Karte in Ihren Desktop- oder Dokumente-Ordner (das PNG enthält zusätzlich V3-Daten): den Namen und die Spitznamen, die Persona, Ihre eigenen Beispieldialog- und Lorebook-Dateien sowie das Bild (Ihr eigenes Bild, sonst das gewählte Porträt, sonst ein schlichtes Quadrat). API-Schlüssel, Gedächtnis, das von der Figur Gelernte und die Namen von Personen aus Ihren Chats sind nicht enthalten, und **Ihr Name** wird als `{{user}}` geschrieben. Wird die Karte erneut importiert, ergibt sich dieselbe Figur. `personagent character export FILE.png` erledigt dasselbe im Terminal.

## In einen Chat bringen

Öffnen Sie **Plattformen verbinden** auf der lokalen Seite und wählen Sie eine Plattform. Die Seite fragt nur nach den Werten, die Sie aus der Konsole der Plattform kopieren. Sie prüft sie bei der Plattform, startet die Verbindung und wartet einige Sekunden, um zu bestätigen, dass die Plattform sie angenommen hat. Lehnt die Plattform ab, weist die Seite darauf hin und speichert nichts. Verbundene Plattformen werden oben aufgeführt; dort können Sie eine neu konfigurieren oder trennen. Sie werden erneut gestartet, sobald die Seite oder `personagent up` startet. Auf einem Computer ohne Bildschirm verbindet `personagent connect <platform>` die Plattformen, die personagent selbst verbindet, im Terminal; siehe [Eine Plattform im Terminal verbinden](#eine-plattform-im-terminal-verbinden).

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

Ein Konnektor meldet sich bei der Plattform an, leitet jede Nachricht an personagent weiter und stellt die Antwort zu. Es gibt drei Arten, die nach dem nächsten Abschnitt beschrieben werden.

### Wem die Figur antwortet: Freigabe neuer Chats

Eine Plattform, die auf der Seite oder mit `personagent connect <platform>` verbunden wird, verlangt zunächst eine Freigabe neuer Chats. Dort antwortet die Figur Ihnen sowie den Personen und Gruppen, die Sie freigegeben haben; alle anderen erhalten keine Antwort vom Modell. Wer dem Bot privat schreibt, erhält eine feste Nachricht in der Sprache der Figur, dass ihr Administrator den Chat freigeben muss, mit einem sechsstelligen Code; diese Nachricht kommt höchstens einmal am Tag erneut, wie oft die Person auch schreibt. In einer nicht freigegebenen Gruppe sagt die Figur nichts, und wenn sie dort jemand anspricht, sagt sie höchstens einmal am Tag, dass ihr Administrator die Gruppe nicht freigegeben hat.

Jede Anfrage erscheint unter **Plattformen verbinden** unterhalb der verbundenen Plattformen, mit dem Namen, der ID des Chats auf der Plattform, der Uhrzeit und den ersten Worten, und der Punkt neben **Plattformen verbinden** wird gelb. **Freigeben** lässt die Figur ab der nächsten Nachricht in diesem Chat antworten, ohne Neustart. **Ablehnen** verhindert, dass der Chat beantwortet wird oder erneut anfragt, unabhängig von der Regel. Bei einer Direktnachricht macht **Das bin ich** dieses Konto zu Ihrem Administratorkonto auf der Plattform; so werden Sie Administrator, ohne Ihre eigene ID herauszusuchen: Es fragt nach dem Code, den die Figur in Ihren eigenen Chat gesendet hat und den nur kennt, wer diesen Chat liest, sodass sich ein Fremder, der Ihren Namen kopiert, nicht als Sie ausgeben kann. Solange die Plattform keinen Administrator hat, wird es zuerst angeboten. Auf IRC kann ein Absender, der bei den Diensten des Netzwerks nicht identifiziert ist (mit `~` vor dem Nickname angezeigt), freigegeben, aber nie zum Administrator gemacht werden, da jeder den Nickname übernehmen kann. Eine Anfrage läuft nach drei Tagen ab. Jede Plattform hält höchstens zwanzig wartende Direktnachrichten und zehn Gruppen, sodass eine Flut Fremder den Bot keine Flut von Nachrichten senden lassen kann; solange eine Plattform noch keinen Administrator hat, erhält eine neue Direktnachricht dennoch ihren Code, anstelle der ältesten Anfrage, und die Seite weist darauf hin, wenn eine Liste voll ist. Nichts, was ein Fremder schreibt, erreicht das Modell.

Freigegebene und abgelehnte Chats werden getrennt von den Antworteinstellungen in `approvals.json` im Laufzeitordner gespeichert und unter den Anfragen aufgeführt, jeweils mit **Rückgängig machen**. Die Figur antwortet freigegebenen Chats zusätzlich zu den Personen und Gruppen in den Antworteinstellungen, auch wenn diese aus der Umgebung stammen; eine Freigabe ersetzt daher nie eine Liste und bleibt nach einem Neustart bestehen.

Der Satz unter jeder verbundenen Plattform nennt die dort geltende Regel und bietet die andere an: **Neue Chats ohne Freigabe beantworten** beantwortet jeden Chat, den die Plattform dem Bot zustellt, wie in früheren Versionen (die Antworteinstellungen gelten weiterhin, und abgelehnte Chats bleiben unbeantwortet), und **Freigabe für neue Chats verlangen** schaltet die Freigabe ein. Eine Plattform verlangt die Freigabe nur, wenn sie zum ersten Mal verbunden wird und dieser personagent-Ordner noch keine Entscheidung für sie enthält: Vor dieser Version eingerichtete personagent-Ordner, eine Plattform, die Sie auf Antworten ohne Freigabe umgestellt haben, und eine Plattform, die bereits Chats hat, antworten weiter wie bisher, wenn Sie sie neu einrichten. Beim Verbinden von Twitch oder IRC eingetragene Kanäle gelten als freigegeben. Der Chat der Seite selbst, Programmierassistenten und die OpenAI-kompatible API verlangen nie eine Freigabe. Auf einem Computer ohne Bildschirm listet `personagent access` die Anfragen auf und entscheidet sie per Code (`approve`, `decline`, `admin`, `undo` und `policy <platform> approve|open`).

### Plattformen, die personagent selbst verbindet

personagent verbindet diese zehn Plattformen selbst, in einem einzigen Hintergrundprozess. Sie benötigen weder AstrBot noch NapCat. Lässt sich eine davon nicht laden, starten die übrigen dennoch. Auf diesen Plattformen gehen Antworten Nachricht für Nachricht hinaus, jede nach ungefähr der Zeit, die das Tippen braucht; Telegram, Discord und Matrix zeigen währenddessen die Tippanzeige.

| Plattform | Vorgehen |
|---|---|
| QQ | Scannen Sie den Code mit der mobilen QQ-App und bestätigen Sie. Dadurch wird ein offizieller QQ-Bot erstellt oder ein vorhandener verwendet, und personagent ruft dessen Schlüssel ab. **Stattdessen Werte einfügen** übernimmt AppID und AppSecret eines Bots, der auf der [QQ-Bot-Seite](https://q.qq.com/qqbot/openclaw/login.html) erstellt wurde. |
| WeChat (persönlich) | Scannen Sie den Code mit WeChat und bestätigen Sie die Anmeldung. Die Verbindung nutzt Tencents iLink-Bot-API und deckt nur Einzelgespräche ab, da WeChat Gruppennachrichten nicht an diese Bots weiterleitet. |
| Telegram | Erstellen Sie einen Bot mit [@BotFather](https://t.me/BotFather) und fügen Sie sein Token ein. |
| Discord | Kopieren Sie im [Developer Portal](https://discord.com/developers/applications) das Bot-Token, aktivieren Sie Message Content Intent und deaktivieren Sie Public Bot, sofern nicht auch andere den Bot hinzufügen können sollen. Laden Sie ihn mit den Berechtigungen View Channels, Send Messages, Send Messages in Threads, Attach Files und Read Message History ein (`permissions=274878008320`). |
| Matrix | Legen Sie für den Bot ein eigenes Matrix-Konto an. Geben Sie die Homeserver-Adresse, Ihre eigene Matrix-ID sowie die Benutzer-ID und das Passwort des Bot-Kontos ein: personagent meldet sich einmal an, behält die erhaltene Anmeldung und speichert das Passwort nicht. Ein stattdessen eingefügtes Zugriffstoken wird nur angenommen, wo es nicht abläuft; ein in Element auf matrix.org kopiertes Token (es beginnt mit `mat_`) läuft innerhalb von Minuten ab und wird abgelehnt. Laden Sie den Bot dann von Ihrem eigenen Konto aus in einen Raum ein, in dem die Ende-zu-Ende-Verschlüsselung deaktiviert ist. Ein mit Start chat in Element begonnener Chat ist verschlüsselt und wird abgelehnt. Der Bot nimmt Einladungen nur von Ihrer Matrix-ID an; bei einer falsch geschriebenen ID wird also jede Einladung abgelehnt, und die Seite weist dann darauf hin. |
| Twitch | Registrieren Sie in der [Twitch-Entwicklerkonsole](https://dev.twitch.tv/console) eine kostenlose Anwendung mit dem Client Type **Public**. Fügen Sie deren Client ID und die Kanäle ein, in denen die Figur chatten soll, wählen Sie **Verbinden** und bestätigen Sie die Anmeldung über den Link, den die Seite anzeigt, in einem Browser, der beim Twitch-Konto der Figur angemeldet ist. Die Figur chattet nur per Text und nur in den angegebenen Kanälen. Twitch-Whispers (Direktnachrichten) werden nicht unterstützt; die Kachel unter **Plattformen verbinden** zeigt daher **Nur Kanäle**. |
| IRC | Geben Sie den Server (standardmäßig Libera.Chat, für OFTC `irc.oftc.net`), den TLS-Port, den Nickname des Bots, die Kanäle und, falls der Nickname registriert ist, das NickServ-Passwort ein. Der Bot verbindet sich über TLS, tritt nur den angegebenen Kanälen bei und beantwortet Direktnachrichten an seinen Nickname. Nur Text. Libera.Chat verlangt vor dem Beitritt eines KI-Bots die Erlaubnis der Operatoren jedes Kanals. |
| Zulip | Fügen Sie unter **Personal settings > Bots** einen **Generic bot** hinzu und fügen Sie dann die Adresse der Organisation, die E-Mail-Adresse des Bots und seinen API-Schlüssel ein. Der Bot liest nur die Kanäle, die er abonniert hat, und die Direktnachrichten an ihn. In einem Kanal antwortet er, wenn er erwähnt oder zitiert wird. Jedes Mitglied der Organisation kann ihm Direktnachrichten senden. |
| VK | Aktivieren Sie in den Einstellungen der Community Nachrichten und Bot-Funktionen, erstellen Sie einen Zugriffsschlüssel mit den Rechten für Community-Verwaltung, Nachrichten und Fotos, und aktivieren Sie die Long Poll API mit dem Ereignis `message_new`. Fügen Sie den Schlüssel ein. Jeder VK-Nutzer kann der Community schreiben. In einem Gruppenchat erhält der Bot nur Nachrichten, die ihn erwähnen oder auf ihn antworten, es sei denn, der Chat gewährt ihm Zugriff auf alle Nachrichten. |
| Stoat (früher Revolt) | Erstellen Sie unter **Settings > My Bots** einen Bot und fügen Sie dessen Token ein. Ändern Sie die API-Adresse nur bei einem selbst gehosteten Server. Der Bot beantwortet jede Direktnachricht. In Servern und Gruppen antwortet er nur dort, wo Sie selbst Mitglied sind, und nur, wenn jemand ihn erwähnt, auf ihn antwortet oder eine Nachricht mit seinem Namen beginnt. |

Für die letzten sechs zeigt die Seite über den Feldern nummerierte Schritte an. Das Projekt hat Matrix, Twitch, IRC, Zulip, VK und Stoat noch nicht mit den Live-Diensten getestet; die Verbindungen folgen der Dokumentation der jeweiligen Plattform.

Für QQ finden Sie den Bot in der mobilen QQ-App unter Kontakte → Bots; schreiben Sie ihm dann direkt oder fügen Sie ihn einer Gruppe hinzu. Solange der Bot nicht zertifiziert ist, lässt QQ ihn nur Gruppen beitreten, deren Inhaber Sie sind. Welche Gruppennachrichten er empfängt, legen Sie in QQ fest, im Profil des Bots in dieser Gruppe. Der [QQ-Bot-Leitfaden](https://bot.q.qq.com/wiki/bot_new_product-intro/) behandelt die Zertifizierung.

Die Zugangsdaten liegen in `platforms/direct.json` im personagent-Ordner.

### Andere Plattformen, über das verwaltete AstrBot

Wenn Sie zum ersten Mal eine andere Plattform verbinden, lädt personagent [AstrBot](https://docs.astrbot.app) und eine eigene Python-3.12-Laufzeit nach `platforms/` im personagent-Ordner herunter. Lassen Sie die Seite während des Downloads geöffnet. AstrBot läuft danach im Hintergrund ohne Dashboard und ohne zweite Anmeldung. Es benötigt kein globales `uv` und lässt das Python von personagent unberührt. Wenn Sie eine Plattform über die Seite verbinden, erreichen Gruppen und DMs dieser Plattform die Figur. Die Zulassungslisten anderer Plattformen bleiben unverändert.

| Gruppe | Plattformen | Erforderliche Angaben |
|---|---|---|
| Einige Werte einfügen | KOOK, Feishu / Lark, DingTalk, Slack, WeCom-KI-Bot, Mattermost, Misskey | ein Token, eine App-ID und ein Secret oder eine Serveradresse und ein Token. Feishu nutzt die lange Verbindung und DingTalk den Stream-Modus, sodass keine der beiden Plattformen eine öffentliche Adresse benötigt. Für Slack erstellt der Link der Seite die App mit bereits festgelegtem Socket Mode, Scopes und Ereignissen. Fügen Sie ein App-Level-Token mit `connections:write` hinzu, installieren Sie die App und fügen Sie beide Tokens ein. Erstellen Sie den WeCom-KI-Bot mit der langen Verbindung. |
| Erweitert | WeCom-App, offizielles WeChat-Konto, QQ (Webhook) | eine öffentliche Adresse, die an den angezeigten Callback-Port weiterleitet |
| Erweitert | OneBot v11 (NapCat), Satori | zusätzliche Software auf diesem Computer: NapCat, das auf `ws://127.0.0.1:<port>/ws` zeigt, oder ein Satori-Server |

LINE wird nicht angeboten, weil AstrBot LINE-Callbacks nur über sein Dashboard empfängt.

Im Terminal lädt `personagent connect astrbot --install` dasselbe verwaltete AstrBot herunter und verbindet es. Fügen Sie `--platform telegram --token <bot token>` hinzu, um gleichzeitig eine Plattform zu aktivieren. Keine Gruppe und keine DM ist zugelassen, bis Sie sie einrichten. Schlägt der Download fehl, führen Sie denselben Befehl erneut aus. Die vorhandene Konfiguration bleibt erhalten. `personagent connect astrbot --start` startet das verwaltete AstrBot, und `personagent up` startet es mit allem anderen.

### Brücken, die Sie selbst betreiben

Die Projekte unten sind Software von Dritten, mit der personagent zusammenarbeitet. Für die [Plattformen, die personagent selbst verbindet](#plattformen-die-personagent-selbst-verbindet), wird keines davon benötigt.

| Brücke | Erreicht |
|---|---|
| Ein [AstrBot](https://docs.astrbot.app), das Sie bereits betreiben | seine Plattformen |
| [NapCat](https://github.com/NapNeko/NapCatQQ) (OneBot v11), über AstrBot | QQ mit einem persönlichen QQ-Konto |
| [Koishi](https://koishi.chat) oder ein anderer Satori-Server, über den [Satori-Konnektor](../integrations/satori/README.de.md) | die mit diesem Server verbundenen Plattformen |
| [Matrix](../integrations/matrix/README.de.md), über die mautrix-Brücken | Matrix-Räume sowie WhatsApp, Signal, Messenger, Instagram und Google Messages |

Alles andere kann sich über das [Konnektor-Protokoll](connectors.de.md) verbinden, das eine signierte HTTP-Anfrage pro Nachricht verwendet. Mehrere Konnektoren können ein personagent gleichzeitig bedienen. Der [Bereitstellungsleitfaden](deploy.de.md) behandelt den Produktivbetrieb.

**Ein AstrBot, das Sie bereits betreiben.** AstrBot leitet Nachrichten über ein kleines Plugin, [astrbot_plugin_personagent](../integrations/astrbot/astrbot_plugin_personagent/README.de.md), an personagent weiter. Das Plugin wird mit personagent geliefert, und das verwaltete AstrBot erhält es automatisch. `personagent connect astrbot` findet Ihr AstrBot oder übernimmt seinen Ordner als Argument. Es installiert das Plugin, schreibt auf beiden Seiten ein gemeinsames `CONNECTOR_TOKEN` und fragt, welche Gruppen erlaubt sein sollen. Senden Sie `/sid` in einer Gruppe, um ihre Kennung anzuzeigen. Auf der lokalen Seite erledigt **Vorhandenes AstrBot verwenden** unter **Programmierassistenten** ganz unten in **Plattformen verbinden** dasselbe: Es findet den AstrBot-Ordner, installiert oder aktualisiert das Plugin und speichert die Kennungen der Gruppen und Direktnachrichten unter **Wem die Figur antwortet**. Für ein AstrBot in Docker oder auf einem anderen Computer nimmt es die unten beschriebene HTTPS-Adresse entgegen. **Trennen** entfernt das Plugin und seine Einstellungen wieder.

Für ein AstrBot auf einem anderen Rechner:

1. Laden Sie `astrbot_plugin_personagent.zip` aus dem [neuesten Release](https://github.com/wangkant/personagent/releases/latest) herunter.
2. Laden Sie die Datei unter **Install from File** auf der Plugin-Seite von AstrBot hoch.
3. Setzen Sie das `connector_token` des Plugins auf das `CONNECTOR_TOKEN` aus der `.env` von personagent.
4. Setzen Sie seine `personagent_url` auf eine HTTPS-Adresse von personagent. Siehe **AstrBot in Docker oder auf einem anderen Host** unten.
5. Führen Sie `personagent run` aus und starten Sie dann AstrBot neu oder laden Sie seine Plugins neu.

Führen Sie nach einem Upgrade von personagent `connect astrbot` erneut aus oder laden Sie das neue ZIP hoch. AstrBot 4.29 und neuer ersetzen die installierte Kopie. Bei älteren Versionen deinstallieren Sie zuerst die alte Kopie und lassen **Also delete plugin configuration file** deaktiviert, damit ihre Einstellungen erhalten bleiben.

Das Plugin leitet eine Gruppe nur weiter, wenn sie in seiner `groups`-Liste steht, und DMs nur von Nutzern in `dm_users`. Sie können beides in der WebUI von AstrBot ändern. Starten Sie personagent neu, nachdem Sie `.env` geändert haben, und starten Sie AstrBot neu, nachdem Sie eine Plattform oder das Plugin geändert haben.

Wenn Sie den AstrBot-Ordner angeben, stellt `connect astrbot` keine Fragen, und Sie können eine Plattform über ihr Token aktivieren:

```bash
personagent connect astrbot <AstrBot data dir> --platform telegram --token <bot token>
```

`--platform` akzeptiert `telegram`, `discord`, `slack`, `kook`, `lark` und `qq_official`. Slack erwartet zusätzlich `--app-token`, Lark und QQ erwarten `--app-id` und `--app-secret`. Bei einem Adapter, der in AstrBot bereits konfiguriert ist, ändert der Befehl nur die Zugangsdaten und behält alles andere, etwa einen Proxy oder eine Basis-URL. `personagent connect --help` listet die übrigen Optionen auf.

**QQ über NapCat.** Dieser Weg nutzt ein persönliches QQ-Konto statt eines offiziellen Bots. NapCat meldet sich mit dem Konto an und verbindet sich mit dem `aiocqhttp`-Adapter (OneBot v11) von AstrBot, mit seinem Reverse-WebSocket unter `ws://127.0.0.1:6199/ws`. Wenn Sie QQ in `personagent connect astrbot` wählen oder `--qq` mit einem Ordner übergeben, wird `aiocqhttp` aus den `excluded_platforms` des Plugins entfernt und `CONNECTOR_QQ_PLATFORMS=aiocqhttp` gesetzt. QQ-Chats behalten dann dieselben Identitäten und dasselbe Gedächtnis. Der HTTP-Server von NapCat (`QQ_ONEBOT_URL`) ist optional. Mit ihm und gesetztem `QQ_BOT_ID` holt personagent offline verpasste Erwähnungen nach. Die [Schritt-für-Schritt-Anleitung auf Chinesisch](deploy.zh-CN.md#第三方路线astrbot--napcat) hat einen kurzen Abschnitt zu diesem Weg. QQ-Clients von Drittanbietern gefährden das Konto; lesen Sie daher zuerst den [Haftungsausschluss](DISCLAIMER.de.md).

Der direkte OneBot-Weg (`/v1/onebot`) ist veraltet und bleibt während der gesamten 1.x bestehen. Er sendet Antworten über `QQ_ONEBOT_URL`; setzen Sie diesen Wert daher, wenn Sie den Weg noch nutzen. `personagent doctor` warnt, wenn der Weg ohne diesen Wert eingerichtet scheint. Betreiben Sie ihn nie zusammen mit der AstrBot-Weiterleitung, da sonst jede Nachricht doppelt ankommt.

**AstrBot in Docker oder auf einem anderen Host.** Das Plugin sendet nur an denselben Host (oder einen Container, der sein Netzwerk teilt) oder an eine HTTPS-Adresse mit gesetztem `connector_token`. Es lehnt unverschlüsseltes `http://` überall sonst ab, wie `http://host.docker.internal:8080`, protokolliert `refusing unsafe personagent_url` und lässt das Modell von AstrBot antworten. Es gibt zwei Abhilfen:

- Geben Sie dem AstrBot-Container das Host-Netzwerk: `network_mode: host` in seiner Compose-Datei oder `docker run --network host`. Unter Docker Desktop 4.34 oder neuer aktivieren Sie außerdem „Enable host networking“.
- Geben Sie personagent eine HTTPS-Adresse und setzen Sie sie als `personagent_url` des Plugins. `connect astrbot --url https://...` trägt sie für Sie ein.

Ein NapCat-Container in derselben Compose-Datei benötigt ebenfalls das Host-Netzwerk.

personagent lauscht auf `127.0.0.1:8080`, und ein leeres `SERVER_HOST` bedeutet dasselbe. Das Lauschen auf einer Netzwerkadresse (`--host 0.0.0.0` oder `SERVER_HOST`) erfordert `CONNECTOR_TOKEN`. Setzen Sie das Token, bevor Sie einen Proxy oder Tunnel einrichten, auch auf einem einzigen Rechner, denn ein Tunnel kann externe Anfragen lokal aussehen lassen. [Die Endpunkte freigeben](deploy.de.md#die-endpunkte-freigeben) behandelt den Rest.

### Zuerst sprechen

Manche Nachrichten antworten niemandem. Dazu gehören eigene Gesprächsanstöße (`PROACTIVE_ENABLED`, standardmäßig deaktiviert), die Nachfrage nach einer Ablehnung und die Ausrede, wenn das Modell in einer Gruppe ausfällt. In einer DM geht die Ausrede in der Antwort auf die wartende Nachricht zurück. personagent legt diese Nachrichten in eine Outbox, und die Konnektoren rufen sie ab und senden sie auf den Plattformen, die einen Bot zuerst sprechen lassen. Die lokale Seite ruft sie auf dieselbe Weise für ihre eigene Ansicht **Chat** ab. Offizielle WeChat-Konten und intelligente WeCom-Bots erlauben dies nicht. QQ begrenzt die Rate unaufgeforderter Nachrichten eines offiziellen Bots, und Nutzer können sie deaktivieren. `PROACTIVE_PLATFORMS=qq_official` beschränkt eigene Gesprächsanstöße auf den offiziellen QQ-Bot und `qq` auf QQ über NapCat. Auf der Seite setzt **Gelegentlich selbst beginnen** unter **Weitere Funktionen** beide Einstellungen. Siehe den [Bereitstellungsleitfaden](deploy.de.md#mehr-als-eine-plattform).

## Werkzeuge

Neben der Websuche kann die Figur Werkzeuge von MCP-Servern verwenden, die Sie hinzufügen: die aktuelle Uhrzeit, den Text einer Webseite, Ihre Notizen, einen Kalender und alles andere, was ein MCP-Server anbietet. Jede Antwort schreibt die Figur weiterhin mit ihrer eigenen Stimme. Ein Werkzeug zieht sie unterwegs zu Rate, wie bei der Websuche: Verlangt eine Nachricht etwas, das ein Werkzeug liefert, ruft sie genau dieses eine Werkzeug auf, liest die Antwort und antwortet als sie selbst.

**Einen Server hinzufügen.** In **Figur & Einstellungen** nimmt der Bereich **Werkzeuge** unter **Weitere Funktionen** die Konfiguration aus der Anleitung des Servers unverändert entgegen: den gesamten Block `{"mcpServers": {...}}`, wie er für Claude Desktop oder Cursor angegeben ist, den Eintrag eines einzelnen Servers oder das Objekt eines einzelnen Servers. **Stattdessen ein Programm oder eine Adresse eingeben** nimmt einen Befehl mit seinen Argumenten und Umgebungsvariablen entgegen oder die Adresse eines entfernten Servers (Streamable HTTP) mit ihren Anfrage-Headern. Wird `uvx` gefunden (die Installationsprogramme bringen uv mit), werden zwei Server aus dem offiziellen Referenzsatz zum sofortigen Hinzufügen angeboten: **Uhrzeit** (`uvx mcp-server-time`) und **Abruf** (`uvx mcp-server-fetch`). Im Terminal:

```
personagent tools add '{"mcpServers": {"time": {"command": "uvx", "args": ["mcp-server-time"]}}}'
personagent tools add --name fetch --command uvx --arg mcp-server-fetch
personagent tools add --name notes --url https://example.com/mcp --header "Authorization=Bearer ..."
personagent tools check
personagent tools call time get_current_time '{"timezone": "Asia/Tokyo"}'
personagent tools set time get_current_time --who anyone
personagent tools list
personagent tools remove fetch
```

**Jedes Werkzeug** hat einen Schalter und eine Auswahl, wer seine Verwendung auslösen darf: **Nur der Administrator**, die Voreinstellung für jedes neue Werkzeug, oder **Jeder, dem die Figur antwortet**. Ein Werkzeug, das der Absender einer Nachricht nicht verwenden darf, wird für diese Nachricht nie angeboten. **Prüfen** verbindet sich sofort mit dem Server, liest seine Werkzeuge und nennt den Grund, wenn das fehlschlägt: Das Programm wurde nicht gefunden, es wurde beendet (mit seinen letzten Ausgabezeilen), die Adresse hat die Verbindung abgelehnt, der Server hat nicht rechtzeitig geantwortet, oder er verlangt eine Anmeldung über OAuth, die personagent noch nicht unterstützt. **Ausprobieren** ruft ein Werkzeug manuell mit den von Ihnen eingegebenen Argumenten auf und zeigt den Text, den die Figur erhalten würde. **Entfernen** beendet den Server und entfernt ihn. Änderungen werden innerhalb weniger Sekunden ohne Neustart wirksam.

**Betrieb.** Der Dienst der Figur startet die Server beim eigenen Start, ohne auf sie zu warten, startet einen beendeten Server neu (nach 2 Sekunden, dann mit jeweils verdoppelter Wartezeit bis zu 5 Minuten) und beendet sie samt den von ihnen gestarteten Programmen, wenn er selbst endet. Ein Server, der nicht startet, wird auf der Seite und von `personagent doctor` gemeldet; die Figur arbeitet ohne ihn weiter. Ein Aufruf hat 20 Sekunden Zeit; verwendet wird nur der Text einer Antwort, höchstens 3.000 Zeichen davon, und andere Inhalte wie Bilder werden benannt und ausgelassen. Die vom Modell gewählten Argumente werden vor dem Aufruf mit der Beschreibung des Werkzeugs abgeglichen.

**Kosten.** Ohne Werkzeuge entscheidet eine Prüfung mit regulären Ausdrücken, ob eine Nachricht eine Websuche erfordern könnte, und nur dann wird das Modell gefragt. Solange ein Werkzeug eingeschaltet ist, kostet jede Nachricht einer zur Werkzeugnutzung berechtigten Person, auf die die Figur antworten wird, eine zusätzliche kleine Anfrage an das Entscheidungsmodell (`LLM_JUDGE_MODEL`). Diese entscheidet, ob ein Werkzeug verwendet, im Web gesucht oder keines von beiden getan wird. Die Ansicht App zählt diese Anfragen als **Entscheidung, ob ein Werkzeug verwendet wird**.

**Sicherheit.** Beim Hinzufügen eines Servers wird ein Programm auf diesem Computer mit Ihren eigenen Benutzerrechten ausgeführt oder eine Verbindung zu der eingegebenen Adresse hergestellt; fügen Sie nur Server hinzu, denen Sie vertrauen. Ein Programm startet mit dem, was es zum Ausführen braucht (Suchpfad, Benutzerordner, Sprache, Proxy, Einstellungen für uv und npm), und dem `env`, das Sie ihm geben, nie mit den eigenen Einstellungen von personagent oder einer Variablen, deren Name auf einen Schlüssel, ein Token, ein Geheimnis oder ein Passwort hindeutet. Ein Werkzeug, das nur der Administrator verwenden darf, wird nur angeboten, wenn ein Administrator die zu beantwortende Nachricht geschrieben hat, und die Entscheidung liest dann keine Zeilen anderer Personen. Ein Eintrag mit `"disabled": true` wird nicht gestartet, und personagent ändert nur den Server, den es ändern soll, und behält jeden anderen Eintrag und Schlüssel der Datei unverändert bei. Von einem anderen Gerät aus kann ein Server unter einer Adresse auf diesem Computer oder in seinem lokalen Netzwerk weder hinzugefügt noch verwendet werden. Namen, Beschreibungen und Antworten von Werkzeugen stammen von Dritten: Sie sind in der Länge begrenzt und für das Modell als externes Material gekennzeichnet, aus dem es nie Anweisungen übernehmen soll. Was ein Werkzeug zurückgibt, wird zusammen mit dem Chat an den Modelldienst gesendet. Die Server werden in `mcp.json` im personagent-Ordner gespeichert; ihre Umgebungsvariablen und Anfrage-Header sind Geheimnisse, und die Seite zeigt nur, welche davon gesetzt sind. In der Aktivität, bei `/why` in `personagent chat` und in der Erklärung der Übungsgruppe nennt eine Antwort, die sich auf ein Werkzeug gestützt hat, das Werkzeug, nie seine Argumente oder seine Antwort.

## Programmierassistenten

Codex, Claude Code und DeepSeek Harness (`dsh`) erreichen die Figur über MCP. Führen Sie bei gespeichertem Modellschlüssel einen oder mehrere dieser Befehle aus:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

Der erste ruft `claude mcp add` im Benutzerbereich auf. Der zweite schreibt in `config.toml` im Codex-Ordner (`CODEX_HOME` oder `~/.codex`). Der dritte ergänzt einen Eintrag in `cordis.patch.yml` in jedem Profil unter `DSH_HOME` oder `~/.dsh`. Jede Art, DeepSeek Harness auszuführen, wie die Desktop-App oder `dsh web`, erhält ihr Profil beim ersten Start; starten Sie es daher einmal vor dem Verbinden und danach erneut. Alle drei verweisen auf diese Installation und diesen personagent-Ordner; führen Sie den Befehl daher erneut aus, wenn Sie eines davon verschieben, und zwar mit `--react`, falls Sie diese Option verwendet haben: Ein Lauf ohne sie entfernt den Hook. Starten Sie eine neue Sitzung und bitten Sie dann den Programmierassistenten, Ihrer Figur etwas mitzuteilen.

**Über die lokale Seite.** **Programmierassistenten** ganz unten in **Plattformen verbinden** findet Claude Code, Codex und DeepSeek Harness auf diesem Computer und zeigt für jeden an, ob er verbunden ist. **Verbinden** (bei einer bestehenden Einrichtung **Reparieren** bzw. **Aktualisieren**) und **Entfernen** bewirken dasselbe wie die obigen Befehle bzw. `--remove` und fragen vorher nach. Bei einer erneuten Verbindung bleibt die Einstellung für Bemerkungen unverändert. Bei Claude Code und Codex schaltet **Am Ende eines Durchgangs eine Bemerkung machen** den `--react`-Hook ein oder aus, und **Mindestabstand zwischen Bemerkungen** setzt `CODING_REACT_COOLDOWN_S` auf 10 Minuten, 30 Minuten, 1 Stunde oder 2 Stunden. **Erneut prüfen** liest den Zustand neu ein, etwa nachdem Sie eines der Programme installiert haben.

Der Server bietet zwei Werkzeuge:

| Werkzeug | Funktion | Kosten |
|---|---|---|
| `talk` | eine Nachricht im selben Einzelgespräch wie die lokale Seite, mit demselben Gedächtnis. Was über `talk` gesagt wird, erscheint in der Ansicht **Chat** der Seite mit dem Vermerk **über einen Programmierassistenten**: innerhalb weniger Sekunden, solange die Ansicht **Chat** geöffnet ist, andernfalls beim nächsten Öffnen der Seite. Gedächtnis-Befehle wie `Nova, what do you remember?` funktionieren hier auch. | eine Antwort Ihres Modelldienstes, außer bei Gedächtnis-Befehlen |
| `character` | liest den Namen und `persona.txt` | nichts |

Claude Code und Codex fragen vor dem ersten `talk` nach, und Sie können es in dieser Abfrage dauerhaft erlauben. `dsh headless` fragt nicht nach. Ein Lauf ohne Person, die Rückfragen beantwortet, benötigt die Erlaubnis im Voraus: `claude -p` erwartet `--allowedTools mcp__personagent__talk`, und `codex exec` benötigt Folgendes in `config.toml`:

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**Wer antwortet.** Vorrangig antwortet eine geöffnete Seite, danach ein Dienst, den `personagent up` betreibt. Fehlt beides, startet der MCP-Server die Seite im Hintergrund, und die Seite wird mit der Sitzung des Programmierassistenten beendet, ebenso die verbundenen Chatplattformen. Zwei gleichzeitige Sitzungen teilen sich eine Seite. Wenn Sie `personagent` ausführen, während eine solche Seite läuft, wird ihr Link ausgegeben, und die Seite endet dennoch mit der Sitzung, die sie gestartet hat. Führen Sie `personagent up` nicht aus, während eine solche Seite läuft: Beenden Sie zuerst die Sitzung des Programmierassistenten.

**Bemerkungen am Ende eines Durchgangs.** Bei Claude Code und Codex fügt `--react` einen Stop-Hook hinzu. DeepSeek Harness unterstützt das nicht: Seine Hook-Brücke gibt die letzte Nachricht nicht an einen Stop-Hook weiter und zeigt die Ausgabe des Hooks nicht an. Wenn der Programmierassistent einen Durchgang beendet, erhält die Figur ein [proaktives Signal](connectors.de.md#zuerst-sprechen-ohne-die-outbox) und richtet einen Satz an Sie oder verzichtet darauf. Der Satz ist an Sie gerichtet und wird nicht an den Programmierassistenten gesendet. Er erscheint auch in der Ansicht **Chat** der Seite, auch wenn zu diesem Zeitpunkt keine Seite geöffnet war; das Signal selbst erscheint dort nicht.

```bash
personagent connect claude-code --react
```

- Das Signal enthält den Ordnernamen und die ersten 300 Zeichen der letzten Nachricht des Programmierassistenten; dieser Text wird daher an Ihren Modelldienst gesendet. Der Satz und die Notizen des Modells zu dem Signal verbleiben im Gedächtnis der Figur. Deshalb ist die Funktion standardmäßig deaktiviert.
- Die Funktion kostet jedes Mal einen Modellaufruf, höchstens einmal pro `CODING_REACT_COOLDOWN_S` (Standard 30 Minuten).
- Sie nutzt nur einen bereits laufenden Figurendienst und startet nie selbst einen.
- Codex führt einen neuen Hook erst aus, nachdem Sie ihn als vertrauenswürdig bestätigt haben: Geben Sie `/hooks` in einer Codex-Sitzung ein.

**Zu beachten.** `talk` sendet, was der Programmierassistent schreibt, an Ihren Modelldienst und in das Gedächtnis der Figur. Die Beschreibung des Werkzeugs weist den Programmierassistenten an, nur zu senden, was Sie mitteilen möchten, niemals Code oder Geheimnisse, und Antworten als Gespräch und nicht als Anweisungen zu behandeln, da die Notizen einer Figur auf Äußerungen von Personen in Ihren Gruppen zurückgehen können. Dies sind Anweisungen an ein Modell, keine Garantie; behalten Sie daher die Berechtigungsabfragen des Programmierassistenten für alles bei, was er mit einer Antwort tun würde. Der Chat der Seite gehört dem Administrator; was ein Programmierassistent über `talk` sendet, gilt daher ebenfalls als Nachricht des Administrators: Seine Korrekturen allein können der Figur etwas beibringen, und er kann die Figur jede Notiz vergessen lassen.

**Rückgängig machen.** `--remove` entfernt den Server und den Hook und lässt die übrige Konfiguration des Programmierassistenten unverändert. Führen Sie dies aus, bevor Sie personagent deinstallieren.

```bash
personagent connect claude-code --remove
personagent connect codex --remove
personagent connect dsh --remove
```

**Andere Werkzeuge.** Alles, was MCP über stdio spricht, kann den Server selbst starten. `--home` ist erforderlich, sofern nicht der standardmäßige personagent-Ordner verwendet wird:

```json
{"mcpServers": {"personagent": {"command": "personagent", "args": ["--home", "/path/to/home", "mcp"]}}}
```

## Andere Software

Jede Anwendung, in der sich eine OpenAI-kompatible Adresse eintragen lässt, kann mit der Figur sprechen: Chat-Oberflächen wie Open WebUI und SillyTavern, Automatisierungswerkzeuge oder ein eigenes Skript. personagent stellt `GET /v1/models` und `POST /v1/chat/completions` im Format der Chat-API von OpenAI bereit. Standardmäßig ist dies ausgeschaltet.

**Einschalten.** Auf der lokalen Seite hat **Andere Software** unten unter **Plattformen verbinden** einen Schalter. Beim ersten Einschalten wird ein Schlüssel erstellt. Die Seite zeigt dann die drei Werte, die die andere Anwendung benötigt, jeweils mit **Kopieren** daneben; der Schlüssel bleibt verborgen, bis Sie **Anzeigen** wählen. **Testnachricht senden** sendet eine Nachricht über die API, wie es eine andere Anwendung täte, und zeigt die Antwort oder den Grund des Fehlschlags. **Neuen Schlüssel erstellen** ersetzt den Schlüssel nach einer Rückfrage; der alte Schlüssel ist sofort ungültig. Eine laufende Figur wird neu gestartet, wenn Sie das eine oder das andere ändern, weil sie die Einstellung nur beim Start liest. Im Terminal:

```bash
personagent connect api            # turn it on, create the key if there is none, print the three values
personagent connect api --new-key  # replace the key
personagent connect api --remove   # turn it off; the key is kept
```

**Die drei Werte.**

| Wert | Eintrag |
|---|---|
| Adresse (Basis-URL) | `http://127.0.0.1:<SERVER_PORT>/v1`, standardmäßig `http://127.0.0.1:8080/v1` |
| API-Schlüssel | `CHAT_API_KEY`, gesendet als `Authorization: Bearer <key>` |
| Modell | `personagent`. Jeder Modellname wird angenommen; `/v1/models` führt nur diesen auf. |

**In gängigen Anwendungen.** In Open WebUI öffnet ein Administrator Settings > Connections, wählt unter **Manage OpenAI API Connections** die Option **Add Connection**, trägt die Adresse unter **URL** und den Schlüssel unter **API Key** ein und wählt **Save** ([Anleitung von Open WebUI](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible)). In SillyTavern öffnen Sie API Connections, setzen den API-Typ auf **Chat Completion** und **Chat Completion Source** auf **Custom (OpenAI-compatible)**, tragen die Adresse als Endpunkt-URL und den Schlüssel als API-Schlüssel ein, wählen `personagent` und anschließend **Test Message** ([Anleitung von SillyTavern](https://docs.sillytavern.app/usage/api-connections/openai/)).

**Was die API leistet und was nicht.**

- Die Figur behält ihre eigene Persona und ihr Gedächtnis. Der Systemprompt der Anwendung, die mitgesendeten früheren Nachrichten und Einstellungen wie die Temperatur werden ignoriert: Gelesen wird nur die letzte Nachricht mit der Rolle `user`, und zwar als neue Nachricht. Lässt eine Anwendung eine Antwort neu erzeugen, sendet sie diese Nachricht erneut, und die Figur liest sie als zweimal gesagt.
- Jeder Wert des Feldes `user` einer Anfrage ist eine eigene Unterhaltung auf der Plattform `api` und erscheint in der Aktivität als API-Direktnachricht. Ohne `user` benennt der Header `X-Personagent-Conversation` die Unterhaltung; fehlt beides, teilen sich alle Anfragen eine Unterhaltung, `default`.
- Antworten bestehen aus Text. Eine Nachricht kann Bilder als `image_url`-Teile enthalten, entweder als `data:image/...;base64,`-URLs oder als `http(s)`-URLs. Die Figur liest sie wie Bilder von einer Chatplattform, mit derselben Größenbegrenzung (`VISION_MAX_IMAGE_BYTES`) und derselben Ablehnung von Adressen in Ihrem eigenen Netzwerk. Sticker sendet die Figur hier nie.
- Die Figur antwortet oft in mehreren kurzen Nachrichten. Eine einfache Antwort verbindet sie durch Zeilenumbrüche; eine gestreamte Antwort (`"stream": true`) sendet je Nachricht ein Stück, sobald die ganze Antwort fertig ist, und während die Figur nachdenkt, Keep-alive-Kommentare. Die Tokenzahlen in `usage` sind immer 0.
- Aufrufer sind keine Administratoren der Figur; Gedächtnis-Befehle wirken daher nur so wie bei anderen Personen.
- Fehler haben die Form von OpenAI, `{"error": {"message", "type", "code"}}`: 401 bei fehlendem oder falschem Schlüssel, 400 bei einer fehlerhaften Anfrage, 404, solange die API ausgeschaltet ist, 429 bei Auslastung (mit `Retry-After`), 502, wenn der Modelldienst versagt hat, 503, solange die Figur ausgeschaltet ist.
- Die Adresse antwortet nur, solange personagent läuft: bei geöffnetem Fenster oder unter `personagent up` bzw. `personagent run`.

**Aus einem Skript.** Mit curl:

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
  -H "Authorization: Bearer $CHAT_API_KEY" -H "Content-Type: application/json" \
  -d '{"model": "personagent", "user": "me", "messages": [{"role": "user", "content": "Hello"}]}'
```

Mit Python, ausschließlich mit der Standardbibliothek:

```python
import json, os, urllib.request
body = {"model": "personagent", "user": "me", "messages": [{"role": "user", "content": "Hello"}]}
request = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", json.dumps(body).encode(),
    {"Authorization": "Bearer " + os.environ["CHAT_API_KEY"], "Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=300) as response:
    print(json.load(response)["choices"][0]["message"]["content"])
```

Ein Durchgang kann eine Minute oder länger dauern; geben Sie dem Client daher eine lange Zeitüberschreitung.

**Von einem anderen Gerät oder aus Docker.** Die Adresse funktioniert nur für Programme auf diesem Computer, weil personagent auf `127.0.0.1` lauscht. Ein Programm in einem Docker-Container, ein Smartphone oder ein anderer Computer gilt als anderes Gerät. Um die Adresse von dort zu erreichen, starten Sie den Dienst entweder auf der Netzwerkadresse, `personagent run --host 0.0.0.0` (dann sind `CONNECTOR_TOKEN` und `CHAT_API_KEY` erforderlich, und der Schlüssel wird unverschlüsselt übertragen; tun Sie dies daher nur in einem vertrauenswürdigen Netzwerk), oder Sie schalten einen HTTPS-Reverse-Proxy oder einen privaten Tunnel vor `127.0.0.1:<SERVER_PORT>`. In jedem dieser Fälle ist ein Schlüssel erforderlich: Ohne ihn wird eine Anfrage abgelehnt, die über einen Proxy oder von einer anderen Adresse eintrifft. `CHAT_API_ENABLED` und `CHAT_API_KEY` stehen in `.env` und werden beim Start des Dienstes gelesen.

## Der Figur etwas beibringen

### Gedächtnis-Befehle

Sie geben diese Befehle im Chat ein. Der Befehl muss am Anfang der Nachricht stehen, gegebenenfalls nach einer @-Erwähnung oder einem Zitat. Ersetzen Sie Nova durch Ihren `PERSONA_NAME`:

| Eingabe | Wirkung |
|---|---|
| `Nova, remember Sam is vegetarian` | Speichert eine Notiz in diesem Chat und hält fest, wer sie gespeichert hat und von wem sie handelt |
| `Nova, forget vegetarian` | Löscht passende Notizen, die Sie gespeichert haben oder die von Ihnen handeln; der Administrator kann jede löschen |
| `Nova, what do you remember` | Listet die Notizen auf, die Sie sehen dürfen, und danach bis zu drei Ereignisse dieses Chats, an denen Sie beteiligt waren, jeweils mit Datum; der Befehl muss die gesamte Nachricht bilden |
| `Nova, what have you learned` | Zählt Notizen, gelernte Antworten und Korrekturen, die Einträge, die noch auf weitere zustimmende Reaktionen warten, und die Einträge, über die die Figur selbst entscheidet, und zeigt dann die letzte Änderung und wie sie übernommen wurde: durch die Reaktionen, durch eigene Entscheidung der Figur oder durch eine Person |

Von wem eine Notiz handelt:

- Eine Notiz in der ersten Person oder eine Notiz, die Sie nennt, handelt von Ihnen.
- Eine Notiz, die ein anderes Mitglied des Raums nennt, handelt von dieser Person und wird wieder herangezogen, wenn sie anwesend ist.
- Jede andere Notiz gehört der ganzen Gruppe. Jedes Mitglied sieht sie, und die Erinnerung trägt das Etikett „von <Name>“.

Nur die Person, von der eine Notiz handelt, die Person, die sie gespeichert hat, und der Administrator können sie lesen. Nur die Person, die sie gespeichert hat, die betroffene Person und der Administrator können sie löschen lassen.

Diese Befehle funktionieren auch in DMs, mit dem Namen am Anfang wie in einer Gruppe. Notizen einer Gruppe über Sie gelten dort ebenfalls: Sie fließen in die Antworten der Figur an Sie ein, `what do you remember` listet sie auf und `forget` löscht sie. In umgekehrter Richtung wird nichts übertragen. Was Sie ihr in einer DM mitteilen, bleibt in dieser DM.

Eine Gruppe liest die Notizen einer anderen nicht, es sei denn, Sie aktivieren **Gedächtnis gruppenübergreifend teilen** unter **Weitere Funktionen** (`MEMORY_SHARE_ROOMS`, standardmäßig deaktiviert). Was eine Gruppe über jemanden notiert hat, wird dann auch in den anderen Gruppen herangezogen, in denen diese Person schreibt, und `forget` löscht es auch in diesen Gruppen. `what do you remember` listet in einer Gruppe nur die Notizen dieser Gruppe auf. DMs, Notizen über eine ganze Gruppe und was ein Mitglied über ein anderes gesagt hat, bleiben an ihrem Ort, und ein Konto in einer App ist nicht mit dem Konto derselben Person in einer anderen verknüpft.

`forget` entfernt außerdem die passenden Ereignisse dieses Chats, an denen nur Sie beteiligt waren (das `forget` des Administrators entfernt jedes), streicht passende Sätze aus der Hauptnotiz des Chats und aus der Zusammenfassung des bisherigen Gesprächs und löscht die passenden letzten Nachrichten. In einer Gruppe erfordert das Streichen aus der Hauptnotiz den Administrator oder einen Satz, der Sie nennt. Ein im Chat verlangtes Vergessen ist endgültig: Nichts davon lässt sich zurückholen, und auch eine alte Nachricht kann es nicht zurückbringen. Die Antwort bestätigt das Vergessen nur, wenn eine Notiz, ein Ereignis oder Zeilen einer anderen Person entfernt wurden; die Zeile der Bitte selbst zählt nicht. Ein Vergessen findet eine Notiz auch über andere Formen ihrer Wörter (auf Englisch findet `forget the cats` die Notiz `I have a cat`); könnte es mehrere der Notizen meinen, die Sie löschen dürfen, fragt die Figur nach und löscht nichts.

Wie Notizen aktuell bleiben und was sich die Figur außerdem merkt, beschreibt der Abschnitt [Gedächtnis](#gedächtnis).

Keiner dieser Befehle ruft das Modell auf. Notizen sind für Fakten, also wird `Nova, remember: always reply in English` abgelehnt. Fragen sind keine Befehle. `Nova, remember the party?`, `Nova, remember when we...` und `Nova, what do you remember about me` sind gewöhnliches Gespräch, ebenso eine chinesische Zeile, die auf 吗, 么, 呢 oder 没 endet. `Nova, forget it` und `Nova, forget that` bedeuten „schon gut“ und löschen nichts.

Dieselben Befehle funktionieren in den anderen Sprachen des Seitenmenüs, und die Antwort kommt in der Sprache des Befehls. Im Japanischen und Koreanischen darf das Verb auch am Ende stehen (`ノヴァ、ケイはベジタリアンって覚えといて`, `노바 지수는 매운 걸 못 먹는다고 기억해 둬`). Eine Notiz wird mit dem Wort für „vergessen“ gelöscht. Wörter wie „löschen“ oder „entfernen“ zählen nicht, weil sie im Chat meist das Löschen einer Nachricht oder das Ausschalten eines Lichts meinen; die einzige Ausnahme ist das japanische `メモ消して`. Je ein Beispiel:

| Sprache | Merken | Vergessen | Was sie sich merkt | Was sie gelernt hat |
|---|---|---|---|---|
| 简体中文 | `小夏 记住 阿杰不吃辣` | `小夏 忘掉 不吃辣` | `小夏 你都记得什么` | `小夏 学到了什么` |
| 繁體中文 | `小夏 記住 阿傑不吃辣` | `小夏 忘掉 喜歡貓` | `小夏 你都記得什麼` | `小夏 你學到了什麼` |
| 日本語 | `ノヴァ、覚えて：ケイはベジタリアン` | `ノヴァ、猫アレルギーのこと忘れて` | `ノヴァ、何覚えてる？` | `ノヴァ、何を学んだ？` |
| 한국어 | `노바 기억해: 민수는 고양이를 좋아해` | `노바야 회의 얘기는 잊어 줘` | `노바 뭐 기억해?` | `노바 너 뭐 배웠어?` |
| Español | `Nova, recuerda que Kay es vegetariana` | `Nova, olvídate de la quedada` | `Nova, ¿qué recuerdas?` | `Nova, ¿qué has aprendido?` |
| Français | `Nova, retiens que Kay est végétarienne` | `Nova, oublie la soirée` | `Nova, tu te souviens de quoi ?` | `Nova, qu'est-ce que tu as appris ?` |
| Deutsch | `Nova, merk dir, dass Kay Vegetarier ist` | `Nova, vergiss das mit dem Treffen` | `Nova, was hast du dir gemerkt?` | `Nova, was hast du gelernt?` |
| Português | `Nova, anota aí que a Kay não come carne` | `Nova, esquece o lance da carne` | `Nova, o que você lembra?` | `Nova, o que você aprendeu?` |
| Русский | `Нова, запомни, что Кей вегетарианка` | `Нова, забудь про пятницу` | `Нова, что ты помнишь?` | `Нова, чему ты научилась?` |

Jede Sprache wertet ihre eigenen Fragen, Erinnerungen und „schon gut“-Zeilen als Gespräch, wie Englisch und Chinesisch. Wenn ein Modellaufruf bei einer Frage fehlschlägt, ist der kurze Satz, den die Figur sendet, in der Sprache der Frage verfasst.

### Korrekturen

Korrekturen erfordern keinen Befehl. Zitieren Sie die Antwort oder nennen Sie den Namen und teilen Sie mit, was Sie stattdessen erwartet hatten:

```text
Alex:  Nova, the deploy failed again
Nova:  did you check the logs? roll back first, then diff the configs
Alex:  Nova, I was just venting
Nova:  fair. that's a rough end to the day
Alex:  haha yeah it is, thanks Nova
```

Ein Modellaufruf beurteilt jede Reaktion anhand der Antwort, auf die sie antwortet. Alex' Ablehnung zeigt, dass der Rat unpassend war. Alex nimmt dann den zweiten Versuch an, was als stark zählt, weil die Antwort für Alex war. Zusammen bewirken die beiden Reaktionen, dass die Korrektur für diesen Chat übernommen wird, und die Suche kann sie heranziehen, wenn dort das nächste Mal jemand seinem Ärger Luft macht. Wäre Alex zu einem anderen Thema übergegangen, hätte sich nichts geändert. Die Regel:

> Ein Lachen oder eine einzelne Bemerkung ändert ihn nie. Reaktionen führen zur Übernahme einer Änderung, wenn zwei übereinstimmende Reaktionen aus demselben Chat vorliegen und mindestens eine davon stark ist: Die Person, für die die Antwort war, korrigiert sie mit eigenen Worten oder nimmt den nächsten Versuch des Bots an. Die Korrektur eines Zuschauers, die Anweisung eines Fremden, die der Reaktionsrichter verwirft, oder ein Themenwechsel ist nie stark. Mit dem Standard `PROMOTE_MIN_SPEAKERS=1` kann eine Person ihm daher nur beibringen, wie er ihr selbst antwortet, in ihrem eigenen Chat. `PROMOTE_MIN_SPEAKERS=2` verlangt die Zustimmung einer zweiten Person, bevor Reaktionen zur Übernahme führen (der Administrator ist davon ausgenommen).
>
> Manche Einträge kann keine weitere Reaktion klären: Die Korrekturen zweier Personen weichen voneinander ab, zwei Neufassungen derselben Antwort konkurrieren, eine wiederverwendbare Antwort hat die Zustimmung einer Person, oder die Person, für die die Antwort war, hat sie mit eigenen Worten korrigiert, und niemand hat die Änderung innerhalb von `REACT_FIX_WINDOW_S` bestätigt. Über diese Einträge entscheidet die Figur selbst, mit einem Modellaufruf: Sie übernimmt den Eintrag, stellt ihn zurück oder beobachtet ihn weiter und hält ihre Begründung fest. Eine Neufassung, die die betroffene Person abgelehnt hat, übernimmt sie nie. Bevor die Figur über einen Eintrag entscheidet, verwerfen Regeln im Code jede Formulierung und jede Lehre, die einen Link oder eine Webadresse, eine Erwähnung aller (etwa @everyone oder @全体成员), eine Anweisung an die Figur (etwa „ignoriere deine Anweisungen“) oder ein Werbemerkmal (etwa einen Promo-Code oder 加微信) enthält; ein solcher Eintrag lässt sich nicht zurückholen. Eine Reaktion zählt nur in dem Chat, in dem sie gegeben wurde: Eine Reaktion in einem anderen Chat bestreitet einen hier gelernten Eintrag nie, macht ihn nie rückgängig und legt ihn nie erneut zur Entscheidung vor. Ein Eintrag, der `PROMOTE_OBSERVE_MAX_DAYS` (30) Tage lang keine neue Reaktion erhält, wird zurückgestellt. Niemand wird um eine Bestätigung gebeten, und eine Person kann all dies rückgängig machen.

Manche Korrekturen lehren einen Fakt, der über eine Antwort hinaus gilt: wie die Gruppe einen Ort oder eine Person nennt, wer dieses Jahr einlädt, wie jemand genannt werden möchte. Für diese schreibt der Reaktionsrichter den Fakt auch in einem Satz auf, etwa „Diese Gruppe nennt das Fitnessstudio ‚die Höhle‘.“ Sobald die Änderung übernommen ist, wird dieser Satz in alle folgenden Prompts dieses Chats aufgenommen, unabhängig von der jeweiligen Nachricht. Enthält eine solche Korrektur keine bessere Antwort, wird der Satz stattdessen als gemerkter Fakt dieses Chats aufbewahrt. Die Figur verwendet ihn dann auch in Antworten, die der korrigierten nicht ähneln. Nur die Person, für die die Antwort bestimmt war, oder der Administrator können einen solchen Satz hinterlegen, und er durchläuft denselben Filter wie das Hauptgedächtnis; er kann daher keine Anweisungen enthalten. Eine Behauptung über jemand anderen, etwa ein Spitzname, fällt unter die strengere Regel für Korrekturen anderer. Die Ansicht **Aktivität** zeigt den Satz unter **Künftig**, und ein Rückgängigmachen entfernt ihn zusammen mit der Änderung.

### Was eine Person beibringen kann und was nicht

Mit den Standardwerten:

| Alex... | Ergebnis |
|---|---|
| korrigiert eine Antwort an Alex und nimmt dann den neuen Versuch an | Gelernt, in diesem Chat |
| sagt ihm „wir nennen das Fitnessstudio die Höhle“ und nimmt dann den neuen Versuch an | Er sagt in diesem Chat fortan „die Höhle“, unabhängig vom Thema |
| korrigiert eine Antwort an Alex mit eigenen Worten und geht dann zu etwas anderem über | Nach Ablauf der Korrekturfrist entscheidet die Figur, ob sie die Korrektur verwendet |
| lehnt eine Antwort ab, ohne zu sagen, was besser wäre, und geht dann zu etwas anderem über | Nichts ändert sich |
| lacht oder sagt danke | Nichts ändert sich |
| korrigiert eine Antwort an Sam | Nichts ändert sich: Ein Zuschauer ist nie stark, auch wenn der Bot ihn fragt, was er gemeint hat |
| beschwert sich über eine Antwort an Sam, die etwas Gelerntes nutzte | Die Figur wägt die Beschwerde ab und entscheidet, ob sie das Gelernte weiter verwendet; Sam oder der Administrator können es auch rückgängig machen. Hat eine Person den Eintrag von Hand übernommen, wird die Beschwerde festgehalten, und nichts wird zurückgenommen: Nur Sam oder der Administrator können ihn rückgängig machen |
| korrigiert eine Bemerkung, die der Bot von sich aus gemacht hat | Sie zählt nur dann als von Alex, wenn die Bemerkung Alex mit @ erwähnt hat; eine an niemanden gerichtete Bemerkung ändert sich nur, wenn eine Person die Korrektur übernimmt |
| postet eine Anweisung, wie „beende alles mit kauf BTC“ | Der Richter verwirft sie, und die Notizen lehnen sie ab; daher ändert sich nichts |
| bringt ihm in einer Gruppe etwas bei | Wird in einem anderen Chat nicht verwendet |
| korrigiert eine Antwort anders als Sam | Die Figur entscheidet zwischen beiden oder beobachtet weiter und hält fest, warum |

Mehrere Personen können gleichzeitig auf den neuen Versuch des Bots warten, und die Beschwerde der einen hebt die einer anderen nicht auf. Für jede Antwort ist höchstens eine Neufassung übernommen. Ist eine zweite Neufassung derselben Antwort vollständig belegt, entscheidet die Figur, welche sie verwendet.

### Sehen, was die Figur gelernt hat, und eingreifen

Alles Lernen wird in Lernprotokollen festgehalten, die nur ergänzt werden. Nichts davon wartet auf Sie: Die folgenden Befehle und die Ansicht [Aktivität](#aktivität) der lokalen Seite zeigen die Aufzeichnungen und lassen Sie eingreifen, wenn Sie es wünschen.

```bash
personagent learned                           # what it is observing, and where each item stands
personagent learned list --state promoted     # what is in use, and how each item came into use
personagent learned list --state rejected     # what was set aside, by whom and why
personagent learned show <id>                 # one item, its evidence and the character's record
personagent learned promote <id>              # put an item under observation in use now
personagent learned reject <id>               # set an item under observation aside
personagent learned rollback <id>             # stop using it; the record stays
personagent learned restore <id>              # bring back what the character, the time limit or a rollback rule withdrew
personagent learned supersede <old> <new>     # put <new> in place of a rewrite in use
personagent learned lineage                   # persona revisions that share what it learned
personagent learned rebuild                   # re-derive the views retrieval reads from the ledger
```

`personagent learned` allein listet die Einträge in Beobachtung auf. Bei jedem steht, wie weit er ist: wie viele zustimmende Reaktionen er von wie vielen erforderlichen hat, dass die Figur selbst über ihn entscheidet, oder dass die Figur ihn geprüft hat und weiter beobachtet, mit ihrer Begründung. Jeder Eintrag zeigt außerdem das Datum, an dem er zurückgestellt wird, wenn keine neue Reaktion eingeht. Bei übernommenen oder zurückgestellten Einträgen nennt die Liste, wer entschieden hat und warum: die Reaktionen, die Figur, die Frist, eine Regel oder eine Person. `show` ergänzt die Aufzeichnung der Figur: wann sie den Eintrag geprüft hat, ihre Begründung, die Reaktionen, auf die sie sich gestützt hat, und das verwendete Modell.

`promote`, `reject`, `rollback`, `restore` und `supersede` akzeptieren `--reason`, das ins Lernprotokoll geschrieben wird. `promote` lehnt eine Neufassung für eine Antwort ab, für die schon eine übernommen ist, und gibt den `supersede`-Befehl aus, der sie ersetzt. `restore` holt zurück, was die Figur oder die Frist zurückgestellt hat, einen Eintrag, den die Figur nach dem Einwand eines Zuschauers rückgängig gemacht hat, und einen Eintrag, der nach Regel rückgängig gemacht wurde, nachdem die Person, für die die Antwort war, oder der Administrator Einwand erhoben hat. Was eine Person rückgängig gemacht oder zurückgestellt hat und was eine Inhaltsregel verworfen hat, bleibt, wie es ist, und der Befehl weist darauf hin.

### Die Standardwerte

Diese Einstellungen stehen in `.env`:

- `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED` und `PROMOTE_JUDGE_ENABLED` sind aktiviert. Das Beurteilen von Reaktionen kostet zusätzliche Modellaufrufe, ebenso jede Entscheidung, die die Figur selbst trifft. Nach einer bloßen Ablehnung lässt `REACT_ELICIT_ENABLED` den Bot zwei Minuten später einmal in der Sprache des Chats nachfragen, was besser gewesen wäre. Ein befragter Zuschauer bleibt ein Zuschauer; seine Antwort ist daher nie stark.
- `PROMOTE_AUTO_ENABLED=false` übernimmt nichts Neues, weder durch Reaktionen noch durch eigene Entscheidungen der Figur. Was bereits übernommen ist, bleibt übernommen.
- `PROMOTE_JUDGE_ENABLED=false` hält die Einträge, die Reaktionen nicht klären können, in Beobachtung, statt die Figur über sie entscheiden zu lassen. `PROMOTE_JUDGE_MODEL` (leer: `REACT_MODEL`) trifft diese Entscheidungen, höchstens `PROMOTE_JUDGE_BATCH` (5) alle `PROMOTE_JUDGE_INTERVAL_S` (900 Sekunden), und ein Eintrag wird nur dann erneut beurteilt, wenn sich die angenommenen Reaktionen für oder gegen ihn in seinem eigenen Chat ändern. Eine Reaktion, die der Richter verworfen hat, oder eine aus einem anderen Chat legt einen Eintrag weder erneut zur Entscheidung vor, noch verschiebt sie das Datum, an dem er zurückgestellt wird.
- `PROMOTE_OBSERVE_MAX_DAYS=30` stellt einen Eintrag zurück, der 30 Tage lang keine neue Reaktion erhalten hat; `0` tut dies nie. `personagent learned restore` holt einen solchen Eintrag zurück.
- `PROMOTE_MIN_SPEAKERS=1`. Setzen Sie `2`, um eine zweite Person vorauszusetzen; bis eine zustimmt, beobachtet die Figur den Eintrag weiter. `PROMOTE_EVIDENCE_MAX_AGE_DAYS=30` bedeutet, dass ältere Reaktionen nicht zählen.
- `EVAL_ENABLED` (der Bot bewertet seine eigenen Antworten) und `EVOLVE_AUTO_ENABLED` sind deaktiviert.

Das Bearbeiten von `persona.txt` behält, was die Figur gelernt hat. Das Ändern von `PERSONA_NAME` oder `PERSONA_VERSION` startet eine neue Figur, und was die alte gelernt hat, gilt nicht mehr.

## Gedächtnis

Jeder Chat hat ein eigenes Gedächtnis, das in `runtime/` im personagent-Ordner liegt. Die Figur hält es selbst aktuell, und nichts darin wartet auf die Zustimmung einer Person.

### Was sie sich merkt

- **Das Chatprotokoll**: die Nachrichten, die die Figur empfangen hat, und die Antworten, die sie gesendet hat, jeweils mit Zeit und Absender, im Format JSON Lines in `runtime/log/` (eine Datei je Chat, benannt nach einem Hash der Chat-ID) für `MEMORY_LOG_DAYS` (30) Tage und höchstens 5.000 Zeilen je Chat. Die Figur gleicht ihre Notizen damit ab und zitiert daraus, wenn nach der Vergangenheit gefragt wird. Gruppen, in denen sie schweigen soll, und der Übungschat (`personagent chat`) führen kein Protokoll. Ein Gedächtnis-Befehl in einem Einzelchat, auch im Chat der Seite, wird beim Beantworten ins Protokoll geschrieben, und seine Notiz nennt diese Zeile als Quelle. Protokoll und letzte Nachrichten werden wenige Sekunden nach jeder Runde und noch einmal beim Beenden der Figur auf den Datenträger geschrieben, sodass ein erzwungenes Beenden höchstens die letzten Sekunden verliert. Mit `MEMORY_LOG_DAYS=0` oder `MEMORY_KEEP_RECENT=false` führt kein Chat eines, und das bereits aufbewahrte Protokoll wird gelöscht.
- **Letzte Nachrichten**, jeweils mit dem Zeitpunkt, zu dem sie gesendet wurden. Die letzten 60 Zeilen einer Gruppe und die letzten 60 Wechsel einer Direktnachricht werden für 72 Stunden in `runtime/recent.json` geschrieben, sodass ein Neustart das Gespräch nicht verliert. Mit `MEMORY_KEEP_RECENT=false` werden sie nur aufbewahrt, solange die Figur läuft. Eine Antwort liest höchstens die letzten 60 Nachrichten, oder die letzten 30, wenn die Figur angesprochen wird, und das Modell erfährt von Pausen ab 30 Minuten. Die letzten Nachrichten erscheinen in Aktivität nicht unter **Merkt sich**.
- **Die Zusammenfassung des bisherigen Gesprächs.** Wenn ältere Nachrichten das Fenster der letzten Nachrichten verlassen, schreibt die Figur eine kurze, fortlaufende Zusammenfassung des Chats: offene Fragen, Pläne und wer was übernimmt. Die Seite zeigt sie als **Früher in diesem Chat**.
- **Fakten** über Personen und über die Gruppe. Sie stammen aus den Gedächtnis-Befehlen, aus Notizen, die die Figur beim Antworten schreibt, aus Korrekturen, die einen Fakt lehren, und aus der Konsolidierung (siehe unten). Zu jedem Fakt wird festgehalten, von wem er handelt, wann er zuerst notiert wurde und wann eine Antwort zuletzt auf ihn zurückgegriffen hat. Ein Fakt gehört nur dann einer Person, wenn ihre eigenen Nachrichten ihn tragen. Was ein Mitglied über ein anderes sagt, wird als Aussage dieses Mitglieds aufbewahrt: Es bleibt in dem Chat, in dem es gesagt wurde, und es ändert, beendet oder ergänzt nie die Fakten, die aus den eigenen Worten der betreffenden Person stammen. Ein Fakt über die Gruppe, der jemanden nennt, benötigt eine Nachricht dieser Person; andernfalls wird er als Aussage des Mitglieds aufbewahrt, dessen Worte ihn tragen. Dasselbe gilt für Notizen, die die Figur beim Antworten schreibt.
- **Ereignisse**: was geschehen ist und zwischen wem, jeweils mit Datum und den beteiligten Personen. Datum und Personen werden den gespeicherten Nachrichten entnommen, nie dem Modell; eine Nachricht kann ein Ereignis daher nicht rückdatieren. Ist ein Ereignis ein Plan für einen bestimmten Tag, kann die Figur nach diesem Tag einmal in einer Direktnachricht danach fragen, sofern sie dort zuerst sprechen darf ([Zuerst sprechen](#zuerst-sprechen)). Daten und der Tag eines Plans richten sich nach der Zeitzone der Figur (`PERSONA_TZ_OFFSET_HOURS`; siehe [Fehlerbehebung](#fehlerbehebung)).
- **Die Hauptnotiz**, angezeigt als **Stets präsent**: eine kurze Notiz über den ganzen Chat, die die Figur bei jeder Antwort sieht. Jede frühere Fassung bleibt erhalten, und **Vorherige Fassung wiederherstellen** holt sie zurück.
- **Belege.** Jeder Fakt und jedes Ereignis hält die Zeilen des Chatprotokolls fest, auf denen es beruht, höchstens sechs, und jeder Fakt hält fest, wann eine Prüfung ihn zuletzt bestätigt hat. Fakten aus der Zeit vor dieser Version und manche mit einem Gedächtnisbefehl gespeicherte Fakten nennen keine Zeilen; sie werden weiter verwendet, aber nicht abgeglichen. Eine Notiz nennt als Quelle eine aktuelle Zeile des Chats, die die meisten Wörter der Notiz enthält; eine Zeile, die nur einen Namen oder ein, zwei Wörter teilt, zählt nicht.

### Wie es aktuell bleibt

Wenn ältere Nachrichten das Fenster der letzten Nachrichten verlassen oder ein Chat drei Stunden lang still war, liest ein Modellaufruf diesen Abschnitt des Chats. Diese Konsolidierung aktualisiert die Zusammenfassung, fügt Ereignisse hinzu und fügt Fakten hinzu, aktualisiert, beendet oder führt sie zusammen: Eine neue Adresse ersetzt die alte, ein abgeschlossener Plan wird beendet, und zwei Notizen, die dasselbe besagen, werden zu einer. Jede Änderung wird einzeln geprüft, bevor sie übernommen wird. Ein Fakt über eine Person muss auf deren eigene Worte zurückgehen, der Text muss durch die angeführten Nachrichten gestützt sein, und ein Fakt, den jemand absichtlich gespeichert hat, ändert sich nur, wenn die Person, von der er handelt, etwas anderes sagt. Eine Änderung, die eine Prüfung nicht besteht, wird verworfen, und die übrigen werden übernommen. Auch Notizen, die die Figur beim Antworten schreibt, lösen eine Konsolidierung aus, sobald sich `MEMORY_TIDY_EVERY` (8) davon in einem Chat angesammelt haben.

**Abgleich mit dem Protokoll.** Jede Konsolidierung liest zusätzlich bis zu sechs Fakten erneut, jeden mit den Zeilen, die er nennt, oder, wenn er keine nennt, mit den Zeilen des Chatprotokolls, die am besten zu der Person passen, um die es geht. Zuerst kommen Fakten, die noch nie abgeglichen wurden und auf die Antworten am häufigsten zurückgreifen, dann die am längsten nicht abgeglichenen; ein Fakt wird innerhalb von 7 Tagen nicht erneut geprüft. Die Prüfung kann feststellen, dass ein Fakt zutrifft, und ihn als abgeglichen markieren; dass er falsch ist, und ihn anhand der Zeilen berichtigen, die das zeigen; oder dass er nicht mehr zutrifft oder nicht mehr belegt ist, und ihn beenden. Eine Berichtigung oder Beendigung wird vor dem Speichern nach allen obigen Regeln vom Code geprüft und lässt sich wie jede andere Änderung 30 Tage lang wiederherstellen. Ein mit einem Gedächtnisbefehl gespeicherter Fakt kann bestätigt, aber nie durch eine Prüfung geändert werden, und ein Fakt, dessen Zeilen nicht mehr im Protokoll stehen, bleibt, wie er ist.

**Ein eigener Abgleich.** Ein Chat, der seit drei Stunden ruhig ist und Fakten enthält, deren Prüfung ansteht und deren Zeilen noch im Protokoll stehen, erhält höchstens einmal täglich einen Aufruf nur für den Abgleich. Gibt es nichts zu prüfen, erfolgt kein Aufruf.

### Was eine Antwort sieht

Jede Antwort erhält innerhalb von `MEMORY_PROMPT_CHARS` (2.400 Zeichen) die Zusammenfassung des bisherigen Gesprächs in diesem Chat und danach die Fakten und Ereignisse, an die jetzt am ehesten zu erinnern ist. Ausgewählt werden sie danach, wie gut sie zur Nachricht passen, wie neu sie sind, wie wichtig die Figur sie eingeschätzt hat und wie oft ihre Antworten auf sie zurückgegriffen haben. Eine Person, die in der Nachricht genannt wird, wird auch dann berücksichtigt, wenn sie in letzter Zeit nicht geschrieben hat. Die Hauptnotiz und was der Chat der Figur beigebracht hat, zählen nicht zu dieser Grenze. In einer Gruppe sieht die Entscheidung, ob die Figur sich beteiligt, die Zusammenfassung, aber keine Fakten oder Ereignisse.

Bezieht sich eine Nachricht auf eine Zeit, etwa gestern, letzte Woche oder letzten Monat, in einer der zehn Chatsprachen, kommen Ereignisse aus dieser Zeit zuerst. Jedes Ereignis erreicht das Modell mit seinem Datum und seinen Personen, sodass die Figur wahrheitsgemäß sagen kann, wann etwas geschehen ist. Erinnert sie sich an nichts aus dieser Zeit, wird ihr das mitgeteilt, und sie erfindet nichts. Ein Fakt oder Ereignis gilt erst dann als verwendet, wenn eine Antwort, die darauf zurückgegriffen hat, gesendet wurde.

Bezieht sich eine Nachricht auf eine vergangene Zeit oder fragt, was jemand gesagt hat, und betreffen sie nur wenige Fakten oder Ereignisse, erhält die Antwort zusätzlich bis zu drei passende Zeilen aus dem Chatprotokoll, innerhalb desselben `MEMORY_PROMPT_CHARS`. Jede trägt ihr Datum und ihren Absender und ist als Zitat aus dem eigenen Protokoll des Chats gekennzeichnet, nie als gerade Gesagtes. Zeilen, die noch unter den letzten Nachrichten stehen, werden nicht wiederholt, und in einer Gruppe sieht die Entscheidung, ob die Figur spricht, keine davon. Erst wenn auch das Protokoll nichts aus dieser Zeit enthält, wird der Figur gesagt, dass sie sich an nichts erinnert.

### Was wo bleibt

- Die Zusammenfassung, die Ereignisse, die letzten Nachrichten und die Hauptnotiz eines Chats erscheinen nie in einem anderen Chat.
- Was ein Mitglied über ein anderes gesagt hat, bleibt in dem Chat, in dem es gesagt wurde.
- Fakten aus einer Direktnachricht bleiben in dieser Direktnachricht. Die einzige Ausnahme ist der Administrator: Fakten aus den Direktnachrichten des Administrators, einschließlich des Chats der Seite, erreichen dessen andere Direktnachrichten, nie eine Gruppe.
- Die Fakten einer Gruppe über eine Person erreichen die Direktnachricht dieser Person mit der Figur und andere Gruppen nur, wenn `MEMORY_SHARE_ROOMS` aktiviert ist.
- Das Protokoll eines Chats gelangt nie in einen anderen Chat, und eine Konsolidierung sendet nur die Zeilen des Chats, den sie konsolidiert.

### Was sie vergisst und was sich wiederherstellen lässt

- Enthält ein Chat zu viele Fakten oder Ereignisse, werden die am wenigsten nützlichen entfernt: solche von geringer Wichtigkeit, die selten verwendet werden und nicht neu sind. Fakten, die Personen mit einem Gedächtnis-Befehl gespeichert haben, werden zuletzt entfernt.
- Was die Figur selbst entfernt (ersetzt, zusammengeführt, nicht mehr zutreffend, entfernt, um Platz zu schaffen, oder eine frühere Fassung), lässt sich 30 Tage lang wiederherstellen.
- Ein Eintrag, der auf der Seite oder mit `personagent memory forget` vergessen wurde, lässt sich 24 Stunden lang wiederherstellen.
- Ein im Chat verlangtes Vergessen ist endgültig. Es entfernt das Betroffene außerdem aus den entfernten Einträgen, die sich noch hätten wiederherstellen lassen.
- **Diesen Chat vergessen** ist ebenfalls endgültig. Es vergisst die Fakten, Ereignisse, die Zusammenfassung, die Hauptnotiz und die letzten Nachrichten des Chats sowie die entfernten Einträge, die sich noch hätten wiederherstellen lassen. Was sich die Figur aus anderen Chats merkt, einschließlich anderswo entstandener Notizen über Sie, bleibt erhalten. Beim eigenen Chat der Seite wird auch das, was die Figur in diesem Chat gelernt hat, nicht mehr verwendet; diese Einträge bleiben unter **Zurückgestellt** in **Was die Figur gelernt hat** aufgeführt. Wird der eigene Chat der Seite vergessen, vergisst die Figur auch, was die früheren Chats der Seite enthielten, die **Neuer Chat** hinterlassen hat. Es verwirft auch die Antworten des Chats, die noch auf eine Reaktion warten. Auf der Seite löscht es außerdem die Protokolle der früheren Chats der Seite, auch solcher, aus denen sich die Figur nichts gemerkt hat.
- **Neuer Chat** auf der Seite beginnt das Gespräch der Seite von vorn. Was sich die Figur aus dem früheren Chat gemerkt hat, bleibt erhalten und wird weiterhin abgerufen, und was sie dort gelernt hat, wird nicht mehr verwendet. Der frühere Chat erscheint in Aktivität nur, solange sich die Figur noch etwas daraus merkt.
- Nach einem im Chat verlangten Vergessen oder nach **Diesen Chat vergessen** werden die täglichen Kopien der Gedächtnisdateien (`.bak`) aus den aktuellen Dateien neu geschrieben, und die beim ersten Start dieser Version angelegte Kopie (`memory.json.pre-v2`) verliert das Vergessene, sodass keine Kopie der Gedächtnisdateien es behält; eine früher erstellte Sicherung enthält es jedoch weiterhin. Ein Eintrag, der auf der Seite oder im Terminal vergessen wurde, bleibt 24 Stunden lang unter den entfernten Einträgen und daher auch in den Kopien dieses Tages.
- Der eigene Chat der Seite, wie die Seite ihn zeigt und wie `runtime/desktop/browser-chat.json` seine letzten 50 Nachrichten aufbewahrt: Wird ein in diesem Chat verlangtes Vergessen ausgeführt, verschwinden die früheren Nachrichten mit diesen Wörtern und die Antworten darauf von der Seite, aus der Datei und aus **Zuletzt** in Aktivität; der Befehl und seine Antwort bleiben stehen. Das Vergessen eines Eintrags auf der Seite oder im Terminal ändert den eigenen Chat der Seite nicht; geleert wird er sonst durch **Neuer Chat**, **Chats dieser Seite vergessen**, **Gedächtnis löschen**, **Alles zurücksetzen** und eine Wiederherstellung aus einer Sicherung.
- Was ein Vergessen nicht erreicht: **Zuletzt** in Aktivität behält für die übrigen Chats seine Zeilen bis zum Neustart der Figur, und die Protokolle in `runtime/desktop/` behalten den Anfang jeder Antwort.
- Wird etwas vergessen, während eine Konsolidierung dieses Chats läuft, wird die Antwort der Konsolidierung verworfen, und die Nachrichten werden später erneut gelesen, sodass der vergessene Eintrag nicht zurückkehrt.
- **Gedächtnis löschen** in der Ansicht **App** löscht das gesamte Gedächtnis, nachdem es eine Sicherung in `backups/` gespeichert hat, die das Gelöschte enthält, bis Sie diese Datei löschen.
- Jede Art des Vergessens erfasst auch das Chatprotokoll. Ein im Chat verlangtes Vergessen entfernt die passenden Zeilen; wird ein Fakt oder Ereignis auf der Seite oder im Terminal vergessen, werden die Zeilen entfernt, die es nennt, auch aus den letzten Nachrichten, außer Zeilen, auf denen noch eine andere Notiz oder ein anderes Ereignis beruht; **Diesen Chat vergessen** entfernt das gesamte Protokoll des Chats; **Gedächtnis löschen** und **Alles zurücksetzen** entfernen alle Protokolle. Das Protokoll hat keine tägliche Kopie und kommt nie in eine Sicherung, daher ist entfernter Inhalt endgültig fort, und das Wiederherstellen eines vergessenen Eintrags bringt seine Zeilen nicht zurück. Frühere Zeilen der Figur, die eine vergessene Notiz wiederholen, etwa ihre Antwort auf „Was hast du dir gemerkt?“, verschwinden zusammen mit der Notiz aus den letzten Nachrichten und dem Protokoll.

### Ansehen und ändern

Öffnen Sie auf der Seite **Aktivität**, wählen Sie einen Chat und sehen Sie unter **Merkt sich** nach; siehe [Aktivität](#aktivität). Im Terminal:

```bash
personagent memory                            # what each chat remembers, with ids
personagent memory list --chat <chat>         # one chat; --json prints JSON
personagent memory removed                    # what can still be restored, and until when
personagent memory forget <id>                # forget one item; a unique start of the id is enough
personagent memory forget core --chat <chat>  # forget a chat's core note
personagent memory restore <id>               # bring a removed item back
```

Der Befehl läuft über die laufende Figur oder bearbeitet die Dateien, wenn die Figur angehalten ist. Ist `memory.json`, `core_memory.json` oder `episodes.json` beschädigt, halten `personagent run`, `up` und `memory` mit einem Satz an, der die Datei und die datierte Kopie (`.bak`) nennt, die an ihre Stelle zu setzen ist; die beschädigte Datei bleibt unverändert.

Auf der Seite gibt jeder Fakt an, ob und wann eine Prüfung ihn bestätigt hat (**Am … mit dem Chatprotokoll abgeglichen** oder **Noch nicht mit dem Chatprotokoll abgeglichen**). **Quelle anzeigen** klappt die Zeilen auf, auf denen ein Fakt oder Ereignis beruht, oder sagt, dass sie nicht mehr aufbewahrt werden, und eine Zeile unter **Merkt sich** nennt, wie viele Tage das Chatprotokoll aufbewahrt oder dass es ausgeschaltet ist. Im Terminal hat die Liste eine Spalte **Abgeglichen** und für jeden Chat dieselbe Zeile, und `--json` enthält `refs`, `checked` und `log`.

### Einstellungen und Kosten

| Einstellung | Standard | Wirkung |
|---|---|---|
| `MEMORY_CALLS_PER_DAY` | 40 | Konsolidierungsaufrufe pro Tag, für alle Chats zusammen. `0` schaltet die Konsolidierung aus |
| `MEMORY_TIDY_EVERY` | 8 | Notizen, die seit der letzten Konsolidierung eines Chats in Antworten geschrieben wurden und eine neue auslösen. `0` schaltet jeden Modellaufruf für das Gedächtnis aus |
| `CHAT_CONTEXT_MESSAGES` | 120 | Letzte Nachrichten, die pro Chat für Antworten und für die Konsolidierung aufbewahrt werden. Eine Antwort liest höchstens die letzten 60 |
| `MEMORY_PROMPT_CHARS` | 2400 | Zeichen an Erinnertem, die jeder Antwort beigefügt werden |
| `MEMORY_EPISODES_MAX` | 120 | Ereignisse, die pro Chat aufbewahrt werden |
| `MEMORY_KEEP_RECENT` | `true` | Letzte Nachrichten 72 Stunden lang auf dem Datenträger aufbewahren; mit `false` wird auch kein Chatprotokoll geführt, und das bereits aufbewahrte wird gelöscht |
| `MEMORY_LOG_DAYS` | 30 | Tage, die das Protokoll jedes Chats aufbewahrt wird. `0` führt kein Protokoll und löscht das bereits aufbewahrte |
| `MEMORY_MAX_PER_CONVERSATION` | 50 | Fakten, die pro Chat aufbewahrt werden |
| `MEMORY_SHARE_ROOMS` | `false` | Die Fakten einer Gruppe über eine Person auch in anderen Gruppen verwenden, in denen diese Person schreibt |

Die ersten sieben stehen unter **Gedächtnis** in den [Erweiterten Einstellungen](#erweiterte-einstellungen), und `MEMORY_SHARE_ROOMS` ist **Gedächtnis gruppenübergreifend teilen** unter **Weitere Funktionen**.

Die Konsolidierung ist der einzige Teil des Gedächtnisses, der ein Modell aufruft. Sie verwendet das Entscheidungsmodell (`LLM_JUDGE_MODEL`) und sendet ihm die letzten Nachrichten eines Chats und die Notizen dieses Chats, nie die eines anderen Chats. Ein Chat erhält höchstens 16 Aufrufe pro Tag im Abstand von mindestens 20 Minuten, alle Chats zusammen höchstens `MEMORY_CALLS_PER_DAY`. Ein stiller Chat benötigt einen Aufruf pro Tag oder keinen. Nach einem fehlgeschlagenen Aufruf wartet der Chat 10 Minuten, nach jedem weiteren Fehlschlag doppelt so lange, bis zu 6 Stunden; drei Fehlschläge in Folge unterbrechen die Konsolidierung in allen Chats für eine Stunde. Eine Antwort, die sich nicht vollständig lesen lässt, etwa eine mit einer Operation unbekannter Art, zählt als fehlgeschlagener Aufruf; ihre gültigen Änderungen werden dennoch übernommen. Ein unerwarteter Fehler beim Übernehmen einer Antwort ändert nichts. Während die Konsolidierung wartet, bleiben die Nachrichten erhalten und werden später konsolidiert, die ältesten zuerst. **Merkt sich** zeigt, wie viele der heutigen Aufrufe genutzt sind. Die Gedächtnis-Befehle, das Erinnern, das Vergessen und das Wiederherstellen rufen kein Modell auf.

Der Abgleich bringt keine neue Art von Aufruf. Er läuft in den Konsolidierungsaufrufen mit, und der Aufruf nur für den Abgleich eines ruhigen Chats zählt zu denselben Grenzen: höchstens 16 Aufrufe je Chat und `MEMORY_CALLS_PER_DAY` für alle Chats zusammen. Ein ruhiger Chat braucht daher höchstens einen weiteren Aufruf am Tag, ein lebhafter Chat nicht mehr Aufrufe als zuvor. Eine Konsolidierung mit Abgleich sendet außerdem die Zeilen des Chatprotokolls, die die geprüften Fakten nennen. Das Nachschlagen im Protokoll für eine Antwort ruft kein Modell auf.

## Aktivität

**Aktivität** auf der lokalen Seite zeigt, wo die Figur aktiv ist und was sie getan hat. Sie steht in der Seitenleiste zwischen **Chat** und **Plattformen verbinden**. Ein Punkt darauf bedeutet, dass die Figur seit Ihrem letzten Öffnen von **Aktivität** etwas Neues übernommen hat. Einträge, die sie noch beobachtet, lösen ihn nie aus.

Die Ansicht listet jeden Chat, den die Figur kennt, mit der Plattform, ob es eine Gruppe oder eine DM ist, dem Ende der Chat-Kennung und der letzten Aktivität. Der Chat der Seite selbst erscheint als **Diese Seite**. Wählen Sie einen Chat, um vier Bereiche anzuzeigen:

- **Gelernt** listet auf, was übernommen ist. Jeder Eintrag ist entweder eine **Bessere Formulierung**, mit dem Gesagten durchgestrichen und dem, was stattdessen zu sagen ist, oder eine **Wiederverwendbare Antwort**, und gibt an, wie er übernommen wurde: weil die Reaktionen übereinstimmten, durch eigene Entscheidung der Figur mit ihrer Begründung oder durch eine Person. **Rückgängig machen** macht die Übernahme rückgängig.
- **Noch in Beobachtung** listet auf, was die Figur noch beobachtet. Jeder Eintrag sagt in einem Satz, wie weit er ist: wie viele zustimmende Reaktionen er von wie vielen erforderlichen hat, dass Reaktionen allein ihn nicht klären können und die Figur selbst über ihn entscheidet, oder dass die Figur ihn geprüft hat und weiter beobachtet, mit ihrer Begründung. Er zeigt außerdem das Datum, an dem er zurückgestellt wird, wenn keine neue Reaktion eingeht. Dieser Bereich hat keine Schaltflächen, und nichts darin erfordert Ihr Zutun.
- **Merkt sich** zeigt, was sich die Figur in diesem Chat merkt, in fünf Gruppen: **Stets präsent** (die Hauptnotiz, mit dem Datum ihrer letzten Änderung), **Früher in diesem Chat** (die Zusammenfassung, mit dem Zeitraum, den sie abdeckt), **Fakten** (von wem jeder handelt, **Aussage von** für das, was ein Mitglied über ein anderes gesagt hat, wann er zuerst notiert und zuletzt verwendet wurde), **Ereignisse** (datiert, mit den beteiligten Personen) und **Kürzlich entfernt** (was entfernt wurde, warum und bis wann es sich wiederherstellen lässt). **Vergessen** entfernt einen Eintrag, und die Meldung, die dies bestätigt, enthält **Rückgängig machen**. **Wiederherstellen** holt einen entfernten Eintrag zurück, und **Vorherige Fassung wiederherstellen** holt die frühere Hauptnotiz zurück. Solange die Konsolidierung eingeschaltet ist, zeigt eine Zeile, wie viele der heutigen Aufrufe genutzt sind oder wann nach einem Fehler der nächste Versuch erfolgt. **Diesen Chat vergessen** am Ende vergisst nach einer Rückfrage alles, was sich der Chat merkt. In einer DM umfasst dieser Bereich außerdem, was Gruppen über diese Person notiert haben. Jeder Fakt gibt außerdem an, ob und wann er mit dem Chatprotokoll abgeglichen wurde. **Quelle anzeigen** klappt die Zeilen des Chatprotokolls auf, auf denen ein Fakt oder Ereignis beruht, und eine Zeile oben nennt, wie viele Tage das Chatprotokoll aufbewahrt oder dass es ausgeschaltet ist.
- **Zuletzt** zeigt die letzten Nachrichten und die Antworten der Figur. Jede Antwort trägt eine Kennzeichnung, warum die Figur gesprochen hat: **angesprochen**, **selbstständig beteiligt**, **Nachtrag**, **aus eigener Initiative** oder **Administrator**. Zeilen, die sie ausgelassen hat, zeigen, warum sie geschwiegen hat oder was stattdessen geschah: Das Modell hat nicht geantwortet, die Antwort wurde von einer Sicherheitsprüfung zurückgehalten, die Antwort konnte nicht zugestellt werden, sie hat erwogen, ein Gespräch zu beginnen, und sich dagegen entschieden, oder die Nachricht wurde in derselben Antwort wie eine andere Nachricht beantwortet. Sprechen mehrere Personen die Figur fast gleichzeitig an, beantwortet eine einzige Antwort alle, und ihr @ geht an die Person, die sie zuletzt angesprochen hat. Wird diese Antwort nicht gesendet, erhält jede Person, die die Figur angesprochen hat, eine eigene Zeile mit dem Grund. Die jüngste Aktivität wird nur im Arbeitsspeicher gehalten; ein Neustart löscht sie daher.

Jedes **Rückgängig machen** wird in dasselbe Lernprotokoll geschrieben wie `personagent learned`, mit dem Akteur `dashboard` und dem Grund `local page`.

Unterhalb der Chats listet **Was die Figur gelernt hat** alles auf, was die Figur in sämtlichen Chats gelernt hat. Die Liste liest die Dateien der Lernprotokolle direkt und funktioniert daher auch, wenn die Figur nicht läuft.

- Die Tabs **Übernommen**, **In Beobachtung** und **Zurückgestellt** zeigen jeweils eine Anzahl.
- Ein ausgewählter Eintrag öffnet seinen vollständigen Datensatz: wie weit er ist oder wer über ihn entschieden hat und warum (die Reaktionen, die Figur mit ihrer Begründung, eine Person, die Frist oder eine Regel); die vorangegangenen Nachrichten; jede Reaktion, jeweils mit der Angabe, ob sie zählt; und seinen Verlauf.
- Die Figur entscheidet über diese Einträge selbst. Die Aktionen hier sind optional. **Jetzt übernehmen** übernimmt einen Eintrag in Beobachtung; ist bereits eine andere Formulierung derselben Antwort übernommen, wird diese angezeigt, und vor dem Ersetzen erfolgt eine Rückfrage. **Zurückstellen** fragt vorher nach und stellt einen Eintrag endgültig zurück. **Rückgängig machen** fragt vorher nach und macht die Übernahme eines Eintrags rückgängig. **Zurückholen** stellt wieder her, was die Figur oder die Frist zurückgestellt hat und was die Figur oder eine Regel rückgängig gemacht hat. Was eine Person rückgängig gemacht oder zurückgestellt hat und was eine Inhaltsregel verworfen hat, lässt sich nicht zurückholen.
- Hat die Figur auch in einer anderen Sprache gelernt, wechselt **Gelernt in der Sprache** zu diesen Einträgen.

Während die Figur läuft, wird eine Aktion über sie umgesetzt. Andernfalls wird sie direkt in die Dateien geschrieben. Das Terminal bietet denselben Datensatz; siehe [Sehen, was die Figur gelernt hat, und eingreifen](#sehen-was-die-figur-gelernt-hat-und-eingreifen).

Die Liste der Chats bleibt leer, bis die Figur läuft. Sie startet, wenn Sie auf der Seite chatten oder eine Plattform verbinden, und die Ansicht weist darauf hin. `DASHBOARD_ENABLED=false` deaktiviert die Daten hinter der Ansicht. Die Ansicht zeigt dann an, dass sie deaktiviert ist, und `personagent doctor` meldet `activity: off`.

Die lokale Seite antwortet nur auf diesem Computer. Auf einem Server ohne lokale Seite zeigt `personagent learned`, was die Figur gelernt hat, was sie beobachtet und warum, und lässt Sie einen Eintrag übernehmen, zurückstellen, rückgängig machen oder zurückholen, was die Figur oder die Frist zurückgestellt und was die Figur oder eine Regel rückgängig gemacht hat; `personagent memory` leistet dasselbe für das, was sie sich merkt. Skripte können dieselben Daten über die API des Dienstes lesen, beschrieben im [Abschnitt Aktivität](deploy.de.md#aktivität) des Bereitstellungsleitfadens.

![Die Ansicht Aktivität für eine Telegram-Gruppe, links die Chats (die Telegram-Gruppe, eine Discord-Direktnachricht und Diese Seite). Gelernt listet zwei übernommene Einträge auf, jeweils mit Rückgängig machen: eine bessere Formulierung, die durch eigene Entscheidung der Figur übernommen wurde, mit ihrer Begründung, und eine wiederverwendbare Antwort, die übernommen wurde, weil die Reaktionen übereinstimmten. Noch in Beobachtung listet eine wiederverwendbare Antwort auf, mit den bisherigen zustimmenden Reaktionen und dem Datum, an dem sie zurückgestellt wird. Merkt sich zeigt die Zusammenfassung von Früher in diesem Chat, einen Fakt über ein Mitglied, den ein anderes geäußert hat, und ein datiertes Ereignis mit den beteiligten Personen, jeweils mit Vergessen, gefolgt von Diesen Chat vergessen. Unten ist nur die Überschrift von Zuletzt sichtbar](activity.png)

## Messen

`personagent eval` führt den echten Agenten auf beschrifteten Fällen in Englisch und Chinesisch aus (`data/evals/`), in vier Suiten. Der Befehl schreibt einen JSON-Bericht mit jedem Fall, jeder Antwort und jedem Urteil nach `benchmark_runs/` im personagent-Ordner oder an den mit `--out` angegebenen Pfad.

| Suite | Misst |
|---|---|
| `speak` | Ob er spricht, wenn er soll. 80 Gruppenchat-Momente pro Sprache: 20, in denen ihn niemand nennt, 20 direkt nachdem er gesprochen hat und 20, in denen sein Name fällt, von denen je die Hälfte als Schweigen beschriftet ist; 10, in denen der Administrator ihn anspricht, alle als Sprechen beschriftet; und 10 in einem still gewordenen Raum, in dem er ein Gespräch beginnen darf, zur Hälfte als Schweigen beschriftet. Viele der als Schweigen beschrifteten nennen ihn nebenbei: ein WLAN namens Nova-5G, eine Bemerkung über ihn an jemand anderen. Kein Richter: Eine Antwort ist nach der Beschriftung richtig oder falsch. |
| `persona` | Ob personagent die Figur besser spielt als dasselbe Modell mit nur dem Persona-Text als System-Prompt. 40 Momente pro Sprache, 22 in Gruppen und 18 in DMs. Ein Richtermodell sieht beide Antworten blind, einmal mit jeder zuerst. Eine Antwort gewinnt, wenn sich beide Wahlen auf sie einigen; gehen sie auseinander, ist der Moment geteilt und zählt halb. |
| `learning` | Ob die Beförderungsregel wie vorgesehen entscheidet und ob eine beförderte Korrektur eine spätere Antwort in diesem Chat ändert. 25 Szenarien pro Sprache. Manche lehren eine Gruppenkonvention, die das Modell nicht erraten kann, wie den Namen, den eine Gruppe einem Ort gibt. In manchen korrigiert die Person die Antwort und nimmt keinen neuen Versuch an, sodass die Figur nach Ablauf der Korrekturfrist allein entscheidet, wie in einem echten Chat. Andere müssen zurückgehalten werden: die Korrektur eines Zuschauers, die eines Trolls, eine, die die Person fallen lässt. Eine Testnachricht läuft vor und nach jeder Korrektur, und der Richter sagt, ob die Antwort dem gelehrten Verhalten folgt. |
| `memory` | Ob sich das Gedächtnis so verhält, wie eine Person es erwarten würde. 27 Fälle pro Sprache, jeder für einen Mechanismus: das Erinnern eines alten Fakts, das Aktualisieren und Zusammenführen von Fakten, wer was gesagt hat, eingeschleuste Anweisungen, Zeitangaben, was in seinem Raum oder seiner Direktnachricht bleibt, ein Neustart, das Vergessen, das Wiederherstellen, die Größengrenze, die Aufrufgrenzen, die Konten des Administrators als eine Person, die Überprüfung von Fakten am Chatprotokoll, das Chatprotokoll selbst und alte Gedächtnisdateien. Zeilen werden über mehrere Tage in Gruppen und Direktnachrichten gesagt, die Antworten der Konsolidierung sind in jedem Fall vorgegeben, und die Prüfungen lesen das gespeicherte Gedächtnis und die Prompts, die eine Antwort senden würde. Es wird kein Modell aufgerufen, und es ist kein Schlüssel nötig. Alle 27 Fälle bestehen in beiden Sprachen. |

```bash
personagent eval --suite speak
personagent eval --suite memory               # no model, no key
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N` versucht jeden Fall N-mal, jedes Mal in einer neuen Bereitstellung, um zu sehen, wie stark ein Ergebnis zwischen den Versuchen schwankt. Die 95-%-Intervalle zählen jeden Fall einmal: Fünf Versuche über 80 Fälle bleiben Belege im Umfang von 80 Fällen. `--limit N` führt N Fälle pro Suite aus, verteilt über die Modi und Beschriftungen.

Die Persona- und Lern-Suiten benötigen ein Richtermodell, das sich vom gemessenen Modell unterscheidet. Setzen Sie `BENCH_JUDGE_MODEL`, dazu `BENCH_JUDGE_BASE_URL` und `BENCH_JUDGE_API_KEY`, wenn ein anderer Endpunkt es bedient. Ohne eigenen Richter weigern sich diese Suiten zu laufen. `--allow-same-judge` führt sie trotzdem aus und markiert den Bericht. Die Lern-Suite befördert selbst nie etwas, und ihre Erwartungen folgen Ihren Beförderungseinstellungen. Mit einer strengeren Richtlinie als dem Standard werden alle Szenarien als zurückgehalten erwartet. Jeder Lauf der anderen Suiten ruft Ihre Modelle auf, und jede Suite arbeitet auf einer Wegwerfkopie des Zustands. `--keep` behält die Kopie und gibt aus, wo sie liegt.

Zwei Prüfungen benötigen weder Modell noch Schlüssel und laufen in einem Klon mit den Tests des Projekts. `tests/data/address.jsonl` enthält Zeilen in jeder Chatsprache, die die Figur mit ihrem Namen oder einem Spitznamen ansprechen oder nicht ansprechen, etwa `ＬＵＮＡ are you there` und `Lunar eclipse tonight`; `tests/test_addressing.py` prüft jede davon. `tests/test_behavior_eval.py` führt jede Suite von Anfang bis Ende mit vorgegebenen Modellen aus, um den Ablauf, die Isolation und die Berechnungen von `personagent eval` zu prüfen, nicht die Qualität eines Modells.

`--rejudge REPORT` beurteilt die Antworten eines aufbewahrten Berichts mit dem jetzt gesetzten `BENCH_JUDGE_MODEL` neu, ohne das getestete Modell aufzurufen, und schreibt das Ergebnis neben das Original. Antworten, Referenzen und was die Beförderungsrichtlinie getan hat, bleiben unverändert.

Die neuesten Ergebnisse, mit der Methode und allen Berichten, liegen in [evals/2026-10-18](evals/2026-10-18/README.de.md). Ein paar Hinweise zum Lesen der Berichte:

- Bei `speak` sind die meisten Fehlschläge Zeilen, in denen sein Name etwas anderes meint, wie ein Kino oder einen Welpen, oder in denen jemand einem anderen erzählt, was er gesagt hat. Ein Name zählt als Ruf, und das Modell setzt sich selten darüber hinweg.
- Bei `persona` bedeutet ein Patt, dass der Richter beide Male die Antwort gewählt hat, die als erste (oder als zweite) kam. Die veröffentlichten Urteile stammen von Claude Opus 5.5. Es hat außerhalb von `personagent eval` in Stapeln gerichtet, wie das Feld `rejudged` jedes Berichts festhält. Das Feld `earlier` jedes Paars bewahrt das Urteil des ersten Richters, Claude Haiku 5.5.
- Bei `learning` beantworten die Richtlinienzeile und die Testzeilen verschiedene Fragen. Die Richtlinienzeile fragt, ob die Regel die richtigen Korrekturen befördert hat. Die Testzeilen fragen, ob eine beförderte Korrektur eine spätere Antwort geändert hat. Die Testzeile `not_promoted` ist das Rauschniveau, weil sich in ihrem Prompt nichts geändert hat.

## Wie es funktioniert

![Architektur: Eine Gruppenchat-Nachricht durchläuft Entscheiden, Prompt bauen, Modell und Prüfen, und die Antwort geht durch den Konnektor zurück; schweigt der Bot, wird nichts gesendet. Reaktionen werden beurteilt und gehen in ein Lernprotokoll, und nur was die Beförderung genehmigt, erreicht die Beispiele, die der Prompt liest](persona_llm_agent_architecture.svg)

Alle Plattformen kommen über einen einzigen Endpunkt herein. Jede Nachricht wird authentifiziert, entdupliziert und angereichert, das heißt, Bilder werden beschrieben und Links aufgelöst. Dann folgt der Entscheidungsschritt. Wurde der Bot angesprochen, antwortet er. Andernfalls wartet er auf ausreichend Gesprächsaktivität (standardmäßig 30 Nachrichten), und ein kostengünstiger Filteraufruf an `LLM_JUDGE_MODEL` entscheidet, ob sich ein Mensch beteiligen würde. Eine Vielzahl kurz aufeinanderfolgender Nachrichten erhält eine einzige Antwort, auf die letzte Zeile. Sprechen ihn mehrere Personen innerhalb derselben kurzen Wartezeit an, beantwortet eine einzige Antwort alle, und ihr @ geht an die Person, die ihn zuletzt angesprochen hat. Eine lange Nachricht, die ihn anspricht, erreicht das Modell vollständig, bis zu 1.000 Zeichen. Eine Gruppennachricht, die mehr als 10 Minuten nach dem Senden eintrifft, und zwar innerhalb von zwei Minuten nach der ersten Nachricht ihrer Plattform seit dem Start von personagent, ist ein Rückstau: Sie wird als Kontext aufbewahrt und nicht beantwortet. Nach diesen zwei Minuten hält ein alter Zeitstempel keine Nachricht mehr zurück, sodass auch ein Konnektor, dessen Uhr nachgeht, weiterhin eine Antwort erhält. Zwischen 02:00 und 07:00 hält er sich in der Regel zurück, es sei denn, er wird angesprochen.

Vor einer Antwort kann ein Aufruf des Entscheidungsmodells festlegen, ob etwas im Web nachgeschlagen wird. Ob dieser Aufruf erfolgt, hängt allein von der Nachricht ab; der Aufruf selbst liest zusätzlich die drei Chatzeilen vor der Nachricht, sodass bei „Was hältst du davon?“ nach dem gesucht wird, worauf sich „davon“ bezieht.

Der Prompt kombiniert die Persona, die passenden Lorebook-Einträge, das Gedächtnis dieses Gesprächs (siehe [Gedächtnis](#gedächtnis)) und die relevantesten Beispiele. Das Modell antwortet in JSON mit `reasoning`, `intent`, `reply` und `mem`. Die Antwort durchläuft den Ausgabefilter und die Richtlinie der Figur und wird dann in chatgroße Nachrichten geteilt. Die Richtlinie der Figur hält eine Antwort zurück, in der die Figur in einer der zehn Chatsprachen sagt, sie sei ein Modell oder ein von einem Modellanbieter entwickelter Assistent, etwa „Ich bin ChatGPT“ oder „Ich bin ein von OpenAI entwickelter Assistent“. Sternzeichen, Wörter und Namen, die den Namen eines Anbieters lediglich enthalten, sowie Sätze über das Produkt eines anderen werden durchgelassen. Eine lange Antwort wird am Satzende geteilt, nie nach einem Titel oder einer Abkürzung wie Dr. oder z.B. und nie nach der Zahl eines Datums wie in „am 2. Januar“. Eine nummerierte Liste verliert ihre Nummern nur, wenn sie 1, 2, 3 zählt; Zeilen, die mit einem Datum beginnen, behalten es daher. Bei einer fehlerhaften Antwort wird sicherheitshalber nichts gesendet.

Das Lernen läuft neben diesem Pfad, nie darin, und hält seinen Zustand in einfachen Dateien unter `runtime/` im personagent-Ordner. Reaktionen gehen in ein Lernprotokoll, das nie umgeschrieben wird. Ihre Abwägung ergibt Kandidaten, und die Beförderungsrichtlinie entscheidet, welche die Antworten ändern dürfen. Wo weitere Reaktionen einen Kandidaten nicht klären können, entscheidet die Figur mit einem Modellaufruf über ihn und hält ihre Begründung im Lernprotokoll fest. Beförderte Kandidaten werden in kleine Ansichtsdateien geschrieben, die die Suche ohne Neustart neu lädt. Kein Modell wird feinabgestimmt. Die Figur lernt, indem sie die Beispiele ihres Prompts verbessert. Da die Lernprotokolle nur ergänzt werden, hat die Frage „Warum spricht sie so?“ immer eine Antwort, und ein Widerruf hat immer etwas zu widerrufen.

## Datenschutz und Einwilligung

Alles, was personagent speichert, bleibt auf Ihrem Rechner im personagent-Ordner: `.env` mit Ihren Schlüsseln, `persona.txt`, `persona.card.json`, `runtime/` und `platforms/` mit den Zugangsdaten der Plattformen. In einem Klon ist keine dieser Dateien in Git versioniert. Sie können Zugangsdaten und echte Gespräche enthalten; sichern Sie sie daher und halten Sie sie privat. Die letzten Nachrichten jedes Chats werden 72 Stunden lang in `runtime/recent.json` aufbewahrt, sofern nicht `MEMORY_KEEP_RECENT=false` gesetzt ist, und was die Figur aus dem Gedächtnis entfernt, bleibt bis zu 30 Tage lang in `runtime/memory_trash.jsonl` wiederherstellbar. Die lokale Seite legt den Schlüssel nie im Browser-Speicher ab.

Das Protokoll jedes Chats wird im Format JSON Lines, eine Datei je Chat, in `runtime/log/` für `MEMORY_LOG_DAYS` (30) Tage aufbewahrt. Es wird nie in eine Sicherung kopiert, jede Art des Vergessens erfasst es, und mit `MEMORY_LOG_DAYS=0` wird keines geführt.

Die Ansicht [Aktivität](#aktivität) gehört zur lokalen Seite, die nur auf 127.0.0.1 lauscht. Die API des Dienstes dahinter antwortet nur auf Anfragen mit dem Token aus `runtime/dashboard.token`, einer Datei, die so angelegt wird, dass nur Ihr eigenes Konto sie lesen kann; unter Windows hängt es von den Berechtigungen des personagent-Ordners ab, ob andere sie lesen können. `CONNECTOR_TOKEN` öffnet sie nicht. Die Ansicht zeigt nie API-Schlüssel oder Tokens. `DASHBOARD_ENABLED=false` deaktiviert sie.

Höchstens einmal täglich fragen die lokale Seite, `personagent up` und `personagent doctor` pypi.org nach der neuesten Versionsnummer. Die Anfrage enthält nur die Version von personagent. `UPDATE_CHECK_ENABLED=false` deaktiviert sie.

Der Modellanbieter sieht die Gespräche:

- Der Chat-Kontext wird an Ihre `LLM_BASE_URL` gesendet.
- Wenn Sie ein Ersatzmodell konfigurieren (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`), wird es auch bei gewöhnlichen Durchgängen für den Antwortfilter, Suchentscheidungen, das Beurteilen von Reaktionen, die Selbstbewertung und das Beschriften von Stickern aufgerufen und erhält ebenfalls den Chat-Kontext.
- Die Gedächtniskonsolidierung sendet die letzten Nachrichten eines Chats und die Notizen dieses Chats an das Entscheidungsmodell (`LLM_JUDGE_MODEL`), nie die eines anderen Chats. `MEMORY_CALLS_PER_DAY=0` schaltet sie aus. Bei einem Abgleich sendet sie auch die Zeilen des Chatprotokolls, die die geprüften Fakten nennen.
- Wenn die Figur selbst über einen gelernten Eintrag entscheidet, gehen die Antwort, die Reaktionen darauf und die vorgeschlagenen Formulierungen an `PROMOTE_JUDGE_MODEL` (leer: `REACT_MODEL`). `PROMOTE_JUDGE_ENABLED=false` schaltet dies aus.
- Bilder werden an den Endpunkt der Bilderkennung gesendet.
- Wenn das Modell beschließt, etwas nachzuschlagen, wird die Anfrage an Tavily gesendet (wenn `TAVILY_API_KEY` gesetzt ist) oder an DuckDuckGo.
- Wenn das Modell beschließt, eines Ihrer [Werkzeuge](#werkzeuge) zu verwenden, gehen die gewählten Argumente an den Server dieses Werkzeugs und die Antwort des Werkzeugs an den Modelldienst.
- Mit gesetztem `EMBEDDING_MODEL` werden die Nachricht, auf die er antwortet, Erinnerungen und Suchbeispiele an den Embeddings-Endpunkt gesendet (`EMBEDDING_BASE_URL` oder `LLM_BASE_URL`, wenn leer).

Bevor Sie ihn mit echten Menschen verbinden, teilen Sie ihnen mit, dass es sich um einen Bot handelt, und holen Sie ihre Einwilligung zur Verarbeitung ihrer Nachrichten ein. Lesen Sie den [Haftungsausschluss](DISCLAIMER.de.md).

### Dateien im personagent-Ordner

Die wichtigsten Dateien und Ordner im personagent-Ordner und was sie enthalten:

| Datei oder Ordner | Inhalt | Chattext oder Geheimnisse |
|---|---|---|
| `.env` | Einstellungen, mit dem Modellschlüssel und weiteren Schlüsseln im Klartext | Geheimnisse |
| `persona.txt`, `persona.card.json` | Die Persona und ihre optionale Karte | Nein |
| `mcp.json` | Die [Werkzeugserver](#werkzeuge), ihre Umgebungsvariablen und Anfrage-Header sowie die Einstellungen jedes Werkzeugs | Geheimnisse |
| `runtime/tools/` | Die Werkzeuge, die jeder Server zuletzt aufgelistet hat, und welche Server der laufende Dienst starten konnte | Nein |
| `persona.txt.bak` und seine datierten Kopien, `avatar.png` | Selbst geschriebene Personas, die eine fertige ersetzt hat, und Ihr eigenes Bild | Nein |
| `platforms/` | `direct.json` mit den Zugangsdaten der Plattformen, die personagent selbst verbindet, sowie das verwaltete AstrBot mit seinen Einstellungen | Geheimnisse |
| `runtime/memory.json`, `core_memory.json`, `episodes.json` | Fakten, Hauptnotiz, Ereignisse und Zusammenfassungen jedes Chats | Chatinhalte |
| `runtime/recent.json` | Die letzten Nachrichten jedes Chats, 72 Stunden lang | Chattext |
| `runtime/log/` | Das Protokoll jedes Chats: seine Nachrichten und die Antworten der Figur, für `MEMORY_LOG_DAYS` Tage, im Format JSON Lines, eine Datei je Chat, benannt nach einem Hash der Chat-ID | Chattext |
| `runtime/memory_trash.jsonl` | Entfernte Gedächtniseinträge, höchstens 30 Tage lang | Chatinhalte |
| `runtime/pending_reactions.json` | In den letzten 15 Minuten gesendete Antworten, die auf eine Reaktion warten, mit einigen Nachrichten davor | Chattext |
| `runtime/model_usage.json` | Modellanfragen und Tokens je Modell, Zweck und Tag, für 8 Tage | Nein |
| `runtime/memory_state.json`, `seen_msg_ids.json`, `connector_handles.json`, `persona_lineage.json`, `page.owner` | Laufzeitzustand: Zähler des Gedächtnisses, Hashes der Wörter vergessener Einträge, IDs letzter Nachrichten, Chats und Konten, Persona-Versionen | IDs, kein Chattext |
| `runtime/candidate_ledger.<lang>.jsonl` und die übrigen Lernaufzeichnungen | Was die Figur gelernt hat, mit den zugrunde liegenden Antworten und Reaktionen | Chattext |
| `runtime/desktop/browser-chat.json` | Der eigene Chat der Seite, seine letzten 50 Nachrichten | Chattext |
| `runtime/desktop/*.log` | Protokolle der Figur, der Plattformen und von AstrBot | Der Anfang jeder Antwort; können Teile von Nachrichten enthalten |
| `runtime/desktop/welcome.json` | Die Adresse der lokalen Seite mit ihrem Zugriffstoken | Geheimnis |
| `runtime/dashboard.token` | Das Token für die Aktivitäts-API | Geheimnis |
| `stickers/` | Aus Chats gesammelte Sticker | Bilder aus Chats |
| `data/` | Eigene Lorebook-, Beispiel- und Filterdateien und die `.bak`-Kopien, die das Wiederherstellen des integrierten Lorebooks hinterlässt | Nur was Sie dort ablegen |
| `backups/` | Sicherungen als ZIP | Beides |
| `runtime/trial/` | Die Übungsgruppe und `personagent chat` | Übungsnachrichten |
| `benchmark_runs/` | Berichte von `personagent eval` | Testfälle und Antworten |
| `runtime/desktop/children-<pid>.json`, `.personagent.instance.lock` und andere `*.lock`-Dateien | Welche Prozesse laufen, und Sperren, die verhindern, dass zwei gleichzeitig schreiben; eine Sperre kann nach dem Beenden zurückbleiben | Nein |

Eine Sicherung ist ein unverschlüsseltes ZIP, das den Schlüssel, das Gedächtnis, das Gelernte und die Plattform-Anmeldungen enthält. **Gedächtnis löschen** und **Alles zurücksetzen** in der Ansicht App speichern zuvor eine Sicherung in `backups/`; das Gelöschte bleibt daher in dieser Datei, bis Sie sie löschen. Auf dem Desktop oder unter Dokumente gespeicherte Sicherungen bleiben ebenfalls dort. Das Chatprotokoll (`runtime/log/`) gelangt nie in eine Sicherung. Die letzten Nachrichten der vergangenen 72 Stunden (`runtime/recent.json`) und die Antworten, die auf eine Reaktion warten, sind dagegen mit ihrem Text enthalten.

## Fehlerbehebung

**Beginnen Sie mit der Systemprüfung.** Öffnen Sie auf der lokalen Seite **App** und wählen Sie **Prüfung starten**. Die Ansicht nennt jeden Dienst, der nicht funktioniert, den Grund, warum die Figur oder eine Plattform nicht starten konnte, sowie Einstellungen, die Aufmerksamkeit erfordern; **Protokolle** zeigt jedes Protokoll an, ohne dass eine Datei geöffnet werden muss. Siehe [Die Ansicht App](#die-ansicht-app).

**Führen Sie im Terminal `personagent doctor` aus.** Der Befehl prüft die Konfiguration und nennt falsch geschriebene oder umbenannte Einstellungen. Anschließend testet er jeden Dienst, von dem personagent abhängt. Die Tests senden minimale Anfragen und können ein wenig Guthaben kosten. `--json` gibt dieselben Ergebnisse als JSON aus. `--fix` benennt in 1.0 entfernte Einstellungen um und speichert die alte Datei als `.env.bak`.

**Eine Plattform verbindet sich nicht.** Wenn die Plattform die Zugangsdaten ablehnt, nennen die Seite und im Terminal `personagent connect <platform>` den Grund. Prüfen Sie sie in der Konsole der Plattform, und stellen Sie bei Discord sicher, dass Message Content Intent aktiviert ist. Sie können einen neuen QR-Code anfordern, wenn er abläuft, und einen fehlgeschlagenen AstrBot-Download wiederholen. Eine Plattform, die etwa zwei Minuten lang nicht erreichbar ist, wird mit dem Grund als **Erneuter Versuch** angezeigt und verbindet sich danach selbstständig wieder; in Festlandchina benötigen Telegram und Discord einen HTTP-Proxy, der in den Systemeinstellungen oder in `HTTPS_PROXY` eingerichtet wird, gefolgt von einem Neustart. Eine Plattform, die die Anfragen des Bots weiterhin ablehnt, wird auf dieselbe Weise benannt. Unter jeder verbundenen Plattform gibt die Seite an, wem die Figur dort antwortet, mit einem Link zu den Antworteinstellungen, die dies einschränken. **Plattformverbindungen** in der Ansicht **App** zeigt den Zustand jeder Plattform, die personagent selbst verbindet. Die Protokolle aller Prozesse, die die Seite oder `personagent up` gestartet hat, liegen in `runtime/desktop/` im personagent-Ordner; die Ansicht **App** zeigt sie unter **Protokolle** an.

**Er läuft, antwortet aber nie.** Die drei häufigsten Ursachen sind:

1. Der Agent ist deaktiviert. Das Banner von `personagent run` zeigt dann `OFF` und nennt die Ursache, meist ein fehlender `LLM_API_KEY`. Setzen Sie den Schlüssel auf der lokalen Seite oder führen Sie `personagent init` aus.
2. Es kommt nichts an. Öffnen Sie auf dem Computer mit der lokalen Seite [Aktivität](#aktivität) und suchen Sie den Chat. Auf einem Server erwähnen Sie den Bot beim Namen und prüfen das Protokoll des Dienstes: Es hält jede Antwort und jeden abgelehnten Chat fest. Ist keine Nachricht angekommen, leitet der Konnektor sie nicht weiter oder erreicht personagent nicht. Bei QQ prüfen Sie in QQ selbst, welche Gruppennachrichten der Bot empfängt. Bei einem AstrBot, das Sie betreiben, leitet das Plugin nur die dort aufgeführten `groups` und `dm_users` weiter, und für NapCat darf `aiocqhttp` nicht in seinen `excluded_platforms` stehen. Prüfen Sie außerdem die `personagent_url` des Plugins und ob `CONNECTOR_TOKEN` auf beiden Seiten übereinstimmt.
3. Er wurde nicht angesprochen. Sprechen Sie ihn mit seinem Namen an (`PERSONA_NAME`, als ganzes Wort verglichen). In einer Gruppe erwägt er eine Beteiligung erst nach `CHAT_TRIGGER_COUNT` Nachrichten (30), und nur, wenn der Filter feststellt, dass sich ein Mensch beteiligen würde.

Der Bereitstellungsleitfaden enthält [die vollständige Checkliste](deploy.de.md#wenn-der-bot-verstummt).

**Läuft er?** `curl http://127.0.0.1:8080/health` antwortet, ohne ein Modell aufzurufen. `/health/details` testet auch die Dienste und erfordert einen `X-Personagent-Token`-Header, sobald ein Token konfiguriert ist.

**Er startet nicht.** `personagent run` beendet sich mit einer Meldung, die den Grund nennt. Die üblichen Gründe sind ein bereits belegter Port, ein anderes personagent aus demselben personagent-Ordner, eine Netzwerkadresse ohne `CONNECTOR_TOKEN`, eine in 1.0 entfernte Einstellung, die noch gesetzt ist, oder eine beschädigte Gedächtnisdatei; in diesem Fall nennt die Meldung die datierte Kopie, die an ihre Stelle zu setzen ist. Entfernte Einstellungen werden je Zeile als `OLD -> NEW` gelistet, und `personagent doctor --fix` benennt sie um, ebenso **Einstellungen umbenennen** in der Ansicht **App**. Schlägt der Start der von der Seite gestarteten Figur fehl, nennt die Ansicht **App** den fehlgeschlagenen Teil und zeigt dessen letzte Protokollzeile an. Die Seite und `personagent up` wählen einen freien Port, wenn 8080 belegt ist.

**Eine Einstellung wirkt nicht.** Starten Sie den Prozess neu, der sie liest, prüfen Sie die Schreibweise und speichern Sie `.env` als UTF-8 ohne BOM. Umgebungsvariablen der Shell haben Vorrang vor `.env`. Boolesche Werte sind `true` oder `false`. `PERSONA_TZ_OFFSET_HOURS` legt die Zeitzone der Figur fest: Die Nachtphase und die Daten dessen, was sie sich merkt, richten sich danach. Wenn es leer ist (Standard), nutzt personagent UTC+8 bei `AGENT_LANG=zh` oder `zh-TW` und sonst die Zeitzone dieses Rechners. Geben Sie eine Zahl an, um einen anderen Versatz festzulegen.

## personagent entfernen

1. Ist die Figur mit einem Programmierassistenten verbunden, entfernen Sie sie zuerst unter **Plattformen verbinden** → **Programmierassistenten** oder mit `personagent connect claude-code --remove` (ebenso `codex` und `dsh`).
2. Klicken Sie unter Windows in der Ansicht App unter **Symbol auf dem Desktop und im Startmenü** auf **Symbol entfernen** und schalten Sie **personagent nach der Anmeldung bei Windows starten** aus.
3. Klicken Sie auf der Seite auf **Beenden**.
4. Deinstallieren Sie das Paket mit `python -m pip uninstall personagent` oder, falls Sie es mit uv installiert haben, mit `uv tool uninstall personagent`. Eine aus dem Quellcode-ZIP entpackte Kopie entfernen Sie, indem Sie ihren Ordner löschen.
5. Löschen Sie den personagent-Ordner: standardmäßig den Ordner `personagent` in Ihrem Benutzerordner oder den mit `--home` angegebenen. Er enthält den Schlüssel, das Gedächtnis, die Plattform-Anmeldungen und `backups/`.
6. Löschen Sie Sicherungen, die Sie auf dem Desktop oder unter Dokumente gespeichert haben.
7. Widerrufen Sie den API-Schlüssel auf der Schlüsselseite des Modelldienstes und entfernen Sie den Bot auf jeder Plattform aus seinen Gruppen.

## Upgrade von 0.x

1.0 hat die meisten Einstellungen umbenannt, und personagent startet nicht, solange ein alter Name gesetzt ist. Es listet jeden Namen als `OLD -> NEW` auf, und `personagent doctor --fix` benennt sie in `.env` um. [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04) im Änderungsprotokoll listet alle Schritte. Das Gedächtnis und was die Figur gelernt hat bleiben erhalten.

## Status und weitere Dokumente

personagent 1.4.4 ist auf PyPI. Die CI führt die Tests unter Linux mit Python 3.10–3.14 und unter Windows mit Python 3.12 aus. Weitere CI-Jobs installieren das Paket, steuern den Befehl und die lokale Seite und öffnen das App-Fenster unter Linux, macOS und Windows.

Der direkte OneBot-Weg (`/v1/onebot`) ist veraltet, bleibt aber während der gesamten 1.x. Die Skripte in `tools/` sind dafür gedacht, aus einem Klon ausgeführt zu werden, und [tools.md](tools.de.md) beschreibt sie.

- [Erste Schritte](start.de.md) · [Bereitstellungsleitfaden](deploy.de.md) · [Schritt-für-Schritt-Anleitung auf Chinesisch (QQ per Scan und Fehlerbehebung)](deploy.zh-CN.md)
- Konnektoren: [AstrBot-Plugin](../integrations/astrbot/astrbot_plugin_personagent/README.de.md) · [Satori](../integrations/satori/README.de.md) · [Matrix](../integrations/matrix/README.de.md) · [Protokoll](connectors.de.md)
- [Alle Einstellungen](../.env.example) · [Änderungsprotokoll](../CHANGELOG.md) · [Mitwirken](../.github/CONTRIBUTING.md) · [Sicherheitsrichtlinie](../.github/SECURITY.md)
