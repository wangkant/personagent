"""What the character has seen, kept for the home page and the days."""
from __future__ import annotations

from persona_agent.library import DISMISSED, KEPT, Item, Library, item_id

NOW = 1_800_000_000


def test_an_item_is_kept_once_and_the_owner_s_choice_outlives_a_second_visit(tmp_path):
    library = Library(tmp_path)
    first = library.add(Item(url="https://example.test/v/1", site="Example", kind="video", title="One",
                             fits=True, seen_at=NOW))
    assert first.id == item_id("https://example.test/v/1") and library.seen(first.url)
    library.change(first.id, state=KEPT, told=True)
    library.add(Item(url=first.url, site="Example", kind="video", title="One, renamed", seen_at=NOW + 5))
    again = Library(tmp_path).get(first.id)
    assert (again.title, again.state, again.told) == ("One, renamed", KEPT, True)
    assert len(library.items()) == 1


def test_what_to_tell_is_what_fits_and_was_not_said_or_dismissed(tmp_path):
    library = Library(tmp_path)
    a = library.add(Item(url="https://example.test/a", fits=True, seen_at=NOW))
    b = library.add(Item(url="https://example.test/b", fits=True, seen_at=NOW + 1))
    library.add(Item(url="https://example.test/c", fits=False, seen_at=NOW + 2))
    d = library.add(Item(url="https://example.test/d", fits=True, seen_at=NOW + 3))
    assert [item.id for item in library.to_tell()] == [a.id, b.id, d.id]
    library.change(a.id, told=True)
    library.change(d.id, state=DISMISSED)
    assert [item.id for item in library.to_tell()] == [b.id]
    assert [item.url[-1] for item in library.items()] == ["d", "c", "b", "a"], "newest first"


def test_a_card_holds_public_facts_and_no_path(tmp_path):
    library = Library(tmp_path)
    item = library.add(Item(url="https://example.test/v/1", site="Example", kind="video", title="One",
                            author="Kim", length=95, description="  a   short\n description ",
                            embed="https://player.example.test/1", seen_at=NOW))
    assert library.save_picture(item.id, b"x" * 10) == f"{item.id}.jpg"
    library.change(item.id)
    item.picture = f"{item.id}.jpg"
    library.add(item)
    card = library.get(item.id).card()
    assert card == {"kind": "video", "title": "One", "site": "Example", "author": "Kim", "length": 95,
                    "picture": f"/api/library/picture/{item.id}", "embed": "https://player.example.test/1",
                    "url": "https://example.test/v/1", "excerpt": "a short description", "readable": False}
    assert library.picture_path(item.id).read_bytes() == b"x" * 10
    assert library.picture_path("missing") is None
    assert library.save_picture(item.id, b"x" * 300_000) == "", "a cover is kept small"


def test_an_unknown_kind_is_a_page_and_damaged_lines_are_passed_over(tmp_path):
    library = Library(tmp_path)
    library.add(Item(url="https://example.test/x", kind="hologram", seen_at=NOW))
    with open(library.items_path, "a", encoding="utf-8") as handle:
        handle.write("{not json\n")
    assert [item.kind for item in Library(tmp_path).items()] == ["page"]


def test_the_walk_is_out_then_home_and_counts_a_day(tmp_path):
    library = Library(tmp_path)
    assert library.outing().state == "home"
    library.left("Example", now=NOW)
    library.at("Other")
    out = Library(tmp_path).outing()
    assert (out.state, out.site, out.since, out.today) == ("out", "Other", NOW, 1)
    back = library.returned(2, sites=["Example"], now=NOW + 60)
    assert (back.state, back.last_count, back.last_end) == ("home", 2, NOW + 60)
    assert back.sites == ["Other", "Example"]
    assert library.left(now=NOW + 120).today == 2
    assert library.left(now=NOW + 86400 * 2).today == 1, "a new day starts the count again"


def test_compacting_keeps_one_line_per_item(tmp_path):
    library = Library(tmp_path)
    item = library.add(Item(url="https://example.test/a", seen_at=NOW))
    for _ in range(5):
        library.change(item.id, state=KEPT)
    assert len(library.items_path.read_text(encoding="utf-8").splitlines()) == 6
    library.compact()
    assert len(library.items_path.read_text(encoding="utf-8").splitlines()) == 1
    assert library.get(item.id).state == KEPT
