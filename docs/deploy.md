# Deploying personagent

[中文：部署、QQ 扫码直连和排查](deploy.zh-CN.md)

The [quick start](start.md) and the [user guide](guide.md) get you to a first
chat: installing, the [home folder](guide.md#install-and-the-home-folder),
setup on the local page and connecting a platform. This guide covers what a
live deployment needs, and what to check when the bot goes quiet.

## The shortest config that works

The local page (`personagent`, or `personagent init --terminal` for the
terminal wizard) checks the key with one small request, then writes `.env` in
the home folder. Chatting needs one setting:

```
LLM_API_KEY=...
```

`LLM_BASE_URL` and `LLM_MODEL` default to `https://api.deepseek.com` and
`deepseek-flash`. Point them at any OpenAI-compatible endpoint, hosted or
local (Ollama, llama.cpp); the API address can be pasted the way the provider
documents it, a root or a version base such as `.../v1` or `.../api/paas/v4`.
Until you write a `persona.txt`, the bundled `data/persona.example.<lang>.txt`
stands in, and until `PERSONA_NAME` is set (setup sets it), the character is
called "bot".

The page also writes `PERSONA_NAME`, `AGENT_LANG` and a `CONNECTOR_TOKEN`.
Platforms connected from the page need nothing more in `.env`; their
credentials go to `<home>/platforms/` (`direct.json` for the platforms
personagent connects itself, and the managed AstrBot's own config for the
rest). Optional additions:

```
ADMIN_IDS=telegram:12345             # the admin's accounts, <platform>:<id>
# QQ through NapCat (OneBot) only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

Keys stay on this machine; the model provider you choose sees the
conversations. Everything else in `.env.example` has a working default: `SERVER_HOST` and
`SERVER_PORT` are `127.0.0.1:8080`, `QQ_ONEBOT_URL` is blank (no NapCat HTTP
server), and an empty `ACCESS_GROUPS` leaves every group to the connector.

## Running it

`personagent` opens the local page, and while it is open it runs the agent,
the process that holds the directly connected platforms, and the managed
AstrBot when one is installed. Running `personagent` again reuses an open
page. `personagent up` starts the same processes without a browser. Either
way, those processes end with it however it ends (a job object on Windows, a
process group elsewhere), and whatever an earlier crashed run left behind is
stopped at the next start. Each writes its log to `<home>/runtime/desktop/`
(`agent.log`, `direct.log`, `astrbot.log`).

`personagent run` starts the agent alone, as [Run the service](guide.md#run-the-service)
describes: use it when your own connectors (an AstrBot you run, Satori,
Matrix) talk to it. `personagent doctor` checks the settings and probes every
upstream service.

**Settings renamed in 1.0.** A start refuses, with exit code 2, while any
setting name that 1.0 retired is still set, and lists each as `OLD -> NEW`.
`personagent doctor --fix` renames them in `<home>/.env`: it keeps the values
and comments, saves the old file as `.env.bak`, and comments out an old line
whose new name is already set. A retired name set in the environment rather
than `.env` must be renamed where it is set. `personagent doctor` exits 1
while any remain, and `--json` lists them under `retired_settings`. `HOST`,
`PORT` and `LOG_FILE` count only when they are written in `.env`.

### The dashboard

[The dashboard](guide.md#the-dashboard) needs no extra install, loads nothing
from the internet and never shows keys or tokens. `DASHBOARD_ENABLED=false`
removes the page and its API.

It opens only through its private link,
`http://127.0.0.1:<SERVER_PORT>/?token=<token>`, which the startup banner and
`personagent doctor` print (`doctor --json` gives it as `dashboard`). The
token lives in `dashboard.token` in the runtime folder (`<home>/runtime/`
unless `AGENT_RUNTIME_DIR` moves it), readable only by the owner;
it is created at first start and kept across restarts. Delete the file and
restart to issue a new one, which signs every browser out.

- Opening the link sets an HttpOnly, `SameSite=Strict` cookie that lasts a
  year, then redirects to the page without the token in the address bar.
  Scripts can send the header `X-Personagent-Dashboard-Token` instead.
- Without the token every page, data and action request gets 401
  (`dashboard_token`), and the page says where to find the link; a wrong token
  gets 403 (`wrong_token`). `CONNECTOR_TOKEN` and `X-Personagent-Token` do not
  open it: they are for connectors and `/health/details` only.
- A browser must name `localhost`, an IP address or `SERVER_HOST` as the host;
  any other host name gets 403 (`foreign_host`), which stops DNS rebinding.
- From another computer, use an SSH tunnel to `127.0.0.1`
  (`ssh -L 8080:127.0.0.1:8080 <host>`, then open the link), or set
  `SERVER_HOST` to this machine's LAN or Tailscale address (with
  `CONNECTOR_TOKEN`, as any network bind needs) and open the link the banner
  prints, which uses that address.

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

## Connecting platforms

Platforms are added under **Connect apps** on the local page. Credentials are
checked against the platform before anything is saved; a refusal is shown and
nothing is kept.

**Connected by personagent itself.** QQ, personal WeChat, Telegram and
Discord run in one "direct" process, with no AstrBot and no NapCat:

| Platform | What you do | Limits |
|---|---|---|
| QQ (official bot) | scan a QR code with mobile QQ, which creates a bot or picks one you made; pasting AppID and AppSecret is the fallback | until the bot is certified, QQ lets it join only groups you own; group message permissions are set in QQ |
| Personal WeChat | scan with WeChat (Tencent's iLink bot API) | one-to-one chats only: WeChat gives such bots no group messages |
| Telegram | paste the token from @BotFather | |
| Discord | paste the bot token, with Message Content Intent on | |

**Through the managed AstrBot.** Every other platform goes through an AstrBot
that personagent downloads (with its own Python 3.12 runtime) and runs
headless: no dashboard and no second login. KOOK, Feishu/Lark (long
connection), DingTalk (Stream mode), Slack (Socket Mode; the guide link
pre-fills the app), WeCom AI bot (long connection), Mattermost and Misskey ask
for one or two values. The advanced group needs a public address or other
software: WeCom app, WeChat Official Account, QQ webhook, OneBot v11 (NapCat)
and Satori. LINE is not offered.

On both paths a connected platform answers every group and DM the platform
delivers to the bot, until `ACCESS_GROUPS` or `ACCESS_DM_USERS` lists an entry
for that platform (see [personagent's own allowlists](#through-an-astrbot-you-already-run)).
Ids arrive as `<platform>:<id>`: `qq_official:<openid>`, `weixin_oc:<id>`,
`telegram:<id>`, `discord:<id>`. The official QQ bot sees openids, not QQ
numbers. Connecting a platform directly removes an AstrBot connection of the
same platform, so one bot is never served twice.

## Through an AstrBot you already run

AstrBot, NapCat (OneBot), Koishi (through the [Satori connector](../integrations/satori/README.md))
and Matrix (through the [Matrix connector](../integrations/matrix/README.md)
and mautrix bridges) are third-party bridges personagent works with. None of
them is needed for QQ, WeChat, Telegram or Discord.

AstrBot hands messages to personagent through a plugin in
`integrations/astrbot/astrbot_plugin_personagent/`: it posts each message to
`POST /v1/events`, relays the replies in the response, and pulls
personagent's outbox (`outbox_enabled`, on by default), so the persona can
speak first wherever the platform lets a bot do that; the plugin README has
the table. The managed AstrBot gets the plugin automatically. For your own
AstrBot, start it once so it creates its data folder (the one holding
`cmd_config.json`, `plugins/` and `config/`), then:

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

It copies the plugin into `<data dir>/plugins/`, writes one `CONNECTOR_TOKEN`
to both `.env` and the plugin config, and sets `personagent_url` to
`http://127.0.0.1:<SERVER_PORT>` unless the plugin already has one it accepts
(a loopback URL, tunnels included, or HTTPS). For an AstrBot on another
machine, download `astrbot_plugin_personagent.zip` from the
[latest release](https://github.com/wangkant/personagent/releases/latest),
upload it under **Install from File** on AstrBot's plugin page, set its
`connector_token` to the `CONNECTOR_TOKEN` in personagent's `.env`, and set
`personagent_url` to an HTTPS address for personagent (see
[Exposing the endpoints](#exposing-the-endpoints)). After upgrading
personagent, rerun `connect astrbot` or upload the new zip. AstrBot 4.29 and
later replace the installed copy; on older versions, uninstall it first and
leave **Also delete plugin configuration file** unticked.

`--qq` takes `aiocqhttp` out of `excluded_platforms`; `--no-qq` puts it back;
with neither, QQ routing stays as it is, and `CONNECTOR_QQ_PLATFORMS` follows
whichever the plugin ends up doing. `--platform
qq_official|telegram|discord|slack|kook|lark --token <token>` also switches
that adapter on in AstrBot's own config (Slack also takes `--app-token`, Lark
and QQ `--app-id` and `--app-secret`); an adapter entry that already exists
keeps its other settings (proxy, base URL, polling) and gets only the new
credentials. `--url https://...` sets an HTTPS address for the plugin to post
to. The first run leaves the allowlists empty; rerunning keeps them, and any
other excluded platforms. `--install` downloads a managed AstrBot instead and
`--start` starts it; `python quickstart.py --astrbot <dir>` still works in a
clone.

The plugin is default-deny: fill in `groups`, and for DMs `dm_users`, in
AstrBot's WebUI (or answer the questions in `connect`); DMs are forwarded once
`dm_users` is not empty (every key is in the
[plugin README](../integrations/astrbot/astrbot_plugin_personagent/README.md)).
The managed AstrBot opens each platform you connect with `<platform>:*`.
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
  on their own. Through AstrBot the platform is the adapter name AstrBot
  shows, and `/sid` in a chat shows an id.
- `ACCESS_GROUPS` and `ACCESS_DM_USERS` let personagent gate a platform
  itself, in the same `<platform>:<id>` form. Each platform is gated on its
  own: one with no entries is left to the connector, and one entry
  restricts that platform to its entries. A turn personagent refuses goes
  back unclaimed, so AstrBot's own model may answer it.

AstrBot in Docker or on another host: see
[the user guide](guide.md#bridges-you-run-yourself).

### QQ through NapCat (OneBot)

For a personal QQ account instead of an official bot: a second QQ account (not
your own; see [DISCLAIMER.md](../DISCLAIMER.md)) in the target groups, logged
in (usually by QR code, in a session that survives restarts) to a OneBot v11
implementation connected to AstrBot's `aiocqhttp` adapter:
[NapCat](https://github.com/NapNeko/NapCatQQ) (tested; it attaches to the
QQ NT desktop client), LLOneBot or Lagrange. On the managed AstrBot, add
**Advanced > OneBot v11 (NapCat)** on the local page and point NapCat at
`ws://127.0.0.1:6199/ws`; the [Chinese guide](deploy.zh-CN.md) walks through
it. With your own AstrBot, remove `aiocqhttp` from the plugin's
`excluded_platforms`, set `CONNECTOR_QQ_PLATFORMS=aiocqhttp` (`--qq` does
both), and set `QQ_BOT_ID` (`personagent connect astrbot` asks for it).

**`CONNECTOR_QQ_PLATFORMS` is not optional here.** Without it, QQ ids arrive
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
`REACT_ELICIT_ENABLED`; the excuse sent in a group when the model call fails) goes back
through the plugin's outbox while the plugin is pulling it, and to
`QQ_ONEBOT_URL` when it is not and the URL is set. Only the sweep for
@-mentions missed while offline needs the server (and `QQ_BOT_ID`): it runs at
startup and then every 30 minutes, covers the QQ groups in `ACCESS_GROUPS`
plus any group with traffic since the last restart, and replays @-mentions
under an hour old. With the URL blank, `personagent doctor` shows the OneBot
bridge as "not configured", not as a failure.

**Lost on every connector path** (direct, AstrBot or another connector), with
no setting to bring it back:

- the OCR fallback for images that no vision model described;
- quote lookup through NapCat. Quotes resolve from personagent's own index of
  recent messages, and from the quoted text a connector sends with the quote;
- collecting new stickers from images posted in groups.

## More than one platform

Connectors can run side by side against one personagent, since each names its
platform (`telegram:-1001234`, `matrix:!room:example.org`): the direct
process, AstrBot, Satori and Matrix at once. Do not bring one chat in through
two connectors, or every message arrives twice. Namespaced ids never collide
with a bare QQ number.

Messages nobody asked for (proactive openers, the question asked after a
rejection, the excuse when the model call fails in a group) reach a platform
through a connector that pulls personagent's outbox. A DM's excuse goes back
in the response to the request that brought the message. The direct process
and the three connectors here all pull it, on platforms where a bot may send
first (QQ rate-limits an official bot's unprompted messages, and a person can
switch them off); a connector of your own sends `connector_id`,
`reply_handle` and `"capabilities": ["outbox"]` with its events and
long-polls `/v1/outbox` (see [the connector protocol](connectors.md)).
Without one, personagent speaks only inside the request that brought a
message: the proactive loops skip those conversations, and the question and
the excuse are not sent. `PROACTIVE_PLATFORMS` limits where the proactive loop
may speak first (`PROACTIVE_PLATFORMS=qq_official` keeps it on the official
QQ bot, `qq` on QQ through NapCat), and
`CONNECTOR_OUTBOX_ENABLED=false` turns the outbox off altogether.

To speak first in a DM without the outbox, your own scheduler (an AstrBot
plugin task, a cron entry) can post a DM event marked `"proactive": true`; see
[Speaking first without the outbox](connectors.md#speaking-first-without-the-outbox).

## Exposing the endpoints

Keep `SERVER_HOST=127.0.0.1` when the connector and personagent share a machine (a
container counts only with the host's network namespace or host networking).
The local page and `personagent up` always do. Otherwise:

1. Set `SERVER_HOST=0.0.0.0` (or `--host 0.0.0.0`) and `CONNECTOR_TOKEN`.
   Startup refuses a network bind without the token. It does not need
   `QQ_ONEBOT_SECRET`, but without it the deprecated `/v1/onebot` is off on a
   network bind: every request to it gets 403 `onebot_disabled`, and the log
   says why once.
2. Put an HTTPS reverse proxy or a private tunnel in front. Every connector
   here posts only to loopback, or to HTTPS with a token set; the AstrBot
   plugin logs anything else as `refusing unsafe personagent_url`, and the
   Satori and Matrix connectors refuse to start.
3. Keep the body byte-for-byte intact (the signature covers it) and the
   clocks within five minutes.

With a credential blank, its endpoint serves only local programs calling
`http://127.0.0.1` or `http://localhost` directly. A request with `Origin`, a
`Sec-Fetch-Site` other than `none`, a `Host` other than `localhost`,
`127.0.0.1` or `::1`, or a proxy header (`X-Forwarded-For`, `Forwarded`,
`X-Real-IP`, `CF-Connecting-IP`, `Via`, `X-Forwarded-Host`,
`X-Forwarded-Proto`, `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP`,
`X-Original-Forwarded-For`) gets 403 `non_local_request`. A proxy on the same
host that adds none of these still looks local, so set `CONNECTOR_TOKEN` (and
`QQ_ONEBOT_SECRET` if you use `/v1/onebot`) before you add any proxy or
tunnel, even on one host.

## Health endpoints

- `GET /health` is free, open, and calls nothing.
- `GET /health/details` probes the upstream services (cached 60 s). With
  `CONNECTOR_TOKEN` blank it answers local requests only; with a token, **only**
  requests carrying a matching `X-Personagent-Token` header, even from
  loopback.
  It returns 503 when a critical probe fails or cannot run: the chat models,
  or the OneBot bridge when `QQ_BOT_ID` is set, `QQ_ONEBOT_URL` is set and
  `CONNECTOR_QQ_PLATFORMS` is not (QQ on the direct OneBot ingress).
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

Most common first. The dashboard (open the link `personagent run` or
`personagent doctor` prints) shows most of these at a glance.

1. **Nothing reaches it.** On the local page, check the platform is listed as
   connected, and read `runtime/desktop/direct.log` or `astrbot.log`. The QQ
   official bot must be in the group, and QQ decides which group messages it
   receives; a personal WeChat bot never receives groups. In an AstrBot you
   run, fill in the plugin's `groups` (and `dm_users` for DMs), and for NapCat
   take `aiocqhttp` out of `excluded_platforms`. The Satori and Matrix
   connectors have their own allowlists in their `.env`; see their READMEs.
   The dashboard says "nothing has arrived" when this is the case.
2. **The agent is off.** The banner at `personagent run` says `agent: OFF`,
   why, and the fix: with no `LLM_API_KEY`, add a key on the local page (or
   set `LLM_API_KEY`) and restart; with `AGENT_ENABLED=false`, set it to
   `true` in `<home>/.env` and restart. Every event then gets `owned: false`,
   and the first one logs a single ERROR line with the same advice.
3. **AstrBot's own model answers instead.** The request failed, or
   personagent turned the message away (item 5), or the agent is off (item 2),
   and the plugin fell back.
   AstrBot's log shows `refusing unsafe personagent_url`, `agent refused the
   request (403): <message>` (or another status; see the table below), or
   `timed out waiting for the agent`. `timeout_s` must cover the debounce
   and every model call in the turn: keep `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`
   under it. Its default (420) covers the agent's defaults (120 × 3 = 360 s);
   raise it when you raise those two.
4. **It was not called.** In a group it answers its name (`PERSONA_NAME`) or an
   @. Otherwise it waits for enough conversation (`CHAT_TRIGGER_COUNT`, 30
   messages by default) and may still pass; from 02:00 to 07:00 in its time
   zone it mostly stays out of chats it was not called into. The time zone is
   `PERSONA_TZ_OFFSET_HOURS`; blank means UTC+8 when `AGENT_LANG=zh` and this
   machine's offset otherwise. The dashboard shows the reason for each recent
   turn. To watch the same decision offline, `personagent chat --trigger 4`.
5. **personagent's allowlists.** `ACCESS_GROUPS` and `ACCESS_DM_USERS`
   (and a bare-id QQ DM needs the admin or an entry) apply on every path. A
   message they turn away goes back unclaimed, so through AstrBot its own
   model may answer it; personagent logs each refused conversation once, at
   INFO, with the setting that refused it, and the dashboard lists them.
6. **The model call fails.** A rejected key (401 or 403) or an empty balance
   (402 or an exhausted quota) logs one ERROR line naming the provider host and
   the setting to fix. Run `personagent doctor`: it sends a tiny request to
   each model endpoint and shows the status, which also catches a wrong
   `LLM_BASE_URL` or `LLM_MODEL`. While the model
   is down the persona sends a short in-character excuse when it is called,
   at most once per conversation every five minutes. The five minutes count
   from an excuse that was delivered: when sending one fails, the next
   failure tries again.
7. **A misspelled setting.** Silent by construction. The startup log and
   `personagent doctor` list every key `.env.example` does not know, and any
   value that starts with `#`.
8. **A BOM on `.env`.** The first setting's name carries it and never reaches
   the process, though the file looks fine in every editor. Startup and
   `personagent doctor` report it; re-save as UTF-8 without a BOM.
9. **`QQ_BOT_ID` unset or wrong with NapCat.** Through AstrBot, @-mentions
   still work but the missed-mention sweep matches on it. On the direct
   OneBot ingress an @-mention is never recognised: the bot starts cleanly,
   logs nothing, and never answers one. `personagent doctor` warns when
   `QQ_BOT_ID` is empty and other QQ settings are set. The official QQ bot
   does not use it.
10. **It answers, but has forgotten what it learned.** NapCat QQ is arriving
    without `CONNECTOR_QQ_PLATFORMS=aiocqhttp`, or `PERSONA_NAME` or
    `PERSONA_VERSION` changed, which starts a new character; the log warns
    when the old one's promoted material is refused whole. Editing
    `persona.txt` does not (the page's Persona box included): its revisions
    under one `PERSONA_VERSION` share a learning scope
    (`runtime/persona_lineage.json`). To fold in rows learned under a persona
    hash the lineage does not list, run `personagent learned lineage adopt
    <hash>` (the hash is in the candidate's scope in `personagent learned show
    <id>`), then `personagent learned rebuild`. Changing `AGENT_LANG` also
    switches to that language's learned files in `runtime/`.

Errors from `/v1/events`. The AstrBot plugin logs the message; `code` is the
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
replies through `QQ_ONEBOT_URL`. This route is deprecated and stays through
1.x; use the official QQ bot connection, or NapCat through AstrBot with
`CONNECTOR_QQ_PLATFORMS=aiocqhttp`. It warns once at first use and marks
every response `Deprecation: true`. `launch.vbs`, which starts NapCat and then
`main.py` on Windows, is deprecated with it.

To move to NapCat through AstrBot, add OneBot v11 (NapCat) on the local page
(or run `personagent connect astrbot <AstrBot data dir> --qq` for your own
AstrBot and fill in the allowlists), point NapCat's WebSocket client at it,
and turn off NapCat's HTTP client (keep its HTTP server). Memory and learning
carry over, because `CONNECTOR_QQ_PLATFORMS` keeps the ids.

If you still run it:

- Set up both directions per [NapCat's documentation](https://napneko.github.io/)
  (the format changes between versions): an **HTTP server** at `QQ_ONEBOT_URL`
  for sending, and an **HTTP client** posting to
  `http://127.0.0.1:8080/v1/onebot` (`SERVER_HOST`, `SERVER_PORT`).
  `QQ_ONEBOT_URL` is blank by default, so write it in `.env`; without it the
  bot receives but never replies. Preflight and `personagent doctor` warn when
  this route looks configured (`QQ_BOT_ID` or `QQ_ONEBOT_SECRET` set,
  `CONNECTOR_QQ_PLATFORMS` empty) and `QQ_ONEBOT_URL` is blank.
- Set `QQ_ONEBOT_SECRET` to the HTTP client's `secret` if NapCat is on another
  machine, or anyone who can reach the port can forge events. Bodies must then
  carry `x-signature: sha1=<hex>` (403 `bad_signature`), and events timestamped
  over five minutes off get 403 `stale_event`. Without the secret the route
  answers only programs on this host, and on a network bind it is off
  (403 `onebot_disabled`).
- With AstrBot on the same account, keep `aiocqhttp` in `excluded_platforms`,
  or every message arrives twice.

Check sending with `curl http://127.0.0.1:3000/get_login_info`, and receiving
by watching personagent's log while you message the bot in a group. A failure
in either direction looks the same from outside: a bot that runs and stays
silent.
