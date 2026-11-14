# SDK des connecteurs

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · Français · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)

`personagent_connector.py` est le côté client du [protocole des connecteurs](../../docs/connectors.fr.md) en un seul fichier. Il signe chaque requête, refuse une URL de base non sûre et exécute la boucle de la boîte d'envoi avec livraison au plus une fois et accusés de réception. Il n'a besoin que de `httpx` : copiez le fichier à côté de votre connecteur, puis exécutez `pip install httpx`. Il n'est pas publié sous forme de paquet.

## Exemple

Ce programme est un connecteur complet pour une plateforme de substitution, le terminal : chaque ligne que vous saisissez parvient au personnage comme message privé, et ses réponses s'affichent. Démarrez l'agent avec `personagent run --port 8080`, puis lancez le programme depuis le dossier qui contient `personagent_connector.py`.

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

`deliver` renvoie `(status, sent_items)`, où status vaut `sent`, `partial`, `failed`, `refused` ou `unsupported`, comme dans le tableau des accusés du protocole. Lorsque seuls certains éléments sont partis, renvoyez `("partial", n)`. La boucle accuse chaque livraison lors de l'interrogation suivante, n'en envoie aucune deux fois et signale comme `expired` une livraison dont le délai a expiré avant l'appel à `deliver`.

## Erreurs

`send_event` lève `httpx.HTTPStatusError` pour un statut d'erreur. `error_code(exc.response)` renvoie le `code` stable de l'agent, comme `invalid_schema` ou `invalid_envelope` ; le [tableau des erreurs](../../docs/connectors.fr.md#erreurs) explique chacun d'eux. `run_outbox` ne lève jamais d'exception pour une interrogation refusée : il consigne le statut et le code, puis réessaie avec une pause croissante d'au plus une minute ; après un `404`, il attend dix minutes.
