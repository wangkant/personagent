"""Tests for access.py: whose ids mean what, and who is admitted where.

The module is pure, so the admission matrix is tested here without an agent;
tests/test_gateway.py drives the same rules through the real one."""
from __future__ import annotations

from persona_agent import access


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English."""
    assert cond, name + (f" - {detail}" if detail else "")


def test_ids_are_canonicalised_to_the_keys_events_carry() -> None:
    natives = ("aiocqhttp",)
    check("a bare id is QQ and stays bare", access.canonical_id("123") == "123")
    check("qq: is the same QQ id", access.canonical_id("qq:123") == "123")
    check("a native forwarder's prefix is dropped, as its events are minted",
          access.canonical_id("aiocqhttp:10000", natives) == "10000")
    check("the same prefix is kept when that platform is not native",
          access.canonical_id("aiocqhttp:10000") == "aiocqhttp:10000")
    check("any other platform keeps its prefix, case included",
          access.canonical_id("Telegram:42", natives) == "Telegram:42")
    check("whitespace is trimmed", access.canonical_id("  qq:7 ") == "7")
    check("a native list may be a comma string",
          access.canonical_id("aiocqhttp:1", "aiocqhttp, x") == "1")
    ids = access.canonical_ids(
        "qq:1, 1 ,telegram:-100,,telegram:", ["2", None, " "],
        native_platforms=natives)
    check("lists merge in order, duplicates and empties dropped",
          ids == ("1", "telegram:-100", "2"), repr(ids))
    check("an entry naming no one does not survive to opt a platform in",
          "telegram:" not in ids and not access.parse_ids("qq:"))
    check("nor does one naming no platform: ':1' would read as a QQ entry",
          not access.parse_ids(":1") and access.is_malformed(":1")
          and access.is_malformed("telegram:")
          and not access.is_malformed("telegram:1")
          and not access.is_malformed("1"))
    check("a single string in a tuple is one id, not a comma list",
          access.parse_ids(("1,2",)) == {"1,2"})


def test_owners_are_found_on_their_platform() -> None:
    owners = access.parse_ids("10000,telegram:1,discord:2")
    check("is_owner by exact key", access.is_owner("telegram:1", owners))
    check("an empty id is nobody's owner", not access.is_owner("", {""}))
    check("the owner's account on the conversation's platform",
          access.owner_on("telegram", owners) == "telegram:1")
    check("else their QQ one, which every room used before",
          access.owner_on("slack", owners) == "10000")
    check("else no one",
          access.owner_on("slack", {"telegram:1"}) == "")
    check("entries_on partitions by platform",
          access.entries_on("qq", owners) == {"10000"}
          and access.entries_on("discord", owners) == {"discord:2"})


def test_group_admission_is_partitioned_per_platform() -> None:
    def refusal(gid, allowed, *, fwd=True, pre=True):
        return access.group_refusal(gid, access.parse_ids(allowed),
                                    via_forwarder=fwd, prefiltered=pre)

    # QQ: empty means every group, entries mean only those.
    check("QQ, no entries: every group", refusal("555", "", fwd=False) == "")
    check("QQ, listed", refusal("123", "123", fwd=False) == "")
    check("QQ, not listed: refused naming ALLOWED_GROUPS and its old name",
          "ALLOWED_GROUPS" in refusal("555", "123", fwd=False)
          and "QQ_GROUPS" in refusal("555", "123", fwd=False))
    check("QQ entries apply to a native forwarder's bare ids too",
          refusal("555", "123") != "" and refusal("123", "123") == "")
    check("a Telegram entry does not close QQ",
          refusal("555", "telegram:-100", fwd=False) == "")

    # A forwarded platform: the forwarder's list until it has entries.
    check("Telegram, no entries: left to the forwarder",
          refusal("telegram:-200", "123") == "")
    check("Telegram, listed", refusal("telegram:-100", "telegram:-100") == "")
    check("Telegram, entries but not this one",
          "telegram" in refusal("telegram:-200", "telegram:-100"))
    check("another platform's entries leave Telegram alone",
          refusal("telegram:-200", "discord:9") == "")
    check("prefiltered=false with no entries: refused",
          "prefiltered=false" in refusal("telegram:-200", "", pre=False))
    check("prefiltered=false with the group listed: admitted",
          refusal("telegram:-100", "telegram:-100", pre=False) == "")
    check("prefiltered=false never tightens QQ, which the agent always gates",
          refusal("555", "", pre=False) == "")

    check("the QQ webhook refuses a namespaced group outright",
          refusal("telegram:-100", "telegram:-100", fwd=False)
          == access.QQ_DOOR_REFUSAL)
    check("even one spelled qq:, which NapCat never sends",
          refusal("qq:123", "", fwd=False) == access.QQ_DOOR_REFUSAL)


def test_dm_admission_is_partitioned_per_platform() -> None:
    owners = access.parse_ids("10000,telegram:1")

    def refusal(uid, allowed, *, fwd=True, pre=True):
        return access.dm_refusal(uid, owners, access.parse_ids(allowed),
                                 via_forwarder=fwd, prefiltered=pre)

    check("QQ: the owner", refusal("10000", "", fwd=False) == "")
    check("QQ: a listed user", refusal("888", "888", fwd=False) == "")
    check("QQ: an empty list still means owner only",
          "ALLOWED_DM_USERS" in refusal("555", "", fwd=False)
          and "PRIVATE_ALLOWED_QQS" in refusal("555", "", fwd=False))
    check("QQ: same through a native forwarder", refusal("555", "") != "")

    check("Telegram, no entries: left to the forwarder",
          refusal("telegram:43", "") == "")
    check("Telegram, listed", refusal("telegram:42", "telegram:42") == "")
    check("Telegram, entries but not this one: refused",
          "telegram" in refusal("telegram:43", "telegram:42"))
    check("Telegram owner: admitted whatever the list says",
          refusal("telegram:1", "telegram:42", pre=False) == "")
    check("an owner on Telegram does not by itself opt Telegram in",
          refusal("telegram:43", "888") == "")
    check("prefiltered=false with no entries: refused",
          "prefiltered=false" in refusal("telegram:43", "", pre=False))

    check("the QQ webhook refuses a namespaced owner: it is forged",
          refusal("telegram:1", "", fwd=False) == access.QQ_DOOR_REFUSAL)
    check("a Telegram refusal names only the new setting",
          "PRIVATE_ALLOWED_QQS" not in refusal("telegram:43", "telegram:42"))


def test_the_identity_reader_folds_the_old_names_in_by_union() -> None:
    env = {
        "ADMIN_IDS": "telegram:1, qq:5", "OWNER_QQ": " 10000 ",
        "GATEWAY_OWNER_IDS": "discord:2,aiocqhttp:7",
        "GATEWAY_NATIVE_PLATFORMS": "aiocqhttp",
        "ALLOWED_GROUPS": "telegram:-100", "QQ_GROUPS": "1,2",
        "ALLOWED_DM_USERS": "slack:U1", "PRIVATE_ALLOWED_QQS": "8",
    }
    ident = access.identity_from_env(env)
    check("owners: every name, canonical",
          ident.owners == {"telegram:1", "5", "10000", "discord:2", "7"},
          repr(ident.owners))
    check("groups: new and old together",
          ident.groups == {"telegram:-100", "1", "2"}, repr(ident.groups))
    check("DM users: new and old together",
          ident.dm_users == {"slack:U1", "8"}, repr(ident.dm_users))
    check("merged keeps the order written, new name first",
          ident.merged("ALLOWED_GROUPS") == ("telegram:-100", "1", "2"))
    check("what was written is kept per name, for preflight",
          ident.written["QQ_GROUPS"] == ("1", "2")
          and ident.written["OWNER_QQ"] == ("10000",))

    old = access.identity_from_env({"OWNER_QQ": "42", "QQ_GROUPS": "g1",
                                    "PRIVATE_ALLOWED_QQS": "p1"})
    check("an .env with only the old names means what it always did",
          (old.owners, old.groups, old.dm_users)
          == ({"42"}, {"g1"}, {"p1"}))
    check("OWNER_QQ is one id, as it always was",
          access.identity_from_env({"OWNER_QQ": "1,2"}).owners == {"1,2"})
    check("nothing set is nobody",
          not access.identity_from_env({}).owners
          and not access.identity_from_env({}).groups)
    half = access.identity_from_env({"ADMIN_IDS": "telegram:1",
                                     "OWNER_QQ": "10000"})
    check("a half-migrated .env keeps its QQ owner",
          half.owners == {"telegram:1", "10000"}, repr(half.owners))
