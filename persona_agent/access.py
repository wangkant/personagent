"""Who the agent answers, and who its admin is, on every platform.

Ids are compared in the stores' spelling (see channels): a QQ id is bare,
every other platform's is "<platform>:<id>". A setting may also write a QQ id
as "qq:<id>", and a CONNECTOR_QQ_PLATFORMS id as "<that platform>:<id>".

* ADMIN_IDS: the admin's accounts, one person on many platforms.
* ACCESS_GROUPS / ACCESS_DM_USERS: who the agent admits, per platform. A
  platform with no entries is not restricted here: every QQ group is
  answered, a QQ DM still needs the admin or an entry, and a forwarded
  platform is left to the connector unless it sent ``prefiltered: false``.
* ACCESS_PAUSED_GROUPS: admitted groups where the agent stays silent for now.
* ACCESS_APPROVAL_PLATFORMS: platforms where the two lists apply even while
  empty: a sender or group in neither gets no model turn but a request the
  admin approves (approvals.py), which adds it to the list.

Imports only channels, so settings, preflight and the tools share it without
an import cycle.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Mapping

from . import channels

#: The admin's reply mode, spelled as the eval, evidence and ledger rows store
#: it, so the rows already written keep matching.
ADMIN_MODE = "owner"

#: The identity settings, each a comma list of ids.
IDENTITY_SETTINGS: tuple[str, ...] = ("ADMIN_IDS", "ACCESS_GROUPS",
                                      "ACCESS_DM_USERS", "ACCESS_PAUSED_GROUPS")

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
    """An entry with an empty platform (":1") or an empty id ("telegram:"),
    which names no one; kept, ":1" would read as QQ and close every QQ group."""
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


#: Where the local page names the sender of its own chat. Whoever sits at
#: the page installed the character, so that sender is an owner too; the file
#: sits beside dashboard.token and is as private.
PAGE_OWNER_FILE = "page.owner"
PAGE_PLATFORM = "browser"
#: The platform of conversations held through the OpenAI-compatible API (chat_api).
API_PLATFORM = "api"
def page_owner(runtime: Path) -> frozenset[str]:
    """The page chat's sender as an admin id, or nothing. Read each time: the file is
    one short line, and its time cannot tell two writes inside one clock tick apart."""
    try:
        sender = (runtime / PAGE_OWNER_FILE).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return frozenset()
    usable = 8 <= len(sender) <= 64 and all(c.isascii() and (c.isalnum() or c in "-_") for c in sender)
    return frozenset({f"{PAGE_PLATFORM}:{sender}"}) if usable else frozenset()


def is_admin(user_id, admins: Iterable[str]) -> bool:
    uid = str(user_id or "")
    return bool(uid) and uid in admins


def entries_on(platform: str, ids: Iterable[str]) -> frozenset[str]:
    """The entries of `ids` that belong to `platform`."""
    return frozenset(i for i in ids if channels.platform_of(i) == platform)


def admin_on(platform: str, admins: Iterable[str]) -> str:
    """The admin's account on `platform`, else their QQ one, else "", so
    memories stay with the admin where they have no account."""
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


#: The platforms where new chats wait for the admin's approval.
APPROVAL_SETTING = "ACCESS_APPROVAL_PLATFORMS"
#: Why a chat there is not answered yet, as the log says it.
UNAPPROVED = f"waiting for the admin's approval ({APPROVAL_SETTING})"
#: Platforms whose connection joins only the channels typed into its form,
#: so every group there was chosen by the admin already.
CHANNELS_LISTED_AT_CONNECT = frozenset({"twitch", "irc"})
#: ...and of those, the ones without direct messages: approval holds nothing there.
NOTHING_TO_APPROVE = frozenset({"twitch"})
#: Never subject to approval: whoever sits at the page, and callers holding the API key.
NEVER_APPROVED = frozenset({PAGE_PLATFORM, API_PLATFORM})


def approval_platforms(value) -> frozenset[str]:
    """ACCESS_APPROVAL_PLATFORMS as a set of lowercase platform names."""
    return frozenset(p.lower() for p in split_ids(value)) - NEVER_APPROVED


def awaits_dm_approval(user_id, platform: str, admins: Iterable[str], allowed: Iterable[str],
                       platforms: Iterable[str], *, via_connector: bool) -> bool:
    """Whether a DM sender is held for approval rather than answered or refused.
    `platform` is the event's (a native connector's, for its bare ids)."""
    uid = str(user_id or "")
    if not uid or platform not in platforms or (not via_connector and ":" in uid):
        return False
    return not (is_admin(uid, admins) or uid in allowed)


def awaits_group_approval(group_id, platform: str, allowed: Iterable[str],
                          platforms: Iterable[str], *, via_connector: bool, user_id="") -> bool:
    """Whether a group is held for approval rather than answered or refused."""
    gid = str(group_id or "")
    if (not gid or platform not in platforms or platform in CHANNELS_LISTED_AT_CONNECT
            or (not via_connector and (":" in gid or ":" in str(user_id or "")))):
        return False
    return gid not in allowed


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

    @property
    def paused_groups(self) -> frozenset[str]:
        return self.ids("ACCESS_PAUSED_GROUPS")


def identity_from_env(env: Mapping[str, str] | None = None) -> Identity:
    """The one reader of the identity settings, shared by the agent,
    preflight and the tools so they agree on who the admin is."""
    source = os.environ if env is None else env
    written = {name: split_ids(source.get(name)) for name in IDENTITY_SETTINGS}
    return Identity(written, split_ids(source.get("CONNECTOR_QQ_PLATFORMS")))
