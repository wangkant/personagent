# Connector protocol

The agent never talks to a chat platform itself. A connector does that work.
It logs in to one platform, or to a framework that covers many, turns each
incoming message into a neutral event, posts the event to personagent and
delivers what comes back. Everything platform-specific stays in the
connector, so the agent sees the same format from every platform.

This repository ships four connectors:

| Connector | Reaches | Path |
|---|---|---|
| Direct | QQ official bots, personal WeChat (iLink), Telegram and Discord, with no other software. The local page and `personagent up` run it as one process, `python -m persona_agent.direct`. | `persona_agent/direct/` |
| AstrBot plugin | The platforms of AstrBot, a third-party bridge. The AstrBot that personagent manages for KOOK, Feishu/Lark, DingTalk, Slack, WeCom, Mattermost, Misskey, OneBot v11 and the rest gets the plugin automatically. For an AstrBot you already run, `personagent connect astrbot` sets it up. You can also upload `astrbot_plugin_personagent.zip` from a GitHub Release with AstrBot's Install from File and set `connector_token` yourself. | `integrations/astrbot/` |
| Satori | Every Satori implementation (Koishi and others, third-party): QQ, Telegram, Discord, KOOK, Lark, DingTalk, LINE, WhatsApp, Matrix, Zulip, email and more. | `integrations/satori/` |
| Matrix | Matrix rooms, and through third-party mautrix bridges WhatsApp, Signal, Messenger, Instagram, Google Messages and more. | `integrations/matrix/` |

All four speak the protocol described on this page. To write a new one you
need this page and an HTTP client. The Python helper in
`integrations/sdk/personagent_connector.py` signs requests and runs the
outbox loop for you. It takes the base URL, the token and the connector's
`connector_id`, and it needs `httpx`.

## Configuration

The local page configures the direct connector. The other three use the same
names, so a setting means the same thing in each of them:

| Meaning | Satori | Matrix | AstrBot plugin key |
|---|---|---|---|
| personagent's base URL, such as `http://127.0.0.1:8080`. The connector appends `/v1/events` and `/v1/outbox`. | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| The shared token, equal to the agent's `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| This connector's id (`connector_id` below) | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| How long one request may take, in seconds | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| Pull the outbox | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| Groups to forward | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| People whose DMs are forwarded | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| The platform's server | `SATORI_URL` | `MATRIX_URL` | AstrBot's own |

An empty group or DM list forwards nothing of that kind. `*` forwards all of
it and marks the events `"prefiltered": false`, which leaves the decision to
the agent's `ACCESS_GROUPS` and `ACCESS_DM_USERS`. Each connector's README
lists its remaining settings.

## Addressing

personagent stores every id as `<platform>:<id>`, for example
`telegram:-1001234` for a group or `discord:4242` for a user. `platform` is
the connector's name for the platform, in lowercase and without `:`.

QQ is the one exception, kept for compatibility. Its ids are stored bare
(`123456`), and `qq:123456` in any setting means the same thing. If a
connector carries QQ and you want its learned state to line up with an
existing QQ deployment, name its platform in `CONNECTOR_QQ_PLATFORMS`. The
AstrBot plugin's QQ adapter is `aiocqhttp`. Ids from the platforms listed
there are stored bare as well.

## Authentication

Both endpoints below use the same scheme. When `CONNECTOR_TOKEN` is set on
the agent, every request carries four headers:

- `X-Personagent-Token`: the token.
- `X-Personagent-Timestamp`: unix seconds. A value more than five minutes
  away from the agent's clock is refused.
- `X-Personagent-Nonce`: a fresh random value. A reused nonce is refused.
- `X-Personagent-Signature`: `sha256=` followed by the hex HMAC-SHA256 of
  `timestamp + "." + nonce + "." + body`, keyed with the token.

The body is canonical JSON: UTF-8, sorted keys, compact separators and
unescaped non-ASCII. The token is also the signing key, so keep it out of
logs.

Without a token, the agent accepts only local programs that call
`127.0.0.1` or `localhost` directly. A connector must refuse to send to
anything other than a loopback URL, or an HTTPS URL with a token.

## Inbound: `POST /v1/events`

Each request carries one message in and returns the replies to it.

```json
{
  "platform": "telegram",
  "conversation_type": "group",
  "conversation_id": "-1001234",
  "sender_id": "42",
  "sender_name": "Alex",
  "bot_id": "7000",
  "message_id": "881",
  "sent_at": 1790320000,
  "addressed": true,
  "text": "Nova, how was your day?",
  "segments": [
    {"type": "text", "text": "Nova, how was your day?"}
  ],
  "connector_id": "astrbot-7f3c",
  "reply_handle": "tg-bot:GroupMessage:-1001234",
  "capabilities": ["outbox", "quote_text"]
}
```

The required fields are `platform`, `conversation_type` (`group` or `dm`),
`sender_id`, `message_id` and `sent_at`, plus `conversation_id` for groups.
`sent_at` is when the platform stamped the message, in unix seconds. Send
raw platform ids. The agent adds the prefix.

The connector sets `addressed`. It is true when the message mentions the
bot, replies to one of the bot's messages, or is addressed to the bot under
the platform's own rules. The agent also notices its name in the text on its
own. It reads a quote of its own message, or an @ of the bot, as a reaction it
may learn from, so set `addressed` on replies to the bot. A quote of another
member's message is never a reaction to the bot.

An event whose `sender_id` equals its `bot_id` is the bot's own message
echoed back. The agent drops it unread and answers
`{"handled": false, "owned": true, "replies": []}`, so the connector's own
bot logic stays quiet as well. Skip such events in the connector.

Segments come in order:

| Type | Fields | Notes |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | A mention of someone. It mentions the bot when `user_id` equals `bot_id`. |
| `image` | `url` or `b64`, `sticker` (bool) | `sticker` marks a sticker sent as an image. |
| `emoji` | `name`, `id` | A platform sticker or custom emoji the agent cannot see. `name` is what a person would call it. |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | The message this one quotes. Send `text` whenever the platform provides it. |

Describe anything else in words, as a `text` segment such as `(sent a voice
message)` or `(sent a file: deck.pdf)`. The agent drops unknown segment
types.

These optional fields turn on more of the agent:

| Field | Meaning |
|---|---|
| `connector_id` | A stable id for this connector instance. The outbox requires it. |
| `reply_handle` | Whatever the connector needs to reach this conversation later without an incoming message: AstrBot's `unified_msg_origin`, a Matrix room id, or a Satori login plus channel id. The agent treats it as opaque, stores it per conversation and hands it back in outbox deliveries. |
| `capabilities` | What the connector can do. `outbox` means it polls the outbox and can send unprompted. `quote_text` means reply segments carry the quoted text. |
| `prefiltered` | `true` (the default) when the connector applied its own allowlist. `false` makes the agent's lists the only filter. |
| `proactive` | Marks a DM event as a cue the connector wrote, not the person's words. See "Speaking first without the outbox". |

The response looks like this:

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`: send them in order, each as a separate message. When
  `mention_user_id` is present, it is the prefixed id to mention. Render the
  mention the way the platform does.
- `owned`: the agent has taken this conversation. When it is true, stop any
  other bot logic from answering, even if `replies` is empty, because the
  persona chose to stay quiet. When it is false, the message is yours to
  handle. Either the conversation is not on the agent's allowlists, or the
  agent cannot answer at all (no `LLM_API_KEY`, or `AGENT_ENABLED=false`). In
  the second case the agent's log carries one ERROR line naming the cause.
- The request lasts as long as the turn, which is a short debounce plus
  every model call. Allow at least `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`
  seconds.

## Outbox: `POST /v1/outbox`

Some messages do not answer a request. Examples are a scheduled opener, the
follow-up question after a rejection, and the excuse when the model is down
in a group. The agent queues these per conversation, and a connector that
declared `outbox` pulls them, so a connector behind NAT or a firewall works
the same way. Conversations stored under bare QQ ids (see Addressing) also use the
outbox while their connector is pulling. Otherwise they go through NapCat's
HTTP API, when `QQ_ONEBOT_URL` is set.

Request:

```json
{
  "kind": "outbox.pull",
  "connector_id": "astrbot-7f3c",
  "wait_s": 25,
  "max_deliveries": 10,
  "acks": [
    {"delivery_id": "d_5c1f...", "status": "sent", "sent_items": 2}
  ]
}
```

The agent holds the request for up to `wait_s` seconds (at most 30) until
something is queued, then answers:

```json
{
  "deliveries": [
    {
      "delivery_id": "d_9a07...",
      "conversation_key": "telegram:-1001234",
      "reply_handle": "tg-bot:GroupMessage:-1001234",
      "platform": "telegram",
      "conversation_type": "group",
      "conversation_id": "-1001234",
      "reason": "proactive",
      "expires_in_s": 300,
      "items": [{"type": "text", "text": "anyone still up?"}]
    }
  ],
  "next_wait_s": 25
}
```

`items` has the same shape as `replies`. `reason` is `proactive`,
`follow_up` or `excuse`, and `conversation_type` is `group` or `dm`.
`conversation_key` is the key the agent stores the conversation under, such
as `private:telegram:42` for a DM. `conversation_id` is the raw id the event
carried, which for a DM is the user id. The agent remembers `reply_handle`,
`connector_id` and `capabilities` from the latest admitted event in each
conversation, so a conversation becomes reachable once it has sent one
message.

Report each delivery in `acks` on the next pull:

| `status` | Meaning |
|---|---|
| `sent` | Every item went out. |
| `partial` | The first `sent_items` items went out. |
| `failed` | Nothing went out. |
| `expired` | Sending did not start within `expires_in_s`. |
| `refused` | The connector no longer allows the conversation. |
| `unsupported` | The platform cannot send unprompted to this conversation. |

Rules:

- **At most once.** The agent hands out a delivery once and never again,
  whatever happens to the ack. Keep the last few hundred `delivery_id`s and
  never send one twice.
- **In order.** Send one conversation's deliveries in the order you received
  them. Different conversations may go out in parallel.
- **Only acked deliveries count.** The agent treats an unacked delivery as
  not sent and records only acked deliveries as sent. It waits for the ack
  until your next pull, and for at most `expires_in_s` plus 60 seconds after
  handing the delivery out. Finish sending a batch before you pull again.
- **Liveness.** A connector that has not pulled for 90 seconds is treated as
  gone. Nothing is queued for its conversations until it pulls again, and
  anything queued for it, or handed to it without an ack, ends as not sent.
  Pull again as soon as a batch is delivered. That pull also carries the
  batch's acks.
- **`unsupported` sticks.** After that ack, the agent stops queueing for the
  conversation until an event brings a different `reply_handle`.
- **Body kinds.** The signature does not cover the URL path. The agent
  therefore refuses an event body on the outbox endpoint and an
  `outbox.pull` body on the event endpoint, with `400` and code
  `invalid_schema`. An event may carry `"kind": "event"`. An event with any
  other `kind` is refused.

A 404 without a `code` means the agent does not serve the outbox. A `404`
with code `outbox_disabled` means the operator turned it off with
`CONNECTOR_OUTBOX_ENABLED`. In both cases, wait a long while before you pull
again.

## Speaking first without the outbox

A connector that cannot poll can still open a DM. Its own scheduler, such as
an AstrBot plugin task or a cron entry, posts an ordinary DM event with
`"proactive": true` to `/v1/events`. The agent reads the text as a cue to
the persona ("they have been quiet a day; their exam was this morning"),
cuts it at 500 characters, and never stores it as the person's words. The
engine's proactive instructions still decide the turn and may keep the
persona silent. If the persona speaks, the reply comes back in the response
for the scheduler to relay.

The event needs everything the connector's normal events carry: the signed
headers, every required field, the same `platform` and raw `sender_id` the
connector sends for that person, non-empty text, and a new `message_id` each
time. An event with a repeated `message_id` is dropped silently. The cue
counts against the same DM cooldown as the agent's own openers
(`PROACTIVE_DM_COOLDOWN_S`), and it does not count as activity from the
person.

Always set the flag; without it, the agent stores the cue as the person's
words. A group event with the flag is claimed (`owned: true`, so the connector keeps its
own bot quiet) and dropped unread.

## Capabilities and what degrades

| Missing | Effect |
|---|---|
| `outbox` | No scheduled openers, no follow-up question, and no excuse for a failed model call in a group. QQ ids still get them through NapCat when `QQ_ONEBOT_URL` is set and reachable. A DM's excuse comes back in the response's `replies` and does not need the outbox. |
| `quote_text` | The agent understands a quoted message only if it saw that message itself. |
| `reply_handle` | Same as a missing `outbox`. |
| `addressed` wrong | The persona treats messages addressed to it as background chatter. |

## Writing a connector

1. Receive a message from the platform. Skip the bot's own messages and
   events that are not messages (joins, recalls, pokes).
2. Build the event described above. Set `addressed` from the platform's own
   mention and reply rules.
3. Sign and post the event. Send `replies` in order, and when `owned` is
   true, keep other bot logic quiet.
4. If the platform can send unprompted, add `connector_id`, `reply_handle`
   and `capabilities: ["outbox"]`, then run the pull loop: pull, deliver each
   delivery through its `reply_handle`, and ack on the next pull.

`integrations/sdk/personagent_connector.py` handles steps 3 and 4.
