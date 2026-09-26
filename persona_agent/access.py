"""Who the agent answers, and who its admin is, on every platform.

Ids here are compared in the spelling the stores use (see channels): a QQ id
is bare, every other platform's is "<platform>:<id>". A setting may also write
a QQ id as "qq:<id>", and an id from a CONNECTOR_QQ_PLATFORMS connector as
"<that platform>:<id>"; both mean the bare key such an event carries.

Three settings, one list each:

* ADMIN_IDS: the admin's accounts. One person on many platforms, sharing
  ADMIN_NAME and ADMIN_RELATIONSHIP.
* ACCESS_GROUPS / ACCESS_DM_USERS: who the agent itself admits, partitioned
  per platform. A platform with no entries is not restricted by the agent:
  every QQ group is answered, a QQ DM still needs the admin or an entry, and a
  forwarded platform is left to the connector's own allowlist unless the event
  says the connector did not filter (``prefiltered: false``).

Pure on purpose: it imports only channels, so settings, preflight and the
offline tools can all ask the same questions without an import cycle.
"""
from __future__ import annotations

import os
from typing import Iterable, Mapping

from . import channels

#: The admin's reply mode, spelled as the eval, evidence and ledger rows store
#: it, so the rows already written keep matching.
ADMIN_MODE = "owner"

#: The identity settings, each a comma list of ids.
IDENTITY_SETTINGS: tuple[str, ...] = ("ADMIN_IDS", "ACCESS_GROUPS",
                                      "ACCESS_DM_USERS")

#: Why /v1/onebot never admits a namespaced id: NapCat only sends QQ numbers,
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


def is_admin(user_id, admins: Iterable[str]) -> bool:
    uid = str(user_id or "")
    return bool(uid) and uid in admins


def entries_on(platform: str, ids: Iterable[str]) -> frozenset[str]:
    """The entries of `ids` that belong to `platform`."""
    return frozenset(i for i in ids if channels.platform_of(i) == platform)


def admin_on(platform: str, admins: Iterable[str]) -> str:
    """The admin's account on `platform`, else their QQ one, else "".

    The QQ fallback is what every conversation used before admins had more
    than one account, so memories keep the attribution they always had."""
    admins = tuple(admins)
    for wanted in (platform, channels.NATIVE_PLATFORM):
        found = sorted(entries_on(wanted, admins))
        if found:
            return found[0]
    return ""


def group_refusal(group_id, allowed: Iterable[str], *, via_connector: bool,
                  prefiltered: bool = True, user_id="") -> str:
    """Why a group is not admitted, naming the setting; "" when it is."""
    gid = str(group_id or "")
    # The sender too: a namespaced sender in a QQ group could match an admin
    # listed on another platform.
    if not via_connector and (":" in gid or ":" in str(user_id or "")):
        return QQ_DOOR_REFUSAL
    platform = channels.platform_of(gid)
    listed = entries_on(platform, allowed)
    if listed:
        if gid in listed:
            return ""
        return f"not in ACCESS_GROUPS, which lists {platform} groups"
    if channels.is_native(gid) or prefiltered:
        return ""
    return (f"ACCESS_GROUPS has no {platform} entries and the connector "
            f"did not filter (prefiltered=false)")


def dm_refusal(user_id, admins: Iterable[str], allowed: Iterable[str], *,
               via_connector: bool, prefiltered: bool = True) -> str:
    """Why a DM sender is not admitted, naming the setting; "" when they are."""
    uid = str(user_id or "")
    if not via_connector and ":" in uid:
        # Before the admin check: an admin-listed namespaced id arriving here
        # is forged by definition.
        return QQ_DOOR_REFUSAL
    if is_admin(uid, admins) or uid in allowed:
        return ""
    platform = channels.platform_of(uid)
    if channels.is_native(uid):
        return ("not in ADMIN_IDS or ACCESS_DM_USERS, one of which every QQ "
                "DM needs")
    if entries_on(platform, allowed):
        return (f"not in ADMIN_IDS or ACCESS_DM_USERS, which lists "
                f"{platform} users")
    if prefiltered:
        return ""
    return (f"ACCESS_DM_USERS has no {platform} entries and the connector "
            f"did not filter (prefiltered=false)")


class Identity:
    """The identity settings as written, and what they add up to."""

    def __init__(self, written: Mapping[str, tuple[str, ...]],
                 native_platforms: Iterable[str] = ()) -> None:
        #: Each name in IDENTITY_SETTINGS -> its entries.
        self.written = {name: tuple(written.get(name, ()))
                        for name in IDENTITY_SETTINGS}
        self.native_platforms = split_ids(native_platforms)

    def ids(self, name: str) -> frozenset[str]:
        """The canonical ids `name` lists."""
        return parse_ids(self.written[name],
                         native_platforms=self.native_platforms)

    @property
    def admins(self) -> frozenset[str]:
        return self.ids("ADMIN_IDS")

    @property
    def groups(self) -> frozenset[str]:
        return self.ids("ACCESS_GROUPS")

    @property
    def dm_users(self) -> frozenset[str]:
        return self.ids("ACCESS_DM_USERS")


def identity_from_env(env: Mapping[str, str] | None = None) -> Identity:
    """The one reader of the identity settings.

    The agent, preflight and the offline tools all read them here, so the
    admin the operator CLI exempts is the admin the agent exempts."""
    source = os.environ if env is None else env
    written = {name: split_ids(source.get(name)) for name in IDENTITY_SETTINGS}
    return Identity(written, split_ids(source.get("CONNECTOR_QQ_PLATFORMS")))
