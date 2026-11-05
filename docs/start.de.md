# Erste Schritte mit personagent

[English](start.md) · [简体中文](start.zh-CN.md) · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · [Français](start.fr.md) · Deutsch · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · [Vollständige Anleitung](guide.de.md)

## Öffnen

Installiere personagent von PyPI und öffne es:

```sh
python -m pip install personagent
personagent
```

Mit [uv](https://docs.astral.sh/uv/) startet `uvx personagent` es ohne eigenen Installationsschritt.

Ein Coding-Agent kann die Einrichtung für dich übernehmen: Bitte ihn, [setup-for-agents.md](setup-for-agents.md) zu lesen und personagent einzurichten.

Unter Windows kannst du auch das Quellcode-ZIP herunterladen, entpacken und `start.bat` doppelklicken. Es legt im Ordner eine eigene Python-Umgebung an und öffnet dieselbe Seite.

Um es aus einem Klon zu starten, gib ihm ein eigenes venv: `python -m venv .venv`, dann `.venv/bin/python -m pip install -e .` und `.venv/bin/python -m persona_agent`. Unter Windows ist der Interpreter `.venv\Scripts\python.exe`, oder du doppelklickst `start.bat`.

## Schlüssel eintragen und chatten

Wähle einen Modelldienst, füge seinen API-Schlüssel ein und klicke auf **Prüfen & Chat starten**. Zu Beginn sind die kostenlosen Modelle von OpenRouter und der Charakter „Herzlicher Zuhörer“ ausgewählt. Der Schlüssel ist kostenlos, das Limit liegt bei 50 Anfragen pro Tag. **Erweiterte Einstellungen** enthält den Modellnamen und die API-Adresse, **Namen oder Persönlichkeit wählen** den Namen und die Persönlichkeit des Charakters.

Der Schlüssel bleibt auf deinem Computer; klicke auf **Anzeigen**, um ihn zu prüfen. Chatnachrichten gehen an den gewählten Modelldienst, zu dessen üblichen Preisen.

Dein Charakter antwortet auf der Seite. Deine Einstellungen werden gespeichert, also geht es beim nächsten Start direkt in den Chat.

Nach der Einrichtung gibt es unter **Charakter & Einstellungen** ein Feld **Persona** mit dem Text, auf dem der Charakter beruht. Schreibe um, wer er ist und wie er spricht, und klicke auf **Persona speichern**. Die Änderung gilt sofort, und was der Charakter gelernt hat, bleibt erhalten.

Darunter schaltet **Weitere Funktionen** die Websuche, das Bildverständnis und das Von-sich-aus-Reden ein. Die Suche nutzt standardmäßig DuckDuckGo; mit einem Tavily-Schlüssel wird sie zuverlässiger. Solange du keine App verbunden hast, zeigt die Ansicht **Chat** eine kurze Einstiegsleiste.

## In andere Apps mitnehmen

1. Klicke auf **Apps verbinden** und wähle eine App. Sobald sie verbunden ist, antwortet dein Charakter in den Gruppenchats und Direktnachrichten dieser App.
   - **Per Scan verbinden**: QQ und persönliches WeChat. Klicke auf **QR-Code holen** und bestätige auf deinem Handy.
     - QQ: Scanne mit mobilem QQ. QQ erstellt einen Bot oder lässt dich einen vorhandenen wählen, und personagent holt seine Schlüssel. Wenn du den Bot selbst auf der [Bot-Seite von QQ](https://q.qq.com/qqbot/openclaw/login.html) erstellt hast, klicke auf **Stattdessen Werte einfügen** und gib seine AppID und sein AppSecret ein.
     - WeChat: Scanne mit WeChat. Der Bot chattet nur eins zu eins, weil WeChat Gruppennachrichten nicht an diese Bots weitergibt.
   - **Ein oder zwei Werte einfügen**: Telegram (ein Token von @BotFather), Discord (ein Bot-Token, mit aktiviertem Message Content Intent), KOOK, Feishu, DingTalk, Slack, WeCom-KI-Bot, Mattermost und Misskey. Die Seite sagt dir, welche Werte du aus der Konsole der App kopieren musst. Alles andere nutzt Standardwerte.
   - **Erweitert**: WeCom-Apps, offizielle WeChat-Konten und QQ-Webhooks brauchen eine öffentliche Adresse, die an ihren Callback-Port weiterleitet. OneBot v11 (NapCat) und Satori brauchen andere Software, die auf diesem Computer läuft.
2. personagent verbindet QQ, WeChat, Telegram und Discord selbst. Die anderen Apps laufen über AstrBot, eine Brücke eines Drittanbieters. Wenn du eine davon zum ersten Mal verbindest, lädt personagent AstrBot mit einer separaten Python-3.12-Laufzeit herunter, also lass die Seite offen, bis das fertig ist. AstrBot läuft danach im Hintergrund, ohne Dashboard, bei dem man sich anmelden müsste.
3. personagent prüft die Zugangsdaten bei der App, bevor es sie speichert. Lehnt die App sie ab, sagt dir die Seite das, und nichts wird gespeichert.
4. Verbundene Apps stehen oben unter **Apps verbinden**, wo du sie neu einrichten oder trennen kannst.

Um einen QQ-Bot zu finden, öffne mobiles QQ und gehe zu Kontakte → Bots. Chatte privat mit ihm oder füge ihn einer Gruppe hinzu, die dir gehört. Dieser Weg nutzt die offizielle Bot-Plattform von QQ, du brauchst also weder ein persönliches QQ-Konto noch zusätzliche Software. QQ entscheidet, wohin der Bot darf. Bis der Bot zertifiziert ist, kann er nur Gruppen beitreten, die seinem Admin gehören, und es gibt keine Sandbox einzurichten. In einer Gruppe sieht er nur Nachrichten, die ihn per @ erwähnen, außer der Gruppeninhaber schaltet im Profil des Bots in dieser Gruppe den Empfang aller Nachrichten ein. Die [Bot-Anleitung von QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) behandelt die Zertifizierung und den Rest auf der Kontoseite.

Wenn ein QR-Code abläuft, fordere einen neuen an. Schlägt ein Download fehl, wiederhole ihn, ohne die Modelleinrichtung noch einmal zu machen. Das Verbinden einer App öffnet dem Charakter nur die Gruppen und Direktnachrichten dieser App; andere Adapter behalten ihre Zulassungslisten. LINE wird nicht angeboten, weil AstrBot LINE-Callbacks nur über sein Dashboard empfängt, das personagent nicht ausführt.

## Beim nächsten Mal

Öffne personagent wieder. Deine Einstellungen bleiben erhalten, und verbundene Apps laufen von selbst weiter. Läuft es bereits, nutzt erneutes Öffnen die laufende Seite. Lass das Startfenster offen, solange du es benutzt. Die von ihm gestarteten Prozesse stoppen mit ihm, egal ob du auf **Beenden** klickst oder das Fenster schließt, und was ein Absturz hinterlassen hat, wird beim nächsten Start beendet.

Wenn eine neuere Version auf PyPI liegt, zeigt die Ansicht **Chat** einen Hinweis mit einem Link zu den Versionshinweisen und dem Update-Befehl für die Art, wie diese Kopie installiert wurde. Eine aus dem Quellcode-ZIP entpackte Kopie bekommt stattdessen einen Link, um den neuen Quellcode von der Release-Seite herunterzuladen. personagent fragt pypi.org höchstens einmal am Tag, und die Anfrage enthält nur seine Versionsnummer. Setze `UPDATE_CHECK_ENABLED=false` in `.env`, um die Prüfung abzuschalten.

Wenn du die Kommandozeile bevorzugst, nutze `personagent start --terminal`, `personagent init --terminal`, `personagent up` oder die Befehle `chat`, `demo` (kein Schlüssel nötig), `run` und `connect`. Sie behalten deine `.env`, deine bearbeitete Persona und die gelernten Erinnerungen. Die [vollständige Anleitung](guide.de.md) behandelt die anderen Plattformen.
