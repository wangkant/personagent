"""The character's life: what it does now, how long it has lived here, its days."""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from persona_agent import candidates, life
from persona_agent.library import DISMISSED, KEPT, Item, Library

NOW = 1_800_000_000
OWNER = "browser:owner-page-1"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(life, "clock", lambda: NOW)


def promoted(cid: str, conv: str, reply: str, better: str = "", at: str = "2027-01-15T08:00:00") -> dict:
    return {"candidate_id": cid, "state": candidates.STATE_PROMOTED, "scope": {"conv_id": conv},
            "reply": reply, "better": better, "created_at": at,
            "history": [{"state": candidates.STATE_PROMOTED, "ts": at}]}


def sources(tmp_path, **kw) -> life.Sources:
    memories = {
        f"private:{OWNER}": [{"id": "n1", "text": "Likes slow travel films", "time": NOW - 50, "born": NOW - 50},
                             {"id": "n2", "text": "Their friend Mei bakes", "user_id": "telegram:9",
                              "time": NOW - 40, "born": NOW - 40}],
        "telegram:-100": [{"id": "n3", "text": "Alex moved to Oslo", "user_id": "telegram:5",
                           "time": NOW - 30, "born": NOW - 30},
                          {"id": "n4", "text": "Is learning the cello", "user_id": OWNER,
                           "time": NOW - 20, "born": NOW - 20}],
    }
    ledger = [promoted("c-dm", f"dm:{OWNER}", "have you tried rebooting", "that sounds annoying"),
              promoted("c-group", "telegram:-100", "Alex is wrong", "fair point, Alex"),
              promoted("c-all", "", "ok", ""),
              {"candidate_id": "c-seen", "state": candidates.STATE_PROPOSED, "scope": {}}]
    values = dict(memories=memories, admins=frozenset(), ledger=ledger, configured=True)
    values.update(kw)
    return life.Sources(tmp_path, **values)


# ------------------------------------------------------------------ now ----

def test_the_now_line_follows_what_is_true(tmp_path):
    library = Library(tmp_path)
    assert life.now_state(library, NOW, running=False)["state"] == "off"
    assert life.now_state(library, NOW, running=True)["state"] == "home"
    asleep = life.now_state(library, NOW, running=True, sleep_until=NOW + 3600)
    assert (asleep["state"], asleep["until"]) == ("asleep", NOW + 3600)
    answering = life.now_state(library, NOW, running=True, busy=("telegram", "group"))
    assert (answering["state"], answering["where"], answering["chat"]) == ("answering", "telegram", "group")
    library.left("Bilibili", now=NOW - 100)
    out = life.now_state(library, NOW, running=True, busy=("telegram", "group"))
    assert (out["state"], out["where"], out["since"]) == ("out", "Bilibili", NOW - 100), "out comes first"
    library.returned(3, now=NOW - 60)
    back = life.now_state(library, NOW, running=True)
    assert (back["state"], back["count"], back["until"]) == ("back", 3, NOW - 60 + life.BACK_S)
    assert life.now_state(library, NOW + life.BACK_S, running=True)["state"] == "home", "back lasts ten minutes"
    library.returned(0, now=NOW)
    assert life.now_state(library, NOW + 1, running=True)["state"] == "home", "a walk with nothing is not news"


def test_sleep_hours_are_on_the_persona_clock_and_end_at_seven():
    zone = timezone(timedelta(hours=8))
    at_three = datetime(2027, 3, 1, 3, 30, tzinfo=zone).timestamp()
    assert life.asleep_until(at_three, 8) == int(datetime(2027, 3, 1, 7, 0, tzinfo=zone).timestamp())
    assert life.asleep_until(datetime(2027, 3, 1, 12, 0, tzinfo=zone).timestamp(), 8) is None
    assert life.asleep_until(at_three, 0) is None, "the same moment is 19:30 in UTC"


def test_a_reply_in_flight_names_its_platform_and_kind_only():
    agent = SimpleNamespace(_pending_outbound={"telegram:-100": SimpleNamespace(busy=False),
                                               "private:discord:42": SimpleNamespace(busy=True)})
    assert life.busy_chat(agent) == ("discord", "dm")
    assert life.busy_chat(SimpleNamespace()) is None


class Roam:
    def __init__(self, missing="", allowed=(True, "")):
        self.missing, self.allowed, self.asked = missing, allowed, 0

    def available(self):
        return self.missing

    def can_go_out(self):
        return self.allowed

    def request(self):
        self.asked += 1


def test_going_out_is_asked_of_the_roam_part_and_its_absence_is_off():
    assert life.can_go_out(None) == (False, "off")
    assert life.can_go_out(SimpleNamespace()) == (False, "off")
    assert life.can_go_out(SimpleNamespace(roam=Roam(missing="no_browser"))) == (False, "no_browser")
    assert life.can_go_out(SimpleNamespace(roam=Roam(allowed=(False, "recent")))) == (False, "recent")
    assert life.can_go_out(SimpleNamespace(roam=Roam())) == (True, "")

    class Broken(Roam):
        def can_go_out(self):
            raise RuntimeError("down")
    assert life.can_go_out(SimpleNamespace(roam=Broken())) == (False, "off")


# --------------------------------------------------------------- growth ----

def test_the_birth_is_marked_once_and_only_once_configured(tmp_path):
    unset = life.Sources(tmp_path, configured=False)
    assert life.born(unset) == 0 and not (tmp_path / life.BORN_FILE).exists()
    src = life.Sources(tmp_path, configured=True)
    assert life.born(src, NOW) == NOW
    assert life.born(src, NOW + 86400 * 3) == NOW, "the marker is never moved"
    assert json.loads((tmp_path / life.BORN_FILE).read_text(encoding="utf-8")) == {"at": NOW}


def test_a_home_older_than_the_marker_dates_from_its_first_note(tmp_path):
    src = sources(tmp_path)
    assert life.born(src, NOW) == NOW - 50


def test_days_and_levels_count_up_by_bands_and_never_down():
    assert life.day_count(0, NOW) == 0
    start = time.mktime((2027, 1, 1, 12, 0, 0, 0, 0, -1))
    assert life.day_count(int(start), start + 3600) == 1
    assert life.day_count(int(start), time.mktime((2027, 1, 7, 9, 0, 0, 0, 0, -1))) == 7
    assert [life.level(d) for d in (0, 1, 6, 7, 29, 30, 99, 100, 364, 365, 2000)] == [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


def test_growth_counts_only_what_is_about_the_owner(tmp_path):
    src = sources(tmp_path, admins=frozenset({OWNER}))
    library = Library(tmp_path)
    kept = library.add(Item(url="https://example.test/a", seen_at=NOW - 5))
    library.change(kept.id, state=KEPT)
    library.add(Item(url="https://example.test/b", seen_at=NOW - 4))
    library.left("Bilibili", now=NOW - 300)
    library.returned(1, sites=["Bilibili", "YouTube"], now=NOW - 200)
    grown = life.growth(src, NOW)
    # n1 (no other subject in the owner's chat) and n4 (the owner, said in a group).
    assert grown == {"day": 1, "level": 1, "remembers": 2, "learned": 3, "sites": 2, "kept": 1}


def test_what_to_tell_waits_a_week_then_lives_in_the_days_only(tmp_path):
    library = Library(tmp_path)
    old = library.add(Item(url="https://example.test/old", fits=True, seen_at=NOW - 8 * 86400))
    new = library.add(Item(url="https://example.test/new", fits=True, seen_at=NOW - 3600))
    assert [i.id for i in life.tell_queue(library, NOW)] == [new.id]
    assert old.id in [e["id"] for e in life.entries(life.Sources(tmp_path), NOW)]


# ----------------------------------------------------------------- days ----

def test_the_days_are_newest_first_and_keep_other_people_out(tmp_path):
    src = sources(tmp_path, admins=frozenset({OWNER}))
    library = Library(tmp_path)
    saw = library.add(Item(url="https://www.bilibili.com/video/BV1", site="Bilibili", kind="video",
                           title="Night train", why="It looked like the films you like.",
                           embed="https://player.bilibili.com/player.html?bvid=BV1", seen_at=NOW - 10))
    gone = library.add(Item(url="https://example.test/gone", seen_at=NOW - 9))
    library.change(gone.id, state=DISMISSED)
    found = life.entries(src, NOW)
    kinds = [e["kind"] for e in found]
    assert kinds[0] == "saw" and found[0]["card"]["embed"].startswith("https://player.bilibili.com/")
    assert found[0]["text"] == "It looked like the films you like."
    assert gone.id not in [e["id"] for e in found], "what the owner turned down is gone from the days"
    texts = " ".join(e["text"] + e.get("instead", "") for e in found)
    assert "Is learning the cello" in texts and "Likes slow travel films" in texts
    for private in ("Alex", "Mei", "telegram"):
        assert private not in texts and private not in json.dumps(found), private
    learned = [e for e in found if e["kind"] == "learned"]
    assert {e["id"] for e in learned} == {"learned:c-dm", "learned:c-all"}
    dm = next(e for e in learned if e["id"] == "learned:c-dm")
    assert (dm["text"], dm["instead"]) == ("that sounds annoying", "have you tried rebooting")
    assert "arrived" in kinds and saw.id in [e["id"] for e in found]
    ats = [(e["at"], e["id"]) for e in found]
    assert ats == sorted(ats, reverse=True)


def test_the_days_page_and_the_kept_shelf(tmp_path):
    library = Library(tmp_path)
    made = [library.add(Item(url=f"https://example.test/{n}", seen_at=NOW - n)) for n in range(5)]
    src = life.Sources(tmp_path)
    first = life.days(src, limit=2)
    assert [e["id"] for e in first["items"]] == [made[0].id, made[1].id] and first["more"]
    rest = life.days(src, before=made[1].id, limit=10)
    assert [e["id"] for e in rest["items"]] == [m.id for m in made[2:]] and not rest["more"]
    assert life.days(src, before="nothing-like-this") == {"items": [], "more": False}
    assert life.mark(library, made[3].id, "keep").state == KEPT
    shelf = life.days(src, kept_only=True)["items"]
    assert [e["id"] for e in shelf] == [made[3].id] and shelf[0]["kept"]
    assert life.mark(library, made[3].id, "keep", kept=False).state == ""
    assert life.mark(library, "0" * 16, "keep") is None


# ---------------------------------------------------------------- cards ----

def test_a_card_keeps_only_listed_players_and_library_pictures():
    base = {"kind": "video", "title": "T", "url": "https://example.test/v", "length": 61,
            "embed": "https://www.youtube-nocookie.com/embed/abc", "picture": "/api/library/picture/" + "a" * 16}
    assert life.clean_card(base)["embed"] == base["embed"]
    assert life.clean_card(base)["picture"] == base["picture"]
    assert life.clean_card({**base, "embed": "https://evil.test/embed"})["embed"] == ""
    assert life.clean_card({**base, "embed": "http://www.youtube.com/embed/abc"})["embed"] == ""
    assert life.clean_card({**base, "picture": "https://evil.test/x.jpg"})["picture"] == ""
    assert life.clean_card({**base, "kind": "hologram", "length": True}) | {} == {
        **life.clean_card(base), "kind": "page", "length": None}
    assert life.clean_card({**base, "url": "javascript:alert(1)"}) is None
    assert life.clean_card("not a card") is None
