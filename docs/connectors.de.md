# Konnektor-Protokoll

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · [繁體中文](connectors.zh-TW.md) · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · [Español](connectors.es.md) · [Français](connectors.fr.md) · Deutsch · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

Der Agent spricht nie selbst mit einer Chat-Plattform. Das übernimmt ein Konnektor. Er meldet sich bei einer Plattform oder bei einem Framework an, das viele Plattformen abdeckt, wandelt jede eingehende Nachricht in ein neutrales Ereignis um, sendet das Ereignis an personagent und stellt zu, was zurückkommt. Alles Plattformspezifische bleibt im Konnektor, sodass der Agent von jeder Plattform dasselbe Format sieht.

Dieses Repository enthält vier Konnektoren:

| Konnektor | Erreicht | Pfad |
|---|---|---|
| Direkt | Offizielle QQ-Bots, persönliches WeChat (iLink), Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK und Stoat, ohne weitere Software. Die lokale Seite und `personagent up` führen ihn als einen Prozess aus, `python -m persona_agent.direct`. | `persona_agent/direct/` |
| AstrBot-Plugin | Die Plattformen von AstrBot, einer Brücke eines Drittanbieters. Das AstrBot, das personagent für KOOK, Feishu/Lark, DingTalk, Slack, WeCom, Mattermost, Misskey, OneBot v11 und die übrigen verwaltet, erhält das Plugin automatisch. Für ein AstrBot, das Sie bereits betreiben, richtet `personagent connect astrbot` es ein. Sie können auch `astrbot_plugin_personagent.zip` aus einem GitHub Release über „Aus Datei installieren“ in AstrBot hochladen und `connector_token` selbst festlegen. | `integrations/astrbot/` |
| Satori | Jede Satori-Implementierung (Koishi und andere, von Drittanbietern): QQ, Telegram, Discord, KOOK, Lark, DingTalk, LINE, WhatsApp, Matrix, Zulip, E-Mail und mehr. | `integrations/satori/` |
| Matrix | Matrix-Räume und über mautrix-Brücken von Drittanbietern WhatsApp, Signal, Messenger, Instagram, Google Messages und mehr. | `integrations/matrix/` |

Programmierassistenten sind keine Chat-Plattformen und haben deshalb einen eigenen Zugang: einen MCP-Server, `personagent mcp`, beschrieben in der [Benutzeranleitung](guide.de.md#programmierassistenten).

Alle vier sprechen das auf dieser Seite beschriebene Protokoll. Um einen neuen Konnektor zu schreiben, benötigen Sie diese Seite und einen HTTP-Client. Das Python-Hilfsmodul in `integrations/sdk/personagent_connector.py` signiert Anfragen und führt die Outbox-Schleife für Sie aus. Es erwartet die Basis-URL, das Token und die `connector_id` des Konnektors und benötigt `httpx`.

## Konfiguration

Die lokale Seite konfiguriert den direkten Konnektor. Die anderen drei verwenden dieselben Namen, sodass eine Einstellung in jedem Konnektor dieselbe Bedeutung hat:

| Bedeutung | Satori | Matrix | Schlüssel im AstrBot-Plugin |
|---|---|---|---|
| Die Basis-URL von personagent, zum Beispiel `http://127.0.0.1:8080`. Der Konnektor hängt `/v1/events` und `/v1/outbox` an. | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| Das gemeinsame Token, identisch mit dem `CONNECTOR_TOKEN` des Agenten | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| Die ID dieses Konnektors (`connector_id` unten) | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| Maximale Dauer einer Anfrage in Sekunden | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| Die Outbox abfragen | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| Weiterzuleitende Gruppen | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| Personen, deren Direktnachrichten weitergeleitet werden | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| Der Server der Plattform | `SATORI_URL` | `MATRIX_URL` | Der von AstrBot |

Eine leere Gruppen- oder DM-Liste leitet nichts dieser Art weiter. `*` leitet alles dieser Art weiter und markiert die Ereignisse mit `"prefiltered": false`, was die Entscheidung den `ACCESS_GROUPS` und `ACCESS_DM_USERS` des Agenten überlässt. Das README jedes Konnektors führt seine übrigen Einstellungen auf.

## Adressierung

personagent speichert jede ID als `<platform>:<id>`, zum Beispiel `telegram:-1001234` für eine Gruppe oder `discord:4242` für einen Nutzer. `platform` ist der Name des Konnektors für die Plattform, kleingeschrieben und ohne `:`.

QQ ist die einzige Ausnahme, beibehalten aus Kompatibilitätsgründen. Seine IDs werden ohne Präfix gespeichert (`123456`), und `qq:123456` bedeutet in jeder Einstellung dasselbe. Wenn ein Konnektor QQ überträgt und Sie seinen gelernten Stand mit einer bestehenden QQ-Bereitstellung zusammenführen möchten, tragen Sie seine Plattform in `CONNECTOR_QQ_PLATFORMS` ein. Der QQ-Adapter des AstrBot-Plugins ist `aiocqhttp`. IDs der dort genannten Plattformen werden ebenfalls ohne Präfix gespeichert.

## Authentifizierung

Beide Endpunkte unten verwenden dasselbe Verfahren. Wenn `CONNECTOR_TOKEN` beim Agenten gesetzt ist, trägt jede Anfrage vier Header:

- `X-Personagent-Token`: das Token.
- `X-Personagent-Timestamp`: Unix-Sekunden. Ein Wert, der mehr als fünf Minuten von der Uhr des Agenten abweicht, wird abgelehnt.
- `X-Personagent-Nonce`: ein neuer Zufallswert. Eine wiederverwendete Nonce wird abgelehnt.
- `X-Personagent-Signature`: `sha256=`, gefolgt vom hexadezimalen HMAC-SHA256 von `timestamp + "." + nonce + "." + body`, mit dem Token als Schlüssel.

Der Body ist kanonisches JSON: UTF-8, sortierte Schlüssel, kompakte Trennzeichen und unmaskiertes Nicht-ASCII. Das Token ist zugleich der Signaturschlüssel; es darf daher nicht in Protokollen erscheinen.

Ohne Token akzeptiert der Agent nur lokale Programme, die `127.0.0.1` oder `localhost` direkt aufrufen. Ein Konnektor muss sich weigern, an etwas anderes zu senden als an eine Loopback-URL oder eine HTTPS-URL mit Token.

## Eingehend: `POST /v1/events`

Jede Anfrage überträgt eine Nachricht und gibt die Antworten darauf zurück.

```json
{
  "platform": "telegram",
  "conversation_type": "group",
  "conversation_id": "-1001234",
  "sender_id": "42",
  "sender_name": "Alex",
  "bot_id": "7000",
  "message_id": "881",
  "sent_at": 1790320000,
  "addressed": true,
  "text": "Nova, how was your day?",
  "segments": [
    {"type": "text", "text": "Nova, how was your day?"}
  ],
  "connector_id": "astrbot-7f3c",
  "reply_handle": "tg-bot:GroupMessage:-1001234",
  "capabilities": ["outbox", "quote_text"]
}
```

Pflichtfelder sind `platform`, `conversation_type` (`group` oder `dm`), `sender_id`, `message_id` und `sent_at`, bei Gruppen zusätzlich `conversation_id`. `sent_at` ist der Zeitstempel, den die Plattform der Nachricht gegeben hat, in Unix-Sekunden. Senden Sie die unveränderten IDs der Plattform. Das Präfix fügt der Agent hinzu.

Der Konnektor setzt `addressed`. Es ist wahr, wenn die Nachricht den Bot erwähnt, auf eine Nachricht des Bots antwortet oder nach den eigenen Regeln der Plattform an den Bot gerichtet ist. Der Agent erkennt seinen Namen im Text auch selbst. Ein Zitat seiner eigenen Nachricht oder ein @ an den Bot wertet er als Reaktion, aus der er lernen darf; setzen Sie `addressed` daher bei Antworten an den Bot. Ein Zitat der Nachricht eines anderen Mitglieds ist nie eine Reaktion auf den Bot.

Ein Ereignis, dessen `sender_id` gleich seiner `bot_id` ist, ist das Echo der eigenen Nachricht des Bots. Der Agent verwirft es ungelesen und antwortet `{"handled": false, "owned": true, "replies": []}`, sodass auch die eigene Bot-Logik des Konnektors schweigt. Überspringen Sie solche Ereignisse im Konnektor.

Segmente werden in ihrer Reihenfolge übertragen:

| Typ | Felder | Hinweise |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | Eine Erwähnung einer Person. Sie erwähnt den Bot, wenn `user_id` gleich `bot_id` ist. |
| `image` | `url` oder `b64`, `sticker` (Boolean) | `sticker` kennzeichnet einen als Bild gesendeten Sticker. |
| `emoji` | `name`, `id` | Ein Plattform-Sticker oder benutzerdefiniertes Emoji, das der Agent nicht sehen kann. `name` ist das, was eine Person dazu sagen würde. |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | Die Nachricht, die diese zitiert. Senden Sie `text`, sofern die Plattform es liefert. |

Beschreiben Sie alles andere in Worten, als `text`-Segment wie `(sent a voice message)` oder `(sent a file: deck.pdf)`. Der Agent verwirft unbekannte Segmenttypen.

Diese optionalen Felder schalten weitere Funktionen des Agenten frei:

| Feld | Bedeutung |
|---|---|
| `connector_id` | Eine stabile ID für diese Konnektor-Instanz. Die Outbox verlangt sie. |
| `reply_handle` | Alles, was der Konnektor benötigt, um diese Unterhaltung später ohne eingehende Nachricht zu erreichen: `unified_msg_origin` von AstrBot, eine Matrix-Raum-ID oder eine Satori-Anmeldung plus Kanal-ID. Der Agent behandelt es als undurchsichtig, speichert es pro Unterhaltung und gibt es in Outbox-Zustellungen zurück. |
| `capabilities` | Die Fähigkeiten des Konnektors. `outbox` bedeutet, dass er die Outbox abfragt und von sich aus senden kann. `quote_text` bedeutet, dass Antwortsegmente den zitierten Text tragen. |
| `prefiltered` | `true` (der Standard), wenn der Konnektor seine eigene Zulassungsliste angewendet hat. `false` macht die Listen des Agenten zum einzigen Filter. |
| `proactive` | Kennzeichnet ein DM-Ereignis als Stichwort, das der Konnektor geschrieben hat, nicht als Worte der Person. Siehe „Zuerst sprechen ohne die Outbox“. |

Die Antwort hat folgende Form:

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`: Senden Sie sie der Reihe nach, jede als eigene Nachricht. Ist `mention_user_id` vorhanden, enthält es die zu erwähnende ID mit Präfix. Stellen Sie die Erwähnung so dar, wie es auf der Plattform üblich ist.
- `owned`: Der Agent hat diese Unterhaltung übernommen. Ist der Wert wahr, verhindern Sie, dass andere Bot-Logik antwortet, selbst wenn `replies` leer ist, denn die Figur hat sich für Schweigen entschieden. Ist er falsch, liegt die Nachricht in der Verantwortung des Konnektors. Entweder steht die Unterhaltung nicht auf den Zulassungslisten des Agenten, oder der Agent kann gar nicht antworten (kein `LLM_API_KEY` oder `AGENT_ENABLED=false`). Im zweiten Fall steht im Log des Agenten eine ERROR-Zeile mit der Ursache.
- Die Anfrage dauert, bis der Durchgang abgeschlossen ist, also eine kurze Entprellung plus die Zeit des Modells. Die Modellaufrufe eines Durchgangs teilen sich ein einziges Budget von 1,5 × `LLM_TIMEOUT_S`, Wiederholungen eingeschlossen, in einer Gruppe wie in einer DM, und eine Nachricht, die eintrifft, während ein früherer Durchgang ihrer Unterhaltung noch nachdenkt, wartet erst dessen Ende ab und beginnt dann ihren eigenen. Planen Sie mindestens 3 × `LLM_TIMEOUT_S` Sekunden ein (360 mit dem Standardwert).
- Ein Gedächtnis-Befehl (etwa „remember ...“), der eintrifft, während ein Durchgang seiner Unterhaltung noch nachdenkt, wird erst nach diesem Durchgang beantwortet. Ein Konnektor, der `outbox` deklariert hat, erhält sofort `{"handled": false, "owned": true, "replies": []}` und das Ergebnis später als `follow_up`-Zustellung. Ohne `outbox` kommt das Ergebnis in der Antwort auf eine Anfrage: auf seine eigene oder auf eine andere wartende Anfrage derselben Unterhaltung. Eine Antwort kann also `replies` enthalten, die jemand anderen als den Absender des Ereignisses erwähnen.

## Outbox: `POST /v1/outbox`

Manche Nachrichten beantworten keine Anfrage. Beispiele sind eine geplante Eröffnung, die Rückfrage nach einer Ablehnung, die Antwort auf einen Gedächtnis-Befehl, der hinter einem Durchgang gewartet hat, und die Ausrede, wenn das Modell in einer Gruppe ausgefallen ist. Der Agent reiht diese pro Unterhaltung ein, und ein Konnektor, der `outbox` deklariert hat, holt sie ab, sodass ein Konnektor hinter NAT oder einer Firewall genauso funktioniert. Unterhaltungen, die unter QQ-IDs ohne Präfix gespeichert sind (siehe Adressierung), nutzen die Outbox ebenfalls, solange ihr Konnektor sie abfragt. Sonst laufen sie über die HTTP-API von NapCat, wenn `QQ_ONEBOT_URL` gesetzt ist.

Anfrage:

```json
{
  "kind": "outbox.pull",
  "connector_id": "astrbot-7f3c",
  "wait_s": 25,
  "max_deliveries": 10,
  "acks": [
    {"delivery_id": "d_5c1f...", "status": "sent", "sent_items": 2}
  ]
}
```

Der Agent hält die Anfrage bis zu `wait_s` Sekunden (höchstens 30), bis etwas eingereiht ist, und antwortet dann:

```json
{
  "deliveries": [
    {
      "delivery_id": "d_9a07...",
      "conversation_key": "telegram:-1001234",
      "reply_handle": "tg-bot:GroupMessage:-1001234",
      "platform": "telegram",
      "conversation_type": "group",
      "conversation_id": "-1001234",
      "reason": "proactive",
      "expires_in_s": 300,
      "items": [{"type": "text", "text": "anyone still up?"}]
    }
  ],
  "next_wait_s": 25
}
```

`items` hat dieselbe Form wie `replies`. `reason` ist `proactive`, `follow_up` oder `excuse`, und `conversation_type` ist `group` oder `dm`. `conversation_key` ist der Schlüssel, unter dem der Agent die Unterhaltung speichert, zum Beispiel `private:telegram:42` für eine DM. `conversation_id` ist die rohe ID aus dem Ereignis, bei einer DM die Nutzer-ID. Der Agent merkt sich `reply_handle`, `connector_id` und `capabilities` aus dem letzten zugelassenen Ereignis jeder Unterhaltung, sodass eine Unterhaltung erreichbar wird, sobald sie eine Nachricht gesendet hat. Eine Ausnahme belässt einen abrufenden Konnektor an seinem Platz: Ein Ereignis von einem Konnektor ohne die Fähigkeit `outbox` ersetzt nicht, was ein anderer Konnektor mit dieser Fähigkeit für dieselbe Unterhaltung gespeichert hat. Ein Konnektor, der die Outbox abruft, erreicht die Unterhaltung daher weiterhin, nachdem ein anderes Programm, etwa ein Programmierassistent, dort gesprochen hat. Ein Ereignis vom selben Konnektor oder von einem beliebigen Konnektor, der `outbox` deklariert, ersetzt die gespeicherten Werte wie bisher.

Die lokale Seite ist selbst ein Outbox-Konnektor mit der `connector_id` `local-welcome`. Sie erhält nur die Zustellungen für den eigenen Chat der Seite und zeigt sie in der Ansicht **Chat** an.

Melden Sie jede Zustellung bei der nächsten Abfrage in `acks`:

| `status` | Bedeutung |
|---|---|
| `sent` | Alle Elemente wurden gesendet. |
| `partial` | Die ersten `sent_items` Elemente wurden gesendet. |
| `failed` | Es wurde nichts gesendet. |
| `expired` | Das Senden hat nicht innerhalb von `expires_in_s` begonnen. |
| `refused` | Der Konnektor lässt die Unterhaltung nicht mehr zu. |
| `unsupported` | Die Plattform kann an diese Unterhaltung nicht von sich aus senden. |

Regeln:

- **Höchstens einmal.** Der Agent gibt eine Zustellung genau einmal heraus, unabhängig davon, was mit dem Ack geschieht. Speichern Sie die zuletzt erhaltenen `delivery_id`s (einige hundert) und senden Sie keine Zustellung zweimal.
- **Der Reihe nach.** Senden Sie die Zustellungen einer Unterhaltung in der Reihenfolge, in der Sie sie erhalten haben. Verschiedene Unterhaltungen dürfen parallel bedient werden.
- **Nur bestätigte Zustellungen zählen.** Der Agent behandelt eine unbestätigte Zustellung als nicht gesendet und verbucht nur bestätigte als gesendet. Er wartet auf das Ack bis zu Ihrer nächsten Abfrage, höchstens jedoch `expires_in_s` plus 60 Sekunden nach der Herausgabe. Senden Sie einen Stapel vollständig, bevor Sie erneut abfragen.
- **Lebenszeichen.** Ein Konnektor, der 90 Sekunden lang nicht abgefragt hat, gilt als getrennt. Für seine Unterhaltungen wird nichts eingereiht, bis er wieder abfragt, und was für ihn eingereiht oder ihm ohne Ack übergeben wurde, endet als nicht gesendet. Fragen Sie erneut ab, sobald ein Stapel zugestellt ist. Diese Abfrage trägt auch die Acks des Stapels.
- **`unsupported` bleibt bestehen.** Nach diesem Ack reiht der Agent für die Unterhaltung nichts mehr ein, bis ein Ereignis einen anderen `reply_handle` bringt.
- **Body-Arten.** Die Signatur deckt den URL-Pfad nicht ab. Der Agent lehnt deshalb einen Ereignis-Body am Outbox-Endpunkt und einen `outbox.pull`-Body am Ereignis-Endpunkt ab, mit `400` und dem Code `invalid_schema`. Ein Ereignis darf `"kind": "event"` tragen. Ein Ereignis mit einem anderen `kind` wird abgelehnt.

Ein 404 ohne `code` bedeutet, dass der Agent die Outbox nicht anbietet. Ein `404` mit dem Code `outbox_disabled` bedeutet, dass der Betreiber sie mit `CONNECTOR_OUTBOX_ENABLED` abgeschaltet hat. Warten Sie in beiden Fällen längere Zeit, bevor Sie erneut abfragen.

## Zuerst sprechen ohne die Outbox

Ein Konnektor, der nicht abfragen kann, kann trotzdem eine DM eröffnen. Sein eigener Planer, etwa eine AstrBot-Plugin-Aufgabe oder ein Cron-Eintrag, schickt ein gewöhnliches DM-Ereignis mit `"proactive": true` an `/v1/events`. Der Agent liest den Text als Stichwort für die Figur („seit einem Tag still; die Prüfung war heute Morgen“), schneidet ihn bei 500 Zeichen ab und speichert ihn nie als Worte der Person. Die proaktiven Anweisungen der Engine entscheiden weiterhin über den Durchgang und können die Figur schweigen lassen. Spricht die Figur, kommt die Antwort in der HTTP-Antwort zurück, damit der Planer sie weitergibt.

Das Ereignis benötigt alles, was die normalen Ereignisse des Konnektors tragen: die signierten Header, jedes Pflichtfeld, dieselbe `platform` und rohe `sender_id`, die der Konnektor für diese Person sendet, nicht leeren Text und jedes Mal eine neue `message_id`. Ein Ereignis mit wiederholter `message_id` wird stillschweigend verworfen. Das Stichwort zählt zur selben DM-Abklingzeit wie die eigenen Eröffnungen des Agenten (`PROACTIVE_DM_COOLDOWN_S`) und nicht als Aktivität der Person.

Setzen Sie das Flag stets; ohne das Flag speichert der Agent das Stichwort als Worte der Person. Ein Gruppenereignis mit dem Flag wird übernommen (`owned: true`, damit der Konnektor seinen eigenen Bot stumm schaltet) und ungelesen verworfen.

## Fähigkeiten und was dann fehlt

| Fehlt | Wirkung |
|---|---|
| `outbox` | Keine geplanten Eröffnungen, keine Rückfrage und keine Ausrede bei einem fehlgeschlagenen Modellaufruf in einer Gruppe. QQ-IDs erhalten sie weiterhin über NapCat, wenn `QQ_ONEBOT_URL` gesetzt und erreichbar ist. Die Ausrede einer DM kommt in den `replies` der Antwort zurück und benötigt die Outbox nicht. |
| `quote_text` | Der Agent versteht eine zitierte Nachricht nur, wenn er diese Nachricht selbst gesehen hat. |
| `reply_handle` | Wie ein fehlendes `outbox`. |
| `addressed` falsch | Die Persona behandelt an sie gerichtete Nachrichten als Hintergrundgeplauder. |

## Einen Konnektor schreiben

1. Empfangen Sie eine Nachricht von der Plattform. Überspringen Sie die eigenen Nachrichten des Bots und Ereignisse, die keine Nachrichten sind (Beitritte, Rückrufe, Anstupser).
2. Erstellen Sie das oben beschriebene Ereignis. Setzen Sie `addressed` nach den eigenen Erwähnungs- und Antwortregeln der Plattform.
3. Signieren und senden Sie das Ereignis. Senden Sie `replies` der Reihe nach, und schalten Sie andere Bot-Logik stumm, wenn `owned` wahr ist.
4. Wenn die Plattform von sich aus senden kann, fügen Sie `connector_id`, `reply_handle` und `capabilities: ["outbox"]` hinzu und führen Sie die Abfrageschleife aus: abfragen, jede Zustellung über ihren `reply_handle` ausliefern und bei der nächsten Abfrage bestätigen.

`integrations/sdk/personagent_connector.py` erledigt die Schritte 3 und 4.
