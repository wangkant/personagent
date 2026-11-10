# personagent-Benutzerhandbuch

[English](guide.md) · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · [日本語](guide.ja.md) · [한국어](guide.ko.md) · [Español](guide.es.md) · [Français](guide.fr.md) · Deutsch · [Português (Brasil)](guide.pt-BR.md) · [Русский](guide.ru.md)

Dieses Handbuch erklärt, wie Sie personagent einrichten, in Ihre Chats einbinden, ihm etwas beibringen und es betreuen. Das [README](readme/README.de.md) ist die Kurzfassung, und [Erste Schritte](start.de.md) erläutert die lokale Seite Ansicht für Ansicht.

1. [Installation und der Home-Ordner](#installation-und-der-home-ordner)
2. [Die lokale Seite](#die-lokale-seite): [Erweiterte Einstellungen](#erweiterte-einstellungen) · [Die Ansicht App](#die-ansicht-app)
3. [Erst ansehen: die Demo](#erst-ansehen-die-demo)
4. [Terminal-Befehle](#terminal-befehle): [Einrichtung](#im-terminal-einrichten) · [Plattform verbinden](#eine-plattform-im-terminal-verbinden) · [Chat](#im-terminal-chatten) · [den Dienst ausführen](#den-dienst-ausführen)
5. [Die eigene Figur gestalten](#die-eigene-figur-gestalten)
6. [In einen Chat bringen](#in-einen-chat-bringen): [Plattformen, die personagent selbst verbindet](#plattformen-die-personagent-selbst-verbindet) · [Andere Plattformen](#andere-plattformen-über-das-verwaltete-astrbot) · [Brücken, die Sie selbst betreiben](#brücken-die-sie-selbst-betreiben) · [Zuerst sprechen](#zuerst-sprechen)
7. [Programmierassistenten](#programmierassistenten)
8. [Der Figur etwas beibringen](#der-figur-etwas-beibringen)
9. [Aktivität](#aktivität)
10. [Messen](#messen)
11. [Wie es funktioniert](#wie-es-funktioniert)
12. [Datenschutz und Einwilligung](#datenschutz-und-einwilligung)
13. [Fehlerbehebung](#fehlerbehebung)
14. [Upgrade von 0.x](#upgrade-von-0x)
15. [Status und weitere Dokumente](#status-und-weitere-dokumente)

## Installation und der Home-Ordner

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

Der **Home-Ordner** enthält die Einstellungen (`.env`), die Figur (`persona.txt`), was sie lernt (`runtime/`) und die Chat-Plattformen (`platforms/`). `platforms/` enthält das verwaltete AstrBot und `direct.json`, das die Zugangsdaten der Plattformen speichert, die personagent selbst verbindet. personagent verwendet den ersten der folgenden Ordner:

1. den Ordner aus `--home DIR` oder `AGENT_HOME`. `--home` kann vor oder nach dem Befehl stehen, wie bei `personagent chat --home D:\bot`.
2. den Klon, wenn Sie personagent aus einem Klon starten.
3. den aktuellen Ordner, wenn er sowohl `.env` als auch `persona.txt` enthält.
4. `~/personagent`, das bei der ersten Einrichtung angelegt wird.

Um mehrere Figuren aus einer Installation zu betreiben, geben Sie jedem einen eigenen Home-Ordner.

Dieses Handbuch gibt Befehle als `personagent ...` an. Wenn Sie personagent nicht installiert haben, stellen Sie `uvx` voran. In einem Klon bewirkt `.venv/bin/python -m persona_agent ...` dasselbe (unter Windows `.venv\Scripts\python.exe -m persona_agent ...`).

## Die lokale Seite

`personagent` (oder `personagent start`) stellt eine Seite bereit, die nur von diesem Computer erreichbar ist. Unter Windows öffnet sie sich in einem eigenen Fenster. Unter macOS und Linux öffnet sie sich im Browser oder ebenfalls in einem Fenster, sobald `pip install "personagent[app]"` [pywebview](https://pywebview.flowrl.com/) hinzugefügt hat, unter Linux zusammen mit Qt. Die Seite hat sechs Ansichten, die in der Seitenleiste in dieser Reihenfolge stehen:

- **Chat** ist ein Einzelgespräch mit der Figur auf der Seite. Derselbe Agent, der Ihre Chat-Plattformen bedient, antwortet hier. In diesem Chat sind Sie der Administrator. Sticker und Bilder, die die Figur sendet, erscheinen im Chat; an der Stelle eines Bildes, das nicht mehr gespeichert ist, steht ein kurzer Hinweis. Nachrichten, die die Figur nach ihrer Antwort sendet, etwa die Antwort auf einen Gedächtnis-Befehl, der während ihrer Antwort gesendet wurde, eine kurze Nachricht bei einem Fehler des Modells oder eine Nachricht, die sie von sich aus beginnt, erscheinen innerhalb weniger Sekunden, solange die Ansicht **Chat** geöffnet ist. Beides bleibt im Verlauf des Chats erhalten. **Gedächtnisbefehle** unterhalb des Eingabefelds listet die [Gedächtnis-Befehle](#gedächtnis-befehle) auf; wenn Sie einen davon auswählen, wird er in das Eingabefeld eingefügt. **Diesen Chat vergessen** löscht, was die Figur sich in diesem Chat notiert hat, und beginnt einen neuen Chat. Dafür sind die Daten hinter [Aktivität](#aktivität) erforderlich.
- **Aktivität** zeigt die Chats, in denen die Figur aktiv ist, was sie zuletzt gesagt hat, was sie gelernt hat und was auf Ihre Entscheidung wartet. Siehe [Aktivität](#aktivität).
- **Plattformen verbinden** bringt die Figur in QQ, WeChat, Telegram, Discord und weitere Plattformen. Siehe [In einen Chat bringen](#in-einen-chat-bringen). Ganz unten verbindet **Programmierassistenten** die Figur mit den [Programmierassistenten](#programmierassistenten) auf diesem Computer.
- **Figur & Einstellungen** ist der Ort, an dem Sie einen Modelldienst auswählen (OpenRouter, DeepSeek, SiliconFlow, Alibaba Bailian, Zhipu GLM, Moonshot, Volcengine Ark, OpenAI, Google Gemini, Ollama oder jeden anderen OpenAI-kompatiblen Dienst), den API-Schlüssel einfügen und einen Namen und eine fertige Persönlichkeit wählen. **Prüfen & Chat starten** testet den Schlüssel mit einer kleinen Anfrage und speichert ihn nur, wenn sie gelingt. Nach der Einrichtung zeigt das Feld **Persona** `persona.txt`. **Persona speichern** startet den Agenten mit dem neuen Text neu und behält, was er gelernt hat. **Weitere Funktionen** schaltet die Websuche über Tavily (DuckDuckGo ist die kostenlose Voreinstellung), die Bilderkennung und eigene Gesprächsanstöße auf den von Ihnen gewählten Plattformen ein. Darauf folgen die [Erweiterten Einstellungen](#erweiterte-einstellungen).
- **Übung** spielt die vorgefertigte Demo ab und stellt einen Übungsgruppenchat bereit. Siehe [Erst ansehen: die Demo](#erst-ansehen-die-demo).
- **App** prüft die Dienste, auf die die Figur angewiesen ist, und bündelt die Protokolle, die Ausführung im Hintergrund, die Updates und Ihre Daten. Siehe [Die Ansicht App](#die-ansicht-app).

**Übung** und **App** lassen sich bereits öffnen, bevor ein Modell eingerichtet ist. Solange Sie keine Plattform verbunden haben, zeigt die Ansicht **Chat** eine kurze Leiste **Erste Schritte**.

Ein erneuter Aufruf von `personagent` holt die bereits geöffnete Seite wieder in den Vordergrund. `--browser` öffnet die Seite im Browser statt in einem Fenster, und `--no-browser` gibt den Link aus und öffnet nichts. Unter Windows legt `personagent shortcut` ein Symbol auf den Desktop und ins Startmenü, das das Fenster ohne Terminal dahinter öffnet, und `personagent shortcut --remove` entfernt es wieder. Die Ansicht **App** bietet dieselbe Funktion.

Wenn auf PyPI eine neuere Version von personagent verfügbar ist, zeigt die Ansicht **Chat** einen Hinweis mit dem Befehl, der Ihre Installation aktualisiert, ob sie aus pip, uvx, uv tool, pipx oder einem Git-Klon stammt. Bei einem entpackten Quellcode-ZIP verweist der Hinweis stattdessen auf die Release-Seite. Das Terminal gibt denselben Befehl aus. Das Schließen des Hinweises blendet ihn für diese Version aus, und **N verfügbar** unter der Versionsnummer zeigt ihn wieder an. `personagent up` und `personagent doctor` melden ebenfalls eine neue Version. Die Seite und `up` fragen pypi.org höchstens einmal täglich im Hintergrund ab. `doctor` fragt sofort ab, wenn die letzte Antwort älter als ein Tag ist. Setzen Sie `UPDATE_CHECK_ENABLED=false`, um die Prüfung zu deaktivieren. Die Ansicht **App** kann das Update auch selbst installieren; siehe [Version und Updates](#version-und-updates).

Die Seite startet den Agenten und die verbundenen Plattformen im Hintergrund; lassen Sie ihr Fenster daher geöffnet, während Sie sie verwenden. Alles, was sie gestartet hat, wird mit ihr beendet, unabhängig davon, ob Sie auf **Beenden** klicken, Strg+C drücken oder das Fenster schließen. Solange eine Plattform verbunden ist, erfolgt vor dem Schließen des Fensters eine Rückfrage. Unter Windows lässt sich stattdessen festlegen, dass personagent nach dem Schließen des Fensters weiterläuft; siehe [Im Hintergrund ausführen](#im-hintergrund-ausführen). Wenn ein früherer Lauf abgestürzt ist und Prozesse hinterlassen hat, beendet der nächste Start sie zuerst.

### Erweiterte Einstellungen

Sobald ein Modell eingerichtet ist, endet **Figur & Einstellungen** mit **Erweiterte Einstellungen**. Dieser Bereich enthält in fünf Abschnitten Einstellungen, die bisher nur in `.env` verfügbar waren. Alle sind optional und haben einen Standardwert; ein leeres Feld verwendet den Standardwert.

| Abschnitt | Einstellungen |
|---|---|
| **Administrator und Zugriff** | Wie die Figur Sie nennt und in welcher Beziehung Sie zu ihr stehen (`ADMIN_NAME`, `ADMIN_RELATIONSHIP`); **Ihre Konten** (`ADMIN_IDS`); **Nur in diesen Gruppen antworten** (`ACCESS_GROUPS`); **Weitere Personen mit Erlaubnis für Direktnachrichten** (`ACCESS_DM_USERS`). **Aus letzten Chats auswählen** listet die Personen und Gruppen aus Aktivität auf, sodass Sie deren Kennungen hinzufügen können, ohne sie einzutippen. |
| **Sprechen und Antwortstil** | **Zeitzone** (`PERSONA_TZ_OFFSET_HOURS`); **Nachrichten vor einer Beteiligung** (`CHAT_TRIGGER_COUNT`); **Häufigkeit eigener Gesprächsanstöße**, womit die sieben `PROACTIVE_*`-Zeitwerte auf einmal festgelegt werden; **Antwortstil**: Emoji, drei Zeichensätze und die maximale Antwortlänge, gespeichert in `persona.card.json`. |
| **Modelle** | Ein Ersatzmodell mit eigener Dienstadresse und eigenem Schlüssel (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`), das Modell für schnelle Entscheidungen (`LLM_JUDGE_MODEL`) und das Modell für Direktnachrichten (`LLM_DM_MODEL`). Das Ersatzmodell wird vor dem Speichern getestet. |
| **Lernen** | `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED` und `PROMOTE_MIN_SPEAKERS` (1 oder 2). **Lernen neu beginnen** schreibt eine neue `PERSONA_VERSION`, sodass das bisher Gelernte nicht mehr verwendet wird. Gelöscht wird nichts. |
| **Weitere Einstellungen** | `AGENT_ENABLED`, `DASHBOARD_ENABLED`, `UPDATE_CHECK_ENABLED`, die sieben `PROACTIVE_*`-Zeitwerte, `CHAT_CONTEXT_MESSAGES`, `CHAT_FOLLOWUP_WINDOW_S`, die Grenzwerte für `REACT_*` und `PROMOTE_*`, `REACT_MODEL` und `PERSONA_VERSION`. |

**Speichern** schreibt nur die geänderten Einstellungen und lässt den Rest von `.env` unverändert. Anschließend wird die Figur neu gestartet, außer wenn `UPDATE_CHECK_ENABLED` die einzige Änderung ist. Vor dem Abschalten der Antworten (`AGENT_ENABLED`) erfolgt eine Rückfrage. Dasselbe gilt für das Umbenennen der Figur unter **Name der Figur**, denn ein neuer Name beginnt eine neue Figur.

### Die Ansicht App

**App** trägt einen roten Punkt, wenn etwas Ihre Aufmerksamkeit erfordert: Ein Dienst konnte nicht starten, eine Einstellung hat einen alten Namen oder einen Fehler, eine Plattformverbindung ist fehlgeschlagen, oder die letzte Prüfung ist fehlgeschlagen.

**Systemprüfung.** **Prüfung starten** testet jeden Dienst, auf den die Figur angewiesen ist: das Chatmodell für Antworten in Gruppen und Direktnachrichten, die Bilderkennung, das Modell für die Selbstbewertung, die Gedächtnissuche, die Websuche, die QQ-Brücke (NapCat) und das Lernprotokoll. Jeder Dienst erhält eine Zeile mit der Kennzeichnung **Funktioniert**, **Funktioniert nicht** oder **Nicht eingerichtet**, und eine Gesamtbewertung über den Zeilen nennt, was zu beheben ist. Läuft die Figur, erfolgt die Prüfung über sie. Andernfalls führt ein separater Testlauf dieselben Prüfungen aus wie `personagent doctor`. Eine Prüfung sendet einige kurze Anfragen und verbraucht einen kleinen Teil des Kontingents Ihres Modelldienstes. Ein Ergebnis, das weniger als eine Minute alt ist, wird wiederverwendet, solange sich die Einstellungen nicht geändert haben. Derselbe Teil der Ansicht zeigt außerdem:

- warum die Figur, AstrBot oder die Plattformverbindung nicht starten konnte, mit der betreffenden Protokollzeile, **Protokoll anzeigen** und **Neu starten**;
- **Einstellungen mit alten Namen**: in 1.0 umbenannte Einstellungen. **Einstellungen umbenennen** bewirkt dasselbe wie `personagent doctor --fix`. Vorher erfolgt eine Rückfrage; die bisherige Datei wird als `.env.bak` aufbewahrt, und die Figur wird erneut gestartet, falls sie den Start verweigert hatte;
- **Plattformverbindungen**: den Zustand jeder Plattform, die personagent selbst verbindet, und bei einem Fehlschlag den Grund;
- **Zu prüfende Einstellungen**: in `.env` gefundene Probleme, etwa ein fehlender Modellschlüssel, eine Einstellung, die personagent nicht liest, ein leerer Wert oder eine Byte-Order-Mark;
- **Protokolle**: die letzten Zeilen jedes Protokolls in `runtime/desktop/` (Figur, AstrBot, Plattformverbindungen, Downloads und Installation, App, Übung und letztes Update). Erkennbare Schlüssel und Tokens werden ausgeblendet, Chatinhalte können jedoch erscheinen. **Weitere Zeilen anzeigen** zeigt bis zu 200 Zeilen an, und **Protokollordner öffnen** öffnet den Ordner.

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
- **Jetzt sichern** speichert eine einzelne ZIP-Datei auf dem Desktop, unter Dokumente oder im Ordner `backups` im Home-Ordner. Sie enthält die Einstellungen mit Ihren API-Schlüsseln, die Persona, das Gedächtnis und die gelernten Inhalte, die Lorebook-Dateien, die Sticker und die Plattform-Anmeldungen. Protokolle und heruntergeladene Komponenten sind nicht enthalten. Bewahren Sie die Datei vertraulich auf.
- **Aus Sicherung wiederherstellen** listet die Sicherungen an diesen drei Orten auf. **Wiederherstellen** fragt zunächst nach, pausiert die Figur, sichert die aktuellen Daten, ersetzt sie durch die Daten der Sicherung und leert den Chat dieser Seite.
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
    jetzt in Gebrauch: 2 übereinstimmende Reaktionen, davon stark: 1, gleicher Chat
```

Die Szene sendet außerdem dieselbe Nachricht vor und nach der Lektion: Jemandes Laptop ist mitten in der Demo ausgefallen. Vor der Korrektur bietet Nova eine Lösung an. Danach zeigt Nova Mitgefühl. Die Demo bleibt auch mit gesetztem Schlüssel vorgegeben, sodass jeder Lauf identisch und kostenlos ist. `personagent demo --online` spielt sie stattdessen mit Ihrem eigenen Modell ab; dies verbraucht Token und variiert von Lauf zu Lauf.

Die Ansicht **Übung** der lokalen Seite spielt dieselben drei Szenen ab. Wählen Sie unter **Demo** eine Szene und dann **Abspielen**. Jeder Schritt zeigt, was die Teilnehmenden und was die Figur gesagt haben, warum sie geschwiegen oder sich beteiligt hat, wie die Reaktionen beurteilt wurden, und die Lern-Checkliste.

**Übungsgruppe** in derselben Ansicht ist die Seitenfassung von [`personagent chat`](#im-terminal-chatten) und setzt ein eingerichtetes Modell voraus. **Schreiben als** legt fest, wer die nächste Nachricht sendet: Sie als Administrator oder eines von drei fiktiven Mitgliedern. **Grund anzeigen** an einer Zeile zeigt, warum die Figur geantwortet oder geschwiegen hat, was sie gelernt hat und welches früher Gelernte sie verwendet hat. **Antworten** zitiert eine Zeile der Figur, sodass die nächste Nachricht als Reaktion darauf zählt. **Gelerntes anzeigen** listet auf, was sie in dieser Gruppe gelernt hat. Die Übungsgruppe speichert ihren Zustand in `runtime/trial/`, demselben Ordner wie `personagent chat`, und wirkt sich nicht auf Ihre echten Chats aus. **Übungsgruppe zurücksetzen** löscht diesen Zustand.

## Terminal-Befehle

Alle Funktionen der Seite stehen auch im Terminal zur Verfügung, was sich für Server und Skripte eignet.

| Befehl | Funktion |
|---|---|
| `personagent start` | öffnet die lokale Seite (`--terminal` für ein Menü im Terminal) |
| `personagent init` | richtet einen Home-Ordner ein; `--terminal` stellt die Fragen im Terminal, `--no-input` übernimmt die Angaben aus Optionen |
| `personagent chat` | ein simulierter Gruppenchat im Terminal |
| `personagent demo` | die geskriptete Demo oben |
| `personagent run` | nur der Dienst, für Konnektoren, die Sie selbst betreiben |
| `personagent up` | der Dienst, die Plattformen, die personagent selbst verbindet, und das verwaltete AstrBot zusammen |
| `personagent connect <platform>` | verbindet eine der [Plattformen, die personagent selbst verbindet](#eine-plattform-im-terminal-verbinden) (`--remove` trennt sie); ohne Plattform listet der Befehl sie auf |
| `personagent connect astrbot` | verbindet ein AstrBot (`--install`, um ein verwaltetes herunterzuladen, `--start`, um es zu starten) |
| `personagent connect claude-code`, `personagent connect codex`, `personagent connect dsh` | bindet die Figur in einen [Programmierassistenten](#programmierassistenten) ein (`--react` für Bemerkungen am Ende eines Durchgangs bei den ersten beiden, `--remove` zum Rückgängigmachen) |
| `personagent mcp` | der MCP-Server, den ein Programmierassistent startet; Sie führen ihn nicht selbst aus |
| `personagent doctor` | prüft die Konfiguration und jeden Dienst, von dem er abhängt |
| `personagent learned` | prüft, befördert oder widerruft, was die Figur gelernt hat |
| `personagent eval` | misst Sprechen, Persona und Lernen |

Alle Befehle akzeptieren `--help`.

### Im Terminal einrichten

`personagent init --terminal` stellt dieselben Fragen wie die Seite, in der Sprache, die Sie zu Beginn wählen, und erklärt jeden Begriff in einer Zeile:

- **Der KI-Dienst.** Die Voreinstellungen entsprechen denen der Seite. Standard ist `openrouter/free` von OpenRouter, das jede Anfrage an eines seiner kostenlosen Modelle weiterleitet. Der Schlüssel ist kostenlos. Das Limit beträgt 20 Anfragen pro Minute und 50 pro Tag, oder 1000 pro Tag, sobald Sie mindestens 10 Credits erworben haben. Jeder Modellaufruf zählt, nicht nur die Antworten, und der Tag beginnt um Mitternacht UTC neu. Ist das Limit erreicht, teilt die Figur mit, dass sie gerade nicht antworten kann, und `runtime/desktop/agent.log` enthält den Grund von OpenRouter. Das Modell wechselt von Anfrage zu Anfrage, sodass die Ausdrucksweise der Figur stärker schwankt als mit einem fest gewählten Modell, und manche kostenlosen Anbieter speichern, was sie erhalten. Für eine beständigere Figur wählen Sie ein kostenpflichtiges Modell mit demselben Schlüssel. Wenn OpenRouter für Sie schwer erreichbar ist, ist `glm-4.7-flash` von Zhipu ebenfalls kostenlos. Für Ollama geben Sie ein Modell an, das Sie bereits heruntergeladen haben. Ollama benötigt keinen Schlüssel.
- **Der Schlüssel.** Die Eingabe ist standardmäßig verborgen. Sie können sie anzeigen lassen; bei einer Neukonfiguration wird dann auch der gespeicherte Schlüssel angezeigt. Der Assistent testet den Schlüssel mit einer kleinen Anfrage. Schlägt sie fehl, zeigt er die aufgerufene Adresse, den HTTP-Status und eine wahrscheinliche Abhilfe.
- **Die Figur.** Ein Name und eine von sieben fertigen Figuren (trockener Freund, aufmerksamer Zuhörer, Gamer, Bücherwurm sowie drei, die die Community bereits zeichnet: das DeepSeek-Walmädchen, das GPT-Drachenmädchen und die Claude-Dame) oder eine schlichte Figur, die Sie selbst beschreiben. Wählen Sie eine der letzten drei, ohne einen Namen festzulegen, trägt die Figur deren Namen. Die lokale Seite zeigt ihr animiertes Porträt.
- **Chatplattformen.** Optional; Sie können diesen Schritt beim ersten Mal überspringen. Die Einrichtung nennt die zehn Plattformen, die personagent selbst verbindet; diese verbinden Sie anschließend mit [`personagent connect <platform>`](#eine-plattform-im-terminal-verbinden). Für die übrigen Plattformen kann sie AstrBot verbinden und es zuvor herunterladen und installieren. Siehe [Brücken, die Sie selbst betreiben](#brücken-die-sie-selbst-betreiben).

Um ohne Rückfragen einzurichten, etwa in einem Skript, führen Sie `personagent init --no-input` mit `--provider`, `--model`, `--key-env VAR`, `--name`, `--lang` und `--persona` aus. In einem neuen Home-Ordner erfordert ein Schlüssel aus `--key-env` oder aus dem `LLM_API_KEY` der Shell `--provider` oder `--base-url`, um anzugeben, zu welchem Dienst er gehört. `--provider other` erfordert außerdem `--base-url`. `personagent init --help` listet alle Optionen auf. Läuft `personagent init` ohne Terminal und ohne eine dieser Optionen, überspringt es die Fragen, weist darauf hin und beendet sich mit Code 2.

### Eine Plattform im Terminal verbinden

`personagent connect <platform>` verbindet ohne die Seite eine der [Plattformen, die personagent selbst verbindet](#plattformen-die-personagent-selbst-verbindet). Als Plattform geben Sie `qq`, `wechat`, `telegram`, `discord`, `matrix`, `twitch`, `irc`, `zulip`, `vk` oder `stoat` an. Der Befehl zeigt dieselben Schritte wie **Plattformen verbinden**, fragt jeden Wert ab, prüft die Werte bei der Plattform und speichert sie in derselben Form wie die Seite, die die Plattform anschließend als verbunden anzeigt. Lehnt die Plattform die Werte ab, nennt der Befehl den Grund und speichert nichts. `personagent connect` ohne Plattform listet die zehn Plattformen auf und gibt für jede an, ob sie verbunden ist.

- QQ und WeChat geben im Terminal einen QR-Code aus, den Sie mit Ihrem Smartphone scannen. Für QQ können Sie stattdessen AppID und AppSecret eines Bots eingeben, den Sie erstellt haben. Lässt sich der Code in Ihrem Terminal nicht scannen, verbinden Sie die Plattform im personagent-Fenster; der Befehl gibt aus, wie Sie es öffnen.
- Twitch gibt einen Link und einen Code aus. Öffnen Sie den Link in einem Browser, der beim Twitch-Konto der Figur angemeldet ist, prüfen Sie, ob die Seite denselben Code anzeigt, und bestätigen Sie die Anmeldung. Bis dahin wartet der Befehl.
- Jeder Wert kann auch als Option angegeben werden, etwa `--telegram-token` oder `--irc-server`; `personagent connect --help` listet alle Optionen auf. Ein als Option angegebener Wert kann im Verlauf der Shell verbleiben. Mit `--no-input` stellt der Befehl keine Fragen; fehlt ein erforderlicher Wert, nennt er die Option und beendet sich mit Code 2.
- `--remove` trennt die Plattform und löscht ihre gespeicherten Werte.

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
| `/quit` | beenden |

`/as`- und `/admin`-Zeilen folgen ebenfalls den Gruppenregeln; nennen Sie also den Namen, um eine Antwort zu erhalten. Eine Zeile unter vier Zeichen, die die Figur nicht nennt, zählt nicht für die Beteiligung. Die [Gedächtnis-Befehle](#gedächtnis-befehle) funktionieren hier auch.

| Option | Funktion |
|---|---|
| `--name Alex` | legt Ihren Namen fest |
| `--admin` | ordnet jede Zeile dem Administrator zu |
| `--dm` | macht daraus ein Einzelgespräch |
| `--lang <code>` | überschreibt `AGENT_LANG`, wie `--lang ja` |
| `--trigger N` | Nachrichten, bevor die Figur eine Beteiligung erwägt (Standard 4) |

Der Testlauf führt die tatsächliche Entscheidung über Sprechen oder Schweigen aus, dazu die Ausgabeprüfungen, die Gedächtnis-Befehle und das Lernen. Er erwägt eine Beteiligung nach 4 Nachrichten, wo der laufende Bot auf 30 wartet. Was er lernt, bleibt in `runtime/trial/` im Home-Ordner, getrennt vom laufenden Bot. `personagent learned` zeigt es nicht, und `/reset` löscht es. Der Testlauf überspringt die Zulassungslisten und die echte Zustellung. Außerdem schaltet er die Selbstbewertung, das Sehen, die Nachfrage und die Nachrichten aus, die die Figur von sich aus beginnen würde. Wenn ein Modellaufruf fehlschlägt, gibt er eine Zeile aus, die angibt, was zu prüfen ist:

```text
Alex> Nova, bist du da?
  [Fehler: der Modellanbieter hat den Schlüssel oder das Konto abgelehnt (HTTP 401); prüfen Sie LLM_API_KEY und führen Sie dann `personagent doctor` aus]
```

### Den Dienst ausführen

`personagent run` startet nur den Dienst, mit dem die Konnektoren sprechen, unter `http://127.0.0.1:8080`. Beim Start gibt er die Version, die Adresse und den Home-Ordner aus sowie, ob der Agent aktiv ist. `--host` und `--port` überschreiben `SERVER_HOST` und `SERVER_PORT`. Verwenden Sie diesen Befehl, wenn Sie den Konnektor selbst betreiben.

`personagent up` startet den Dienst mit allen Plattformen, die über die Seite, mit `personagent connect <platform>` oder mit `connect astrbot --install` verbunden wurden. Es öffnet keinen Browser. Strg+C beendet alles, und jeder Prozess schreibt sein Log nach `runtime/desktop/` im Home-Ordner.

## Die eigene Figur gestalten

`persona.txt` im Home-Ordner legt die Figur fest. Bearbeiten Sie die Datei im Feld **Persona** der Seite oder in einem beliebigen Editor und starten Sie anschließend neu. Beschreiben Sie, wer die Figur ist, wie sie gewöhnlich spricht und wie sie sich in den Situationen verhält, die Ihnen wichtig sind. Konkrete Gewohnheiten wirken besser als die Bitte an das Modell, „natürlich zu klingen“:

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG` ist eines von `en`, `zh`, `zh-TW`, `ja`, `ko`, `es`, `fr`, `de`, `pt-BR` und `ru`. Es legt die Startpersona, die Einrichtung im Terminal, den Testlauf und die Demo, `--help` und `doctor`, die Gedächtnis-Befehle und die festen Antworten fest. Die mitgelieferten Beispiele, Filter und Prüfungen sind für `zh` und `zh-TW` chinesisch und sonst englisch. Ihre Persona wird nicht übersetzt. [.env.example](../.env.example) beschreibt jede Einstellung.

Das Sprachmenü oben rechts auf der lokalen Seite bietet English, 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil) und Русский. Es ändert die Sprache der Seite, und der Browser speichert die Auswahl. Wenn Sie die Einstellungen speichern, wird die Sprache der Seite zu `AGENT_LANG`. Die Figur antwortet in der Sprache, die im Chat verwendet wird. Die Prompts der Figur sind englisch und chinesisch. Die [Gedächtnis-Befehle](#gedächtnis-befehle) und die wenigen festen Antworten, die nicht durchs Modell gehen, funktionieren in allen zehn Sprachen.

Um eine mitgelieferte Datei zu ersetzen, legen Sie eine Datei gleichen Namens in `data/` im Home-Ordner ab. Dateien, die Sie nicht ersetzen, kommen aus der mit personagent gelieferten Kopie.

| Datei | Inhalt |
|---|---|
| `data/examples.<lang>.jsonl` | Beispielgespräche, die das Modell nachahmen kann |
| `data/feedback.<lang>.jsonl` | Antworten, gepaart mit besseren Fassungen |
| `data/lorebook.<lang>.json` | Hintergrundnotizen, die hinzukommen, wenn ein Schlüsselwort fällt |
| `data/output_filter.<lang>.json` | Ersetzungs- und Ablehnungsregeln für laufende Antworten |
| `persona.card.json` | Optionale Einstellungen für Emoji, Zeichensatz und Länge, wie `{ "reply_style": { "emoji": true, "max_chars": 320 } }` |

Damit die Figur Bilder erkennt, setzen Sie `VISION_MODEL`, `VISION_API_KEY` und `VISION_BASE_URL`, oder aktivieren Sie die Bilderkennung unter **Weitere Funktionen**.

## In einen Chat bringen

Öffnen Sie **Plattformen verbinden** auf der lokalen Seite und wählen Sie eine Plattform. Die Seite fragt nur nach den Werten, die Sie aus der Konsole der Plattform kopieren. Sie prüft sie bei der Plattform, startet die Verbindung und wartet einige Sekunden, um zu bestätigen, dass die Plattform sie angenommen hat. Lehnt die Plattform ab, weist die Seite darauf hin und speichert nichts. Verbundene Plattformen werden oben aufgeführt; dort können Sie eine neu konfigurieren oder trennen. Sie werden erneut gestartet, sobald die Seite oder `personagent up` startet. Auf einem Computer ohne Bildschirm verbindet `personagent connect <platform>` die Plattformen, die personagent selbst verbindet, im Terminal; siehe [Eine Plattform im Terminal verbinden](#eine-plattform-im-terminal-verbinden).

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

Ein Konnektor meldet sich bei der Plattform an, leitet jede Nachricht an personagent weiter und stellt die Antwort zu. Es gibt drei Arten.

### Plattformen, die personagent selbst verbindet

personagent verbindet diese zehn Plattformen selbst, in einem einzigen Hintergrundprozess. Sie benötigen weder AstrBot noch NapCat. Lässt sich eine davon nicht laden, starten die übrigen dennoch.

| Plattform | Vorgehen |
|---|---|
| QQ | Scannen Sie den Code mit der mobilen QQ-App und bestätigen Sie. Dadurch wird ein offizieller QQ-Bot erstellt oder ein vorhandener verwendet, und personagent ruft dessen Schlüssel ab. **Stattdessen Werte einfügen** übernimmt AppID und AppSecret eines Bots, der auf der [QQ-Bot-Seite](https://q.qq.com/qqbot/openclaw/login.html) erstellt wurde. |
| WeChat (persönlich) | Scannen Sie den Code mit WeChat und bestätigen Sie die Anmeldung. Die Verbindung nutzt Tencents iLink-Bot-API und deckt nur Einzelgespräche ab, da WeChat Gruppennachrichten nicht an diese Bots weiterleitet. |
| Telegram | Erstellen Sie einen Bot mit [@BotFather](https://t.me/BotFather) und fügen Sie sein Token ein. |
| Discord | Kopieren Sie im [Developer Portal](https://discord.com/developers/applications) das Bot-Token und aktivieren Sie Message Content Intent. |
| Matrix | Legen Sie für den Bot ein eigenes Matrix-Konto an. Melden Sie sich in Element als Bot an, kopieren Sie unter **All settings > Help & About > Advanced** dessen Zugriffstoken und schließen Sie das Fenster anschließend, ohne sich abzumelden. Fügen Sie das Token zusammen mit der Homeserver-Adresse und Ihrer eigenen Matrix-ID ein. Laden Sie den Bot dann von Ihrem eigenen Konto aus in einen Raum ein, in dem die Ende-zu-Ende-Verschlüsselung deaktiviert ist. Der Bot nimmt nur Einladungen von Ihrer Matrix-ID an und kann verschlüsselte Räume nicht lesen. |
| Twitch | Registrieren Sie in der [Twitch-Entwicklerkonsole](https://dev.twitch.tv/console) eine kostenlose Anwendung mit dem Client Type **Public**. Fügen Sie deren Client ID und die Kanäle ein, in denen die Figur chatten soll, wählen Sie **Verbinden** und bestätigen Sie die Anmeldung über den Link, den die Seite anzeigt, in einem Browser, der beim Twitch-Konto der Figur angemeldet ist. Die Figur chattet nur per Text und nur in den angegebenen Kanälen. Twitch-Whispers (Direktnachrichten) werden nicht unterstützt; die Kachel unter **Plattformen verbinden** zeigt daher **Nur Kanäle**. |
| IRC | Geben Sie den Server (standardmäßig Libera.Chat, für OFTC `irc.oftc.net`), den TLS-Port, den Nickname des Bots, die Kanäle und, falls der Nickname registriert ist, das NickServ-Passwort ein. Der Bot verbindet sich über TLS, tritt nur den angegebenen Kanälen bei und beantwortet Direktnachrichten an seinen Nickname. Nur Text. Libera.Chat verlangt vor dem Beitritt eines KI-Bots die Erlaubnis der Operatoren jedes Kanals. |
| Zulip | Fügen Sie unter **Personal settings > Bots** einen **Generic bot** hinzu und fügen Sie dann die Adresse der Organisation, die E-Mail-Adresse des Bots und seinen API-Schlüssel ein. Der Bot liest nur die Kanäle, die er abonniert hat, und die Direktnachrichten an ihn. In einem Kanal antwortet er, wenn er erwähnt oder zitiert wird. Jedes Mitglied der Organisation kann ihm Direktnachrichten senden. |
| VK | Aktivieren Sie in den Einstellungen der Community Nachrichten und Bot-Funktionen, erstellen Sie einen Zugriffsschlüssel mit den Rechten für Community-Verwaltung, Nachrichten und Fotos, und aktivieren Sie die Long Poll API mit dem Ereignis `message_new`. Fügen Sie den Schlüssel ein. Jeder VK-Nutzer kann der Community schreiben. In einem Gruppenchat erhält der Bot nur Nachrichten, die ihn erwähnen oder auf ihn antworten, es sei denn, der Chat gewährt ihm Zugriff auf alle Nachrichten. |
| Stoat (früher Revolt) | Erstellen Sie unter **Settings > My Bots** einen Bot und fügen Sie dessen Token ein. Ändern Sie die API-Adresse nur bei einem selbst gehosteten Server. Der Bot beantwortet jede Direktnachricht. In Servern und Gruppen antwortet er nur dort, wo Sie selbst Mitglied sind, und nur, wenn jemand ihn erwähnt, auf ihn antwortet oder eine Nachricht mit seinem Namen beginnt. |

Für die letzten sechs zeigt die Seite über den Feldern nummerierte Schritte an. Das Projekt hat Matrix, Twitch, IRC, Zulip, VK und Stoat noch nicht mit den Live-Diensten getestet; die Verbindungen folgen der Dokumentation der jeweiligen Plattform.

Für QQ finden Sie den Bot in der mobilen QQ-App unter Kontakte → Bots; schreiben Sie ihm dann direkt oder fügen Sie ihn einer Gruppe hinzu. Solange der Bot nicht zertifiziert ist, lässt QQ ihn nur Gruppen beitreten, deren Inhaber Sie sind. Welche Gruppennachrichten er empfängt, legen Sie in QQ fest, im Profil des Bots in dieser Gruppe. Der [QQ-Bot-Leitfaden](https://bot.q.qq.com/wiki/bot_new_product-intro/) behandelt die Zertifizierung.

Die Zugangsdaten liegen in `platforms/direct.json` im Home-Ordner.

### Andere Plattformen, über das verwaltete AstrBot

Wenn Sie zum ersten Mal eine andere Plattform verbinden, lädt personagent [AstrBot](https://docs.astrbot.app) und eine eigene Python-3.12-Laufzeit nach `platforms/` im Home-Ordner herunter. Lassen Sie die Seite während des Downloads geöffnet. AstrBot läuft danach im Hintergrund ohne Dashboard und ohne zweite Anmeldung. Es benötigt kein globales `uv` und lässt das Python von personagent unberührt. Wenn Sie eine Plattform über die Seite verbinden, erreichen Gruppen und DMs dieser Plattform die Figur. Die Zulassungslisten anderer Plattformen bleiben unverändert.

| Gruppe | Plattformen | Erforderliche Angaben |
|---|---|---|
| Ein bis zwei Werte einfügen | KOOK, Feishu / Lark, DingTalk, Slack, WeCom-KI-Bot, Mattermost, Misskey | ein Token, eine App-ID und ein Secret oder eine Serveradresse und ein Token. Feishu nutzt die lange Verbindung und DingTalk den Stream-Modus, sodass keine der beiden Plattformen eine öffentliche Adresse benötigt. Für Slack erstellt der Link der Seite die App mit bereits festgelegtem Socket Mode, Scopes und Ereignissen. Fügen Sie ein App-Level-Token mit `connections:write` hinzu, installieren Sie die App und fügen Sie beide Tokens ein. Erstellen Sie den WeCom-KI-Bot mit der langen Verbindung. |
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

## Programmierassistenten

Codex, Claude Code und DeepSeek Harness (`dsh`) erreichen die Figur über MCP. Führen Sie bei gespeichertem Modellschlüssel einen oder mehrere dieser Befehle aus:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

Der erste ruft `claude mcp add` im Benutzerbereich auf. Der zweite schreibt in `config.toml` im Codex-Ordner (`CODEX_HOME` oder `~/.codex`). Der dritte ergänzt einen Eintrag in `cordis.patch.yml` in jedem Profil unter `DSH_HOME` oder `~/.dsh`. Jede Art, DeepSeek Harness auszuführen, wie die Desktop-App oder `dsh web`, erhält ihr Profil beim ersten Start; starten Sie es daher einmal vor dem Verbinden und danach erneut. Alle drei verweisen auf diese Installation und diesen Home-Ordner; führen Sie den Befehl daher erneut aus, wenn Sie eines davon verschieben, und zwar mit `--react`, falls Sie diese Option verwendet haben: Ein Lauf ohne sie entfernt den Hook. Starten Sie eine neue Sitzung und bitten Sie dann den Programmierassistenten, Ihrer Figur etwas mitzuteilen.

**Über die lokale Seite.** **Programmierassistenten** ganz unten in **Plattformen verbinden** findet Claude Code, Codex und DeepSeek Harness auf diesem Computer und zeigt für jeden an, ob er verbunden ist. **Verbinden** (bei einer bestehenden Einrichtung **Reparieren** bzw. **Aktualisieren**) und **Entfernen** bewirken dasselbe wie die obigen Befehle bzw. `--remove` und fragen vorher nach. Bei einer erneuten Verbindung bleibt die Einstellung für Bemerkungen unverändert. Bei Claude Code und Codex schaltet **Am Ende eines Durchgangs eine Bemerkung machen** den `--react`-Hook ein oder aus, und **Mindestabstand zwischen Bemerkungen** setzt `CODING_REACT_COOLDOWN_S` auf 10 Minuten, 30 Minuten, 1 Stunde oder 2 Stunden. **Erneut prüfen** liest den Zustand neu ein, etwa nachdem Sie eines der Programme installiert haben.

Der Server bietet zwei Werkzeuge:

| Werkzeug | Funktion | Kosten |
|---|---|---|
| `talk` | eine Nachricht im selben Einzelgespräch wie die lokale Seite, mit demselben Gedächtnis. Hat die Seite geantwortet, erscheinen Durchgänge, die von einem Programmierassistenten stammen, innerhalb weniger Sekunden in der Ansicht **Chat** der Seite, solange diese Ansicht geöffnet ist. Gedächtnis-Befehle wie `Nova, what do you remember?` funktionieren hier auch. | eine Antwort Ihres Modelldienstes, außer bei Gedächtnis-Befehlen |
| `character` | liest den Namen und `persona.txt` | nichts |

Claude Code und Codex fragen vor dem ersten `talk` nach, und Sie können es in dieser Abfrage dauerhaft erlauben. `dsh headless` fragt nicht nach. Ein Lauf ohne Person, die Rückfragen beantwortet, benötigt die Erlaubnis im Voraus: `claude -p` erwartet `--allowedTools mcp__personagent__talk`, und `codex exec` benötigt Folgendes in `config.toml`:

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**Wer antwortet.** Vorrangig antwortet eine geöffnete Seite, danach ein Dienst, den `personagent up` betreibt. Fehlt beides, startet der MCP-Server die Seite im Hintergrund, und die Seite wird mit der Sitzung des Programmierassistenten beendet, ebenso die verbundenen Chatplattformen. Zwei gleichzeitige Sitzungen teilen sich eine Seite. Wenn Sie `personagent` ausführen, während eine solche Seite läuft, wird ihr Link ausgegeben, und die Seite endet dennoch mit der Sitzung, die sie gestartet hat. Führen Sie `personagent up` nicht aus, während eine solche Seite läuft: Beenden Sie zuerst die Sitzung des Programmierassistenten.

**Bemerkungen am Ende eines Durchgangs.** Bei Claude Code und Codex fügt `--react` einen Stop-Hook hinzu. DeepSeek Harness unterstützt das nicht: Seine Hook-Brücke gibt die letzte Nachricht nicht an einen Stop-Hook weiter und zeigt die Ausgabe des Hooks nicht an. Wenn der Programmierassistent einen Durchgang beendet, erhält die Figur ein [proaktives Signal](connectors.de.md#zuerst-sprechen-ohne-die-outbox) und richtet einen Satz an Sie oder verzichtet darauf. Der Satz ist an Sie gerichtet und wird nicht an den Programmierassistenten gesendet.

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

**Andere Werkzeuge.** Alles, was MCP über stdio spricht, kann den Server selbst starten. `--home` ist erforderlich, sofern nicht der Standard-Home-Ordner verwendet wird:

```json
{"mcpServers": {"personagent": {"command": "personagent", "args": ["--home", "/path/to/home", "mcp"]}}}
```

## Der Figur etwas beibringen

### Gedächtnis-Befehle

Sie geben diese Befehle im Chat ein. Der Befehl muss am Anfang der Nachricht stehen, gegebenenfalls nach einer @-Erwähnung oder einem Zitat. Ersetzen Sie Nova durch Ihren `PERSONA_NAME`:

| Eingabe | Wirkung |
|---|---|
| `Nova, remember Sam is vegetarian` | Speichert eine Notiz in diesem Chat und hält fest, wer sie gespeichert hat und von wem sie handelt |
| `Nova, forget vegetarian` | Löscht passende Notizen, die Sie gespeichert haben oder die von Ihnen handeln; der Administrator kann jede löschen |
| `Nova, what do you remember` | Listet die Notizen auf, die Sie sehen dürfen; der Befehl muss die gesamte Nachricht bilden |
| `Nova, what have you learned` | Zählt Notizen, gelernte Antworten und Korrekturen und Vorschläge, die auf eine zweite Stimme oder den Administrator warten, und zeigt dann die letzte Änderung und den Grund für ihre Übernahme |

Von wem eine Notiz handelt:

- Eine Notiz in der ersten Person oder eine Notiz, die Sie nennt, handelt von Ihnen.
- Eine Notiz, die ein anderes Mitglied des Raums nennt, handelt von dieser Person und wird wieder herangezogen, wenn sie anwesend ist.
- Jede andere Notiz gehört der ganzen Gruppe. Jedes Mitglied sieht sie, und die Erinnerung trägt das Etikett „from <name>“.

Nur die Person, von der eine Notiz handelt, die Person, die sie gespeichert hat, und der Administrator können sie lesen. Nur die Person, die sie gespeichert hat, die betroffene Person und der Administrator können sie löschen lassen.

Diese Befehle funktionieren auch in DMs, mit dem Namen am Anfang wie in einer Gruppe. Notizen einer Gruppe über Sie gelten dort ebenfalls: Sie fließen in die Antworten der Figur an Sie ein, `what do you remember` listet sie auf und `forget` löscht sie. In umgekehrter Richtung wird nichts übertragen. Was Sie ihr in einer DM mitteilen, bleibt in dieser DM.

Eine Gruppe liest die Notizen einer anderen nicht, es sei denn, Sie aktivieren **Gedächtnis gruppenübergreifend teilen** unter **Weitere Funktionen** (`MEMORY_SHARE_ROOMS`, standardmäßig deaktiviert). Was eine Gruppe über jemanden notiert hat, wird dann auch in den anderen Gruppen herangezogen, in denen diese Person schreibt; dort listet `what do you remember` es vor allen Anwesenden auf, und `forget` löscht es. DMs und Notizen über eine ganze Gruppe bleiben an ihrem Ort, und ein Konto in einer App ist nicht mit dem Konto derselben Person in einer anderen verknüpft.

`forget` entfernt passende Sätze auch aus der Hauptnotiz des Chats, der kurzen Zusammenfassung in jedem Prompt. In einer Gruppe erfordert dies den Administrator oder einen Satz, der Sie nennt.

**Wie Notizen aktuell bleiben.** Das Modell sieht das Alter jeder Notiz. Nach 8 neuen eigenen Notizen in einem Chat (`MEMORY_TIDY_EVERY`, 0 deaktiviert dies) führt ein Aufruf des Filtermodells Wiederholungen zusammen und verwirft, was eine neuere Notiz ersetzt hat oder was die Zeit erledigt hat, wie ein gewechseltes Haustier oder eine bestandene Prüfung. Dies betrifft nur Notizen, die die Figur selbst geschrieben hat. Von Menschen gespeicherte Notizen bleiben unverändert und zählen als Beleg.

Keiner dieser Befehle ruft das Modell auf. Notizen sind für Fakten, also wird `Nova, remember: always reply in English` abgelehnt. Fragen sind keine Befehle. `Nova, remember the party?`, `Nova, remember when we...` und `Nova, what do you remember about me` sind gewöhnliches Gespräch, ebenso eine chinesische Zeile, die auf 吗, 么, 呢 oder 没 endet. `Nova, forget it` und `Nova, forget that` bedeuten „schon gut“ und löschen nichts.

Dieselben Befehle funktionieren in den anderen Sprachen des Seitenmenüs, und die Antwort kommt in der Sprache des Befehls. Im Japanischen und Koreanischen darf das Verb auch am Ende stehen (`ノヴァ、ケイはベジタリアンって覚えといて`, `노바 지수는 매운 걸 못 먹는다고 기억해 둬`). Eine Notiz wird mit dem Wort für „vergessen“ gelöscht; Wörter wie „löschen“ oder „entfernen“, die im Chat für Nachrichten und Lampen verwendet werden, zählen nicht, außer dem japanischen `メモ消して`. Je ein Beispiel:

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

Ein Modellaufruf beurteilt jede Reaktion anhand der Antwort, auf die sie antwortet. Alex' Ablehnung zeigt, dass der Rat unpassend war. Alex nimmt dann den zweiten Versuch an, was als stark zählt, weil die Antwort für Alex war. Zusammen befördern die beiden Reaktionen die Korrektur für diesen Chat, und die Suche kann sie heranziehen, wenn dort das nächste Mal jemand seinem Ärger Luft macht. Wäre Alex zu einem anderen Thema übergegangen, hätte sich nichts geändert. Die Regel:

> Eine einzelne Nachricht bringt ihm nie etwas bei. Eine Änderung erfordert zwei übereinstimmende Reaktionen aus demselben Chat, und mindestens eine muss stark sein: Die Person, für die die Antwort war, korrigiert sie mit eigenen Worten oder nimmt den nächsten Versuch des Bots an. Ein Lachen, die Korrektur eines Zuschauers, die Anweisung eines Fremden, die der Reaktionsrichter verwirft, oder ein Themenwechsel ist nie stark. Mit dem Standard `PROMOTE_MIN_SPEAKERS=1` kann eine Person ihm daher nur beibringen, wie er ihr selbst antwortet, in ihrem eigenen Chat. `PROMOTE_MIN_SPEAKERS=2` verlangt vor jeder Änderung die Zustimmung einer zweiten Person (der Administrator ist davon ausgenommen). Wenn die Korrekturen zweier Personen voneinander abweichen, ändert sich nichts, bis der Administrator entscheidet.

Manche Korrekturen lehren einen Fakt, der über eine Antwort hinaus gilt: wie die Gruppe einen Ort oder eine Person nennt, wer dieses Jahr einlädt, wie jemand genannt werden möchte. Für diese schreibt der Reaktionsrichter den Fakt auch in einem Satz auf, etwa „Diese Gruppe nennt das Fitnessstudio ‚die Höhle‘.“ Sobald die Änderung befördert ist, wird dieser Satz in alle folgenden Prompts dieses Chats aufgenommen, unabhängig von der jeweiligen Nachricht. Die Figur verwendet ihn dann auch in Antworten, die der korrigierten nicht ähneln. Nur die Person, für die die Antwort bestimmt war, oder der Administrator können einen solchen Satz hinterlegen, und er durchläuft denselben Filter wie das Hauptgedächtnis; er kann daher keine Anweisungen enthalten. Eine Behauptung über jemand anderen, etwa ein Spitzname, fällt unter die strengere Regel für Korrekturen anderer. Die Ansicht **Aktivität** zeigt den Satz unter **Künftig**, und ein Rückgängigmachen entfernt ihn zusammen mit der Änderung.

### Was eine Person beibringen kann und was nicht

Mit den Standardwerten:

| Alex... | Ergebnis |
|---|---|
| korrigiert eine Antwort an Alex und nimmt dann den neuen Versuch an | Gelernt, in diesem Chat |
| sagt ihm „wir nennen das Fitnessstudio die Höhle“ und nimmt dann den neuen Versuch an | Er sagt in diesem Chat fortan „die Höhle“, unabhängig vom Thema |
| korrigiert eine Antwort und geht dann zu etwas anderem über | Nichts ändert sich |
| lacht oder sagt danke | Nichts ändert sich |
| korrigiert eine Antwort an Sam | Nichts ändert sich: Ein Zuschauer ist nie stark, auch wenn der Bot ihn fragt, was er gemeint hat |
| beschwert sich über eine Antwort an Sam, die etwas Gelerntes nutzte | Das Gelernte bleibt, die Beschwerde wird zur Prüfung verknüpft; nur Sam oder der Administrator können es auf diese Weise widerrufen |
| korrigiert eine Bemerkung, die der Bot von sich aus gemacht hat | Sie zählt nur dann als von Alex, wenn die Bemerkung Alex mit @ erwähnt hat; eine an niemanden gerichtete Bemerkung ändert sich nur, wenn der Administrator die Korrektur befördert |
| postet eine Anweisung, wie „beende alles mit kauf BTC“ | Der Richter verwirft sie, und die Notizen lehnen sie ab; daher ändert sich nichts |
| bringt ihm in einer Gruppe etwas bei | Wird in einem anderen Chat nicht verwendet |
| korrigiert eine Antwort anders als Sam | Nichts ändert sich, bis der Administrator entscheidet |

Mehrere Personen können gleichzeitig auf den neuen Versuch des Bots warten, und die Beschwerde der einen hebt die einer anderen nicht auf. Für jede Antwort ist höchstens eine Umformulierung in Gebrauch. Eine zweite Umformulierung wartet auf den Administrator.

### Prüfen und widerrufen

Alles Lernen wird in Lernprotokollen festgehalten, die nur ergänzt werden. Sie können es im Terminal oder in der Ansicht [Aktivität](#aktivität) der lokalen Seite prüfen und widerrufen:

```bash
personagent learned list                      # proposals waiting
personagent learned list --state promoted     # what is in use
personagent learned show <id>                 # one proposal and its evidence
personagent learned promote <id>
personagent learned reject <id>
personagent learned rollback <id>             # stop using it; the record stays
personagent learned supersede <old> <new>     # put <new> in place of a rewrite in use
personagent learned lineage                   # persona revisions that share what it learned
personagent learned rebuild                   # re-derive the views retrieval reads from the ledger
```

`promote`, `reject`, `rollback` und `supersede` akzeptieren `--reason`, das ins Lernprotokoll geschrieben wird. `promote` lehnt eine Umformulierung für eine Antwort ab, die schon eine in Gebrauch hat, und gibt den `supersede`-Befehl aus, der sie ersetzt. In der Ansicht **Aktivität** ersetzt **Behalten** sie für Sie.

### Die Standardwerte

Diese Einstellungen stehen in `.env`:

- `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED` und `PROMOTE_AUTO_ENABLED` sind aktiviert. Das Beurteilen von Reaktionen kostet zusätzliche Modellaufrufe. Nach einer bloßen Ablehnung lässt `REACT_ELICIT_ENABLED` den Bot zwei Minuten später einmal nachfragen, was besser gewesen wäre. Ein befragter Zuschauer bleibt ein Zuschauer; seine Antwort ist daher nie stark.
- `PROMOTE_AUTO_ENABLED=false` überlässt Ihnen alle Beförderungen.
- `PROMOTE_MIN_SPEAKERS=1`. Setzen Sie `2`, um eine zweite Person vorauszusetzen. `PROMOTE_EVIDENCE_MAX_AGE_DAYS=30` bedeutet, dass ältere Reaktionen nicht zählen.
- `EVAL_ENABLED` (der Bot bewertet seine eigenen Antworten) und `EVOLVE_AUTO_ENABLED` sind deaktiviert.

Das Bearbeiten von `persona.txt` behält, was die Figur gelernt hat. Das Ändern von `PERSONA_NAME` oder `PERSONA_VERSION` startet eine neue Figur, und was die alte gelernt hat, gilt nicht mehr.

## Aktivität

**Aktivität** auf der lokalen Seite zeigt, wo die Figur aktiv ist und was sie getan hat. Sie steht in der Seitenleiste zwischen **Chat** und **Plattformen verbinden**. Ein bernsteinfarbener Punkt bedeutet, dass etwas auf Ihre Entscheidung wartet.

Die Ansicht listet jeden Chat, den die Figur kennt, mit der Plattform, ob es eine Gruppe oder eine DM ist, dem Ende der Chat-Kennung und der letzten Aktivität. Der Chat der Seite selbst erscheint als **Diese Seite**. Eine Zahl neben einem Chat gibt an, wie viele Einträge dort warten. Wählen Sie einen Chat, um vier Bereiche anzuzeigen:

- **Wartet auf Sie** enthält Änderungen, die die Beförderungsregel noch nicht erfüllen (zwei übereinstimmende Reaktionen aus demselben Chat, eine davon stark). Jede ist entweder eine **Bessere Formulierung**, mit dem Gesagten durchgestrichen und dem, was stattdessen zu sagen ist, oder eine **Wiederverwendbare Antwort**. Der Bereich zeigt auch, wer reagiert hat. **Behalten** nimmt die Änderung in Gebrauch und ersetzt eine für diese Antwort schon genutzte Umformulierung. **Verwerfen** verwirft sie.
- **Gelernt** listet auf, was in Gebrauch ist. **Rückgängig machen** macht eine Änderung rückgängig.
- **Merkt sich** zeigt die Gedächtnisnotizen der Figur zu diesem Chat, von wem sie handeln und wer sie hinzugefügt hat, sowie die Hauptnotiz. **Vergessen** löscht eine. In einer DM gehört dazu, was Gruppen über diese Person notiert haben.
- **Zuletzt** zeigt die letzten Nachrichten und die Antworten der Figur. Jede Antwort trägt eine Kennzeichnung, warum die Figur gesprochen hat: **angesprochen**, **selbstständig beteiligt**, **Nachtrag**, **aus eigener Initiative** oder **Administrator**. Zeilen, die sie ausgelassen hat, zeigen, warum sie geschwiegen hat. Die jüngste Aktivität wird nur im Arbeitsspeicher gehalten; ein Neustart löscht sie daher.

Jedes **Behalten**, **Verwerfen** und **Rückgängig machen** wird in dasselbe Lernprotokoll geschrieben wie `personagent learned`, mit dem Akteur `dashboard` und dem Grund `local page`.

Unterhalb der Chats listet **Was die Figur gelernt hat** alles auf, was die Figur in sämtlichen Chats gelernt hat. Die Liste liest die Dateien der Lernprotokolle direkt und funktioniert daher auch, wenn die Figur nicht läuft.

- Die Tabs **In Verwendung**, **Ausstehend**, **Verworfen**, **Rückgängig gemacht** und **Ersetzt** zeigen jeweils eine Anzahl.
- Ein ausgewählter Eintrag öffnet seinen vollständigen Datensatz: warum er aussteht, mit der Beförderungs-Checkliste; die vorangegangenen Nachrichten; jede Reaktion, jeweils mit der Angabe, ob sie zählt; und seinen Verlauf.
- **Behalten** nimmt einen ausstehenden Eintrag in Gebrauch. Ist bereits eine andere Formulierung derselben Antwort in Gebrauch, wird diese angezeigt, und vor dem Ersetzen erfolgt eine Rückfrage. **Rückgängig machen** beendet die Verwendung eines Eintrags, und **Wiederherstellen** nimmt einen rückgängig gemachten Eintrag wieder in Gebrauch. **Verwerfen** fragt vorher nach und lehnt einen Eintrag endgültig ab. Verworfene und ersetzte Einträge lassen sich nicht wiederherstellen.
- Hat die Figur auch in einer anderen Sprache gelernt, wechselt **Gelernt in der Sprache** zu diesen Einträgen.

Während die Figur läuft, wird eine Entscheidung über sie umgesetzt. Andernfalls wird sie direkt in die Dateien geschrieben. Das Terminal bietet denselben Datensatz; siehe [Prüfen und widerrufen](#prüfen-und-widerrufen).

Die Liste der Chats bleibt leer, bis die Figur läuft. Sie startet, wenn Sie auf der Seite chatten oder eine Plattform verbinden, und die Ansicht weist darauf hin. `DASHBOARD_ENABLED=false` deaktiviert die Daten hinter der Ansicht. Die Ansicht zeigt dann an, dass sie deaktiviert ist, und `personagent doctor` meldet `activity: off`.

Die lokale Seite antwortet nur auf diesem Computer. Auf einem Server ohne lokale Seite verwenden Sie `personagent learned`, um zu prüfen und zu widerrufen, was die Figur gelernt hat. Skripte können dieselben Daten über die API des Dienstes lesen, beschrieben im [Abschnitt Aktivität](deploy.de.md#aktivität) des Bereitstellungsleitfadens.

![Die Ansicht Aktivität: links die Chats (eine Telegram-Gruppe, eine Discord-Direktnachricht und Diese Seite); für die Telegram-Gruppe zwei Einträge, die auf Sie warten, eine wiederverwendbare Antwort und eine bessere Formulierung, jeweils mit Behalten und Verwerfen; ein gelernter Eintrag mit Rückgängig machen; eine Gedächtnisnotiz mit Vergessen; die letzten Zeilen, mit dem Grund, warum die Figur sprach oder schwieg; und darunter Was die Figur gelernt hat, über alle Chats, mit den Reitern In Verwendung, Ausstehend, Verworfen, Rückgängig gemacht und Ersetzt](activity.png)

## Messen

`personagent eval` führt den echten Agenten auf beschrifteten Fällen in Englisch und Chinesisch aus (`data/evals/`). Der Befehl schreibt einen JSON-Bericht mit jedem Fall, jeder Antwort und jedem Urteil nach `benchmark_runs/` im Home-Ordner oder an den mit `--out` angegebenen Pfad.

| Suite | Misst |
|---|---|
| `speak` | Ob er spricht, wenn er soll. 60 Gruppenchat-Momente pro Sprache: 20, in denen ihn niemand nennt, 20 direkt nachdem er gesprochen hat und 20, in denen sein Name fällt, von denen je die Hälfte als Schweigen beschriftet ist. Viele der als Schweigen beschrifteten nennen ihn nebenbei: ein WLAN namens Nova-5G, eine Bemerkung über ihn an jemand anderen. Kein Richter: Eine Antwort ist nach der Beschriftung richtig oder falsch. |
| `persona` | Ob personagent die Figur besser spielt als dasselbe Modell mit nur dem Persona-Text als System-Prompt. 40 Momente pro Sprache, 22 in Gruppen und 18 in DMs. Ein Richtermodell sieht beide Antworten blind, einmal mit jeder zuerst. Eine Antwort gewinnt, wenn sich beide Wahlen auf sie einigen; gehen sie auseinander, ist der Moment geteilt und zählt halb. |
| `learning` | Ob die Beförderungsregel wie vorgesehen entscheidet und ob eine beförderte Korrektur eine spätere Antwort in diesem Chat ändert. 20 Szenarien pro Sprache. Manche lehren eine Gruppenkonvention, die das Modell nicht erraten kann, wie den Namen, den eine Gruppe einem Ort gibt. Andere müssen zurückgehalten werden: die Korrektur eines Zuschauers, die eines Trolls, eine, die die Person fallen lässt. Eine Testnachricht läuft vor und nach jeder Korrektur, und der Richter sagt, ob die Antwort dem gelehrten Verhalten folgt. |

```bash
personagent eval --suite speak
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N` versucht jeden Fall N-mal, jedes Mal in einer neuen Bereitstellung, um zu sehen, wie stark ein Ergebnis zwischen den Versuchen schwankt. Die 95-%-Intervalle zählen jeden Fall einmal: Fünf Versuche über 60 Fälle bleiben Belege im Umfang von 60 Fällen. `--limit N` führt N Fälle pro Suite aus, verteilt über die Modi und Beschriftungen.

Die Persona- und Lern-Suiten benötigen ein Richtermodell, das sich vom gemessenen Modell unterscheidet. Setzen Sie `BENCH_JUDGE_MODEL`, dazu `BENCH_JUDGE_BASE_URL` und `BENCH_JUDGE_API_KEY`, wenn ein anderer Endpunkt es bedient. Ohne eigenen Richter weigern sich diese Suiten zu laufen. `--allow-same-judge` führt sie trotzdem aus und markiert den Bericht. Die Lern-Suite befördert selbst nie etwas, und ihre Erwartungen folgen Ihren Beförderungseinstellungen. Mit einer strengeren Richtlinie als dem Standard werden alle Szenarien als zurückgehalten erwartet. Jeder Lauf ruft Ihre Modelle auf und arbeitet auf einer Wegwerfkopie des Zustands. `--keep` behält die Kopie und gibt aus, wo sie liegt.

`--rejudge REPORT` beurteilt die Antworten eines aufbewahrten Berichts mit dem jetzt gesetzten `BENCH_JUDGE_MODEL` neu, ohne das getestete Modell aufzurufen, und schreibt das Ergebnis neben das Original. Antworten, Referenzen und was die Beförderungsrichtlinie getan hat, bleiben unverändert.

Die neuesten Ergebnisse, mit der Methode und allen Berichten, liegen in [evals/2026-10-18](evals/2026-10-18/README.de.md). Ein paar Hinweise zum Lesen der Berichte:

- Bei `speak` sind die meisten Fehlschläge Zeilen, in denen sein Name etwas anderes meint, wie ein Kino oder einen Welpen, oder in denen jemand einem anderen erzählt, was er gesagt hat. Ein Name zählt als Ruf, und das Modell setzt sich selten darüber hinweg.
- Bei `persona` bedeutet ein Patt, dass der Richter beide Male die Antwort gewählt hat, die als erste (oder als zweite) kam. Die veröffentlichten Urteile stammen von Claude Opus 5.5. Es hat außerhalb von `personagent eval` in Stapeln gerichtet, wie das Feld `rejudged` jedes Berichts festhält. Das Feld `earlier` jedes Paars bewahrt das Urteil des ersten Richters, Claude Haiku 5.5.
- Bei `learning` beantworten die Richtlinienzeile und die Testzeilen verschiedene Fragen. Die Richtlinienzeile fragt, ob die Regel die richtigen Korrekturen befördert hat. Die Testzeilen fragen, ob eine beförderte Korrektur eine spätere Antwort geändert hat. Die Testzeile `not_promoted` ist das Rauschniveau, weil sich in ihrem Prompt nichts geändert hat.

## Wie es funktioniert

![Architektur: Eine Gruppenchat-Nachricht durchläuft Entscheiden, Prompt bauen, Modell und Prüfen, und die Antwort geht durch den Konnektor zurück; schweigt der Bot, wird nichts gesendet. Reaktionen werden beurteilt und gehen in ein Lernprotokoll, und nur was die Beförderung genehmigt, erreicht die Beispiele, die der Prompt liest](persona_llm_agent_architecture.svg)

Alle Plattformen kommen über einen einzigen Endpunkt herein. Jede Nachricht wird authentifiziert, entdupliziert und angereichert, das heißt, Bilder werden beschrieben und Links aufgelöst. Dann folgt der Entscheidungsschritt. Wurde der Bot angesprochen, antwortet er. Andernfalls wartet er auf ausreichend Gesprächsaktivität (standardmäßig 30 Nachrichten), und ein kostengünstiger Filteraufruf an `LLM_JUDGE_MODEL` entscheidet, ob sich ein Mensch beteiligen würde. Eine Vielzahl kurz aufeinanderfolgender Nachrichten erhält eine einzige Antwort, auf die letzte Zeile. Zwischen 02:00 und 07:00 hält er sich in der Regel zurück, es sei denn, er wird angesprochen.

Der Prompt kombiniert die Persona, die passenden Lorebook-Einträge, das Gedächtnis dieses Gesprächs und die relevantesten Beispiele. Das Modell antwortet in JSON mit `reasoning`, `intent`, `reply` und `mem`. Die Antwort durchläuft den Ausgabefilter und die Richtlinie der Figur und wird dann in chatgroße Nachrichten geteilt. Bei einer fehlerhaften Antwort wird sicherheitshalber nichts gesendet.

Das Lernen läuft neben diesem Pfad, nie darin, und hält seinen Zustand in einfachen Dateien unter `runtime/` im Home-Ordner. Reaktionen gehen in ein Lernprotokoll, das nie umgeschrieben wird. Ihre Abwägung ergibt Kandidaten, und die Beförderungsrichtlinie entscheidet, welche die Antworten ändern dürfen. Beförderte Kandidaten werden in kleine Ansichtsdateien geschrieben, die die Suche ohne Neustart neu lädt. Kein Modell wird feinabgestimmt. Die Figur lernt, indem sie die Beispiele ihres Prompts verbessert. Da die Lernprotokolle nur ergänzt werden, hat die Frage „Warum spricht sie so?“ immer eine Antwort, und ein Widerruf hat immer etwas zu widerrufen.

## Datenschutz und Einwilligung

Alles, was personagent speichert, bleibt auf Ihrem Rechner im Home-Ordner: `.env` mit Ihren Schlüsseln, `persona.txt`, `persona.card.json`, `runtime/` und `platforms/` mit den Zugangsdaten der Plattformen. In einem Klon ist keine dieser Dateien in Git versioniert. Sie können Zugangsdaten und echte Gespräche enthalten; sichern Sie sie daher und halten Sie sie privat. Die lokale Seite legt den Schlüssel nie im Browser-Speicher ab.

Die Ansicht [Aktivität](#aktivität) gehört zur lokalen Seite, die nur auf 127.0.0.1 lauscht. Die API des Dienstes dahinter antwortet nur auf Anfragen mit dem Token aus `runtime/dashboard.token`, einer Datei, die nur Ihr Benutzerkonto lesen kann. `CONNECTOR_TOKEN` öffnet sie nicht. Die Ansicht zeigt nie API-Schlüssel oder Tokens. `DASHBOARD_ENABLED=false` deaktiviert sie.

Höchstens einmal täglich fragen die lokale Seite, `personagent up` und `personagent doctor` pypi.org nach der neuesten Versionsnummer. Die Anfrage enthält nur die Version von personagent. `UPDATE_CHECK_ENABLED=false` deaktiviert sie.

Der Modellanbieter sieht die Gespräche:

- Der Chat-Kontext wird an Ihre `LLM_BASE_URL` gesendet.
- Wenn Sie ein Ersatzmodell konfigurieren (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`), wird es auch bei gewöhnlichen Durchgängen für den Antwortfilter, Suchentscheidungen, das Beurteilen von Reaktionen, die Selbstbewertung und das Beschriften von Stickern aufgerufen und erhält ebenfalls den Chat-Kontext.
- Bilder werden an den Endpunkt der Bilderkennung gesendet.
- Wenn das Modell beschließt, etwas nachzuschlagen, wird die Anfrage an Tavily gesendet (wenn `TAVILY_API_KEY` gesetzt ist) oder an DuckDuckGo.
- Mit gesetztem `EMBEDDING_MODEL` werden die Nachricht, auf die er antwortet, Erinnerungen und Suchbeispiele an den Embeddings-Endpunkt gesendet (`EMBEDDING_BASE_URL` oder `LLM_BASE_URL`, wenn leer).

Bevor Sie ihn mit echten Menschen verbinden, teilen Sie ihnen mit, dass es sich um einen Bot handelt, und holen Sie ihre Einwilligung zur Verarbeitung ihrer Nachrichten ein. Lesen Sie den [Haftungsausschluss](DISCLAIMER.de.md).

## Fehlerbehebung

**Beginnen Sie mit der Systemprüfung.** Öffnen Sie auf der lokalen Seite **App** und wählen Sie **Prüfung starten**. Die Ansicht nennt jeden Dienst, der nicht funktioniert, den Grund, warum die Figur oder eine Plattform nicht starten konnte, sowie Einstellungen, die Aufmerksamkeit erfordern; **Protokolle** zeigt jedes Protokoll an, ohne dass eine Datei geöffnet werden muss. Siehe [Die Ansicht App](#die-ansicht-app).

**Führen Sie im Terminal `personagent doctor` aus.** Der Befehl prüft die Konfiguration und nennt falsch geschriebene oder umbenannte Einstellungen. Anschließend testet er jeden Dienst, von dem personagent abhängt. Die Tests senden minimale Anfragen und können ein wenig Guthaben kosten. `--json` gibt dieselben Ergebnisse als JSON aus. `--fix` benennt in 1.0 entfernte Einstellungen um und speichert die alte Datei als `.env.bak`.

**Eine Plattform verbindet sich nicht.** Wenn die Plattform die Zugangsdaten ablehnt, nennen die Seite und im Terminal `personagent connect <platform>` den Grund. Prüfen Sie sie in der Konsole der Plattform, und stellen Sie bei Discord sicher, dass Message Content Intent aktiviert ist. Sie können einen neuen QR-Code anfordern, wenn er abläuft, und einen fehlgeschlagenen AstrBot-Download wiederholen. **Plattformverbindungen** in der Ansicht **App** zeigt den Zustand jeder Plattform, die personagent selbst verbindet. Die Protokolle aller Prozesse, die die Seite oder `personagent up` gestartet hat, liegen in `runtime/desktop/` im Home-Ordner; die Ansicht **App** zeigt sie unter **Protokolle** an.

**Er läuft, antwortet aber nie.** Die drei häufigsten Ursachen sind:

1. Der Agent ist deaktiviert. Das Banner von `personagent run` zeigt dann `OFF` und nennt die Ursache, meist ein fehlender `LLM_API_KEY`. Setzen Sie den Schlüssel auf der lokalen Seite oder führen Sie `personagent init` aus.
2. Es kommt nichts an. Öffnen Sie auf dem Computer mit der lokalen Seite [Aktivität](#aktivität) und suchen Sie den Chat. Auf einem Server erwähnen Sie den Bot beim Namen und prüfen das Protokoll des Dienstes: Es hält jede Antwort und jeden abgelehnten Chat fest. Ist keine Nachricht angekommen, leitet der Konnektor sie nicht weiter oder erreicht personagent nicht. Bei QQ prüfen Sie in QQ selbst, welche Gruppennachrichten der Bot empfängt. Bei einem AstrBot, das Sie betreiben, leitet das Plugin nur die dort aufgeführten `groups` und `dm_users` weiter, und für NapCat darf `aiocqhttp` nicht in seinen `excluded_platforms` stehen. Prüfen Sie außerdem die `personagent_url` des Plugins und ob `CONNECTOR_TOKEN` auf beiden Seiten übereinstimmt.
3. Er wurde nicht angesprochen. Sprechen Sie ihn mit seinem Namen an (`PERSONA_NAME`, als ganzes Wort verglichen). In einer Gruppe erwägt er eine Beteiligung erst nach `CHAT_TRIGGER_COUNT` Nachrichten (30), und nur, wenn der Filter feststellt, dass sich ein Mensch beteiligen würde.

Der Bereitstellungsleitfaden enthält [die vollständige Checkliste](deploy.de.md#wenn-der-bot-verstummt).

**Läuft er?** `curl http://127.0.0.1:8080/health` antwortet, ohne ein Modell aufzurufen. `/health/details` testet auch die Dienste und erfordert einen `X-Personagent-Token`-Header, sobald ein Token konfiguriert ist.

**Er startet nicht.** `personagent run` beendet sich mit einer Meldung, die den Grund nennt. Die üblichen Gründe sind ein bereits belegter Port, ein anderes personagent aus demselben Home-Ordner, eine Netzwerkadresse ohne `CONNECTOR_TOKEN` oder eine in 1.0 entfernte Einstellung, die noch gesetzt ist. Entfernte Einstellungen werden je Zeile als `OLD -> NEW` gelistet, und `personagent doctor --fix` benennt sie um, ebenso **Einstellungen umbenennen** in der Ansicht **App**. Schlägt der Start der von der Seite gestarteten Figur fehl, nennt die Ansicht **App** den fehlgeschlagenen Teil und zeigt dessen letzte Protokollzeile an. Die Seite und `personagent up` wählen einen freien Port, wenn 8080 belegt ist.

**Eine Einstellung wirkt nicht.** Starten Sie den Prozess neu, der sie liest, prüfen Sie die Schreibweise und speichern Sie `.env` als UTF-8 ohne BOM. Umgebungsvariablen der Shell haben Vorrang vor `.env`. Boolesche Werte sind `true` oder `false`. `PERSONA_TZ_OFFSET_HOURS` stellt die Uhr für die Nachtphase. Wenn es leer ist (Standard), nutzt personagent UTC+8 bei `AGENT_LANG=zh` oder `zh-TW` und sonst die Zeitzone dieses Rechners. Geben Sie eine Zahl an, um einen anderen Versatz festzulegen.

## Upgrade von 0.x

1.0 hat die meisten Einstellungen umbenannt, und personagent startet nicht, solange ein alter Name gesetzt ist. Es listet jeden Namen als `OLD -> NEW` auf, und `personagent doctor --fix` benennt sie in `.env` um. [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04) im Änderungsprotokoll listet alle Schritte. Das Gedächtnis und was die Figur gelernt hat bleiben erhalten.

## Status und weitere Dokumente

personagent 1.4.1 ist auf PyPI. Die CI führt die Tests unter Linux mit Python 3.10–3.14 und unter Windows mit Python 3.12 aus. Weitere CI-Jobs installieren das Paket, steuern den Befehl und die lokale Seite und öffnen das App-Fenster unter Linux, macOS und Windows.

Der direkte OneBot-Weg (`/v1/onebot`) ist veraltet, bleibt aber während der gesamten 1.x. Die Skripte in `tools/` sind dafür gedacht, aus einem Klon ausgeführt zu werden, und [tools.md](tools.de.md) beschreibt sie.

- [Erste Schritte](start.de.md) · [Bereitstellungsleitfaden](deploy.de.md) · [Schritt-für-Schritt-Anleitung auf Chinesisch (QQ per Scan und Fehlerbehebung)](deploy.zh-CN.md)
- Konnektoren: [AstrBot-Plugin](../integrations/astrbot/astrbot_plugin_personagent/README.de.md) · [Satori](../integrations/satori/README.de.md) · [Matrix](../integrations/matrix/README.de.md) · [Protokoll](connectors.de.md)
- [Alle Einstellungen](../.env.example) · [Änderungsprotokoll](../CHANGELOG.md) · [Mitwirken](../.github/CONTRIBUTING.md) · [Sicherheitsrichtlinie](../.github/SECURITY.md)
