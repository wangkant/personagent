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

- The committed `data/examples.*.jsonl` / `data/feedback.*.jsonl` are synthetic
  seeds, but the agent **appends high-scoring real replies to them at runtime**;
  `memory.json` / `eval.jsonl` also capture real chat content (those are
  gitignored). **Review `data/examples.*.jsonl` / `data/feedback.*.jsonl` before
  pushing** to a public repo, or keep your tuned copies out of git
- LLM API requests send chat context to the model provider. Read the
  provider's data-retention policy before using; some providers train on
  your data unless you opt out
- Tag your bot account clearly so group members know they're talking to an
  AI

## No warranty

The software is provided "as is", without warranty of any kind. See
[LICENSE](LICENSE).
