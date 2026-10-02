"""One vocabulary for conversation keys, across every channel.

A conversation has THREE names here and they are not interchangeable:

* **routing** — what the transport, the locks and the debounce buffers use.
  This is the key the inbound path mints and passes around.
* **memory** — the namespace `memories` / `core_memory` are stored under.
* **learning** — the `conv_id` written into every evidence event and every
  candidate scope, and therefore the one retrieval must compare against.

The table, in full:

    channel        routing               memory                learning
    ------------------------------------------------------------------------
    QQ group       "123456"              "123456"              "123456"
    QQ DM          "private:777"         "private:777"         "dm:777"
    connector room "telegram:c1"         "telegram:c1"         "telegram:c1"
    connector DM   "private:telegram:1"  "private:telegram:1"  "dm:telegram:1"

The mapping lives here alone; call sites must not re-derive it:

* retrieval must look promoted examples up under the LEARNING key, the one
  every writer uses. `_authorized_view` compares all six scope fields and the
  MEMORY key differs on two of them, so nothing a DM taught the bot would be
  authorized back into a DM prompt, silently, on every turn.
* `platform_of` must not read the whole `dm:` prefix as QQ. A Telegram DM
  scope would compare compatible with a QQ DM scope under
  `PROMOTE_REQUIRE_SAME_CONVERSATION=false`, the cross-platform combination
  the evidence rules forbid.
* `transport._evict_conversation` uses `learning_key` for the same
  `private:` -> `dm:` step rather than spelling it by hand.
"""
from __future__ import annotations

#: Prefix the ROUTING and MEMORY keys use for a one-to-one conversation.
DM_ROUTING_PREFIX = "private:"

#: Prefix the LEARNING scope uses for the same thing. Different on purpose and
#: load-bearing: `dm:` is what every evidence writer spells, and changing it
#: would orphan every DM candidate already in a live ledger.
DM_LEARNING_PREFIX = "dm:"

#: The platform a bare key belongs to. QQ ids carry no namespace because QQ
#: was the only channel when the key format was chosen.
NATIVE_PLATFORM = "qq"


def is_dm(routing_key: str) -> bool:
    """Is this key a one-to-one conversation rather than a room."""
    return str(routing_key or "").startswith(DM_ROUTING_PREFIX)


def learning_key(routing_key: str) -> str:
    """The LEARNING scope for the conversation a routing key names.

    Connector DMs map correctly too: `private:telegram:1` -> `dm:telegram:1`,
    which is what the writers spell. A key that is not a DM is its own
    learning key, so this is safe to apply unconditionally.
    """
    key = str(routing_key or "")
    if not is_dm(key):
        return key
    return DM_LEARNING_PREFIX + key[len(DM_ROUTING_PREFIX):]


def platform_of(key: str) -> str:
    """Which platform a conversation belongs to, from either spelling.

    Accepts a routing key or a learning key, because callers hold both.

    Evidence from two platforms is never combined, so this has to be right
    rather than merely plausible: `dm:` and `private:` are DM MARKERS, not
    platforms, and what follows them may carry a platform of its own.
    """
    value = str(key or "")
    if ":" not in value:
        return NATIVE_PLATFORM
    for marker in (DM_LEARNING_PREFIX, DM_ROUTING_PREFIX):
        if value.startswith(marker):
            rest = value[len(marker):]
            # `<marker><uid>` is native; `<marker><platform>:<id>` is not.
            # The `or NATIVE_PLATFORM` matters for the same reason it does on
            # the room branch below: an empty prefix (`private::9`) must fall
            # back rather than return "", which no scope would ever match.
            if ":" not in rest:
                return NATIVE_PLATFORM
            return rest.split(":", 1)[0] or NATIVE_PLATFORM
    return value.split(":", 1)[0] or NATIVE_PLATFORM


def is_native(key: str) -> bool:
    """Does this key claim NATIVE-platform authority.

    True for "123456" and "private:777", false for "telegram:c1" and
    "dm:telegram:1". The QQ entries of ADMIN_IDS, ACCESS_GROUPS and
    ACCESS_DM_USERS are bare ids, so a key that reads as native is asking to
    be measured against them — whichever door it arrived through. That is the
    question the whitelist gates have to ask: a connector authorized to mint
    native ids must not thereby escape the whitelists those ids belong to.
    """
    return platform_of(key) == NATIVE_PLATFORM


def dm_routing_key(user_id: str) -> str:
    """The routing/memory key for a one-to-one conversation with `user_id`."""
    return f"{DM_ROUTING_PREFIX}{user_id}"


def dm_learning_key(user_id: str) -> str:
    """The learning scope for a one-to-one conversation with `user_id`."""
    return f"{DM_LEARNING_PREFIX}{user_id}"
