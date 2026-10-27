# astrbot_plugin_personagent

This [AstrBot](https://github.com/AstrBotDevs/AstrBot) plugin connects AstrBot
to [personagent](https://github.com/wangkant/personagent). It forwards each
allowed message to the agent and sends the agent's replies back to the chat.
A Chinese version of this page is [README.zh-CN.md](README.zh-CN.md).

## Do you need it?

You do not need it for QQ, WeChat, Telegram or Discord. personagent connects
those itself, without AstrBot. Run `personagent` to open its local page and
add them under **Connect apps**.

You need this plugin when AstrBot carries the conversation. That happens in
two cases.

- **You add another platform on personagent's page.** KOOK, Feishu/Lark,
  DingTalk, Slack, WeCom AI bot, Mattermost, Misskey and the platforms under
  Advanced all run through AstrBot. The page downloads and runs an AstrBot for
  you and installs this plugin in it, so you have nothing to do here.
- **You already run an AstrBot** with its own platforms and plugins. Install
  the plugin as described below.

## What it does

- Receives group messages and DMs from every AstrBot platform adapter
  (Telegram, Discord, Slack, QQ, ...), except those in `excluded_platforms`.
- Forwards messages from allowlisted groups and senders to the agent's
  `POST /v1/events` as a platform-neutral event. It reads each platform the
  way its adapter delivers it, including who was addressed, what was quoted,
  stickers, images, voice notes and the time the platform says it was sent.
- Sends the agent's replies back through AstrBot in the form each platform
  expects. Replies can carry text and images, and in group chats a mention
  when the agent asks for one.
- Pulls the agent's outbox to deliver what it says unprompted, such as a
  scheduled opener, a follow-up question, or the excuse it posts in a group
  when its model is down. See [Outbox](#outbox).
- Stops AstrBot's own pipeline when the agent claims the conversation
  (`block_default`), so AstrBot's built-in model never answers in the
  persona's place.

The persona, memory, debounce and typing simulation all run in the agent.
This plugin is a connector as defined in the agent's
[`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.md).

## Install into your own AstrBot

You need AstrBot, started at least once so that its data directory exists,
and personagent (`python -m pip install personagent`; see its README).

### With personagent's setup

```bash
personagent connect astrbot
```

The command first looks for AstrBot's data directory, the folder that holds
`cmd_config.json`, `plugins/` and `config/`. If it finds none, it offers to
download AstrBot. It then asks whether AstrBot runs in Docker, which chat app
the bot joins (with that app's token where AstrBot still needs one), the
groups, the admin and the people allowed to DM the bot. For QQ through NapCat
it also asks for the bot account's number. Finally it copies this plugin,
generates a shared token, writes it to both sides and writes the allowlists.
`personagent init --terminal` offers the same step at the end.

To skip the questions, pass the data directory:

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

Run this way, a first connection leaves the allowlists **empty**, and you
fill them in the plugin settings. `personagent connect astrbot --help` lists
the flags that also switch on a platform in AstrBot.

You can run the command again at any time. It keeps the allowlists, other
excluded platforms, and any `personagent_url` this plugin accepts (see
[Where the agent can run](#where-the-agent-can-run)). A `personagent_url` the
plugin would refuse is replaced with the loopback default. QQ routing changes
only when you pass `--qq` or `--no-qq`, and the agent's
`CONNECTOR_QQ_PLATFORMS` follows it. When asked, the current allowlists are
the defaults: press Enter to keep one, or type `-` to clear it.

Then restart AstrBot and start the agent (see [Check it works](#check-it-works)).

### From AstrBot's WebUI

1. Download `astrbot_plugin_personagent.zip` from the
   [latest personagent release](https://github.com/wangkant/personagent/releases/latest).
2. Upload it under **Install from File** on AstrBot's plugin page.
3. Set `connector_token` to the `CONNECTOR_TOKEN` in personagent's `.env`, and
   fill the allowlists as described below.
4. If AstrBot runs on a different computer from personagent, set
   `personagent_url` to an HTTPS address (see
   [Where the agent can run](#where-the-agent-can-run)).

To update, upload the newer release's zip the same way. AstrBot 4.29 and
later replace the installed copy. On older versions, uninstall the plugin
first and leave **Also delete plugin configuration file** unticked.

### By hand

1. Copy this folder to
   `<AstrBot data dir>/plugins/astrbot_plugin_personagent/`.
2. Restart AstrBot, or reload plugins in its WebUI. AstrBot installs
   `requirements.txt`, which lists only `httpx`.
3. Open the plugin's settings in the WebUI. They are saved to
   `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json`.
   - Add the group IDs the persona may join to `groups`.
   - Add the sender IDs whose DMs it may answer to `dm_users`.
   - If the agent's `.env` sets `CONNECTOR_TOKEN`, put the same value in
     `connector_token`. It is required when the agent is on another host.
   - Leave `personagent_url` at its default when the agent runs on the same
     host with the default `SERVER_PORT=8080`.

The plugin is **default-deny**. With empty allowlists it forwards nothing,
and AstrBot behaves as if the plugin were not installed. Write IDs the way
AstrBot shows them; send `/sid` in a chat to see them. A bare ID matches on
every adapter. `qq_official:ID` matches on that adapter only, and
`qq_official:*` forwards every conversation of that kind on it.

A bare `*` in `groups` or `dm_users` forwards every conversation of that kind
on every adapter and marks it `prefiltered: false`. The agent's own
`ACCESS_GROUPS` and `ACCESS_DM_USERS` then decide alone. The agent refuses a
platform with no entries there, except QQ groups, which it answers unless
`ACCESS_GROUPS` lists some.

### Check it works

1. Start the agent with `personagent run`, which starts the server alone. Its
   banner should show `agent: on`.
2. Say the bot's name (the agent's `PERSONA_NAME`) in an allowed group.

If no reply arrives, look for `personagent:` lines in AstrBot's log, then
read what `personagent run` printed after its banner, and see
[Troubleshooting](#troubleshooting).

## Configuration

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | The agent's base URL. The plugin appends `/v1/events` and `/v1/outbox`. Must be loopback, or HTTPS with `connector_token` set. |
| `connector_token` | string | `""` | Shared secret. Must match the agent's `CONNECTOR_TOKEN`. Required for any non-loopback `personagent_url`. |
| `timeout_s` | int | `420` | Seconds to wait for each attempt. See [Timeouts](#timeouts). |
| `excluded_platforms` | list | `["aiocqhttp"]` | Adapter names that are never forwarded. Remove `aiocqhttp` to route QQ (NapCat) through this plugin. See [QQ through NapCat](#qq-through-napcat). |
| `groups` | list | `[]` | Group IDs to forward. Empty forwards no groups. `adapter:ID` or `adapter:*` limits an entry to one adapter. A bare `*` forwards all groups unfiltered. |
| `dm_users` | list | `[]` | Sender IDs whose DMs are forwarded. Empty forwards no DMs. `adapter:ID` or `adapter:*` limits an entry to one adapter. A bare `*` forwards all DMs unfiltered. |
| `block_default` | bool | `true` | Stop AstrBot's pipeline when the agent claims the conversation. |
| `forward_quoted_text` | bool | `true` | Send a quoted message's text and author along with its id, where the platform provides them. While this is on and `quote_max_chars` is above 0, every event declares the `quote_text` capability. |
| `quote_max_chars` | int | `200` | Longest quoted text sent. Longer quotes are cut. |
| `max_inline_image_bytes` | int | `4000000` | Largest image sent inline. Images the agent cannot fetch itself (Telegram, local files, private addresses) are inlined. A larger one arrives as the note `(sent an image)`. Keep it under the agent's `VISION_MAX_IMAGE_BYTES`. |
| `outbox_enabled` | bool | `true` | Pull and deliver the agent's outbox. See [Outbox](#outbox). |
| `outbox_wait_s` | int | `25` | How long one outbox pull may wait at the agent, at most 30. |
| `connector_id` | string | `""` | This AstrBot's name to the agent. Empty generates one once and keeps it. Two AstrBot hosts need different names. |

### Where the agent can run

- **Same host**, or a container that shares the host's network namespace or
  uses host networking: keep the default loopback `personagent_url`.
- **Another container or host**: use an HTTPS `personagent_url`, and set the
  same non-empty secret in `connector_token` and the agent's
  `CONNECTOR_TOKEN`. A private tunnel that ends at a loopback URL visible to
  AstrBot also works. Set the same token on both sides in that case too,
  because the agent refuses tokenless requests that arrive through a proxy.

The plugin refuses plain `http://` to anything other than loopback, such as
`http://host.docker.internal:8080`, even with a token. Each message then logs
`refusing unsafe personagent_url`, and AstrBot's own model answers instead.

**AstrBot in Docker.** Inside a container, `127.0.0.1` is the container
itself, so the default `personagent_url` reaches nothing. You have two
options:

- Give AstrBot host networking: `network_mode: host` in its compose file, or
  `docker run --network host`. Docker Desktop needs version 4.34 or later
  with host networking enabled. A NapCat container in the same compose file
  needs host networking too.
- Put the agent behind HTTPS and set that address as `personagent_url`
  (`personagent connect astrbot <dir> --url https://...`).

The agent listens on `127.0.0.1:8080` by default. If you set its
`SERVER_HOST` to a non-loopback address, it refuses to start unless
`CONNECTOR_TOKEN` is set. Set the token before you put a proxy or tunnel in
front of the agent, even on a single host.

### Timeouts

Each request lasts as long as the agent's turn, which is a short debounce
plus every model call and retry. If `timeout_s` runs out, the agent still
finishes the turn and keeps what it learned, but the reply is lost and
AstrBot's own model answers the message instead.

Keep the agent's `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` below `timeout_s`.
With the agent's defaults (`LLM_TIMEOUT_S=120`, `LLM_MAX_RETRIES=2`), a turn
whose model calls keep timing out can take over 360 s, which the default
`timeout_s` of 420 covers. If you raise either setting on the agent, raise
`timeout_s` as well.

The plugin retries a 429 or 500 from the agent up to twice, honouring
`Retry-After` on a 429, as long as the signed request is still fresh.

### `block_default` and ownership

The plugin stops AstrBot's pipeline whenever the agent reports that the
conversation is its own (`owned: true`), whether or not it replied, so
AstrBot's built-in model stays out of turns the persona sits out.

Transport errors, invalid responses and conversations the agent turns away
continue to AstrBot's normal pipeline. If the agent's response has no
`owned` field, the plugin uses `handled` instead.

## QQ through NapCat

personagent connects QQ official bots itself, without AstrBot. This section
covers only a QQ account run through NapCat (or another OneBot v11
implementation) behind AstrBot's `aiocqhttp` adapter. When you add OneBot v11
on personagent's own page, it removes `aiocqhttp` from `excluded_platforms`
and sets `CONNECTOR_QQ_PLATFORMS` for you.

1. Remove `aiocqhttp` from `excluded_platforms` and add the QQ groups to
   `groups`.
2. In the agent's `.env`, set `CONNECTOR_QQ_PLATFORMS=aiocqhttp` and
   `QQ_BOT_ID` (the bot account's number).
3. Optional: set the agent's `QQ_ONEBOT_URL` to NapCat's HTTP server. This
   enables the catch-up sweep for missed mentions, which also needs
   `QQ_BOT_ID`. Proactive messages, the follow-up question after a rejection
   and a group's excuse when the model fails go through this plugin's
   [outbox](#outbox) while it is pulling. Otherwise they go through NapCat
   directly, provided that URL is set.
4. If NapCat also posts to the agent's `/v1/onebot`, turn that off. The route
   is deprecated, and running both delivers every message twice.

`personagent connect astrbot <data dir> --qq` removes `aiocqhttp` from
`excluded_platforms` and sets `CONNECTOR_QQ_PLATFORMS`. Run without a folder,
it also asks for `QQ_BOT_ID`. A short section in Chinese covers this route:
[docs/deploy.zh-CN.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md#第三方路线astrbot--napcat).

Do not skip `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Without it the agent files QQ
chats under `aiocqhttp:`-prefixed ids, anything learned under the plain QQ
ids no longer matches, and the ledgers cannot be re-keyed afterwards.

Because QQ ids stay plain, the agent's own QQ settings still apply to them.
The QQ entries of `ACCESS_GROUPS` gate groups (no entries means every QQ
group), and DMs are answered only from the admin in `ADMIN_IDS` or from
`ACCESS_DM_USERS`. The wizard writes the QQ groups you give it to the agent's
`.env`. To add a QQ group later, add it to both `groups` and `ACCESS_GROUPS`,
or list no QQ groups in `ACCESS_GROUPS`.

Before AstrBot carries a busy QQ group, review two AstrBot settings. Both run
before plugin handlers.

- `platform_settings.rate_limit` defaults to 30 messages per 60 s. Messages
  over the limit are delayed, not dropped. Raise or disable the limit.
- `content_safety.internal_keywords` is on by default and drops
  messages that match its keyword list, including ones the persona would have
  answered. Review the list.

## Platforms

The agent speaks one neutral format, and the plugin translates at the edges
using each platform's own mechanisms. The table below was checked against the
adapters in AstrBot 4.25.5.

On every platform:

- Only messages a person wrote are forwarded. QQ notices (pokes, recalls,
  joins) and requests, and Slack joins and topic changes, are not turns.
- Videos, files and voice messages arrive as a note the persona can react
  to, such as `(sent a video)`, `(sent a file: deck.pdf)` or
  `(sent a voice message)`, with the platform's transcript when it has one.
- Quoted messages carry their text and author where the platform provides
  them (`forward_quoted_text`).
- Wherever the adapter keeps it, the message's time is the platform's own
  rather than the time AstrBot received it.
- Replies are split below the platform's length limit, with the mention and
  escapes counted the way the platform counts them. They never become a
  text-to-image picture, and they name people the way the platform does.
- The outbox is used only where the platform can send unprompted.

| Platform (adapter) | What works | What the platform itself cannot do |
| --- | --- | --- |
| QQ via OneBot (`aiocqhttp`) | Groups and DMs. @ and reply-to-bot, also when the adapter could not look up the @. Face names, store stickers (`mface`) and sticker images marked as stickers. Mentions as a real QQ @, followed by one space. Long replies split under AstrBot's `forward_threshold`, so none turns into a merged-forward card. Outbox. | Markdown shows as typed. |
| QQ official (`qq_official`, `qq_official_webhook`) | Group messages that @ the bot, and DMs. Faces as `[表情:name]`. Replies request plain text instead of the adapter's markdown. | Groups deliver only messages that @ the bot, so the persona cannot follow a conversation. No quotes, no names (only openids), no mentions in replies. Replies are possible only within 5 minutes of a message, so there is no outbox. |
| Telegram (`telegram`) | Groups, topics (`<chat>#<thread>`) and DMs. Reply-to-bot for any kind of message, with the adapter's `/@bot` wake prefix removed. Sticker emoji, plus the image for static stickers. Images fetched through the adapter's bot, so the bot token never leaves AstrBot. A mentioned username becomes the person's numeric id once they have written. Replies mention by username, or by a `tg://user` link for someone without one, and show `*`, `_` and similar characters as typed. Outbox. | With BotFather's privacy mode on (the default), groups deliver only commands, @mentions and replies to the bot. Turn it off so the persona can follow the conversation. Animated and video stickers cannot be viewed. |
| Discord (`discord`) | Channels and threads as groups, and DMs. A leading `@bot` (which the adapter strips), a ping of one of the bot's roles, and replies to the bot all address it. Quotes with their text. Stickers. Voice and video attachments as notes. Mentions as `<@id>`, with `@everyone` and `@here` kept inert. Replies split at 2000 characters. Outbox, DMs included. | Needs the Message Content intent. |
| Slack (`slack`) | Channels and DMs. A thread reply under the bot's message addresses it. Links unfolded. Message ids are Slack's `ts`. Mentions as `<@id>`. `&`, `<` and `>` escaped so text cannot ping a channel. Replies split at 3000 characters. Outbox. | A thread reply carries no parent text. No typing indicator for bots. Answers land in the channel, not the thread (adapter). |
| KOOK (`kook`) | Channels and DMs. @, and pings of a role the bot holds. Quotes when KOOK includes them. `(emj)` emoji and the real send time. Mentions inline in the text, with `(met)`-style tags in the persona's text kept inert. Images sent as a file, since the adapter uploads only JPEG base64. Outbox. | AstrBot's adapter drops plain image, file, voice and video messages (not cards) before any plugin sees them. No typing indicator. |
| Lark / Feishu (`lark`) | Groups and DMs. @, and replies to the bot (Lark names the app as the sender). Quotes with their text. Stickers as an emoji. Outbox. | Without the "read all group messages" scope, only @-messages arrive. Every reply quotes the message it answers, and markdown renders (adapter). Names are id prefixes. |
| DingTalk (`dingtalk`) | Groups and DMs. Images, which the adapter hands over as local files, are inlined. Videos as a note. Outbox. DMs reach people who have written to the bot. | Groups deliver only messages that @ the bot. No quotes, and no mentions or quote-replies in replies. Every reply is markdown titled "AstrBot" (adapter). |
| LINE (`line`) | Groups, rooms and DMs. @ the bot. Quote ids. Sticker keywords. A turn's bubbles sent in one call, five at a time, so the free reply token covers them. Outbox, which counts against the push quota. | LINE sends no quoted text. No mentions in replies (adapter). Outgoing images need a public HTTPS `callback_api_base`. Names are id prefixes. |
| Mattermost (`mattermost`) | Channels and DMs. @ the bot. Thread root as the quote. Images inlined. Mentions by username once the person has written. `@channel`, `@all` and `@here` kept inert. Replies split at 4000 characters. Outbox. | Quoted text would need a lookup the plugin does not make. No typing indicator. |
| Misskey (`misskey`) | Chat DMs and rooms, with `@bot` anywhere in a room message. Mentions as `@user@host` once the person has written, with any other `@` in the persona's text kept inert. Replies split at 3000 characters. Outbox for chat and rooms. | Notes (public posts) are not forwarded, because AstrBot types them as system events and a reply would be public. `unique_session` breaks rooms (adapter). |
| Satori (`satori`) | Whatever the Satori backend bridges: groups, DMs, @, replies to the bot, quotes with text. Millisecond timestamps read as seconds. Outbox. | The group id is the guild, so a guild's channels share one conversation. Limits of the bridged platform apply. |
| WebChat (`webchat`) | The dashboard chat, as DMs. Quotes and images. Outbox, shown live or saved to the conversation. | One-to-one only. |
| WeCom app (`wecom`) | DMs, images, and voice with its transcript. Customer-service mode forwards only the customer's messages, with the real send time. Replies split by bytes. Outbox in app mode, once someone has written since AstrBot started. | DMs only, no quotes. Customer-service mode cannot send unprompted. Markdown shows as typed. |
| WeCom AI bot (`wecom_ai_bot`) | Groups (WeCom delivers a group message only when the bot is @-ed) and DMs. Voice, file and video notes. A turn sent as one streamed answer. | Replies only inside the answer to a message, so no outbox and no mentions. The answer renders as markdown. Set `wecom_ai_bot_name` in AstrBot so that "@bot" is removed from the text. |
| WeChat official account (`weixin_official_account`) | DMs, and voice with its transcript. A turn sent as one message. | Passive mode delivers one reply per user message, within WeChat's 5 s window. The rest waits for the user's next message, and a turn the persona sits out leaves the user waiting (adapter). Images only in active mode. No outbox. |
| Personal WeChat (`weixin_oc`) | DMs. Quotes with their text. Images inlined. Voice with its transcript. Typing indicator. Outbox. | No groups. After a re-login nobody is reachable until they write again. |
| Any other adapter | Forwarded as AstrBot delivers it. Mentions as an At. | No outbox claimed. |

## Outbox

Some messages answer nothing: a scheduled opener, the follow-up question
after a rejection, or the excuse in a group when the model is down. (A DM's
excuse comes back in the event's own response.) The agent queues these
messages, and this plugin pulls them from `POST <personagent_url>/v1/outbox`
with the same signing as events, so the agent never has to reach AstrBot.
The outbox is on by default (`outbox_enabled`).

- Each delivery goes out through the conversation's own AstrBot session, in
  order, and each message is sent at most once.
- A delivery goes only to a session the plugin itself took from a message in
  that same conversation. These sessions are kept in AstrBot's plugin store,
  so they survive a reload. Nothing else that posts an event to the agent can
  point the outbox at another chat, and the plugin refuses such a delivery.
- The plugin checks the allowlists and `excluded_platforms` again at send
  time and refuses a conversation that has since been removed.
- Platforms that cannot speak first (see the table) never receive outbox
  messages, because the plugin does not declare the outbox for their
  conversations.
- An agent without the outbox answers 404. The plugin asks again every ten
  minutes.

The agent knows this AstrBot by `connector_id`, which the plugin generates
once and keeps. Two AstrBot hosts talking to one agent need different ids.

## Request authentication

When `connector_token` is set, every request carries four headers:

- `X-Personagent-Token`: the token.
- `X-Personagent-Timestamp`: unix seconds.
- `X-Personagent-Nonce`: a fresh random value.
- `X-Personagent-Signature`: `sha256=` followed by the hex HMAC-SHA256,
  keyed with the token, of `timestamp + "." + nonce + "." + body`.

The body is canonical JSON: UTF-8, keys sorted, compact separators, and
non-ASCII characters unescaped. The signature covers those exact bytes, so a
proxy must not rewrite the body. The agent rejects a bad signature, a reused
nonce, or a timestamp more than five minutes from its own clock. Keep the two
clocks in sync.

The body also carries the adapter's own time for the message as `sent_at`.
The agent checks it separately against `CONNECTOR_MAX_EVENT_AGE_S` (default
24 hours), so an old event re-sent with a fresh signature is still rejected.
The plugin does not forward a message whose adapter gives no valid
timestamp, and AstrBot handles that message as usual.

## Identities on the agent side

The agent prefixes every forwarded id with its platform, as
`<platform>:<raw id>` (for example `telegram:12345`), so ids from different
platforms never collide. Platforms listed in `CONNECTOR_QQ_PLATFORMS` keep
plain ids. The agent's `ADMIN_IDS`, `ACCESS_GROUPS` and `ACCESS_DM_USERS`
take ids in the same form. For example, `ADMIN_IDS=telegram:12345` makes that
account the admin on Telegram, in groups and DMs. A platform with entries in
`ACCESS_GROUPS` or `ACCESS_DM_USERS` is gated by the agent as well as by this
plugin's allowlists.

## Troubleshooting

The plugin's lines in AstrBot's log start with `personagent:`.

| Log message | What to do |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` is plain HTTP to another host, or HTTPS without `connector_token`. See [Where the agent can run](#where-the-agent-can-run). |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` is empty or does not match the agent's `CONNECTOR_TOKEN`, the two clocks differ by more than five minutes, or a proxy changed the body. If the agent's log says `connector replay guard full`, wait for it to drain. |
| `agent refused the request (403): stale or invalid sent_at` | The message is older than the agent's `CONNECTOR_MAX_EVENT_AGE_S`. This usually happens after AstrBot delivers a backlog. |
| `agent refused the request (403): authentication required` or `... only local requests accepted` | The agent has no `CONNECTOR_TOKEN` and the request is not local. Set the same token on both sides. |
| `agent at capacity (429)` | The agent was already running `CONNECTOR_MAX_INFLIGHT` turns and still turned the message away after retries, so AstrBot's own model answered it. Raise `CONNECTOR_MAX_INFLIGHT` if this happens often. |
| `agent rejected the body as too large (413)` | Usually a large inline image. Raise the agent's `SERVER_MAX_BODY_BYTES`. |
| `agent rejected the event schema (400)` | The event had no message id or sender id (some adapters omit them), or this plugin has a bug. Please report it with the log line. |
| `timed out waiting for the agent` | See [Timeouts](#timeouts). |
| `dropping event without a valid time the platform sent it` | The adapter gave no timestamp. AstrBot handles that message itself. |
| `agent request failed: ...` or `agent request failed (<status>)` | Usually the agent is not running or `personagent_url` is wrong. A 404 means a wrong path: `personagent_url` is the base URL, without `/v1/events`. A 500 means the agent failed, so check its log. |
| `outbox off: ...` | The outbox follows the same `personagent_url` rule as events. See the first row. |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | The agent's `CONNECTOR_OUTBOX_ENABLED` is off. |
| `outbox: outbox pull refused (403)` or `outbox pull failed: ...` | Same causes as for events: the token, the clocks, or the agent not running. The plugin backs off up to a minute between tries. |
| `outbox: no running platform '<id>'` | A delivery for an adapter that is disabled or was renamed in AstrBot. The plugin reports it to the agent as failed. |
| `could not store connector_id` | AstrBot's plugin store failed. Set `connector_id` yourself, or the agent sees a new AstrBot after every restart. |

If the agent's own log says the connector sends `X-Personagent-Token` but
`CONNECTOR_TOKEN` is blank, the agent is ignoring the token. Set the same
value in the agent's `.env`.

On QQ, Telegram, Discord, KOOK, QQ official and Misskey, the message's time
is the platform's own, not the time AstrBot received it. When AstrBot has been
down longer than the agent's `CONNECTOR_MAX_EVENT_AGE_S`, the agent refuses
the backlog AstrBot delivers as stale.

## Known limitation: Telegram mentions

AstrBot's Telegram adapter identifies a sender by numeric user id
(`telegram:<numeric id>`), but identifies an `@username` mention in a message
only by username. The plugin rewrites a mentioned username to the numeric id
of the person who uses it once that person has written since AstrBot started.
Until then, the mention reaches the agent under the username.

Replies mention someone by username, or with a `tg://user` link when they
have none. The plugin does not mention someone it has not seen since AstrBot
started.
