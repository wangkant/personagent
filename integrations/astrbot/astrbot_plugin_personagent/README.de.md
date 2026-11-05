# astrbot_plugin_personagent

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · Deutsch · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Dieses [AstrBot](https://github.com/AstrBotDevs/AstrBot)-Plugin verbindet AstrBot mit [personagent](https://github.com/wangkant/personagent). Es leitet jede erlaubte Nachricht an den Agenten weiter und schickt die Antworten des Agenten zurück in den Chat.

## Brauchst du es?

Für QQ, WeChat, Telegram oder Discord nicht. personagent verbindet sie selbst, ohne AstrBot. Führe `personagent` aus, um die lokale Seite zu öffnen, und füge sie unter **Apps verbinden** hinzu.

Du brauchst dieses Plugin, wenn AstrBot das Gespräch trägt. Das passiert in zwei Fällen.

- **Du fügst auf der personagent-Seite eine andere Plattform hinzu.** KOOK, Feishu/Lark, DingTalk, Slack, WeCom-KI-Bot, Mattermost, Misskey und die Plattformen unter Erweitert laufen alle über AstrBot. Die Seite lädt und startet ein AstrBot für dich und installiert dieses Plugin darin, du musst hier also nichts tun.
- **Du betreibst schon ein AstrBot** mit eigenen Plattformen und Plugins. Installiere das Plugin wie unten beschrieben.

## Was es tut

- Empfängt Gruppennachrichten und DMs von jedem Plattformadapter von AstrBot (Telegram, Discord, Slack, QQ, ...), außer denen in `excluded_platforms`.
- Leitet Nachrichten von Gruppen und Absendern auf der Zulassungsliste als plattformneutrales Ereignis an `POST /v1/events` des Agenten weiter. Es liest jede Plattform so, wie ihr Adapter sie liefert, einschließlich wer angesprochen wurde, was zitiert wurde, Sticker, Bilder, Sprachnachrichten und der Zeit, die die Plattform als Sendezeit nennt.
- Schickt die Antworten des Agenten über AstrBot in der Form zurück, die jede Plattform erwartet. Antworten können Text und Bilder enthalten und in Gruppenchats eine Erwähnung, wenn der Agent darum bittet.
- Fragt die Outbox des Agenten ab, um zuzustellen, was er von sich aus sagt, etwa einen geplanten Gesprächsanfang, eine Nachfrage oder die Ausrede, die er in einer Gruppe postet, wenn sein Modell ausgefallen ist. Siehe [Outbox](#outbox).
- Stoppt die eigene Pipeline von AstrBot, wenn der Agent das Gespräch übernimmt (`block_default`), sodass das eingebaute Modell von AstrBot nie anstelle der Persona antwortet.

Persona, Gedächtnis, Debounce und Tipp-Simulation laufen alle im Agenten. Dieses Plugin ist ein Konnektor im Sinne von [`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.de.md) des Agenten.

## In dein eigenes AstrBot installieren

Du brauchst AstrBot, mindestens einmal gestartet, damit sein Datenordner existiert, und personagent (`python -m pip install personagent`; siehe dessen README).

### Mit der personagent-Einrichtung

```bash
personagent connect astrbot
```

Der Befehl sucht zuerst den Datenordner von AstrBot, den Ordner mit `cmd_config.json`, `plugins/` und `config/`. Findet er keinen, bietet er an, AstrBot herunterzuladen. Dann fragt er, ob AstrBot in Docker läuft, welcher Chat-App der Bot beitritt (mit dem Token dieser App, wo AstrBot noch eines braucht), die Gruppen, den Admin und die Personen, die dem Bot DMs schicken dürfen. Für QQ über NapCat fragt er auch nach der Nummer des Bot-Kontos. Zuletzt kopiert er dieses Plugin, erzeugt ein gemeinsames Token, schreibt es auf beide Seiten und schreibt die Zulassungslisten. `personagent init --terminal` bietet denselben Schritt am Ende an.

Um die Fragen zu überspringen, übergib den Datenordner:

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

So ausgeführt lässt eine erste Verbindung die Zulassungslisten **leer**, und du füllst sie in den Plugin-Einstellungen aus. `personagent connect astrbot --help` listet die Flags, die auch eine Plattform in AstrBot einschalten.

Du kannst den Befehl jederzeit erneut ausführen. Er behält die Zulassungslisten, andere ausgeschlossene Plattformen und jede `personagent_url`, die dieses Plugin akzeptiert (siehe [Wo der Agent laufen kann](#wo-der-agent-laufen-kann)). Eine `personagent_url`, die das Plugin ablehnen würde, wird durch den Loopback-Standard ersetzt. Das QQ-Routing ändert sich nur, wenn du `--qq` oder `--no-qq` übergibst, und `CONNECTOR_QQ_PLATFORMS` des Agenten folgt ihm. Bei der Nachfrage sind die aktuellen Zulassungslisten die Standardwerte: Drücke die Eingabetaste, um eine zu behalten, oder tippe `-`, um sie zu leeren.

Starte dann AstrBot neu und starte den Agenten (siehe [Prüfen, ob es funktioniert](#prüfen-ob-es-funktioniert)).

### Über die WebUI von AstrBot

1. Lade `astrbot_plugin_personagent.zip` von der [neuesten personagent-Version](https://github.com/wangkant/personagent/releases/latest) herunter.
2. Lade es unter **Install from File** auf der Plugin-Seite von AstrBot hoch.
3. Setze `connector_token` auf das `CONNECTOR_TOKEN` in der `.env` von personagent und fülle die Zulassungslisten wie unten beschrieben aus.
4. Läuft AstrBot auf einem anderen Computer als personagent, setze `personagent_url` auf eine HTTPS-Adresse (siehe [Wo der Agent laufen kann](#wo-der-agent-laufen-kann)).

Zum Aktualisieren lade das Zip der neueren Version auf dieselbe Weise hoch. AstrBot 4.29 und neuer ersetzen die installierte Kopie. Bei älteren Versionen deinstalliere das Plugin zuerst und lass **Also delete plugin configuration file** deaktiviert.

### Von Hand

1. Kopiere diesen Ordner nach `<AstrBot data dir>/plugins/astrbot_plugin_personagent/`.
2. Starte AstrBot neu oder lade die Plugins in der WebUI neu. AstrBot installiert `requirements.txt`, die nur `httpx` listet.
3. Öffne die Einstellungen des Plugins in der WebUI. Sie werden in `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json` gespeichert.
   - Füge die Gruppen-IDs, denen die Persona beitreten darf, zu `groups` hinzu.
   - Füge die Absender-IDs, deren DMs sie beantworten darf, zu `dm_users` hinzu.
   - Wenn die `.env` des Agenten `CONNECTOR_TOKEN` setzt, trage denselben Wert in `connector_token` ein. Das ist Pflicht, wenn der Agent auf einem anderen Host läuft.
   - Lass `personagent_url` auf dem Standard, wenn der Agent auf demselben Host mit dem Standard `SERVER_PORT=8080` läuft.

Das Plugin **lehnt standardmäßig ab**. Mit leeren Zulassungslisten leitet es nichts weiter, und AstrBot verhält sich, als wäre das Plugin nicht installiert. Schreibe IDs so, wie AstrBot sie zeigt; sende `/sid` in einem Chat, um sie zu sehen. Eine ID ohne Präfix passt auf jedem Adapter. `qq_official:ID` passt nur auf diesem Adapter, und `qq_official:*` leitet dort jedes Gespräch dieser Art weiter.

Ein einzelnes `*` in `groups` oder `dm_users` leitet jedes Gespräch dieser Art auf jedem Adapter weiter und markiert es mit `prefiltered: false`. Dann entscheiden allein `ACCESS_GROUPS` und `ACCESS_DM_USERS` des Agenten. Der Agent lehnt eine Plattform ohne Einträge dort ab, außer QQ-Gruppen, denen er antwortet, solange `ACCESS_GROUPS` keine listet.

### Prüfen, ob es funktioniert

1. Starte den Agenten mit `personagent run`, das nur den Server startet. Sein Banner sollte `agent: on` zeigen.
2. Sage den Namen des Bots (das `PERSONA_NAME` des Agenten) in einer erlaubten Gruppe.

Kommt keine Antwort, suche nach `personagent:`-Zeilen im Log von AstrBot, lies dann, was `personagent run` nach seinem Banner ausgegeben hat, und sieh unter [Fehlerbehebung](#fehlerbehebung) nach.

## Konfiguration

| Schlüssel | Typ | Standard | Beschreibung |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | Basis-URL des Agenten. Das Plugin hängt `/v1/events` und `/v1/outbox` an. Muss Loopback sein oder HTTPS mit gesetztem `connector_token`. |
| `connector_token` | string | `""` | Gemeinsames Geheimnis. Muss zum `CONNECTOR_TOKEN` des Agenten passen. Pflicht für jede `personagent_url`, die nicht Loopback ist. |
| `timeout_s` | int | `420` | Wartezeit in Sekunden je Versuch. Siehe [Zeitlimits](#zeitlimits). |
| `excluded_platforms` | list | `["aiocqhttp"]` | Adapternamen, die nie weitergeleitet werden. Entferne `aiocqhttp`, um QQ (NapCat) über dieses Plugin zu führen. Siehe [QQ über NapCat](#qq-über-napcat). |
| `groups` | list | `[]` | Weiterzuleitende Gruppen-IDs. Leer leitet keine Gruppen weiter. `adapter:ID` oder `adapter:*` beschränkt einen Eintrag auf einen Adapter. Ein einzelnes `*` leitet alle Gruppen ungefiltert weiter. |
| `dm_users` | list | `[]` | Absender-IDs, deren DMs weitergeleitet werden. Leer leitet keine DMs weiter. `adapter:ID` oder `adapter:*` beschränkt einen Eintrag auf einen Adapter. Ein einzelnes `*` leitet alle DMs ungefiltert weiter. |
| `block_default` | bool | `true` | Stoppt die Pipeline von AstrBot, wenn der Agent das Gespräch übernimmt. |
| `forward_quoted_text` | bool | `true` | Sendet Text und Autor einer zitierten Nachricht zusammen mit ihrer ID, wo die Plattform sie liefert. Solange dies aktiv und `quote_max_chars` größer als 0 ist, deklariert jedes Ereignis die Fähigkeit `quote_text`. |
| `quote_max_chars` | int | `200` | Längster gesendeter zitierter Text. Längere Zitate werden gekürzt. |
| `max_inline_image_bytes` | int | `4000000` | Größtes inline gesendetes Bild. Bilder, die der Agent nicht selbst abrufen kann (Telegram, lokale Dateien, private Adressen), werden inline gesendet. Ein größeres kommt als Notiz `(sent an image)` an. Halte den Wert unter `VISION_MAX_IMAGE_BYTES` des Agenten. |
| `outbox_enabled` | bool | `true` | Die Outbox des Agenten abfragen und zustellen. Siehe [Outbox](#outbox). |
| `outbox_wait_s` | int | `25` | Wie lange eine Outbox-Abfrage beim Agenten warten darf, höchstens 30. |
| `connector_id` | string | `""` | Name dieses AstrBot beim Agenten. Leer erzeugt einmalig einen und behält ihn. Zwei AstrBot-Hosts brauchen verschiedene Namen. |

### Wo der Agent laufen kann

- **Gleicher Host** oder ein Container, der den Netzwerk-Namespace des Hosts teilt oder Host-Networking nutzt: Behalte die Loopback-`personagent_url` als Standard.
- **Anderer Container oder Host**: Nutze eine HTTPS-`personagent_url` und setze dasselbe nicht leere Geheimnis in `connector_token` und `CONNECTOR_TOKEN` des Agenten. Auch ein privater Tunnel, der an einer für AstrBot sichtbaren Loopback-URL endet, funktioniert. Setze auch dann auf beiden Seiten dasselbe Token, denn der Agent lehnt Anfragen ohne Token ab, die über einen Proxy kommen.

Das Plugin lehnt unverschlüsseltes `http://` zu allem außer Loopback ab, etwa `http://host.docker.internal:8080`, auch mit Token. Jede Nachricht protokolliert dann `refusing unsafe personagent_url`, und das eigene Modell von AstrBot antwortet stattdessen.

**AstrBot in Docker.** In einem Container ist `127.0.0.1` der Container selbst, also erreicht die Standard-`personagent_url` nichts. Du hast zwei Möglichkeiten:

- Gib AstrBot Host-Networking: `network_mode: host` in seiner Compose-Datei oder `docker run --network host`. Docker Desktop braucht Version 4.34 oder neuer mit aktiviertem Host-Networking. Ein NapCat-Container in derselben Compose-Datei braucht ebenfalls Host-Networking.
- Stelle den Agenten hinter HTTPS und setze diese Adresse als `personagent_url` (`personagent connect astrbot <dir> --url https://...`).

Der Agent lauscht standardmäßig auf `127.0.0.1:8080`. Setzt du sein `SERVER_HOST` auf eine Adresse außerhalb von Loopback, verweigert er den Start ohne `CONNECTOR_TOKEN`. Setze das Token, bevor du einen Proxy oder Tunnel vor den Agenten stellst, auch auf einem einzigen Host.

### Zeitlimits

Jede Anfrage dauert so lange wie der Zug des Agenten, also ein kurzer Debounce plus jeder Modellaufruf und jede Wiederholung. Läuft `timeout_s` ab, beendet der Agent den Zug trotzdem und behält, was er gelernt hat, aber die Antwort geht verloren, und das eigene Modell von AstrBot beantwortet die Nachricht.

Halte `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` des Agenten unter `timeout_s`. Mit den Standardwerten des Agenten (`LLM_TIMEOUT_S=120`, `LLM_MAX_RETRIES=2`) kann ein Zug, dessen Modellaufrufe immer wieder ablaufen, über 360 s dauern, was das Standard-`timeout_s` von 420 abdeckt. Erhöhst du einen der beiden Werte beim Agenten, erhöhe auch `timeout_s`.

Das Plugin wiederholt ein 429 oder 500 vom Agenten bis zu zweimal und beachtet bei einem 429 `Retry-After`, solange die signierte Anfrage noch frisch ist.

### `block_default` und Zuständigkeit

Das Plugin stoppt die Pipeline von AstrBot immer dann, wenn der Agent meldet, dass das Gespräch seines ist (`owned: true`), ob er geantwortet hat oder nicht, sodass das eingebaute Modell von AstrBot sich aus Zügen heraushält, in denen die Persona schweigt.

Transportfehler, ungültige Antworten und Gespräche, die der Agent abweist, laufen in die normale Pipeline von AstrBot weiter. Hat die Antwort des Agenten kein Feld `owned`, nutzt das Plugin stattdessen `handled`.

## QQ über NapCat

Offizielle QQ-Bots verbindet personagent selbst, ohne AstrBot. Dieser Abschnitt betrifft nur ein QQ-Konto, das über NapCat (oder eine andere OneBot-v11-Implementierung) hinter dem Adapter `aiocqhttp` von AstrBot läuft. Wenn du OneBot v11 auf der eigenen Seite von personagent hinzufügst, entfernt sie `aiocqhttp` aus `excluded_platforms` und setzt `CONNECTOR_QQ_PLATFORMS` für dich.

1. Entferne `aiocqhttp` aus `excluded_platforms` und füge die QQ-Gruppen zu `groups` hinzu.
2. Setze in der `.env` des Agenten `CONNECTOR_QQ_PLATFORMS=aiocqhttp` und `QQ_BOT_ID` (die Nummer des Bot-Kontos).
3. Optional: Setze `QQ_ONEBOT_URL` des Agenten auf den HTTP-Server von NapCat. Das aktiviert die Nachhol-Runde für verpasste Erwähnungen, die ebenfalls `QQ_BOT_ID` braucht. Proaktive Nachrichten, die Nachfrage nach einer Ablehnung und die Ausrede einer Gruppe bei einem Modellfehler laufen über die [Outbox](#outbox) dieses Plugins, solange es abfragt. Sonst laufen sie direkt über NapCat, sofern diese URL gesetzt ist.
4. Wenn NapCat auch an `/v1/onebot` des Agenten postet, schalte das ab. Die Route ist veraltet, und wenn beide laufen, wird jede Nachricht doppelt zugestellt.

`personagent connect astrbot <data dir> --qq` entfernt `aiocqhttp` aus `excluded_platforms` und setzt `CONNECTOR_QQ_PLATFORMS`. Ohne Ordner ausgeführt fragt er auch nach `QQ_BOT_ID`. Der Bereitstellungsleitfaden behandelt diesen Weg ebenfalls: [docs/deploy.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.de.md#qq-über-napcat-onebot).

Lass `CONNECTOR_QQ_PLATFORMS=aiocqhttp` nicht weg. Ohne das legt der Agent QQ-Chats unter IDs mit dem Präfix `aiocqhttp:` ab, unter den einfachen QQ-IDs Gelerntes passt nicht mehr, und die Register lassen sich danach nicht neu zuordnen.

Weil QQ-IDs ohne Präfix bleiben, gelten die eigenen QQ-Einstellungen des Agenten weiter. Die QQ-Einträge von `ACCESS_GROUPS` filtern Gruppen (keine Einträge bedeutet jede QQ-Gruppe), und beantwortet werden nur DMs vom Admin in `ADMIN_IDS` oder von Personen in `ACCESS_DM_USERS`. Der Assistent schreibt die QQ-Gruppen, die du ihm gibst, in die `.env` des Agenten. Um später eine QQ-Gruppe hinzuzufügen, füge sie sowohl zu `groups` als auch zu `ACCESS_GROUPS` hinzu oder liste in `ACCESS_GROUPS` keine QQ-Gruppen.

Bevor AstrBot eine aktive QQ-Gruppe trägt, prüfe zwei Einstellungen von AstrBot. Beide laufen vor den Plugin-Handlern.

- `platform_settings.rate_limit` steht standardmäßig auf 30 Nachrichten pro 60 s. Nachrichten über dem Limit werden verzögert, nicht verworfen. Erhöhe oder deaktiviere das Limit.
- `content_safety.internal_keywords` ist standardmäßig aktiv und verwirft Nachrichten, die seiner Schlüsselwortliste entsprechen, auch solche, die die Persona beantwortet hätte. Prüfe die Liste.

## Plattformen

Der Agent spricht ein neutrales Format, und das Plugin übersetzt an den Rändern mit den eigenen Mechanismen jeder Plattform. Die Tabelle unten wurde mit den Adaptern in AstrBot 4.25.5 abgeglichen.

Auf jeder Plattform:

- Nur Nachrichten, die eine Person geschrieben hat, werden weitergeleitet. QQ-Hinweise (Anstupsen, Zurückziehen, Beitritte) und -Anfragen sowie Slack-Beitritte und Themenänderungen sind keine Züge.
- Videos, Dateien und Sprachnachrichten kommen als Notiz an, auf die die Persona reagieren kann, etwa `(sent a video)`, `(sent a file: deck.pdf)` oder `(sent a voice message)`, mit dem Transkript der Plattform, wenn sie eines hat.
- Zitierte Nachrichten tragen ihren Text und Autor, wo die Plattform sie liefert (`forward_quoted_text`).
- Wo der Adapter sie aufbewahrt, ist die Zeit der Nachricht die der Plattform und nicht die, zu der AstrBot sie empfangen hat.
- Antworten werden unter dem Längenlimit der Plattform geteilt, wobei Erwähnung und Escapes so gezählt werden, wie die Plattform sie zählt. Sie werden nie zu einem Text-zu-Bild-Bild und nennen Leute so, wie die Plattform es tut.
- Die Outbox wird nur genutzt, wo die Plattform von sich aus senden kann.

| Plattform (Adapter) | Was funktioniert | Was die Plattform selbst nicht kann |
| --- | --- | --- |
| QQ über OneBot (`aiocqhttp`) | Gruppen und DMs. @ und Antwort an den Bot, auch wenn der Adapter das @ nicht auflösen konnte. Gesichtsnamen, Store-Sticker (`mface`) und als Sticker markierte Bilder. Erwähnungen als echtes QQ-@, gefolgt von einem Leerzeichen. Lange Antworten werden unter `forward_threshold` von AstrBot geteilt, sodass keine zur Sammelweiterleitungs-Karte wird. Outbox. | Markdown wird so angezeigt, wie es getippt wurde. |
| QQ offiziell (`qq_official`, `qq_official_webhook`) | Gruppennachrichten, die den Bot mit @ ansprechen, und DMs. Gesichter als `[表情:name]`. Antworten fordern Klartext statt des Markdown des Adapters an. | Gruppen liefern nur Nachrichten, die den Bot mit @ ansprechen, also kann die Persona einem Gespräch nicht folgen. Keine Zitate, keine Namen (nur openids), keine Erwähnungen in Antworten. Antworten sind nur innerhalb von 5 Minuten nach einer Nachricht möglich, daher keine Outbox. |
| Telegram (`telegram`) | Gruppen, Themen (`<chat>#<thread>`) und DMs. Antwort an den Bot für jede Nachrichtenart, ohne das Weckpräfix `/@bot` des Adapters. Sticker-Emoji, bei statischen Stickern auch das Bild. Bilder werden über den Bot des Adapters geholt, sodass das Bot-Token AstrBot nie verlässt. Ein erwähnter Benutzername wird zur numerischen ID der Person, sobald sie geschrieben hat. Antworten erwähnen per Benutzername oder bei Personen ohne einen per `tg://user`-Link und zeigen `*`, `_` und ähnliche Zeichen so, wie sie getippt wurden. Outbox. | Mit aktivem Datenschutzmodus von BotFather (Standard) liefern Gruppen nur Befehle, @-Erwähnungen und Antworten an den Bot. Schalte ihn ab, damit die Persona dem Gespräch folgen kann. Animierte und Video-Sticker können nicht angesehen werden. |
| Discord (`discord`) | Kanäle und Threads als Gruppen, und DMs. Ein führendes `@bot` (das der Adapter entfernt), ein Ping einer Rolle des Bots und Antworten an den Bot sprechen ihn an. Zitate mit ihrem Text. Sticker. Sprach- und Videoanhänge als Notizen. Erwähnungen als `<@id>`, wobei `@everyone` und `@here` wirkungslos bleiben. Antworten werden bei 2000 Zeichen geteilt. Outbox, DMs eingeschlossen. | Braucht den Message-Content-Intent. |
| Slack (`slack`) | Kanäle und DMs. Eine Thread-Antwort unter der Nachricht des Bots spricht ihn an. Links werden aufgeklappt. Nachrichten-IDs sind Slacks `ts`. Erwähnungen als `<@id>`. `&`, `<` und `>` werden maskiert, damit Text keinen Kanal anpingen kann. Antworten werden bei 3000 Zeichen geteilt. Outbox. | Eine Thread-Antwort trägt keinen Text der übergeordneten Nachricht. Keine Tippanzeige für Bots. Antworten landen im Kanal, nicht im Thread (Adapter). |
| KOOK (`kook`) | Kanäle und DMs. @ und Pings einer Rolle, die der Bot hat. Zitate, wenn KOOK sie mitliefert. `(emj)`-Emoji und die echte Sendezeit. Erwähnungen inline im Text, wobei `(met)`-artige Tags im Text der Persona wirkungslos bleiben. Bilder werden als Datei gesendet, da der Adapter nur JPEG-Base64 hochlädt. Outbox. | Der Adapter von AstrBot verwirft einfache Bild-, Datei-, Sprach- und Videonachrichten (nicht Karten), bevor ein Plugin sie sieht. Keine Tippanzeige. |
| Lark / Feishu (`lark`) | Gruppen und DMs. @ und Antworten an den Bot (Lark nennt die App als Absender). Zitate mit ihrem Text. Sticker als Emoji. Outbox. | Ohne die Berechtigung „alle Gruppennachrichten lesen“ kommen nur @-Nachrichten an. Jede Antwort zitiert die beantwortete Nachricht, und Markdown wird gerendert (Adapter). Namen sind ID-Präfixe. |
| DingTalk (`dingtalk`) | Gruppen und DMs. Bilder, die der Adapter als lokale Dateien übergibt, werden inline gesendet. Videos als Notiz. Outbox. DMs erreichen Personen, die dem Bot geschrieben haben. | Gruppen liefern nur Nachrichten, die den Bot mit @ ansprechen. Keine Zitate und keine Erwähnungen oder Zitat-Antworten in Antworten. Jede Antwort ist Markdown mit dem Titel "AstrBot" (Adapter). |
| LINE (`line`) | Gruppen, Räume und DMs. @ an den Bot. Zitat-IDs. Sticker-Schlüsselwörter. Die Blasen eines Zuges gehen in einem Aufruf hinaus, fünf auf einmal, sodass der kostenlose Reply-Token sie abdeckt. Outbox, die auf das Push-Kontingent angerechnet wird. | LINE sendet keinen zitierten Text. Keine Erwähnungen in Antworten (Adapter). Ausgehende Bilder brauchen eine öffentliche HTTPS-`callback_api_base`. Namen sind ID-Präfixe. |
| Mattermost (`mattermost`) | Kanäle und DMs. @ an den Bot. Thread-Wurzel als Zitat. Bilder inline. Erwähnungen per Benutzername, sobald die Person geschrieben hat. `@channel`, `@all` und `@here` bleiben wirkungslos. Antworten werden bei 4000 Zeichen geteilt. Outbox. | Zitierter Text bräuchte eine Abfrage, die das Plugin nicht macht. Keine Tippanzeige. |
| Misskey (`misskey`) | Chat-DMs und Räume, mit `@bot` an beliebiger Stelle einer Raumnachricht. Erwähnungen als `@user@host`, sobald die Person geschrieben hat, wobei jedes andere `@` im Text der Persona wirkungslos bleibt. Antworten werden bei 3000 Zeichen geteilt. Outbox für Chat und Räume. | Notes (öffentliche Beiträge) werden nicht weitergeleitet, weil AstrBot sie als Systemereignisse einstuft und eine Antwort öffentlich wäre. `unique_session` zerstört Räume (Adapter). |
| Satori (`satori`) | Was das Satori-Backend überbrückt: Gruppen, DMs, @, Antworten an den Bot, Zitate mit Text. Millisekunden-Zeitstempel werden als Sekunden gelesen. Outbox. | Die Gruppen-ID ist die Gilde, also teilen sich die Kanäle einer Gilde ein Gespräch. Die Grenzen der überbrückten Plattform gelten. |
| WebChat (`webchat`) | Der Dashboard-Chat, als DMs. Zitate und Bilder. Outbox, live angezeigt oder im Gespräch gespeichert. | Nur eins zu eins. |
| WeCom-App (`wecom`) | DMs, Bilder und Sprache mit Transkript. Der Kundendienstmodus leitet nur die Nachrichten des Kunden weiter, mit der echten Sendezeit. Antworten werden nach Bytes geteilt. Outbox im App-Modus, sobald jemand seit dem Start von AstrBot geschrieben hat. | Nur DMs, keine Zitate. Der Kundendienstmodus kann nicht von sich aus senden. Markdown wird so angezeigt, wie es getippt wurde. |
| WeCom-KI-Bot (`wecom_ai_bot`) | Gruppen (WeCom liefert eine Gruppennachricht nur, wenn der Bot mit @ angesprochen wird) und DMs. Sprach-, Datei- und Videonotizen. Ein Zug wird als eine gestreamte Antwort gesendet. | Antwortet nur innerhalb der Antwort auf eine Nachricht, also keine Outbox und keine Erwähnungen. Die Antwort wird als Markdown gerendert. Setze `wecom_ai_bot_name` in AstrBot, damit "@bot" aus dem Text entfernt wird. |
| Offizielles WeChat-Konto (`weixin_official_account`) | DMs und Sprache mit Transkript. Ein Zug wird als eine Nachricht gesendet. | Der passive Modus liefert eine Antwort pro Benutzernachricht innerhalb von WeChats 5-s-Fenster. Der Rest wartet auf die nächste Nachricht des Benutzers, und ein Zug, in dem die Persona schweigt, lässt den Benutzer warten (Adapter). Bilder nur im aktiven Modus. Keine Outbox. |
| Persönliches WeChat (`weixin_oc`) | DMs. Zitate mit ihrem Text. Bilder inline. Sprache mit Transkript. Tippanzeige. Outbox. | Keine Gruppen. Nach einer Neuanmeldung ist niemand erreichbar, bis er wieder schreibt. |
| Jeder andere Adapter | Wird weitergeleitet, wie AstrBot es liefert. Erwähnungen als At. | Keine Outbox deklariert. |

## Outbox

Manche Nachrichten beantworten nichts: ein geplanter Gesprächsanfang, die Nachfrage nach einer Ablehnung oder die Ausrede in einer Gruppe, wenn das Modell ausgefallen ist. (Die Ausrede einer DM kommt in der Antwort auf das Ereignis zurück.) Der Agent reiht diese Nachrichten ein, und dieses Plugin holt sie von `POST <personagent_url>/v1/outbox` mit derselben Signatur wie Ereignisse, sodass der Agent AstrBot nie erreichen muss. Die Outbox ist standardmäßig aktiv (`outbox_enabled`).

- Jede Zustellung geht über die eigene AstrBot-Sitzung des Gesprächs, der Reihe nach, und jede Nachricht wird höchstens einmal gesendet.
- Eine Zustellung geht nur an eine Sitzung, die das Plugin selbst aus einer Nachricht desselben Gesprächs entnommen hat. Diese Sitzungen liegen im Plugin-Speicher von AstrBot und überstehen so ein Neuladen. Nichts anderes, das ein Ereignis an den Agenten postet, kann die Outbox auf einen anderen Chat richten, und das Plugin lehnt eine solche Zustellung ab.
- Das Plugin prüft die Zulassungslisten und `excluded_platforms` beim Senden erneut und lehnt ein inzwischen entferntes Gespräch ab.
- Plattformen, die nicht zuerst sprechen können (siehe Tabelle), erhalten nie Outbox-Nachrichten, weil das Plugin die Outbox für ihre Gespräche nicht deklariert.
- Ein Agent ohne Outbox antwortet mit 404. Das Plugin fragt alle zehn Minuten erneut.

Der Agent kennt dieses AstrBot unter `connector_id`, die das Plugin einmal erzeugt und behält. Zwei AstrBot-Hosts, die mit einem Agenten sprechen, brauchen verschiedene IDs.

## Anfrage-Authentifizierung

Wenn `connector_token` gesetzt ist, trägt jede Anfrage vier Header:

- `X-Personagent-Token`: das Token.
- `X-Personagent-Timestamp`: Unix-Sekunden.
- `X-Personagent-Nonce`: ein frischer Zufallswert.
- `X-Personagent-Signature`: `sha256=` gefolgt vom hexadezimalen HMAC-SHA256 mit dem Token als Schlüssel über `timestamp + "." + nonce + "." + body`.

Der Body ist kanonisches JSON: UTF-8, sortierte Schlüssel, kompakte Trennzeichen und unmaskierte Nicht-ASCII-Zeichen. Die Signatur deckt genau diese Bytes ab, also darf ein Proxy den Body nicht umschreiben. Der Agent lehnt eine falsche Signatur, eine wiederverwendete Nonce oder einen Zeitstempel ab, der mehr als fünf Minuten von seiner eigenen Uhr abweicht. Halte die beiden Uhren synchron.

Der Body trägt außerdem die Zeit des Adapters für die Nachricht als `sent_at`. Der Agent prüft sie separat gegen `CONNECTOR_MAX_EVENT_AGE_S` (standardmäßig 24 Stunden), sodass ein altes, mit frischer Signatur erneut gesendetes Ereignis trotzdem abgelehnt wird. Das Plugin leitet keine Nachricht weiter, deren Adapter keinen gültigen Zeitstempel liefert, und AstrBot behandelt diese Nachricht wie gewohnt.

## Identitäten auf der Agent-Seite

Der Agent stellt jeder weitergeleiteten ID ihre Plattform voran, als `<platform>:<raw id>` (zum Beispiel `telegram:12345`), sodass IDs verschiedener Plattformen nie kollidieren. Plattformen in `CONNECTOR_QQ_PLATFORMS` behalten IDs ohne Präfix. `ADMIN_IDS`, `ACCESS_GROUPS` und `ACCESS_DM_USERS` des Agenten nehmen IDs in derselben Form. Zum Beispiel macht `ADMIN_IDS=telegram:12345` dieses Konto zum Admin auf Telegram, in Gruppen und DMs. Eine Plattform mit Einträgen in `ACCESS_GROUPS` oder `ACCESS_DM_USERS` wird vom Agenten ebenso wie von den Zulassungslisten dieses Plugins gefiltert.

## Fehlerbehebung

Die Zeilen des Plugins im Log von AstrBot beginnen mit `personagent:`.

| Log-Meldung | Was zu tun ist |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` ist unverschlüsseltes HTTP zu einem anderen Host oder HTTPS ohne `connector_token`. Siehe [Wo der Agent laufen kann](#wo-der-agent-laufen-kann). |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` ist leer oder passt nicht zum `CONNECTOR_TOKEN` des Agenten, die beiden Uhren weichen um mehr als fünf Minuten ab, oder ein Proxy hat den Body geändert. Sagt das Log des Agenten `connector replay guard full`, warte, bis er sich leert. |
| `agent refused the request (403): stale or invalid sent_at` | Die Nachricht ist älter als `CONNECTOR_MAX_EVENT_AGE_S` des Agenten. Das passiert meist, nachdem AstrBot einen Rückstau zugestellt hat. |
| `agent refused the request (403): authentication required` oder `... only local requests accepted` | Der Agent hat kein `CONNECTOR_TOKEN`, und die Anfrage ist nicht lokal. Setze auf beiden Seiten dasselbe Token. |
| `agent at capacity (429)` | Der Agent führte bereits `CONNECTOR_MAX_INFLIGHT` Züge aus und wies die Nachricht auch nach Wiederholungen ab, also antwortete das eigene Modell von AstrBot. Erhöhe `CONNECTOR_MAX_INFLIGHT`, wenn das oft passiert. |
| `agent rejected the body as too large (413)` | Meist ein großes Inline-Bild. Erhöhe `SERVER_MAX_BODY_BYTES` des Agenten. |
| `agent rejected the event schema (400)` | Dem Ereignis fehlte die Nachrichten- oder Absender-ID (manche Adapter lassen sie weg), oder dieses Plugin hat einen Fehler. Bitte melde es mit der Log-Zeile. |
| `timed out waiting for the agent` | Siehe [Zeitlimits](#zeitlimits). |
| `dropping event without a valid time the platform sent it` | Der Adapter lieferte keinen Zeitstempel. AstrBot behandelt diese Nachricht selbst. |
| `agent request failed: ...` oder `agent request failed (<status>)` | Meist läuft der Agent nicht, oder `personagent_url` ist falsch. Ein 404 bedeutet einen falschen Pfad: `personagent_url` ist die Basis-URL, ohne `/v1/events`. Ein 500 bedeutet, dass der Agent gescheitert ist, also prüfe sein Log. |
| `outbox off: ...` | Die Outbox folgt derselben `personagent_url`-Regel wie Ereignisse. Siehe die erste Zeile. |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | `CONNECTOR_OUTBOX_ENABLED` des Agenten ist aus. |
| `outbox: outbox pull refused (403)` oder `outbox pull failed: ...` | Dieselben Ursachen wie bei Ereignissen: das Token, die Uhren oder ein nicht laufender Agent. Das Plugin wartet zwischen Versuchen bis zu einer Minute. |
| `outbox: no running platform '<id>'` | Eine Zustellung für einen Adapter, der in AstrBot deaktiviert oder umbenannt wurde. Das Plugin meldet sie dem Agenten als fehlgeschlagen. |
| `could not store connector_id` | Der Plugin-Speicher von AstrBot ist fehlgeschlagen. Setze `connector_id` selbst, sonst sieht der Agent nach jedem Neustart ein neues AstrBot. |

Antwortet das eigene Modell von AstrBot plötzlich mit einer anderen Stimme, hat das Plugin den Agenten nicht erreicht, oder der Agent hat das Gespräch nicht übernommen. Prüfe die Tabelle oben und führe dann `personagent doctor` aus. Hat die lokale Seite den Agenten gestartet, öffne dort **Aktivität**, um zu sehen, ob die Nachricht ankam und warum die Persona schwieg. Hast du ihn mit `personagent run` gestartet, lies sein Terminal.

Sagt das eigene Log des Agenten, dass der Konnektor `X-Personagent-Token` sendet, aber `CONNECTOR_TOKEN` leer ist, ignoriert der Agent das Token. Setze denselben Wert in der `.env` des Agenten.

Auf QQ, Telegram, Discord, KOOK, QQ offiziell und Misskey ist die Zeit der Nachricht die der Plattform, nicht die, zu der AstrBot sie empfangen hat. War AstrBot länger ausgefallen als `CONNECTOR_MAX_EVENT_AGE_S` des Agenten, lehnt der Agent den von AstrBot zugestellten Rückstau als veraltet ab.

## Bekannte Einschränkung: Telegram-Erwähnungen

Der Telegram-Adapter von AstrBot identifiziert einen Absender über die numerische Benutzer-ID (`telegram:<numeric id>`), eine `@username`-Erwähnung in einer Nachricht aber nur über den Benutzernamen. Das Plugin schreibt einen erwähnten Benutzernamen in die numerische ID der Person um, die ihn nutzt, sobald sie seit dem Start von AstrBot geschrieben hat. Bis dahin erreicht die Erwähnung den Agenten unter dem Benutzernamen.

Antworten erwähnen jemanden per Benutzername oder mit einem `tg://user`-Link, wenn die Person keinen hat. Das Plugin erwähnt niemanden, den es seit dem Start von AstrBot nicht gesehen hat.
