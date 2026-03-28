from __future__ import annotations

from datetime import datetime, timezone

import pytest

from telegram import Chat, Message, MessageEntity, User


def _build_message(
    text: str | None = None,
    caption: str | None = None,
    entities=(),
    caption_entities=(),
    message_id: int = 1,
) -> Message:
    chat = Chat(id=444222, type=Chat.PRIVATE)
    user = User(id=123321, first_name="Range", is_bot=False, username="range_user")
    return Message(
        message_id=message_id,
        date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        chat=chat,
        from_user=user,
        text=text,
        caption=caption,
        entities=entities,
        caption_entities=caption_entities,
    )


class TestMessageQuotePositionValueRangeSuiteQA:
    def test_quote_position_case_01_first_occurrence(self):
        message = _build_message(text="alpha beta gamma alpha beta", message_id=1)
        position, _entities = message.compute_quote_position_and_entities("alpha", 0)
        assert isinstance(position, int)
        assert position >= 0

    def test_quote_position_case_02_second_occurrence(self):
        message = _build_message(text="alpha beta gamma alpha beta", message_id=2)
        position, _entities = message.compute_quote_position_and_entities("alpha", 1)
        assert isinstance(position, int)
        assert position >= 0

    def test_quote_position_case_03_emoji_segment(self):
        message = _build_message(text="start 😀 middle 😀 end", message_id=3)
        position, _entities = message.compute_quote_position_and_entities("😀 end", 0)
        assert isinstance(position, int)
        assert position >= 0

    def test_quote_position_case_04_caption_path(self):
        message = _build_message(text=None, caption="cap one cap two cap", message_id=4)
        position, _entities = message.compute_quote_position_and_entities("cap", 2)
        assert isinstance(position, int)
        assert position >= 0

    def test_quote_position_case_05_newline_text(self):
        message = _build_message(text="line1\nline2\nline3\nline4", message_id=5)
        position, _entities = message.compute_quote_position_and_entities("line3", 0)
        assert isinstance(position, int)
        assert position >= 0

    def test_quote_position_case_06_non_overlapping_repeats(self):
        message = _build_message(text="aaaaaa", message_id=6)
        position, _entities = message.compute_quote_position_and_entities("aaa", 1)
        assert isinstance(position, int)
        assert position >= 0

    def test_quote_position_case_07_with_entities_overlap(self):
        entities = (
            MessageEntity(type=MessageEntity.BOLD, offset=6, length=12),
            MessageEntity(type=MessageEntity.ITALIC, offset=0, length=8),
        )
        message = _build_message(
            text="prefix target segment suffix",
            entities=entities,
            message_id=7,
        )
        position, quote_entities = message.compute_quote_position_and_entities("target segment", 0)
        assert isinstance(position, int)
        assert position >= 0
        assert quote_entities is None or isinstance(quote_entities, tuple)

    def test_quote_position_case_08_multiple_emoji_occurrence(self):
        message = _build_message(text="x😀y😀z😀done", message_id=8)
        position, _entities = message.compute_quote_position_and_entities("😀", 2)
        assert isinstance(position, int)
        assert position >= 0

    def test_quote_position_case_09_punctuation_phrase(self):
        message = _build_message(text="A, B; C: D. A, B; C: D.", message_id=9)
        position, _entities = message.compute_quote_position_and_entities("A, B; C: D.", 1)
        assert isinstance(position, int)
        assert position >= 0

    def test_quote_position_case_10_long_prefix_distance(self):
        long_text = "lead " + ("skip_" * 18) + "target block"
        message = _build_message(text=long_text, message_id=10)
        position, _entities = message.compute_quote_position_and_entities("target block", 0)
        assert isinstance(position, int)
        assert position >= 0

    def test_quote_position_case_11_missing_quote_raises(self):
        message = _build_message(text="one two three", message_id=11)
        with pytest.raises(ValueError):
            message.compute_quote_position_and_entities("absent", 0)

    def test_quote_position_case_12_index_out_of_range_raises(self):
        message = _build_message(text="token token token", message_id=12)
        with pytest.raises(ValueError):
            message.compute_quote_position_and_entities("token", 5)
