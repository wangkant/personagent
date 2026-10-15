# Security policy

## Reporting a vulnerability

Please report it privately, not in a public issue.

Use GitHub's private vulnerability reporting: open the
[Security tab of wangkant/personagent](https://github.com/wangkant/personagent/security),
choose "Report a vulnerability", and describe what you found. Include the
version (`personagent --version`), how you installed it, which connector you
use, and the smallest steps that reproduce it. Do not include real API keys,
tokens or chat logs.

This is a one-person project. You will get a reply as soon as it can be read,
usually within a week. A confirmed problem is fixed in a patch release and
credited in the advisory and the CHANGELOG, unless you prefer not to be named.
Please give a reasonable time to ship the fix before you publish details.

## Supported versions

| Version | Supported |
|---|---|
| 1.x (the latest release) | yes |
| 0.x | no |

## What is in scope

The surfaces below hold the security-relevant behaviour. A way around any of
them is a vulnerability.

- **The connector token and signatures.** `POST /v1/events` and
  `POST /v1/outbox` take `CONNECTOR_TOKEN` as a bearer header plus an
  HMAC-SHA256 over `timestamp.nonce.body`. Timestamps more than five minutes
  from the server's clock are refused, and so are events whose `sent_at` is
  older than `CONNECTOR_MAX_EVENT_AGE_S`.
- **The replay guard.** A nonce is accepted once. The guard persists to disk, so
  a restart inside the window still refuses a replay.
- **Local-only endpoints.** With no credential set, the endpoints answer only a
  program on this machine. A request carrying `Origin`, a `Sec-Fetch-Site`
  other than `none`, a foreign `Host`, or a proxy header (`X-Forwarded-For`,
  `Forwarded`, `Via`, `X-Real-IP` and the others listed in
  [docs/deploy.md](docs/deploy.md#exposing-the-endpoints)) is refused, which
  stops a web page or a tunnel from reaching them. A blank `SERVER_HOST` means
  `127.0.0.1`. A network bind (`SERVER_HOST=0.0.0.0`) will not start without
  `CONNECTOR_TOKEN`, and on it the deprecated `/v1/onebot` route is off
  (403 `onebot_disabled`) unless `QQ_ONEBOT_SECRET` is set.
- **The SSRF guard.** Every fetch of a link, share card or image goes through
  one guard: public addresses only, every address a name resolves to checked,
  redirects checked at each hop.
- **The local page.** `personagent start` serves it on 127.0.0.1 only. Its
  API needs the token in the link the command opens (a new one each run),
  and refuses a host other than `localhost`, `127.0.0.1` or `::1`, an
  `Origin` other than the page's own, and forwarding headers. It sends a
  strict content security policy.
- **The dashboard.** Every request needs its own token, from
  `<runtime>/dashboard.token` (owner-only): the HttpOnly, `SameSite=Strict`
  cookie its private link sets, or the `X-Personagent-Dashboard-Token`
  header. `CONNECTOR_TOKEN` does not open it. A browser must name
  `localhost`, an IP address or `SERVER_HOST` as the host, which stops DNS
  rebinding. Changes need a same-origin POST with a custom header. It sends a
  strict content security policy, masks credentials in URLs it shows, and
  never shows a value whose name ends in `_KEY`, `_TOKEN`, `_SECRET` or
  `PASSWORD`.
- **Secrets in the home folder.** API keys and tokens live in `.env`, and the
  credentials of QQ, WeChat, Telegram and Discord bots in
  `platforms/direct.json`. Both are made owner-only where the operating
  system allows it.
  Anything that leaks them to a log, a response, a connector or another user is
  a vulnerability.
- **The AstrBot plugin**, which hands AstrBot's messages to personagent. It
  refuses plain `http://` to anything but loopback, and delivers outbox
  messages only to a conversation it has itself seen.
- **What it learns.** Planting an instruction or a memory in the bot from a chat
  without the corroboration the learning rule asks for, or making a change
  that the ledger cannot undo, is in scope.

## What is not

- A model saying something wrong or rude.
- Account restrictions on a chat platform that a connector causes; see
  [DISCLAIMER.md](DISCLAIMER.md).
- Anything that needs control of the machine or of `.env`, or a connector that
  already holds the token.
- Denial of service by a connector that holds the token.
- Flaws in a chat platform's API, in third-party bridges such as AstrBot,
  NapCat, Koishi or mautrix, in a model provider or in another dependency:
  report those upstream.

## Running it safely

See [Exposing the endpoints](docs/deploy.md#exposing-the-endpoints) before you
reach it from another machine, and the guide's
[privacy section](docs/guide.md#privacy-and-consent) for what to keep private.
