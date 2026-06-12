# astrbot_plugin_llm_persona_gateway

An [AstrBot](https://github.com/AstrBotDevs/AstrBot) plugin that turns AstrBot into a thin
multi-platform transport for [persona-llm-agent](https://github.com/qiankangwang/persona-llm-agent).

## What it does

- Subscribes to every message AstrBot receives on any platform adapter
  (Telegram, Discord, Slack, WeChat bridges, ...).
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

3. Open the plugin's configuration in the AstrBot WebUI and point
   `agent_url` at your running agent.

## Configuration

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `agent_url` | string | `http://127.0.0.1:8080/webhook/gateway` | Agent gateway endpoint. |
| `gateway_token` | string | `""` | Sent as `X-Gateway-Token`; must match the agent's `GATEWAY_TOKEN` env. Leave empty if the agent has none. |
| `timeout_s` | int | `180` | HTTP timeout per round-trip. The agent simulates typing delays, keep it generous. |
| `excluded_platforms` | list | `["aiocqhttp"]` | Platform adapter names never forwarded. |
| `group_whitelist` | list | `[]` | Group IDs to forward; empty = all groups. |
| `private_enabled` | bool | `true` | Forward private messages. |
| `private_whitelist` | list | `[]` | Allowed private senders; empty = all. |
| `block_default` | bool | `true` | Call `event.stop_event()` after forwarding to suppress AstrBot's own reply pipeline. |

## Important: QQ / NapCat double-handling

If NapCat already feeds the agent directly through `POST /webhook/qq`, keep
`aiocqhttp` in `excluded_platforms` (it is there by default). Otherwise the
same QQ message would reach the agent twice — once from NapCat and once from
this plugin.

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
