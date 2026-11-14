# 连接器 SDK

[English](README.md) · 简体中文 · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)

`personagent_connector.py` 是[连接器协议](../../docs/connectors.zh-CN.md)客户端的单文件实现。它为每个请求签名，拒绝不安全的基础 URL，并运行 outbox 循环，保证每次投递最多发送一次并完成确认。它只依赖 `httpx`：把这个文件复制到连接器旁边，再执行 `pip install httpx` 即可。它没有作为软件包发布。

## 示例

下面的程序是一个完整的连接器，以终端作为替代平台：你输入的每一行都会作为私聊消息送到角色那里，角色的回复会打印出来。先用 `personagent run --port 8080` 启动 agent，再在存放 `personagent_connector.py` 的文件夹中运行此程序。

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

`deliver` 返回 `(status, sent_items)`，其中 status 为 `sent`、`partial`、`failed`、`refused` 或 `unsupported`，与协议中的确认表一致。只发出了部分条目时，返回 `("partial", n)`。循环在下一次拉取时确认每次投递，任何投递都不会发送两次；如果调用 `deliver` 之前投递已过期，则报告为 `expired`。

## 错误

`send_event` 遇到错误状态码时抛出 `httpx.HTTPStatusError`。`error_code(exc.response)` 返回 agent 稳定的 `code`，例如 `invalid_schema` 或 `invalid_envelope`；各代码的含义见[错误表](../../docs/connectors.zh-CN.md#错误)。拉取被拒绝时，`run_outbox` 从不抛出异常，而是记录状态码和代码，并以逐渐延长、最长一分钟的间隔重试；遇到 `404` 时等待十分钟。
