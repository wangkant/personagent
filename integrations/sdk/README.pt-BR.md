# SDK de conectores

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · Português (Brasil) · [Русский](README.ru.md)

`personagent_connector.py` é o lado cliente do [protocolo de conectores](../../docs/connectors.pt-BR.md) em um único arquivo. Ele assina cada solicitação, recusa uma URL base insegura e executa o ciclo da caixa de saída com entrega no máximo uma vez e confirmações. Ele precisa apenas de `httpx`: copie o arquivo para junto do seu conector e execute `pip install httpx`. Ele não é publicado como pacote.

## Exemplo

Este programa é um conector completo para uma plataforma substituta, o terminal: cada linha digitada chega ao personagem como mensagem privada, e as respostas dele são exibidas. Inicie o agente com `personagent run --port 8080` e execute o programa na pasta que contém `personagent_connector.py`.

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

`deliver` retorna `(status, sent_items)`, em que status é `sent`, `partial`, `failed`, `refused` ou `unsupported`, como na tabela de confirmações do protocolo. Quando só alguns itens saíram, retorne `("partial", n)`. O ciclo confirma cada entrega na consulta seguinte, não envia nenhuma duas vezes e informa como `expired` uma entrega cujo prazo venceu antes de `deliver` ser chamado.

## Erros

`send_event` lança `httpx.HTTPStatusError` para um status de erro. `error_code(exc.response)` retorna o `code` estável do agente, como `invalid_schema` ou `invalid_envelope`; a [tabela de erros](../../docs/connectors.pt-BR.md#erros) explica cada um. `run_outbox` nunca lança exceção por uma consulta recusada: ele registra o status e o código e tenta de novo com uma pausa crescente de até um minuto; após um `404`, espera dez minutos.
