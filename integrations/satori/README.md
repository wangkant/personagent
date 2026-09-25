# Satori connector

Connects [personagent](https://github.com/wangkant/personagent) to a
[Satori](https://satori.chat) server. Satori is a cross-platform chat protocol:
a server such as [Koishi](https://koishi.chat) (with its `server-satori`
plugin), Chronocat or LLOneBot logs in to the chat platforms, and a client like
this one gets every message from every login over one websocket. So one
process puts the persona on Telegram, Discord, KOOK, Lark, DingTalk, LINE, QQ
(through OneBot) and anything else the server has an adapter for.

The connector forwards each allowed message to the agent's
`POST /v1/events` as a neutral event ([docs/connectors.md](../../docs/connectors.md))
and sends the replies back through Satori. It also pulls the agent's outbox, so
scheduled openers, follow-up questions and excuses reach the chat.

## Why satori-python

The Satori side runs on [satori-python](https://github.com/RF-Tar-Railt/satori-python)
(MIT, maintained, used by the Entari framework). Its client already does
everything protocol-shaped this connector needs: the websocket with IDENTIFY,
heartbeat, resume and reconnect; the login list; parsing message content into
elements; and the HTTP API (`message.create`, resource downloads through the
server's proxy). The alternatives were writing the protocol by hand, or
`nonebot-adapter-satori`, which only runs inside NoneBot. What is left here is
the mapping between Satori and personagent's event format.

The agent side uses [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py)
for signing and the outbox loop.

## Setup, with Koishi

1. **Koishi.** Install it (the desktop launcher, or `npm init koishi@latest`).
   In its console, add and configure an adapter for your platform, for
   example `adapter-telegram` or `adapter-discord`, and make sure the bot is
   online. Enable the `server` and `server-satori` plugins. Koishi then serves
   Satori at `http://127.0.0.1:5140/satori`. Give `server-satori` a `token` if
   anything other than this machine can reach that port.

   Koishi keeps running its other plugins. If one of them also answers
   messages (a chat model, a reply plugin), it answers next to the persona:
   the connector cannot silence it. Disable it, or scope it away from the
   conversations you forward.

2. **The agent.** Run personagent as its README describes. If the connector
   and the agent are on different hosts, set `CONNECTOR_TOKEN` in the agent's
   `.env` and put the agent behind HTTPS.

3. **The connector.** From the personagent checkout:

   ```bash
   pip install -r integrations/satori/requirements.txt
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   Edit `integrations/satori/.env`: the Satori server's URL and token, the
   agent's base URL and `CONNECTOR_TOKEN`, and the conversations to forward (see
   [Allowlists](#allowlists)). Then:

   ```bash
   python integrations/satori/satori_connector.py
   ```

   `--config FILE` reads another settings file. Every setting can also be an
   environment variable, which wins over the file.

4. **Check it works.** The log shows `Satori login telegram:7000 is ONLINE`
   for each bot the server holds. Mention the bot in a forwarded group: the
   agent's log shows the turn, and the reply arrives in the chat. If nothing
   happens, set `SATORI_LOG_LEVEL=DEBUG`.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | the Satori server; a trailing `/v1` is optional |
| `SATORI_TOKEN` | | the server's token (Koishi: `server-satori` → `token`) |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | the agent's base URL; `/v1/events` and `/v1/outbox` are appended |
| `CONNECTOR_TOKEN` | | the agent's `CONNECTOR_TOKEN` |
| `SATORI_GROUPS` | | groups to forward: channel or guild ids, optionally `platform:id`; empty for none, `*` for all |
| `SATORI_DM_USERS` | | people whose DMs are forwarded: user ids, optionally `platform:id`; empty for none, `*` for all |
| `SATORI_PLATFORMS` | all | only these Satori platforms |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | rename platforms as the agent sees them: `satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | pull the agent's outbox |
| `SATORI_CONNECTOR_ID` | from `SATORI_URL` | this connector's id at the agent; keep it stable |
| `SATORI_TIMEOUT_S` | `420` | how long one turn may take; keep it above the agent's `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | download public image URLs here instead of passing the URL to the agent |
| `SATORI_LOG_LEVEL` | `INFO` | |

The agent URL must be loopback, or HTTPS with `CONNECTOR_TOKEN`; the connector
refuses to start otherwise. A `SATORI_TOKEN` sent over plain `http` to another
host is logged as a warning.

## Allowlists

The connector is **default-deny**: with empty lists it forwards nothing.

- A group is a Satori channel. It is forwarded when its channel id or its
  guild id is in `SATORI_GROUPS`, so on Discord or KOOK one guild id admits
  every channel in it, and each channel is still its own conversation.
- A DM is forwarded when the sender's user id is in `SATORI_DM_USERS`.
- An entry can name its platform, `telegram:-1001234` or `discord:4242`, and
  then matches only there. A bare entry matches on every platform.
- `*` forwards every group (or DM) and marks the event `prefiltered: false`,
  which hands the decision to the agent's own `ACCESS_GROUPS` and
  `ACCESS_DM_USERS`: a platform with no entries there is refused.

Koishi's `inspect` plugin prints the platform, channel, guild and user ids of
a message.

## Platform names and QQ

personagent stores ids as `<platform>:<id>`, and the platform is the Satori
login's (`telegram`, `discord`, `onebot`, ...; the log line in step 4 shows
it). Two cases need a thought:

- **QQ through OneBot** (Koishi's `adapter-onebot`, with NapCat or LLOneBot
  behind it) has QQ numbers as ids. To keep what the agent learned on an
  existing QQ deployment, add the platform to the agent's
  `CONNECTOR_QQ_PLATFORMS` (`CONNECTOR_QQ_PLATFORMS=onebot`): its ids are
  then stored bare, like the direct QQ path, and the QQ entries of
  `ACCESS_GROUPS` and `ACCESS_DM_USERS` apply to them. Do this only for a platform whose ids
  really are QQ numbers.
- **The official QQ bot API** (Koishi's `adapter-qq`) calls its platform `qq`
  but uses openids, not QQ numbers. The connector renames it `qqbot` so it can
  never be mistaken for QQ numbers; `SATORI_PLATFORM_NAMES` overrides it.

## What works

| Feature | Status |
|---|---|
| Group chats and DMs | Yes. A DM is a `DIRECT` channel, or a message without a guild |
| Addressed detection (`addressed`) | An `<at>` of the bot (by id, or by the bot's name when the server gives no id) and a reply to one of its messages. `@all` is text, not a mention |
| Quoted messages | The quoted text, sender and id, from a `<quote>` element or from `message.quote` |
| Images in | `data:` and `internal:` images and images on the Satori server are inlined; public URLs are passed on for the agent to fetch; private-network URLs are described as `(sent an image)`. At most 4 downloads, 4 MB each, per message |
| Stickers and emoji | `<emoji>` and QQ `<face>` arrive as emoji the persona knows it cannot see |
| Voice, video, files | Described in words: `(sent a voice message)`, `(sent a video)`, `(sent a file: deck.pdf)` |
| Replies | Text, and images as `data:` URIs, each as its own message with a short gap. A mention the agent asks for is an `<at>` in groups |
| Passive-reply platforms | Replies carry the event's `referrer`, which the official QQ bot API needs to answer a message |
| Outbox | Scheduled openers, follow-ups and excuses go to the channel through the login that received the conversation. The connector signs each reply handle with a key derived from `SATORI_TOKEN` and `CONNECTOR_TOKEN` and sends only to handles it signed, so after changing either token a conversation is reachable again once it has spoken. An agent with `CONNECTOR_OUTBOX_ENABLED=false` answers 404; the connector asks again every 10 minutes |
| Typing indicator | No: Satori has no typing API |
| `owned` | Honoured by never sending anything else; other Koishi plugins are not stopped (see step 1) |

Platform rules still apply: the official QQ bot API, for one, strictly limits
messages a bot sends unprompted, so outbox deliveries there may come back
`failed`.

## Tests

`tests/test_satori_connector.py` runs without satori-python or any network:
it fakes the element objects, the account and the agent.
