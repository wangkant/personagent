# astrbot_plugin_llm_persona_gateway

An [AstrBot](https://github.com/AstrBotDevs/AstrBot) plugin that puts
[personagent](https://github.com/wangkant/personagent) on every platform
AstrBot supports. It forwards each allowed message to the agent and sends the
agent's replies back.

## What it does

- Receives group and private messages from every AstrBot platform adapter
  (Telegram, Discord, Slack, QQ, ...), except the ones in `excluded_platforms`.
- Forwards messages from allowlisted groups and senders to the agent's
  `POST /webhook/gateway` as a platform-neutral event, reading each platform
  the way its adapter delivers it: who was addressed, what was quoted,
  stickers, images, voice notes and when the message was really sent.
- Sends the agent's replies (text and images, with a mention in group chats
  where the agent asks for one) back through AstrBot, written the way each
  platform expects.
- Delivers what the agent says unprompted (a scheduled opener, a follow-up
  question, the excuse when its model is down) by pulling its outbox. See
  [Outbox](#outbox).
- Stops AstrBot's own pipeline when the agent claims the conversation
  (`block_default`), so AstrBot's built-in model never answers in the
  persona's place.

The persona, memory, debounce and typing simulation all run in the agent. This
plugin is a connector in the sense of the agent's
[`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): it translates, and
decides nothing about what the persona says.

## Install

You need AstrBot, started at least once so its data directory exists, and a
personagent checkout (see its README).

### With the setup wizard

From the personagent checkout, run:

```bash
python quickstart.py
```

Answer yes to connecting AstrBot and give it AstrBot's data directory (the
folder holding `plugins/` and `config/`). The wizard copies this plugin,
generates a shared token and writes it to both sides, and asks which group and
sender IDs to allow.

To skip all the wizard's questions, including the API key and bot name (set
`LLM_API_KEY` and `BOT_NAME` in `.env` yourself):

```bash
python quickstart.py --astrbot <AstrBot data dir>        # add --qq to route QQ as well
```

The first run leaves the allowlists **empty**: add them in the plugin
settings. Run `python quickstart.py --help` for the flags that also switch on
a platform in AstrBot.

Running it again is safe. The allowlists, `private_enabled`, any `agent_url`
this plugin accepts (see [Where the agent can run](#where-the-agent-can-run)),
and other excluded platforms are kept; an `agent_url` it would refuse is
replaced with the loopback default. QQ routing changes only when you pass
`--qq` or `--no-qq`, and the agent's `GATEWAY_NATIVE_PLATFORMS` is kept in
step with it. The wizard's AstrBot step offers the current allowlists as
defaults, so Enter keeps them and `-` clears one.

Then restart AstrBot and start the agent (see [Check it works](#check-it-works)).

### By hand

1. Copy this folder to
   `<AstrBot data dir>/plugins/astrbot_plugin_llm_persona_gateway/`.
2. Restart AstrBot, or reload plugins in its WebUI. AstrBot installs
   `requirements.txt` (only `httpx`).
3. Open the plugin's settings in the WebUI. They are saved to
   `<AstrBot data dir>/config/astrbot_plugin_llm_persona_gateway_config.json`.
   - Add the group IDs the persona may join to `group_whitelist`.
   - For private chats, turn on `private_enabled` and add sender IDs to
     `private_whitelist`.
   - If the agent's `.env` sets `GATEWAY_TOKEN`, put the same value in
     `gateway_token`. It is required when the agent is not on the same host.
   - Leave `agent_url` at its default when the agent runs on the same host
     with the default `PORT=8080`.

The plugin is **default-deny**. With empty allowlists it forwards nothing, and
AstrBot behaves as if the plugin were not installed. Use IDs as AstrBot shows
them, without a platform prefix.

### Check it works

1. Start the agent from the personagent checkout: `.venv/bin/python main.py`
   (Windows: `.venv\Scripts\python.exe main.py`).
2. Say the bot's name (the agent's `BOT_NAME`) in an allowed group.

If nothing comes back, look for `llm_persona_gateway:` lines in AstrBot's log
and see [Troubleshooting](#troubleshooting).

## Configuration

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `agent_url` | string | `http://127.0.0.1:8080/webhook/gateway` | The agent's gateway endpoint. Must be loopback, or HTTPS with `gateway_token` set. |
| `gateway_token` | string | `""` | Shared secret. Must match the agent's `GATEWAY_TOKEN`. Required for any non-loopback `agent_url`. |
| `timeout_s` | int | `180` | Seconds to wait for each attempt. See [Timeouts](#timeouts). |
| `excluded_platforms` | list | `["aiocqhttp"]` | Adapter names never forwarded. Remove `aiocqhttp` to route QQ through this plugin. |
| `group_whitelist` | list | `[]` | Group IDs to forward. Empty forwards no groups. |
| `private_enabled` | bool | `false` | Forward private messages from senders in `private_whitelist`. |
| `private_whitelist` | list | `[]` | Sender IDs allowed in private chat. Empty allows none. |
| `block_default` | bool | `true` | Stop AstrBot's pipeline when the agent claims the conversation. |
| `forward_quoted_text` | bool | `true` | Send a quoted message's text and author along with its id, where the platform provides them. |
| `quote_max_chars` | int | `200` | Longest quoted text sent; longer quotes are cut. |
| `max_inline_image_bytes` | int | `4000000` | Largest image sent inline. Images the agent cannot fetch itself (Telegram, local files, private addresses) are inlined; a bigger one arrives as the note `(sent an image)`. Keep it under the agent's `MAX_IMAGE_BYTES`. |
| `outbox_enabled` | bool | `true` | Pull and deliver the agent's outbox. See [Outbox](#outbox). |
| `outbox_wait_s` | int | `25` | How long one outbox pull may wait at the agent (at most 30). |
| `forwarder_id` | string | `""` | This AstrBot's name to the agent. Empty generates one once and keeps it. Give two AstrBot hosts different names, never the same one. |

### Where the agent can run

- **Same host** (or a container sharing the host's network namespace, or
  using host networking): keep the default loopback `agent_url`.
- **Another container or host**: use an HTTPS `agent_url` and the same
  non-empty secret in `gateway_token` and the agent's `GATEWAY_TOKEN`. A
  private tunnel that ends at a loopback URL visible to AstrBot also works;
  still set the same token on both sides, because the agent refuses tokenless
  requests that arrive through a proxy.

Plain `http://` to anything but loopback, such as
`http://host.docker.internal:8080`, is refused even with a token. Each message
then logs `refusing unsafe agent_url` and AstrBot's own model answers instead.

The agent listens on `127.0.0.1:8080` by default. If you set its `HOST` to a
non-loopback address, it refuses to start unless both `GATEWAY_TOKEN` and
`WEBHOOK_SECRET` are set.

### Timeouts

Each request lasts as long as the agent's turn: a short debounce plus every
model call and retry, so a slow round-trip is normal. If `timeout_s` runs
out, the agent still finishes the turn and keeps its reply and what it
learned, but nobody sees that reply, and
AstrBot's own model answers the same message in a different voice.

Keep the agent's `LLM_TIMEOUT × (1 + LLM_MAX_RETRIES)` under `timeout_s`. With
the agent's defaults (`LLM_TIMEOUT=120`, `LLM_MAX_RETRIES=2`) a turn whose
model calls keep timing out can take over 360 s, so with a slow model raise
`timeout_s` or lower those two settings.

A 429 or 500 from the agent is retried up to twice, honouring `Retry-After`
on a 429, as long as the signed request is still fresh.

### `block_default` and ownership

The plugin stops AstrBot's pipeline when the agent says the conversation is
its own (`owned: true`), whether or not it replied. The agent often stays
quiet on purpose: it passes, merges several messages into one answer, or holds
back to keep a natural rhythm. Handing those turns to AstrBot's built-in model
would let someone else answer in a conversation the persona chose to sit out.

Transport errors, invalid responses and conversations the agent turns away go
on to AstrBot's normal pipeline. If the agent's response has no `owned` field,
the plugin uses `handled` instead.

## QQ through AstrBot

QQ goes through this plugin like any other platform, using AstrBot's
`aiocqhttp` adapter and a OneBot v11 implementation such as NapCat.

1. Remove `aiocqhttp` from `excluded_platforms` and add the QQ groups to
   `group_whitelist`.
2. In the agent's `.env`, set `GATEWAY_NATIVE_PLATFORMS=aiocqhttp` and
   `BOT_QQ` (the bot account's number).
3. Keep NapCat's HTTP API reachable at the agent's `NAPCAT_API` for the
   catch-up sweep for missed mentions. Proactive messages, the follow-up
   question after a rejection and the excuse when the model fails go through
   this plugin's [outbox](#outbox) while it is pulling, and through NapCat
   directly otherwise.
4. If NapCat also posts to the agent's `/webhook/qq`, turn that off. That
   route is deprecated since 0.3.0, and running both delivers every message
   twice.

`quickstart.py --astrbot <data dir> --qq` removes `aiocqhttp` from
`excluded_platforms` and sets `GATEWAY_NATIVE_PLATFORMS`; the wizard also asks
for `BOT_QQ`.

Do not skip `GATEWAY_NATIVE_PLATFORMS=aiocqhttp`. Without it the agent files QQ
chats under `aiocqhttp:`-prefixed ids. Its QQ-side actions then target groups
and people that do not exist, anything learned under the plain QQ ids no longer
matches, and the ledgers cannot be re-keyed afterwards. With it, a QQ message
relayed by AstrBot lands on the same ids NapCat would have produced.

Because QQ ids stay plain, the agent's own QQ settings still apply to them:
the QQ entries of `ALLOWED_GROUPS` (none means every QQ group), and private
chats only from an owner in `OWNER_IDS` or from `ALLOWED_DM_USERS`. The wizard
writes the QQ groups you give it to the agent's `.env`, so to add a QQ group
later, add it to both `group_whitelist` and `ALLOWED_GROUPS` (or list no QQ
groups there). The old names `QQ_GROUPS`, `OWNER_QQ` and `PRIVATE_ALLOWED_QQS`
still work.

Before AstrBot carries a busy QQ group, change two AstrBot settings. Both run
before plugin handlers:

- `platform_settings.rate_limit` defaults to 30 messages per 60 s and delays
  messages over the limit rather than dropping them. Raise or disable it.
- `content_safety.internal_keywords` is on by default and silently drops
  messages that match its keyword list, including ones the persona would have
  answered. Review it.

## Platforms

The agent speaks one neutral format; the plugin translates at the edges,
using each platform's own mechanisms. Checked against the adapters in
AstrBot 4.25.5; adapter internals change between versions, so every raw
field is read defensively and missing ones fall back to what AstrBot gives.

On every platform:

- Only something a person wrote is forwarded: QQ notices (pokes, recalls,
  joins) and requests, Slack joins and topic changes are not turns.
- Videos, files and voice messages arrive as a note the persona can react
  to: `(sent a video)`, `(sent a file: deck.pdf)`, `(sent a voice message)`,
  with the platform's transcript when it has one.
- Quoted messages carry their text and author where the platform provides
  them (`forward_quoted_text`).
- The message's time is the platform's own, not when AstrBot received it,
  wherever the adapter keeps it.
- Replies are split below the platform's length limit, never become a
  text-to-image picture, and name people the way the platform does.
- The outbox is used only where the platform can send unprompted.

| Platform (adapter) | What works | What the platform itself cannot do |
| --- | --- | --- |
| QQ via OneBot (`aiocqhttp`) | Groups and DMs. @ and reply-to-bot, also when the adapter could not look up the @. Face names, store stickers (`mface`) and sticker images marked as stickers. Mentions as a real QQ @, with one space. Long replies split under AstrBot's `forward_threshold`, so none turns into a merged-forward card. Outbox. | Markdown shows as typed. |
| QQ official (`qq_official`, `qq_official_webhook`) | Group messages that @ the bot, and DMs. Faces as `[表情:name]`. Replies ask for plain text instead of the adapter's markdown. | Groups deliver only messages that @ the bot, so the persona cannot follow a conversation. No quotes, no names (only openids), no mentions in replies. Replies only within 5 minutes of a message, so no outbox. |
| Telegram (`telegram`) | Groups, topics (`<chat>#<thread>`) and DMs. Reply-to-bot for any kind of message, and the adapter's `/@bot` wake prefix removed. Sticker emoji, with the image for static stickers. Images fetched through the adapter's bot, so the bot token never leaves AstrBot. Mentions of a username in a message become the person's numeric id once they have written. Replies mention by username, or by a `tg://user` link for someone without one, and show `*`, `_` and the like as typed. Outbox. | With BotFather's privacy mode on (the default), groups deliver only commands, @mentions and replies to the bot: turn it off for the persona to follow the conversation. Animated and video stickers cannot be looked at. |
| Discord (`discord`) | Channels and threads as groups, and DMs. A leading `@bot` (which the adapter strips), a ping of one of the bot's roles, and replies to the bot all address it. Quotes with their text. Stickers. Voice and video attachments as notes. Mentions as `<@id>`, `@everyone` and `@here` kept inert, 2000-character split. Outbox, DMs included. | Needs the Message Content intent. |
| Slack (`slack`) | Channels and DMs. A thread reply under the bot's message addresses it. Links unfolded. Message ids are Slack's `ts`. Mentions as `<@id>`; `&`, `<` and `>` escaped so text cannot ping a channel. 3000-character split. Outbox. | A thread reply carries no parent text. No typing indicator for bots. Answers land in the channel, not the thread (adapter). |
| KOOK (`kook`) | Channels and DMs. @ (and pings of a role the bot holds). Quotes when KOOK includes them. `(emj)` emoji, real send time. Mentions inline in the text; `(met)`-style tags in the persona's text kept inert. Images sent through a file, since the adapter uploads only JPEG base64. Outbox. | Plain image, file, voice and video messages (not cards) are dropped by AstrBot's adapter before any plugin sees them. No typing indicator. |
| Lark / Feishu (`lark`) | Groups and DMs. @, and replies to the bot (Lark names the app as the sender). Quotes with their text. Stickers as an emoji. Outbox. | Without the "read all group messages" scope only @-messages arrive. Every reply quotes the message it answers, and markdown renders (adapter). Names are id prefixes. |
| DingTalk (`dingtalk`) | Groups and DMs. Images, which the adapter hands over as local files, inlined; videos as a note. Outbox; DMs reach people who have written to the bot. | Groups deliver only messages that @ the bot. No quotes, no mentions or quote-replies in replies. Every reply is markdown titled "AstrBot" (adapter). |
| LINE (`line`) | Groups, rooms and DMs. @ the bot. Quote ids. Sticker keywords. A turn's bubbles sent in one call, five at a time, so the free reply token covers them. Outbox (counts against the push quota). | LINE sends no quoted text. No mentions in replies (adapter). Images out need a public HTTPS `callback_api_base`. Names are id prefixes. |
| Mattermost (`mattermost`) | Channels and DMs. @ the bot. Thread root as the quote. Images inlined. Mentions by username once the person has written. `@channel`, `@all` and `@here` kept inert, 4000-character split. Outbox. | Quoted text would need a lookup the plugin does not make. No typing indicator. |
| Misskey (`misskey`) | Chat DMs and rooms, with `@bot` anywhere in a room message. Mentions as `@user@host` once the person has written; other `@` in the persona's text kept inert. 3000-character split. Outbox (chat and rooms). | Notes (public posts) are not forwarded: AstrBot types them as system events, and a reply would be public. `unique_session` breaks rooms (adapter). |
| Satori (`satori`) | Whatever the Satori backend bridges: groups, DMs, @, replies to the bot, quotes with text. Millisecond timestamps read as seconds. Outbox. | The group id is the guild, so a guild's channels share one conversation. Limits of the bridged platform apply. |
| WebChat (`webchat`) | The dashboard chat, as DMs. Quotes, images. Outbox (shown live or saved to the conversation). | One-to-one only. |
| WeCom app (`wecom`) | DMs, images, voice with its transcript. Customer-service mode forwards only the customer's messages, with the real send time. Replies split by bytes. Outbox in app mode, once someone has written since AstrBot started. | DMs only, no quotes. Customer-service mode cannot send unprompted. Markdown shows as typed. |
| WeCom smart bot (`wecom_ai_bot`) | Groups (which WeCom delivers only when the bot is @-ed) and DMs. Voice, file and video notes. A turn sent as one streamed answer. | Replies only inside the answer to a message: no outbox, no mentions. The answer renders as markdown. Set `wecom_ai_bot_name` in AstrBot so "@bot" is removed from the text. |
| WeChat official account (`weixin_official_account`) | DMs, voice with its transcript. A turn sent as one message. | Passive mode delivers one reply per message the user sends, within WeChat's 5 s window; the rest waits for their next message, and a turn the persona sits out leaves them waiting (adapter). Images only in active mode. No outbox. |
| Personal WeChat (`weixin_oc`) | DMs. Quotes with their text. Images inlined. Voice with its transcript. Typing indicator. Outbox. | No groups. After a re-login nobody is reachable until they write again. |
| Any other adapter | Forwarded as AstrBot delivers it; mentions as an At. | No outbox claimed. |

## Outbox

Some messages are not an answer to anything: a scheduled opener, the
follow-up question after a rejection, the excuse when the model is down.
The agent queues those, and this plugin pulls them from
`POST <agent_url>/outbox` (with the same signing as events), so the agent
never has to reach AstrBot. It is on by default (`outbox_enabled`).

- A delivery goes out through the conversation's own AstrBot session,
  in order, each message at most once.
- The allowlists and `excluded_platforms` are checked again at send time;
  a conversation removed since is refused.
- Platforms that cannot speak first (see the table) never get one: the
  plugin does not declare the outbox for their conversations.
- An agent without the outbox answers 404; the plugin asks again every ten
  minutes and otherwise behaves exactly as before.

The agent knows this AstrBot by `forwarder_id`, which the plugin generates
once and keeps. Two AstrBot hosts talking to one agent need different ones.

## Request authentication

When `gateway_token` is set, every request carries four headers:

- `X-Gateway-Token`: the token.
- `X-Gateway-Timestamp`: unix seconds.
- `X-Gateway-Nonce`: a fresh random value.
- `X-Gateway-Signature`: `sha256=` followed by the hex
  HMAC-SHA256, keyed with the token, of `timestamp + "." + nonce + "." + body`.

The body is canonical JSON: UTF-8, keys sorted, compact separators, non-ASCII
characters unescaped. The signature covers those exact bytes, so a proxy must
not rewrite the body. The agent rejects a bad signature, a reused nonce, or a
timestamp more than five minutes from its own clock, so keep the two clocks in
sync.

The body also carries the adapter's own `source_timestamp`. The agent checks
it separately against `GATEWAY_SOURCE_MAX_AGE_SECONDS` (default 24 hours), so
an old event re-sent with a fresh signature is still rejected. A message whose
adapter gives no valid timestamp is not forwarded; AstrBot handles it as usual.

## Identities on the agent side

The agent prefixes every gateway id with its platform, as `<platform>:<raw id>`
(for example `telegram:12345`), so ids from different platforms never collide.
Platforms listed in `GATEWAY_NATIVE_PLATFORMS` keep plain ids. The agent's
`OWNER_IDS`, `ALLOWED_GROUPS` and `ALLOWED_DM_USERS` take ids in the same form:
`OWNER_IDS=telegram:12345` makes that account the owner on Telegram, in groups
and DMs. A platform with entries in `ALLOWED_GROUPS` or `ALLOWED_DM_USERS` is
gated by the agent as well as by this plugin's allowlists.

## Troubleshooting

Messages in AstrBot's log start with `llm_persona_gateway:`.

| Log message | What to do |
| --- | --- |
| `refusing unsafe agent_url` | `agent_url` is plain HTTP to another host, or HTTPS without `gateway_token`. See [Where the agent can run](#where-the-agent-can-run). |
| `agent refused the request (403): invalid, stale, or replayed gateway envelope` | `gateway_token` is empty or does not match the agent's `GATEWAY_TOKEN`, the two clocks differ by more than five minutes, or a proxy changed the body. If the agent's log says `gateway replay guard full`, wait for it to drain. |
| `agent refused the request (403): stale gateway source event` | The message is older than the agent's `GATEWAY_SOURCE_MAX_AGE_SECONDS`, usually after AstrBot delivered a backlog. |
| `agent refused the request (403): authentication required` or `... only local requests accepted` | The agent has no `GATEWAY_TOKEN` and the request is not local. Set the same token on both sides. |
| `agent at capacity (429)` | The agent is already running `MAX_INFLIGHT_GATEWAY` turns and turned the message away after retries, so AstrBot's own model answers it. Raise `MAX_INFLIGHT_GATEWAY` if this is frequent. |
| `agent rejected the body as too large (413)` | Usually a large inline image. Raise the agent's `MAX_WEBHOOK_BODY_BYTES`. |
| `agent rejected the event schema (400)` | The event had no message id or sender id (some adapters omit them), or this plugin has a bug. Please report it with the log line. |
| `timed out waiting for the agent` | See [Timeouts](#timeouts). |
| `dropping event without a valid authoritative source timestamp` | The adapter gave no timestamp. AstrBot handles that message itself. |
| `agent request failed: ...` or `agent request failed (<status>)` | Usually the agent is not running or `agent_url` is wrong (a 404 means a wrong path). A 500 means the agent failed; check its log. |
| `outbox off: ...` | The outbox follows the same `agent_url` rule as events; see the first row. |
| `outbox: agent has no outbox (older version); retrying in 10 minutes` | Expected with an agent that predates the outbox. Nothing else changes. |
| `outbox: outbox pull refused (403)` or `outbox pull failed: ...` | As for events: the token, the clocks, or the agent not running. The plugin backs off up to a minute between tries. |
| `outbox: no running platform '<id>'` | A delivery for an adapter that is disabled or was renamed in AstrBot. It is reported to the agent as failed. |
| `could not store forwarder_id` | AstrBot's plugin store failed. Set `forwarder_id` yourself, or the agent sees a new AstrBot after every restart. |

If the agent's own log says the forwarder sends `X-Gateway-Token` but
`GATEWAY_TOKEN` is blank, the token is being ignored. Set the same value in
the agent's `.env`.

Since 0.5.0 the message's time is the platform's own on QQ, Telegram,
Discord, KOOK, QQ official and Misskey, not when AstrBot received it. A
backlog AstrBot delivers after being down longer than the agent's
`GATEWAY_SOURCE_MAX_AGE_SECONDS` is therefore refused as stale, as it
should be.

## Known limitation: Telegram mentions

AstrBot's Telegram adapter identifies a sender by numeric user id
(`telegram:<numeric id>`), but an `@username` mention in a message only by
username. The plugin rewrites a mentioned username to the numeric id of the
person who uses it, once that person has written since AstrBot started;
until then the mention reaches the agent under the username.

Replies mention someone by username, or with a `tg://user` link when they
have none. Someone the plugin has not seen since AstrBot started is not
mentioned at all, rather than as the inert text `@123456`.
