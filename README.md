<div align="center">

# personagent

<p><strong>A persona agent that knows how to talk — and when not to.</strong></p>

Deployable in group chats and DMs. Grounded in the room, selective by design,<br>
and able to learn from reactions without letting one noisy signal rewrite its character.

[**English**](README.md) · [简体中文](README.zh-CN.md)

[![CI](https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg)](https://github.com/wangkant/personagent/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/wangkant/personagent?display_name=tag&sort=semver&color=6f42c1)](https://github.com/wangkant/personagent/releases)
[![Python 3.10–3.12](https://img.shields.io/badge/Python-3.10%E2%80%933.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2f855a.svg)](LICENSE)

[**Quick start**](#quick-start) · [Why it is different](#why-personagent) · [Deploy](#deployment-paths) · [Architecture](#architecture) · [Configure](#configuration)

</div>

<a href="#quick-start">
  <img src="assets/demo.svg" alt="personagent selectively replies or stays silent after a structured decision" width="100%">
</a>

`personagent` turns any OpenAI-compatible chat model into a situated conversational persona. It can run locally in a terminal, directly on QQ through OneBot v11, or across Telegram, Discord, Slack, Lark, and KOOK through the bundled AstrBot gateway.

## Quick start

You need Git, Python 3.10+, and one OpenAI-compatible API key. The local trial does not require QQ, NapCat, or another messaging adapter.

```bash
git clone https://github.com/wangkant/personagent.git
cd personagent
python quickstart.py
```

The setup wizard creates `.venv`, installs dependencies, writes `.env`, optionally verifies the model endpoint, creates a persona file, and offers to open the terminal trial. It is safe to run again and supports DeepSeek, Kimi, OpenAI, Ollama, and custom OpenAI-compatible endpoints.

<details>
<summary><strong>Open the terminal trial again or bootstrap without prompts</strong></summary>

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

The trial uses the same persona, prompt assembly, retrieval, output parser, and reply validator as a live deployment. Add `--owner` to test the configured owner relationship or `--name <name>` to choose the speaker.

</details>

## Why personagent

Most group-chat bots are permanently on duty: formal, eager, and visibly assistant-shaped. `personagent` is built around the social position of a participant instead.

| **Situated persona** | **Selective by design** |
|---|---|
| Register, relationships, conversational position, intent, and scoped memory live in the core reply path. | `PASS` is a first-class outcome. The agent can decide that silence fits the room better than another message. |
| **Learning behind a gate** | **Media as context** |
| Reactions become append-only evidence; only corroborated, promoted candidates can affect future replies, and every promotion is reversible. | Images, stickers, URLs, videos, and share cards become usable context and can form part of the persona's voice. |

### Production-minded by default

- **Fail-closed output boundary:** structured model output is parsed, filtered, checked against the character policy, and validated before delivery.
- **Vendor-neutral and operable:** chat, judge, evaluation, and vision calls use OpenAI-compatible HTTP endpoints; authenticated webhooks, replay protection, limits, persistent deduplication, health checks, isolated runtime state, and cross-platform CI are included.

> **Beta:** versioned releases follow Semantic Versioning, and behavioural or storage changes are recorded in the [changelog](CHANGELOG.md). Controlled personal deployments are supported, but platform-policy and account risk remain the operator's responsibility. Read the [deployment disclaimer](DISCLAIMER.md) before connecting a third-party IM client.

## Deployment paths

| Path | Best for | Entry point | Notes |
|---|---|---|---|
| **Terminal** | Persona design and local evaluation | `try_chat.py` | No IM account or adapter required. |
| **OneBot v11** | Full QQ deployment | `main.py` → `/webhook/qq` | Primary path; supports QQ-specific image, sticker, proactive, and catch-up features. |
| **AstrBot gateway** | Telegram, Discord, Slack, Lark, KOOK, and other AstrBot adapters | `/webhook/gateway` | Uses the same agent pipeline through the bundled forwarder plugin. |

### QQ through OneBot

1. Run `python quickstart.py` and answer the optional live-deployment questions, or fill `BOT_QQ`, `BOT_NAME`, `NAPCAT_API`, and `QQ_GROUPS` in `.env`.
2. Start the agent:

   ```bash
   python main.py
   # or: ./start.sh
   # Windows: .\start.ps1
   ```

3. Configure a OneBot v11 client such as [NapCat](https://github.com/NapNeko/NapCatQQ) with an HTTP API and webhook:

   ```json
   {
     "http": { "enable": true, "host": "127.0.0.1", "port": 3000 },
     "webhook": {
       "enable": true,
       "url": "http://127.0.0.1:8080/webhook/qq",
       "timeout": 5000
     }
   }
   ```

The two HTTP directions serve different purposes:

```text
OneBot client ──events──▶ personagent :8080   (HOST / PORT)
personagent   ──actions─▶ OneBot client :3000 (NAPCAT_API)
```

Keep the default loopback binding when both services run on one machine. If you expose the webhook to another host, set `HOST=0.0.0.0`, configure `WEBHOOK_SECRET`, and protect the network boundary. `launch.vbs` is available for a local Windows deployment after its three path/account values are configured.

### Other platforms through AstrBot

`POST /webhook/gateway` accepts a platform-neutral event and returns replies for the forwarding adapter to relay. The bundled AstrBot plugin is in [`integrations/astrbot/`](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md).

```text
Telegram / Discord / Slack / Lark / KOOK
                    │
                    ▼
          AstrBot + forwarder plugin
                    │ signed HTTP
                    ▼
      personagent /webhook/gateway
```

The forwarder is default-deny: no group or DM is forwarded until it is explicitly allowlisted. For cross-host deployments, use HTTPS or a private tunnel and configure the same non-empty secret as the plugin's `gateway_token` and the agent's `GATEWAY_TOKEN`. Signed timestamp/nonce/body envelopes are replay-checked. Keep AstrBot's QQ adapter excluded if NapCat already feeds `/webhook/qq`, or the same event will be processed twice.

## Architecture

![personagent architecture](docs/persona_llm_agent_architecture.svg)

Each inbound event passes through one reply boundary regardless of transport:

1. **Ingest** — authenticate, limit, deduplicate, normalize, and enrich the event with conversation, image, link, and share-card context.
2. **Decide** — resolve the relationship and mode (`owner`, direct call, follow-up, judge, or proactive), then decide whether to reply at all.
3. **Retrieve** — combine the persona, lorebook, scoped memory, synthetic seeds, and promoted runtime examples relevant to this turn.
4. **Generate** — call the configured model with a structured output contract.
5. **Validate and deliver** — parse JSON, apply output filters and the character policy, split the reply safely, resolve stickers, and send only committed output.
6. **Learn off the hot path** — record evaluation and directed user reactions as evidence; candidate promotion never blocks the live reply.

The importable core lives in `persona_agent/`; `main.py`, `try_chat.py`, and the tools are thin entry points. Mutable state is separated from tracked seeds under `runtime/` by default.

<details>
<summary><strong>Core package map</strong></summary>

| Module | Responsibility |
|---|---|
| `agent.py` | Orchestration, modes, debounce, prompt assembly, and model calls. |
| `prompts.py`, `textproc.py`, `pools.py` | Persona contract, safe output processing, and append-aware retrieval datasets. |
| `ingestion.py`, `transport.py`, `gateway.py` | Content enrichment, bounded delivery, and platform-neutral forwarding. |
| `learning.py`, `reactions.py`, `evolution.py` | Evaluation, reaction adjudication, and candidate generation. |
| `evidence.py`, `candidates.py`, `promotion.py` | Append-only evidence, candidate lifecycle, promotion policy, rollback, and materialized views. |
| `stickers.py` | Sticker ingestion, deduplication, tagging, persona-fit gates, scoring, and selection. |
| `storage.py`, `paths.py`, `health.py` | Locked/atomic persistence, runtime-path isolation, and service diagnostics. |

</details>

## Learning with guardrails

The learning system separates observation from authority:

| Term | Meaning |
|---|---|
| **Evidence** | An append-only record of a reaction, accepted retry, or evaluation. It cannot alter behaviour. |
| **Candidate** | A versioned proposed example or preference pair derived from evidence. It is inert by default. |
| **Promotion** | The explicit grant of authority that makes a candidate available to retrieval. |
| **Rollback / supersession** | Removal or replacement of that authority without deleting history. |

By default, automatic promotion needs at least two compatible events and at least one strong event. Evidence is scoped by persona, persona version, language, conversation, and mode; stale or contradictory evidence cannot silently combine. Positive reactions and self-scores are weak signals and never promote a candidate by themselves.

Promoted material is materialized atomically into `runtime/promoted.{examples,feedback}.<lang>.jsonl` and hot-reloads into the next relevant conversation. The append-only ledger remains the source of truth, so views can be rebuilt and every decision can be audited or reversed.

```bash
python tools/candidates_admin.py list
python tools/candidates_admin.py show <candidate-id>
python tools/candidates_admin.py promote <candidate-id> --reason "reviewed"
python tools/candidates_admin.py rollback <candidate-id> --reason "regression"
python tools/candidates_admin.py rebuild
```

Set `PROMOTE_AUTO=false` for fully manual authority. `EVOLVE_AUTO=true` enables unattended diagnosis of low-scoring replies, but it only files candidates; it does not bypass promotion. For an interactive review workflow, run `python tools/auto_reviewer.py --apply`.

![Self-evolution loop](docs/self_evolution_loop.svg)

## Output and safety boundary

The model must return one object:

```json
{
  "reasoning": "internal decision summary",
  "intent": "chat",
  "reply": "text to send, or PASS",
  "mem": "optional memory line"
}
```

Only `reply` can reach the transport. Malformed structured output fails closed unless it is a short, chat-shaped naked reply that still passes the validator. XML/JSON residue, provider tokens, template markers, unsupported control characters, unsafe URLs, oversized images, unauthenticated remote webhooks, and replayed gateway envelopes are rejected before delivery.

The character policy is deliberately conservative: common language scripts are allowed; typography is normalized; emoji and optional stylistic character sets require persona-level opt-in. See [v0.2.0](CHANGELOG.md#020--2026-08-11) for the current policy and regression coverage.

## Configuration

`.env.example` is the authoritative, fully annotated reference. The setup wizard writes the minimum viable `.env`; advanced features remain opt-in.

| Area | Main settings | Default posture |
|---|---|---|
| Model | `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` | One OpenAI-compatible endpoint is enough to start. |
| Persona | `BOT_NAME`, `AGENT_LANG`, `PERSONA_FILE`, `PERSONA_CARD_FILE`, `PERSONA_VERSION` | English example persona; custom persona stored outside Git. |
| Runtime state | `AGENT_RUNTIME_DIR` | `runtime/`, gitignored. |
| QQ / OneBot | `BOT_QQ`, `QQ_GROUPS`, `NAPCAT_API`, `WEBHOOK_SECRET` | Loopback-only webhook; all groups when `QQ_GROUPS` is empty. |
| Gateway | `GATEWAY_TOKEN`, `GATEWAY_OWNER_IDS`, `GATEWAY_SOURCE_MAX_AGE_SECONDS` | Loopback-only unless authenticated. |
| Vision and search | `VISION_MODEL`, `GLM_API_KEY`, `TAVILY_API_KEY` | Vision off; keyless DuckDuckGo search fallback. |
| Learning | `REACT_*`, `PROMOTE_*`, `EVOLVE_*`, `EVAL_*` | Reaction capture on; conservative promotion; unattended evolution and self-eval off. |
| Proactive messages | `PROACTIVE_*` | Off. Never cold-opens an unseen conversation when enabled. |
| Capacity and logging | `MAX_IMAGE_BYTES`, `MAX_WEBHOOK_BODY_BYTES`, `MAX_INFLIGHT_WEBHOOKS`, `LOG_FILE` | Bounded input/concurrency; console-only logs. |

Language selection is one switch:

```dotenv
AGENT_LANG=en  # primary build
# AGENT_LANG=zh  # Chinese persona, data files, validator, and lexicons
```

Language-specific seeds live in `data/*.<lang>.*`. Adding another language requires its persona/examples/feedback/filter/lorebook files; non-`zh` languages use the letter-based validator mode.

## Operations

### Health checks

```bash
python tools/healthcheck.py
curl http://127.0.0.1:8080/health
```

- `GET /health` is a cheap liveness endpoint and never spends upstream credits.
- `GET /health/details` probes dependencies, is cached for 60 seconds, and is available only from loopback or with `X-Gateway-Token` when `GATEWAY_TOKEN` is configured.
- A degraded critical dependency returns HTTP 503 from the detailed endpoint.

### Runtime data and backups

Back up `AGENT_RUNTIME_DIR` together with your private persona files. It contains memory, evidence, the candidate ledger, promoted views, learned examples, deduplication state, and sticker metadata. Writes use file locks and atomic replacement where required; the candidate/event logs are append-only.

Do not commit runtime state. It may contain API keys, account identifiers, conversation excerpts, reactions, image metadata, and learned material. The committed `data/` and `tools/fixtures.*.jsonl` files are synthetic seeds only.

### Updating

Review [CHANGELOG.md](CHANGELOG.md), stop the process, back up runtime state, pull the selected release, reinstall dependencies, and restart. Startup performs compatibility handling for supported legacy state; version-specific changes are documented in the release notes.

## Development

Install the checkout and run the same offline suite used by CI:

```bash
python -m pip install -r requirements.txt "pytest>=8,<10"
python -m pytest -q
python -m compileall -q .
```

CI runs the suite on Python 3.10, 3.11, and 3.12 on Linux, runs the real storage and launcher paths on Windows, and builds/imports both wheel and source distributions. Tests use stubbed models and transports; no API keys or network access are required.

Useful maintenance tools:

```bash
python tools/prompt_lab.py
python tools/auto_reviewer.py --apply
python tools/candidates_admin.py list
python tools/import_stickers_folder.py <folder>
python tools/evolution_benchmark.py --help
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for repository conventions, test discovery rules, the module map, and privacy requirements. Please use [GitHub Issues](https://github.com/wangkant/personagent/issues) for reproducible bugs and focused feature proposals.

## Repository structure

```text
persona_agent/   importable application core
main.py          FastAPI service and background loops
quickstart.py    idempotent setup wizard
try_chat.py      terminal trial through the production reply path
integrations/    platform adapters (AstrBot forwarder included)
data/            versioned synthetic persona/retrieval seeds
runtime/         private mutable state (gitignored, created at runtime)
tools/           review, tuning, benchmark, import, and health CLIs
tests/           offline cross-platform regression suite
docs/            architecture and pipeline diagrams
```

## Responsible use

This project is unaffiliated with and neither endorsed nor sponsored by any messaging-platform or model provider. Third-party protocol clients may violate upstream terms or trigger account controls. Use a secondary account, keep deployments private by default, protect secrets and conversation data, and obtain appropriate consent before processing other people's messages.

See [DISCLAIMER.md](DISCLAIMER.md) for the full deployment notice.

## License

[MIT](LICENSE) © 2026 Qiankang Wang.

## Acknowledgements

`personagent` builds on the [OneBot v11](https://github.com/botuniverse/onebot-11) event model, [NapCat](https://github.com/NapNeko/NapCatQQ), [AstrBot](https://github.com/AstrBotDevs/AstrBot), [FastAPI](https://github.com/fastapi/fastapi), [httpx](https://github.com/encode/httpx), and ideas from [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557), and [BlenderBot 3x](https://arxiv.org/abs/2306.04707). The lorebook/filter model is inspired by SillyTavern's World Info and regex extensions.
