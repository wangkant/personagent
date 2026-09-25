# Connector protocol

personagent never talks to a chat platform itself. A **connector** does: it
logs in to one platform (or to a framework that covers many), turns each
incoming message into a neutral event, posts it to personagent, and delivers
what comes back. Everything platform-specific lives in the connector; the
agent sees one format for every platform.

Connectors in this repository:

| Connector | Reaches | Path |
|---|---|---|
| AstrBot plugin | every AstrBot adapter: QQ, Telegram, Discord, Slack, KOOK, Lark, DingTalk, LINE, WeCom, Mattermost, Misskey, ... | `integrations/astrbot/` |
| Satori | every Satori implementation (Koishi and others): QQ, Telegram, Discord, KOOK, Lark, DingTalk, LINE, WhatsApp, Matrix, Zulip, email, ... | `integrations/satori/` |
| Matrix | Matrix rooms, and through mautrix bridges WhatsApp, Signal, Messenger, Instagram, Google Messages, ... | `integrations/matrix/` |

A new connector needs only this page and an HTTP client. The Python helper in
`integrations/sdk/personagent_connector.py` signs requests and runs the outbox
loop for you; it takes the base URL below and the connector's `connector_id`.

## Configuration

The three connectors use the same names, so a setting means the same thing in
each:

| Meaning | Satori | Matrix | AstrBot plugin key |
|---|---|---|---|
| personagent's base URL, such as `http://127.0.0.1:8080`; the connector appends `/v1/events` and `/v1/outbox` | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| the shared token, the same value as the agent's `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| this connector's id (`connector_id` below) | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| how long one request may take, in seconds | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| pull the outbox | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| groups forwarded | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| people whose DMs are forwarded | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| the platform's server | `SATORI_URL` | `MATRIX_URL` | AstrBot's own |

An empty group or DM list forwards nothing of that kind; `*` forwards all of
it and marks the events `"prefiltered": false`, so the agent's
`ACCESS_GROUPS` and `ACCESS_DM_USERS` decide. Each connector's README lists
the rest of its settings.

## Addressing

Every id personagent stores is `<platform>:<id>`, for example
`telegram:-1001234` for a group or `discord:4242` for a user. `platform` is
the connector's name for the platform, lowercase, without `:`.

QQ is the one exception kept for compatibility: its ids are stored bare
(`123456`), and `qq:123456` in any setting means the same thing. A connector
that carries QQ and wants learned state to line up with an existing QQ
deployment names its platform in `CONNECTOR_QQ_PLATFORMS` (the AstrBot
plugin's QQ adapter is `aiocqhttp`); ids from those platforms are stored bare
too.

## Authentication

Both endpoints below use the same scheme. With `CONNECTOR_TOKEN` set on the
agent, every request carries:

- `X-Personagent-Token`: the token.
- `X-Personagent-Timestamp`: unix seconds; more than five minutes from the
  agent's clock is refused.
- `X-Personagent-Nonce`: a fresh random value; a reused one is refused.
- `X-Personagent-Signature`: `sha256=` + hex HMAC-SHA256, keyed with the
  token, of `timestamp + "." + nonce + "." + body`.

The body is canonical JSON: UTF-8, keys sorted, compact separators, non-ASCII
unescaped. The token is the signing key, so keep it out of logs.

Without a token the agent accepts only local programs calling `127.0.0.1` or
`localhost` directly. A connector must refuse to send to anything but a
loopback URL, or HTTPS with a token.

## Inbound: `POST /v1/events`

One message in, the replies to it out, in the same request.

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

Required: `platform`, `conversation_type` (`group` or `dm`), `sender_id`,
`message_id`, `sent_at` (when the platform stamped the message, unix
seconds), and `conversation_id` for groups. Ids are raw platform ids; the
agent adds the prefix.

`addressed` is the connector's job: true when the message mentions the bot,
replies to one of its messages, or is otherwise addressed to it by the
platform's own rules. The agent separately notices its name in the text.

Segments, in order:

| Type | Fields | Notes |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | a mention of someone; of the bot itself when `user_id` equals `bot_id` |
| `image` | `url` or `b64`, `sticker` (bool) | `sticker` marks a sticker sent as an image |
| `emoji` | `name`, `id` | a platform sticker or custom emoji the agent cannot see; `name` is what a person would call it |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | the message this one quotes; send `text` whenever the platform gives it |

Describe anything else in words, as a `text` segment: `(sent a voice
message)`, `(sent a file: deck.pdf)`. Unknown segment types are dropped.

Optional fields that turn on more of the agent:

| Field | Meaning |
|---|---|
| `connector_id` | a stable id for this connector instance; required for the outbox |
| `reply_handle` | whatever the connector needs to address this conversation later without an incoming message: AstrBot's `unified_msg_origin`, a Matrix room id, a Satori login plus channel id. Opaque to the agent, stored per conversation, handed back in outbox deliveries |
| `capabilities` | what the connector can do: `outbox` (it polls the outbox and can send unprompted), `quote_text` (reply segments carry the quoted text) |
| `prefiltered` | `true` (default) when the connector applied its own allowlist; `false` makes the agent's lists the only filter |
| `proactive` | this DM event is a cue the connector wrote, not the person's words; see "Speaking first without the outbox" |

The response:

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`: send them in order, each as its own message. `mention_user_id`,
  when present, is the prefixed id to mention; render it the platform's way.
- `owned`: the agent has taken this conversation. When it is true, stop any
  other bot logic from answering, even with an empty `replies`: the persona
  chose to stay quiet. When it is false, the message is yours to handle.
- The request lasts as long as the turn: a short debounce plus every model
  call. Allow at least `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` seconds.

## Outbox: `POST /v1/outbox`

Some messages are not an answer to a request: a scheduled opener, the follow-up
question after a rejection, the excuse when the model is down. The agent
queues those per conversation, and a connector that declared `outbox` pulls
them. Pull rather than push means the agent never needs to reach the
connector, so a connector behind NAT or a firewall works the same.
Conversations stored under bare QQ ids (see Addressing) use the outbox too
while their connector is pulling, and NapCat's HTTP API (`QQ_ONEBOT_URL`)
otherwise, as they always have.

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

The agent holds the request up to `wait_s` seconds (at most 30) until
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

`items` uses the same shape as `replies`. `reason` is `proactive`,
`follow_up` or `excuse`. `conversation_type` is `group` or `dm`.
`conversation_key` is the key the agent stores the conversation under
(`private:telegram:42` for a DM); `conversation_id` is the raw id the event
carried (the user id for a DM). The agent remembers `reply_handle`,
`connector_id` and `capabilities` from the latest admitted event in each
conversation, so a conversation becomes reachable once it has sent one.

Report each delivery on the next pull, in `acks`:

| `status` | Meaning |
|---|---|
| `sent` | every item went out |
| `partial` | the first `sent_items` items went out |
| `failed` | nothing went out |
| `expired` | not started within `expires_in_s` |
| `refused` | the conversation is no longer allowed on the connector's side |
| `unsupported` | the platform cannot send unprompted to this conversation |

Rules:

- **At most once.** A delivery is handed out once and never again, whatever
  happens to the ack; retrying an ambiguous send would duplicate a chat
  message. Keep the last few hundred `delivery_id`s and never send one twice.
- **In order.** Send one conversation's deliveries in the order received;
  different conversations may go in parallel.
- **Only what is acked counts.** The agent treats an unacked delivery as not
  sent, and remembers only what was acked as sent. It waits for the ack until
  your next pull, and at most `expires_in_s` plus 60 seconds after handing
  the delivery out, so finish sending a batch before you pull again.
- **Liveness.** A connector that has not pulled for 90 seconds is treated as
  gone: nothing is queued for its conversations until it pulls again, and
  what was queued for it or handed to it without an ack yet ends as not sent.
  Pull again as soon as a batch is delivered, which is also when its acks go.
- **`unsupported` sticks.** After that ack the agent stops queueing for the
  conversation until an event brings a different `reply_handle`.
- **Body kinds.** The signature does not cover the URL path, so the agent
  refuses an event body on the outbox endpoint and an `outbox.pull` body on the
  event endpoint (`400`, code `invalid_schema`). An event may say
  `"kind": "event"`; one with any other `kind` is refused.

A 404 without a `code` means the agent does not serve the outbox; `404` with
code `outbox_disabled` means the operator turned it off
(`CONNECTOR_OUTBOX_ENABLED`). Either way, pull again after a long pause.

## Speaking first without the outbox

A connector that cannot poll can still start a DM: post an ordinary DM event
with `"proactive": true`. Its text is read as a cue to the persona
("they have been quiet a day; their exam was this morning"), cut at 500
characters, and never stored as the person's words. If the persona decides to
speak, the reply comes back in the response. A group event with the flag is
claimed and dropped. The cue counts against the same DM cooldown as the
agent's own openers, and not as the person's activity.

## Capabilities and what degrades

| Missing | Effect |
|---|---|
| `outbox` | no scheduled openers, no follow-up question, no excuse for a failed model call in that conversation (QQ ids still get them through NapCat when `QQ_ONEBOT_URL` reaches it) |
| `quote_text` | a quoted message is understood only if the agent saw it itself |
| `reply_handle` | same as no `outbox` |
| `addressed` wrong | the persona treats addressed messages as background chatter |

## Writing a connector

1. Receive a message from the platform. Skip the bot's own messages and
   non-message events (joins, recalls, pokes).
2. Build the event above; set `addressed` from the platform's own mention and
   reply rules.
3. Sign and post it. Send `replies` in order; when `owned` is true, keep other
   bot logic quiet.
4. If the platform can send unprompted, add `connector_id`, `reply_handle` and
   `capabilities: ["outbox"]`, and run the pull loop: pull, deliver each
   delivery through `reply_handle`, ack on the next pull.

`integrations/sdk/personagent_connector.py` does steps 3 and 4.
