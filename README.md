<div align="center">

# personagent

<p><strong>A persona agent that knows how to talk — and when not to.</strong></p>

One conversational character across group chats and DMs.<br>
Situated in the room, selective by design, and able to learn without letting one noisy reaction rewrite its personality.

[**English**](README.md) · [简体中文](README.zh-CN.md)

[![CI](https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg)](https://github.com/wangkant/personagent/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/wangkant/personagent?display_name=tag&sort=semver&color=6f42c1)](https://github.com/wangkant/personagent/releases)
[![Python 3.10–3.12](https://img.shields.io/badge/Python-3.10%E2%80%933.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2f855a.svg)](LICENSE)

[**Quick start**](#quick-start) · [Why personagent](#why-personagent) · [Deploy](#deployment) · [Architecture](#architecture) · [Configure](#configuration)

</div>

<a href="#quick-start">
  <img src="assets/demo.svg" alt="personagent selectively replies or stays silent after a structured decision" width="100%">
</a>

`personagent` turns any OpenAI-compatible chat model into a situated conversational persona. Run it locally in a terminal, connect QQ directly through OneBot v11, or use the bundled AstrBot gateway for QQ, Telegram, Discord, Slack, Lark, KOOK, and other adapters — all through the same persona, memory, safety, and learning pipeline.

## Quick start

You need Git, Python 3.10+, and one OpenAI-compatible API key. A local trial needs no messaging account or adapter.

```bash
git clone https://github.com/wangkant/personagent.git
cd personagent
python quickstart.py
```

The setup wizard creates `.venv`, installs dependencies, writes `.env`, creates a persona file, optionally checks the model endpoint, and offers to open the terminal trial. It is safe to run again and supports DeepSeek, Kimi, OpenAI, Ollama, and custom OpenAI-compatible endpoints.

Startup preflight reports missing essentials, unknown `.env` keys, invalid runtime paths, and an empty bot name instead of leaving a misconfigured agent silently inactive.

<details>
<summary><strong>Open the terminal trial again or run setup without prompts</strong></summary>

```bash
# macOS / Linux
.venv/bin/python try_chat.py
.venv/bin/python try_chat.py --lang zh

# Windows
.venv\Scripts\python.exe try_chat.py
.venv\Scripts\python.exe try_chat.py --lang zh

# CI / provisioning
python quickstart.py --no-input
```

The trial uses the production persona, prompt assembly, retrieval, output parser, and reply validator. Add `--owner` to test the configured owner relationship or `--name <name>` to choose the speaker.

</details>

## Why personagent

Most chat bots are permanently on duty: formal, eager, and visibly assistant-shaped. `personagent` is built to occupy the social position of a participant.

| | |
|---|---|
| **Situated persona**<br>Register, relationships, conversation position, intent, and scoped memory sit in the core reply path. | **Selective by design**<br>`PASS` is a first-class outcome. Silence can be the correct response. |
| **Learning behind a gate**<br>Reactions become append-only evidence. Only corroborated and promoted candidates affect future replies, and every promotion is reversible. | **Media as context**<br>Images, stickers, URLs, videos, and share cards can inform both meaning and voice. |
| **One character, many transports**<br>Terminal, direct QQ, and gateway traffic share the same agent pipeline. | **Fail-closed output boundary**<br>Structured output is parsed, filtered, policy-checked, and validated before anything is delivered. |

The runtime is vendor-neutral and production-minded: authenticated webhooks, replay protection, bounded concurrency and payloads, persistent deduplication, health checks, isolated mutable state, and cross-platform CI are included.

> **Beta:** releases follow Semantic Versioning, and behavioural or storage changes are recorded in the [changelog](CHANGELOG.md). Controlled personal deployments are supported, but platform-policy and account risk remain the operator's responsibility. Read the [deployment disclaimer](DISCLAIMER.md) before connecting a third-party IM client.

## Deployment

| Path | Best for | Inbound entry | Reply path |
|---|---|---|---|
| **Terminal** | Persona design and local evaluation | `try_chat.py` | Terminal |
| **QQ direct** | The simplest full QQ deployment | NapCat → `/webhook/qq` | NapCat HTTP API |
| **AstrBot gateway** | One transport layer for multiple platforms, optionally including QQ | AstrBot → `/webhook/gateway` | Synchronous gateway response |

### QQ now has two inbound routes — choose one

The original direct path remains the default:

```text
QQ → NapCat → /webhook/qq → personagent
```

QQ can also join every other AstrBot adapter behind the gateway:

```text
QQ → AstrBot → /webhook/gateway → personagent
```

For the second route, remove `aiocqhttp` from the plugin's `excluded_platforms`, allowlist the QQ conversation, stop NapCat from posting the same events to `/webhook/qq`, and set:

```dotenv
GATEWAY_NATIVE_PLATFORMS=aiocqhttp
```

That setting preserves the bare QQ IDs already used by memory, history, whitelists, and learning scopes. **Never enable both inbound routes for QQ at once** or the same event will be processed twice.

Even when AstrBot carries QQ inbound, keep NapCat's HTTP API available through `NAPCAT_API`: QQ-specific proactive sends, missed-mention catch-up, old quoted-message resolution, and OCR still use that direct action channel. See the [deployment guide](docs/deploy.md) and the [AstrBot plugin README](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md) for the exact checklist.

### Direct QQ setup

1. Run `python quickstart.py` and answer the optional deployment questions, or configure `BOT_QQ`, `BOT_NAME`, `NAPCAT_API`, and `QQ_GROUPS` in `.env`.
2. Start with `python main.py`, `./start.sh`, or `.\start.ps1`.
3. Configure a OneBot v11 client such as [NapCat](https://github.com/NapNeko/NapCatQQ) with an HTTP API for outgoing actions and a webhook to `http://127.0.0.1:8080/webhook/qq` for incoming events.

The directions are independent:

```text
OneBot client ──events──▶ personagent :8080   (HOST / PORT)
personagent   ──actions─▶ OneBot client :3000 (NAPCAT_API)
```

NapCat's configuration format can change between releases; use its [current documentation](https://napneko.github.io/) and the repository's [verification checklist](docs/deploy.md) rather than copying a stale configuration block.

### AstrBot gateway

The bundled [AstrBot forwarder](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md) maps adapter events into a platform-neutral request and relays the returned text, images, and mentions. The plugin is default-deny: no group or DM is forwarded until explicitly allowlisted.

Gateway identities are namespaced as `<platform>:<id>` unless the platform is explicitly listed in `GATEWAY_NATIVE_PLATFORMS`. The response includes `owned` separately from `handled`, so an intentional `PASS` still prevents AstrBot's built-in model from speaking over the persona.

Forwarder-only platforms have no persistent outbound channel. To offer a proactive turn, the caller sends a normal gateway event marked `"proactive": true`; if the persona decides to speak, the reply returns in that same request for the caller to relay. The cue is kept out of user history, reactions, and promotable memory.

For any non-loopback deployment, use HTTPS or a private tunnel and configure **both** `WEBHOOK_SECRET` and `GATEWAY_TOKEN`. Gateway requests carry a signed timestamp/nonce/body envelope and are replay-checked. Startup refuses a public bind without both secrets because both webhook routes are always mounted.

## Architecture

![personagent architecture](docs/persona_llm_agent_architecture.svg)

Both QQ ingress choices and every gateway platform converge on one reply boundary:

1. **Ingest** — authenticate, limit, deduplicate, normalize, and enrich the event with conversation, image, link, and share-card context.
2. **Decide** — resolve relationship and mode (`owner`, direct call, follow-up, judge, or proactive), including whether to reply at all.
3. **Retrieve** — combine persona, lorebook, scoped memory, synthetic seeds, and promoted runtime examples relevant to this turn.
4. **Generate** — call the configured model through a structured output contract.
5. **Validate and deliver** — parse JSON, apply output filters and character policy, split safely, resolve stickers, and release only committed output.
6. **Learn off the hot path** — store evaluation and directed reactions as evidence; candidate promotion never blocks the live reply.

The importable core lives in `persona_agent/`; `main.py`, `try_chat.py`, and the tools are thin entry points. Mutable state is separated from tracked seeds under `runtime/` by default.

<details>
<summary><strong>Core package map</strong></summary>

| Modules | Responsibility |
|---|---|
| `agent.py` | Orchestration, modes, debounce, prompt assembly, and model calls. |
| `prompts.py`, `textproc.py`, `pools.py` | Persona contract, safe output processing, and retrieval datasets. |
| `ingestion.py`, `transport.py`, `gateway.py` | Content enrichment, bounded delivery, and platform-neutral forwarding. |
| `learning.py`, `reactions.py`, `evolution.py` | Evaluation, reaction adjudication, and candidate generation. |
| `evidence.py`, `candidates.py`, `promotion.py` | Evidence, candidate lifecycle, promotion, rollback, and materialized views. |
| `stickers.py` | Sticker ingestion, deduplication, tagging, scoring, and selection. |
| `storage.py`, `paths.py`, `health.py`, `preflight.py` | Persistence, runtime isolation, diagnostics, and configuration checks. |

</details>

## Learning with guardrails

The learning system separates observation from authority:

| Stage | What it can do |
|---|---|
| **Evidence** | Record a reaction, accepted retry, or evaluation. It cannot change behaviour. |
| **Candidate** | Propose a versioned example or preference pair. It is inert by default. |
| **Promotion** | Grant a candidate authority to enter retrieval. |
| **Rollback / supersession** | Remove or replace that authority without deleting history. |

Automatic promotion requires at least two compatible events and at least one strong event by default. Evidence is scoped by persona, version, language, conversation, and mode; stale or contradictory signals cannot silently combine. Positive reactions and self-scores are weak signals and never promote a candidate by themselves.

Promoted views are materialized atomically and hot-reloaded into the next relevant turn. The append-only ledgers remain authoritative, so views can be rebuilt and every decision can be audited or reversed.

```bash
python tools/candidates_admin.py list
python tools/candidates_admin.py show <candidate-id>
python tools/candidates_admin.py promote <candidate-id> --reason "reviewed"
python tools/candidates_admin.py rollback <candidate-id> --reason "regression"
python tools/candidates_admin.py rebuild
```

Set `PROMOTE_AUTO=false` for fully manual authority. `EVOLVE_AUTO=true` may diagnose low-scoring replies and file candidates, but it never bypasses promotion.

## Configuration

`.env.example` is the complete, annotated reference and is checked against every environment lookup in the codebase. The setup wizard writes only the essentials; advanced behaviour stays opt-in.

| Area | Main settings | Default posture |
|---|---|---|
| Model | `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` | One OpenAI-compatible endpoint is enough. |
| Persona | `BOT_NAME`, `AGENT_LANG`, `PERSONA_FILE`, `PERSONA_CARD_FILE` | Example persona; private custom files stay outside Git. |
| Runtime | `AGENT_RUNTIME_DIR`, `LOG_FILE` | Isolated `runtime/`; console-only logging. |
| QQ | `BOT_QQ`, `QQ_GROUPS`, `NAPCAT_API`, `WEBHOOK_SECRET` | Direct OneBot ingress; loopback bind. |
| Gateway | `GATEWAY_TOKEN`, `GATEWAY_OWNER_IDS`, `GATEWAY_NATIVE_PLATFORMS` | Namespaced identities; no native platforms. |
| Learning | `REACT_*`, `PROMOTE_*`, `EVOLVE_*`, `EVAL_*` | Capture on; conservative promotion; unattended evolution off. |
| Proactive | `PROACTIVE_*` | Off; never cold-opens an unseen conversation. |

```dotenv
AGENT_LANG=en  # English persona, data, validator, and lexicons
# AGENT_LANG=zh  # Chinese equivalents
```

## Operations and development

```bash
# Cheap liveness check — no model call
curl http://127.0.0.1:8080/health

# Full diagnostic — service probes do spend configured model credits
python tools/healthcheck.py

# Offline test suite used by CI
python -m pip install -r requirements.txt "pytest>=8,<10"
python -m pytest -q
python -m compileall -q .
```

Back up `AGENT_RUNTIME_DIR` together with private persona files. It contains memory, evidence, candidate ledgers, promoted views, learned examples, deduplication state, and sticker metadata. Do not commit it: runtime data may contain credentials, account identifiers, conversation excerpts, reactions, and learned material.

See [CONTRIBUTING.md](CONTRIBUTING.md) for repository conventions and [CHANGELOG.md](CHANGELOG.md) before updating an existing deployment.

<details>
<summary><strong>Repository structure</strong></summary>

```text
persona_agent/   importable application core
main.py          FastAPI service and background loops
quickstart.py    idempotent setup wizard
try_chat.py      terminal trial through the production reply path
integrations/    platform adapters (AstrBot forwarder included)
data/            versioned synthetic persona and retrieval seeds
runtime/         private mutable state (gitignored)
tools/           review, tuning, benchmark, import, and health CLIs
tests/           offline cross-platform regression suite
docs/            deployment guide and architecture diagrams
```

</details>

## Responsible use

This project is unaffiliated with and neither endorsed nor sponsored by any messaging platform or model provider. Third-party protocol clients may violate upstream terms or trigger account controls. Use a secondary account, keep deployments private by default, protect secrets and conversation data, and obtain appropriate consent before processing other people's messages.

See [DISCLAIMER.md](DISCLAIMER.md) for the full deployment notice.

## License

[MIT](LICENSE) © 2026 Qiankang Wang.

## Acknowledgements

`personagent` builds on the [OneBot v11](https://github.com/botuniverse/onebot-11) event model, [NapCat](https://github.com/NapNeko/NapCatQQ), [AstrBot](https://github.com/AstrBotDevs/AstrBot), [FastAPI](https://github.com/fastapi/fastapi), [httpx](https://github.com/encode/httpx), and ideas from [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557), and [BlenderBot 3x](https://arxiv.org/abs/2306.04707). The lorebook/filter model is inspired by SillyTavern's World Info and regex extensions.
