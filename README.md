<div align="center">

# personagent

<p><strong>A chat bot that acts like someone in the room, not an assistant in a sidebar.</strong></p>

You describe a character in a text file. personagent plays that character in your group chats and DMs —<br>
answering when it has something to say, staying quiet when it doesn't, and taking corrections when it gets one wrong.

[**English**](README.md) · [简体中文](README.zh-CN.md)

[![CI](https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg)](https://github.com/wangkant/personagent/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/wangkant/personagent?display_name=tag&sort=semver&color=6f42c1)](https://github.com/wangkant/personagent/releases)
[![Python 3.10–3.12](https://img.shields.io/badge/Python-3.10%E2%80%933.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2f855a.svg)](LICENSE)

[**What is this?**](#what-is-this) · [Try it in 5 minutes](#try-it-in-5-minutes) · [Write your character](#write-your-character) · [Put it in a real chat](#put-it-in-a-real-chat) · [How it learns](#how-it-learns) · [Configuration](#configuration) · [Troubleshooting](#running-it-day-to-day) · [Docs](#documentation)

</div>

<a href="#try-it-in-5-minutes">
  <img src="assets/demo.svg" alt="personagent reads a group chat and either replies, saves a memory, or stays silent" width="100%">
</a>

## What is this?

personagent is a Python program you run on your own machine. It gives one made-up character a chat account and lets it sit in your group chats like any other member.

Here is the whole idea in one example. A friend posts:

> **sam:** spent 3 hours on this and ctrl+z'd the whole thing into the void

| A normal assistant bot says | personagent says |
|---|---|
| "I'm sorry to hear that! Have you tried checking your editor's local history? Let me know if you'd like more tips on recovering unsaved work." | "rip. take five before you go back in" |

And when the next three messages in the room are `lol`, `same`, `D . e`, it says **nothing at all** — which in a real group chat is usually the correct answer. Deciding not to speak is a normal outcome here, not a failure.

### What you need

| You bring | Why |
|---|---|
| **A character** — a few sentences in a `persona.txt` you write | This is the bot's entire personality. A starter file is copied in for you. |
| **An API key** for any OpenAI-compatible chat model — DeepSeek, Kimi, OpenAI, Zhipu, Together, or a **local Ollama** | Every reply is one or two model calls, billed to your account. There is no personagent service; running a model locally is the only free option. |
| **A way onto a chat platform** — [AstrBot](https://github.com/AstrBotDevs/AstrBot), a separate program you install yourself | personagent never logs into QQ / Telegram / Discord itself. Not needed to try it locally. |

### What it is, technically

- **A small web service you run**, not a library. `python main.py` starts FastAPI on `127.0.0.1:8080`. AstrBot holds the chat-platform connections and POSTs each message to it; personagent returns the reply in the same HTTP response, or returns "nothing to say."
- **Clone it, don't `pip install` it.** `main.py`, `try_chat.py` and `quickstart.py` are repo-root entry points, and the seed data in `data/` has to sit next to the package. Installing the wheel gets you the pipeline for testing, not a runnable bot.
- **Vendor-neutral by plain HTTP.** Every model call — writing a reply, captioning an image, and the cheap second model that decides whether to speak at all — is a POST to an OpenAI-compatible chat-completions endpoint. No vendor SDK is installed.
- **Your data stays yours.** Everything the bot remembers or learns is JSON under `runtime/` on your disk. What leaves your machine is what you'd expect: the chat context in each model request, to the provider you configured.

### What it does that a normal bot doesn't

- **Stays quiet.** In a group chat the model can answer with `PASS` instead of text, and most silences are cheaper than that — an un-addressed room needs ~30 messages before the bot even considers speaking. *(In a one-on-one DM there is no PASS: the persona always answers, and only the length varies.)*
- **Doesn't sound like a help desk.** The prompt bans assistant tone outright, and a regex filter drops a finished reply that still slipped out an "as an AI…" or "hope this helps."
- **Types like a person.** A reply is written as separate lines, and each goes out as its own message with a typing pause — so a longer thought arrives as two or three bubbles rather than one paragraph. Most replies are one-liners and go out as a single message.
- **Remembers, per conversation.** Short notes scoped to one room, never leaking between rooms or platforms.
- **Reads more than text.** Images get captioned, stickers get recognized and re-used, Bilibili/YouTube/web links get unwrapped into a title and description, QQ share cards get unpacked. Voice, video and forwarded chats become honest placeholders it is told not to invent around.
- **Takes corrections.** Tell it a reply was wrong and say what you wanted instead; after a second confirming signal, that correction starts shaping later replies. See [How it learns](#how-it-learns).

**Who it's for:** someone who wants one specific character living in their own group chat. **Who it's not for:** anyone building a support assistant — this project spends all its effort on *not* being one.

## Try it in 5 minutes

No chat account, no AstrBot, no platform setup. You need Git and Python 3.10–3.12.

```bash
git clone https://github.com/wangkant/personagent.git
cd personagent
python quickstart.py
```

It creates `.venv/`, installs the dependencies and drops a copy of `.env.example` into place, then asks eight short questions — which model provider and model, the key, the bot's name, the language, whether to connect AstrBot (say no for now), whether to test the key with one tiny call, and whether to chat right away. Your answers go into `.env`, a starter `persona.txt` is copied in, and you land in a terminal chat.

**Want a zero-cost trial?** Install [Ollama](https://ollama.com) and pull the model first — `ollama pull qwen3` — then pick provider **4) Ollama (local)** at the first question and press Enter through the key prompt, which is pre-filled with a dummy value because a local Ollama doesn't check it. If the wizard's test call fails on this path it almost always means Ollama isn't running or the model isn't pulled, not that your key is bad.

Reopening the trial later, without activating the venv:

```bash
.venv/bin/python try_chat.py              # macOS / Linux
```
```powershell
.venv\Scripts\python.exe try_chat.py      # Windows
```

Inside the trial: `/owner <msg>` speaks as the **owner** — the one account you designate as the bot's closest person (`OWNER_QQ`, or `GATEWAY_OWNER_IDS` on other platforms); it gets a warmer register and can manage the bot's memories. `/as <name> <msg>` speaks as someone else in the room, `/reset` clears the conversation, `/quit` exits. Flags: `--owner` to speak as the owner throughout, `--name Alex` to set your own display name, and `--lang zh` to switch the *seed data* (examples, feedback, lorebook, output filter) and the reply validator to Chinese — your `persona.txt` is used as written either way, so write it in the language you want.

> **`(stays quiet)` is not a bug.** The trial prints that when the character decided it had nothing to add. Try again, or say something it can actually respond to.

<details>
<summary><b>What the trial does and doesn't cover</b></summary>

The trial runs the real reply path — your persona, example retrieval, the structured output contract, the glyph/charset filter — so what you read is close to what a group would see. Three deliberate differences:

- **Self-scoring and image understanding are off**, to keep a first run cheap.
- **The output filter doesn't run.** A reply that production would drop as too assistant-sounding is still printed here.
- **The pre-model silence gates are bypassed.** Because you're always talking to the bot directly, the allowlist, the addressed check and the ~30-message threshold never run. The model's own `PASS` decision still does, which is why `(stays quiet)` can still come back.

</details>

<details>
<summary><b>What gets created on your disk</b></summary>

| Path | What it is |
|---|---|
| `.venv/` | The virtualenv, holding the seven declared dependencies and everything they pull in (~25 packages). Nothing is installed globally. |
| `.env` | Your settings, **including your API key**. Created `chmod 600`, gitignored. |
| `persona.txt` | Your character, copied from `data/persona.example.<lang>.txt`. Gitignored — yours never gets committed. |
| `runtime/` | Everything the bot remembers and learns, as JSON. Gitignored. Contains real chat excerpts once it is live. |

Re-running `python quickstart.py` never touches an existing `persona.txt`, and won't copy `.env` over the top of yours. It does ask before re-running the wizard — but only if `LLM_API_KEY` is already set, and if you go ahead, the wizard rewrites `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `BOT_NAME` and `AGENT_LANG` from *its* defaults, not from your current values. Re-type them rather than pressing Enter through: a changed `BOT_NAME` starts a new character and orphans everything it learned.

`python quickstart.py --no-input` skips the wizard entirely (this also happens automatically in CI or when stdin is piped).

</details>

## Write your character

`persona.txt` is the whole personality, in plain language. No schema, no YAML — you are writing a description of a person.

```text
You're Nova, just another regular in this group chat. The goal: send messages
that read like a real person, not an AI assistant.

Vibe:
- dry, deadpan, terminally online, drops the right meme at the right moment

Style rules:
- Not a help desk. Don't summarize, don't offer to assist
- Tease with a light touch — leave people an out
- Don't fake knowing a meme/show/game. If you don't know it, say so
- Match the room's energy: short when it's banter, an actual take when it's a real conversation
```

The starter file quickstart copies in is a **template**: it still contains `{bot_name}`, `{owner_name}` and `{owner_relationship}` placeholders and a note-to-self at the bottom. Nothing fills those in for you — the file is handed to the model exactly as written — so replace them before going live.

`persona.txt` is read once at startup, so an edit takes effect when you restart `python main.py`. Editing it does **not** lose anything the bot has learned.

Four smaller files under `data/` shape behaviour alongside it, and unlike `persona.txt` these *are* re-read from disk while the bot runs:

| File | What it does |
|---|---|
| `examples.<lang>.jsonl` | Good replies, retrieved by relevance and shown to the model as few-shot examples. |
| `feedback.<lang>.jsonl` | "You said X, better would have been Y" pairs — the same shape the learning loop produces. |
| `lorebook.<lang>.json` | Keyword-triggered blocks, injected only when a keyword shows up. Six ship: three honesty guardrails (how to answer "are you a bot?", don't fake having seen that show, don't invent a shared memory), plus don't-pile-on-the-owner, a slang glossary, and a don't-repeat-the-URL rule for shared links. |
| `output_filter.<lang>.json` | Regexes applied to the finished reply. Each either rewrites it or drops it entirely. This is what kills "as an AI…" and "hope this helps." |

<details>
<summary><b>Optional: the style knobs</b></summary>

A persona document may end with a `[style]` block, which the engine reads and strips out before the text reaches the model:

| Knob | Options | Means |
|---|---|---|
| `length` | short / medium / long | Default reply length. |
| `vent` | hold / ask / solve | When someone is venting: sit with it, ask, or offer a fix. |
| `recs` | ask_back / offer | Asked for a recommendation: narrow it down first, or just name one. |
| `good_news` | cheer / deadpan | How it reacts to good news. |
| `particles` | capped / free / none | Filler words and verbal tics. |
| `fatigue` | stock / own | When its last two replies both used the same snarky-reversal register, the third has to switch — from a fixed phrase menu (`stock`) or in the character's own words (`own`). |

Separately, `persona.card.json` is a small config file (not text for the model) controlling emoji and reply length:

```json
{ "reply_style": { "emoji": true, "charsets": ["music"], "max_chars": 320 } }
```

Both are opt-in; without them the character gets a narrow default — no emoji, no optional character sets.

</details>

## Put it in a real chat

personagent does not connect to any chat platform. **[AstrBot](https://github.com/AstrBotDevs/AstrBot) does** — it is a separate chat-bot framework you install and run yourself, and it already speaks QQ, Telegram, Discord, Slack, Lark, KOOK and more. This repo ships a small plugin for it that forwards every message to personagent and sends the reply back.

```text
   QQ / Telegram / Discord / Slack / Lark / KOOK / …
                        │
                        ▼
              AstrBot  +  forwarder plugin          ← a separate program you install
                        │  HTTP POST
                        ▼
            personagent  /webhook/gateway           ← this repo, python main.py
```

Two processes, one direction: AstrBot calls personagent, never the other way round. So after changing platform credentials or the plugin's settings you restart **AstrBot**; after changing `.env` you restart **personagent**.

**Steps**

1. **Install and start AstrBot**, and set up at least one platform in its own WebUI. Nothing in this repo installs it for you.
2. **Wire the two together** — `python quickstart.py` and answer yes to "connect to an AstrBot install". It copies the [forwarder plugin](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md) into AstrBot's `data/plugins/`, generates a shared `GATEWAY_TOKEN` and writes it to both sides, and can switch on a platform adapter from a bot token. Non-interactively:
   ```bash
   python quickstart.py --astrbot <AstrBot data dir> [--qq] [--platform telegram --token <bot token>]
   ```
   Telegram, Discord and KOOK take one bot token; **Slack needs `--token` *and* `--app-token`**; **Lark uses `--app-id` and `--app-secret`** instead.
3. **Fill in the allowlists** in AstrBot's WebUI, under the plugin's config. The plugin forwards **nothing** until you do — `group_whitelist` and `private_whitelist` both start empty, and DMs are off. This is the most common reason a fresh install looks dead.
4. **Restart AstrBot**, then start the agent:
   ```bash
   .venv/bin/python main.py              # macOS / Linux
   ```
   ```powershell
   .venv\Scripts\python.exe main.py      # Windows
   ```
   Or `./start.sh` / `.\start.ps1`, which create the venv and install dependencies themselves if they're missing. Run it from the repo root either way.

**Set `BOT_NAME` and `BOT_QQ` in `.env`** (quickstart wrote that file into the repo root):

```ini
BOT_NAME=Nova
BOT_QQ=10001
```

Despite the name, `BOT_QQ` is load-bearing on *every* platform: with it empty the @-mention check always returns false, so the bot never answers a bare @. It still answers its name, DMs and the occasional spontaneous turn, which is exactly what makes this hard to spot. Any stable number works if you have no QQ account. With `BOT_NAME` empty, the bot only answers explicit @-mentions, never its own name.

<details>
<summary><b>Adding QQ specifically</b></summary>

QQ needs more than the other platforms, and none of it lives here: a second QQ account (not your own), the QQ NT desktop client, and a OneBot v11 implementation such as [NapCat](https://github.com/NapNeko/NapCatQQ) logged in on it. AstrBot's `aiocqhttp` adapter then talks to NapCat — and you configure that inside AstrBot, not with the wizard.

**Two settings, not one.** Remove `aiocqhttp` from the plugin's `excluded_platforms` (it is excluded by default, so QQ messages are dropped before the allowlists are even read), *and* set `GATEWAY_NATIVE_PLATFORMS=aiocqhttp` on the agent. The `--qq` flag does both. Skipping the second one means every QQ conversation arrives under a new namespaced id and all existing memory and learning for those rooms is orphaned — and it can't be undone by editing a field afterwards.

**Keep NapCat's HTTP API reachable** (`NAPCAT_API`, default `http://127.0.0.1:3000`) even once AstrBot carries QQ messages. Two things still go out through it directly: proactive messages, and the catch-up sweep for @s missed while offline. Turn it off and both fail silently. (Quote resolution falls back to the agent's own recent-message index on the forwarded route, and OCR is skipped there entirely — NapCat is only asked for those on the deprecated direct path.)

Two things that only work on QQ: the bot cannot speak first on a forwarded platform (there is no open channel to send into — a reply can only ride back on the request that brought a message), and sticker-learning and OCR are QQ-path features.

The old direct route — a OneBot client POSTing to `/webhook/qq` — is **deprecated since 0.3.0**. It still works and warns once. Don't run both doors for QQ at the same time, or every message arrives twice. `launch.vbs` in the repo root belongs to that old path and is deprecated too.

</details>

<details>
<summary><b>Running across two machines</b></summary>

The default is a loopback-only service with no authentication, which is correct when AstrBot and personagent share a machine. The moment they don't:

- Set `HOST=0.0.0.0` **and both `GATEWAY_TOKEN` and `WEBHOOK_SECRET`**. Startup refuses a non-loopback bind without both — even if you never touch the QQ route that `WEBHOOK_SECRET` protects.
- **personagent serves plain HTTP only.** "Use HTTPS" means putting a reverse proxy or a private tunnel in front of it.
- That proxy must pass the request body through **byte for byte**. Each request carries an HMAC signature over the exact bytes, so anything that re-serializes the JSON turns every request into a 403.
- Clocks must be within 5 minutes on both hosts, for the same reason.

The service exposes four routes — `GET /health`, `GET /health/details`, `POST /webhook/gateway`, and the deprecated `POST /webhook/qq` — plus FastAPI's `/docs`, `/redoc` and `/openapi.json`, which are **not** disabled. Worth knowing before you bind a public interface.

</details>

## How a message becomes a reply

![personagent architecture](docs/persona_llm_agent_architecture.svg)

1. **Arrive** — authenticate, drop duplicates, check the allowlist, and wait ~2.5 s so a burst of messages becomes one turn.
2. **Translate** — images to captions, stickers to meanings, links to titles, quotes to who-said-what. All of it fenced as untrusted text the model is told may contain injection attempts.
3. **Decide** — is this addressed to me, is it my business, is there anything to say? Most silences never reach a model at all. Self-initiated turns get a cheap model call that answers only PASS-or-reply before the expensive one runs.
4. **Write and check** — one model call returns a single JSON object with four fields: `reasoning`, `intent`, `reply` and `mem`. Anything malformed is discarded whole and nothing is sent. `reply: "PASS"` means stay silent; `mem` is a fact worth remembering.
5. **Deliver** — run the output filter, strip any emoji or symbol sets the persona didn't ask for, split into short messages, send.
6. **Watch** — record what happens next as evidence, without blocking the reply.

**Memory** is two small things, both scoped to one conversation and kept in `runtime/`: up to 50 short notes per conversation (written by the model, or by you with `Nova remember <fact>`), and one longer standing note the model rewrites as things change. Both refuse anything shaped like an instruction, so nobody can store "always reply in French" as a "fact." The rolling message buffer is in memory only and is gone on restart.

## How it learns

Nothing is fine-tuned and no weights change. "Learning" here means a handful of extra examples get pasted into the prompt on later turns — and there is a gate in front of that.

**What you do:** reply to one of the bot's messages — quote it, @ it, or say its name — and tell it that reply was wrong, ideally saying what you wanted instead. In a group, a reaction that neither quotes nor names the bot is invisible to this path, however obviously it was aimed at the bot. (One exception: if the bot has just asked you what you meant, your next message counts for a few minutes without either.)

**What happens:** the bot watches for 15 minutes for a reaction to each reply it sends. A cheap model reads yours and classifies it. The verdict is appended to a log that is never rewritten, and proposes a *candidate* — a change that does nothing at all until it is promoted. Promotion needs **two compatible signals, at least one of them strong**, from the same conversation, within 30 days. A "strong" signal is one of two things, and both require the person the reply was aimed at: they said it was wrong *and* said what it should have been, or they accepted the bot's second attempt. A bystander's correction is never strong, not even the owner's. Contradicting evidence blocks promotion outright and leaves it for you.

In practice, correcting it twice yourself is the normal way to teach it — a rejection followed by the clarification, or a correction followed by accepting its second attempt.

**Two things that surprise people:**

- **Good replies are never learned automatically.** Five people can laugh at a reply and nothing happens. "That one was great, do more of that" only takes effect if you promote it by hand.
- **This is on by default and costs money.** Every matched reaction is one extra model call. It can also send an unprompted "wait, what did you mean?" about two minutes after you tell it a reply was wrong without saying what you wanted instead (at most once an hour per conversation). Turn both off with `REACT_LEARN=false` / `REACT_ELICIT=false`. Self-scoring (`EVAL_ENABLE`) and unattended self-diagnosis (`EVOLVE_AUTO`) are the ones that ship **off**.

**Seeing and undoing it:**

```bash
python tools/candidates_admin.py list                   # proposals still waiting — NOT what it has learned
python tools/candidates_admin.py list --state promoted  # what is actually shaping replies right now
python tools/candidates_admin.py show <id>              # one proposal and every piece of evidence behind it
python tools/candidates_admin.py promote <id>           # approve by hand (the only route for a good reply)
python tools/candidates_admin.py rollback <id>          # revoke a promoted one; takes effect next turn
```

Or just tell it in the chat that it was wrong — an accepted correction automatically revokes anything that taught that reply. Nothing is ever erased, only stripped of authority; the logs stay for audit, which also means they keep verbatim quotes of real messages. Deleting files under `runtime/` yourself is the only true erasure.

**Editing `persona.txt` keeps everything learned.** Changing `PERSONA_VERSION` — or `BOT_NAME` — starts a new character, and the old one's learned material is refused from then on. That is deliberate for `PERSONA_VERSION`; it surprises people about `BOT_NAME`.

## Configuration

`.env.example` is the full annotated reference, and a test keeps it honest — every setting the code reads is documented there. It lists 91 settings.

**Exactly one of them is required: `LLM_API_KEY`.** The other 90 all have defaults. The template shows the value the shipped `.env` uses, which for a couple of settings differs from the code's built-in fallback — so change values rather than deleting lines. For a live bot, add `BOT_NAME` and `BOT_QQ` so it can tell when it is being spoken to.

| What you want to do | Settings |
|---|---|
| Pick a model | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` — any OpenAI-compatible `/v1` endpoint. `PRIVATE_MODEL`, `FALLBACK_MODEL` and `JUDGE_MODEL` are alternate model *names* on the same endpoint and key. |
| Name the character | `BOT_NAME`, `PERSONA_FILE`, `PERSONA_CARD_FILE`. |
| Switch language | `AGENT_LANG=en` or `zh` — picks the seed examples, lorebook and filter, and gives that language its own separate learning history. Your own `persona.txt` is used as written. |
| Connect a platform | `GATEWAY_TOKEN` (shared with the plugin), `GATEWAY_OWNER_IDS` (`telegram:12345`), `GATEWAY_NATIVE_PLATFORMS`; `BOT_QQ`, `OWNER_QQ`, `NAPCAT_API` for QQ. |
| Control learning | `REACT_LEARN` and `REACT_ELICIT` (both **on**), `PROMOTE_AUTO` (on), `EVAL_ENABLE` and `EVOLVE_AUTO` (both off). |
| Read images | `VISION_MODEL` plus `GLM_API_KEY` and `GLM_BASE_URL` — vision always uses this **second credential pair**, never your primary key. Leave `VISION_MODEL` blank and image captioning does nothing. |
| Move state | `AGENT_HOME` (deployment root — give each character its own to run several from one copy), `AGENT_RUNTIME_DIR` (must stay *beneath* `AGENT_HOME`, or startup fails). |

A few sharp edges worth knowing before they bite:

- **A misspelled setting is silent** — the value is ignored and the default is used. Startup logs every key `.env.example` doesn't recognize, but only for keys in the `.env` *file*; variables injected by Docker or systemd are never checked. Neither stops startup.
- **A shell variable beats `.env`.** Settings are loaded without override, so a stale `export` quietly shadows a corrected file.
- **Booleans are inconsistent.** `PROACTIVE_ENABLE=1` reads as *false*; several flags accept only the literal `true`. Use `true`/`false`.
- **`TZ_OFFSET_HOURS` defaults to 8 (UTC+8)**, and drives a 02:00–07:00 window in which the bot mostly stays quiet. If you're not in that timezone, set it, or it will go silent at odd hours.
- **Coming from 0.1.x?** `DEEPSEEK_API_KEY` / `_BASE_URL` / `_MODEL` were renamed to `LLM_*` in 0.2.0 and the old names are **not** read.

## Running it day to day

These use the venv's Python — prefix with `.venv/bin/python` (or `.venv\Scripts\python.exe` on Windows) unless you have activated it.

```bash
curl http://127.0.0.1:8080/health                     # liveness; free, no model call
.venv/bin/python tools/healthcheck.py                 # full diagnostic — config, ledger sizes, then live probes
.venv/bin/python tools/candidates_admin.py list       # what it is proposing to learn
.venv/bin/python -m pip install -e ".[dev]"           # pytest is not a runtime dependency
.venv/bin/python -m pytest -q                         # the regression suite; offline, free, no API key
```

`tools/healthcheck.py` is the one to run after any config change — its first section is the same preflight that runs at startup and costs nothing. Its later probes **do spend credits**, as does `GET /health/details` (cached 60 s), so don't point an uptime monitor at that one.

In any group chat the character is in, say its **name** followed by one of these — all four are free and never call a model:

| Say | Get |
|---|---|
| `Nova what have you learned` | This conversation's memory count, what's shaping replies now, what's waiting for a second signal. |
| `Nova what do you remember` | The notes it holds here. |
| `Nova remember <fact>` | Stores one note. Instruction-shaped text is refused. |
| `Nova forget <text>` | Deletes matching notes. Unless you're the owner, only notes you saved yourself. |

The name has to be in the message text — an @-mention alone isn't enough. Chinese phrasings (`学到了什么`, `记得什么`, `记住…`, `忘了…`) work in an English deployment too. These are group-chat only.

**Back up `runtime/` together with `.env`, `persona.txt` and `persona.card.json`** — the persona files live at the deployment root, not inside `runtime/`. All of it is gitignored, so none of it is in any repo backup, and a restore without `.env` is a bot with no API key.

<details>
<summary><b>If it starts cleanly and never answers</b></summary>

In rough order of likelihood:

1. **The plugin's allowlists are still empty.** It forwards nothing and logs nothing. Check AstrBot's WebUI first.
2. **On QQ: `aiocqhttp` is still in the plugin's `excluded_platforms`.** Messages are dropped before the allowlists are read.
3. **`BOT_QQ` is unset**, so no @-mention registers on any platform.
4. **A misspelled setting**, or a **UTF-8 BOM on `.env`** — which attaches itself to the first key's name and looks perfectly fine in every editor. `tools/healthcheck.py` catches both.
5. **Token mismatch, clock skew, or a proxy rewriting the body** — all three look identical: a 403 on every gateway request.
6. **Nobody addressed it.** An un-addressed room needs ~30 messages (about 10 the first time) before it considers speaking on its own.
7. **`BOT_NAME` or `PERSONA_VERSION` changed**, so everything the old character learned is now refused.

The full checklist, including how to test each direction on its own, is in [the deployment guide](docs/deploy.md#when-the-bot-goes-quiet).

</details>

## What to expect

**Cost.** Every reply is at least one model call, and often two — self-initiated replies get a cheap PASS-or-reply check first. On top of that: one call per reaction while `REACT_LEARN` is on, one per image if vision is configured, one per web search. A cheap model for the gate and an expensive one for the writing is the intended setup.

**Maturity.** Version 0.3.0, beta, one author, MIT. The test suite is real — ~1,000 assertions across 17 suites, fully offline, costing nothing — and CI runs it on Linux across Python 3.10–3.12 and on Windows on 3.12. There is no macOS job and 3.13 is untested. `main` usually runs ahead of the latest tagged release.

**Platforms.** QQ is the one that is actually deployed and tested. Everything else reaches the bot through AstrBot and shares the same pipeline, but no platform is integration-tested end to end. On any forwarded platform the bot cannot speak first — it can only answer.

**Experimental parts.** `tools/dspy_tune.py` says "SCAFFOLD ONLY" in its own docstring. `tools/evolution_benchmark.py` runs on 64 synthetic English scenarios and states plainly that its numbers do not measure how much a real deployment learns on its own. The papers under Acknowledgements are influences, not validation of this implementation.

## Responsible use

Read [DISCLAIMER.md](DISCLAIMER.md) before pointing this at QQ. The short version:

- **QQ protocol clients are not sanctioned by Tencent**, and running one can get the account frozen, restricted or **permanently banned** — far more aggressively from a cloud or overseas IP. Use a throwaway account, not your own, and run it from a residential connection.
- **Tell people it's a bot.** Tag the account clearly. Don't deploy it where its behaviour would mislead someone, and don't impersonate a real person without their consent.
- **Get consent before processing other people's messages.** `runtime/` ends up holding verbatim quotes of real conversations, and the logs are append-only by design.
- **Your provider sees the chat context** in every request, and some train on it unless you opt out.

## Documentation

- [Deployment guide](docs/deploy.md) — the load-bearing details, and the full "bot goes quiet" checklist
- [AstrBot forwarder plugin](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md)
- [Configuration reference](.env.example) — all 91 settings, annotated
- [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Disclaimer](DISCLAIMER.md)

## License

[MIT](LICENSE) © 2026 Qiankang Wang.

## Acknowledgements

Built on the [OneBot v11](https://github.com/botuniverse/onebot-11) event model, [NapCat](https://github.com/NapNeko/NapCatQQ), [AstrBot](https://github.com/AstrBotDevs/AstrBot), [FastAPI](https://github.com/fastapi/fastapi) and [httpx](https://github.com/encode/httpx), with ideas from [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) and [BlenderBot 3x](https://arxiv.org/abs/2306.04707). The lorebook and output-filter model follows SillyTavern's World Info and regex extensions.
