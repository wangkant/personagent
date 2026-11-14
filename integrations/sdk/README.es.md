# SDK de conectores

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · Español · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)

`personagent_connector.py` es el lado cliente del [protocolo de conectores](../../docs/connectors.es.md) en un solo archivo. Firma cada solicitud, rechaza una URL base insegura y ejecuta el bucle de la bandeja de salida con entrega como máximo una vez y confirmaciones. Solo necesita `httpx`: copie el archivo junto a su conector y ejecute `pip install httpx`. No se publica como paquete.

## Ejemplo

Este programa es un conector completo para una plataforma de sustitución, el terminal: cada línea que escribe llega al personaje como mensaje directo, y sus respuestas se muestran en pantalla. Inicie el agente con `personagent run --port 8080` y ejecute el programa desde la carpeta que contiene `personagent_connector.py`.

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

`deliver` devuelve `(status, sent_items)`, donde status es `sent`, `partial`, `failed`, `refused` o `unsupported`, como en la tabla de confirmaciones del protocolo. Cuando solo salieron algunos elementos, devuelva `("partial", n)`. El bucle confirma cada entrega en la consulta siguiente, no envía ninguna dos veces e informa como `expired` una entrega cuyo plazo venció antes de llamar a `deliver`.

## Errores

`send_event` lanza `httpx.HTTPStatusError` ante un estado de error. `error_code(exc.response)` devuelve el `code` estable del agente, como `invalid_schema` o `invalid_envelope`; la [tabla de errores](../../docs/connectors.es.md#errores) explica cada uno. `run_outbox` nunca lanza una excepción por una consulta rechazada: registra el estado y el código, y lo intenta de nuevo con una pausa creciente de hasta un minuto; tras un `404` espera diez minutos.
