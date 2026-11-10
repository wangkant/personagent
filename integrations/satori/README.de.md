# Satori-Konnektor

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · Deutsch · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Dieser Konnektor verbindet [personagent](https://github.com/wangkant/personagent) mit einem [Satori](https://satori.chat)-Server. Satori ist ein plattformübergreifendes Chat-Protokoll. Ein Server wie [Koishi](https://koishi.chat) (mit seinem `server-satori`-Plugin), Chronocat oder LLOneBot meldet sich bei den Chat-Plattformen an, und ein Client wie dieser empfängt jede Nachricht jeder Anmeldung über einen einzigen Websocket. Ein einziger Konnektor-Prozess bringt die Figur somit auf jede Plattform, für die der Server einen Adapter hat.

Satori und Koishi sind Software von Dritten. personagent benötigt sie nicht für QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK oder Stoat, die es selbst verbindet, und nicht für die Plattformen, die seine lokale Seite über AstrBot einrichtet. Verwenden Sie diesen Konnektor, wenn Sie bereits Koishi betreiben oder eine Plattform benötigen, die nur Koishi erreicht.

Der Konnektor leitet jede erlaubte Nachricht als neutrales Ereignis an `POST /v1/events` des Agenten weiter ([docs/connectors.md](../../docs/connectors.de.md)) und sendet die Antworten über Satori zurück. Er ruft außerdem die Outbox des Agenten ab, sodass geplante Gesprächsanfänge, Nachfragen und Ausreden den Chat erreichen.

[satori-python](https://github.com/RF-Tar-Railt/satori-python) übernimmt die Satori-Seite: den Websocket, die Anmeldeliste und die HTTP-API. Dieser Konnektor übersetzt zwischen Satori und dem Ereignisformat von personagent und verwendet [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py) für das Signieren und die Outbox-Schleife.

## Einrichtung, mit Koishi

1. **Koishi.** Installieren Sie Koishi mit dem Desktop-Launcher oder `npm init koishi@latest`. Fügen Sie in seiner Konsole einen Adapter für Ihre Plattform hinzu und konfigurieren Sie ihn, etwa `adapter-telegram` oder `adapter-discord`, und stellen Sie sicher, dass der Bot online ist. Aktivieren Sie die Plugins `server` und `server-satori`. Koishi stellt Satori dann unter `http://127.0.0.1:5140/satori` bereit. Geben Sie `server-satori` ein `token`, wenn außer diesem Rechner etwas anderes den Port erreichen kann.

   Koishi führt seine übrigen Plugins weiterhin aus. Wenn eines davon ebenfalls Nachrichten beantwortet, etwa ein Chat-Modell oder ein Antwort-Plugin, antwortet es zusätzlich zur Figur, und der Konnektor kann es nicht unterbinden. Deaktivieren Sie dieses Plugin oder nehmen Sie die weitergeleiteten Gespräche davon aus.

2. **Der Agent.** Führen Sie personagent aus (`personagent run`, siehe dessen README). Wenn Konnektor und Agent auf verschiedenen Hosts laufen, setzen Sie `CONNECTOR_TOKEN` in der `.env` des Agenten und stellen Sie den Agenten hinter HTTPS. Setzen Sie das Token, bevor Sie einen Proxy oder Tunnel hinzufügen, auch auf einem einzigen Host.

3. **Der Konnektor.** Der Konnektor ist ein Skript in diesem Repository; er benötigt daher eine Kopie des Repositorys (einen Klon oder das ZIP von GitHub) und eine eigene Python-Umgebung, weil `satori-python` keine Abhängigkeit von personagent ist. In einem Klon, der bereits das `.venv` von personagent enthält, installieren Sie in diese Umgebung:

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   Wenn Sie personagent von PyPI mit pip installiert haben oder mit uvx starten, erstellen Sie ein eigenes venv neben der Kopie:

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   Unter Windows ist der Interpreter `.venv\Scripts\python.exe` oder `connector-venv\Scripts\python.exe`. Kopieren Sie anschließend die Einstellungsdatei:

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   Setzen Sie in `integrations/satori/.env` die URL und das Token des Satori-Servers, die Basis-URL und das `CONNECTOR_TOKEN` des Agenten und die weiterzuleitenden Gespräche (siehe [Zulassungslisten](#zulassungslisten)). Starten Sie dann den Konnektor mit demselben Interpreter:

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE` liest eine andere Einstellungsdatei. Jede Einstellung kann auch als Umgebungsvariable angegeben werden, die Vorrang vor der Datei hat.

4. **Prüfen Sie die Funktion.** Für jeden Bot des Servers zeigt das Log eine Zeile wie `Satori login telegram:7000 is ONLINE`. Erwähnen Sie den Bot in einer weitergeleiteten Gruppe. Das Log des Agenten zeigt den Durchgang, und die Antwort erscheint im Chat. Geschieht nichts, setzen Sie `SATORI_LOG_LEVEL=DEBUG`.

## Einstellungen

| Einstellung | Standard | Bedeutung |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | Der Satori-Server. Ein abschließendes `/v1` ist optional. |
| `SATORI_TOKEN` | | Das Token des Servers (in Koishi `server-satori` → `token`). |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | Die Basis-URL des Agenten. `/v1/events` und `/v1/outbox` werden angehängt. |
| `CONNECTOR_TOKEN` | | Das `CONNECTOR_TOKEN` des Agenten. |
| `SATORI_GROUPS` | | Weiterzuleitende Gruppen, als Kanal- oder Server-IDs, optional `platform:id`. Leer leitet keine weiter, `*` alle. |
| `SATORI_DM_USERS` | | Personen, deren DMs weitergeleitet werden, als Benutzer-IDs, optional `platform:id`. Leer leitet keine weiter, `*` alle. |
| `SATORI_PLATFORMS` | alle | Beschränkt den Konnektor auf diese Satori-Plattformen. |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | Benennt Plattformen um, wie der Agent sie sieht: `satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | Die Outbox des Agenten abholen. |
| `SATORI_CONNECTOR_ID` | aus `SATORI_URL` | Die ID dieses Konnektors beim Agenten. Ändern Sie sie nicht. |
| `SATORI_TIMEOUT_S` | `420` | Wie lange ein Durchgang dauern darf. Halten Sie den Wert über 3 × `LLM_TIMEOUT_S` des Agenten. |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | Öffentliche Bild-URLs im Konnektor herunterladen, statt die URL an den Agenten zu geben. |
| `SATORI_LOG_LEVEL` | `INFO` | |

Die Agenten-URL muss eine Loopback-Adresse sein oder HTTPS mit gesetztem `CONNECTOR_TOKEN`. Sonst weigert sich der Konnektor zu starten. Würde `SATORI_TOKEN` über unverschlüsseltes `http` an einen anderen Host gesendet, protokolliert der Konnektor eine Warnung.

## Zulassungslisten

Der Konnektor lehnt standardmäßig ab. Mit leeren Listen leitet er nichts weiter.

- Eine Gruppe ist ein Satori-Kanal. Sie wird weitergeleitet, wenn ihre Kanal- oder Server-ID in `SATORI_GROUPS` steht. Auf Discord oder KOOK lässt eine Server-ID also jeden Kanal dieses Servers zu, und jeder Kanal bleibt ein eigenes Gespräch.
- Eine DM wird weitergeleitet, wenn die Benutzer-ID des Absenders in `SATORI_DM_USERS` steht.
- Ein Eintrag kann seine Plattform nennen, wie `telegram:-1001234` oder `discord:4242`, und passt dann nur auf dieser Plattform. Ein Eintrag ohne Plattform passt auf jeder.
- `*` leitet jede Gruppe (oder jede DM) weiter und markiert das Ereignis mit `prefiltered: false`. Dann entscheiden `ACCESS_GROUPS` und `ACCESS_DM_USERS` des Agenten, und eine Plattform ohne Einträge dort wird abgelehnt.

Koishis `inspect`-Plugin gibt die Plattform-, Kanal-, Server- und Benutzer-IDs einer Nachricht aus.

## Plattformnamen und QQ

personagent speichert IDs als `<platform>:<id>`, wobei die Plattform die der Satori-Anmeldung ist (`telegram`, `discord`, `onebot` und so weiter). Die Log-Zeile aus Schritt 4 zeigt sie. Zwei Fälle sind besonders:

- **QQ über OneBot** (Koishis `adapter-onebot`, dahinter NapCat oder LLOneBot) nutzt QQ-Nummern als IDs. Um zu behalten, was der Agent bei einer bestehenden QQ-Bereitstellung gelernt hat, fügen Sie die Plattform zu `CONNECTOR_QQ_PLATFORMS` des Agenten hinzu (`CONNECTOR_QQ_PLATFORMS=onebot`). Ihre IDs werden dann ohne Präfix gespeichert, wie QQ-Nummern von NapCat, und die QQ-Einträge von `ACCESS_GROUPS` und `ACCESS_DM_USERS` gelten für sie. Tun Sie dies nur für eine Plattform, deren IDs tatsächlich QQ-Nummern sind.
- **Die offizielle QQ-Bot-API** (Koishis `adapter-qq`) nennt ihre Plattform `qq`, aber ihre IDs sind OpenIDs, keine QQ-Nummern. Der Konnektor benennt die Plattform in `qqbot` um. `SATORI_PLATFORM_NAMES` überschreibt die Umbenennung. personagent kann offizielle QQ-Bots auch selbst verbinden, ohne Koishi.

## Was funktioniert

| Funktion | Status |
|---|---|
| Gruppenchats und DMs | Ja. Eine DM ist ein `DIRECT`-Kanal oder eine Nachricht ohne Server. |
| Anruferkennung (`addressed`) | Ein `<at>` des Bots (per ID oder per Bot-Name, wenn der Server keine ID liefert) und eine Antwort auf eine Nachricht des Bots. `@all` zählt als Text, nicht als Erwähnung. |
| Zitierte Nachrichten | Der zitierte Text, Absender und ID, aus einem `<quote>`-Element oder aus `message.quote`. |
| Eingehende Bilder | `data:`- und `internal:`-Bilder und Bilder auf dem Satori-Server werden eingebettet. Öffentliche URLs werden weitergegeben, damit der Agent sie abruft. URLs aus privaten Netzen werden als `(sent an image)` beschrieben. Höchstens 4 Downloads pro Nachricht, je 4 MB. |
| Sticker und Emoji | `<emoji>` und QQs `<face>` kommen als Emoji an, und die Figur weiß, dass sie sie nicht sehen kann. |
| Sprache, Video, Dateien | In Worten beschrieben: `(sent a voice message)`, `(sent a video)`, `(sent a file: deck.pdf)`. |
| Antworten | Text und Bilder als `data:`-URIs, jeweils als eigene Nachricht mit kurzem Abstand. In Gruppen wird eine vom Agenten verlangte Erwähnung zu einem `<at>`. |
| Plattformen mit passiver Antwort | Antworten tragen den `referrer` des Ereignisses, den die offizielle QQ-Bot-API benötigt, um auf eine Nachricht zu antworten. |
| Outbox | Geplante Gesprächsanfänge, Nachfragen und Ausreden gehen über die Anmeldung, die das Gespräch empfangen hat, in den Kanal. Der Konnektor signiert jedes Antwort-Handle mit einem aus `SATORI_TOKEN` und `CONNECTOR_TOKEN` abgeleiteten Schlüssel und sendet nur an Handles, die er signiert hat. Nachdem Sie eines der Tokens geändert haben, ist ein Gespräch wieder erreichbar, sobald es eine Nachricht gesendet hat. Ein Agent mit `CONNECTOR_OUTBOX_ENABLED=false` antwortet 404, und der Konnektor versucht es alle 10 Minuten erneut. |
| Tippanzeige | Nein. Satori hat keine Tipp-API. |
| `owned` | Beachtet: Der Konnektor sendet sonst nichts. Andere Koishi-Plugins kann er nicht stoppen (siehe Schritt 1). |

Plattformregeln gelten weiterhin. Die offizielle QQ-Bot-API zum Beispiel beschränkt streng, welche Nachrichten ein Bot unaufgefordert senden darf, daher können Outbox-Zustellungen dort als `failed` zurückkommen.

## Tests

`tests/test_satori_connector.py` läuft ohne satori-python und ohne Netzwerk. Es simuliert die Elementobjekte, das Konto und den Agenten.
