# qq-persona-agent

**English** | [中文](README.zh-CN.md)

A template for building a **persona-driven LLM agent on QQ groups** — designed to send messages that read like a real person rather than a customer-service bot.

> **Read [DISCLAIMER.md](DISCLAIMER.md) before deploying.** Third-party QQ protocol clients are unsanctioned by Tencent; use a secondary account and run from a residential IP.

## What's in the box

| Module | What it does |
|---|---|
| `agent.py` | Hermes-style two-stage output (`<reasoning>` + `<intent>` + `<reply>`); 6 intent tags drive sub-styles; per-user RAG memory; dynamic few-shot retrieval over `examples.jsonl` / `feedback.jsonl`; regex pre-flight that strips markdown / emoji / fake-action artifacts; async self-eval scoring each reply 1-5 to `eval.jsonl` |
| `stickers.py` | md5-deduped sticker library; auto-steals new stickers seen in group; vision-tags them once context accumulates; lets the model send them via `[STICKER:<tag>]` markers in the reply |
| `main.py` | FastAPI webhook receiver. NapCat POSTs group events to `/webhook/qq`, agent processes and POSTs replies back to NapCat's HTTP API |
| `tools/bootstrap_from_history.py` | One-shot bootstrap: pulls group history, computes owner's message-frequency profile, seeds the sticker library |
| `tools/auto_reviewer.py` | Scans low-score entries in `eval.jsonl` and proposes `failure_mode + constraint + BAD/OK pair_draft` for prompt patches |
| `tools/prompt_lab.py` | Offline interactive tuning: run the agent against `fixtures.jsonl`, rate replies, approved ones flow into `examples.jsonl` |
| `tools/import_stickers_folder.py` | Bulk-import stickers from a local folder, auto-tag via vision model |

## Quick start

Requirements: Python 3.10+, NapCat (or any OneBot v11 implementation), an OpenAI-compatible chat completions API key.

```powershell
# 1. Install deps
pip install -r requirements.txt

# 2. Configure (every field is empty by default — fill in your own)
copy .env.example .env
notepad .env

# 3. Persona
copy persona.example.txt persona.txt
notepad persona.txt        # write your bot's personality

# 4. Run
$env:PYTHONIOENCODING='utf-8'
python main.py
```

You should see `bot started on 0.0.0.0:8080 (agent=True)`.

> Optional: `launch.vbs` in the repo root is a one-click Windows launcher that starts NapCat and the agent in two minimized windows. Edit the three paths/QQ at the top before using.

Configure your NapCat / OneBot client to POST events to `http://127.0.0.1:8080/webhook/qq`:

```json
{
  "http": { "enable": true, "host": "0.0.0.0", "port": 3000 },
  "webhook": {
    "enable": true,
    "url": "http://127.0.0.1:8080/webhook/qq",
    "timeout": 5000
  }
}
```

## Configuration

All settings come from `.env`. Key fields:

| Variable | What |
|---|---|
| `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` | Primary chat-completion model. Any OpenAI-compatible endpoint works |
| `ANTHROPIC_*` | Optional Anthropic-compatible endpoint used by the private-message path |
| `BOT_QQ` / `BOT_NAME` | The bot account's QQ number and display name |
| `OWNER_QQ` / `OWNER_NAME` / `OWNER_RELATIONSHIP` | A "favorite person" the bot is closer to (optional) |
| `QQ_GROUPS` | Comma-separated group IDs to listen on |
| `VISION_MODEL` + `GLM_API_KEY` / `GLM_BASE_URL` | Vision model for image / sticker understanding. Leave blank to skip (OCR-only fallback) |
| `PERSONA_FILE` | Path to your persona prompt (default `persona.txt`) |
| `FALLBACK_MODEL` + `RATE_THRESHOLD` | Auto-downgrade to a cheaper model when request rate spikes |

See `.env.example` for the full list.

## Iteration loop (Hermes-style)

The agent's prompt is structured to make failures debuggable:

```
observe failure
  ↓
locate which block owns it (STYLE_GUIDE / REASONING_PROTOCOL / INTENT_RULES)
  ↓
add a hard constraint with a counter-example next to similar rules
  ↓
write a BAD/OK pair into feedback.jsonl
  ↓
next time a similar input arrives, dynamic few-shot retrieval surfaces the pair
```

The retrieval over `examples.jsonl` + `feedback.jsonl` uses 2-char Chinese ngrams + scenario tags + recency decay, so even small datasets (5-10 entries per failure mode) start helping immediately.

## Privacy

Files that may contain real chat content are gitignored:

```
.env                      # API keys
eval.jsonl                # raw self-eval scoring trace
memory.json               # extracted long-term memories
stickers.json             # sticker index incl. sample chat contexts
stickers/auto/            # downloaded sticker binaries
owner_profile.json        # owner's message-frequency profile
unknown_stickers.jsonl    # download URLs
candidates.jsonl          # auto-reviewer output
```

Do not push them. The committed `examples.jsonl` / `feedback.jsonl` / `tools/fixtures.jsonl` in this template are **fully synthetic** examples showing the format only.

## License

[MIT](LICENSE).

## Acknowledgements

- Hermes 3 (NousResearch) for the thinking-then-reply output format
- NapCat / OneBot v11 ecosystem for the QQ protocol layer
- Various OpenAI-compatible model providers used during development
