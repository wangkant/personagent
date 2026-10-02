# Deploying personagent

[中文：从零部署到 QQ 群（NapCat + AstrBot + personagent）](deploy.zh-CN.md)

The README gets you to a first chat. This guide covers what a live deployment
needs, and what to check when the bot goes quiet.

## Install and the home folder

| You want | Run |
|---|---|
| To see it with nothing configured | `uvx personagent demo` |
| To set it up and chat | `uvx personagent init`, then `uvx personagent chat` |
| A permanent command | `uv tool install personagent` or `pipx install personagent`, then `personagent init` |
| To install into a venv | `pip install personagent` |
| To work from a clone | `git clone https://github.com/wangkant/personagent.git`, `cd personagent`, `python quickstart.py` |

uv fetches a suitable Python by itself. To install uv: macOS and Linux
`curl -LsSf https://astral.sh/uv/install.sh | sh`; Windows
`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
Python 3.10 to 3.14 work. With no Git, download the repository ZIP from GitHub;
it unpacks to `personagent-main`.

Everything personagent keeps lives in one **home folder**: `.env` (settings),
`persona.txt`, and `runtime/` (what it remembers and learned). The home is:

1. the folder `AGENT_HOME` names, or `--home DIR` (it goes before the command:
   `personagent --home D:\bot run`);
2. else the clone, when you run from one;
3. else the current folder, if it holds both `.env` and `persona.txt`;
4. else `~/personagent`, which `personagent init` creates.

To run several personas from one install, give each its own home.

## The shortest config that works

For `personagent chat`, one setting in `.env` (`personagent init` writes it):

```
LLM_API_KEY=...
```

`LLM_BASE_URL` and `LLM_MODEL` default to `https://api.deepseek.com` and
`deepseek-flash`. Point them at any OpenAI-compatible endpoint, hosted or
local (Ollama, llama.cpp); the API address can be pasted the way the provider
documents it, a root or a version base such as `.../v1` or `.../api/paas/v4`.
Until you write a `persona.txt`, the bundled `data/persona.example.<lang>.txt`
stands in.

To run live behind AstrBot:

```
LLM_API_KEY=...
PERSONA_NAME=...                     # the name it answers to
CONNECTOR_TOKEN=...                  # shared with the plugin; recommended, required across hosts
ADMIN_IDS=telegram:12345             # optional: the admin's accounts, <platform>:<id>
# QQ only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

`personagent connect astrbot` writes the connector lines for you. Everything
else in `.env.example` has a working default: `SERVER_HOST` and `SERVER_PORT`
are `127.0.0.1:8080`, `QQ_ONEBOT_URL` is blank (no NapCat HTTP server), and an
empty `ACCESS_GROUPS` leaves every group to the plugin's allowlist.

## Running it

```
personagent run                  # from a clone: start.bat, start.ps1, start.sh, or .venv/bin/python main.py
```

It prints a short banner: the version, the address, the home folder, the
dashboard address, and whether the agent is on (with the model and language) or
`OFF` with the reason. Keep it running; the connectors talk to it. `--host` and
`--port` override `SERVER_HOST` and `SERVER_PORT`.

From a clone, `start.bat` (double-click on Windows), `start.ps1` and `start.sh`
do the same. If there is no `.env` yet, they run the setup wizard first.

`personagent doctor` checks the setup and every upstream service
(`--json` for a script). `tools/healthcheck.py` still works and is the same
command. It reports missing and **misspelled** settings (a typo is otherwise
silent: the default is used), then probes each service. Startup logs the same
settings check.

Open `http://127.0.0.1:8080/` (your `SERVER_PORT`) for the dashboard: whether
messages arrive, which connectors are pulling, why it spoke or stayed quiet in
each chat, what it learned with the evidence behind it, and promote / reject /
roll back buttons. It needs no extra install. It answers only this machine:
a request from another host, through a proxy or tunnel, or carrying an
`Origin` from another site is refused, unless it carries the
`X-Personagent-Token` header with `CONNECTOR_TOKEN`. To see it from another
computer, use an SSH tunnel (`ssh -L 8080:127.0.0.1:8080 host`), or a reverse
proxy that adds the header. `DASHBOARD_ENABLED=false` removes the page and its
API. It never shows keys or tokens.

## What the host must provide

1. **A writable home.** Startup takes a lock at
   `<home>/.personagent.instance.lock`, outside `runtime/`. A read-only home
   fails to start.
2. **One process per home.** The lock stops two copies from corrupting each
   other's ledgers; a second `personagent run` exits with one sentence saying
   so.
3. **A free port.** A taken or forbidden port also exits with one sentence;
   pick another with `--port` or `SERVER_PORT`.

`AGENT_RUNTIME_DIR` must resolve beneath the home, or startup fails. A relative
`PERSONA_FILE` or `PERSONA_CARD_FILE` resolves under it too, so a persona kept
elsewhere needs an absolute path.

Seed data (examples, lorebook, output filters) comes from `<home>/data/` first,
then from the copy shipped with the package. To change one, put a file of the
same name under `<home>/data/`.

## Connectors

personagent never logs in to a chat platform. A connector does: it turns each
message into a neutral event, posts it to `POST /v1/events`, and sends
the replies that come back. Three ship in this repository:

| Connector | Reaches | Guide |
|---|---|---|
| AstrBot plugin | every AstrBot adapter: QQ, Telegram, Discord, Slack, KOOK, Lark, DingTalk, LINE, WeCom, Mattermost, Misskey, WeChat official accounts, ... | [below](#connecting-through-astrbot) |
| Satori | every Satori server (Koishi and others): Telegram, Discord, KOOK, Lark, DingTalk, LINE, QQ, ... | [integrations/satori](../integrations/satori/README.md) |
| Matrix | Matrix rooms, and through mautrix bridges WhatsApp, Signal, Messenger, Instagram, Google Messages, ... | [integrations/matrix](../integrations/matrix/README.md) |

For anything else, the [connector protocol](connectors.md) is one signed HTTP
request per message plus an optional outbox, and
`integrations/sdk/personagent_connector.py` is its client side in Python.

Connectors can run side by side against one personagent. Each names its
platform, so ids never collide (`telegram:-1001234`, `matrix:!room:example.org`).
Do not bring one chat in through two connectors, or every message arrives
twice.

## Connecting through AstrBot

AstrBot logs in to the platforms, and the plugin in
`integrations/astrbot/astrbot_plugin_personagent/` posts each message to
`POST /v1/events` and relays the replies in the response. It reaches
the most platforms, and it is the one `personagent init` sets up. It also pulls
personagent's outbox (`outbox_enabled`, on by default), so the persona can
speak first wherever the platform lets a bot do that; the plugin README has
the table.

Start AstrBot once so it creates its data folder (the one holding
`cmd_config.json`, `plugins/` and `config/`), then:

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

It copies the plugin into `<data dir>/plugins/`, writes one `CONNECTOR_TOKEN`
to both `.env` and the plugin config, and sets `personagent_url` to
`http://127.0.0.1:<SERVER_PORT>` unless the plugin already has one it accepts
(a loopback URL, tunnels included, or HTTPS). `--qq` takes `aiocqhttp` out of
`excluded_platforms`; `--no-qq` puts it back; with neither, QQ routing stays as
it is, and `CONNECTOR_QQ_PLATFORMS` follows whichever the plugin ends up
doing. `--platform telegram|discord|slack|kook|lark --token <token>` also
switches that adapter on in AstrBot's own config, and `--url https://...` sets
an HTTPS address for the plugin to post to. The first run leaves the
allowlists empty; rerunning keeps them, and any other excluded platforms.
`personagent init` offers the same step at its end, and `python quickstart.py
--astrbot <dir>` still works in a clone.

The plugin is default-deny: fill in `groups`, and for DMs `dm_users`, in
AstrBot's WebUI (or answer the questions in `connect`); DMs are forwarded once
`dm_users` is not empty (every key is in the
[plugin README](../integrations/astrbot/astrbot_plugin_personagent/README.md)).
Restart AstrBot, or reload plugins in its WebUI, after the plugin is installed.
On the personagent side:

- `CONNECTOR_TOKEN` authenticates each request: the `X-Personagent-Token`
  header plus an HMAC-SHA256 keyed with the token over `timestamp.nonce.body`,
  with a replay guard. A captured request cannot be replayed or altered, but the
  token is also the signing key: keep it out of logs and rotate it if it
  leaks. Optional on one host, required across hosts.
- `ADMIN_IDS` lists the admin's accounts as `<platform>:<id>`
  (`telegram:12345`, `discord:4242`; a bare id or `qq:<id>` is a QQ number),
  and `ADMIN_NAME` their name.
  One person on every platform listed: they get the closer persona in groups
  and DMs, may manage what the bot remembers about a group, and may teach it
  on their own. The platform is the adapter name AstrBot shows, and
  `/sid` in a chat shows an id.
- `ACCESS_GROUPS` and `ACCESS_DM_USERS` let personagent gate a platform
  itself, in the same `<platform>:<id>` form. Each platform is gated on its
  own: one with no entries is left to the plugin's allowlists, and one entry
  restricts that platform to its entries. A turn personagent refuses goes
  back unclaimed, so AstrBot's own model may answer it.

### AstrBot in Docker

Inside a container, `127.0.0.1` is the container itself, and the plugin refuses
plain `http://` to any other address. Either give AstrBot host networking
(`network_mode: host` in its compose file, or `docker run --network host`;
Docker Desktop needs 4.34 or later with host networking enabled), or put
personagent behind HTTPS and pass that address with `--url`. A NapCat container
in the same compose file needs the same treatment, and its WebSocket address
becomes `ws://127.0.0.1:6199/ws`.

## QQ through AstrBot

You need a second QQ account (not your own; see
[DISCLAIMER.md](../DISCLAIMER.md)) in the target groups, logged in (usually
by QR code, in a session that survives restarts) to a OneBot v11
implementation connected to AstrBot's `aiocqhttp` adapter:
[NapCat](https://github.com/NapNeko/NapCatQQ) (tested; it attaches to the
QQ NT desktop client), LLOneBot or Lagrange. The step by step, in Chinese, is
[deploy.zh-CN.md](deploy.zh-CN.md).
Then remove `aiocqhttp` from the plugin's `excluded_platforms`, set
`CONNECTOR_QQ_PLATFORMS=aiocqhttp` (`--qq` does both), and set `QQ_BOT_ID`
(`personagent connect astrbot` asks for it).

**`CONNECTOR_QQ_PLATFORMS` is not optional.** Without it, QQ ids arrive
namespaced (`aiocqhttp:123456`) and every conversation looks new. Memory,
history and learned examples are keyed by the bare id, and the ledgers derive
row ids from the conversation id, so the split cannot be repaired afterwards.

Bare ids carry QQ authority, so the QQ entries of `ADMIN_IDS`,
`ACCESS_GROUPS` and `ACCESS_DM_USERS` apply on top of the plugin's
allowlists: a QQ DM must be in `dm_users` *and* come from the admin or
an `ACCESS_DM_USERS` entry, and when `ACCESS_GROUPS` lists QQ groups, a QQ
group must be in both. Only list a platform in `CONNECTOR_QQ_PLATFORMS` if
you trust its connector with that authority.

**NapCat's HTTP server** (`QQ_ONEBOT_URL`, blank by default) is optional on
this path. What personagent starts itself (proactive messages, off by default
with `PROACTIVE_ENABLED`; the question asked two minutes after a rejection,
`REACT_ELICIT_ENABLED`; the excuse sent when the model call fails) goes back
through the plugin's outbox while the plugin is pulling it, and to
`QQ_ONEBOT_URL` when it is not and the URL is set. Only the sweep for
@-mentions missed while offline needs the server (and `QQ_BOT_ID`): it runs at
startup and then every 30 minutes, covers the QQ groups in `ACCESS_GROUPS`
plus any group with traffic since the last restart, and replays @-mentions
under an hour old. With the URL blank, `personagent doctor` shows the OneBot
bridge as "not configured", not as a failure.

**Lost on this path**, with no setting to bring it back:

- the OCR fallback for images that no vision model described;
- quote lookup through NapCat. Quotes resolve from personagent's own index of
  recent messages, and from the quoted text a connector sends with the quote;
- collecting new stickers from images posted in groups.

## More than one platform

Telegram, Discord, Slack, KOOK, Lark and the other AstrBot platforms connect
the same way (`personagent connect astrbot <dir> --platform <kind> --token
<token>` switches one of the first five on in AstrBot's config). Their
ids are namespaced as `<platform>:<id>`, so they never collide with a QQ
number. The connector's allowlists are their filter until `ACCESS_GROUPS` or
`ACCESS_DM_USERS` lists an entry for that platform.

Messages nobody asked for (proactive openers, the question asked after a
rejection, the excuse when the model call fails) reach a platform through a
connector that pulls personagent's outbox. All three connectors here do, on
platforms where a bot may send first; a connector of your own sends
`connector_id`, `reply_handle` and `"capabilities": ["outbox"]` with its
events and long-polls `/v1/outbox` (see [the connector protocol](connectors.md)).
Without one, personagent speaks only inside the request that brought a
message: the proactive loops skip those conversations, and the question and
the excuse are not sent. `PROACTIVE_PLATFORMS` limits where the proactive loop
may speak first (`PROACTIVE_PLATFORMS=qq` keeps it on QQ), and
`CONNECTOR_OUTBOX_ENABLED=false` turns the outbox off altogether.

**To speak first in a DM without the outbox**, have your own scheduler (an
AstrBot plugin task, a cron entry) post an ordinary DM event with
`"proactive": true` to `/v1/events` (schema in
[the connector protocol](connectors.md)). Its text is a cue to the persona
("they have been quiet a day; their exam was this morning"), not the other
person's words, cut at 500 characters. The engine's proactive
instructions still decide the turn and may keep the persona silent; if it
speaks, the reply comes back in the response for the scheduler to relay.
The request needs what the plugin's requests carry: the signed headers, every
required field, the same platform name and raw sender id the plugin sends,
non-empty text, and a fresh `message_id` each time (a repeated one is dropped
without a word). It counts against the same DM cooldown
(`PROACTIVE_DM_COOLDOWN_S`) as the agent's own openers.

Always set the flag. Without it, the cue is stored as the other person's
words: it stays in the DM history for the next 40 messages, can be quoted back
at them, and can be saved as a memory about them. A group event marked
`"proactive"` is claimed (`owned: true`, so the connector keeps its own model
quiet) and dropped unread.

## Exposing the endpoints

Keep `SERVER_HOST=127.0.0.1` when the connector and personagent share a machine (a
container counts only with the host's network namespace or host networking).
Otherwise:

1. Set `SERVER_HOST=0.0.0.0` (or `--host 0.0.0.0`) and `CONNECTOR_TOKEN`.
   Startup refuses a network bind without the token. `QQ_ONEBOT_SECRET` is
   needed only when a NapCat on another machine must reach the deprecated
   `/v1/onebot`; without it that route answers only programs on this host.
2. Put an HTTPS reverse proxy or a private tunnel in front. Every connector
   here posts only to loopback, or to HTTPS with a token set; the AstrBot
   plugin logs anything else as `refusing unsafe personagent_url`, and the
   Satori and Matrix connectors refuse to start.
3. Keep the body byte-for-byte intact (the signature covers it) and the
   clocks within five minutes.

With a credential blank, its endpoint serves only local programs calling
`http://127.0.0.1` or `http://localhost` directly. A request with `Origin`, a
`Sec-Fetch-Site` other than
`none`, a `Host` other than `localhost`, `127.0.0.1` or `::1`, or a proxy
header (`X-Forwarded-For`, `Forwarded`, `X-Real-IP`, `CF-Connecting-IP`) gets
403 `non_local_request`. So set the credential before adding a tunnel, even
on one host.

## Health endpoints

- `GET /health` is free, open, and calls nothing.
- `GET /health/details` probes the upstream services (cached 60 s). With
  `CONNECTOR_TOKEN` blank it answers local requests only; with a token, **only**
  requests carrying a matching `X-Personagent-Token` header, even from
  loopback.
  It returns 503 when a critical probe fails or cannot run: the chat models,
  or the OneBot bridge when `QQ_BOT_ID` is set, `QQ_ONEBOT_URL` is set and
  `CONNECTOR_QQ_PLATFORMS` is not (QQ on the direct ingress).
- `personagent doctor [--json]` runs the same probes plus the settings check,
  and exits non-zero in the same case.

## Costs

- **Probes spend credit.** `personagent doctor` and `/health/details` send one
  tiny chat completion to each configured model endpoint (chat, DM, eval and
  vision), one embedding if `EMBEDDING_MODEL` is set, plus one Tavily search
  if `TAVILY_API_KEY` is set. `/health`
  and the settings and ledger checks are free.
- **The scripts in `tools/`** differ: some are free, some call a model. The
  table in [tools.md](tools.md) says which.
- **`personagent eval`** calls the model for every case; the persona and
  learning suites also need a second model as judge (`BENCH_JUDGE_MODEL`).
- **Memory.** Past 256 namespaced (non-QQ) conversations, the least recently
  active idle one loses its recent history and pending reactions; long-term
  memories, core notes and ledgers stay. A conversation mid-request is never
  evicted. Long-term memories are loaded from disk at startup and are not
  bounded by this cap.
- **Disk.** The evidence log and candidate ledger in `runtime/` are
  append-only and never truncated; `personagent doctor` flags either past 50 MB
  (`LEDGER_EVIDENCE_WARN_BYTES`, `LEDGER_CANDIDATES_WARN_BYTES`). Back up
  `runtime/`: it holds everything the bot has learned.

## When the bot goes quiet

Most common first. The dashboard (`http://127.0.0.1:8080/`) shows most of
these at a glance.

1. **The connector forwards nothing.** In the AstrBot plugin, fill in
   `groups` (and `dm_users` for DMs), and on QQ take `aiocqhttp` out of
   `excluded_platforms`. The Satori and Matrix connectors have their
   own allowlists in their `.env`; see their READMEs. The dashboard says
   "nothing has arrived" when this is the case.
2. **The agent is off.** The banner at `personagent run` says `agent: OFF` and
   why: `LLM_API_KEY` is not set (check `<home>/.env`, or run
   `personagent init`) or `AGENT_ENABLED=false`. Every event then gets
   `owned: false`, and the first one logs a single ERROR line naming the cause.
3. **AstrBot's own model answers instead.** The request failed, or
   personagent turned the message away (item 5), or the agent is off (item 2),
   and the plugin fell back.
   AstrBot's log shows `refusing unsafe personagent_url`, `agent refused the
   request (403): <message>` (or another status; see the table below), or
   `timed out waiting for the agent`. `timeout_s` (default 180) must cover the debounce
   and every model call in the turn: keep `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`
   under it. The defaults (120 × 3 = 360 s) do not.
4. **It was not called.** In a group it answers its name (`PERSONA_NAME`) or an
   @. Otherwise it waits for enough conversation (`CHAT_TRIGGER_COUNT`, 30
   messages by default) and may still pass; from 02:00 to 07:00 in its time
   zone (`PERSONA_TZ_OFFSET_HOURS`, this machine's by default) it mostly
   stays out of chats it was not called into. The dashboard shows the reason for each recent turn. To watch
   the same decision offline, `personagent chat --trigger 4`.
5. **personagent's allowlists.** `ACCESS_GROUPS` and `ACCESS_DM_USERS`
   (and a QQ DM needs the admin or an entry) apply behind AstrBot too. A
   message they turn away goes back unclaimed, so AstrBot's own model answers
   it; personagent logs each refused conversation once, at INFO, with the
   setting that refused it, and the dashboard lists them.
6. **The model call fails.** A rejected key (401 or 403) or an empty balance
   (402 or an exhausted quota) logs one ERROR line naming the provider host and
   the setting to fix. Run `personagent doctor`: it sends a tiny request to
   each model endpoint and shows the status, which also catches a wrong
   `LLM_BASE_URL` or `LLM_MODEL`. While the model
   is down the persona sends a short in-character excuse, at most once per
   conversation every five minutes.
7. **A misspelled setting.** Silent by construction. The startup log and
   `personagent doctor` list every key `.env.example` does not know, and any
   value that starts with `#`.
8. **A BOM on `.env`.** The first setting's name carries it and never reaches
   the process, though the file looks fine in every editor. Startup and
   `personagent doctor` report it; re-save as UTF-8 without a BOM.
9. **`QQ_BOT_ID` unset or wrong on QQ.** Through AstrBot, @-mentions still work
   but the missed-mention sweep matches on it. On the direct ingress an
   @-mention is never recognised: the bot starts cleanly, logs nothing, and
   never answers one. `personagent doctor` warns when `QQ_BOT_ID` is empty and
   other QQ settings are set.
10. **It answers, but has forgotten what it learned.** QQ is arriving without
    `CONNECTOR_QQ_PLATFORMS=aiocqhttp`, or `PERSONA_NAME` or `PERSONA_VERSION`
    changed, which starts a new character; the log warns when the old one's
    promoted material is refused whole. Editing `persona.txt` does not: its
    revisions under one `PERSONA_VERSION` share a learning scope
    (`runtime/persona_lineage.json`). To fold in rows learned under a persona
    hash the lineage does not list, run `personagent learned lineage adopt
    <hash>` (the hash is in the candidate's scope in `personagent learned show
    <id>`), then `personagent learned rebuild`. Changing `AGENT_LANG` also
    switches to that language's learned files in `runtime/`.

Errors from `/v1/events`. The plugin logs the message; `code` is the
stable field a client can branch on.

| Status | `code` | Message in AstrBot's log | Cause |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | no `CONNECTOR_TOKEN`, and the caller is not on this machine |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | no `CONNECTOR_TOKEN`; sent through a browser, a proxy or another host name |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | missing or wrong token, headers or signature; clocks over 5 min apart; a reused nonce; or a full replay guard (`connector replay guard full` in the agent's log) |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` differs from now by more than `CONNECTOR_MAX_EVENT_AGE_S` (24 h), including future or millisecond timestamps |
| 400 | `invalid_schema` | invalid event schema | a required field is missing: `platform`, `conversation_type`, `sender_id`, `message_id`, `sent_at`, and `conversation_id` for groups |
| 400 | `client_disconnected` | client disconnected | the caller hung up while sending |
| 408 | `body_timeout` | request body not received in time | the body took more than 30 s to arrive |
| 413 | `body_too_large` | request body too large | over `SERVER_MAX_BODY_BYTES` (8 MB), usually an inline image |
| 429 | `capacity_exceeded` | webhook capacity exceeded | over `CONNECTOR_MAX_INFLIGHT` turns in flight; retry after 3 s |

## Legacy: the direct OneBot ingress

NapCat's webhook can still post events to `POST /v1/onebot`, and personagent
replies through `QQ_ONEBOT_URL`. The supported QQ route is AstrBot with
`CONNECTOR_QQ_PLATFORMS=aiocqhttp`; this one is deprecated and stays through
1.x. It warns once at first use and marks every response `Deprecation: true`.
`launch.vbs`, which starts NapCat and then `main.py` on Windows, is deprecated
with it.

To move over, connect NapCat to AstrBot's `aiocqhttp` adapter, run
`personagent connect astrbot <AstrBot data dir> --qq`, fill in the
allowlists, and turn off NapCat's HTTP client (keep its HTTP server). Memory
and learning carry over, because `CONNECTOR_QQ_PLATFORMS` keeps the ids.

If you still run it:

- Set up both directions per [NapCat's documentation](https://napneko.github.io/)
  (the format changes between versions): an **HTTP server** at `QQ_ONEBOT_URL`
  for sending, and an **HTTP client** posting to
  `http://127.0.0.1:8080/v1/onebot` (`SERVER_HOST`, `SERVER_PORT`).
- Set `QQ_ONEBOT_SECRET` to the HTTP client's `secret` if NapCat is on another
  machine, or anyone who can reach the port can forge events. Bodies must then
  carry `x-signature: sha1=<hex>` (403 `bad_signature`), and events timestamped
  over five minutes off get 403 `stale_event`. Without the secret the route
  answers only programs on this host.
- With AstrBot on the same account, keep `aiocqhttp` in `excluded_platforms`,
  or every message arrives twice.

Check sending with `curl http://127.0.0.1:3000/get_login_info`, and receiving
by watching personagent's log while you message the bot in a group. A failure
in either direction looks the same from outside: a bot that runs and stays
silent.
