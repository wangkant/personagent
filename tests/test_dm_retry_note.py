"""The note for an empty draft is spelled once, for group and private chats."""
from __future__ import annotations

from persona_agent import decision, dm


def test_private_chats_use_the_group_turns_empty_draft_note() -> None:
    assert dm._EMPTY_DRAFT_RETRY_NOTE is decision.EMPTY_DRAFT_RETRY_NOTE
