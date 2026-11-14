# Connector SDK

English · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)

`personagent_connector.py` is the client side of the
[connector protocol](../../docs/connectors.md) in one file. It signs each
request, refuses an unsafe base URL, and runs the outbox loop with
at-most-once delivery and acks. It needs only `httpx`: copy the file next to
your connector and `pip install httpx`. It is not published as a package.

## Example

This program is a complete connector for a stand-in platform, the terminal:
each line you type reaches the character as a direct message, and its
replies are printed. Start the agent with `personagent run --port 8080`,
then run the program from the folder that holds `personagent_connector.py`.

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

`deliver` returns `(status, sent_items)`, where status is `sent`,
`partial`, `failed`, `refused` or `unsupported`, as in the protocol's ack
table. When only some items went out, return `("partial", n)`. The loop
acks each delivery on the next pull, sends none twice, and reports a
delivery as `expired` when its time ran out before `deliver` was called.

## Errors

`send_event` raises `httpx.HTTPStatusError` for an error status.
`error_code(exc.response)` returns the agent's stable `code`, such as
`invalid_schema` or `invalid_envelope`; the
[error table](../../docs/connectors.md#errors) explains each one.
`run_outbox` never raises for a refused pull. It logs the status and the
code, and tries again with a growing pause of up to one minute; after a
`404` it waits ten minutes.
