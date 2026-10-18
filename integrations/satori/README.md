# Satori connector

This connector links [personagent](https://github.com/wangkant/personagent)
to a [Satori](https://satori.chat) server. Satori is a cross-platform chat
protocol. A server such as [Koishi](https://koishi.chat) (with its
`server-satori` plugin), Chronocat or LLOneBot logs in to the chat
platforms, and a client like this one receives every message from every
login over one websocket. One connector process therefore puts the persona
on every platform the server has an adapter for.

Satori and Koishi are third-party software. personagent does not need them
for QQ, WeChat, Telegram or Discord, which it connects itself, or for the
platforms its local page sets up through AstrBot. Use this connector when
you already run Koishi, or when you want a platform that only Koishi
reaches.

The connector forwards each allowed message to the agent's
`POST /v1/events` as a neutral event ([docs/connectors.md](../../docs/connectors.md))
and sends the replies back through Satori. It also pulls the agent's outbox,
so scheduled openers, follow-up questions and excuses reach the chat.

[satori-python](https://github.com/RF-Tar-Railt/satori-python) handles the
Satori side: the websocket, the login list and the HTTP API. This connector
maps between Satori and personagent's event format, and uses
[`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py)
for signing and the outbox loop.

## Setup, with Koishi

1. **Koishi.** Install Koishi with the desktop launcher or
   `npm init koishi@latest`. In its console, add and configure an adapter
   for your platform, such as `adapter-telegram` or `adapter-discord`, and
   make sure the bot is online. Enable the `server` and `server-satori`
   plugins. Koishi then serves Satori at `http://127.0.0.1:5140/satori`.
   Give `server-satori` a `token` if anything other than this machine can
   reach that port.

   Koishi keeps running its other plugins. If one of them also answers
   messages, such as a chat model or a reply plugin, it will answer
   alongside the persona, and the connector cannot silence it. Disable that
   plugin, or scope it away from the conversations you forward.

2. **The agent.** Run personagent (`personagent run`, see its README). If
   the connector and the agent are on different hosts, set
   `CONNECTOR_TOKEN` in the agent's `.env` and put the agent behind HTTPS.
   Set the token before you add any proxy or tunnel, even on a single host.

3. **The connector.** The connector is a script in this repository, so it
   needs a copy of the repository (a clone, or the ZIP from GitHub) and a
   Python environment of its own, because `satori-python` is not one of
   personagent's dependencies. In a clone that already has personagent's
   `.venv`, install into that environment:

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   If you installed personagent from PyPI with pip, or run it with uvx,
   create a separate venv next to the copy:

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   On Windows the interpreter is `.venv\Scripts\python.exe` or
   `connector-venv\Scripts\python.exe`. Next, copy the settings file:

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   In `integrations/satori/.env`, set the Satori server's URL and token, the
   agent's base URL and `CONNECTOR_TOKEN`, and the conversations to forward
   (see [Allowlists](#allowlists)). Then start the connector with the same
   interpreter:

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE` reads a different settings file. Any setting can also be
   given as an environment variable, which takes precedence over the file.

4. **Check that it works.** For each bot the server holds, the log shows a
   line such as `Satori login telegram:7000 is ONLINE`. Mention the bot in a
   forwarded group. The agent's log shows the turn, and the reply appears in
   the chat. If nothing happens, set `SATORI_LOG_LEVEL=DEBUG`.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | The Satori server. A trailing `/v1` is optional. |
| `SATORI_TOKEN` | | The server's token (in Koishi, `server-satori` → `token`). |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | The agent's base URL. `/v1/events` and `/v1/outbox` are appended. |
| `CONNECTOR_TOKEN` | | The agent's `CONNECTOR_TOKEN`. |
| `SATORI_GROUPS` | | Groups to forward, as channel or guild ids, optionally `platform:id`. Empty forwards none, `*` forwards all. |
| `SATORI_DM_USERS` | | People whose DMs are forwarded, as user ids, optionally `platform:id`. Empty forwards none, `*` forwards all. |
| `SATORI_PLATFORMS` | all | Limits the connector to these Satori platforms. |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | Renames platforms as the agent sees them: `satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | Pull the agent's outbox. |
| `SATORI_CONNECTOR_ID` | from `SATORI_URL` | This connector's id at the agent. Keep it stable. |
| `SATORI_TIMEOUT_S` | `420` | How long one turn may take. Keep it above the agent's `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`. |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | Download public image URLs in the connector instead of passing the URL to the agent. |
| `SATORI_LOG_LEVEL` | `INFO` | |

The agent URL must be a loopback address, or HTTPS with `CONNECTOR_TOKEN`
set. Otherwise the connector refuses to start. If `SATORI_TOKEN` would be
sent over plain `http` to another host, the connector logs a warning.

## Allowlists

The connector denies by default. With empty lists it forwards nothing.

- A group is a Satori channel. It is forwarded when its channel id or its
  guild id is in `SATORI_GROUPS`. On Discord or KOOK, one guild id therefore
  admits every channel in that guild, and each channel is still a separate
  conversation.
- A DM is forwarded when the sender's user id is in `SATORI_DM_USERS`.
- An entry can name its platform, as in `telegram:-1001234` or
  `discord:4242`, and then matches only on that platform. A bare entry
  matches on every platform.
- `*` forwards every group (or every DM) and marks the event
  `prefiltered: false`. The agent's own `ACCESS_GROUPS` and
  `ACCESS_DM_USERS` then decide, and a platform with no entries there is
  refused.

Koishi's `inspect` plugin prints the platform, channel, guild and user ids
of a message.

## Platform names and QQ

personagent stores ids as `<platform>:<id>`, where the platform is the
Satori login's platform (`telegram`, `discord`, `onebot` and so on). The log
line from step 4 shows it. Two cases need care:

- **QQ through OneBot** (Koishi's `adapter-onebot`, with NapCat or LLOneBot
  behind it) uses QQ numbers as ids. To keep what the agent learned on an
  existing QQ deployment, add the platform to the agent's
  `CONNECTOR_QQ_PLATFORMS` (`CONNECTOR_QQ_PLATFORMS=onebot`). Its ids are
  then stored bare, like QQ numbers from NapCat, and the QQ entries of
  `ACCESS_GROUPS` and `ACCESS_DM_USERS` apply to them. Do this only for a
  platform whose ids really are QQ numbers.
- **The official QQ bot API** (Koishi's `adapter-qq`) calls its platform
  `qq`, but its ids are openids, not QQ numbers. The connector renames the
  platform to `qqbot` so its ids are never mistaken for QQ numbers.
  `SATORI_PLATFORM_NAMES` overrides the rename. personagent can also connect
  official QQ bots itself, without Koishi.

## What works

| Feature | Status |
|---|---|
| Group chats and DMs | Yes. A DM is a `DIRECT` channel, or a message without a guild. |
| Addressed detection (`addressed`) | An `<at>` of the bot (by id, or by the bot's name when the server gives no id), and a reply to one of the bot's messages. `@all` counts as text, not a mention. |
| Quoted messages | The quoted text, sender and id, taken from a `<quote>` element or from `message.quote`. |
| Images in | `data:` and `internal:` images, and images on the Satori server, are inlined. Public URLs are passed on for the agent to fetch. Private-network URLs are described as `(sent an image)`. At most 4 downloads per message, 4 MB each. |
| Stickers and emoji | `<emoji>` and QQ `<face>` arrive as emoji, and the persona knows it cannot see them. |
| Voice, video, files | Described in words: `(sent a voice message)`, `(sent a video)`, `(sent a file: deck.pdf)`. |
| Replies | Text, and images as `data:` URIs, each sent as a separate message with a short gap. In groups, a mention the agent asks for becomes an `<at>`. |
| Passive-reply platforms | Replies carry the event's `referrer`, which the official QQ bot API needs to answer a message. |
| Outbox | Scheduled openers, follow-ups and excuses go to the channel through the login that received the conversation. The connector signs each reply handle with a key derived from `SATORI_TOKEN` and `CONNECTOR_TOKEN`, and sends only to handles it signed. After you change either token, a conversation becomes reachable again once it has sent a message. An agent with `CONNECTOR_OUTBOX_ENABLED=false` answers 404, and the connector retries every 10 minutes. |
| Typing indicator | No. Satori has no typing API. |
| `owned` | Honoured: the connector sends nothing else. It cannot stop other Koishi plugins (see step 1). |

Platform rules still apply. The official QQ bot API, for example, strictly
limits the messages a bot may send unprompted, so outbox deliveries there
may come back `failed`.

## Tests

`tests/test_satori_connector.py` runs without satori-python and without a
network. It fakes the element objects, the account and the agent.
