# Deploying personagent

[中文：部署、QQ 扫码直连和排查](deploy.zh-CN.md)

The [quick start](start.md) and the [user guide](guide.md) take you to a
first chat. They cover installing, the
[home folder](guide.md#install-and-the-home-folder), setup on the local page
and connecting a platform. This guide covers what a live deployment needs,
and what to check when the bot goes quiet.

## The shortest config that works

The local page (`personagent`, or `personagent init --terminal` for the
terminal wizard) checks the key with one small request, then writes `.env` in
the home folder. Chatting needs one setting:

```
LLM_API_KEY=...
```

`LLM_BASE_URL` and `LLM_MODEL` default to `https://api.deepseek.com` and
`deepseek-flash`. You can point them at any OpenAI-compatible endpoint,
hosted or local (Ollama, llama.cpp). Paste the API address the way the
provider documents it, either a root or a version base such as `.../v1` or
`.../api/paas/v4`. Until you write a `persona.txt`, the bundled
`data/persona.example.<lang>.txt` stands in. Until `PERSONA_NAME` is set
(setup sets it), the character is called "bot".

The page also writes `PERSONA_NAME`, `AGENT_LANG` and a `CONNECTOR_TOKEN`.
Platforms connected from the page need nothing more in `.env`. Their
credentials go to `<home>/platforms/`: `direct.json` holds the platforms
personagent connects itself, and the managed AstrBot keeps the rest in its
own config. Optional additions:

```
ADMIN_IDS=telegram:12345             # the admin's accounts, <platform>:<id>
# QQ through NapCat (OneBot) only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

Keys stay on this machine. The model provider you choose sees the
conversations. Everything else in `.env.example` has a working default.
`SERVER_HOST` and `SERVER_PORT` are `127.0.0.1:8080`, `QQ_ONEBOT_URL` is
blank (no NapCat HTTP server), and an empty `ACCESS_GROUPS` leaves every group
to the connector.

## Running it

`personagent` opens the local page. While the page is open, it runs the
agent, the process that holds the directly connected platforms, and the
managed AstrBot when one is installed. Running `personagent` again reuses an
open page. `personagent up` starts the same processes without a browser.

Either way, those processes end with it, however it ends. Windows uses a job
object and other systems a process group. Anything an earlier crashed run
left behind is stopped at the next start. Each process writes its log to
`<home>/runtime/desktop/` (`agent.log`, `direct.log`, `astrbot.log`).

The local page and `personagent up` ask pypi.org at most once a day whether a
newer personagent is out. When one is, the Chat view and the terminal show the
command that updates this copy. The request carries only the version number,
and `UPDATE_CHECK_ENABLED=false` turns the check off.

`personagent run` starts the agent alone, as
[Run the service](guide.md#run-the-service) describes. Use it when your own
connectors (an AstrBot you run, Satori, Matrix) talk to it.
`personagent doctor` checks the settings and probes every upstream service.

**Settings renamed in 1.0.** While any setting name that 1.0 retired is still
set, a start refuses with exit code 2 and lists each one as `OLD -> NEW`.
`personagent doctor --fix` renames them in `<home>/.env`. It keeps the values
and comments, saves the old file as `.env.bak`, and comments out an old line
whose new name is already set. A retired name set in the environment rather
than in `.env` must be renamed where it is set. `personagent doctor` exits 1
while any remain, and `--json` lists them under `retired_settings`. `HOST`,
`PORT` and `LOG_FILE` count only when they are written in `.env`.

### Activity

[Activity](guide.md#activity) is a view in the local page. It needs no extra
install, loads nothing from the internet and never shows keys or tokens. It
reads the JSON API of the agent service that the local page started. With
`personagent run` alone, read the service's log and use `personagent learned`
instead. `DASHBOARD_ENABLED=false` turns the API off. The view then says so,
and `personagent doctor` prints `activity: off (...)`.

The API lives under `/api/dashboard/` on the agent service:

- `GET status`, `GET conversations` and `GET conversation?id=<chat id>` read
  the service's state, the chats it knows and one chat in detail.
- `POST candidates/<id>/promote`, `replace`, `reject` and `rollback` change
  what it has learned. Each change goes into the same ledger as
  `personagent learned`, with the actor `dashboard`.

Every call needs the header `X-Personagent-Dashboard-Token` with the token in
`dashboard.token` in the runtime folder (`<home>/runtime/` unless
`AGENT_RUNTIME_DIR` moves it). Only the owner can read the file, and the
service creates it when it starts. A call without the header gets 401
(`dashboard_token`), and a wrong token gets 403 (`wrong_token`).
`CONNECTOR_TOKEN` and `X-Personagent-Token` do not open it. They are for
connectors and `/health/details` only.

- Writes also need `X-Personagent-Dashboard: 1` and
  `Content-Type: application/json`. When the request sends an `Origin`, it
  must be the service's own.
- Cross-site browser requests are refused.
- Responses replace every credential with `***`. URLs in the startup
  checks also have their user name, password and query masked.
- Scripts on the same computer may call the API the same way the local page
  does.

The service serves no page. `GET /` answers a short note that points to the
local page and to `personagent learned`, which is also what an old `?token=`
link opens now. The local page binds to 127.0.0.1 only. On a server with no
local page, review and overrule learning with `personagent learned`.

## What the host must provide

1. **A writable home.** Startup takes a lock at
   `<home>/.personagent.instance.lock`, outside `runtime/`. A read-only home
   fails to start.
2. **One process per home.** The lock stops two copies from corrupting each
   other's ledgers. A second `personagent run` exits with one sentence saying
   so.
3. **A free port.** A taken or forbidden port also exits with one sentence.
   Pick another with `--port` or `SERVER_PORT`.

`AGENT_RUNTIME_DIR` must resolve beneath the home, or startup fails. A
relative `PERSONA_FILE` or `PERSONA_CARD_FILE` resolves under the home too,
so a persona kept elsewhere needs an absolute path.

## Connecting platforms

Add platforms under **Connect apps** on the local page. personagent checks
the credentials against the platform before it saves anything. If the
platform refuses them, the page shows the refusal and keeps nothing.

**Connected by personagent itself.** QQ, personal WeChat, Telegram and
Discord run in one "direct" process, with no AstrBot and no NapCat.

| Platform | What you do | Limits |
|---|---|---|
| QQ (official bot) | Scan a QR code with mobile QQ, which creates a bot or picks one you made. Pasting the AppID and AppSecret is the fallback. | Until the bot is certified, QQ lets it join only groups you own. Group message permissions are set in QQ. |
| Personal WeChat | Scan with WeChat (Tencent's iLink bot API). | One-to-one chats only. WeChat gives such bots no group messages. |
| Telegram | Paste the token from @BotFather. | |
| Discord | Paste the bot token, with Message Content Intent on. | |

**Through the managed AstrBot.** Every other platform goes through an AstrBot
that personagent downloads, together with its own Python 3.12 runtime, and
runs headless. It has no dashboard and needs no second login. KOOK,
Feishu/Lark (long connection), DingTalk (Stream mode), Slack (Socket Mode,
and the guide link pre-fills the app), WeCom AI bot (long connection),
Mattermost and Misskey ask for one or two values. The Advanced group needs a
public address or other software: WeCom app, WeChat Official Account, QQ
webhook, OneBot v11 (NapCat) and Satori. LINE is not offered.

On both paths, a connected platform answers every group and DM the platform
delivers to the bot. That changes once `ACCESS_GROUPS` or `ACCESS_DM_USERS`
lists an entry for that platform (see
[personagent's own allowlists](#through-an-astrbot-you-already-run)). Ids
arrive as `<platform>:<id>`, for example `qq_official:<openid>`,
`weixin_oc:<id>`, `telegram:<id>` and `discord:<id>`. The official QQ bot
sees openids, not QQ numbers. Connecting a platform directly removes an
AstrBot connection for the same platform, so one bot is never served twice.

## Through an AstrBot you already run

AstrBot, NapCat (OneBot), Koishi (through the
[Satori connector](../integrations/satori/README.md)) and Matrix (through the
[Matrix connector](../integrations/matrix/README.md) and mautrix bridges) are
third-party bridges that personagent works with. None of them is needed for
QQ, WeChat, Telegram or Discord.

AstrBot hands messages to personagent through a plugin in
`integrations/astrbot/astrbot_plugin_personagent/`. The plugin posts each
message to `POST /v1/events` and relays the replies in the response. It also
pulls personagent's outbox (`outbox_enabled`, on by default), so the persona
can speak first wherever the platform lets a bot do that. The plugin README
has the table. The managed AstrBot gets the plugin automatically. For your
own AstrBot, start it once so it creates its data folder (the one holding
`cmd_config.json`, `plugins/` and `config/`), then run:

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

The command copies the plugin into `<data dir>/plugins/` and writes one
`CONNECTOR_TOKEN` to both `.env` and the plugin config. It sets
`personagent_url` to `http://127.0.0.1:<SERVER_PORT>` unless the plugin
already has a URL it accepts (a loopback URL, tunnels included, or HTTPS).

For an AstrBot on another machine, download `astrbot_plugin_personagent.zip`
from the [latest release](https://github.com/wangkant/personagent/releases/latest)
and upload it under **Install from File** on AstrBot's plugin page. Set its
`connector_token` to the `CONNECTOR_TOKEN` in personagent's `.env`, and set
`personagent_url` to an HTTPS address for personagent (see
[Exposing the endpoints](#exposing-the-endpoints)).

After upgrading personagent, rerun `connect astrbot` or upload the new zip.
AstrBot 4.29 and later replace the installed copy. On older versions,
uninstall it first and leave **Also delete plugin configuration file**
unticked.

Options for `connect astrbot`:

- `--qq` takes `aiocqhttp` out of `excluded_platforms`, and `--no-qq` puts it
  back. With neither, QQ routing stays as it is. `CONNECTOR_QQ_PLATFORMS`
  follows whatever the plugin ends up doing.
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>`
  also switches that adapter on in AstrBot's own config. Slack also takes
  `--app-token`, and Lark and QQ take `--app-id` and `--app-secret`. An
  adapter entry that already exists keeps its other settings (proxy, base
  URL, polling) and gets only the new credentials.
- `--url https://...` sets an HTTPS address for the plugin to post to.
- `--install` downloads a managed AstrBot instead, and `--start` starts it.

The first run leaves the allowlists empty. A rerun keeps them, along with any
other excluded platforms.

The plugin denies by default. Fill in `groups`, and `dm_users` for DMs, in
AstrBot's WebUI, or answer the questions `connect` asks. DMs are forwarded
once `dm_users` is not empty. The
[plugin README](../integrations/astrbot/astrbot_plugin_personagent/README.md)
lists every key. The managed AstrBot opens each platform you connect with
`<platform>:*`. After the plugin is installed, restart AstrBot or reload
plugins in its WebUI. On the personagent side:

- `CONNECTOR_TOKEN` authenticates each request. The request carries the
  `X-Personagent-Token` header plus an HMAC-SHA256, keyed with the token, over
  `timestamp.nonce.body`, and a replay guard rejects reused nonces. A captured
  request cannot be replayed or altered. The token is also the signing key,
  so keep it out of logs and rotate it if it leaks. It is optional on one
  host and required across hosts.
- `ADMIN_IDS` lists the admin's accounts as `<platform>:<id>`
  (`telegram:12345`, `discord:4242`). A bare id or `qq:<id>` is a QQ number.
  `ADMIN_NAME` sets the admin's name. Every account listed belongs to one
  person, who gets the closer persona in groups and DMs, may manage what the
  bot remembers about a group, and may teach it alone. Through AstrBot, the
  platform is the adapter name AstrBot shows, and `/sid` in a chat shows an
  id.
- `ACCESS_GROUPS` and `ACCESS_DM_USERS` let personagent gate a platform
  itself, in the same `<platform>:<id>` form. Each platform is gated
  separately. A platform with no entries is left to the connector, and a
  single entry restricts that platform to its entries. A turn personagent
  refuses goes back unclaimed, so AstrBot's own model may answer it.

For AstrBot in Docker or on another host, see
[the user guide](guide.md#bridges-you-run-yourself).

### QQ through NapCat (OneBot)

This path uses a personal QQ account instead of an official bot. You need a
second QQ account in the target groups, not your own (see
[DISCLAIMER.md](DISCLAIMER.md)). It logs in, usually by QR code and in a
session that survives restarts, to a OneBot v11 implementation connected to
AstrBot's `aiocqhttp` adapter. [NapCat](https://github.com/NapNeko/NapCatQQ)
is tested and attaches to the QQ NT desktop client. LLOneBot and Lagrange
are other OneBot v11 implementations.

On the managed AstrBot, add **Advanced > OneBot v11 (NapCat)** on the local
page and point NapCat at `ws://127.0.0.1:6199/ws`. The
[Chinese guide](deploy.zh-CN.md) walks through it step by step. With your own
AstrBot, remove `aiocqhttp` from the plugin's `excluded_platforms`, set
`CONNECTOR_QQ_PLATFORMS=aiocqhttp` (`--qq` does both), and set `QQ_BOT_ID`
(`personagent connect astrbot` asks for it).

**`CONNECTOR_QQ_PLATFORMS` is required here.** Without it, QQ ids arrive
namespaced (`aiocqhttp:123456`) and every conversation looks new. Memory,
history and learned examples are keyed by the bare id, and the ledgers derive
row ids from the conversation id, so the split cannot be repaired afterwards.

Bare ids carry QQ authority, so the QQ entries of `ADMIN_IDS`,
`ACCESS_GROUPS` and `ACCESS_DM_USERS` apply on top of the plugin's
allowlists. A QQ DM must be in `dm_users` *and* come from the admin or an
`ACCESS_DM_USERS` entry. When `ACCESS_GROUPS` lists QQ groups, a QQ group
must be in both. List a platform in `CONNECTOR_QQ_PLATFORMS` only if you
trust its connector with that authority.

**NapCat's HTTP server** (`QQ_ONEBOT_URL`, blank by default) is optional on
this path. personagent also sends messages on its own initiative:

- proactive messages (`PROACTIVE_ENABLED`, off by default);
- the question asked two minutes after a rejection (`REACT_ELICIT_ENABLED`);
- the excuse sent in a group when the model call fails.

These go back through the plugin's outbox while the plugin is pulling it.
When it is not, they go to `QQ_ONEBOT_URL` if the URL is set. Only the sweep
for @-mentions missed while offline needs the server, together with
`QQ_BOT_ID`. The sweep runs at startup and then every 30 minutes. It covers
the QQ groups in `ACCESS_GROUPS` plus any group with traffic since the last
restart, and replays @-mentions under an hour old. With the URL blank,
`personagent doctor` shows the OneBot bridge as "not configured", not as a
failure.

**Lost on every connector path** (direct, AstrBot or another connector), with
no setting to bring it back:

- the OCR fallback for images that no vision model described;
- quote lookup through NapCat. Quotes resolve from personagent's own index of
  recent messages, and from the quoted text a connector sends with the quote;
- collecting new stickers from images posted in groups.

## More than one platform

Several connectors can run side by side against one personagent, because
each names its platform (`telegram:-1001234`, `matrix:!room:example.org`).
The direct process, AstrBot, Satori and Matrix can all run at once. Do not
bring one chat in through two connectors, or every message arrives twice.
Namespaced ids never collide with a bare QQ number.

Messages nobody asked for reach a platform through a connector that pulls
personagent's outbox. These are proactive openers, the question asked after a
rejection, and the excuse when the model call fails in a group. A DM's excuse
goes back in the response to the request that brought the message.

The direct process and the three connectors here all pull the outbox, on
platforms where a bot may send first. QQ rate-limits an official bot's
unprompted messages, and a person can switch them off. A connector of your
own sends `connector_id`, `reply_handle` and `"capabilities": ["outbox"]`
with its events and long-polls `/v1/outbox` (see
[the connector protocol](connectors.md)). Without such a connector,
personagent speaks only inside the request that brought a message. The
proactive loops skip those conversations, and the question and the excuse
are not sent.

`PROACTIVE_PLATFORMS` limits where the proactive loop may speak first.
`PROACTIVE_PLATFORMS=qq_official` keeps it on the official QQ bot, and `qq`
on QQ through NapCat. `CONNECTOR_OUTBOX_ENABLED=false` turns the outbox off
altogether.

To speak first in a DM without the outbox, your own scheduler (an AstrBot
plugin task, a cron entry) can post a DM event marked `"proactive": true`.
See [Speaking first without the outbox](connectors.md#speaking-first-without-the-outbox).

## Exposing the endpoints

Keep `SERVER_HOST=127.0.0.1` when the connector and personagent share a
machine. A container counts as the same machine only with the host's network
namespace or host networking. The local page and `personagent up` always
bind to `127.0.0.1`. Otherwise:

1. Set `SERVER_HOST=0.0.0.0` (or `--host 0.0.0.0`) and `CONNECTOR_TOKEN`.
   Startup refuses a network bind without the token. It does not require
   `QQ_ONEBOT_SECRET`, but without it the deprecated `/v1/onebot` is off on a
   network bind. Every request to it gets 403 `onebot_disabled`, and the log
   says why once.
2. Put an HTTPS reverse proxy or a private tunnel in front. Every connector
   here posts only to loopback, or to HTTPS with a token set. The AstrBot
   plugin logs anything else as `refusing unsafe personagent_url`, and the
   Satori and Matrix connectors refuse to start.
3. Keep the body byte-for-byte intact, because the signature covers it, and
   keep the clocks within five minutes of each other.

With a credential blank, its endpoint serves only local programs that call
`http://127.0.0.1` or `http://localhost` directly. A request gets 403
`non_local_request` if it has any of the following:

- an `Origin` header;
- a `Sec-Fetch-Site` other than `none`;
- a `Host` other than `localhost`, `127.0.0.1` or `::1`;
- a proxy header: `X-Forwarded-For`, `Forwarded`, `X-Real-IP`,
  `CF-Connecting-IP`, `Via`, `X-Forwarded-Host`, `X-Forwarded-Proto`,
  `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP` or
  `X-Original-Forwarded-For`.

A proxy on the same host that adds none of these still looks local. Set
`CONNECTOR_TOKEN` (and `QQ_ONEBOT_SECRET` if you use `/v1/onebot`) before you
add any proxy or tunnel, even on one host.

## Health endpoints

- `GET /health` is free and open, and calls nothing.
- `GET /health/details` probes the upstream services (cached for 60 s). With
  `CONNECTOR_TOKEN` blank, it answers local requests only. With a token set,
  it answers **only** requests carrying a matching `X-Personagent-Token`
  header, even from loopback. It returns 503 when a critical probe fails or
  cannot run. The critical probes are the chat models, and the OneBot bridge
  when QQ uses the direct OneBot ingress (`QQ_BOT_ID` and `QQ_ONEBOT_URL` set,
  `CONNECTOR_QQ_PLATFORMS` not set).
- `personagent doctor [--json]` runs the same probes plus the settings check,
  and exits non-zero in the same case. When the last update check is a day
  old, it also asks pypi.org for the newest version
  (`UPDATE_CHECK_ENABLED=false` skips that).

## Costs

- **Probes spend credit.** `personagent doctor` and `/health/details` send one
  tiny chat completion to each configured model endpoint (chat, DM, eval and
  vision). They also send one embedding if `EMBEDDING_MODEL` is set, and one
  Tavily search if `TAVILY_API_KEY` is set. `/health` and the settings and
  ledger checks are free.
- **The scripts in `tools/`** differ. Some are free and some call a model.
  The table in [tools.md](tools.md) says which.
- **`personagent eval`** calls the model for every case. The persona and
  learning suites also need a second model as judge (`BENCH_JUDGE_MODEL`).
- **Memory.** Past 256 namespaced (non-QQ) conversations, the least recently
  active idle one loses its recent history and pending reactions. Long-term
  memories, core notes and ledgers stay. A conversation in the middle of a
  request is never evicted. Long-term memories are loaded from disk at
  startup and are not bounded by this cap.
- **Disk.** The evidence log and candidate ledger in `runtime/` are
  append-only and never truncated. `personagent doctor` flags either one past
  50 MB (`LEDGER_EVIDENCE_WARN_BYTES`, `LEDGER_CANDIDATES_WARN_BYTES`). Back
  up `runtime/`, because it holds everything the bot has learned.

## When the bot goes quiet

The causes are listed with the most common first. When the local page runs
the agent, [Activity](guide.md#activity) shows whether messages arrive
and why it stayed quiet. On a server, read the service log, and use
`personagent learned` for what it has learned.

1. **Nothing reaches it.** On the local page, check that the platform is
   listed as connected, and read `runtime/desktop/direct.log` or
   `astrbot.log`. The QQ official bot must be in the group, and QQ decides
   which group messages it receives. A personal WeChat bot never receives
   groups. In an AstrBot you run, fill in the plugin's `groups` (and
   `dm_users` for DMs), and for NapCat take `aiocqhttp` out of
   `excluded_platforms`. The Satori and Matrix connectors have their own
   allowlists in their `.env`. See their READMEs. In this case the chat
   never appears in Activity.
2. **The agent is off.** The banner at `personagent run` says `agent: OFF`,
   gives the reason and the fix. With no `LLM_API_KEY`, add a key on the
   local page (or set `LLM_API_KEY`) and restart. With `AGENT_ENABLED=false`,
   set it to `true` in `<home>/.env` and restart. Until then every event gets
   `owned: false`, and the first one logs a single ERROR line with the same
   advice.
3. **AstrBot's own model answers instead.** The plugin fell back because the
   request failed, personagent turned the message away (item 5), or the
   agent is off (item 2). AstrBot's log shows `refusing unsafe
   personagent_url`, `agent refused the request (403): <message>` (or another
   status, see the table below), or `timed out waiting for the agent`.
   `timeout_s` must cover the debounce and every model call in the turn, so
   keep `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` under it. Its default (420)
   covers the agent's defaults (120 × 3 = 360 s). Raise it when you raise
   those two.
4. **It was not called.** In a group it answers its name (`PERSONA_NAME`) or
   an @. Otherwise it waits for enough conversation (`CHAT_TRIGGER_COUNT`, 30
   messages by default) and may still pass. From 02:00 to 07:00 in its time
   zone, it mostly stays out of chats it was not called into. The time zone
   is `PERSONA_TZ_OFFSET_HOURS`. Left blank, it is UTC+8 when `AGENT_LANG=zh`
   and this machine's offset otherwise. Activity shows the reason for each
   recent turn. To watch the same decision offline, run
   `personagent chat --trigger 4`.
5. **personagent's allowlists.** `ACCESS_GROUPS` and `ACCESS_DM_USERS` apply
   on every path, and a bare-id QQ DM also needs the admin or an entry. A
   message they turn away goes back unclaimed, so through AstrBot its own
   model may answer it. personagent logs each refused conversation once, at
   INFO, with the setting that refused it.
6. **The model call fails.** A rejected key (401 or 403) or an empty balance
   (402 or an exhausted quota) logs one ERROR line naming the provider host
   and the setting to fix. Run `personagent doctor`. It sends a tiny request
   to each model endpoint and shows the status, which also catches a wrong
   `LLM_BASE_URL` or `LLM_MODEL`. While the model is down, the persona sends a
   short in-character excuse when it is called, at most once per conversation
   every five minutes. The five minutes count from an excuse that was
   delivered, so when sending one fails, the next failure tries again.
7. **A misspelled setting.** Nothing fails, so the mistake is easy to miss.
   The startup log and `personagent doctor` list every key that
   `.env.example` does not know, and any value that starts with `#`.
8. **A BOM on `.env`.** The first setting's name carries the BOM and never
   reaches the process, although the file looks fine in every editor. Startup
   and `personagent doctor` report it. Re-save the file as UTF-8 without a
   BOM.
9. **`QQ_BOT_ID` unset or wrong with NapCat.** Through AstrBot, @-mentions
   still work, but the missed-mention sweep matches on it. On the direct
   OneBot ingress an @-mention is never recognised. The bot starts cleanly,
   logs nothing, and never answers one. `personagent doctor` warns when
   `QQ_BOT_ID` is empty and other QQ settings are set. The official QQ bot
   does not use it.
10. **It answers, but has forgotten what it learned.** Either NapCat QQ is
    arriving without `CONNECTOR_QQ_PLATFORMS=aiocqhttp`, or `PERSONA_NAME` or
    `PERSONA_VERSION` changed, which starts a new character. The log warns
    when the old character's promoted material is refused as a whole. Editing
    `persona.txt`, including in the page's Persona box, does not start a new
    character. Its revisions under one `PERSONA_VERSION` share a learning
    scope (`runtime/persona_lineage.json`). To fold in rows learned under a
    persona hash the lineage does not list, run
    `personagent learned lineage adopt <hash>`, then
    `personagent learned rebuild`. The hash is in the candidate's scope in
    `personagent learned show <id>`. Changing `AGENT_LANG` also switches to
    that language's learned files in `runtime/`.

Errors from `/v1/events` are listed below. The AstrBot plugin logs the
message, and `code` is the stable field a client can branch on.

| Status | `code` | Message in AstrBot's log | Cause |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | no `CONNECTOR_TOKEN`, and the caller is not on this machine |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | no `CONNECTOR_TOKEN`, and the request came through a browser, a proxy or another host name |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | missing or wrong token, headers or signature, clocks over 5 min apart, a reused nonce, or a full replay guard (`connector replay guard full` in the agent's log) |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` differs from now by more than `CONNECTOR_MAX_EVENT_AGE_S` (24 h), including future or millisecond timestamps |
| 400 | `invalid_schema` | invalid event schema | a required field is missing: `platform`, `conversation_type`, `sender_id`, `message_id`, `sent_at`, and `conversation_id` for groups |
| 400 | `client_disconnected` | client disconnected | the caller hung up while sending |
| 408 | `body_timeout` | request body not received in time | the body took more than 30 s to arrive |
| 413 | `body_too_large` | request body too large | over `SERVER_MAX_BODY_BYTES` (8 MB), usually an inline image |
| 429 | `capacity_exceeded` | webhook capacity exceeded | over `CONNECTOR_MAX_INFLIGHT` turns in flight; retry after 3 s |

## Legacy: the direct OneBot ingress

NapCat's webhook can still post events to `POST /v1/onebot`, and personagent
replies through `QQ_ONEBOT_URL`. This route is deprecated and stays through
1.x. Use the official QQ bot connection instead, or NapCat through AstrBot
with `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. The route warns once at first use
and marks every response `Deprecation: true`.

To move to NapCat through AstrBot, add OneBot v11 (NapCat) on the local page,
or run `personagent connect astrbot <AstrBot data dir> --qq` for your own
AstrBot and fill in the allowlists. Point NapCat's WebSocket client at it,
and turn off NapCat's HTTP client (keep its HTTP server). Memory and learning
carry over, because `CONNECTOR_QQ_PLATFORMS` keeps the ids.

If you still run the legacy route:

- Set up both directions as
  [NapCat's documentation](https://napneko.github.io/) describes, since the
  format changes between versions. You need an **HTTP server** at
  `QQ_ONEBOT_URL` for sending, and an **HTTP client** posting to
  `http://127.0.0.1:8080/v1/onebot` (`SERVER_HOST`, `SERVER_PORT`).
  `QQ_ONEBOT_URL` is blank by default, so write it in `.env`. Without it the
  bot receives but never replies. Preflight and `personagent doctor` warn
  when this route looks configured (`QQ_BOT_ID` or `QQ_ONEBOT_SECRET` set,
  `CONNECTOR_QQ_PLATFORMS` empty) and `QQ_ONEBOT_URL` is blank.
- If NapCat is on another machine, set `QQ_ONEBOT_SECRET` to the HTTP
  client's `secret`. Otherwise anyone who can reach the port can forge
  events. Bodies must then carry `x-signature: sha1=<hex>` (403
  `bad_signature`), and events timestamped more than five minutes off get
  403 `stale_event`. Without the secret, the route answers only programs on
  this host, and on a network bind it is off (403 `onebot_disabled`).
- With AstrBot on the same account, keep `aiocqhttp` in
  `excluded_platforms`, or every message arrives twice.

Check sending with `curl http://127.0.0.1:3000/get_login_info`. Check
receiving by watching personagent's log while you message the bot in a group.
A failure in either direction looks the same from outside: the bot runs and
stays silent.
