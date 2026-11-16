# personagent bereitstellen

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · [繁體中文](deploy.zh-TW.md) · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · Deutsch · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

Der [Schnellstart](start.de.md) und das [Benutzerhandbuch](guide.de.md) führen Sie bis zum ersten Chat. Sie behandeln die Installation, den [personagent-Ordner](guide.de.md#installation-und-der-personagent-ordner), die Einrichtung auf der lokalen Seite und das Verbinden einer Plattform. Dieser Leitfaden behandelt, was ein dauerhafter Betrieb erfordert und was Sie prüfen sollten, wenn der Bot verstummt.

## Die kürzeste Konfiguration, die funktioniert

Die lokale Seite (`personagent`, oder `personagent init --terminal` für den Terminal-Assistenten) prüft den Schlüssel mit einer kleinen Anfrage und schreibt dann `.env` in den personagent-Ordner. Zum Chatten ist ein Schlüssel erforderlich, und `.env.example` ist auf die kostenlosen Modelle von OpenRouter voreingestellt:

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

Diese beiden Zeilen sind nötig: Eine `.env`, die nur den Schlüssel setzt, verwendet die Vorgaben des Codes, `https://api.deepseek.com` und `deepseek-flash` von DeepSeek, nicht OpenRouter. Sie können sie auf jeden OpenAI-kompatiblen Endpunkt richten, gehostet oder lokal (Ollama, llama.cpp). Geben Sie die API-Adresse so ein, wie der Anbieter sie dokumentiert, entweder als Stammadresse oder als versionierte Basis wie `.../v1` oder `.../api/paas/v4`. Solange Sie keine `persona.txt` angelegt haben, wird die mitgelieferte `data/persona.example.<lang>.txt` verwendet. Solange `PERSONA_NAME` nicht gesetzt ist (die Einrichtung setzt den Wert), heißt die Figur „bot“.

Die Seite schreibt außerdem `PERSONA_NAME`, `AGENT_LANG` und ein `CONNECTOR_TOKEN`. Von der Seite verbundene Plattformen benötigen keine weiteren Einträge in `.env`. Ihre Zugangsdaten werden in `<home>/platforms/` gespeichert: `direct.json` enthält die Plattformen, die personagent selbst verbindet, und das verwaltete AstrBot führt die übrigen in seiner eigenen Konfiguration. Optionale Ergänzungen:

```
ADMIN_IDS=telegram:12345             # the admin's accounts, <platform>:<id>
# QQ through NapCat (OneBot) only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

Schlüssel verbleiben auf diesem Rechner. Der gewählte Modellanbieter erhält die Gespräche. Alles andere in `.env.example` hat einen funktionierenden Standardwert. `SERVER_HOST` und `SERVER_PORT` sind `127.0.0.1:8080`, `QQ_ONEBOT_URL` ist leer (kein NapCat-HTTP-Server), und ein leeres `ACCESS_GROUPS` überlässt alle Gruppen dem Konnektor.

## Ausführen

`personagent` öffnet die lokale Seite. Solange die Seite geöffnet ist, laufen der Agent, der Prozess für die direkt verbundenen Plattformen und, falls installiert, das verwaltete AstrBot. Ein erneuter Aufruf von `personagent` verwendet eine bereits geöffnete Seite wieder. `personagent up` startet dieselben Prozesse ohne Browser.

In beiden Fällen werden diese Prozesse mit dem Hauptprozess beendet, unabhängig davon, wie dieser endet. Was ein früherer, abgestürzter Lauf hinterlassen hat, wird beim nächsten Start beendet. Jeder Prozess schreibt sein Log nach `<home>/runtime/desktop/` (`agent.log`, `direct.log`, `astrbot.log`).

Die lokale Seite und `personagent up` fragen pypi.org höchstens einmal täglich ab, ob eine neuere Version von personagent erschienen ist. Ist dies der Fall, zeigen die Ansicht **Chat** und das Terminal den Befehl an, der diese Kopie aktualisiert. Die Anfrage enthält nur die Versionsnummer, und `UPDATE_CHECK_ENABLED=false` deaktiviert die Prüfung.

`personagent run` startet nur den Agenten, wie [Den Dienst ausführen](guide.de.md#den-dienst-ausführen) beschreibt. Verwenden Sie diesen Befehl, wenn Ihre eigenen Konnektoren (ein AstrBot, das Sie betreiben, Satori, Matrix) mit dem Agenten kommunizieren. `personagent doctor` prüft die Einstellungen und testet jeden vorgelagerten Dienst.

**In 1.0 umbenannte Einstellungen.** Solange ein von 1.0 abgeschaffter Einstellungsname noch gesetzt ist, bricht der Start mit Exit-Code 2 ab und listet jeden Namen als `OLD -> NEW` auf. `personagent doctor --fix` benennt sie in `<home>/.env` um. Dabei bleiben Werte und Kommentare erhalten; der Befehl speichert die alte Datei als `.env.bak` und kommentiert eine alte Zeile aus, deren neuer Name schon gesetzt ist. Ein abgeschaffter Name, der in der Umgebung statt in `.env` gesetzt ist, muss dort umbenannt werden, wo er gesetzt ist. `personagent doctor` endet mit dem Exit-Code 1, solange solche Namen vorhanden sind, und `--json` listet sie unter `retired_settings` auf. `HOST`, `PORT` und `LOG_FILE` zählen nur, wenn sie in `.env` stehen.

### Aktivität

[Aktivität](guide.de.md#aktivität) ist eine Ansicht der lokalen Seite. Sie erfordert keine zusätzliche Installation, lädt nichts aus dem Internet und zeigt nie Schlüssel oder Tokens. Sie liest die JSON-API des Agentendienstes, den die lokale Seite gestartet hat. Wird nur `personagent run` ausgeführt, lesen Sie das Protokoll des Dienstes und verwenden Sie stattdessen `personagent learned` und `personagent memory`. `DASHBOARD_ENABLED=false` deaktiviert die API. Die Ansicht weist dann darauf hin, und `personagent doctor` gibt `activity: off (...)` aus.

Die API liegt unter `/api/dashboard/` auf dem Agentendienst:

- `GET conversations` und `GET conversation?id=<chat id>` lesen die dem Dienst bekannten Chats und einen Chat im Detail. Jeder Chat in `conversations` enthält `learned`, `observing` (die Anzahl der Einträge in Beobachtung) und `latest` (wann zuletzt etwas übernommen wurde). `conversation` liefert die Listen `learned` und `observing`. Ein Eintrag in Beobachtung enthält `standing` (seine Stufe, was ihm noch fehlt, die Begründung der Figur und das Datum, an dem er zurückgestellt wird); ein übernommener Eintrag enthält `by` (`reactions`, `character` oder `person`) und `why`. Außerdem liefert es, was sich der Chat merkt: `memories`, `core_note` und `core_at`, `thread`, `episodes`, `removed` und `memory_status`.
- `POST candidates/<id>/promote`, `replace`, `reject`, `rollback` und `restore` sind optionale Aktionen einer Person in Bezug auf das, was er gelernt hat. Jede geht in dasselbe Lernprotokoll wie `personagent learned`, mit dem Akteur `dashboard`. `restore` holt zurück, was die Figur oder die Frist zurückgestellt hat und was die Figur oder eine Regel rückgängig gemacht hat; was eine Person rückgängig gemacht oder zurückgestellt hat und was eine Inhaltsregel verworfen hat, bleibt, wie es ist. `promote` holt keinen Eintrag zurück, der rückgängig gemacht wurde.
- `POST memory/forget` mit dem Body `{"conv": "<chat id>", "kind": "note", "id": "<id>"}` vergisst einen Eintrag und antwortet mit der `tid`, die `POST memory/restore` (`{"tid": "<tid>"}`) benötigt, um ihn zurückzuholen. `kind` ist `note`, `episode`, `thread` oder `core`. Der frühere Body `{"conv": "<chat id>", "note": "<note id>"}` funktioniert weiterhin, und ohne `note` vergisst er die Hauptnotiz des Chats.
- `POST memory/forget_chat` mit `{"conv": "<chat id>"}` vergisst alles, was sich dieser Chat merkt. Dies lässt sich nicht rückgängig machen.
- `GET memory/list?conv=<chat id>` listet auf, was sich jeder Chat merkt und was sich noch wiederherstellen lässt; `personagent memory` liest es, während der Dienst läuft.
- `GET memory/evidence?conv=<chat id>&kind=note|episode&id=<id>` liefert die Zeilen des Chatprotokolls, auf denen ein Fakt oder Ereignis beruht (`lines`, jede mit `seq`, `t`, `name`, `self` und `text`), wie viele Zeilen es nennt (`refs`) und ob das Protokoll eingeschaltet ist (`on`). In `conversation` und `memory/list` trägt jeder Fakt außerdem `refs` und `checked` (wann eine Prüfung ihn zuletzt bestätigt hat; `0` für nie), jedes Ereignis `refs` und jeder Chat `log` (`on`, `days`, `lines` und `first_at`).

Jeder Aufruf erfordert den Header `X-Personagent-Dashboard-Token` mit dem Token aus `dashboard.token` im Laufzeitordner (`<home>/runtime/`, sofern `AGENT_RUNTIME_DIR` ihn nicht verlegt). Nur der Besitzer kann die Datei lesen, und der Dienst legt sie beim Start an. Ein Aufruf ohne den Header erhält 401 (`dashboard_token`), ein falsches Token 403 (`wrong_token`). `CONNECTOR_TOKEN` und `X-Personagent-Token` öffnen sie nicht. Sie gelten nur für Konnektoren und `/health/details`.

- Schreibzugriffe erfordern außerdem `X-Personagent-Dashboard: 1` und `Content-Type: application/json`. Wenn die Anfrage ein `Origin` sendet, muss es das des Dienstes sein.
- Websiteübergreifende Browser-Anfragen werden abgelehnt.
- Antworten ersetzen alle Zugangsdaten durch `***`. URLs in den Startprüfungen maskieren außerdem Benutzername, Passwort und Query.
- Skripte auf demselben Computer dürfen die API genauso aufrufen wie die lokale Seite.

Der Dienst liefert keine Seite aus. `GET /` antwortet mit einem kurzen Hinweis, der auf die lokale Seite und auf `personagent learned` verweist; das öffnet jetzt auch ein alter `?token=`-Link. Die lokale Seite bindet nur an 127.0.0.1. Auf einem Server ohne lokale Seite zeigt `personagent learned`, was die Figur gelernt hat, was sie beobachtet und warum, und lässt Sie einen Eintrag übernehmen, zurückstellen, rückgängig machen oder zurückholen, was die Figur oder die Frist zurückgestellt und was die Figur oder eine Regel rückgängig gemacht hat. `personagent memory` listet auf, was sie sich merkt, und vergisst einen Eintrag oder stellt ihn wieder her.

## Auf einem Server, einem NAS oder in Docker

personagent läuft gut auf einem Rechner ohne Bildschirm. Drei Dinge machen das möglich: Die Seite antwortet anderen Geräten hinter einem Passwort, `personagent service install` hält es nach einem Neustart in Betrieb, und ein Image führt alles in Docker aus.

### Ein Server von Grund auf

1. Installieren Sie personagent auf dem Server ([Installation und der personagent-Ordner](guide.de.md#installation-und-der-personagent-ordner); die Einzeiler-Installationsprogramme funktionieren auch über SSH).
2. Legen Sie ein Seitenpasswort fest. Es wird zweimal eingegeben und nicht angezeigt, und in `.env` wird nur sein Hash gespeichert:

   ```
   personagent page password
   ```

   Auf einem Server ohne Person an der Tastatur erzeugt `personagent page password --random` ein Passwort und gibt es einmal aus.
3. Machen Sie die Seite für andere Geräte erreichbar. Ergänzen Sie in `<home>/.env`:

   ```
   PAGE_HOST=0.0.0.0
   ```

4. Starten Sie es: `personagent up`. Der Befehl gibt den Link für diesen Computer und die Adresse für andere Geräte aus, Port 8090, sofern `PAGE_PORT` nichts anderes angibt. Öffnen Sie diese Adresse auf einem Smartphone oder einem anderen Computer, melden Sie sich an, fügen Sie den Modellschlüssel ein und verbinden Sie die Plattformen. Der QR-Code einer Plattform erscheint auf der Seite. Die Figur startet, sobald der Schlüssel gespeichert ist.
5. Halten Sie es in Betrieb: `personagent service install`.

### Die Seite von einem anderen Gerät aus

| Einstellung | Bedeutung |
|---|---|
| `PAGE_HOST` | Wo die Seite lauscht. Leer oder `127.0.0.1`: nur dieser Computer, über den Link mit seinem Token, wie bisher. `0.0.0.0` oder `::`: auch andere Geräte. Eine bestimmte Adresse dieses Computers funktioniert ebenfalls; die Seite lauscht dann zusätzlich auf `127.0.0.1`, für den Link. |
| `PAGE_PORT` | Der Port der Seite. Leer: ein freier Port auf Loopback, 8090 darüber hinaus. |
| `PAGE_PASSWORD` | Womit sich andere Geräte anmelden: 12 oder mehr Zeichen, davon 5 verschiedene. `personagent page password` speichert seinen Hash; ein Klartextwert aus der Umgebung (Docker) funktioniert ebenfalls. |
| `PAGE_ALLOWED_HOSTS` | Hostnamen, auf die die Seite antwortet, etwa `nas.local` oder ein Tailscale-Name. Als Zahlen eingegebene Adressen und der eigene Name dieses Computers funktionieren immer. |

Wie bei jeder Einstellung hat die Umgebung Vorrang vor `.env`. Sobald `PAGE_HOST`, `PAGE_PORT` oder `PAGE_PASSWORD` gesetzt ist, stellt `personagent up` zusätzlich die Seite bereit; `personagent up --page` tut dies auch ohne sie. `personagent start --no-browser` behält seine Bedeutung: Der Befehl gibt den Link aus und öffnet nichts, und während `up` die Seite bereitstellt, gibt er den Link dieser Seite aus.

**Verweigerungen.** Über Loopback hinaus startet die Seite nicht ohne Passwort oder mit einem schwachen; sie nennt die betreffende Einstellung und wie sie zu beheben ist, und `personagent doctor` sowie die Ansicht App der Seite zeigen dasselbe. `doctor` hat eine Zeile für die Seite: wo sie lauscht und ob ein Passwort sie schützt.

**Anmeldung.** Ein Gerät, das nicht dieser Computer ist, erhält eine Anmeldeseite. Das richtige Passwort gibt ihm ein Sitzungscookie (HttpOnly, SameSite=Strict, hinter HTTPS Secure), das 7 Tage gilt, bis **Abmelden** oben auf der Seite gewählt wird, bis sich das Passwort ändert oder bis personagent neu startet. Auf jedes falsche Passwort folgt eine Sekunde Wartezeit; fünf falsche von einer Adresse innerhalb von 15 Minuten sperren diese Adresse für 15 Minuten aus. Das Passwort wird in konstanter Zeit verglichen und nie protokolliert oder angezeigt. Die API der Seite nimmt eine Sitzung nur mit dem eigenen Header der Seite an und lehnt Anfragen von einer anderen Website (`Origin`, `Sec-Fetch-Site`) sowie an einen nicht zugelassenen Hostnamen ab, sodass eine Webseite die Sitzung nicht nutzen und die Seite nicht unter einem eigenen Namen erreichen kann.

**Auf diesem Computer ändert sich nichts.** Ein Browser hier, der den Link mit dem Token öffnet, wird ohne Passwort eingelassen. Eine Anfrage über einen Proxy zählt als anderes Gerät, auch von diesem Computer aus.

**Was ein anderes Gerät nicht kann.** Einen Ordner öffnen, das Desktopsymbol, der Start bei der Anmeldung, die Schaltflächen des App-Fensters, Beenden und das Aktualisieren über die Seite wirken auf den Computer, auf dem personagent läuft; daher blendet die Seite sie dort aus, und die API lehnt sie ab. Sicherungen, Wiederherstellungen und Zurücksetzungen funktionieren, und ihre Dateien bleiben auf jenem Computer.

### Die Seite sicher erreichen

Die Seite spricht unverschlüsseltes HTTP. In einem Netzwerk, das Sie nicht kontrollieren, können Passwort und Sitzung bei der Übertragung mitgelesen werden; verwenden Sie daher eine dieser Möglichkeiten:

- **Ein SSH-Tunnel.** Lassen Sie `PAGE_HOST` leer, setzen Sie `PAGE_PORT=8090` und führen Sie `personagent up` aus. Von Ihrem eigenen Computer aus:

  ```
  ssh -L 8090:127.0.0.1:8090 you@server
  ```

  Öffnen Sie dann den Link, den `personagent up` ausgegeben hat (mit `#token=`), oder führen Sie `personagent start --no-browser` auf dem Server aus, um ihn erneut auszugeben. Ein Passwort ist nicht nötig: Für die Seite ist der Tunnel dieser Computer.
- **Tailscale oder ZeroTier.** Beide verschlüsseln den Verkehr zwischen Ihren Geräten. Setzen Sie `PAGE_HOST=0.0.0.0` (oder die Tailscale-Adresse des Servers) und das Seitenpasswort, und tragen Sie den Tailscale-Namen des Servers in `PAGE_ALLOWED_HOSTS` ein, wenn Sie ihn verwenden.
- **Ein Reverse-Proxy mit HTTPS** (Caddy, nginx, der eines NAS). Behalten Sie `PAGE_HOST=127.0.0.1` bei, setzen Sie das Seitenpasswort und tragen Sie den öffentlichen Namen in `PAGE_ALLOWED_HOSTS` ein. Eine Anfrage über den Proxy erhält dann die Anmeldeseite, während der Link auf dem Server selbst weiterhin funktioniert. Mit Caddy:

  ```
  personagent.example.com {
      reverse_proxy 127.0.0.1:8090
  }
  ```

  Mit nginx geben Sie Host und Schema weiter:

  ```
  location / {
      proxy_pass http://127.0.0.1:8090;
      proxy_set_header Host $http_host;
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_set_header X-Forwarded-Proto $scheme;
  }
  ```

  Jeder Aufrufer kommt dann von der Adresse des Proxys; fünf falsche Passwörter von irgendjemandem setzen die Anmeldung daher für alle 15 Minuten lang aus.

personagent terminiert TLS nicht selbst und öffnet auch keine Tunnel.

### In Betrieb halten: `personagent service`

```
personagent service install     # write the service and start it
personagent service status
personagent service restart     # after an update
personagent service remove
```

Mit `--dry-run` werden die Datei und die Befehle ausgegeben, ohne sie auszuführen. Der Dienst führt `personagent up` für diesen personagent-Ordner mit dem eigenen Python dieser Installation aus, startet es nach einem Fehler neu und schreibt seine Ausgabe nach `<home>/runtime/desktop/service.log`, lesbar nur für Ihren Benutzer. Er wird nicht installiert, solange `up` nicht dauerhaft laufen könnte: bevor die Einrichtung abgeschlossen ist (außer wenn die Seite für ein anderes Gerät eingerichtet ist), bei einer Seite ohne Passwort oder unter uvx, dessen Kopie temporär ist.

- **Linux:** eine systemd-Benutzereinheit, `~/.config/systemd/user/personagent.service` (ein anderer personagent-Ordner erhält ein Suffix), aktiviert mit `systemctl --user enable --now`. Die Dienste eines Benutzers enden, wenn er sich abmeldet, und starten erst bei der Anmeldung, sofern Lingering nicht eingeschaltet ist: `install` führt `loginctl enable-linger` aus und gibt, wenn das nicht erlaubt ist, den auszuführenden `sudo`-Befehl aus. Mit Lingering startet der Dienst beim Hochfahren. Exit-Code 2 (Einrichtung nicht abgeschlossen, eine Seite ohne Passwort, ein anderes personagent in diesem personagent-Ordner) führt zu keinem Neustart. Eine systemweite Variante gibt es nicht: Die Benutzereinheit läuft unter Ihrem Konto, was die sicherere Wahl ist.
- **macOS:** ein LaunchAgent, `~/Library/LaunchAgents/com.github.wangkant.personagent.plist`, geladen mit `launchctl bootstrap gui/<uid>`. Er läuft, solange Sie angemeldet sind; schalten Sie daher auf einem Mac, der für andere bereitsteht, die automatische Anmeldung ein.
- **Windows:** der eigene Start der App bei der Anmeldung (derselbe Schalter wie in der Ansicht App): personagent öffnet sich hinter seinem Symbol im Infobereich, wenn Sie sich anmelden. Nach einem Fehler wird es nicht neu gestartet; `restart` ist nicht verfügbar.

### Docker

```
docker compose up -d
docker compose logs personagent      # the page password the first start made
```

`compose.yaml` im Repository führt `ghcr.io/wangkant/personagent` aus, mit der Seite auf Port 8090 und dem personagent-Ordner im Volume `personagent-data` (eingehängt unter `/data`). Ohne Compose:

```
docker run -d --name personagent --init --restart unless-stopped \
  -p 8090:8090 -v personagent-data:/data ghcr.io/wangkant/personagent
```

Erster Start: Öffnen Sie `http://<server>:8090/`, melden Sie sich mit dem Passwort aus dem Log an, fügen Sie einen Modellschlüssel ein und verbinden Sie die Plattformen; QR-Codes erscheinen auf der Seite. Das Image führt `personagent up` als Benutzer ohne besondere Rechte mit `PAGE_HOST=0.0.0.0` und `PAGE_PORT=8090` aus. Geben Sie `PAGE_PASSWORD` in der Umgebung an, um ein eigenes Passwort zu wählen; ohne eines erzeugt der erste Start ein Passwort, speichert nur seinen Hash in `/data/.env` und gibt es einmal aus. Jede andere Einstellung kann ebenfalls in der Umgebung angegeben werden. `docker exec -it personagent personagent page password` ändert das Passwort, und `docker exec personagent personagent doctor` prüft die Einrichtung. Veröffentlichen Sie den Port als `127.0.0.1:8090:8090`, um die Seite auf einen SSH-Tunnel oder einen Proxy auf demselben Host zu beschränken. Ein Bind-Mount muss für den Benutzer 1000 beschreibbar sein.

Docker Desktop unter Windows und macOS leitet jede Verbindung zu einem veröffentlichten Port von einer einzigen Gateway-Adresse in den Container weiter, sodass die Seite alle Geräte als eines sieht: Fünf falsche Passwörter von einem beliebigen Gerät setzen die Anmeldung für alle Geräte 15 Minuten lang aus. Unter Linux behält jedes Gerät seine eigene Adresse. Halten Sie den Port mit Docker Desktop aus Netzwerken fern, denen Sie nicht vertrauen: Veröffentlichen Sie ihn als `127.0.0.1:8090:8090` und verwenden Sie einen SSH-Tunnel, oder erreichen Sie ihn über Tailscale.

Was ein Container nicht hat:

- **Das App-Fenster, das Symbol im Infobereich und das Desktopsymbol.** Es gibt keinen Bildschirm; die Seite übernimmt all das.
- **Das Aktualisieren über die Seite.** Das Image wird aktualisiert, indem ein neues abgerufen wird: `docker compose pull && docker compose up -d`. Der Update-Hinweis sagt das.
- **Das verwaltete AstrBot** funktioniert: Es benötigt glibc (das Image basiert auf Debian), einen beschreibbaren personagent-Ordner (`/data`) und ausgehenden Zugriff auf PyPI und GitHub oder deren Spiegel (`PERSONAGENT_MIRROR`). Es wird in das Volume heruntergeladen, mehrere hundert Megabyte.
- **Ihre Zeitzone.** Die Uhr eines Containers läuft auf UTC. Setzen Sie `PERSONA_TZ_OFFSET_HOURS` (die Stunden, die Sie UTC voraus sind, etwa `8` oder `-5`) in `compose.yaml` oder mit `-e`; andernfalls nennt die Figur die Uhrzeit und hält ihre nächtlichen Ruhezeiten nach UTC ein.

Die Integritätsprüfung des Images fragt `/health` der Seite ab. Images werden mit jedem Release für amd64 und arm64 veröffentlicht, mit der Version und `latest` getaggt.

## Was der Host bereitstellen muss

1. **Ein beschreibbarer personagent-Ordner.** Der Start legt eine Sperre unter `<home>/.personagent.instance.lock` an, außerhalb von `runtime/`. Mit einem schreibgeschützten personagent-Ordner startet der Dienst nicht.
2. **Ein Prozess pro personagent-Ordner.** Ein zweites `personagent run` mit demselben personagent-Ordner beendet sich mit einer entsprechenden Meldung.
3. **Ein freier Port.** Ein belegter oder unzulässiger Port führt ebenfalls zum Abbruch mit einer Meldung. Wählen Sie mit `--port` oder `SERVER_PORT` einen anderen.

`AGENT_RUNTIME_DIR` muss sich unterhalb des personagent-Ordners auflösen, sonst schlägt der Start fehl. Ein relatives `PERSONA_FILE` oder `PERSONA_CARD_FILE` löst sich ebenfalls im personagent-Ordner auf, daher benötigt eine an anderer Stelle gespeicherte Persona einen absoluten Pfad.

Eine beschädigte `memory.json`, `core_memory.json` oder `episodes.json` bricht den Start mit Exit-Code 2 ab, mit einem Satz, der die Datei und ihre `.bak`-Kopie nennt, die an ihre Stelle zu setzen ist. Die beschädigte Datei bleibt unverändert.

## Plattformen verbinden

Fügen Sie Plattformen unter **Plattformen verbinden** auf der lokalen Seite hinzu. personagent prüft die Zugangsdaten bei der Plattform, bevor es etwas speichert. Lehnt die Plattform sie ab, zeigt die Seite die Ablehnung an und speichert nichts.

Auf einem Server ohne Bildschirm verbinden Sie die Plattformen, die personagent selbst verbindet, im Terminal mit `personagent connect <platform>`, zum Beispiel `personagent connect telegram`. Der Befehl führt dieselben Schritte und Prüfungen aus wie die Seite und speichert die Werte in derselben Form. QQ und WeChat geben ihren QR-Code im Terminal aus, Twitch gibt einen Link und einen Code aus. Mit `--no-input` und allen Werten als Optionen stellt der Befehl keine Fragen und beendet sich mit Code 2, wenn ein erforderlicher Wert fehlt. Anschließend startet `personagent up` personagent mit seinen verbundenen Plattformen. Das Benutzerhandbuch beschreibt [den Befehl und seine Optionen](guide.de.md#eine-plattform-im-terminal-verbinden).

**Von personagent selbst verbunden.** QQ, persönliches WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK und Stoat laufen in einem „direct“-Prozess, ohne AstrBot und ohne NapCat. Eine Plattform, die sich nicht laden lässt, wird übersprungen; die übrigen starten trotzdem. Die Tabelle behandelt die ersten vier; das Benutzerhandbuch beschreibt, [was die anderen sechs benötigen und welche Einschränkungen gelten](guide.de.md#plattformen-die-personagent-selbst-verbindet).

| Plattform | Vorgehen | Einschränkungen |
|---|---|---|
| QQ (offizieller Bot) | Scannen Sie einen QR-Code mit der mobilen QQ-App, die einen Bot erstellt oder einen von Ihnen erstellten auswählt. Alternativ fügen Sie AppID und AppSecret ein. | Bis der Bot zertifiziert ist, lässt QQ ihn nur Gruppen beitreten, deren Inhaber Sie sind. In einer Gruppe empfängt er nur Nachrichten, die ihn per @ erwähnen, es sei denn, der Gruppeninhaber aktiviert im Profil des Bots in dieser Gruppe den Empfang aller Nachrichten; bis dahin kann er sich nicht von selbst einbringen. |
| Persönliches WeChat | Scannen Sie mit WeChat (Tencents iLink-Bot-API). | Nur Einzelchats. WeChat gibt solchen Bots keine Gruppennachrichten. |
| Telegram | Fügen Sie das Token von @BotFather ein. | |
| Discord | Fügen Sie das Bot-Token ein; der Message Content Intent muss aktiviert sein. | |

**Über das verwaltete AstrBot.** Jede andere Plattform läuft über ein AstrBot, das personagent zusammen mit einer eigenen Python-3.12-Laufzeit herunterlädt und headless ausführt. Es hat kein Dashboard und erfordert keine zweite Anmeldung. KOOK, Feishu/Lark (lange Verbindung), DingTalk (Stream-Modus), Slack (Socket Mode, und der Link im Leitfaden füllt die App vor), WeCom-KI-Bot (lange Verbindung), Mattermost und Misskey erfordern ein bis zwei Werte. Die Gruppe **Erweitert** erfordert eine öffentliche Adresse oder zusätzliche Software: WeCom-App, offizielles WeChat-Konto, QQ-Webhook, OneBot v11 (NapCat) und Satori. LINE wird nicht angeboten.

Auf beiden Wegen verlangt eine Plattform, die auf der Seite oder mit `personagent connect <platform>` verbunden wurde, eine Freigabe neuer Chats: Die Figur antwortet dem Administrator sowie den Personen und Gruppen, die der Administrator freigegeben hat, und alle anderen erhalten eine feste Nachricht mit einem kurzen Code und warten unter **Plattformen verbinden** oder in `personagent access` (siehe [Unter Kontrolle behalten](#unter-kontrolle-behalten)). Ein vor dieser Version eingerichteter personagent-Ordner oder eine auf **Neue Chats ohne Freigabe beantworten** umgestellte Plattform antwortet in jeder Gruppe und jeder DM, die die Plattform dem Bot zustellt. Zum Einschränken verwenden Sie auf der Seite **Nur in diesen Gruppen antworten**. Die Seite speichert dies als `ACCESS_GROUPS`, und `ACCESS_DM_USERS` leistet dasselbe für Direktnachrichten; sobald eine der beiden einen Eintrag für eine Plattform enthält, ist diese Plattform auf ihre Einträge beschränkt (siehe [personagents eigene Zulassungslisten](#über-ein-astrbot-das-sie-bereits-betreiben)). IDs kommen als `<platform>:<id>` an, zum Beispiel `qq_official:<openid>`, `weixin_oc:<id>`, `telegram:<id>` und `discord:<id>`. Der offizielle QQ-Bot sieht openids, keine QQ-Nummern. Wird eine Plattform direkt verbunden, entfällt eine AstrBot-Verbindung für dieselbe Plattform.

## Unter Kontrolle behalten

Alles Folgende erledigen Sie auf der lokalen Seite. Die Einstellungen befinden sich unter **Figur & Einstellungen** → **Erweiterte Einstellungen** und gelten, sobald Sie auf **Erweiterte Einstellungen speichern** klicken. In Klammern steht der Name der jeweiligen Einstellung in `.env`; eine direkt in `.env` vorgenommene Änderung wirkt erst nach einem Neustart von personagent.

- **Neue Chats freigeben.** Auf einer Plattform, die in `ACCESS_APPROVAL_PLATFORMS` aufgeführt ist (jede ab dieser Version verbundene Plattform), erhält ein Chat, der in keiner der beiden Listen unten steht, keine Antwort vom Modell. Eine Direktnachricht erhält höchstens einmal am Tag eine feste Zeile mit einem sechsstelligen Code; eine nicht freigegebene Gruppe hört höchstens eine Zeile am Tag, und nur, wenn jemand die Figur anspricht. Die Anfrage wartet unter **Plattformen verbinden** mit **Freigeben**, **Ablehnen** und bei einer Direktnachricht **Das bin ich**, das das Konto zum Administrator macht, sobald Sie den Code eingeben, den Ihr eigener Chat erhalten hat. Auf einem Server listet `personagent access` die Anfragen auf, und `personagent access approve CODE` (oder `decline`, `admin`) entscheidet eine davon. Freigegebene und abgelehnte Chats werden in `approvals.json` im Laufzeitordner gespeichert, die der laufende Dienst sofort liest; sie werden zu `ADMIN_IDS`, `ACCESS_DM_USERS` und `ACCESS_GROUPS` hinzugenommen, ob diese aus `.env` oder aus der Umgebung stammen, und ändern sie nie. Ein abgelehnter Chat bleibt unabhängig von der Regel unbeantwortet. Anfragen laufen nach drei Tagen ab; je Plattform warten höchstens zwanzig Direktnachrichten und zehn Gruppen. Eine Plattform verlangt die Freigabe nur, wenn sie zum ersten Mal verbunden wird, ohne gespeicherte Entscheidung und noch ohne Chats. `personagent access policy <platform> open` (oder **Neue Chats ohne Freigabe beantworten** auf der Seite) schaltet die Freigabe für eine Plattform ab.
- **Sich selbst zum Administrator machen.** Senden Sie der Figur eine Direktnachricht, klicken Sie dann unter **Antworten, Administrator und Zugriff** auf **Aus letzten Chats auswählen** und neben Ihrem Konto auf **Das bin ich** (`ADMIN_IDS`). So gehen Sie beim offiziellen QQ-Bot vor, der statt Ihrer QQ-Nummer eine openid sieht.
- **Nur in bestimmten Gruppen antworten.** Aktivieren Sie in derselben Liste **In dieser Gruppe antworten** für jede Gruppe, die bleiben soll, oder tragen Sie die IDs unter **Nur in diesen Gruppen antworten** (`ACCESS_GROUPS`) ein. Sobald eine Gruppe einer Plattform aufgeführt ist, antwortet die Figur in den übrigen Gruppen dieser Plattform nicht mehr. Eine Gruppe mit dem per QR-Code verbundenen offiziellen QQ-Bot hat eine ID der Form `qq_official:<id>`, die QQ selbst nicht anzeigt: Erwähnen Sie den Bot einmal in dieser Gruppe und wählen Sie die Gruppe dann über **Aus letzten Chats auswählen**.
- **Alle Antworten pausieren.** Schalten Sie **Auf Nachrichten antworten** (`AGENT_ENABLED`) aus, die erste Einstellung unter **Antworten, Administrator und Zugriff**; vor dem Speichern wird nachgefragt. Die Figur bleibt verbunden, antwortet aber auf nichts, bis Sie die Option wieder einschalten.
- **Nur einzelne Gruppen pausieren.** Aktivieren Sie in derselben Liste neben einer Gruppe **Hier schweigen**, oder tragen Sie ihre ID unter **In diesen Gruppen schweigen** (`ACCESS_PAUSED_GROUPS`) ein. Dort antwortet die Figur auf nichts, auch nicht, wenn sie angesprochen wird, und auch der plattformeigene Bot bleibt still; überall sonst antwortet sie weiter. Nachrichten aus einer pausierten Gruppe werden weder behalten noch zum Lernen verwendet. Entfernen Sie die Gruppe aus der Liste, um fortzufahren.
- **Nur antworten, wenn angesprochen.** Schalten Sie unter **Sprechen und Antwortstil** die Option **In Gruppen nur antworten, wenn angesprochen** (`CHAT_ONLY_WHEN_CALLED`) ein. In Gruppen antwortet die Figur dann nur, wenn jemand ihren Namen nennt, sie erwähnt oder auf eine ihrer Nachrichten antwortet, und beteiligt sich nie von sich aus an einem Gespräch oder beginnt eines. Private Chats sind nicht betroffen.
- **Nur Sie dürfen sie belehren.** Schalten Sie unter **Lernen** die Option **Nur aus Korrekturen des Administrators lernen** (`REACT_LEARN_ADMIN_ONLY`) ein. Reaktionen von Personen, die nicht unter **Ihre Konten** stehen, werden weiterhin erfasst, doch nichts von dem, was sie vorschlagen, wird übernommen. Tragen Sie zuerst Ihre Konten ein; ohne Konten lernt die Figur nur aus Korrekturen unter **Chat** auf dieser Seite.
- **Etwas Gelerntes rückgängig machen.** Wählen Sie in **Aktivität** den Chat und klicken Sie neben dem Eintrag auf **Rückgängig machen**, oder führen Sie `personagent learned rollback <id>` aus.
- **Aus einer Gruppe entfernen.** Entfernen Sie den Bot in der Plattform selbst. Das Trennen unter **Plattformen verbinden** beendet nur die Verbindung von personagent; der Bot bleibt Mitglied seiner Gruppen.
- **Wenn er entfernt oder eingeschränkt wird.** Eine Gruppe, die den Bot entfernt hat, sendet ihm einfach nichts mehr, und es muss nichts neu verbunden werden. Sperrt die Plattform den Bot oder nimmt sie ihn offline, endet die Verbindung einer Plattform, die personagent selbst verbindet, und **Plattformen verbinden** nennt den Grund.

## Über ein AstrBot, das Sie bereits betreiben

AstrBot, NapCat (OneBot), Koishi (über den [Satori-Konnektor](../integrations/satori/README.de.md)) und Matrix (über den [Matrix-Konnektor](../integrations/matrix/README.de.md) und mautrix-Bridges) sind Drittanbieter-Bridges, mit denen personagent zusammenarbeitet. Keine davon ist für die Plattformen erforderlich, die personagent selbst verbindet.

AstrBot übergibt Nachrichten über ein Plugin in `integrations/astrbot/astrbot_plugin_personagent/` an personagent. Das Plugin sendet jede Nachricht an `POST /v1/events` und leitet die Antworten aus der Response weiter. Es ruft außerdem personagents Outbox ab (`outbox_enabled`, standardmäßig aktiviert), sodass die Figur zuerst sprechen kann, wo die Plattform das einem Bot erlaubt. Das Plugin-README enthält die Tabelle. Das verwaltete AstrBot erhält das Plugin automatisch. Starten Sie Ihr eigenes AstrBot einmal, damit es seinen Datenordner anlegt (den Ordner mit `cmd_config.json`, `plugins/` und `config/`), und führen Sie dann Folgendes aus:

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

Der Befehl kopiert das Plugin nach `<data dir>/plugins/` und schreibt ein gemeinsames `CONNECTOR_TOKEN` in `.env` und in die Plugin-Konfiguration. Er setzt `personagent_url` auf `http://127.0.0.1:<SERVER_PORT>`, sofern das Plugin nicht bereits eine zulässige URL hat (eine Loopback-URL, Tunnel eingeschlossen, oder HTTPS).

Für ein AstrBot auf einem anderen Rechner laden Sie `astrbot_plugin_personagent.zip` aus dem [neuesten Release](https://github.com/wangkant/personagent/releases/latest) herunter und laden es unter **Install from File** auf AstrBots Plugin-Seite hoch. Setzen Sie sein `connector_token` auf das `CONNECTOR_TOKEN` aus personagents `.env`, und `personagent_url` auf eine HTTPS-Adresse für personagent (siehe [Die Endpunkte freigeben](#die-endpunkte-freigeben)).

Führen Sie nach einem personagent-Upgrade `connect astrbot` erneut aus oder laden Sie das neue ZIP hoch. AstrBot 4.29 und neuer ersetzen die installierte Kopie. Bei älteren Versionen deinstallieren Sie das Plugin zuerst und lassen **Also delete plugin configuration file** deaktiviert.

Optionen für `connect astrbot`:

- `--qq` nimmt `aiocqhttp` aus `excluded_platforms`, und `--no-qq` setzt es zurück. Ohne eine der beiden Optionen bleibt das QQ-Routing unverändert. `CONNECTOR_QQ_PLATFORMS` folgt dem, was das Plugin am Ende tut.
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>` schaltet diesen Adapter auch in AstrBots eigener Konfiguration ein. Slack erwartet zusätzlich `--app-token`, Lark und QQ erwarten `--app-id` und `--app-secret`. Ein vorhandener Adaptereintrag behält seine übrigen Einstellungen (Proxy, Basis-URL, Polling) und erhält nur die neuen Zugangsdaten.
- `--url https://...` setzt eine HTTPS-Adresse, an die das Plugin sendet.
- `--install` lädt stattdessen ein verwaltetes AstrBot herunter, und `--start` startet es.

Der erste Lauf lässt die Zulassungslisten leer. Ein erneuter Lauf behält sie, zusammen mit anderen ausgeschlossenen Plattformen.

Das Plugin lässt standardmäßig nichts zu. Füllen Sie `groups` und für DMs `dm_users` in AstrBots WebUI aus, oder beantworten Sie die Fragen von `connect`. DMs werden weitergeleitet, sobald `dm_users` nicht leer ist. Das [Plugin-README](../integrations/astrbot/astrbot_plugin_personagent/README.de.md) listet alle Schlüssel. Das verwaltete AstrBot öffnet jede verbundene Plattform mit `<platform>:*`. Starten Sie nach der Plugin-Installation AstrBot neu oder laden Sie die Plugins in seiner WebUI neu. Auf der personagent-Seite:

- `CONNECTOR_TOKEN` authentifiziert jede Anfrage. Die Anfrage trägt den Header `X-Personagent-Token` und einen HMAC-SHA256, mit dem Token als Schlüssel, über `timestamp.nonce.body`, und ein Replay-Schutz lehnt wiederverwendete Nonces ab. Eine abgefangene Anfrage kann weder wiederholt noch verändert werden. Das Token ist zugleich der Signaturschlüssel; halten Sie es daher aus Protokollen heraus und ersetzen Sie es, falls es offengelegt wurde. Auf einem Host ist es optional, über Hosts hinweg Pflicht.
- `ADMIN_IDS` listet die Konten des Administrators als `<platform>:<id>` (`telegram:12345`, `discord:4242`). Eine bloße ID oder `qq:<id>` ist eine QQ-Nummer. `ADMIN_NAME` setzt den Namen des Administrators. Alle aufgeführten Konten gehören einer Person, der gegenüber sich die Figur in Gruppen und DMs vertrauter verhält, die verwalten darf, was der Bot sich über eine Gruppe merkt, und die ihn als Einzige anleiten darf. Über AstrBot ist die Plattform der Adaptername, den AstrBot anzeigt, und `/sid` in einem Chat zeigt eine ID.
- `ACCESS_GROUPS` und `ACCESS_DM_USERS` lassen personagent eine Plattform selbst einschränken, in derselben Form `<platform>:<id>`. Jede Plattform wird getrennt eingeschränkt. Eine Plattform ohne Einträge bleibt dem Konnektor überlassen, und schon ein Eintrag beschränkt diese Plattform auf ihre Einträge. Ein Durchgang, den personagent ablehnt, wird nicht übernommen, sodass AstrBots eigenes Modell antworten kann.
- `ACCESS_APPROVAL_PLATFORMS` nennt die Plattformen (hier mit AstrBots Adapternamen), auf denen die beiden Listen auch dann gelten, wenn sie für die Plattform keine Einträge enthalten. Ein Chat, der in keiner steht, wird für die Freigabe durch den Administrator zurückgehalten und übernommen, sodass auch AstrBots eigenes Modell schweigt; `groups` und `dm_users` des Plugins entscheiden weiterhin zuerst, was personagent erreicht.

Für AstrBot in Docker oder auf einem anderen Host siehe [das Benutzerhandbuch](guide.de.md#brücken-die-sie-selbst-betreiben).

### QQ über NapCat (OneBot)

Dieser Weg nutzt ein persönliches QQ-Konto statt eines offiziellen Bots. Sie benötigen ein zweites QQ-Konto in den Zielgruppen, nicht Ihr eigenes (siehe [DISCLAIMER.md](DISCLAIMER.de.md)). Es meldet sich, meist per QR-Code und in einer Sitzung, die Neustarts übersteht, bei einer OneBot-v11-Implementierung an, die mit AstrBots Adapter `aiocqhttp` verbunden ist. [NapCat](https://github.com/NapNeko/NapCatQQ) ist getestet und hängt sich an den QQ-NT-Desktop-Client. LLOneBot und Lagrange sind weitere OneBot-v11-Implementierungen. Fügen Sie dieses Konto selbst jeder Gruppe hinzu: Solange es kein Mitglied ist, erreicht keine Nachricht der Gruppe die Figur.

Beim verwalteten AstrBot fügen Sie auf der lokalen Seite **Erweitert > OneBot v11 (NapCat)** hinzu und richten NapCat auf `ws://127.0.0.1:6199/ws` aus. Die [chinesische Anleitung](deploy.zh-CN.md) beschreibt die Schritte im Einzelnen. Bei Ihrem eigenen AstrBot entfernen Sie `aiocqhttp` aus `excluded_platforms` des Plugins, setzen `CONNECTOR_QQ_PLATFORMS=aiocqhttp` (`--qq` erledigt beides) und setzen `QQ_BOT_ID` (`personagent connect astrbot` fragt danach).

**`CONNECTOR_QQ_PLATFORMS` ist hier Pflicht.** Ohne diese Einstellung kommen QQ-IDs mit Namensraum an (`aiocqhttp:123456`), und jedes Gespräch erscheint neu. Gedächtnis, Verlauf und gelernte Beispiele sind nach der bloßen ID geordnet, und die Lernprotokolle leiten Zeilen-IDs aus der Gesprächs-ID ab; die Aufspaltung lässt sich daher später nicht beheben.

Bloße IDs tragen QQ-Befugnisse; daher gelten die QQ-Einträge von `ADMIN_IDS`, `ACCESS_GROUPS` und `ACCESS_DM_USERS` zusätzlich zu den Zulassungslisten des Plugins. Eine QQ-DM muss in `dm_users` stehen *und* vom Administrator oder einem Eintrag in `ACCESS_DM_USERS` kommen. Wenn `ACCESS_GROUPS` QQ-Gruppen enthält, muss eine QQ-Gruppe in beiden stehen. Nehmen Sie eine Plattform nur dann in `CONNECTOR_QQ_PLATFORMS` auf, wenn Sie ihrem Konnektor diese Befugnis anvertrauen.

**NapCats HTTP-Server** (`QQ_ONEBOT_URL`, standardmäßig leer) ist auf diesem Weg optional. personagent sendet auch von sich aus Nachrichten:

- proaktive Nachrichten (`PROACTIVE_ENABLED`, standardmäßig aus);
- die Frage zwei Minuten nach einer Ablehnung (`REACT_ELICIT_ENABLED`);
- die Ausrede, die in einer Gruppe gesendet wird, wenn der Modellaufruf fehlschlägt.

Diese werden über die Outbox des Plugins zugestellt, solange das Plugin sie abruft. Andernfalls werden sie an `QQ_ONEBOT_URL` gesendet, sofern die URL gesetzt ist. Nur der Durchlauf für offline verpasste @-Erwähnungen benötigt den Server, zusammen mit `QQ_BOT_ID`. Der Durchlauf läuft beim Start und dann alle 30 Minuten. Er umfasst die QQ-Gruppen in `ACCESS_GROUPS` plus jede Gruppe mit Aktivität seit dem letzten Neustart und spielt @-Erwähnungen ab, die jünger als eine Stunde sind. Bei leerer URL zeigt `personagent doctor` die OneBot-Bridge als „not configured“.

**Auf jedem Konnektor-Weg nicht verfügbar** (direkt, AstrBot oder anderer Konnektor), ohne Einstellung, die diese Funktionen wiederherstellt:

- der OCR-Rückfall für Bilder, die kein Vision-Modell beschrieben hat;
- die Zitat-Suche über NapCat. Zitate werden aus personagents eigenem Index der letzten Nachrichten aufgelöst und aus dem zitierten Text, den ein Konnektor mit dem Zitat sendet.

Neue Sticker werden auf jedem Weg gesammelt, wie bei QQ: aus Bildern, die in Gruppen gepostet werden und direkt eingebettet oder als Sticker gekennzeichnet ankommen. Ein Foto, das ein Konnektor nur als Link sendet, wird nicht gesammelt.

## Mehr als eine Plattform

Mehrere Konnektoren können nebeneinander gegen ein personagent laufen, weil jeder seine Plattform benennt (`telegram:-1001234`, `matrix:!room:example.org`). Der direct-Prozess, AstrBot, Satori und Matrix können alle gleichzeitig laufen. Binden Sie einen Chat nicht über zwei Konnektoren ein, da sonst jede Nachricht doppelt ankommt. IDs mit Namensraum kollidieren nie mit einer bloßen QQ-Nummer.

Nachrichten, die nicht auf eine Anfrage antworten, erreichen eine Plattform über einen Konnektor, der personagents Outbox abruft. Das sind proaktive Einstiege, die Frage nach einer Ablehnung und die Ausrede, wenn der Modellaufruf in einer Gruppe fehlschlägt. Die Ausrede in einer DM wird in der Response auf die Anfrage zurückgegeben, die die Nachricht übermittelt hat.

Der direct-Prozess und die drei hier beschriebenen Konnektoren rufen alle die Outbox ab, auf Plattformen, auf denen ein Bot zuerst schreiben darf. QQ begrenzt die Rate unaufgeforderter Nachrichten eines offiziellen Bots, und eine Person kann sie deaktivieren. Ein eigener Konnektor sendet `connector_id`, `reply_handle` und `"capabilities": ["outbox"]` mit seinen Ereignissen und macht Long-Polling auf `/v1/outbox` (siehe [das Konnektor-Protokoll](connectors.de.md)). Ohne einen solchen Konnektor antwortet personagent nur innerhalb der Anfrage, die eine Nachricht übermittelt hat. Die proaktiven Schleifen überspringen diese Gespräche, und die Frage und die Ausrede werden nicht gesendet.

Auch die lokale Seite ruft die Outbox ab, jedoch nur für ihren eigenen Chat. Ein Ereignis von einem Programm, das die Outbox nicht abruft, etwa von einem Programmierassistenten, der in einem Chat spricht, nimmt diesen Chat keinem Konnektor weg, der die Outbox abruft (siehe [das Konnektor-Protokoll](connectors.de.md#outbox-post-v1outbox)).

`PROACTIVE_PLATFORMS` begrenzt, wo die proaktive Schleife zuerst sprechen darf. `PROACTIVE_PLATFORMS=qq_official` beschränkt sie auf den offiziellen QQ-Bot, `qq` auf QQ über NapCat. `CONNECTOR_OUTBOX_ENABLED=false` deaktiviert die Outbox vollständig.

Um ohne die Outbox in einer DM zuerst zu sprechen, kann Ihr eigener Scheduler (eine AstrBot-Plugin-Aufgabe, ein Cron-Eintrag) ein DM-Ereignis senden, das mit `"proactive": true` markiert ist. Siehe [Zuerst sprechen ohne die Outbox](connectors.de.md#zuerst-sprechen-ohne-die-outbox).

## Die Endpunkte freigeben

Behalten Sie `SERVER_HOST=127.0.0.1` bei, wenn Konnektor und personagent auf demselben Rechner laufen. Ein Container zählt nur mit dem Netzwerk-Namensraum des Hosts oder Host-Networking als derselbe Rechner. Der Agent, den die lokale Seite oder `personagent up` startet, bindet immer an `127.0.0.1`; die Seite selbst folgt `PAGE_HOST` ([Die Seite von einem anderen Gerät aus](#die-seite-von-einem-anderen-gerät-aus)). Andernfalls:

1. Setzen Sie `SERVER_HOST=0.0.0.0` (oder `--host 0.0.0.0`) und `CONNECTOR_TOKEN`. Ohne das Token verweigert der Start eine Netzwerkbindung. `QQ_ONEBOT_SECRET` ist nicht erforderlich, doch ohne diesen Wert ist das veraltete `/v1/onebot` bei einer Netzwerkbindung deaktiviert. Jede Anfrage daran erhält 403 `onebot_disabled`, und das Log nennt den Grund einmal.
2. Schalten Sie einen HTTPS-Reverse-Proxy oder einen privaten Tunnel vor. Alle hier beschriebenen Konnektoren senden nur an Loopback oder an HTTPS mit gesetztem Token. Das AstrBot-Plugin protokolliert alles andere als `refusing unsafe personagent_url`, und die Satori- und Matrix-Konnektoren verweigern den Start.
3. Lassen Sie den Body bytegenau unverändert, da die Signatur ihn abdeckt, und halten Sie die Abweichung der Uhren unter fünf Minuten.

Ist ein Zugangsdatum leer, bedient sein Endpunkt nur lokale Programme, die `http://127.0.0.1` oder `http://localhost` direkt aufrufen. Eine Anfrage erhält 403 `non_local_request`, wenn sie eines der folgenden Merkmale aufweist:

- einen `Origin`-Header;
- ein `Sec-Fetch-Site` außer `none`;
- einen `Host` außer `localhost`, `127.0.0.1` oder `::1`;
- einen Proxy-Header: `X-Forwarded-For`, `Forwarded`, `X-Real-IP`, `CF-Connecting-IP`, `Via`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP` oder `X-Original-Forwarded-For`.

Ein Proxy auf demselben Host, der nichts davon hinzufügt, gilt weiterhin als lokal. Setzen Sie `CONNECTOR_TOKEN` (und `QQ_ONEBOT_SECRET`, falls Sie `/v1/onebot` verwenden), bevor Sie einen Proxy oder Tunnel einrichten, auch auf einem einzelnen Host.

## Health-Endpunkte

- `GET /health` ist kostenlos und offen und ruft nichts auf.
- `GET /health/details` testet die vorgelagerten Dienste (60 s im Cache). Bei leerem `CONNECTOR_TOKEN` antwortet es nur auf lokale Anfragen. Mit gesetztem Token antwortet es **nur** auf Anfragen mit passendem `X-Personagent-Token`-Header, selbst von Loopback. Es gibt 503 zurück, wenn ein kritischer Test fehlschlägt oder nicht laufen kann. Die kritischen Tests sind die Chat-Modelle und, wenn QQ den direkten OneBot-Eingang nutzt (`QQ_BOT_ID` und `QQ_ONEBOT_URL` gesetzt, `CONNECTOR_QQ_PLATFORMS` nicht gesetzt), die OneBot-Bridge.
- `personagent doctor [--json]` führt dieselben Tests plus die Einstellungsprüfung aus und endet im selben Fall mit einem Wert ungleich null. Liegt die letzte Update-Prüfung einen Tag zurück, fragt der Befehl außerdem die neueste Version bei pypi.org ab (`UPDATE_CHECK_ENABLED=false` unterdrückt dies).

## Kosten

- **Tests kosten Guthaben.** `personagent doctor` und `/health/details` senden eine minimale Chat-Completion an jedes Modell, an das der Agent Arbeit sendet: Antworten in Gruppen und Direktnachrichten, die Entscheidung über die Websuche, die Bewertung von Reaktionen (solange `REACT_LEARN_ENABLED` aktiviert ist), die Selbstbewertung (solange `EVAL_ENABLED` aktiviert ist) und Vision. Sie senden außerdem ein Embedding, wenn `EMBEDDING_MODEL` gesetzt ist, und eine Tavily-Suche, wenn `TAVILY_API_KEY` gesetzt ist. `/health` und die Prüfungen der Einstellungen und Lernprotokolle sind kostenlos.
- **Die Modellnutzung wird gezählt.** Jede Modellanfrage wird pro Modell und pro Tag anhand der vom Anbieter gemeldeten Nutzung erfasst, mit den Kosten, sofern der Anbieter sie meldet. `personagent doctor` gibt den heutigen Tag und die letzten 7 Tage aus, und die Ansicht **App** der lokalen Seite zeigt dasselbe. Die Zähldatei wird im Hintergrund geschrieben, höchstens einmal pro Minute und ein weiteres Mal beim Beenden. Eine Anfrage ist ein Modellaufruf, und eine Nachricht führt meist zu mehreren; die Ansicht App schlüsselt die heutigen Anfragen außerdem nach Zweck auf. Ein erzwungenes Beenden kann die Zählungen der letzten Minute verlieren.
- **Lernen und Gedächtnis.** Die eigenen Lernentscheidungen der Figur kosten je einen Aufruf von `PROMOTE_JUDGE_MODEL`, höchstens `PROMOTE_JUDGE_BATCH` alle `PROMOTE_JUDGE_INTERVAL_S`. Die Gedächtniskonsolidierung kostet einen Aufruf von `LLM_JUDGE_MODEL` je Abschnitt eines Chats, höchstens 16 pro Chat und `MEMORY_CALLS_PER_DAY` (40) für alle Chats zusammen pro Tag. `PROMOTE_JUDGE_ENABLED=false` und `MEMORY_CALLS_PER_DAY=0` schalten sie aus.
- **Die Skripte in `tools/`** unterscheiden sich. Manche sind kostenlos, manche rufen ein Modell auf. Die Tabelle in [tools.md](tools.de.md) gibt an, welche.
- **`personagent eval`** ruft das Modell für jeden Fall auf, außer in der Suite `memory`, die offline mit vorgegebenen Antworten läuft. Die Persona- und Lern-Suiten benötigen außerdem ein zweites Modell als Richter (`BENCH_JUDGE_MODEL`).
- **Speicher.** Ab 256 Gesprächen mit Namensraum (nicht QQ) wird das am längsten untätige Gespräch aus dem Arbeitsspeicher entfernt und verliert seine ausstehenden Reaktionen. Seine noch nicht konsolidierten Nachrichten werden zuvor konsolidiert, und seine letzten Nachrichten bleiben 72 Stunden lang in `runtime/recent.json`, sofern nicht `MEMORY_KEEP_RECENT=false` gesetzt ist. Fakten, Ereignisse, Kernnotizen und Lernprotokolle bleiben erhalten. Ein Gespräch mitten in einer Anfrage wird nie verdrängt. Langzeiterinnerungen werden beim Start von der Platte geladen und fallen nicht unter diese Grenze.
- **Platte.** Das Beweis-Log und das Kandidatenregister in `runtime/` werden nur angehängt und nie gekürzt. `personagent doctor` meldet jedes davon ab 50 MB (`LEDGER_EVIDENCE_WARN_BYTES`, `LEDGER_CANDIDATES_WARN_BYTES`). Die Gedächtnisdateien bleiben klein: `recent.json` enthält die Chats, die in den letzten 72 Stunden aktiv waren, und `memory_trash.jsonl` bewahrt entfernte Einträge höchstens 30 Tage lang auf. Vor der ersten Änderung eines jeden Tages werden `memory.json`, `core_memory.json` und `episodes.json` in eine gleichnamige Datei mit der Endung `.bak` kopiert, und der erste Start dieser Version bewahrt die alte Gedächtnisdatei als `memory.json.pre-v2` auf. Nach **Diesen Chat vergessen** oder einem im Chat verlangten Vergessen werden die `.bak`-Kopien aus den aktuellen Dateien neu geschrieben, und `memory.json.pre-v2` verliert das Vergessene, sodass keine Kopie der Gedächtnisdateien es behält; eine früher erstellte Sicherung enthält es jedoch weiterhin, ebenso der eigene Chat der Seite (`runtime/desktop/browser-chat.json`) bis **Neuer Chat** oder **Chats dieser Seite vergessen**, ausgenommen das, was ein in diesem Chat verlangtes Vergessen daraus entfernt hat. Sichern Sie `runtime/`, denn der Ordner enthält alles, was der Bot gelernt hat und sich merkt.
- **Chatprotokoll.** Das Protokoll jedes Chats in `runtime/log/` bewahrt seine Zeilen `MEMORY_LOG_DAYS` (30) Tage lang und höchstens 5.000 Zeilen auf und wird einmal täglich bereinigt. Es hat keine `.bak`-Kopie, kommt nie in eine Sicherung, und jede Art des Vergessens erfasst es. Der Abgleich von Fakten damit läuft in den Konsolidierungsaufrufen mit, und ein ruhiger Chat erhält höchstens einen Aufruf nur für den Abgleich am Tag, innerhalb von `MEMORY_CALLS_PER_DAY`. Eine Sicherung enthält jedoch `recent.json` und `pending_reactions.json`, die aktuellen Chattext aufbewahren.

## Wenn der Bot verstummt

Die Ursachen stehen nach Häufigkeit geordnet. Wenn die lokale Seite den Agenten ausführt, zeigt [Aktivität](guide.de.md#aktivität), ob Nachrichten ankommen und warum er still blieb. Auf einem Server lesen Sie das Protokoll des Dienstes und verwenden `personagent learned` für das Gelernte.

1. **Es kommt nichts an.** Prüfen Sie auf der lokalen Seite, ob die Plattform als verbunden angezeigt wird, und lesen Sie `runtime/desktop/direct.log` oder `astrbot.log`. Der offizielle QQ-Bot muss Mitglied der Gruppe sein, und QQ entscheidet, welche Gruppennachrichten er erhält. Ein persönlicher WeChat-Bot erhält nie Gruppennachrichten. In einem AstrBot, das Sie betreiben, füllen Sie `groups` des Plugins aus (und `dm_users` für DMs) und entfernen für NapCat `aiocqhttp` aus `excluded_platforms`. Die Satori- und Matrix-Konnektoren haben eigene Zulassungslisten in ihrer `.env`; siehe deren READMEs. In diesem Fall erscheint der Chat nie in Aktivität.
2. **Der Agent ist deaktiviert.** Das Banner bei `personagent run` zeigt `agent: OFF` und nennt den Grund und die Abhilfe. Fehlt `LLM_API_KEY`, fügen Sie auf der lokalen Seite einen Schlüssel hinzu (oder setzen Sie `LLM_API_KEY`) und starten Sie neu. Bei `AGENT_ENABLED=false` setzen Sie den Wert in `<home>/.env` auf `true` und starten neu. Bis dahin erhält jedes Ereignis `owned: false`, und das erste protokolliert eine einzelne ERROR-Zeile mit demselben Rat.
3. **AstrBots eigenes Modell antwortet stattdessen.** Das Plugin hat auf AstrBot zurückgegriffen, weil die Anfrage fehlschlug, personagent die Nachricht abgewiesen hat (Punkt 5) oder der Agent deaktiviert ist (Punkt 2). AstrBots Log zeigt `refusing unsafe personagent_url`, `agent refused the request (403): <message>` (oder einen anderen Status, siehe die Tabelle unten) oder `timed out waiting for the agent`. `timeout_s` muss die Entprellung und die Modellaufrufe des Durchgangs abdecken, außerdem den Durchgang, der beim Eintreffen der Nachricht noch lief. Die Modellaufrufe eines Durchgangs teilen sich 1,5 × `LLM_TIMEOUT_S`, in einer Gruppe wie in einer DM; halten Sie 3 × `LLM_TIMEOUT_S` daher unter diesem Wert. Sein Standardwert (420) deckt den Standardwert des Agenten ab (3 × 120 = 360 s). Erhöhen Sie ihn, wenn Sie `LLM_TIMEOUT_S` erhöhen.
4. **Er wurde nicht angesprochen.** In einer Gruppe antwortet er auf seinen Namen (`PERSONA_NAME`) oder ein @. Andernfalls wartet er auf ausreichend Gesprächsaktivität (`CHAT_TRIGGER_COUNT`, standardmäßig 30 Nachrichten) und kann dennoch schweigen. Von 02:00 bis 07:00 in seiner Zeitzone beteiligt er sich in der Regel nicht an Chats, in denen er nicht angesprochen wurde. Die Zeitzone ist `PERSONA_TZ_OFFSET_HOURS`. Leer ist sie UTC+8, wenn `AGENT_LANG` `zh` oder `zh-TW` ist, sonst der Versatz dieses Rechners. Eine Gruppennachricht, die mehr als 10 Minuten nach dem Senden eintrifft, und zwar innerhalb von zwei Minuten nach der ersten Nachricht ihrer Plattform seit dem Start, ist ein Rückstau: Sie wird als Kontext aufbewahrt und nicht beantwortet, und das Dienstprotokoll vermerkt dies. **Aktivität** zeigt den Grund für jeden der letzten Durchgänge. Um dieselbe Entscheidung offline nachzuvollziehen, führen Sie `personagent chat --trigger 4` aus.
5. **personagents Zulassungslisten.** `ACCESS_GROUPS` und `ACCESS_DM_USERS` gelten auf jedem Weg, und eine QQ-DM mit bloßer ID erfordert zusätzlich den Administrator oder einen Eintrag. Eine von ihnen abgewiesene Nachricht wird nicht übernommen, sodass über AstrBot dessen Modell antworten kann. personagent protokolliert jedes abgelehnte Gespräch einmal, auf INFO, mit der Einstellung, die es abgelehnt hat. Auf einer in `ACCESS_APPROVAL_PLATFORMS` aufgeführten Plattform wartet ein Chat, der in keiner der beiden Listen steht, stattdessen auf Freigabe: `personagent access` listet ihn auf, und das Protokoll vermerkt „waiting for the admin's approval“.
6. **Der Modellaufruf schlägt fehl.** Ein abgelehnter Schlüssel (401 oder 403) oder ein leeres Guthaben (402 oder erschöpftes Kontingent) protokolliert eine ERROR-Zeile, die den Anbieter-Host und die zu korrigierende Einstellung nennt. Führen Sie `personagent doctor` aus. Der Befehl sendet eine minimale Anfrage an jeden Modell-Endpunkt und zeigt den Status, was auch ein falsches `LLM_BASE_URL` oder `LLM_MODEL` aufdeckt. Überschreitet das Hauptmodell die Zeit oder bricht die Verbindung ab und nennt `LLM_FALLBACK_MODEL` ein anderes Modell, wechselt der Aufruf sofort zum Ersatzmodell, sodass der Durchgang dennoch innerhalb seines Zeitbudgets beantwortet wird. Ein Fehler, den ein Anbieter innerhalb einer normalen Antwort sendet, etwa die Upstream-Fehler von OpenRouter, wird wie der entsprechende HTTP-Fehler behandelt. Solange das Modell ausgefallen ist, sendet die Figur eine kurze, zur Rolle passende Ausrede, wenn sie angesprochen wird, höchstens einmal pro Gespräch alle fünf Minuten; **Aktivität** zeigt den Durchgang als „das Modell hat nicht geantwortet“.
7. **Eine falsch geschriebene Einstellung.** Das Start-Log und `personagent doctor` listen jeden Schlüssel, den `.env.example` nicht kennt, und jeden Wert, der mit `#` beginnt.
8. **Ein BOM in `.env`.** Der Name der ersten Einstellung trägt das BOM und erreicht den Prozess nie. Der Start und `personagent doctor` melden es. Speichern Sie die Datei erneut als UTF-8 ohne BOM.
9. **`QQ_BOT_ID` nicht gesetzt oder falsch bei NapCat.** Über AstrBot funktionieren @-Erwähnungen weiterhin, doch der Durchlauf für verpasste Erwähnungen gleicht mit diesem Wert ab. Beim direkten OneBot-Eingang wird eine @-Erwähnung nie erkannt. Der Bot startet fehlerfrei, protokolliert nichts und antwortet nie. `personagent doctor` warnt, wenn `QQ_BOT_ID` leer ist und andere QQ-Einstellungen gesetzt sind. Der offizielle QQ-Bot nutzt es nicht.
10. **Er antwortet, hat aber vergessen, was er gelernt hat.** Entweder kommt NapCat-QQ ohne `CONNECTOR_QQ_PLATFORMS=aiocqhttp` an, oder `PERSONA_NAME` oder `PERSONA_VERSION` hat sich geändert, wodurch eine neue Figur beginnt. Das Protokoll warnt, wenn das übernommene Material der alten Figur insgesamt verworfen wird. Das Bearbeiten von `persona.txt`, auch im Feld **Persona** der Seite, lässt keine neue Figur beginnen. Überarbeitungen der Datei unter einem `PERSONA_VERSION` teilen sich einen Lernbereich (`runtime/persona_lineage.json`). Um Zeilen einzubeziehen, die unter einem Persona-Hash gelernt wurden, den die Abstammung nicht enthält, führen Sie `personagent learned lineage adopt <hash>` und anschließend `personagent learned rebuild` aus. Der Hash steht im Bereich des Kandidaten in `personagent learned show <id>`. Ein Wechsel von `AGENT_LANG` zwischen Chinesisch und einer anderen Sprache schaltet auch auf die anderen Lerndateien in `runtime/` um.

Fehler von `/v1/events` stehen unten. Das AstrBot-Plugin protokolliert die Meldung, und `code` ist das stabile Feld, nach dem ein Client verzweigen kann.

| Status | `code` | Meldung in AstrBots Log | Ursache |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | kein `CONNECTOR_TOKEN`, und der Aufrufer ist nicht auf diesem Rechner |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | kein `CONNECTOR_TOKEN`, und die Anfrage kam über einen Browser, einen Proxy oder einen anderen Hostnamen |
| 403 | `invalid_envelope` | invalid request envelope: … | fehlendes oder falsches Token, Header oder Signatur, Uhren über 5 Min. auseinander, eine wiederverwendete Nonce oder ein voller Replay-Schutz (`connector replay guard full` im Log des Agenten) |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` weicht um mehr als `CONNECTOR_MAX_EVENT_AGE_S` (24 h) von jetzt ab, einschließlich zukünftiger oder Millisekunden-Zeitstempel |
| 400 | `invalid_schema` | invalid event schema: … | ein Pflichtfeld fehlt: `platform`, `conversation_type`, `sender_id`, `message_id`, `sent_at`, und `conversation_id` für Gruppen |
| 400 | `client_disconnected` | client disconnected | der Aufrufer hat die Verbindung während des Sendens getrennt |
| 408 | `body_timeout` | request body not received in time | die Übertragung des Body dauerte länger als 30 s |
| 413 | `body_too_large` | request body too large | über `SERVER_MAX_BODY_BYTES` (8 MB), meist ein eingebettetes Bild |
| 429 | `capacity_exceeded` | webhook capacity exceeded | über `CONNECTOR_MAX_INFLIGHT` laufende Durchgänge; nach 3 s erneut versuchen |

## Altlast: der direkte OneBot-Eingang

NapCats Webhook kann weiterhin Ereignisse an `POST /v1/onebot` senden, und personagent antwortet über `QQ_ONEBOT_URL`. Diese Route ist veraltet und bleibt während 1.x bestehen. Verwenden Sie stattdessen die Verbindung des offiziellen QQ-Bots oder NapCat über AstrBot mit `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Die Route warnt einmal bei der ersten Nutzung und markiert jede Response mit `Deprecation: true`.

Um auf NapCat über AstrBot umzusteigen, fügen Sie auf der lokalen Seite OneBot v11 (NapCat) hinzu oder führen für Ihr eigenes AstrBot `personagent connect astrbot <AstrBot data dir> --qq` aus und füllen die Zulassungslisten aus. Richten Sie NapCats WebSocket-Client darauf aus und deaktivieren Sie NapCats HTTP-Client (behalten Sie seinen HTTP-Server bei). Gedächtnis und Gelerntes bleiben erhalten, weil `CONNECTOR_QQ_PLATFORMS` die IDs behält.

Wenn Sie die alte Route noch verwenden:

- Richten Sie beide Richtungen ein, wie es [NapCats Dokumentation](https://napneko.github.io/) beschreibt. Sie benötigen einen **HTTP-Server** unter `QQ_ONEBOT_URL` zum Senden und einen **HTTP-Client**, der an `http://127.0.0.1:8080/v1/onebot` sendet (`SERVER_HOST`, `SERVER_PORT`). `QQ_ONEBOT_URL` ist standardmäßig leer; tragen Sie den Wert daher in `.env` ein. Ohne ihn empfängt der Bot Nachrichten, antwortet aber nie. Die Vorabprüfung und `personagent doctor` warnen, wenn diese Route konfiguriert aussieht (`QQ_BOT_ID` oder `QQ_ONEBOT_SECRET` gesetzt, `CONNECTOR_QQ_PLATFORMS` leer) und `QQ_ONEBOT_URL` leer ist.
- Wenn NapCat auf einem anderen Rechner läuft, setzen Sie `QQ_ONEBOT_SECRET` auf das `secret` des HTTP-Clients. Sonst kann jeder, der den Port erreicht, Ereignisse fälschen. Bodies müssen dann `x-signature: sha1=<hex>` tragen (403 `bad_signature`), und Ereignisse, deren Zeitstempel um mehr als fünf Minuten abweicht, erhalten 403 `stale_event`. Ohne das Secret antwortet die Route nur Programmen auf diesem Host, und bei einer Netzwerkbindung ist sie deaktiviert (403 `onebot_disabled`).
- Wenn AstrBot dasselbe Konto verwendet, belassen Sie `aiocqhttp` in `excluded_platforms`, da sonst jede Nachricht doppelt ankommt.

Prüfen Sie das Senden mit `curl http://127.0.0.1:3000/get_login_info`. Prüfen Sie den Empfang, indem Sie personagents Protokoll beobachten, während Sie dem Bot in einer Gruppe schreiben.
