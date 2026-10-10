"""One vocabulary for conversation keys, across every channel.

A conversation has three names: routing (transport, locks, buffers), memory
(`memories` / `core_memory`) and learning (the `conv_id` of every evidence
event and candidate scope, which retrieval compares against):

    channel        routing               memory                learning
    ------------------------------------------------------------------------
    QQ group       "123456"              "123456"              "123456"
    QQ DM          "private:777"         "private:777"         "dm:777"
    connector room "telegram:c1"         "telegram:c1"         "telegram:c1"
    connector DM   "private:telegram:1"  "private:telegram:1"  "dm:telegram:1"

The mapping lives here alone; call sites must not re-derive it.
"""
from __future__ import annotations

#: Prefix the ROUTING and MEMORY keys use for a one-to-one conversation.
DM_ROUTING_PREFIX = "private:"

#: Prefix the LEARNING scope uses; changing it would orphan every stored DM candidate.
DM_LEARNING_PREFIX = "dm:"

#: The platform a bare (un-namespaced) key belongs to.
NATIVE_PLATFORM = "qq"


def is_dm(routing_key: str) -> bool:
    """Is this key a one-to-one conversation rather than a room."""
    return str(routing_key or "").startswith(DM_ROUTING_PREFIX)


def learning_key(routing_key: str) -> str:
    """The LEARNING key for a routing key (`private:x` -> `dm:x`); any other
    key is its own learning key."""
    key = str(routing_key or "")
    if not is_dm(key):
        return key
    return DM_LEARNING_PREFIX + key[len(DM_ROUTING_PREFIX):]


def platform_of(key: str) -> str:
    """The platform of a routing or learning key. `dm:` and `private:` are DM
    markers, not platforms; evidence from two platforms never combines."""
    value = str(key or "")
    if ":" not in value:
        return NATIVE_PLATFORM
    for marker in (DM_LEARNING_PREFIX, DM_ROUTING_PREFIX):
        if value.startswith(marker):
            rest = value[len(marker):]
            # `<marker><uid>` is native; an empty platform (`private::9`) falls back.
            if ":" not in rest:
                return NATIVE_PLATFORM
            return rest.split(":", 1)[0] or NATIVE_PLATFORM
    return value.split(":", 1)[0] or NATIVE_PLATFORM


def is_native(key: str) -> bool:
    """Does this key read as native ("123456", "private:777"), and so face
    the QQ whitelists whichever door it came through."""
    return platform_of(key) == NATIVE_PLATFORM


def dm_routing_key(user_id: str) -> str:
    """The routing/memory key for a one-to-one conversation with `user_id`."""
    return f"{DM_ROUTING_PREFIX}{user_id}"


def dm_learning_key(user_id: str) -> str:
    """The learning scope for a one-to-one conversation with `user_id`."""
    return f"{DM_LEARNING_PREFIX}{user_id}"
