"""Who the agent answers, and who its admin is, on every platform.

Ids here are compared in the spelling the stores use (see channels): a QQ id
is bare, every other platform's is "<platform>:<id>". A setting may also write
a QQ id as "qq:<id>", and an id from a GATEWAY_NATIVE_PLATFORMS forwarder as
"<that platform>:<id>"; both mean the bare key such an event carries.

Three settings, one list each:

* ADMIN_IDS: the admin's accounts. One person on many platforms, sharing
  ADMIN_NAME and ADMIN_RELATIONSHIP. The code calls them the owner, the
  name the settings had until 0.5.
* ALLOWED_GROUPS / ALLOWED_DM_USERS: who the agent itself admits, partitioned
  per platform. A platform with no entries is not restricted by the agent:
  every QQ group is answered, a QQ DM still needs the admin or an entry, and a
  forwarded platform is left to the forwarder's own allowlist unless the event
  says the forwarder did not filter (``prefiltered: false``).

Pure on purpose: it imports only channels, so settings, preflight and the
offline tools can all ask the same questions without an import cycle.
"""
from __future__ import annotations

import os
from typing import Iterable, Mapping

from . import channels

#: Each identity setting, and the older names folded into it. The old names
#: are merged by UNION: a half-migrated .env (ADMIN_IDS=telegram:1 with
#: OWNER_QQ still set) must keep the QQ admin it already had.
IDENTITY_SETTINGS: dict[str, tuple[str, ...]] = {
    "ADMIN_IDS": ("OWNER_QQ", "GATEWAY_OWNER_IDS"),
    "ALLOWED_GROUPS": ("QQ_GROUPS",),
    "ALLOWED_DM_USERS": ("PRIVATE_ALLOWED_QQS",),
}

#: The old names, which still work and are no longer advertised.
LEGACY_SETTINGS: frozenset[str] = frozenset(
    old for olds in IDENTITY_SETTINGS.values() for old in olds)

#: Read as one id, not a comma list, exactly as it always was.
_SINGLE_VALUE = frozenset({"OWNER_QQ"})

#: Why /webhook/qq never admits a namespaced id: NapCat only sends QQ numbers,
#: so one arriving there was written by someone else.
QQ_DOOR_REFUSAL = "the QQ webhook carries bare QQ ids only"


def split_ids(values) -> tuple[str, ...]:
    """Trimmed non-empty entries: a comma list, or any iterable of ids."""
    if values is None:
        return ()
    parts = values.split(",") if isinstance(values, str) else values
    out = []
    for part in parts:
        if part is None:
            continue
        text = str(part).strip()
        if text:
            out.append(text)
    return tuple(out)


def canonical_id(raw, native_platforms: Iterable[str] = ()) -> str:
    """The key an event from this id carries: "qq:" and native prefixes go."""
    value = str(raw or "").strip()
    prefix, sep, rest = value.partition(":")
    if sep and rest and (prefix == channels.NATIVE_PLATFORM
                         or prefix in split_ids(native_platforms)):
        return rest
    return value


def is_malformed(entry: str) -> bool:
    """An entry with an empty platform (":1") or an empty id ("telegram:").

    Neither names anyone, and kept as-is either would be counted as an entry
    on a platform: ":1" reads as QQ, so it would close every QQ group."""
    prefix, sep, rest = str(entry).partition(":")
    return bool(sep) and (not prefix or not rest)


def canonical_ids(*lists, native_platforms: Iterable[str] = ()) -> tuple[str, ...]:
    """Every entry of `lists`, canonical, in order, without duplicates.

    Malformed entries (see `is_malformed`) are dropped."""
    natives = split_ids(native_platforms)
    seen: dict[str, None] = {}
    for values in lists:
        for entry in split_ids(values):
            if is_malformed(entry):
                continue
            seen.setdefault(canonical_id(entry, natives), None)
    return tuple(seen)


def parse_ids(*lists, native_platforms: Iterable[str] = ()) -> frozenset[str]:
    """`canonical_ids` as a set, for membership tests."""
    return frozenset(canonical_ids(*lists, native_platforms=native_platforms))


def is_owner(user_id, owners: Iterable[str]) -> bool:
    uid = str(user_id or "")
    return bool(uid) and uid in owners


def entries_on(platform: str, ids: Iterable[str]) -> frozenset[str]:
    """The entries of `ids` that belong to `platform`."""
    return frozenset(i for i in ids if channels.platform_of(i) == platform)


def owner_on(platform: str, owners: Iterable[str]) -> str:
    """The owner's account on `platform`, else their QQ one, else "".

    The QQ fallback is what every conversation used before owners had more
    than one account, so memories keep the attribution they always had."""
    owners = tuple(owners)
    for wanted in (platform, channels.NATIVE_PLATFORM):
        found = sorted(entries_on(wanted, owners))
        if found:
            return found[0]
    return ""


def _setting(name: str, platform: str) -> str:
    """`name` as a refusal names it; QQ entries may still be under the old one."""
    if platform != channels.NATIVE_PLATFORM:
        return name
    return f"{name} (or {', '.join(IDENTITY_SETTINGS[name])})"


def group_refusal(group_id, allowed: Iterable[str], *, via_forwarder: bool,
                  prefiltered: bool = True) -> str:
    """Why a group is not admitted, naming the setting; "" when it is."""
    gid = str(group_id or "")
    if not via_forwarder and ":" in gid:
        return QQ_DOOR_REFUSAL
    platform = channels.platform_of(gid)
    listed = entries_on(platform, allowed)
    if listed:
        if gid in listed:
            return ""
        return (f"not in {_setting('ALLOWED_GROUPS', platform)}, which lists "
                f"{platform} groups")
    if channels.is_native(gid) or prefiltered:
        return ""
    return (f"ALLOWED_GROUPS has no {platform} entries and the connector "
            f"did not filter (prefiltered=false)")


def dm_refusal(user_id, owners: Iterable[str], allowed: Iterable[str], *,
               via_forwarder: bool, prefiltered: bool = True) -> str:
    """Why a DM sender is not admitted, naming the setting; "" when they are."""
    uid = str(user_id or "")
    if not via_forwarder and ":" in uid:
        # Before the owner check: an owner-listed namespaced id arriving here
        # is forged by definition.
        return QQ_DOOR_REFUSAL
    if is_owner(uid, owners) or uid in allowed:
        return ""
    platform = channels.platform_of(uid)
    if channels.is_native(uid):
        return (f"not in ADMIN_IDS or {_setting('ALLOWED_DM_USERS', platform)}"
                f", one of which every QQ DM needs")
    if entries_on(platform, allowed):
        return (f"not in ADMIN_IDS or ALLOWED_DM_USERS, which lists "
                f"{platform} users")
    if prefiltered:
        return ""
    return (f"ALLOWED_DM_USERS has no {platform} entries and the connector "
            f"did not filter (prefiltered=false)")


class Identity:
    """The identity settings as written, and what they add up to."""

    def __init__(self, written: Mapping[str, tuple[str, ...]],
                 native_platforms: Iterable[str] = ()) -> None:
        #: Every name in IDENTITY_SETTINGS, new and old, -> its entries.
        self.written = {name: tuple(written.get(name, ()))
                        for name in ALL_NAMES}
        self.native_platforms = split_ids(native_platforms)

    def merged(self, name: str) -> tuple[str, ...]:
        """`name`'s entries, then its old names', deduplicated, as written."""
        seen: dict[str, None] = {}
        for source in (name, *IDENTITY_SETTINGS[name]):
            for entry in self.written[source]:
                seen.setdefault(entry, None)
        return tuple(seen)

    def ids(self, name: str) -> frozenset[str]:
        """The canonical ids `name` means once its old names are folded in."""
        return parse_ids(self.merged(name),
                         native_platforms=self.native_platforms)

    @property
    def owners(self) -> frozenset[str]:
        return self.ids("ADMIN_IDS")

    @property
    def groups(self) -> frozenset[str]:
        return self.ids("ALLOWED_GROUPS")

    @property
    def dm_users(self) -> frozenset[str]:
        return self.ids("ALLOWED_DM_USERS")


#: Every identity setting name, new ones first.
ALL_NAMES: tuple[str, ...] = (
    tuple(IDENTITY_SETTINGS) + tuple(sorted(LEGACY_SETTINGS)))


def identity_from_env(env: Mapping[str, str] | None = None) -> Identity:
    """The one reader of the identity settings.

    The agent, preflight and the offline tools all read them here, so the
    admin the operator CLI exempts is the admin the agent exempts."""
    source = os.environ if env is None else env
    written = {}
    for name in ALL_NAMES:
        raw = source.get(name)
        if name in _SINGLE_VALUE:
            text = str(raw or "").strip()
            written[name] = (text,) if text else ()
        else:
            written[name] = split_ids(raw)
    return Identity(written, split_ids(source.get("GATEWAY_NATIVE_PLATFORMS")))
