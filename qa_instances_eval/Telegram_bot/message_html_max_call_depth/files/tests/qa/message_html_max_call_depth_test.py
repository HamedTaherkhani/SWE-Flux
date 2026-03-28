from datetime import datetime, timezone

from telegram import Chat, Message, MessageEntity, User


class TestMessageHtmlMaxCallDepthQA:
    def test_message_html_max_call_depth_case(self):
        text = "abcdefghijklmnopqrstuvwxzy0123456789ABCDEFGHIJKLMN"

        entity_types = [
            MessageEntity.BOLD,
            MessageEntity.ITALIC,
            MessageEntity.UNDERLINE,
            MessageEntity.STRIKETHROUGH,
            MessageEntity.SPOILER,
            MessageEntity.CODE,
        ]

        nested_entities = []
        text_len = len(text)
        for i in range(12):
            nested_entities.append(
                MessageEntity(
                    type=entity_types[i % len(entity_types)],
                    offset=i,
                    length=text_len - (2 * i),
                )
            )

        user = User(id=70001, first_name="Depth", is_bot=False)
        chat = Chat(id=70002, type=Chat.PRIVATE)
        message = Message(
            message_id=70003,
            date=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
            chat=chat,
            from_user=user,
            text=text,
            entities=tuple(nested_entities),
        )

        rendered = message.text_html

        assert isinstance(rendered, str)
        assert "<b>" in rendered
        assert "</b>" in rendered
