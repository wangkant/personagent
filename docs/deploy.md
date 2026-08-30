# Deploying personagent

The README covers the happy path. This covers the parts that are load-bearing
and were previously written down nowhere — every item here was found by an
audit that tried to deploy from a clean clone and hit something the docs did
not mention.

## The shortest config that works

**To get one reply out of `python try_chat.py`: one setting.**

```
DEEPSEEK_API_KEY=...
```

`DEEPSEEK_BASE_URL` and `DEEPSEEK_MODEL` only matter if you are not using
DeepSeek — the names are historical, and any OpenAI-compatible `/v1` endpoint
works (OpenAI, Zhipu, Moonshot, Together, a local ollama or llama.cpp). There
is no `persona.txt` requirement; a default persona ships in the code.

**To run live on QQ: three.**

```
DEEPSEEK_API_KEY=...
BOT_NAME=...          # what the persona is called, and what it answers to
BOT_QQ=...            # the bot account's number
```

`NAPCAT_API` defaults to `http://127.0.0.1:3000`, `HOST`/`PORT` default to
`127.0.0.1:8080`, and an empty `QQ_GROUPS` means every group the account is in.

Everything else in `.env.example` has a working default. Run
`python tools/healthcheck.py` after configuring: it reports missing settings,
**misspelled** ones (a typo is otherwise completely silent — the value is
ignored and the default is used), and whether each upstream service answers.

## What the host has to provide

Four requirements that nothing else states:

1. **The deployment root must be writable.** Startup takes an instance lock at
   `<AGENT_HOME>/.personagent.instance.lock`, outside `runtime/`. A read-only
   checkout fails to start.
2. **One process per root.** That lock is how two copies are kept from
   corrupting each other's ledgers. To run several personas from one installed
   copy, give each its own `AGENT_HOME`.
3. **`python main.py` runs from the repository root.** It starts uvicorn with
   an import string (`main:app`), so the working directory has to contain it.
4. **`data/` must sit next to the package.** If it does not, the root detector
   falls back to the working directory and every seed lookup silently misses.

## The OneBot bridge

This is the largest piece of the deployment and none of it lives in this
repository. You need, roughly in order:

1. **A second QQ account.** Do not use your own — see `DISCLAIMER.md`.
2. **The QQ NT desktop client**, which the bridge attaches to.
3. **A OneBot v11 implementation**: [NapCat](https://github.com/NapNeko/NapCatQQ),
   LLOneBot or Lagrange. NapCat is what this project is tested against.
4. **A logged-in session** on that account, usually by QR, that survives
   restarts.
5. **Two network directions configured in the bridge**, which is the part
   people get wrong:
   - an **HTTP server** the agent calls to send messages — this is what
     `NAPCAT_API` points at, `http://127.0.0.1:3000` by default;
   - an **HTTP client / webhook** the bridge calls to deliver events, pointed
     at `http://127.0.0.1:8080/webhook/qq` (`HOST`/`PORT`).
6. **The bot account added to the target group.**

The exact configuration shape is the bridge's, not ours, and it has changed
between NapCat major versions — read
[NapCat's own configuration documentation](https://napneko.github.io/) rather
than copying a snippet from here. What must be true is the two directions
above; how they are spelled is theirs.

**Verify the bridge before blaming the agent**, in this order:

```bash
# 1. the outbound direction: the agent -> the bridge
curl http://127.0.0.1:3000/get_login_info

# 2. the inbound direction: send the bot a message in the group and watch
#    the agent's log for the webhook arriving
```

If (1) fails, the agent can never send. If (1) works and (2) never logs
anything, the bridge's webhook is not configured or is pointed elsewhere. Both
failures look identical from the outside — a bot that is running and silent.

## More than one platform

Everything above is the QQ path. For Telegram, Discord, Slack and the rest,
the agent does not connect to the platform at all — a forwarder does, and
POSTs a platform-neutral event to `POST /webhook/gateway`. The one in this
repo is an [AstrBot](https://github.com/AstrBotDevs/AstrBot) plugin at
`integrations/astrbot/astrbot_plugin_llm_persona_gateway/`; copy it into
AstrBot's `data/plugins/`, and configure the platforms in AstrBot's own UI.
The persona, memory, learning and typing simulation stay here.

Two settings and one decision:

- `GATEWAY_TOKEN` — shared with the plugin. Required off-host, and the
  request carries an HMAC-SHA256 envelope over `timestamp.nonce.body` with a
  replay guard, so a token seen in a log is not enough on its own.
- `GATEWAY_OWNER_IDS` — platform-prefixed ids (`telegram:12345`) that get the
  owner branch in DMs. Gateway identities are namespaced `<platform>:<id>` so
  they can never collide with a QQ number.
- The decision: **does QQ go through the forwarder too?**

Leave QQ on NapCat and you have two inbound paths but nothing to reconcile.
Route it through the forwarder and there is one door and one place to
configure platforms — but then set `GATEWAY_NATIVE_PLATFORMS` to the
forwarder's QQ adapter name (`aiocqhttp` for AstrBot), or every QQ
conversation arrives under a namespaced name it has never had before. Memory,
history and every learned example are keyed the bare way, and the evidence and
candidate ledgers content-address their rows over the conversation id — so the
rename changes every id derived from it and cannot be undone by rewriting a
field. `GATEWAY_NATIVE_PLATFORMS` keeps the ids identical to NapCat's.

Naming a platform there grants its forwarder QQ authority, since bare ids are
what `OWNER_QQ`, `QQ_GROUPS` and `PRIVATE_ALLOWED_QQS` are compared against.
Which is why those whitelists then apply to it, unlike to a namespaced
platform — the forwarder's own allowlist is not the only filter any more.

Do not run both doors for QQ at once; the same message would arrive twice.

## Exposing the webhook

Keep the default loopback binding when the bridge and the agent share a
machine. If they do not, set `HOST=0.0.0.0` **and both** `WEBHOOK_SECRET` and
`GATEWAY_TOKEN`. Startup refuses a non-loopback `HOST` without them, including
for a QQ-only deployment: `/webhook/gateway` is mounted whether or not you use
it, so binding a public interface without a gateway token would leave it open.

## Costs to know about

- **`tools/healthcheck.py` spends credits.** Its probes POST to
  `/v1/chat/completions` on every configured endpoint — primary, private, eval
  and vision. The `GET /health` endpoint is the cheap one. The config and
  ledger-size sections of the CLI cost nothing; the service probes do.
- **`tools/prompt_lab.py` needs a second vendor.** `pip install -e ".[judge]"`
  plus `ANTHROPIC_API_KEY`, because the lab generates through a different model
  from the one being tuned — that separation is what makes it a measurement.
- **`tools/auto_reviewer.py --dry-run` is free**; it calls no model. `--no-write`
  reviews for real and prints instead of writing.

## When the bot goes quiet

In rough order of likelihood:

1. **`BOT_QQ` unset or wrong.** The mention detector returns false immediately,
   so the bot starts cleanly, logs nothing, and never answers. `healthcheck`
   warns about this now.
2. **A misspelled setting.** Silent by construction — the default is used.
   `healthcheck` lists any key `.env.example` does not know.
3. **A BOM on `.env`.** The first setting's name carries it and never reaches
   the process, and the file looks correct in every editor.
4. **The bridge's webhook is not reaching you.** See the verification above.
5. **The persona document changed.** `persona_hash` scopes everything the bot
   has learned, so editing `persona.txt` — even a typo fix — orphans the
   promoted material. The agent logs a warning when an entire promoted view is
   refused; there is no re-scoping tool yet, so the learned corpus starts over.
