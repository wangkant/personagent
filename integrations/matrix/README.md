# Matrix connector

This connector puts [personagent](https://github.com/wangkant/personagent)
in Matrix rooms, and through [mautrix bridges](https://docs.mau.fi/bridges/)
on WhatsApp, Signal, Messenger, Instagram, Google Messages and other
networks. Matrix and the bridges are third-party software that you run
yourself. personagent does not need them for the platforms it connects from
its local page.

The connector is a small standalone process built on
[matrix-nio](https://github.com/matrix-nio/matrix-nio), which supports
end-to-end encryption without libolm. It logs in to a homeserver as an
ordinary Matrix user, forwards every allowed room message to the agent's
`POST /v1/events` as a platform-neutral event
([docs/connectors.md](../../docs/connectors.md)), and posts the agent's
replies back into the room. It also polls the agent's outbox, so scheduled
openers, follow-up questions and excuses reach Matrix as well.

## What it does

Inbound, for each message in an allowed room:

- The event uses platform `matrix` and raw Matrix ids, so the agent stores
  `matrix:@alex:example.org` and `matrix:!room:example.org`.
- A room counts as a direct chat when the bot's `m.direct` lists it, or when
  it has exactly one member besides the bot and the users in
  `MATRIX_IGNORE_USERS`. A direct chat is keyed by the person, and a group by
  the room. A room named by id in `MATRIX_GROUPS` is always a group.
- `addressed` is true when the message mentions the bot or replies to one of
  the bot's messages. A mention is `m.mentions`, or, from clients too old to
  send `m.mentions`, a pill or the bot's user id in the text.
- A reply carries the quoted message's sender and text. The connector takes
  them from a cache of recent events, or fetches the parent event. It strips
  the reply fallback that older clients prepend
  (`> <@alex:example.org> ...`), so the agent never reads someone else's
  words as the sender's.
- Images and stickers up to 4 MB are downloaded, decrypted in encrypted
  rooms, and sent to the agent as bytes. Voice messages, videos and files are described in words.
- A room's messages reach the agent in the order they were sent. A message
  sent after an image waits until the image has been downloaded. The agent
  can still work on several turns at once.
- The timestamp is the homeserver's `origin_server_ts`.
- The connector skips the bot's own messages, `m.notice` messages (the type
  bots send), edits, reactions,
  messages from `MATRIX_IGNORE_USERS`, the backlog the first sync returns at
  startup, and anything older than `MATRIX_MAX_EVENT_AGE_S`, such as history
  a bridge backfills into a new room.

Outbound:

- Text replies are `m.text`. When the agent asks to mention someone in a
  group, the reply starts with a pill and lists that person in `m.mentions`.
  Every other reply carries an empty `m.mentions`, so no client turns a name
  in the text into a ping.
- Image replies are uploaded, and encrypted in encrypted rooms.
- A typing notice runs while the agent works on a turn.
- A message in a thread is answered in that thread.
- Once the agent takes the conversation, the bot marks the message read
  (`MATRIX_READ_RECEIPTS_ENABLED`). Through a bridge, this shows as the read
  tick on the other network.
- Outbox deliveries go to the room the conversation last came from. The
  event's `reply_handle` is the room id.

## Install

You need a running personagent and a Matrix account for the bot. Create a
dedicated account rather than sharing one with a person.

The connector is a script in this repository, so it needs a copy of the
repository (a clone, or the ZIP from GitHub) and a Python environment of its
own, because `matrix-nio` is not one of personagent's dependencies. In a
clone that already has personagent's `.venv`, install into that
environment:

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

If you installed personagent from PyPI with pip, or run it with uvx, create
a separate venv next to the copy:

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

On Windows the interpreter is `.venv\Scripts\python.exe` or
`connector-venv\Scripts\python.exe`. Next, copy the settings file:

```bash
cp integrations/matrix/.env.example integrations/matrix/.env
```

Edit `integrations/matrix/.env`:

```ini
MATRIX_URL=https://matrix.example.org
MATRIX_USER_ID=@nova:example.org
MATRIX_PASSWORD=...
MATRIX_GROUPS=!AbCdEf:example.org
MATRIX_DM_USERS=@alex:example.org
PERSONAGENT_URL=http://127.0.0.1:8080
```

Then start the connector next to the agent, with the same interpreter:

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

Invite the bot to a room listed in `MATRIX_GROUPS`, and it joins. In
Element, the room id is under Room settings, Advanced.

### Logging in

A password login is the easiest way to start. The connector saves the
session it gets (user id, device id and access token) in
`MATRIX_STORE_DIR/session.json` and reuses it on the next start, so a
restart does not create a new device. Delete that file to log in again.

To use an existing access token instead, set `MATRIX_ACCESS_TOKEN`. The
connector asks the homeserver which account the token belongs to. Do not
use the token of a session you use yourself, because logging that session
out also logs the bot out.

When the homeserver logs the bot out (`M_UNKNOWN_TOKEN`), the connector
stops with an error that says so. After a password login, starting it again
logs in again. With `MATRIX_ACCESS_TOKEN`, set a new token first. Any other
failed sync is retried after a delay that doubles up to one minute.

### Where the agent can run

The protocol sets the rule. `PERSONAGENT_URL` must be a loopback address, or
HTTPS with `CONNECTOR_TOKEN` set to the agent's `CONNECTOR_TOKEN`. Otherwise
the connector refuses to start. Set the token on both sides before you put
any proxy or tunnel in front of the agent, even on a single host.

## Settings

[.env.example](.env.example) lists every setting. Lists are comma-separated
and accept globs, so `@*:example.org` matches a whole server. An empty list
answers no one. A bare `*` matches everyone and marks the event
`prefiltered: false`. The agent's own `ACCESS_GROUPS` / `ACCESS_DM_USERS`
then decide alone, and a platform with no entries there is refused.

| Setting | Meaning |
|---|---|
| `MATRIX_GROUPS` | Group rooms to answer in, by room id. `*` means every room the bot has joined. |
| `MATRIX_DM_USERS` | People who may talk to the bot in a direct chat. `*` means everyone. |
| `MATRIX_INVITE_FROM` | Users whose invites the bot accepts. Invites to rooms named in `MATRIX_GROUPS`, and direct-chat invites from `MATRIX_DM_USERS`, are always accepted. Other invites are left pending. |
| `MATRIX_IGNORE_USERS` | Never answered, and not counted as members when the connector tells a direct chat from a group. |
| `MATRIX_E2EE_ENABLED` | End-to-end encryption. See below. |
| `MATRIX_TIMEOUT_S` | How long one turn may take. Keep it above the agent's `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`. |
| `MATRIX_OUTBOX_ENABLED` | Poll the agent's outbox. |

## Bridges: WhatsApp, Signal, Messenger, Instagram and more

A mautrix bridge logs in to another network as an account on that network
and mirrors its chats into Matrix rooms, called portals. Everyone on the
other side appears in Matrix as a ghost user such as
`@whatsapp_4912345:example.org`. When the bot's Matrix account is the one
logged in to the bridge, the persona lives on that network. A WhatsApp
contact writes to the persona's number, the bridge posts the message in a
portal room, this connector forwards it, and the reply travels back the same
way.

| Network | Bridge |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger, Instagram DMs | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages (RCS and SMS through an Android phone) | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice, LinkedIn, Twitter/X DMs, Bluesky DMs, Google Chat, Zulip, IRC, iMessage | The other [mautrix bridges](https://github.com/mautrix) |
| Telegram, Discord, Slack | mautrix bridges exist, but these networks have official bot APIs. personagent connects Telegram and Discord itself, and Slack through the AstrBot its local page runs. |

To set one up:

1. Run a homeserver you control (Synapse, or another server that supports
   application services) and install the bridge by following
   [its documentation](https://docs.mau.fi/bridges/). Give the bot's account
   the `user` permission level in the bridge's `permissions`.
2. Sign in to Element as the bot, open a chat with the bridge bot (for
   example `@whatsappbot:example.org`) and send `login`. Link the network
   account the persona will use. For WhatsApp, Signal and Google Messages,
   scan the QR code with the persona's phone. For Messenger and Instagram,
   give the Meta login. See
   [Using bridges](https://docs.mau.fi/bridges/general/using-bridges.html).
3. Let the connector join the portals, and keep the bridge's own messages
   out:

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   The second entry in `MATRIX_IGNORE_USERS` is the bridge's ghost of the
   persona's own number. Without
   [double puppeting](https://docs.mau.fi/bridges/general/double-puppeting.html),
   a message typed on the persona's phone reaches Matrix from that ghost,
   and the bot would answer itself. `MATRIX_GROUPS=*` forwards every group
   portal the bot is in, and personagent then answers only in the rooms its
   `ACCESS_GROUPS` lists as `matrix:!room:server`. List room ids here to
   choose rooms in the connector instead.

### Puppeting

- The bridge is an unofficial client of the network, logged in as a normal
  user account (a linked device or a web session). It does not use a bot
  API, and nothing on the network marks the account as a bot.
- The persona needs its own account, usually with its own phone number, and
  the phone must stay reachable. WhatsApp disconnects linked devices once
  the phone has been offline for about two weeks, and Google Messages works
  only while the Android phone is online.
- In group chats the persona's account looks like any other member. Tell
  people they are talking to a bot.
- Reactions, edits, deletions, polls and calls are not forwarded to the
  agent.

### Terms of each network

Read the terms of every network before you connect it.

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) lists
  auto-messaging among impermissible communications, forbids non-personal
  use it has not authorized, and can ban accounts that do either. Its
  sanctioned route for automation is the WhatsApp Business Platform, which a
  bridge does not use.
- [Signal](https://signal.org/legal/) also lists auto-messaging as
  impermissible.
- [Facebook](https://www.facebook.com/terms.php) and
  [Instagram](https://help.instagram.com/581066165581870) forbid automated
  access without Meta's permission, and Meta may lock an account that logs
  in from a client it does not recognise.
- Google Messages falls under
  [Google's terms](https://policies.google.com/terms) and under your mobile
  carrier's terms for SMS and RCS, which may charge for or restrict
  automated messages.

Use a dedicated account you can afford to lose, only in conversations where
people know they are talking to a bot, and read
[DISCLAIMER.md](../../docs/DISCLAIMER.md).

## End-to-end encryption

With `MATRIX_E2EE_ENABLED=false` (the default), the bot reads only
unencrypted rooms. In an encrypted room it logs that it cannot decrypt the
message, and it never sends a plaintext reply there.

With `MATRIX_E2EE_ENABLED=true`:

- `MATRIX_STORE_DIR` (by default `runtime/` next to the script, which git
  ignores) holds the device's keys and the sync token. Keep this directory.
  If it is lost, the bot becomes a new device that cannot read anything
  encrypted before that point.
- The device must stay the same across restarts. A password login keeps it
  through the saved session. With an access token, set `MATRIX_DEVICE_ID` to
  the token's device.
- The bot shares its keys with every device in the room, verified or not.
  It cannot verify itself interactively, so people see its device as
  unverified. It has no key backup and no cross-signing.
- A message whose key has not arrived is logged and skipped, not retried.
- A mautrix bridge can encrypt its portals
  ([end-to-bridge encryption](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)).
  The bridge holds those keys on your server, so the protection ends there,
  and the other network carries the message under its own encryption. If
  your bridge encrypts portals, turn `MATRIX_E2EE_ENABLED` on.

## Tests

`tests/test_matrix_connector.py` fakes the Matrix client and the agent, so
it runs without matrix-nio and without a network:

```bash
python -m pytest tests/test_matrix_connector.py
```
