<div align="center">

# personagent

<p><strong>A persona agent that knows how to talk — and when not to.</strong></p>

A single conversational character for group chats and DMs.<br>
Situated in the room, selective by design, and able to learn without being rewritten by one noisy reaction.

[**English**](README.md) · [简体中文](README.zh-CN.md)

[![CI](https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg)](https://github.com/wangkant/personagent/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/wangkant/personagent?display_name=tag&sort=semver&color=6f42c1)](https://github.com/wangkant/personagent/releases)
[![Python 3.10–3.12](https://img.shields.io/badge/Python-3.10%E2%80%933.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2f855a.svg)](LICENSE)

[**Quick start**](#quick-start) · [Why personagent](#why-personagent) · [Deploy](#deploy-with-astrbot) · [Architecture](#architecture) · [Docs](#documentation)

</div>

<a href="#quick-start">
  <img src="assets/demo.svg" alt="personagent selectively replies or stays silent after a structured decision" width="100%">
</a>

`personagent` turns an OpenAI-compatible chat model into a participant rather than an always-on assistant. AstrBot provides one transport layer for QQ, Telegram, Discord, Slack, Lark, KOOK, and other adapters; every platform shares the same persona, memory, safety, and learning pipeline.

## Quick start

You need Git, Python 3.10+, and one OpenAI-compatible API key. The local trial needs no messaging account or adapter.

```bash
git clone https://github.com/wangkant/personagent.git
cd personagent
python quickstart.py
```

The wizard creates `.venv`, installs dependencies, writes `.env`, creates a persona, can check the model endpoint, and opens the terminal trial. It supports DeepSeek, Kimi, OpenAI, Ollama, and custom OpenAI-compatible endpoints.

```bash
# Open the trial again
.venv/bin/python try_chat.py                 # macOS / Linux
.venv\Scripts\python.exe try_chat.py        # Windows
```

## Why personagent

| | |
|---|---|
| **Situated persona**<br>Relationships, conversational position, intent, and scoped memory sit in the core reply path. | **Selective by design**<br>`PASS` is a first-class outcome. Silence can be the correct response. |
| **Learning behind a gate**<br>Reactions become append-only evidence; only corroborated and promoted candidates affect future replies. | **Fail-closed delivery**<br>Structured output is parsed, filtered, policy-checked, and validated before anything is sent. |

Images, stickers, URLs, videos, and share cards can all become context. Chat, vision, evaluation, and judge calls remain vendor-neutral through OpenAI-compatible HTTP endpoints.

## Deploy with AstrBot

Live conversations use one route:

```text
QQ / Telegram / Discord / Slack / Lark / KOOK / …
                           │
                           ▼
                  AstrBot + forwarder
                           │
                           ▼
             personagent /webhook/gateway
```

1. Run `python quickstart.py`, then start the agent with `python main.py`.
2. Copy the bundled [AstrBot forwarder](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md) into AstrBot's `data/plugins/` directory.
3. In the plugin, allowlist the conversations this persona owns and point `agent_url` to `http://127.0.0.1:8080/webhook/gateway`.
4. To include QQ, remove `aiocqhttp` from `excluded_platforms` and set:

   ```dotenv
   GATEWAY_NATIVE_PLATFORMS=aiocqhttp
   ```

This keeps QQ identity, memory, and learning scopes stable while every platform enters through the same gateway. Keep `NAPCAT_API` configured for QQ-specific background actions. The plugin is default-deny and will forward nothing until its allowlists are configured.

For cross-host deployment, use HTTPS or a private tunnel and set the same non-empty `GATEWAY_TOKEN` in the plugin and agent. A public agent bind also requires `WEBHOOK_SECRET`. See the [deployment guide](docs/deploy.md) for the complete checklist.

## Architecture

![personagent architecture](docs/persona_llm_agent_architecture.svg)

Every message crosses the same boundary:

1. **Ingest** — authenticate, limit, deduplicate, normalize, and enrich the event.
2. **Decide** — resolve relationship and intent, retrieve scoped context, and decide whether to reply.
3. **Generate and validate** — call the model through a structured contract, then filter and validate the result.
4. **Learn asynchronously** — record reactions and evaluations as evidence without blocking the live reply.

Evidence alone changes nothing. Automatic promotion requires compatible corroboration, and every promoted candidate can be audited, rolled back, or superseded. Mutable state stays under `runtime/`; the append-only ledgers remain the source of truth.

## Configuration

`.env.example` is the complete annotated reference. The setup wizard writes only the essentials, and startup preflight reports missing or misspelled settings.

```dotenv
AGENT_LANG=en  # English persona and data
# AGENT_LANG=zh  # Chinese persona and data
```

## Operations

```bash
curl http://127.0.0.1:8080/health   # liveness; no model call
python tools/healthcheck.py          # full diagnostic; model probes spend credits
python -m pytest -q                  # offline regression suite
```

Back up `AGENT_RUNTIME_DIR` together with private persona files, and never commit runtime state. It may contain credentials, account identifiers, conversation excerpts, reactions, and learned material.

## Documentation

- [Deployment guide](docs/deploy.md)
- [AstrBot plugin](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md)
- [Configuration reference](.env.example)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Deployment disclaimer](DISCLAIMER.md)

## Responsible use

Third-party protocol clients may violate platform terms or trigger account controls. Keep deployments private by default, protect secrets and conversation data, use a secondary account where appropriate, and obtain consent before processing other people's messages.

## License

[MIT](LICENSE) © 2026 Qiankang Wang.
