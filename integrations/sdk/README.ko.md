# 커넥터 SDK

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · 한국어 · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)

`personagent_connector.py`는 [커넥터 프로토콜](../../docs/connectors.ko.md)의 클라이언트 쪽을 파일 하나로 구현한 것입니다. 요청마다 서명하고, 안전하지 않은 기본 URL을 거부하며, 배달을 최대 한 번만 보내고 ack를 돌려주는 아웃박스 루프를 실행합니다. 필요한 것은 `httpx`뿐입니다. 이 파일을 커넥터 옆에 복사하고 `pip install httpx`를 실행하십시오. 패키지로는 배포하지 않습니다.

## 예제

이 프로그램은 터미널을 대신 플랫폼으로 쓰는 완전한 커넥터입니다. 입력한 각 줄은 DM으로 캐릭터에게 가고, 캐릭터의 답장이 출력됩니다. 먼저 `personagent run --port 8080`으로 에이전트를 시작한 뒤, `personagent_connector.py`가 있는 폴더에서 이 프로그램을 실행하십시오.

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

`deliver`는 `(status, sent_items)`를 돌려줍니다. status는 프로토콜의 ack 표와 같이 `sent`, `partial`, `failed`, `refused`, `unsupported` 중 하나입니다. 일부 항목만 보냈다면 `("partial", n)`을 돌려주십시오. 루프는 각 배달의 ack를 다음 가져오기 때 보내고, 같은 배달을 두 번 보내지 않으며, `deliver`를 호출하기 전에 시간이 지난 배달은 `expired`로 보고합니다.

## 오류

`send_event`는 오류 상태에 대해 `httpx.HTTPStatusError`를 일으킵니다. `error_code(exc.response)`는 `invalid_schema`나 `invalid_envelope` 같은 에이전트의 바뀌지 않는 `code`를 돌려줍니다. 각 코드의 뜻은 [오류 표](../../docs/connectors.ko.md#오류)에 있습니다. `run_outbox`는 가져오기가 거부되어도 예외를 일으키지 않습니다. 상태와 코드를 로그에 남기고, 최대 1분까지 점점 늘어나는 간격으로 다시 시도합니다. `404` 뒤에는 10분을 기다립니다.
