"""Who is the same person across chats. Only the operator is linked: every
admin account (ADMIN_IDS) and every page chat id (`browser:<token>`, minted
anew on New chat). Nobody else is ever linked, whatever a chat claims."""
from __future__ import annotations

import re
from typing import Iterable

from . import access, channels

_PAGE_PREFIX = access.PAGE_PLATFORM + ":"
_CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯豈-﫿]")


def is_page_id(uid: str) -> bool:
    return str(uid or "").startswith(_PAGE_PREFIX)


def operator_ids(admins: Iterable[str], memories: dict) -> frozenset[str]:
    """The admin ids plus every page id memory.json knows, as a key or as a
    note's subject."""
    ids = {str(a) for a in admins if a}
    for key, rows in memories.items():
        uid = channels.dm_user(key)
        if is_page_id(uid):
            ids.add(uid)
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and is_page_id(row.get("user_id")):
                ids.add(str(row["user_id"]))
    return frozenset(ids)


def same_person(uid: str, operator: frozenset[str]) -> frozenset[str]:
    """Every id that is `uid`'s person: the operator set for the operator,
    else just `uid`."""
    uid = str(uid or "")
    if not uid:
        return frozenset()
    if uid in operator or is_page_id(uid):
        return frozenset(operator | {uid})
    return frozenset({uid})


def is_operator_dm(key: str, operator: frozenset[str]) -> bool:
    uid = channels.dm_user(key)
    return bool(uid) and (uid in operator or is_page_id(uid))


def names_in(text: str, rows: Iterable[dict]) -> set[str]:
    """Subjects of `rows` whose display name (2+ characters) `text` names:
    whole words in spaced scripts, any substring for CJK; any case."""
    text = str(text or "")
    low = text.lower()
    found: set[str] = set()
    for row in rows:
        uid, name = str(row.get("user_id") or ""), str(row.get("user_name") or "").strip()
        if not uid or len(name) < 2 or uid in found:
            continue
        if _CJK.search(name):
            if name.lower() in low:
                found.add(uid)
        elif re.search(rf"(?<![\w]){re.escape(name.lower())}(?![\w])", low):
            found.add(uid)
    return found
