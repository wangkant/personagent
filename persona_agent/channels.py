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
    gateway room   "telegram:c1"         "telegram:c1"         "telegram:c1"
    gateway DM     "private:telegram:1"  "private:telegram:1"  "dm:telegram:1"

WHY THIS MODULE EXISTS. Three call sites derived that mapping independently
and two of them got it wrong:

* retrieval read promoted examples under the MEMORY key while every writer
  used the LEARNING one. `_authorized_view` compares all six scope fields and
  these disagree on two of them, so nothing a DM ever taught the bot could be
  authorized back into a DM prompt — silently, on every turn.
* `_conv_platform` read the whole `dm:` prefix as QQ, so every Telegram and
  Discord DM was stamped `platform="qq"`. With
  `PROMOTE_REQUIRE_SAME_CONVERSATION=false` a Telegram DM scope and a QQ DM
  scope then compared compatible — the exact cross-platform combination that
  function's docstring promises never happens.
* `transport._evict_conversation` spells the same `private:` -> `dm:` step by
  hand a third time.

Each was a small, reasonable line of code. The defect was that there were
three of them.
"""
from __future__ import annotations

#: Prefix the ROUTING and MEMORY keys use for a one-to-one conversation.
DM_ROUTING_PREFIX = "private:"

#: Prefix the LEARNING scope uses for the same thing. Different on purpose and
#: load-bearing: `dm:` is what every evidence writer has always spelled, and
#: changing it would orphan every DM candidate already in a live ledger.
DM_LEARNING_PREFIX = "dm:"

#: The platform a bare key belongs to. QQ ids carry no namespace because QQ
#: was the only channel when the key format was chosen.
NATIVE_PLATFORM = "qq"


def is_dm(routing_key: str) -> bool:
    """Is this key a one-to-one conversation rather than a room."""
    return str(routing_key or "").startswith(DM_ROUTING_PREFIX)


def learning_key(routing_key: str) -> str:
    """The LEARNING scope for the conversation a routing key names.

    Gateway DMs map correctly too: `private:telegram:1` -> `dm:telegram:1`,
    which is what the writers spell. A key that is not a DM is its own
    learning key, so this is safe to apply unconditionally.
    """
    key = str(routing_key or "")
    if not is_dm(key):
        return key
    return DM_LEARNING_PREFIX + key[len(DM_ROUTING_PREFIX):]


def platform_of(key: str) -> str:
    """Which platform a conversation belongs to, from either spelling.

    Accepts a routing key or a learning key, because callers hold both and
    asking them to remember which is which is how the two prefixes drifted
    apart in the first place.

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
            return rest.split(":", 1)[0] if ":" in rest else NATIVE_PLATFORM
    return value.split(":", 1)[0] or NATIVE_PLATFORM


def dm_routing_key(user_id: str) -> str:
    """The routing/memory key for a one-to-one conversation with `user_id`."""
    return f"{DM_ROUTING_PREFIX}{user_id}"


def dm_learning_key(user_id: str) -> str:
    """The learning scope for a one-to-one conversation with `user_id`."""
    return f"{DM_LEARNING_PREFIX}{user_id}"
