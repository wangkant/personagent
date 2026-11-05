# Matrix-Konnektor

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · Deutsch · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Dieser Konnektor bringt [personagent](https://github.com/wangkant/personagent) in Matrix-Räume und über [mautrix-Brücken](https://docs.mau.fi/bridges/) auf WhatsApp, Signal, Messenger, Instagram, Google Messages und andere Netzwerke. Matrix und die Brücken sind Software von Dritten, die du selbst betreibst. personagent braucht sie nicht für die Plattformen, die es von seiner lokalen Seite aus verbindet.

Der Konnektor ist ein kleiner eigenständiger Prozess auf Basis von [matrix-nio](https://github.com/matrix-nio/matrix-nio), das Ende-zu-Ende-Verschlüsselung ohne libolm unterstützt. Er meldet sich als gewöhnlicher Matrix-Benutzer bei einem Homeserver an, leitet jede erlaubte Raumnachricht als plattformneutrales Ereignis an `POST /v1/events` des Agenten weiter ([docs/connectors.md](../../docs/connectors.de.md)) und postet die Antworten des Agenten zurück in den Raum. Er fragt auch die Outbox des Agenten ab, sodass geplante Gesprächsanfänge, Nachfragen und Ausreden ebenfalls Matrix erreichen.

## Was er tut

Eingehend, für jede Nachricht in einem erlaubten Raum:

- Das Ereignis nutzt die Plattform `matrix` und rohe Matrix-IDs, also speichert der Agent `matrix:@alex:example.org` und `matrix:!room:example.org`.
- Ein Raum zählt als Direktchat, wenn das `m.direct` des Bots ihn listet oder wenn er außer dem Bot und den Benutzern in `MATRIX_IGNORE_USERS` genau ein Mitglied hat. Ein Direktchat wird nach der Person geführt, eine Gruppe nach dem Raum. Ein per ID in `MATRIX_GROUPS` genannter Raum ist immer eine Gruppe.
- `addressed` ist wahr, wenn die Nachricht den Bot erwähnt oder auf eine seiner Nachrichten antwortet. Eine Erwähnung ist `m.mentions` oder, von Clients, die zu alt sind, um `m.mentions` zu senden, eine Pille oder die Benutzer-ID des Bots im Text.
- Eine Antwort trägt Absender und Text der zitierten Nachricht. Der Konnektor nimmt sie aus einem Cache jüngster Ereignisse oder holt das übergeordnete Ereignis. Er entfernt den Antwort-Fallback, den ältere Clients voranstellen (`> <@alex:example.org> ...`), sodass der Agent nie die Worte eines anderen als die des Absenders liest.
- Bilder und Sticker bis 4 MB werden heruntergeladen, in verschlüsselten Räumen entschlüsselt und als Bytes an den Agenten geschickt. Sprachnachrichten, Videos und Dateien werden in Worten beschrieben.
- Die Nachrichten eines Raums erreichen den Agenten in der Reihenfolge, in der sie gesendet wurden. Eine nach einem Bild gesendete Nachricht wartet, bis das Bild heruntergeladen ist. Der Agent kann trotzdem mehrere Züge gleichzeitig bearbeiten.
- Der Zeitstempel ist der `origin_server_ts` des Homeservers.
- Der Konnektor überspringt die eigenen Nachrichten des Bots, `m.notice`-Nachrichten (der Typ, den Bots senden), Bearbeitungen, Reaktionen, Nachrichten von `MATRIX_IGNORE_USERS`, den Rückstand, den die erste Synchronisierung beim Start liefert, und alles, was älter als `MATRIX_MAX_EVENT_AGE_S` ist, etwa Verlauf, den eine Brücke in einen neuen Raum nachträgt.

Ausgehend:

- Textantworten sind `m.text`. Wenn der Agent in einer Gruppe jemanden erwähnen will, beginnt die Antwort mit einer Pille und listet diese Person in `m.mentions`. Jede andere Antwort trägt ein leeres `m.mentions`, sodass kein Client einen Namen im Text zu einer Benachrichtigung macht.
- Bildantworten werden hochgeladen und in verschlüsselten Räumen verschlüsselt.
- Während der Agent an einem Zug arbeitet, läuft eine Tippanzeige.
- Eine Nachricht in einem Thread wird in diesem Thread beantwortet.
- Sobald der Agent das Gespräch übernimmt, markiert der Bot die Nachricht als gelesen (`MATRIX_READ_RECEIPTS_ENABLED`). Über eine Brücke erscheint das als Lesehäkchen im anderen Netzwerk.
- Outbox-Zustellungen gehen in den Raum, aus dem das Gespräch zuletzt kam. Das `reply_handle` des Ereignisses ist die Raum-ID.

## Installation

Du brauchst ein laufendes personagent und ein Matrix-Konto für den Bot. Erstelle ein eigenes Konto, statt eines mit einer Person zu teilen.

Der Konnektor ist ein Skript in diesem Repository, also braucht er eine Kopie des Repositorys (einen Klon oder das ZIP von GitHub) und eine eigene Python-Umgebung, weil `matrix-nio` keine Abhängigkeit von personagent ist. In einem Klon, der schon das `.venv` von personagent hat, installiere in diese Umgebung:

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

Wenn du personagent von PyPI mit pip installiert hast oder mit uvx startest, erstelle ein eigenes venv neben der Kopie:

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

Unter Windows ist der Interpreter `.venv\Scripts\python.exe` oder `connector-venv\Scripts\python.exe`. Kopiere als Nächstes die Einstellungsdatei:

```bash
cp integrations/matrix/.env.example integrations/matrix/.env
```

Bearbeite `integrations/matrix/.env`:

```ini
MATRIX_URL=https://matrix.example.org
MATRIX_USER_ID=@nova:example.org
MATRIX_PASSWORD=...
MATRIX_GROUPS=!AbCdEf:example.org
MATRIX_DM_USERS=@alex:example.org
PERSONAGENT_URL=http://127.0.0.1:8080
```

Starte dann den Konnektor neben dem Agenten, mit demselben Interpreter:

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

Lade den Bot in einen Raum aus `MATRIX_GROUPS` ein, und er tritt bei. In Element steht die Raum-ID in den Raumeinstellungen unter Erweitert.

### Anmelden

Die Passwort-Anmeldung ist der einfachste Einstieg. Der Konnektor speichert die erhaltene Sitzung (Benutzer-ID, Geräte-ID und Zugriffstoken) in `MATRIX_STORE_DIR/session.json` und verwendet sie beim nächsten Start wieder, also erzeugt ein Neustart kein neues Gerät. Lösche die Datei, um dich neu anzumelden.

Um stattdessen ein vorhandenes Zugriffstoken zu nutzen, setze `MATRIX_ACCESS_TOKEN`. Der Konnektor fragt den Homeserver, zu welchem Konto das Token gehört. Nutze nicht das Token einer Sitzung, die du selbst verwendest, denn wenn du dich dort abmeldest, wird auch der Bot abgemeldet.

Wenn der Homeserver den Bot abmeldet (`M_UNKNOWN_TOKEN`), stoppt der Konnektor mit einem Fehler, der das sagt. Nach einer Passwort-Anmeldung meldet ein erneuter Start ihn wieder an. Bei `MATRIX_ACCESS_TOKEN` setze zuerst ein neues Token. Jede andere fehlgeschlagene Synchronisierung wird nach einer Wartezeit wiederholt, die sich bis auf eine Minute verdoppelt.

### Wo der Agent laufen kann

Das Protokoll setzt die Regel. `PERSONAGENT_URL` muss eine Loopback-Adresse sein oder HTTPS mit `CONNECTOR_TOKEN`, gesetzt auf das `CONNECTOR_TOKEN` des Agenten. Sonst weigert sich der Konnektor zu starten. Setze das Token auf beiden Seiten, bevor du einen Proxy oder Tunnel vor den Agenten stellst, auch auf einem einzigen Host.

## Einstellungen

[.env.example](.env.example) listet jede Einstellung. Listen sind kommagetrennt und akzeptieren Globs, also passt `@*:example.org` auf einen ganzen Server. Eine leere Liste antwortet niemandem. Ein einzelnes `*` passt auf alle und markiert das Ereignis mit `prefiltered: false`. Dann entscheiden allein `ACCESS_GROUPS` / `ACCESS_DM_USERS` des Agenten, und eine Plattform ohne Einträge dort wird abgelehnt.

| Einstellung | Bedeutung |
|---|---|
| `MATRIX_GROUPS` | Gruppenräume, in denen geantwortet wird, per Raum-ID. `*` bedeutet jeden Raum, dem der Bot beigetreten ist. |
| `MATRIX_DM_USERS` | Personen, die im Direktchat mit dem Bot sprechen dürfen. `*` bedeutet alle. |
| `MATRIX_INVITE_FROM` | Benutzer, deren Einladungen der Bot annimmt. Einladungen in Räume aus `MATRIX_GROUPS` und Direktchat-Einladungen von `MATRIX_DM_USERS` werden immer angenommen. Andere Einladungen bleiben offen. |
| `MATRIX_IGNORE_USERS` | Bekommen nie eine Antwort und zählen nicht als Mitglieder, wenn der Konnektor einen Direktchat von einer Gruppe unterscheidet. |
| `MATRIX_E2EE_ENABLED` | Ende-zu-Ende-Verschlüsselung. Siehe unten. |
| `MATRIX_TIMEOUT_S` | Wie lange ein Zug dauern darf. Halte den Wert über `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` des Agenten. |
| `MATRIX_OUTBOX_ENABLED` | Die Outbox des Agenten abfragen. |

## Brücken: WhatsApp, Signal, Messenger, Instagram und mehr

Eine mautrix-Brücke meldet sich bei einem anderen Netzwerk als Konto dieses Netzwerks an und spiegelt seine Chats in Matrix-Räume, sogenannte Portale. Jeder auf der anderen Seite erscheint in Matrix als Geisterbenutzer wie `@whatsapp_4912345:example.org`. Wenn das Matrix-Konto des Bots das ist, das bei der Brücke angemeldet ist, lebt die Persona in diesem Netzwerk. Ein WhatsApp-Kontakt schreibt an die Nummer der Persona, die Brücke postet die Nachricht in einen Portalraum, dieser Konnektor leitet sie weiter, und die Antwort nimmt denselben Weg zurück.

| Netzwerk | Brücke |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger, Instagram-DMs | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages (RCS und SMS über ein Android-Telefon) | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice, LinkedIn, Twitter/X-DMs, Bluesky-DMs, Google Chat, Zulip, IRC, iMessage | Die anderen [mautrix-Brücken](https://github.com/mautrix) |
| Telegram, Discord, Slack | mautrix-Brücken gibt es, aber diese Netzwerke haben offizielle Bot-APIs. personagent verbindet Telegram und Discord selbst und Slack über das AstrBot, das seine lokale Seite betreibt. |

So richtest du eine ein:

1. Betreibe einen Homeserver, den du kontrollierst (Synapse oder einen anderen Server, der Anwendungsdienste unterstützt), und installiere die Brücke nach [ihrer Dokumentation](https://docs.mau.fi/bridges/). Gib dem Konto des Bots die Berechtigungsstufe `user` in den `permissions` der Brücke.
2. Melde dich als Bot in Element an, öffne einen Chat mit dem Brücken-Bot (zum Beispiel `@whatsappbot:example.org`) und sende `login`. Verknüpfe das Netzwerkkonto, das die Persona nutzen wird. Für WhatsApp, Signal und Google Messages scanne den QR-Code mit dem Telefon der Persona. Für Messenger und Instagram gib die Meta-Anmeldung an. Siehe [Brücken nutzen](https://docs.mau.fi/bridges/general/using-bridges.html).
3. Lass den Konnektor den Portalen beitreten und halte die eigenen Nachrichten der Brücke heraus:

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   Der zweite Eintrag in `MATRIX_IGNORE_USERS` ist der Brücken-Geist der eigenen Nummer der Persona. Ohne [Double Puppeting](https://docs.mau.fi/bridges/general/double-puppeting.html) erreicht eine auf dem Telefon der Persona getippte Nachricht Matrix von diesem Geist, und der Bot würde sich selbst antworten. `MATRIX_GROUPS=*` leitet jedes Gruppenportal weiter, in dem der Bot ist, und personagent antwortet dann nur in den Räumen, die sein `ACCESS_GROUPS` als `matrix:!room:server` listet. Liste hier Raum-IDs, um die Räume stattdessen im Konnektor zu wählen.

### Puppeting

- Die Brücke ist ein inoffizieller Client des Netzwerks, angemeldet als normales Benutzerkonto (ein verknüpftes Gerät oder eine Websitzung). Sie nutzt keine Bot-API, und nichts im Netzwerk kennzeichnet das Konto als Bot.
- Die Persona braucht ein eigenes Konto, meist mit eigener Telefonnummer, und das Telefon muss erreichbar bleiben. WhatsApp trennt verknüpfte Geräte, sobald das Telefon etwa zwei Wochen offline war, und Google Messages funktioniert nur, solange das Android-Telefon online ist.
- In Gruppenchats sieht das Konto der Persona aus wie jedes andere Mitglied. Sag den Leuten, dass sie mit einem Bot sprechen.
- Reaktionen, Bearbeitungen, Löschungen, Umfragen und Anrufe werden nicht an den Agenten weitergeleitet.

### Bedingungen der einzelnen Netzwerke

Lies die Bedingungen jedes Netzwerks, bevor du es verbindest.

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) zählt automatisches Senden von Nachrichten zu den unzulässigen Kommunikationen, verbietet nicht autorisierte nicht persönliche Nutzung und kann Konten sperren, die eines von beidem tun. Sein zugelassener Weg zur Automatisierung ist die WhatsApp Business Platform, die eine Brücke nicht nutzt.
- [Signal](https://signal.org/legal/) führt automatisches Senden von Nachrichten ebenfalls als unzulässig.
- [Facebook](https://www.facebook.com/terms.php) und [Instagram](https://help.instagram.com/581066165581870) verbieten automatisierten Zugriff ohne Metas Erlaubnis, und Meta kann ein Konto sperren, das sich von einem unbekannten Client anmeldet.
- Google Messages fällt unter die [Bedingungen von Google](https://policies.google.com/terms) und die deines Mobilfunkanbieters für SMS und RCS, die automatisierte Nachrichten berechnen oder einschränken können.

Nutze ein eigenes Konto, dessen Verlust du verkraften kannst, nur in Gesprächen, in denen die Leute wissen, dass sie mit einem Bot sprechen, und lies [DISCLAIMER.md](../../docs/DISCLAIMER.de.md).

## Ende-zu-Ende-Verschlüsselung

Mit `MATRIX_E2EE_ENABLED=false` (Standard) liest der Bot nur unverschlüsselte Räume. In einem verschlüsselten Raum protokolliert er, dass er die Nachricht nicht entschlüsseln kann, und sendet dort nie eine Klartextantwort.

Mit `MATRIX_E2EE_ENABLED=true`:

- `MATRIX_STORE_DIR` (standardmäßig `runtime/` neben dem Skript, von git ignoriert) enthält die Schlüssel des Geräts und das Synchronisierungstoken. Bewahre dieses Verzeichnis auf. Geht es verloren, wird der Bot zu einem neuen Gerät, das nichts lesen kann, was vor diesem Zeitpunkt verschlüsselt wurde.
- Das Gerät muss über Neustarts hinweg dasselbe bleiben. Eine Passwort-Anmeldung behält es durch die gespeicherte Sitzung. Bei einem Zugriffstoken setze `MATRIX_DEVICE_ID` auf das Gerät des Tokens.
- Der Bot teilt seine Schlüssel mit jedem Gerät im Raum, verifiziert oder nicht. Er kann sich nicht interaktiv verifizieren, also sehen andere sein Gerät als nicht verifiziert. Er hat weder Schlüsselsicherung noch Cross-Signing.
- Eine Nachricht, deren Schlüssel nicht angekommen ist, wird protokolliert und übersprungen, nicht wiederholt.
- Eine mautrix-Brücke kann ihre Portale verschlüsseln ([Ende-zu-Brücke-Verschlüsselung](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)). Die Brücke hält diese Schlüssel auf deinem Server, also endet der Schutz dort, und das andere Netzwerk trägt die Nachricht unter seiner eigenen Verschlüsselung. Wenn deine Brücke Portale verschlüsselt, schalte `MATRIX_E2EE_ENABLED` ein.

## Tests

`tests/test_matrix_connector.py` simuliert den Matrix-Client und den Agenten, läuft also ohne matrix-nio und ohne Netzwerk:

```bash
python -m pytest tests/test_matrix_connector.py
```
