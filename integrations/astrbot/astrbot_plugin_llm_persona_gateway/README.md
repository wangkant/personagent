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
| `block_default` | bool | `true` | Call `event.stop_event()` only after the agent successfully accepts ownership (`handled: true`). Transport failures, invalid responses, and `handled: false` fall back to AstrBot's normal pipeline. |

## Important: QQ / NapCat double-handling

If NapCat already feeds the agent directly through `POST /webhook/qq`, keep
`aiocqhttp` in `excluded_platforms` (it is there by default). Otherwise the
same QQ message would reach the agent twice — once from NapCat and once from
this plugin.

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
