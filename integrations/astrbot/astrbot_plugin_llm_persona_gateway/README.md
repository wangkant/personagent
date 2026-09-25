# astrbot_plugin_llm_persona_gateway

An [AstrBot](https://github.com/AstrBotDevs/AstrBot) plugin that puts
[personagent](https://github.com/wangkant/personagent) on every platform
AstrBot supports. It forwards each allowed message to the agent and sends the
agent's replies back.

## What it does

- Receives group and private messages from every AstrBot platform adapter
  (Telegram, Discord, Slack, QQ, ...), except the ones in `excluded_platforms`.
- Forwards messages from allowlisted groups and senders to the agent's
  `POST /webhook/gateway` as a platform-neutral event.
- Sends the agent's replies (text and images, with a mention in group chats
  where the agent asks for one) back through AstrBot.
- Stops AstrBot's own pipeline when the agent claims the conversation
  (`block_default`), so AstrBot's built-in model never answers in the
  persona's place.

The persona, memory, debounce and typing simulation all run in the agent. This
plugin only forwards and relays.

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
3. Keep NapCat's HTTP API reachable at the agent's `NAPCAT_API`. Proactive
   messages and the catch-up sweep for missed mentions go through it directly.
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
`QQ_GROUPS` (empty means every group), and private chats only from `OWNER_QQ`
or `PRIVATE_ALLOWED_QQS`. The wizard writes the QQ groups you give it to
`QQ_GROUPS`, so to add a QQ group later, add it to both `group_whitelist` and
`QQ_GROUPS` (or leave `QQ_GROUPS` empty).

Before AstrBot carries a busy QQ group, change two AstrBot settings. Both run
before plugin handlers:

- `platform_settings.rate_limit` defaults to 30 messages per 60 s and delays
  messages over the limit rather than dropping them. Raise or disable it.
- `content_safety.internal_keywords` is on by default and silently drops
  messages that match its keyword list, including ones the persona would have
  answered. Review it.

## What changes per platform

The agent speaks one neutral format. The plugin translates at the edges, using
each platform's own mechanisms:

| Platform | Inbound | Outbound |
| --- | --- | --- |
| Telegram | Replying to the bot counts as addressing it, and the adapter's `/@bot` wake prefix is removed from the text. Stickers arrive as an image plus an emoji (adapter). | AstrBot's typing indicator runs for the whole round-trip; mentions rendered by the adapter |
| Discord | `<@id>` becomes a mention with the member's display name; `<#id>`, `<@&id>` and custom emoji become `#channel`, `@role` and `:name:` | Mentions as `<@id>` (adapter) |
| Slack | `<url\|label>` links become `label (url)`; `&amp;`, `&lt;` and `&gt;` are unescaped | Mentions written as `<@id>` in the text, since the adapter drops mention components |
| QQ (aiocqhttp), KOOK, Lark | As the adapter delivers them | Mentions via the adapter |
| All | Videos, files and voice messages arrive as a note the persona can react to: `(sent a video)`, `(sent a file: deck.pdf)`, `(sent a voice message)` | Typing indicator wherever AstrBot's event API supports it |

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
Platforms listed in `GATEWAY_NATIVE_PLATFORMS` keep plain ids. To make someone
the owner in gateway DMs, add their prefixed id to the agent's
`GATEWAY_OWNER_IDS`.

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

If the agent's own log says the forwarder sends `X-Gateway-Token` but
`GATEWAY_TOKEN` is blank, the token is being ignored. Set the same value in
the agent's `.env`.

## Known limitation: Telegram mentions

AstrBot's Telegram adapter identifies a sender by numeric user id
(`telegram:<numeric id>`), but an `@username` mention in a message only by
username (`telegram:<username>`). One person can therefore appear under two
ids, and the agent cannot join them.

When the model mentions a numeric id, Telegram cannot resolve it without a
username, so the mention goes out as the plain text `@123456`. This comes from
the adapter's data model; neither the plugin nor the agent can fix it.
