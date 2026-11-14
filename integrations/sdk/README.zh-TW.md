# 聯結器 SDK

[English](README.md) · [简体中文](README.zh-CN.md) · 繁體中文 · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)

`personagent_connector.py` 是[聯結器協定](../../docs/connectors.zh-TW.md)用戶端的單一檔案實作。它會簽署每個請求、拒絕不安全的基礎 URL，並執行 outbox 迴圈，確保每次投遞最多傳送一次並完成確認。它只需要 `httpx`：將這個檔案複製到聯結器旁邊，再執行 `pip install httpx` 即可。它並未以套件形式發布。

## 範例

下面的程式是一個完整的聯結器，以終端機作為替代平台：你輸入的每一行都會作為私訊送到角色那裡，角色的回覆會列印出來。先以 `personagent run --port 8080` 啟動 agent，再於存放 `personagent_connector.py` 的資料夾中執行此程式。

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

`deliver` 傳回 `(status, sent_items)`，其中 status 為 `sent`、`partial`、`failed`、`refused` 或 `unsupported`，與協定中的確認表一致。只送出部分項目時，傳回 `("partial", n)`。迴圈會在下一次拉取時確認每次投遞，任何投遞都不會傳送兩次；如果呼叫 `deliver` 之前投遞已逾期，則回報為 `expired`。

## 錯誤

`send_event` 遇到錯誤狀態碼時會擲出 `httpx.HTTPStatusError`。`error_code(exc.response)` 傳回 agent 穩定的 `code`，例如 `invalid_schema` 或 `invalid_envelope`；各錯誤碼的含義見[錯誤表](../../docs/connectors.zh-TW.md#錯誤)。拉取遭拒時，`run_outbox` 從不擲出例外，而是記錄狀態碼和錯誤碼，並以逐漸延長、最長一分鐘的間隔重試；遇到 `404` 時等候十分鐘。
