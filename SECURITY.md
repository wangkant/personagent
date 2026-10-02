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
  other than `none`, a foreign `Host`, or a proxy header is refused, which
  stops a web page or a tunnel from reaching them. A network bind
  (`SERVER_HOST=0.0.0.0`) will not start without `CONNECTOR_TOKEN`, and the
  deprecated `/v1/onebot` route answers only this machine unless
  `QQ_ONEBOT_SECRET` is set.
- **The SSRF guard.** Every fetch of a link, share card or image goes through
  one guard: public addresses only, every address a name resolves to checked,
  redirects checked at each hop.
- **The dashboard.** It is served only to this machine (a loopback peer, a local
  `Host`, no proxy headers) unless a request carries `CONNECTOR_TOKEN`. Changes
  need a same-origin POST with a custom header. It sends a strict content
  security policy, and never shows a value whose name ends in `_KEY`,
  `_TOKEN`, `_SECRET` or `PASSWORD`.
- **Secrets in `.env`.** API keys and tokens live in the home folder's `.env`.
  Setup narrows its permissions where the operating system allows it.
  Anything that leaks them to a log, a response, a connector or another user is
  a vulnerability.
- **The AstrBot plugin.** It refuses plain `http://` to anything but loopback,
  and delivers outbox messages only to a conversation it has itself seen.
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
- Flaws in AstrBot, NapCat, Koishi, a model provider or another dependency:
  report those upstream.

## Running it safely

Keep `SERVER_HOST=127.0.0.1` when the connector is on the same machine. If you
expose it, set `CONNECTOR_TOKEN` and put HTTPS in front. Keep `.env` and
`runtime/` private and out of version control. See
[docs/deploy.md](docs/deploy.md#exposing-the-endpoints).
