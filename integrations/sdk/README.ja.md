# コネクター SDK

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · 日本語 · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)

`personagent_connector.py` は、[コネクタープロトコル](../../docs/connectors.ja.md)のクライアント側を 1 ファイルにまとめたものです。各リクエストに署名し、安全でないベース URL を拒否し、配信を最大 1 回に保ちつつ ack を返すアウトボックスのループを実行します。必要なのは `httpx` だけです。このファイルをコネクターの隣にコピーし、`pip install httpx` を実行してください。パッケージとしては公開していません。

## 例

このプログラムは、端末を代わりのプラットフォームとする完全なコネクターです。入力した各行が DM としてキャラクターに届き、その返信が表示されます。まず `personagent run --port 8080` でエージェントを起動し、`personagent_connector.py` のあるフォルダーでこのプログラムを実行してください。

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

`deliver` は `(status, sent_items)` を返します。status はプロトコルの ack の表と同じく `sent`、`partial`、`failed`、`refused`、`unsupported` のいずれかです。一部の項目だけ送れたときは `("partial", n)` を返してください。ループは各配信の ack を次の取得で返し、同じ配信を 2 度送ることはありません。`deliver` を呼ぶ前に期限が切れた配信は `expired` として報告します。

## エラー

`send_event` はエラーのステータスに対して `httpx.HTTPStatusError` を送出します。`error_code(exc.response)` は、`invalid_schema` や `invalid_envelope` のようなエージェントの変わらない `code` を返します。各コードの意味は[エラーの表](../../docs/connectors.ja.md#エラー)にあります。`run_outbox` は取得が拒否されても例外を送出しません。ステータスとコードをログに残し、最長 1 分まで少しずつ延ばした間隔で再試行します。`404` の後は 10 分待ちます。
