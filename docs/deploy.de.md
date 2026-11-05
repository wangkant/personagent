# personagent bereitstellen

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · [繁體中文](deploy.zh-TW.md) · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · Deutsch · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

Der [Schnellstart](start.de.md) und das [Benutzerhandbuch](guide.de.md) bringen dich bis zum ersten Chat. Sie behandeln die Installation, den [Home-Ordner](guide.de.md#installation-und-der-home-ordner), die Einrichtung auf der lokalen Seite und das Verbinden einer Plattform. Dieser Leitfaden behandelt, was ein echter Betrieb braucht und was du prüfen solltest, wenn der Bot verstummt.

## Die kürzeste Konfiguration, die funktioniert

Die lokale Seite (`personagent`, oder `personagent init --terminal` für den Terminal-Assistenten) prüft den Schlüssel mit einer kleinen Anfrage und schreibt dann `.env` in den Home-Ordner. Chatten braucht einen Schlüssel, und `.env.example` startet dich mit den kostenlosen Modellen von OpenRouter:

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

Eine `.env`, die nur den Schlüssel setzt, bedeutet `https://api.deepseek.com` und `deepseek-flash`. Du kannst sie auf jeden OpenAI-kompatiblen Endpunkt richten, gehostet oder lokal (Ollama, llama.cpp). Füge die API-Adresse so ein, wie der Anbieter sie dokumentiert, entweder als Wurzel oder als versionierte Basis wie `.../v1` oder `.../api/paas/v4`. Bis du eine `persona.txt` schreibst, springt die mitgelieferte `data/persona.example.<lang>.txt` ein. Bis `PERSONA_NAME` gesetzt ist (die Einrichtung setzt es), heißt der Charakter „bot“.

Die Seite schreibt außerdem `PERSONA_NAME`, `AGENT_LANG` und ein `CONNECTOR_TOKEN`. Von der Seite verbundene Plattformen brauchen nichts weiter in `.env`. Ihre Zugangsdaten landen in `<home>/platforms/`: `direct.json` enthält die Plattformen, die personagent selbst verbindet, und das verwaltete AstrBot hält den Rest in seiner eigenen Konfiguration. Optionale Ergänzungen:

```
ADMIN_IDS=telegram:12345             # the admin's accounts, <platform>:<id>
# QQ through NapCat (OneBot) only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

Schlüssel bleiben auf diesem Rechner. Der gewählte Modellanbieter sieht die Gespräche. Alles andere in `.env.example` hat einen funktionierenden Standardwert. `SERVER_HOST` und `SERVER_PORT` sind `127.0.0.1:8080`, `QQ_ONEBOT_URL` ist leer (kein NapCat-HTTP-Server), und ein leeres `ACCESS_GROUPS` überlässt alle Gruppen dem Konnektor.

## Ausführen

`personagent` öffnet die lokale Seite. Solange die Seite offen ist, laufen der Agent, der Prozess für die direkt verbundenen Plattformen und, falls installiert, das verwaltete AstrBot. Erneutes Ausführen von `personagent` verwendet eine offene Seite wieder. `personagent up` startet dieselben Prozesse ohne Browser.

So oder so enden diese Prozesse mit ihm, egal wie es endet. Was ein früherer abgestürzter Lauf hinterlassen hat, wird beim nächsten Start gestoppt. Jeder Prozess schreibt sein Log nach `<home>/runtime/desktop/` (`agent.log`, `direct.log`, `astrbot.log`).

Die lokale Seite und `personagent up` fragen pypi.org höchstens einmal am Tag, ob ein neueres personagent erschienen ist. Wenn ja, zeigen die Ansicht Chat und das Terminal den Befehl, der diese Kopie aktualisiert. Die Anfrage enthält nur die Versionsnummer, und `UPDATE_CHECK_ENABLED=false` schaltet die Prüfung ab.

`personagent run` startet nur den Agenten, wie [Den Dienst ausführen](guide.de.md#den-dienst-ausführen) beschreibt. Nutze es, wenn deine eigenen Konnektoren (ein AstrBot, das du betreibst, Satori, Matrix) mit ihm sprechen. `personagent doctor` prüft die Einstellungen und testet jeden vorgelagerten Dienst.

**In 1.0 umbenannte Einstellungen.** Solange ein von 1.0 abgeschaffter Einstellungsname noch gesetzt ist, verweigert der Start mit Exit-Code 2 und listet jeden als `OLD -> NEW`. `personagent doctor --fix` benennt sie in `<home>/.env` um. Es behält Werte und Kommentare, speichert die alte Datei als `.env.bak` und kommentiert eine alte Zeile aus, deren neuer Name schon gesetzt ist. Ein abgeschaffter Name, der in der Umgebung statt in `.env` gesetzt ist, muss dort umbenannt werden, wo er gesetzt ist. `personagent doctor` beendet sich mit 1, solange welche übrig sind, und `--json` listet sie unter `retired_settings`. `HOST`, `PORT` und `LOG_FILE` zählen nur, wenn sie in `.env` stehen.

### Aktivität

[Aktivität](guide.de.md#aktivität) ist eine Ansicht der lokalen Seite. Sie braucht keine zusätzliche Installation, lädt nichts aus dem Internet und zeigt nie Schlüssel oder Tokens. Sie liest die JSON-API des Agentendienstes, den die lokale Seite gestartet hat. Bei `personagent run` allein lies das Log des Dienstes und nutze stattdessen `personagent learned`. `DASHBOARD_ENABLED=false` schaltet die API ab. Die Ansicht sagt das dann, und `personagent doctor` gibt `activity: off (...)` aus.

Die API liegt unter `/api/dashboard/` auf dem Agentendienst:

- `GET status`, `GET conversations` und `GET conversation?id=<chat id>` lesen den Zustand des Dienstes, die ihm bekannten Chats und einen Chat im Detail.
- `POST candidates/<id>/promote`, `replace`, `reject` und `rollback` ändern, was er gelernt hat. Jede Änderung geht in dasselbe Register wie `personagent learned`, mit dem Akteur `dashboard`.

Jeder Aufruf braucht den Header `X-Personagent-Dashboard-Token` mit dem Token aus `dashboard.token` im Laufzeitordner (`<home>/runtime/`, sofern `AGENT_RUNTIME_DIR` ihn nicht verlegt). Nur der Besitzer kann die Datei lesen, und der Dienst legt sie beim Start an. Ein Aufruf ohne den Header bekommt 401 (`dashboard_token`), ein falsches Token 403 (`wrong_token`). `CONNECTOR_TOKEN` und `X-Personagent-Token` öffnen sie nicht. Sie gelten nur für Konnektoren und `/health/details`.

- Schreibzugriffe brauchen außerdem `X-Personagent-Dashboard: 1` und `Content-Type: application/json`. Wenn die Anfrage ein `Origin` sendet, muss es das des Dienstes sein.
- Websiteübergreifende Browser-Anfragen werden abgelehnt.
- Antworten ersetzen alle Zugangsdaten durch `***`. URLs in den Startprüfungen maskieren außerdem Benutzername, Passwort und Query.
- Skripte auf demselben Computer dürfen die API genauso aufrufen wie die lokale Seite.

Der Dienst liefert keine Seite aus. `GET /` antwortet mit einem kurzen Hinweis, der auf die lokale Seite und auf `personagent learned` verweist; das öffnet jetzt auch ein alter `?token=`-Link. Die lokale Seite bindet nur an 127.0.0.1. Auf einem Server ohne lokale Seite prüfst und überstimmst du Gelerntes mit `personagent learned`.

## Was der Host bereitstellen muss

1. **Ein beschreibbares Home.** Der Start legt eine Sperre unter `<home>/.personagent.instance.lock` an, außerhalb von `runtime/`. Ein schreibgeschütztes Home startet nicht.
2. **Ein Prozess pro Home.** Ein zweites `personagent run` auf demselben Home beendet sich mit einem Satz, der das sagt.
3. **Ein freier Port.** Ein belegter oder verbotener Port beendet ebenfalls mit einem Satz. Wähle einen anderen mit `--port` oder `SERVER_PORT`.

`AGENT_RUNTIME_DIR` muss sich unterhalb des Home auflösen, sonst schlägt der Start fehl. Ein relatives `PERSONA_FILE` oder `PERSONA_CARD_FILE` löst sich ebenfalls unter dem Home auf, also braucht eine anderswo liegende Persona einen absoluten Pfad.

## Plattformen verbinden

Füge Plattformen unter **Apps verbinden** auf der lokalen Seite hinzu. personagent prüft die Zugangsdaten bei der Plattform, bevor es etwas speichert. Lehnt die Plattform sie ab, zeigt die Seite die Ablehnung und behält nichts.

**Von personagent selbst verbunden.** QQ, persönliches WeChat, Telegram und Discord laufen in einem „direct“-Prozess, ohne AstrBot und ohne NapCat.

| Plattform | Was du tust | Grenzen |
|---|---|---|
| QQ (offizieller Bot) | Scanne einen QR-Code mit mobilem QQ, das einen Bot erstellt oder einen von dir erstellten auswählt. Das Einfügen von AppID und AppSecret ist die Alternative. | Bis der Bot zertifiziert ist, lässt QQ ihn nur Gruppen beitreten, die dir gehören. Berechtigungen für Gruppennachrichten werden in QQ gesetzt. |
| Persönliches WeChat | Scanne mit WeChat (Tencents iLink-Bot-API). | Nur Einzelchats. WeChat gibt solchen Bots keine Gruppennachrichten. |
| Telegram | Füge das Token von @BotFather ein. | |
| Discord | Füge das Bot-Token ein, mit aktiviertem Message Content Intent. | |

**Über das verwaltete AstrBot.** Jede andere Plattform läuft über ein AstrBot, das personagent zusammen mit einer eigenen Python-3.12-Laufzeit herunterlädt und headless ausführt. Es hat kein Dashboard und braucht keine zweite Anmeldung. KOOK, Feishu/Lark (lange Verbindung), DingTalk (Stream-Modus), Slack (Socket Mode, und der Link im Leitfaden füllt die App vor), WeCom-KI-Bot (lange Verbindung), Mattermost und Misskey fragen nach ein oder zwei Werten. Die Gruppe Erweitert braucht eine öffentliche Adresse oder andere Software: WeCom-App, offizielles WeChat-Konto, QQ-Webhook, OneBot v11 (NapCat) und Satori. LINE wird nicht angeboten.

Auf beiden Wegen antwortet eine verbundene Plattform in jeder Gruppe und jeder DM, die die Plattform dem Bot zustellt. Das ändert sich, sobald `ACCESS_GROUPS` oder `ACCESS_DM_USERS` einen Eintrag für diese Plattform enthält (siehe [personagents eigene Zulassungslisten](#über-ein-astrbot-das-du-schon-betreibst)). IDs kommen als `<platform>:<id>` an, zum Beispiel `qq_official:<openid>`, `weixin_oc:<id>`, `telegram:<id>` und `discord:<id>`. Der offizielle QQ-Bot sieht openids, keine QQ-Nummern. Eine Plattform direkt zu verbinden entfernt eine AstrBot-Verbindung für dieselbe Plattform.

## Über ein AstrBot, das du schon betreibst

AstrBot, NapCat (OneBot), Koishi (über den [Satori-Konnektor](../integrations/satori/README.de.md)) und Matrix (über den [Matrix-Konnektor](../integrations/matrix/README.de.md) und mautrix-Bridges) sind Drittanbieter-Bridges, mit denen personagent zusammenarbeitet. Keine davon ist für QQ, WeChat, Telegram oder Discord nötig.

AstrBot übergibt Nachrichten über ein Plugin in `integrations/astrbot/astrbot_plugin_personagent/` an personagent. Das Plugin sendet jede Nachricht an `POST /v1/events` und leitet die Antworten aus der Response weiter. Es holt außerdem personagents Outbox ab (`outbox_enabled`, standardmäßig an), sodass die Persona zuerst sprechen kann, wo die Plattform das einem Bot erlaubt. Das Plugin-README enthält die Tabelle. Das verwaltete AstrBot bekommt das Plugin automatisch. Starte dein eigenes AstrBot einmal, damit es seinen Datenordner anlegt (den mit `cmd_config.json`, `plugins/` und `config/`), und führe dann aus:

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

Der Befehl kopiert das Plugin nach `<data dir>/plugins/` und schreibt ein gemeinsames `CONNECTOR_TOKEN` in `.env` und in die Plugin-Konfiguration. Er setzt `personagent_url` auf `http://127.0.0.1:<SERVER_PORT>`, sofern das Plugin nicht schon eine akzeptierte URL hat (eine Loopback-URL, Tunnel eingeschlossen, oder HTTPS).

Für ein AstrBot auf einem anderen Rechner lade `astrbot_plugin_personagent.zip` aus dem [neuesten Release](https://github.com/wangkant/personagent/releases/latest) herunter und lade es unter **Install from File** auf AstrBots Plugin-Seite hoch. Setze sein `connector_token` auf das `CONNECTOR_TOKEN` aus personagents `.env`, und `personagent_url` auf eine HTTPS-Adresse für personagent (siehe [Die Endpunkte freigeben](#die-endpunkte-freigeben)).

Führe nach einem personagent-Upgrade `connect astrbot` erneut aus oder lade das neue Zip hoch. AstrBot 4.29 und neuer ersetzen die installierte Kopie. Bei älteren Versionen deinstalliere es zuerst und lass **Also delete plugin configuration file** deaktiviert.

Optionen für `connect astrbot`:

- `--qq` nimmt `aiocqhttp` aus `excluded_platforms`, und `--no-qq` setzt es zurück. Ohne beide bleibt das QQ-Routing, wie es ist. `CONNECTOR_QQ_PLATFORMS` folgt dem, was das Plugin am Ende tut.
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>` schaltet diesen Adapter auch in AstrBots eigener Konfiguration ein. Slack nimmt zusätzlich `--app-token`, Lark und QQ nehmen `--app-id` und `--app-secret`. Ein vorhandener Adaptereintrag behält seine anderen Einstellungen (Proxy, Basis-URL, Polling) und bekommt nur die neuen Zugangsdaten.
- `--url https://...` setzt eine HTTPS-Adresse, an die das Plugin sendet.
- `--install` lädt stattdessen ein verwaltetes AstrBot herunter, und `--start` startet es.

Der erste Lauf lässt die Zulassungslisten leer. Ein erneuter Lauf behält sie, zusammen mit anderen ausgeschlossenen Plattformen.

Das Plugin verweigert standardmäßig. Fülle `groups`, und `dm_users` für DMs, in AstrBots WebUI aus, oder beantworte die Fragen von `connect`. DMs werden weitergeleitet, sobald `dm_users` nicht leer ist. Das [Plugin-README](../integrations/astrbot/astrbot_plugin_personagent/README.de.md) listet alle Schlüssel. Das verwaltete AstrBot öffnet jede verbundene Plattform mit `<platform>:*`. Starte nach der Plugin-Installation AstrBot neu oder lade die Plugins in seiner WebUI neu. Auf der personagent-Seite:

- `CONNECTOR_TOKEN` authentifiziert jede Anfrage. Die Anfrage trägt den Header `X-Personagent-Token` und einen HMAC-SHA256, mit dem Token als Schlüssel, über `timestamp.nonce.body`, und ein Replay-Schutz lehnt wiederverwendete Nonces ab. Eine abgefangene Anfrage kann weder wiederholt noch verändert werden. Das Token ist auch der Signaturschlüssel, also halte es aus Logs heraus und tausche es, wenn es durchsickert. Auf einem Host ist es optional, über Hosts hinweg Pflicht.
- `ADMIN_IDS` listet die Konten des Admins als `<platform>:<id>` (`telegram:12345`, `discord:4242`). Eine bloße ID oder `qq:<id>` ist eine QQ-Nummer. `ADMIN_NAME` setzt den Namen des Admins. Alle gelisteten Konten gehören einer Person, die in Gruppen und DMs die vertrautere Persona bekommt, verwalten darf, was der Bot sich über eine Gruppe merkt, und ihn allein unterrichten darf. Über AstrBot ist die Plattform der Adaptername, den AstrBot anzeigt, und `/sid` in einem Chat zeigt eine ID.
- `ACCESS_GROUPS` und `ACCESS_DM_USERS` lassen personagent eine Plattform selbst einschränken, in derselben Form `<platform>:<id>`. Jede Plattform wird getrennt eingeschränkt. Eine Plattform ohne Einträge bleibt dem Konnektor überlassen, und schon ein Eintrag beschränkt diese Plattform auf ihre Einträge. Ein Zug, den personagent ablehnt, geht unbeansprucht zurück, also kann AstrBots eigenes Modell antworten.

Für AstrBot in Docker oder auf einem anderen Host siehe [das Benutzerhandbuch](guide.de.md#brücken-die-du-selbst-betreibst).

### QQ über NapCat (OneBot)

Dieser Weg nutzt ein persönliches QQ-Konto statt eines offiziellen Bots. Du brauchst ein zweites QQ-Konto in den Zielgruppen, nicht dein eigenes (siehe [DISCLAIMER.md](DISCLAIMER.de.md)). Es meldet sich, meist per QR-Code und in einer Sitzung, die Neustarts übersteht, bei einer OneBot-v11-Implementierung an, die mit AstrBots Adapter `aiocqhttp` verbunden ist. [NapCat](https://github.com/NapNeko/NapCatQQ) ist getestet und hängt sich an den QQ-NT-Desktop-Client. LLOneBot und Lagrange sind weitere OneBot-v11-Implementierungen.

Beim verwalteten AstrBot füge auf der lokalen Seite **Erweitert > OneBot v11 (NapCat)** hinzu und richte NapCat auf `ws://127.0.0.1:6199/ws`. Die [chinesische Anleitung](deploy.zh-CN.md) führt Schritt für Schritt durch. Bei deinem eigenen AstrBot entferne `aiocqhttp` aus `excluded_platforms` des Plugins, setze `CONNECTOR_QQ_PLATFORMS=aiocqhttp` (`--qq` macht beides) und setze `QQ_BOT_ID` (`personagent connect astrbot` fragt danach).

**`CONNECTOR_QQ_PLATFORMS` ist hier Pflicht.** Ohne es kommen QQ-IDs mit Namensraum an (`aiocqhttp:123456`), und jedes Gespräch wirkt neu. Gedächtnis, Verlauf und gelernte Beispiele sind nach der bloßen ID verschlüsselt, und die Register leiten Zeilen-IDs aus der Gesprächs-ID ab, also lässt sich die Spaltung später nicht reparieren.

Bloße IDs tragen QQ-Befugnis, also gelten die QQ-Einträge von `ADMIN_IDS`, `ACCESS_GROUPS` und `ACCESS_DM_USERS` zusätzlich zu den Zulassungslisten des Plugins. Eine QQ-DM muss in `dm_users` stehen *und* vom Admin oder einem Eintrag in `ACCESS_DM_USERS` kommen. Wenn `ACCESS_GROUPS` QQ-Gruppen enthält, muss eine QQ-Gruppe in beiden stehen. Nimm eine Plattform nur dann in `CONNECTOR_QQ_PLATFORMS` auf, wenn du ihrem Konnektor diese Befugnis anvertraust.

**NapCats HTTP-Server** (`QQ_ONEBOT_URL`, standardmäßig leer) ist auf diesem Weg optional. personagent sendet auch von sich aus Nachrichten:

- proaktive Nachrichten (`PROACTIVE_ENABLED`, standardmäßig aus);
- die Frage zwei Minuten nach einer Ablehnung (`REACT_ELICIT_ENABLED`);
- die Ausrede, die in einer Gruppe gesendet wird, wenn der Modellaufruf fehlschlägt.

Diese gehen über die Outbox des Plugins zurück, solange das Plugin sie abholt. Wenn nicht, gehen sie an `QQ_ONEBOT_URL`, falls die URL gesetzt ist. Nur der Durchlauf für offline verpasste @-Erwähnungen braucht den Server, zusammen mit `QQ_BOT_ID`. Der Durchlauf läuft beim Start und dann alle 30 Minuten. Er umfasst die QQ-Gruppen in `ACCESS_GROUPS` plus jede Gruppe mit Aktivität seit dem letzten Neustart und spielt @-Erwähnungen ab, die jünger als eine Stunde sind. Bei leerer URL zeigt `personagent doctor` die OneBot-Bridge als „not configured“.

**Auf jedem Konnektor-Weg verloren** (direkt, AstrBot oder anderer Konnektor), ohne Einstellung, die es zurückbringt:

- der OCR-Rückfall für Bilder, die kein Vision-Modell beschrieben hat;
- die Zitat-Suche über NapCat. Zitate werden aus personagents eigenem Index der letzten Nachrichten aufgelöst und aus dem zitierten Text, den ein Konnektor mit dem Zitat sendet;
- das Sammeln neuer Sticker aus in Gruppen geposteten Bildern.

## Mehr als eine Plattform

Mehrere Konnektoren können nebeneinander gegen ein personagent laufen, weil jeder seine Plattform benennt (`telegram:-1001234`, `matrix:!room:example.org`). Der direct-Prozess, AstrBot, Satori und Matrix können alle gleichzeitig laufen. Führe einen Chat nicht über zwei Konnektoren herein, sonst kommt jede Nachricht zweimal an. IDs mit Namensraum kollidieren nie mit einer bloßen QQ-Nummer.

Nachrichten, um die niemand gebeten hat, erreichen eine Plattform über einen Konnektor, der personagents Outbox abholt. Das sind proaktive Einstiege, die Frage nach einer Ablehnung und die Ausrede, wenn der Modellaufruf in einer Gruppe fehlschlägt. Die Ausrede einer DM geht in der Response auf die Anfrage zurück, die die Nachricht gebracht hat.

Der direct-Prozess und die drei Konnektoren hier holen alle die Outbox ab, auf Plattformen, auf denen ein Bot zuerst schreiben darf. QQ begrenzt die Rate unaufgeforderter Nachrichten eines offiziellen Bots, und eine Person kann sie abschalten. Ein eigener Konnektor sendet `connector_id`, `reply_handle` und `"capabilities": ["outbox"]` mit seinen Ereignissen und macht Long-Polling auf `/v1/outbox` (siehe [das Konnektor-Protokoll](connectors.de.md)). Ohne einen solchen Konnektor spricht personagent nur innerhalb der Anfrage, die eine Nachricht gebracht hat. Die proaktiven Schleifen überspringen diese Gespräche, und die Frage und die Ausrede werden nicht gesendet.

`PROACTIVE_PLATFORMS` begrenzt, wo die proaktive Schleife zuerst sprechen darf. `PROACTIVE_PLATFORMS=qq_official` hält sie beim offiziellen QQ-Bot, und `qq` bei QQ über NapCat. `CONNECTOR_OUTBOX_ENABLED=false` schaltet die Outbox ganz ab.

Um ohne die Outbox in einer DM zuerst zu sprechen, kann dein eigener Scheduler (eine AstrBot-Plugin-Aufgabe, ein Cron-Eintrag) ein DM-Ereignis senden, das mit `"proactive": true` markiert ist. Siehe [Zuerst sprechen ohne die Outbox](connectors.de.md#zuerst-sprechen-ohne-die-outbox).

## Die Endpunkte freigeben

Behalte `SERVER_HOST=127.0.0.1`, wenn Konnektor und personagent sich einen Rechner teilen. Ein Container zählt nur mit dem Netzwerk-Namensraum des Hosts oder Host-Networking als derselbe Rechner. Die lokale Seite und `personagent up` binden immer an `127.0.0.1`. Andernfalls:

1. Setze `SERVER_HOST=0.0.0.0` (oder `--host 0.0.0.0`) und `CONNECTOR_TOKEN`. Der Start verweigert eine Netzwerkbindung ohne das Token. `QQ_ONEBOT_SECRET` verlangt er nicht, aber ohne es ist das veraltete `/v1/onebot` bei einer Netzwerkbindung aus. Jede Anfrage daran bekommt 403 `onebot_disabled`, und das Log nennt den Grund einmal.
2. Setze einen HTTPS-Reverse-Proxy oder einen privaten Tunnel davor. Alle Konnektoren hier senden nur an Loopback oder an HTTPS mit gesetztem Token. Das AstrBot-Plugin protokolliert alles andere als `refusing unsafe personagent_url`, und die Satori- und Matrix-Konnektoren verweigern den Start.
3. Lass den Body byte-genau unverändert, weil die Signatur ihn abdeckt, und halte die Uhren innerhalb von fünf Minuten zueinander.

Ist ein Zugangsdatum leer, bedient sein Endpunkt nur lokale Programme, die `http://127.0.0.1` oder `http://localhost` direkt aufrufen. Eine Anfrage bekommt 403 `non_local_request`, wenn sie eines der folgenden hat:

- einen `Origin`-Header;
- ein `Sec-Fetch-Site` außer `none`;
- einen `Host` außer `localhost`, `127.0.0.1` oder `::1`;
- einen Proxy-Header: `X-Forwarded-For`, `Forwarded`, `X-Real-IP`, `CF-Connecting-IP`, `Via`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP` oder `X-Original-Forwarded-For`.

Ein Proxy auf demselben Host, der nichts davon hinzufügt, wirkt weiterhin lokal. Setze `CONNECTOR_TOKEN` (und `QQ_ONEBOT_SECRET`, falls du `/v1/onebot` nutzt), bevor du einen Proxy oder Tunnel hinzufügst, auch auf einem einzelnen Host.

## Health-Endpunkte

- `GET /health` ist kostenlos und offen und ruft nichts auf.
- `GET /health/details` testet die vorgelagerten Dienste (60 s im Cache). Bei leerem `CONNECTOR_TOKEN` antwortet es nur auf lokale Anfragen. Mit gesetztem Token antwortet es **nur** auf Anfragen mit passendem `X-Personagent-Token`-Header, selbst von Loopback. Es gibt 503 zurück, wenn ein kritischer Test fehlschlägt oder nicht laufen kann. Die kritischen Tests sind die Chat-Modelle und, wenn QQ den direkten OneBot-Eingang nutzt (`QQ_BOT_ID` und `QQ_ONEBOT_URL` gesetzt, `CONNECTOR_QQ_PLATFORMS` nicht gesetzt), die OneBot-Bridge.
- `personagent doctor [--json]` führt dieselben Tests plus die Einstellungsprüfung aus und endet im selben Fall mit einem Wert ungleich null. Wenn die letzte Update-Prüfung einen Tag her ist, fragt es pypi.org auch nach der neuesten Version (`UPDATE_CHECK_ENABLED=false` lässt das aus).

## Kosten

- **Tests kosten Guthaben.** `personagent doctor` und `/health/details` senden eine winzige Chat-Completion an jeden konfigurierten Modell-Endpunkt (Chat, DM, Auswertung und Vision). Sie senden außerdem ein Embedding, wenn `EMBEDDING_MODEL` gesetzt ist, und eine Tavily-Suche, wenn `TAVILY_API_KEY` gesetzt ist. `/health` und die Einstellungs- und Register-Prüfungen sind kostenlos.
- **Die Skripte in `tools/`** unterscheiden sich. Manche sind kostenlos, manche rufen ein Modell auf. Die Tabelle in [tools.md](tools.de.md) sagt welche.
- **`personagent eval`** ruft das Modell für jeden Fall auf. Die Persona- und Lern-Suiten brauchen außerdem ein zweites Modell als Richter (`BENCH_JUDGE_MODEL`).
- **Speicher.** Ab 256 Gesprächen mit Namensraum (nicht QQ) verliert das am längsten untätige Gespräch seinen jüngsten Verlauf und seine ausstehenden Reaktionen. Langzeiterinnerungen, Kernnotizen und Register bleiben. Ein Gespräch mitten in einer Anfrage wird nie verdrängt. Langzeiterinnerungen werden beim Start von der Platte geladen und fallen nicht unter diese Grenze.
- **Platte.** Das Beweis-Log und das Kandidatenregister in `runtime/` werden nur angehängt und nie gekürzt. `personagent doctor` meldet jedes davon ab 50 MB (`LEDGER_EVIDENCE_WARN_BYTES`, `LEDGER_CANDIDATES_WARN_BYTES`). Sichere `runtime/`, denn es enthält alles, was der Bot gelernt hat.

## Wenn der Bot verstummt

Die Ursachen stehen nach Häufigkeit geordnet. Wenn die lokale Seite den Agenten ausführt, zeigt [Aktivität](guide.de.md#aktivität), ob Nachrichten ankommen und warum er still blieb. Auf einem Server lies das Log des Dienstes und nutze `personagent learned` für das Gelernte.

1. **Nichts kommt an.** Prüfe auf der lokalen Seite, ob die Plattform als verbunden angezeigt wird, und lies `runtime/desktop/direct.log` oder `astrbot.log`. Der offizielle QQ-Bot muss in der Gruppe sein, und QQ entscheidet, welche Gruppennachrichten er bekommt. Ein persönlicher WeChat-Bot bekommt nie Gruppen. In einem AstrBot, das du betreibst, fülle `groups` des Plugins aus (und `dm_users` für DMs), und nimm für NapCat `aiocqhttp` aus `excluded_platforms`. Die Satori- und Matrix-Konnektoren haben eigene Zulassungslisten in ihrer `.env`. Siehe ihre READMEs. In diesem Fall erscheint der Chat nie in Aktivität.
2. **Der Agent ist aus.** Das Banner bei `personagent run` sagt `agent: OFF`, nennt den Grund und die Lösung. Ohne `LLM_API_KEY` füge auf der lokalen Seite einen Schlüssel hinzu (oder setze `LLM_API_KEY`) und starte neu. Bei `AGENT_ENABLED=false` setze es in `<home>/.env` auf `true` und starte neu. Bis dahin bekommt jedes Ereignis `owned: false`, und das erste protokolliert eine einzelne ERROR-Zeile mit demselben Rat.
3. **AstrBots eigenes Modell antwortet stattdessen.** Das Plugin ist zurückgefallen, weil die Anfrage fehlschlug, personagent die Nachricht abgewiesen hat (Punkt 5) oder der Agent aus ist (Punkt 2). AstrBots Log zeigt `refusing unsafe personagent_url`, `agent refused the request (403): <message>` (oder einen anderen Status, siehe die Tabelle unten) oder `timed out waiting for the agent`. `timeout_s` muss das Debounce und jeden Modellaufruf im Zug abdecken, also halte `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` darunter. Sein Standardwert (420) deckt die Standardwerte des Agenten ab (120 × 3 = 360 s). Erhöhe ihn, wenn du diese beiden erhöhst.
4. **Er wurde nicht gerufen.** In einer Gruppe antwortet er auf seinen Namen (`PERSONA_NAME`) oder ein @. Sonst wartet er auf genug Gespräch (`CHAT_TRIGGER_COUNT`, standardmäßig 30 Nachrichten) und kann trotzdem aussetzen. Von 02:00 bis 07:00 in seiner Zeitzone hält er sich meist aus Chats heraus, in die er nicht gerufen wurde. Die Zeitzone ist `PERSONA_TZ_OFFSET_HOURS`. Leer ist sie UTC+8, wenn `AGENT_LANG` `zh` oder `zh-TW` ist, sonst der Versatz dieses Rechners. Aktivität zeigt den Grund für jeden jüngsten Zug. Um dieselbe Entscheidung offline zu sehen, führe `personagent chat --trigger 4` aus.
5. **personagents Zulassungslisten.** `ACCESS_GROUPS` und `ACCESS_DM_USERS` gelten auf jedem Weg, und eine QQ-DM mit bloßer ID braucht zusätzlich den Admin oder einen Eintrag. Eine von ihnen abgewiesene Nachricht geht unbeansprucht zurück, also kann über AstrBot dessen Modell antworten. personagent protokolliert jedes abgelehnte Gespräch einmal, auf INFO, mit der Einstellung, die es abgelehnt hat.
6. **Der Modellaufruf schlägt fehl.** Ein abgelehnter Schlüssel (401 oder 403) oder ein leeres Guthaben (402 oder erschöpftes Kontingent) protokolliert eine ERROR-Zeile, die den Anbieter-Host und die zu korrigierende Einstellung nennt. Führe `personagent doctor` aus. Es sendet eine winzige Anfrage an jeden Modell-Endpunkt und zeigt den Status, was auch ein falsches `LLM_BASE_URL` oder `LLM_MODEL` aufdeckt. Solange das Modell ausgefallen ist, sendet die Persona eine kurze Ausrede im Charakter, wenn sie gerufen wird, höchstens einmal pro Gespräch alle fünf Minuten.
7. **Eine falsch geschriebene Einstellung.** Das Start-Log und `personagent doctor` listen jeden Schlüssel, den `.env.example` nicht kennt, und jeden Wert, der mit `#` beginnt.
8. **Ein BOM in `.env`.** Der Name der ersten Einstellung trägt das BOM und erreicht den Prozess nie. Der Start und `personagent doctor` melden es. Speichere die Datei erneut als UTF-8 ohne BOM.
9. **`QQ_BOT_ID` nicht gesetzt oder falsch bei NapCat.** Über AstrBot funktionieren @-Erwähnungen noch, aber der Durchlauf für verpasste Erwähnungen gleicht damit ab. Beim direkten OneBot-Eingang wird eine @-Erwähnung nie erkannt. Der Bot startet sauber, protokolliert nichts und antwortet nie. `personagent doctor` warnt, wenn `QQ_BOT_ID` leer ist und andere QQ-Einstellungen gesetzt sind. Der offizielle QQ-Bot nutzt es nicht.
10. **Er antwortet, hat aber vergessen, was er gelernt hat.** Entweder kommt NapCat-QQ ohne `CONNECTOR_QQ_PLATFORMS=aiocqhttp` an, oder `PERSONA_NAME` oder `PERSONA_VERSION` hat sich geändert, was einen neuen Charakter startet. Das Log warnt, wenn das beförderte Material des alten Charakters als Ganzes abgelehnt wird. `persona.txt` zu bearbeiten, auch im Feld Persona der Seite, startet keinen neuen Charakter. Ihre Überarbeitungen unter einem `PERSONA_VERSION` teilen einen Lernbereich (`runtime/persona_lineage.json`). Um Zeilen einzubeziehen, die unter einem Persona-Hash gelernt wurden, den die Abstammung nicht enthält, führe `personagent learned lineage adopt <hash>` und dann `personagent learned rebuild` aus. Der Hash steht im Bereich des Kandidaten in `personagent learned show <id>`. `AGENT_LANG` zwischen Chinesisch und einer anderen Sprache zu wechseln, schaltet auch auf die anderen Lerndateien in `runtime/` um.

Fehler von `/v1/events` stehen unten. Das AstrBot-Plugin protokolliert die Meldung, und `code` ist das stabile Feld, nach dem ein Client verzweigen kann.

| Status | `code` | Meldung in AstrBots Log | Ursache |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | kein `CONNECTOR_TOKEN`, und der Aufrufer ist nicht auf diesem Rechner |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | kein `CONNECTOR_TOKEN`, und die Anfrage kam über einen Browser, einen Proxy oder einen anderen Hostnamen |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | fehlendes oder falsches Token, Header oder Signatur, Uhren über 5 Min. auseinander, eine wiederverwendete Nonce oder ein voller Replay-Schutz (`connector replay guard full` im Log des Agenten) |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` weicht um mehr als `CONNECTOR_MAX_EVENT_AGE_S` (24 h) von jetzt ab, einschließlich zukünftiger oder Millisekunden-Zeitstempel |
| 400 | `invalid_schema` | invalid event schema | ein Pflichtfeld fehlt: `platform`, `conversation_type`, `sender_id`, `message_id`, `sent_at`, und `conversation_id` für Gruppen |
| 400 | `client_disconnected` | client disconnected | der Aufrufer hat beim Senden aufgelegt |
| 408 | `body_timeout` | request body not received in time | der Body brauchte mehr als 30 s |
| 413 | `body_too_large` | request body too large | über `SERVER_MAX_BODY_BYTES` (8 MB), meist ein eingebettetes Bild |
| 429 | `capacity_exceeded` | webhook capacity exceeded | über `CONNECTOR_MAX_INFLIGHT` laufende Züge; nach 3 s erneut versuchen |

## Altlast: der direkte OneBot-Eingang

NapCats Webhook kann weiterhin Ereignisse an `POST /v1/onebot` senden, und personagent antwortet über `QQ_ONEBOT_URL`. Diese Route ist veraltet und bleibt während 1.x bestehen. Nutze stattdessen die Verbindung des offiziellen QQ-Bots oder NapCat über AstrBot mit `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Die Route warnt einmal bei der ersten Nutzung und markiert jede Response mit `Deprecation: true`.

Um auf NapCat über AstrBot umzusteigen, füge auf der lokalen Seite OneBot v11 (NapCat) hinzu, oder führe für dein eigenes AstrBot `personagent connect astrbot <AstrBot data dir> --qq` aus und fülle die Zulassungslisten aus. Richte NapCats WebSocket-Client darauf und schalte NapCats HTTP-Client ab (behalte seinen HTTP-Server). Gedächtnis und Gelerntes bleiben erhalten, weil `CONNECTOR_QQ_PLATFORMS` die IDs behält.

Wenn du die alte Route noch nutzt:

- Richte beide Richtungen ein, wie es [NapCats Dokumentation](https://napneko.github.io/) beschreibt. Du brauchst einen **HTTP-Server** unter `QQ_ONEBOT_URL` zum Senden und einen **HTTP-Client**, der an `http://127.0.0.1:8080/v1/onebot` sendet (`SERVER_HOST`, `SERVER_PORT`). `QQ_ONEBOT_URL` ist standardmäßig leer, also schreibe es in `.env`. Ohne es empfängt der Bot, antwortet aber nie. Die Vorabprüfung und `personagent doctor` warnen, wenn diese Route konfiguriert aussieht (`QQ_BOT_ID` oder `QQ_ONEBOT_SECRET` gesetzt, `CONNECTOR_QQ_PLATFORMS` leer) und `QQ_ONEBOT_URL` leer ist.
- Wenn NapCat auf einem anderen Rechner läuft, setze `QQ_ONEBOT_SECRET` auf das `secret` des HTTP-Clients. Sonst kann jeder, der den Port erreicht, Ereignisse fälschen. Bodies müssen dann `x-signature: sha1=<hex>` tragen (403 `bad_signature`), und Ereignisse mit mehr als fünf Minuten abweichendem Zeitstempel bekommen 403 `stale_event`. Ohne das Secret antwortet die Route nur Programmen auf diesem Host, und bei einer Netzwerkbindung ist sie aus (403 `onebot_disabled`).
- Mit AstrBot auf demselben Konto behalte `aiocqhttp` in `excluded_platforms`, sonst kommt jede Nachricht zweimal an.

Prüfe das Senden mit `curl http://127.0.0.1:3000/get_login_info`. Prüfe den Empfang, indem du personagents Log beobachtest, während du dem Bot in einer Gruppe schreibst.
