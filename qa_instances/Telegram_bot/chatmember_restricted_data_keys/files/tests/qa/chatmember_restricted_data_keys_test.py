from datetime import datetime, timezone

from telegram import CallbackQuery, Chat, Message, MessageEntity, User


class TestChatMemberRestrictedDataKeysQA:
    def test_telegramobject_get_attrs_data_keys_case(self):
        base_text = "prefix alpha beta gamma suffix"
        entities = [
            MessageEntity(offset=7, length=5, type=MessageEntity.BOLD),
            MessageEntity(offset=13, length=4, type=MessageEntity.ITALIC),
        ]

        chat = Chat(id=-100778899, type=Chat.SUPERGROUP, title="attrs_room")
        sender = User(id=88001, is_bot=False, first_name="Sender")
        actor = User(id=88002, is_bot=False, first_name="Actor")
        message = Message(
            message_id=515,
            date=datetime(2024, 12, 20, 8, 45, tzinfo=timezone.utc),
            chat=chat,
            from_user=sender,
            text=base_text,
            entities=entities,
        )

        callback_query = CallbackQuery(
            id="attrs-cq-1",
            from_user=actor,
            chat_instance="attrs-inst-91",
            message=message,
            data="route:attrs",
        )

        attrs_map = callback_query._get_attrs(recursive=True, include_private=False, remove_bot=False)

        assert isinstance(attrs_map, dict)
        assert "from" in attrs_map
        assert "from_user" not in attrs_map
        assert "message" in attrs_map
