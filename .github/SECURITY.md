# Security policy

## Reporting a vulnerability

Please report vulnerabilities privately, not in a public issue.

Use GitHub's private vulnerability reporting. Open the
[Security tab of wangkant/personagent](https://github.com/wangkant/personagent/security),
choose "Report a vulnerability", and describe what you found. Include the
version (`personagent --version`), how you installed it, which connector you
use, and the smallest set of steps that reproduces the problem. Do not
include real API keys, tokens or chat logs.

One person maintains this project, so expect a reply within about a week.
A confirmed problem is fixed in a patch release and credited in the
advisory and the CHANGELOG, unless you prefer not to be named. Please allow
reasonable time for the fix to ship before you publish details.

## Supported versions

| Version | Supported |
|---|---|
| 1.x (the latest release) | yes |
| 0.x | no |

## What is in scope

The surfaces below carry the security-relevant behaviour. A way around any
of them is a vulnerability.

- **The connector token and signatures.** `POST /v1/events` and
  `POST /v1/outbox` require `CONNECTOR_TOKEN` as a bearer header and an
  HMAC-SHA256 over `timestamp.nonce.body`. The server refuses timestamps
  more than five minutes from its clock, and events whose `sent_at` is
  older than `CONNECTOR_MAX_EVENT_AGE_S`.
- **The replay guard.** Each nonce is accepted once. The guard persists to
  disk, so a replay is still refused after a restart inside the window.
- **Local-only endpoints.** With no credential set, the endpoints answer
  only programs on the same machine. The server refuses a request that
  carries `Origin`, a `Sec-Fetch-Site` other than `none`, a foreign `Host`,
  or a proxy header. The proxy headers include `X-Forwarded-For`,
  `Forwarded`, `Via`, `X-Real-IP` and the others listed in
  [docs/deploy.md](../docs/deploy.md#exposing-the-endpoints). This keeps
  web pages and tunnels from reaching the endpoints. A blank `SERVER_HOST`
  means `127.0.0.1`. A network bind (`SERVER_HOST=0.0.0.0`) will not start
  without `CONNECTOR_TOKEN`. On such a bind the deprecated `/v1/onebot`
  route is off (403 `onebot_disabled`) unless `QQ_ONEBOT_SECRET` is set.
- **The SSRF guard.** Every fetch of a link, share card or image goes
  through one guard. It allows public addresses only, checks every address
  a name resolves to, and checks redirects at each hop.
- **The local page.** `personagent start` serves it on 127.0.0.1 only. Its
  API requires the token in the link the command opens, which is new on
  each run. It refuses a host other than `localhost`, `127.0.0.1` or `::1`,
  an `Origin` other than the page's own, and forwarding headers. It sends a
  strict content security policy.
- **The Activity API.** The agent service serves no page. `GET /` answers
  a plain-text note, and the JSON API under `/api/dashboard/` feeds the
  local page's Activity view. Every call needs the
  `X-Personagent-Dashboard-Token` header with the token stored owner-only
  in `<runtime>/dashboard.token`, which the service creates when it starts.
  No link, query string or cookie carries the token. `CONNECTOR_TOKEN` does
  not open the API. A request that a browser marks as cross-site or
  same-site is refused. Changes need a POST with `X-Personagent-Dashboard:
  1`, `Content-Type: application/json` and, when an `Origin` is sent, the
  service's own origin. Responses carry a strict content security policy,
  never include a value whose name ends in `_KEY`, `_TOKEN`, `_SECRET` or
  `PASSWORD`, and mask credentials in the URLs of the startup checks. The
  local page, bound to 127.0.0.1, reads the token file on the same machine
  and calls the API from its own process, so the token never reaches the
  browser. `DASHBOARD_ENABLED=false` removes the API.
- **Secrets in the home folder.** API keys and tokens live in `.env`. The
  credentials of QQ, WeChat, Telegram and Discord bots live in
  `platforms/direct.json`. Both files are made owner-only where the
  operating system allows it. Anything that leaks them to a log, a
  response, a connector or another user is a vulnerability.
- **The AstrBot plugin**, which passes AstrBot's messages to personagent.
  It refuses plain `http://` to anything but loopback, and delivers outbox
  messages only to conversations it has seen itself.
- **What it learns.** Planting an instruction or a memory in the bot from a
  chat without the corroboration the learning rules require is in scope.
  So is making a change that the ledger cannot undo.

## What is not

- A model saying something wrong or rude.
- Account restrictions that a chat platform applies because of a
  connector. See [DISCLAIMER.md](../docs/DISCLAIMER.md).
- Anything that requires control of the machine or of `.env`, or a
  connector that already holds the token.
- Denial of service by a connector that holds the token.
- Flaws in a chat platform's API, in third-party bridges such as AstrBot,
  NapCat, Koishi or mautrix, in a model provider or in another dependency.
  Report those upstream.

## Running it safely

Read [Exposing the endpoints](../docs/deploy.md#exposing-the-endpoints)
before you make the service reachable from another machine, and the
guide's [privacy section](../docs/guide.md#privacy-and-consent) for what to
keep private.

personagent asks PyPI whether a newer release exists at most once a day.
The request carries only the version number. Set
`UPDATE_CHECK_ENABLED=false` in `.env` to turn the check off.
