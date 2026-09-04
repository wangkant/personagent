# astrbot_plugin_llm_persona_gateway

An [AstrBot](https://github.com/AstrBotDevs/AstrBot) plugin that turns AstrBot into a thin
multi-platform transport for [personagent](https://github.com/wangkant/personagent).

## What it does

- Subscribes to every message AstrBot receives on any platform adapter
  (Telegram, Discord, Slack, ...).
- Maps each message to a platform-neutral inbound event and POSTs it to the
  agent's `POST /webhook/gateway` endpoint.
- Converts the agent's reply items (text and base64 images, with optional
  mentions in group chats) back into AstrBot message chains and sends them.
- Optionally stops the AstrBot pipeline afterwards (`block_default`, on by
  default) so AstrBot's built-in LLM never double-replies in conversations
  owned by the agent.

The persona, memory, debounce and typing simulation all live in the agent;
this plugin only forwards and relays. The HTTP round-trip therefore takes as
long as the agent "thinks and types" — that is expected, and the default
180 s timeout covers it.

## Install

The agent's setup wizard does all of this: `python quickstart.py` (answer yes
to connecting AstrBot) or `python quickstart.py --astrbot <AstrBot data dir>
[--qq]` copies the folder, generates the shared token and writes it to both
sides, and writes the allowlists. By hand:

1. Copy this folder into your AstrBot `data/plugins/` directory:

   ```
   data/plugins/astrbot_plugin_llm_persona_gateway/
   ```

2. Restart AstrBot (or reload plugins from the WebUI). AstrBot installs
   `requirements.txt` (only `httpx`) automatically.

3. Open the plugin's configuration in the AstrBot WebUI, explicitly allow the
   group IDs and/or private senders this agent should receive, then point
   `agent_url` at your running agent.

The plugin starts **default-deny**: it forwards no groups and no private
messages until you configure the allowlists. For same-host installs, keep the
default loopback URL. For an agent on another host, use HTTPS and set the same
non-empty secret in the plugin's `gateway_token` and the agent's
`GATEWAY_TOKEN`. A private tunnel is also suitable when it terminates at a
loopback URL visible to AstrBot; never send the token over cleartext HTTP.

## What changes per platform

The agent speaks one neutral dialect; the plugin translates at the edges,
using each platform's own mechanisms rather than its own formats:

| Platform | Inbound | Outbound |
| --- | --- | --- |
| Telegram | Reply-to-bot wake artifact stripped; stickers arrive as image + emoji (adapter) | AstrBot's typing indicator runs for the whole round-trip; mentions rendered by the adapter |
| Discord | `<@id>` becomes a mention segment named from `Message.mentions`; `<#id>`, `<@&id>` and custom emoji become `#channel`, `@role`, `:name:` | mentions as `<@id>` (adapter) |
| Slack | `<url\|label>` links and `&amp;`-style entities unfolded | mention rendered as Slack's `<@id>` mrkdwn, since the adapter drops At components |
| QQ (aiocqhttp), KOOK, Lark | as the adapter delivers them | mentions via the adapter |
| all | videos, files and voice messages arrive as a note the persona can react to (`(sent a video)`, `(sent a file: deck.pdf)`, `(sent a voice message)`) | typing indicator wherever AstrBot's event API supports it |

## Configuration

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `agent_url` | string | `http://127.0.0.1:8080/webhook/gateway` | Agent gateway endpoint. |
| `gateway_token` | string | `""` | Shared secret for bearer authentication and the signed timestamp/nonce/body envelope. Must match `GATEWAY_TOKEN`; required off-host. |
| `timeout_s` | int | `180` | HTTP timeout per round-trip. The agent simulates typing delays, keep it generous. |
| `excluded_platforms` | list | `["aiocqhttp"]` | Platform adapter names never forwarded. |
| `group_whitelist` | list | `[]` | Group IDs to forward; empty = none. |
| `private_enabled` | bool | `false` | Enable forwarding for explicitly allowlisted private senders. |
| `private_whitelist` | list | `[]` | Allowed private senders; empty = none. |
| `block_default` | bool | `true` | Call `event.stop_event()` once the agent claims the conversation (`owned: true`). Transport failures, invalid responses and conversations the agent turned away fall back to AstrBot's normal pipeline. |

`owned` is not `handled`. The agent stays quiet on purpose far more often
than it speaks — a PASS, several messages merged into one answer, the rhythm
gate — and all of those return `handled: false`. Gating on that would hand
the room to AstrBot's built-in model, which would then answer as someone else
in a conversation the persona had decided to sit out. An agent too old to
send `owned` falls back to `handled`, which is what it did before.

## QQ: two ways, and you must pick one

**Default — NapCat feeds the agent directly.** `aiocqhttp` stays in
`excluded_platforms`, QQ goes NapCat → `POST /webhook/qq`, and this plugin
carries everything else. Nothing to configure.

**Or route QQ through here too**, so AstrBot is the single place you configure
every platform. Remove `aiocqhttp` from `excluded_platforms`, add the QQ group
to `group_whitelist`, stop NapCat posting to `/webhook/qq`, and set
`GATEWAY_NATIVE_PLATFORMS=aiocqhttp` on the agent.

That last setting is not optional and not cosmetic. Without it the agent
namespaces forwarded ids, so every QQ conversation arrives under a new name
and the agent addresses rooms and people that do not exist — memory, history
and every learned example are keyed the old way, and the ledgers
content-address their rows over the conversation id, so it cannot be renamed
back afterwards. With it, a QQ message relayed by AstrBot lands on exactly the
keys NapCat would have produced.

Do **not** do both at once: the same message would reach the agent twice.

Two things to change on the AstrBot side before it can carry a busy QQ group,
because both run before plugin handlers: raise or disable the rate-limit stage
(30 messages / 60 s by default, and it stalls rather than drops), and review
`content_safety.internal_keywords`, which is on by default and will silently
drop messages the persona would have answered.

## Request authentication

When `gateway_token` is set, every request carries the legacy
`X-Gateway-Token` bearer header plus a replay-resistant envelope:
`X-Gateway-Timestamp`, a fresh `X-Gateway-Nonce`, and
`X-Gateway-Signature`. The signature is
`sha256=<HMAC-SHA256(token, timestamp + "." + nonce + "." + canonical JSON bytes)>`.
Canonical JSON here means UTF-8, lexicographically sorted keys, compact
separators, and unescaped Unicode. The agent rejects bad, stale, or reused
envelopes. Because the signature covers the exact request bytes, proxies must
not rewrite the JSON body.

The JSON also carries the adapter's original event timestamp. The agent checks
that source time separately from the forwarding-envelope time, so replaying an
old queued event with a freshly signed request is rejected. Events whose
adapter does not provide a valid source timestamp are left to AstrBot's normal
pipeline instead of being forwarded.

## How identities look on the agent side

The agent namespaces every gateway identity as `<platform>:<raw id>`
(e.g. `telegram:12345`), so memory and history never collide with QQ
numbers. To grant someone owner privileges in gateway DMs, add their
prefixed id to the agent's `GATEWAY_OWNER_IDS` env.

## Known limitation: Telegram mention-identity asymmetry

The AstrBot Telegram adapter exposes two different identity spaces for the
same human:

- **Senders** are identified by their numeric Telegram user id, so the
  agent sees them as `telegram:<numeric id>`.
- **Inbound third-party mentions** (`@username` in a message) carry only
  the username, so the agent sees the mention target as
  `telegram:<username>`.

One person can therefore map to two distinct ids in the agent's memory and
buffers, and the agent has no way to join them. Consequently, when the
model emits a mention of a *numeric* id (e.g. `[AT:telegram:123456]`,
learned from a sender identity), the Telegram send path renders it as the
literal text `@123456` rather than a working mention — Telegram cannot
resolve a bare numeric id without a username. This is a limitation of the
AstrBot adapter's data model, not something the plugin or agent can fix.
