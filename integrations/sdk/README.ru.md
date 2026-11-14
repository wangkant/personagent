# SDK для коннекторов

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · Русский

`personagent_connector.py` — клиентская сторона [протокола коннекторов](../../docs/connectors.ru.md) в одном файле. Он подписывает каждый запрос, отказывается работать с небезопасным базовым URL и выполняет цикл исходящей очереди с доставкой не более одного раза и подтверждениями. Ему нужен только `httpx`: скопируйте файл рядом со своим коннектором и выполните `pip install httpx`. Пакетом он не публикуется.

## Пример

Эта программа — полный коннектор для платформы-заменителя, терминала: каждая введённая строка доходит до персонажа как личное сообщение, а его ответы выводятся на экран. Запустите агент командой `personagent run --port 8080`, затем запустите программу из папки, где лежит `personagent_connector.py`.

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

`deliver` возвращает `(status, sent_items)`, где status — `sent`, `partial`, `failed`, `refused` или `unsupported`, как в таблице подтверждений протокола. Если ушла только часть элементов, верните `("partial", n)`. Цикл подтверждает каждую доставку при следующем опросе, ни одну не отправляет дважды и сообщает как `expired` доставку, срок которой истёк до вызова `deliver`.

## Ошибки

`send_event` выбрасывает `httpx.HTTPStatusError` при статусе ошибки. `error_code(exc.response)` возвращает стабильный `code` агента, например `invalid_schema` или `invalid_envelope`; каждый из них объяснён в [таблице ошибок](../../docs/connectors.ru.md#ошибки). `run_outbox` никогда не выбрасывает исключение из-за отклонённого опроса: он записывает в журнал статус и код и повторяет попытку с растущей паузой до одной минуты; после `404` он ждёт десять минут.
