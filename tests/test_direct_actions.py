"""The switches, limits, counts and record every account action shares."""
from __future__ import annotations

import json

from persona_agent.direct import actions as act

LIKE = act.Action("like_this", act.RESPOND, "Like the message you are answering.", per_day=30, undo="unlike_this")
INFO = act.Action("video_info", act.LOOK, "Read a linked video's title and uploader.", per_day=40,
                  params={"which": {"type": "integer", "minimum": 1, "maximum": 3}})
FOLLOW = act.Action("follow", act.REACH, "Follow the person.", per_day=3)
NOW = 1_800_000_000.0


def test_reach_is_off_until_the_owner_turns_it_on(tmp_path):
    settings = act.Settings(tmp_path)
    assert settings.of("site", LIKE) == (True, 30)
    assert settings.of("site", FOLLOW) == (False, 3)
    assert settings.set("site", FOLLOW, on=True) == (True, 3)
    assert act.Settings(tmp_path).of("site", FOLLOW) == (True, 3), "kept on disk"
    assert act.Settings(tmp_path).of("other", FOLLOW) == (False, 3), "one account's switch is its own"


def test_no_setting_goes_past_the_ceiling(tmp_path):
    settings = act.Settings(tmp_path)
    assert settings.set("site", LIKE, per_day=5000) == (True, act.CEILING[act.RESPOND])
    act.settings_path(tmp_path).write_text(json.dumps(
        {"site": {"actions": {"follow": {"on": True, "per_day": 999}}}}), encoding="utf-8")
    assert settings.of("site", FOLLOW) == (True, act.CEILING[act.REACH]), "a hand-edited file is held to it too"
    assert settings.set("site", LIKE, per_day=-4) == (True, 0)


def test_a_change_on_disk_holds_at_once_and_a_damaged_file_means_the_defaults(tmp_path):
    settings = act.Settings(tmp_path)
    assert settings.of("site", LIKE)[0]
    act.Settings(tmp_path).set("site", LIKE, on=False)
    assert not settings.of("site", LIKE)[0]
    act.settings_path(tmp_path).write_text("{not json", encoding="utf-8")
    assert settings.of("site", LIKE) == (True, 30) and settings.of("site", FOLLOW) == (False, 3)


def test_the_reasons_an_action_is_refused(tmp_path):
    settings = act.Settings(tmp_path)
    counts = act.Counts(tmp_path / "counts.json")

    def why(action, **more):
        return act.refusal("site", action, settings, counts, now=NOW, **more)

    assert why(LIKE, person="kim", item="c1") == ""
    assert why(FOLLOW) == act.OFF

    counts.add(LIKE, person="kim", item="c1", now=NOW)
    assert why(LIKE, person="kim", item="c1") == act.ALREADY, "one like for one thing"
    for n in range(2, act.PER_PERSON + 1):
        counts.add(LIKE, person="kim", item=f"c{n}", now=NOW)
    assert why(LIKE, person="kim", item="c9") == act.PER_PERSON_LIMIT
    assert why(LIKE, person="lee", item="c9") == ""

    settings.set("site", LIKE, per_day=act.PER_PERSON)
    assert why(LIKE, person="lee", item="c9") == act.DAILY_LIMIT
    assert act.refusal("site", LIKE, settings, counts, person="lee", item="c9", now=NOW + 86400) == "", \
        "a new day starts the count again"

    settings.pause("site", True)
    assert why(INFO) == act.PAUSED
    settings.pause("site", False)

    settings.set("site", FOLLOW, on=True)
    assert why(FOLLOW) == ""
    counts.add(FOLLOW, now=NOW)
    assert why(FOLLOW) == act.TOO_SOON
    assert act.refusal("site", FOLLOW, settings, counts, now=NOW + act.REACH_SPACING_S + 1) == ""


def test_counts_outlive_a_restart_and_a_taken_back_like_can_be_given_again(tmp_path):
    counts = act.Counts(tmp_path / "counts.json")
    counts.add(LIKE, person="kim", item="c1", now=NOW)
    again = act.Counts(tmp_path / "counts.json")
    assert again.done("like_this", NOW) == 1 and "c1" in again.items and again.people == {"kim": 1}
    again.take_back("c1")
    assert "c1" not in act.Counts(tmp_path / "counts.json").items


def test_the_record_is_newest_first_and_holds_no_more_than_it_shows(tmp_path):
    for n in range(3):
        act.record(tmp_path, kind="site", account="Robin", action="like_this",
                   done=act.Done(True, what=f"comment {n} by Kim: " + "x" * 200, link="https://example.test/c"),
                   why="answering Kim", now=NOW + n)
    act.record(tmp_path, kind="site", account="Robin", action="follow", done=act.Done(False, code=act.OFF),
               now=NOW + 9)
    rows = act.recent(tmp_path)
    assert [row["action"] for row in rows] == ["follow", "like_this", "like_this", "like_this"]
    assert rows[0]["ok"] is False and rows[0]["code"] == act.OFF
    assert len(rows[1]["what"]) == 80 and rows[1]["why"] == "answering Kim"
    assert act.recent(tmp_path, limit=2) == rows[:2]
    assert act.recent(tmp_path / "nowhere") == []


def test_an_action_is_offered_in_its_own_words_with_no_room_for_an_id():
    offered = act.function_for("site", INFO)
    assert offered["name"] == "site_video_info" and offered["description"] == INFO.says
    assert offered["parameters"] == {"type": "object", "additionalProperties": False,
                                     "properties": {"which": {"type": "integer", "minimum": 1, "maximum": 3}}}
