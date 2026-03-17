from datetime import datetime, timezone

from telegram import Chat, Message, MessageEntity, User


class TestCallbackQueryPostCallStateQA:
    def test_parse_html_postcall_state_case(self):
        text_value = "alpha beta gamma https://x.y/z omega"

        entities = [
            MessageEntity(offset=0, length=16, type=MessageEntity.BOLD),
            MessageEntity(offset=6, length=4, type=MessageEntity.ITALIC),
            MessageEntity(offset=11, length=5, type=MessageEntity.CODE),
            MessageEntity(offset=17, length=13, type=MessageEntity.URL),
        ]

        chat = Chat(id=-100245001, type=Chat.SUPERGROUP, title="html_flow_room")
        author = User(id=73001, is_bot=False, first_name="Author")
        message = Message(
            message_id=404,
            date=datetime(2025, 1, 10, 12, 30, tzinfo=timezone.utc),
            chat=chat,
            from_user=author,
            text=text_value,
            entities=entities,
        )

        html_urled = message.text_html_urled

        assert isinstance(html_urled, str)
        assert "<a href=" in html_urled
        assert "<b>" in html_urled
        assert "<code>" in html_urled
