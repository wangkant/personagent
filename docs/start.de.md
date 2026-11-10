# Erste Schritte mit personagent

[English](start.md) · [简体中文](start.zh-CN.md) · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · [Français](start.fr.md) · Deutsch · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · [Vollständige Anleitung](guide.de.md)

## Öffnen

Installieren Sie personagent von PyPI und öffnen Sie es:

```sh
python -m pip install personagent
personagent
```

Mit [uv](https://docs.astral.sh/uv/) startet `uvx personagent` das Programm ohne gesonderten Installationsschritt.

Unter Windows öffnet sich die Seite in einem eigenen Fenster. Unter macOS und Linux öffnet sie sich in Ihrem Browser; mit `pip install "personagent[app]"` erhält sie auch dort ein eigenes Fenster.

Ein Programmierassistent kann die Einrichtung für Sie übernehmen: Bitten Sie ihn, [setup-for-agents.md](setup-for-agents.md) zu lesen und personagent einzurichten.

Unter Windows können Sie auch das Quellcode-ZIP herunterladen, entpacken und `start.bat` doppelklicken. Das Skript legt im Ordner eine eigene Python-Umgebung an und öffnet dieselbe Seite. Beim ersten Start legt es außerdem ein personagent-Symbol auf Ihrem Desktop und im Startmenü an.

Um personagent aus einem Klon zu starten, richten Sie eine eigene virtuelle Umgebung ein: `python -m venv .venv`, dann `.venv/bin/python -m pip install -e .` und `.venv/bin/python -m persona_agent`. Unter Windows lautet der Interpreter `.venv\Scripts\python.exe`; alternativ doppelklicken Sie `start.bat`.

## Schlüssel eintragen und chatten

Wählen Sie einen Modelldienst, fügen Sie dessen API-Schlüssel ein und klicken Sie auf **Prüfen & Chat starten**. Voreingestellt sind die kostenlosen Modelle von OpenRouter und die Figur „Einfühlsamer Zuhörer“. Der Schlüssel ist kostenlos, das Limit beträgt 50 Anfragen pro Tag. **Erweiterte Einstellungen** enthält den Modellnamen und die API-Adresse, **Namen oder Persönlichkeit wählen** den Namen und die Persönlichkeit der Figur.

Der Schlüssel bleibt auf Ihrem Computer; klicken Sie auf **Anzeigen**, um ihn zu überprüfen. Chatnachrichten werden an den gewählten Modelldienst gesendet und zu dessen üblichen Preisen abgerechnet.

Ihre Figur antwortet auf der Seite. Ihre Einstellungen werden gespeichert, sodass der nächste Start direkt in den Chat führt.

Nach der Einrichtung enthält **Figur & Einstellungen** ein Feld **Persona** mit dem Text, auf dem die Figur beruht. Formulieren Sie dort um, wer sie ist und wie sie spricht, und klicken Sie auf **Persona speichern**. Die Änderung gilt sofort, und was die Figur gelernt hat, bleibt erhalten.

Darunter schaltet **Weitere Funktionen** die Websuche, die Bilderkennung und eigene Gesprächsanstöße ein. Die Suche verwendet standardmäßig DuckDuckGo; mit einem Tavily-Schlüssel arbeitet sie zuverlässiger. **Erweiterte Einstellungen** darunter enthält die Einstellungen, die bisher nur in `.env` verfügbar waren. Solange Sie keine App verbunden haben, zeigt die Ansicht **Chat** eine kurze Leiste **Erste Schritte**.

Zwei weitere Ansichten kommen ohne verbundene App aus. **Übung** spielt eine vorgefertigte Demo ab und stellt einen Übungsgruppenchat bereit, in dem Sie nachvollziehen können, warum die Figur antwortet oder schweigt. **App** prüft alle Dienste, auf die die Figur angewiesen ist, zeigt die Protokolle an und bündelt Updates, Sicherungen und das Desktopsymbol.

## In andere Apps mitnehmen

1. Klicken Sie auf **Apps verbinden** und wählen Sie eine App. Sobald sie verbunden ist, antwortet Ihre Figur in den Gruppenchats und Direktnachrichten dieser App.
   - **Per Scan verbinden**: QQ und persönliches WeChat. Klicken Sie auf **QR-Code abrufen** und bestätigen Sie auf Ihrem Smartphone.
     - QQ: Scannen Sie mit der mobilen QQ-App. QQ erstellt einen Bot oder lässt Sie einen vorhandenen auswählen, und personagent ruft dessen Schlüssel ab. Wenn Sie den Bot selbst auf der [Bot-Seite von QQ](https://q.qq.com/qqbot/openclaw/login.html) erstellt haben, klicken Sie auf **Stattdessen Werte einfügen** und geben Sie seine AppID und sein AppSecret ein.
     - WeChat: Scannen Sie mit WeChat. Der Bot chattet nur in Einzelgesprächen, da WeChat Gruppennachrichten nicht an diese Bots weiterleitet.
   - **Ein bis zwei Werte einfügen**: Telegram (ein Token von @BotFather), Discord (ein Bot-Token, mit aktiviertem Message Content Intent), KOOK, Feishu, DingTalk, Slack, WeCom-KI-Bot, Mattermost, Misskey, Matrix, Twitch, IRC, Zulip, VK und Stoat. Die Seite gibt an, welche Werte Sie aus der Konsole der App kopieren müssen. Für alles Weitere gelten Standardwerte. Bei Twitch bestätigen Sie zusätzlich eine Anmeldung über einen Link.
   - **Erweitert**: WeCom-Apps, offizielle WeChat-Konten und QQ-Webhooks benötigen eine öffentliche Adresse, die an ihren Callback-Port weiterleitet. OneBot v11 (NapCat) und Satori erfordern zusätzliche Software, die auf diesem Computer läuft.
2. personagent verbindet QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK und Stoat selbst. Die übrigen Apps laufen über AstrBot, eine Brücke eines Drittanbieters. Wenn Sie eine davon zum ersten Mal verbinden, lädt personagent AstrBot mit einer separaten Python-3.12-Laufzeit herunter; lassen Sie die Seite daher geöffnet, bis der Vorgang abgeschlossen ist. AstrBot läuft anschließend im Hintergrund, ohne ein Dashboard, bei dem man sich anmelden müsste.
3. personagent prüft die Zugangsdaten bei der App, bevor es sie speichert. Lehnt die App sie ab, teilt Ihnen die Seite dies mit, und es wird nichts gespeichert.
4. Verbundene Apps werden oben unter **Apps verbinden** aufgeführt; dort können Sie sie neu einrichten oder trennen.

Um einen QQ-Bot zu finden, öffnen Sie die mobile QQ-App und wechseln Sie zu Kontakte → Bots. Chatten Sie privat mit ihm oder fügen Sie ihn einer Gruppe hinzu, deren Inhaber Sie sind. Dieser Weg nutzt die offizielle Bot-Plattform von QQ; Sie benötigen daher weder ein persönliches QQ-Konto noch zusätzliche Software. QQ legt fest, wo der Bot eingesetzt werden darf. Bis der Bot zertifiziert ist, kann er nur Gruppen beitreten, deren Inhaber sein Administrator ist, und es ist keine Sandbox einzurichten. In einer Gruppe sieht er nur Nachrichten, die ihn per @ erwähnen, es sei denn, der Gruppeninhaber aktiviert im Profil des Bots in dieser Gruppe den Empfang aller Nachrichten. Die [Bot-Anleitung von QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) behandelt die Zertifizierung und die übrigen Kontoeinstellungen.

Wenn ein QR-Code abläuft, fordern Sie einen neuen an. Schlägt ein Download fehl, wiederholen Sie ihn, ohne die Modelleinrichtung erneut durchzuführen. Das Verbinden einer App gibt der Figur nur die Gruppen und Direktnachrichten dieser App frei; andere Adapter behalten ihre bestehenden Zulassungslisten. LINE wird nicht angeboten, da AstrBot LINE-Callbacks nur über sein Dashboard empfängt, das personagent nicht ausführt.

## Beim nächsten Mal

Öffnen Sie personagent erneut. Ihre Einstellungen bleiben erhalten, und verbundene Apps setzen ihren Betrieb selbstständig fort. Läuft personagent bereits, holt erneutes Öffnen sein Fenster wieder in den Vordergrund. Lassen Sie es geöffnet, solange Sie es verwenden: Die von ihm gestarteten Prozesse werden mit ihm beendet, unabhängig davon, ob Sie auf **Beenden** klicken oder das Fenster schließen, und was ein Absturz hinterlassen hat, wird beim nächsten Start beendet. Unter Windows legt `personagent shortcut` ein Symbol auf Ihrem Desktop und im Startmenü an, das personagent ohne Terminal öffnet. Ebenfalls unter Windows können Sie mit **Im Hintergrund ausführen** in der Ansicht **App** festlegen, dass personagent nach dem Schließen des Fensters hinter einem Symbol im Infobereich weiterläuft; die Figur antwortet dann weiterhin.

Wenn auf PyPI eine neuere Version verfügbar ist, zeigt die Ansicht **Chat** einen Hinweis mit einem Link zu den Versionshinweisen und dem Update-Befehl für die Installationsart dieser Kopie. Eine aus dem Quellcode-ZIP entpackte Kopie erhält stattdessen einen Link, über den der neue Quellcode von der Release-Seite heruntergeladen werden kann. Bei den meisten Installationen installiert **Aktualisieren und neu öffnen** in der Ansicht **App** das Update. personagent fragt pypi.org höchstens einmal täglich ab, und die Anfrage enthält nur die eigene Versionsnummer. Setzen Sie `UPDATE_CHECK_ENABLED=false` in `.env`, um die Prüfung zu deaktivieren.

Wenn Sie die Kommandozeile bevorzugen, verwenden Sie `personagent start --terminal`, `personagent init --terminal`, `personagent up` oder die Befehle `chat`, `demo` (kein Schlüssel erforderlich), `run` und `connect`. Sie übernehmen Ihre bestehende `.env`, Ihre bearbeitete Persona und die gelernten Erinnerungen. Die [vollständige Anleitung](guide.de.md) behandelt die übrigen Plattformen.
