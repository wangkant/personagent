# Matrix connector

Puts [personagent](https://github.com/wangkant/personagent) in Matrix rooms,
and through [mautrix bridges](https://docs.mau.fi/bridges/) on WhatsApp,
Signal, Messenger, Instagram, Google Messages and other networks.

The connector is a small standalone process. It logs in to a homeserver as an
ordinary Matrix user, forwards every allowed room message to the agent's
`POST /webhook/gateway` as a platform-neutral event
([docs/connectors.md](../../docs/connectors.md)), and posts the agent's
replies back into the room. It also polls the agent's outbox, so scheduled
openers, follow-up questions and excuses reach Matrix too.

## What it does

Inbound, for each message in an allowed room:

- The event is on platform `matrix`, with raw Matrix ids: the agent stores
  `matrix:@alex:example.org` and `matrix:!room:example.org`.
- A room is a **direct chat** when the bot's `m.direct` lists it, or when it
  holds exactly one other member besides the bot and the users in
  `MATRIX_IGNORE_USERS`. A direct chat is keyed by the person, a group by the
  room. A room named by id in `MATRIX_ROOMS` is always a group.
- `is_at_me` is true when the message mentions the bot (`m.mentions`, or a
  pill or the bot's user id from a client too old to send `m.mentions`), or
  replies to one of the bot's messages.
- A reply carries the quoted message's sender and text, from a cache of recent
  events or by fetching the parent event. The reply fallback that older
  clients prepend (`> <@alex:example.org> ...`) is stripped, so the agent never
  reads someone else's words as the sender's.
- Images and stickers are downloaded (and decrypted in encrypted rooms) and
  sent to the agent as bytes, up to 4 MB. Matrix media has needed an access
  token since spec 1.11, so the agent could not fetch a URL itself. Voice
  messages, videos and files are described in words.
- A room's messages reach the agent in the order they were sent: one sent
  after an image waits until the image is downloaded. The agent can still
  work on several at once.
- The timestamp is the homeserver's `origin_server_ts`.
- Skipped: the bot's own messages, `m.notice` (the message type bots use,
  so two bots never answer each other), edits, reactions, messages from
  `MATRIX_IGNORE_USERS`, the backlog the first sync returns at startup, and
  anything older than `MATRIX_MAX_EVENT_AGE_S`, such as history a bridge
  backfills into a new room.

Outbound:

- Text replies are `m.text`. When the agent asks to mention someone in a
  group, the reply starts with a pill and lists them in `m.mentions`; every
  other reply carries an empty `m.mentions`, so no client turns a name in the
  text into a ping.
- Image replies are uploaded, encrypted in encrypted rooms.
- A typing notice runs while the agent works on a turn.
- A message in a thread is answered in that thread.
- The bot marks a message read once the agent takes the conversation
  (`MATRIX_READ_RECEIPTS`). Through a bridge, that is the read tick on the
  other network.
- Outbox deliveries go to the room the conversation last came from (the
  event's `reply_handle` is the room id).

## Install

You need a running personagent and a Matrix account for the bot. Create a
dedicated account; the persona should not share one with a person.

```bash
pip install -r integrations/matrix/requirements.txt
cp integrations/matrix/.env.example integrations/matrix/.env
```

Edit `integrations/matrix/.env`:

```ini
MATRIX_HOMESERVER=https://matrix.example.org
MATRIX_USER_ID=@nova:example.org
MATRIX_PASSWORD=...
MATRIX_ROOMS=!AbCdEf:example.org
MATRIX_DM_USERS=@alex:example.org
PERSONAGENT_URL=http://127.0.0.1:8080/webhook/gateway
```

Then run it next to the agent:

```bash
python integrations/matrix/matrix_connector.py
# or: python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

Invite the bot to a room listed in `MATRIX_ROOMS` and it joins. Room ids are
under Room settings, Advanced in Element.

### Logging in

A password login is the simplest. The session it gets (user id, device id and
access token) is saved in `MATRIX_STORE_PATH/session.json` and reused on the
next start, so a restart is not a new device. Delete that file to log in
again.

To use an existing access token instead, set `MATRIX_ACCESS_TOKEN`; the
connector asks the homeserver whose it is. Do not take the token of a session
you use yourself: logging that session out also logs the bot out.

When the homeserver logs the bot out (`M_UNKNOWN_TOKEN`), the connector stops
with an error saying so. After a password login, starting it again logs in
again; with `MATRIX_ACCESS_TOKEN`, set a new token first. Any other failed
sync is retried after a wait that doubles up to a minute.

### Where the agent can run

The rule is the protocol's: `PERSONAGENT_URL` must be a loopback address, or
HTTPS with `GATEWAY_TOKEN` set to the agent's `GATEWAY_TOKEN`. The connector
refuses to start otherwise.

## Settings

Every setting is in [.env.example](.env.example). Lists are comma separated
and take globs: `*` is everyone, `@*:example.org` a whole server.

| Setting | Meaning |
|---|---|
| `MATRIX_ROOMS` | group rooms to answer in, by room id; `*` for every room the bot has joined |
| `MATRIX_DM_USERS` | people who may talk to the bot in a direct chat |
| `MATRIX_INVITE_FROM` | whose invites the bot accepts. Invites to rooms named in `MATRIX_ROOMS`, and direct-chat invites from `MATRIX_DM_USERS`, are always accepted; everything else is left pending |
| `MATRIX_IGNORE_USERS` | never answered, and not counted as members when telling a direct chat from a group |
| `MATRIX_E2EE` | end-to-end encryption, see below |
| `MATRIX_TIMEOUT_S` | how long one turn may take; keep it above the agent's `LLM_TIMEOUT × (1 + LLM_MAX_RETRIES)` |
| `MATRIX_OUTBOX` | poll the agent's outbox |

## Bridges: WhatsApp, Signal, Messenger, Instagram and more

A mautrix bridge logs in to another network **as an account on that network**
and mirrors its chats into Matrix rooms ("portals"). Everyone on the other side
appears in Matrix as a ghost user such as `@whatsapp_4912345:example.org`.
When the bot's Matrix account is the one logged in to the bridge, the persona
lives on that network: a WhatsApp contact writes to the persona's number, the
bridge posts the message in a portal room, this connector forwards it, and the
reply goes back the same way.

| Network | Bridge |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger, Instagram DMs | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages (RCS and SMS through an Android phone) | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice, LinkedIn, Twitter/X DMs, Bluesky DMs, Google Chat, Zulip, IRC, iMessage | the other [mautrix bridges](https://github.com/mautrix) |
| Telegram, Discord, Slack | mautrix bridges exist, but these networks have official bot APIs: prefer the AstrBot or Satori connector, which use them |

Setting one up:

1. Run a homeserver you control (Synapse, or another that supports
   application services) and install the bridge following
   [its documentation](https://docs.mau.fi/bridges/). Give the bot's account
   the `user` permission level in the bridge's `permissions`.
2. Sign in to Element as the bot, open a chat with the bridge bot (for
   example `@whatsappbot:example.org`) and send `login`. Link the network
   account the persona will use: scan the QR code with the persona's phone
   for WhatsApp, Signal and Google Messages, or give Meta's login for
   Messenger and Instagram. See
   [Using bridges](https://docs.mau.fi/bridges/general/using-bridges.html).
3. Let the connector join the portals and keep the bridge's own talk out:

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_ROOMS=!groupPortal:example.org
   ```

   The second entry in `MATRIX_IGNORE_USERS` is the bridge's ghost of the
   persona's own number. Without
   [double puppeting](https://docs.mau.fi/bridges/general/double-puppeting.html),
   a message typed on the persona's phone reaches Matrix from that ghost, and
   the bot would answer itself. `MATRIX_ROOMS=*` answers in every group portal
   the bot is in; list room ids to choose.

### Caveats of puppeting

- The bridge is an **unofficial client** of the network, logged in as a
  normal user account (a linked device or a web session). It is not a bot API,
  and nothing on the network marks the account as a bot.
- The persona needs **its own account**, usually its own phone number, and the
  phone must stay reachable: WhatsApp disconnects linked devices once the phone
  has been offline for about two weeks, and Google Messages works only while
  the Android phone is online.
- Group chats show the persona's account like any member. Tell people they are
  talking to a bot.
- Reactions, edits, deletions, polls and calls are not forwarded to the agent.

### Terms of each network

Read the terms of every network you connect before you do. They change, and
the account at stake is yours.

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) lists
  auto-messaging among impermissible communications and forbids non-personal
  use it has not authorized, and it can ban accounts that do either. Its
  sanctioned route for automation is the WhatsApp Business Platform, which a
  bridge does not use.
- [Signal](https://signal.org/legal/) also lists auto-messaging as
  impermissible.
- [Facebook](https://www.facebook.com/terms.php) and
  [Instagram](https://help.instagram.com/581066165581870) forbid automated
  access without Meta's permission, and Meta may lock an account that logs in
  from a client it does not recognise.
- Google Messages is covered by
  [Google's terms](https://policies.google.com/terms) and by your mobile
  carrier's terms for SMS and RCS, which may charge for or restrict automated
  messages.

Use a dedicated account you can afford to lose, only in conversations where
people know they are talking to a bot, and see [DISCLAIMER.md](../../DISCLAIMER.md).

## End-to-end encryption

With `MATRIX_E2EE=false` (the default) the bot reads only unencrypted rooms.
In an encrypted room it logs that it cannot decrypt, and it never sends a
plaintext reply there.

With `MATRIX_E2EE=true`:

- `MATRIX_STORE_PATH` (default `runtime/` next to the script, which git
  ignores) holds the device's keys and the sync token. Keep it: a lost store is
  a new device that cannot read anything encrypted before it.
- The device must stay the same across restarts. A password login does that
  through the saved session; with an access token, set `MATRIX_DEVICE_ID` to
  the token's device.
- The bot shares its keys with every device in the room, verified or not, and
  cannot verify itself interactively, so people see its device as unverified.
  It has no key backup and no cross-signing.
- A message whose key has not arrived is logged and skipped, not retried.
- A mautrix bridge can encrypt its portals
  ([end-to-bridge encryption](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)).
  The bridge holds those keys on your server, so the protection ends there and
  the other network carries the message under its own encryption. If your
  bridge encrypts portals, turn `MATRIX_E2EE` on.

## Why matrix-nio

The connector uses [matrix-nio](https://github.com/matrix-nio/matrix-nio)
0.26 rather than [mautrix-python](https://github.com/mautrix/python). Both are
maintained (releases in July 2026) and asyncio-based.

- **Encryption.** matrix-nio 0.26 does end-to-end encryption with
  [vodozemac](https://github.com/matrix-org/vodozemac), the Rust implementation
  that replaced libolm; it installs from wheels on Linux, macOS and Windows.
  mautrix-python's encryption still goes through python-olm and libolm, which
  the Matrix.org Foundation
  [deprecated in 2024](https://matrix.org/blog/2024/08/libolm-deprecation/)
  and which has to be compiled where no wheel exists.
- **License.** matrix-nio is ISC, a permissive license like this project's
  MIT. mautrix-python is MPL-2.0, fine as a dependency but file-level copyleft
  if copied.
- **Fit.** matrix-nio is a client library for one account, which is what a
  connector is. mautrix-python is a framework for bridges and application
  services; its maintainer's bridges are now mostly written in Go.
- **Media.** matrix-nio has used authenticated media since 0.25.1, which
  matrix.org and other homeservers require for downloads.

## Tests

`tests/test_matrix_connector.py` fakes the Matrix client and the agent, so it
runs without matrix-nio and without a network:

```bash
python -m pytest tests/test_matrix_connector.py
```
