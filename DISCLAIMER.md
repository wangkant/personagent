# Disclaimer

This project is published for **educational and research purposes** —
specifically to demonstrate prompt-engineering techniques for building
conversational LLM agents (Hermes-style two-stage reasoning, intent
classification, dynamic few-shot retrieval, sticker auto-learning, etc.).

## QQ / Tencent terms of service

The agent depends on third-party QQ protocol implementations (e.g. NapCat,
OneBot v11) which Tencent does **not** officially sanction. Running automated
clients against QQ:

- May violate Tencent's terms of service
- May lead to your QQ account being **frozen, restricted, or permanently
  banned**, especially when the client connects from cloud / overseas IPs
- Is at **your own risk** — neither the author of this template nor the
  maintainers of NapCat / OneBot accept liability for account loss, data
  loss, or any other consequence

## Recommended use

- Use a **secondary / throwaway QQ account**, not your primary one
- Run from a residential IP (home network or a small home server), not a
  cloud VPS — cloud IPs trigger Tencent risk control far more aggressively
- Don't deploy in groups where the bot's behavior would harm or mislead
  users; LLM responses are imperfect and can be wrong
- Don't impersonate real people without their consent

## Privacy

If you fine-tune the persona on real chat data:

- The committed `data/examples.*.jsonl` / `data/feedback.*.jsonl` are read-only
  synthetic seeds. Real reactions, learned examples, preference pairs and
  candidate/evidence logs are written under `runtime/` by default;
  `memory.json` / `eval.jsonl` can also capture real chat content. These default
  paths are gitignored. If you set `AGENT_RUNTIME_DIR`, `AGENT_MEMORY_FILE`,
  `EVAL_FILE` or `LOG_FILE` to another in-repository path, add that path to
  `.gitignore` yourself before running the agent
- LLM API requests send chat context to the model provider. Read the
  provider's data-retention policy before using; some providers train on
  your data unless you opt out
- Tag your bot account clearly so group members know they're talking to an
  AI

## No warranty

The software is provided "as is", without warranty of any kind. See
[LICENSE](LICENSE).
