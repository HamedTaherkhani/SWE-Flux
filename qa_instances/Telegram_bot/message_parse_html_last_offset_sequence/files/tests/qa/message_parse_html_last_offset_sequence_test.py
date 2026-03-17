from datetime import datetime, timezone

from telegram import Chat, Message, MessageEntity, User


class TestMessageParseHtmlLastOffsetSequenceQA:
    def test_message_parse_html_last_offset_sequence_case(self):
        words = [
            "alfa",
            "brav",
            "char",
            "delt",
            "echo",
            "foxt",
            "golf",
            "hote",
            "indi",
            "juli",
            "kilo",
            "lima",
            "mike",
        ]
        text = " ".join(words)

        def start(i: int) -> int:
            return i * 5

        entities = (
            MessageEntity(type=MessageEntity.BOLD, offset=start(0), length=9),
            MessageEntity(type=MessageEntity.ITALIC, offset=start(2), length=4),
            MessageEntity(type=MessageEntity.URL, offset=start(3), length=9),
            MessageEntity(type=MessageEntity.UNDERLINE, offset=start(5), length=4),
            MessageEntity(type=MessageEntity.STRIKETHROUGH, offset=start(6), length=9),
            MessageEntity(type=MessageEntity.SPOILER, offset=start(8), length=4),
            MessageEntity(type=MessageEntity.PRE, offset=start(9), length=14, language="py"),
            MessageEntity(type=MessageEntity.CODE, offset=start(10), length=4),
            MessageEntity(type=MessageEntity.BLOCKQUOTE, offset=start(12), length=4),
        )

        message = Message(
            message_id=81001,
            date=datetime(2025, 2, 2, 12, 0, tzinfo=timezone.utc),
            chat=Chat(id=81002, type=Chat.PRIVATE),
            from_user=User(id=81003, first_name="Depth", is_bot=False),
            text=text,
            entities=entities,
        )

        rendered = message.text_html_urled

        assert isinstance(rendered, str)
        assert "<pre><code class=\"py\">" in rendered
        assert "<blockquote>" in rendered
