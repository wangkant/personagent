# Konnektor-SDK

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · Deutsch · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)

`personagent_connector.py` ist die Client-Seite des [Konnektor-Protokolls](../../docs/connectors.de.md) in einer Datei. Es signiert jede Anfrage, lehnt eine unsichere Basis-URL ab und führt die Outbox-Schleife mit höchstens einmaliger Zustellung und Acks aus. Es benötigt nur `httpx`: Kopieren Sie die Datei neben Ihren Konnektor und führen Sie `pip install httpx` aus. Als Paket wird es nicht veröffentlicht.

## Beispiel

Dieses Programm ist ein vollständiger Konnektor für eine Ersatzplattform, das Terminal: Jede eingegebene Zeile erreicht die Figur als Direktnachricht, und ihre Antworten werden ausgegeben. Starten Sie den Agenten mit `personagent run --port 8080` und führen Sie das Programm dann in dem Ordner aus, der `personagent_connector.py` enthält.

```python
import asyncio
import time
import uuid

from personagent_connector import Connector

BASE_URL = "http://127.0.0.1:8080"
TOKEN = ""  # the agent's CONNECTOR_TOKEN; blank works only on the same machine


def show(item: dict) -> None:
    # A real connector sends each item to the platform as one message.
    if item.get("type") == "text":
        print("character:", item["text"])
    else:
        print("character sent:", item.get("type"))


async def deliver(delivery: dict) -> tuple[str, int]:
    # An outbox delivery: a message nobody asked for. A real connector reaches
    # the conversation through delivery["reply_handle"].
    for item in delivery["items"]:
        show(item)
    return "sent", len(delivery["items"])


async def chat(conn: Connector) -> None:
    while True:
        text = await asyncio.to_thread(input, "> ")
        if not text.strip():
            continue
        answer = await conn.send_event({
            "platform": "console",
            "conversation_type": "dm",
            "sender_id": "me",
            "sender_name": "Me",
            "bot_id": "bot",
            "message_id": uuid.uuid4().hex,
            "sent_at": int(time.time()),
            "addressed": True,
            "text": text,
            "segments": [{"type": "text", "text": text}],
            "reply_handle": "me",
            "capabilities": ["outbox"],
        })
        for item in answer["replies"]:
            show(item)
        if not answer["owned"]:
            print("(the agent did not take this message)")


async def main() -> None:
    conn = Connector(BASE_URL, TOKEN, connector_id="console-1")
    try:
        await asyncio.gather(chat(conn), conn.run_outbox(deliver))
    finally:
        await conn.aclose()


asyncio.run(main())
```

`deliver` gibt `(status, sent_items)` zurück; status ist `sent`, `partial`, `failed`, `refused` oder `unsupported`, wie in der Ack-Tabelle des Protokolls. Wenn nur einige Einträge hinausgingen, geben Sie `("partial", n)` zurück. Die Schleife bestätigt jede Zustellung bei der nächsten Abfrage, sendet keine zweimal und meldet eine Zustellung als `expired`, deren Frist abgelaufen war, bevor `deliver` aufgerufen wurde.

## Fehler

`send_event` löst bei einem Fehlerstatus `httpx.HTTPStatusError` aus. `error_code(exc.response)` liefert den stabilen `code` des Agenten, etwa `invalid_schema` oder `invalid_envelope`; die [Fehlertabelle](../../docs/connectors.de.md#fehler) erklärt jeden davon. `run_outbox` löst bei einer abgewiesenen Abfrage nie eine Ausnahme aus: Es protokolliert Status und Code und versucht es mit wachsender Pause von bis zu einer Minute erneut; nach einem `404` wartet es zehn Minuten.
