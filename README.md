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
.venv/bin/python try_chat.py --lang zh       # Chinese persona and data
.venv/bin/python try_chat.py --owner         # speak as the configured owner
```

The trial runs the production reply path: persona, retrieval, structured output, filters, and validator. Inside it, `/owner <msg>` speaks one line as the owner, `/as <name> <msg>` as another participant, `/reset` clears the buffer, and `/quit` exits.

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

1. Run `python quickstart.py` and say yes to "connect to an AstrBot install": the wizard copies the bundled [forwarder plugin](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md) into AstrBot's `data/plugins/`, generates the shared `GATEWAY_TOKEN` and writes it to both sides, writes the allowlists you give it, and, if QQ is included, sets `GATEWAY_NATIVE_PLATFORMS=aiocqhttp`. Non-interactive: `python quickstart.py --astrbot <AstrBot data dir> [--qq]`.
2. Restart AstrBot (or reload plugins in its WebUI). Platforms themselves are configured in AstrBot.
3. Start the agent with `python main.py` (or `start.sh` / `start.ps1`, which use the wizard's `.venv`).

Doing it by hand instead: copy the plugin folder into `data/plugins/`, set `agent_url` to `http://127.0.0.1:8080/webhook/gateway`, the same non-empty `gateway_token` as the agent's `GATEWAY_TOKEN`, and the allowlists; to include QQ, remove `aiocqhttp` from `excluded_platforms` and set:

   ```dotenv
   GATEWAY_NATIVE_PLATFORMS=aiocqhttp
   ```

This keeps QQ identity, memory, and learning scopes stable while every platform enters through the same gateway. Keep the OneBot HTTP API (`NAPCAT_API`) reachable for QQ-specific background actions such as proactive sends and OCR. The plugin is default-deny and will forward nothing until its allowlists are configured. The older direct ingress, a OneBot client posting to `/webhook/qq`, is deprecated since 0.3.0: still served, but no longer the documented path.

For cross-host deployment, use HTTPS or a private tunnel and set the same non-empty `GATEWAY_TOKEN` in the plugin and agent. A public agent bind (`HOST=0.0.0.0`) also requires `WEBHOOK_SECRET`; startup refuses a non-loopback bind without both. See the [deployment guide](docs/deploy.md) for the complete checklist, including how to verify each direction on its own.

## Architecture

![personagent architecture](docs/persona_llm_agent_architecture.svg)

Every message crosses the same boundary:

1. **Ingest** — authenticate, limit, deduplicate, normalize, and enrich the event.
2. **Decide** — resolve relationship and intent, retrieve scoped context, and decide whether to reply.
3. **Generate and validate** — call the model through a structured contract, then filter and validate the result.
4. **Learn asynchronously** — record reactions and evaluations as evidence without blocking the live reply.

Evidence alone changes nothing. Automatic promotion requires compatible corroboration, and every promoted candidate can be audited, rolled back, or superseded. Editing the persona document keeps everything learned; a new `PERSONA_VERSION` starts a clean slate. Mutable state stays under `runtime/`; the append-only ledgers remain the source of truth.

## Configuration

`.env.example` is the complete annotated reference. The setup wizard fills in the essentials; the startup preflight (also the first section of `tools/healthcheck.py`) reports missing required settings and any key the template does not list, so a typo is loud instead of silently ignored.

| Area | Settings |
|---|---|
| Model | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` — any OpenAI-compatible `/v1` endpoint. `PRIVATE_MODEL`, `FALLBACK_MODEL`, and `JUDGE_MODEL` share it. |
| Persona | `BOT_NAME`, `AGENT_LANG`, `PERSONA_FILE`, `PERSONA_CARD_FILE` — the card's `reply_style` opts into emoji and extra character sets. |
| Gateway | `GATEWAY_TOKEN`, `GATEWAY_OWNER_IDS`, `GATEWAY_NATIVE_PLATFORMS`; QQ-specific `BOT_QQ`, `NAPCAT_API`, `OWNER_QQ`. |
| Learning | `PROMOTE_AUTO` (conservative promotion, on); `EVAL_ENABLE` and `EVOLVE_AUTO` (self-evaluation and unattended diagnosis, off). |
| State | `AGENT_HOME` (deployment root; relative persona paths resolve under it), `AGENT_RUNTIME_DIR` (`runtime/`, gitignored). |

```dotenv
AGENT_LANG=en  # English persona and data
# AGENT_LANG=zh  # Chinese persona and data
```

## Operations

```bash
curl http://127.0.0.1:8080/health           # liveness; no model call
curl http://127.0.0.1:8080/health/details   # dependency probes; needs X-Gateway-Token once GATEWAY_TOKEN is set
python tools/healthcheck.py                  # full diagnostic; model probes spend credits
python tools/candidates_admin.py list        # what the bot has learned, and from which evidence
python -m pytest -q                          # offline regression suite
```

In any chat the persona owns, `@<BOT_NAME> what have you learned` (or `你学到了什么`) answers with that room's memories, the promoted replies and "not this, this" pairs in effect, proposals still waiting for a second voice, and the recent self-scores; `what do you remember` lists the memories. Neither calls the model.

Back up `AGENT_RUNTIME_DIR` together with private persona files, and never commit runtime state. It may contain credentials, account identifiers, conversation excerpts, reactions, and learned material. If the bot starts cleanly and never answers, work through [when the bot goes quiet](docs/deploy.md#when-the-bot-goes-quiet).

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

## Acknowledgements

Built on the [OneBot v11](https://github.com/botuniverse/onebot-11) event model, [NapCat](https://github.com/NapNeko/NapCatQQ), [AstrBot](https://github.com/AstrBotDevs/AstrBot), [FastAPI](https://github.com/fastapi/fastapi), and [httpx](https://github.com/encode/httpx), with ideas from [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557), and [BlenderBot 3x](https://arxiv.org/abs/2306.04707). The lorebook and output-filter model follows SillyTavern's World Info and regex extensions.
