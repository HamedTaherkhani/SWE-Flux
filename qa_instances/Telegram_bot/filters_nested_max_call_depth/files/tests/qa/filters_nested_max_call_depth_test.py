from datetime import datetime, timezone

from telegram import Chat, Message, MessageEntity, Update, User
from telegram.ext import filters


class TestFiltersNestedMaxCallDepthQA:
    def test_filters_nested_max_call_depth_case(self):
        user = User(id=99001, first_name="Depth", is_bot=False, username="depth_user")
        chat = Chat(id=99002, type=Chat.GROUP)

        text = "run /start and visit https://example.org now"
        entities = (
            MessageEntity(type=MessageEntity.BOT_COMMAND, offset=4, length=6),
            MessageEntity(type=MessageEntity.URL, offset=21, length=19),
        )

        message = Message(
            message_id=99003,
            date=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            chat=chat,
            from_user=user,
            text=text,
            entities=entities,
            caption="caption text for depth",
        )
        update = Update(update_id=99004, message=message)

        f1 = filters.Regex(r"run\s+/start") & filters.Entity(MessageEntity.BOT_COMMAND)
        f2 = filters.Entity(MessageEntity.URL) & filters.ChatType.GROUP
        f3 = filters.CaptionRegex(r"caption\s+text") | filters.User(username="depth_user")
        f4 = ~filters.FORWARDED

        combined = ((f1 | f2) & (f3 | f4)) ^ (filters.COMMAND & ~filters.ChatType.CHANNEL)

        result = combined.check_update(update)

        assert bool(result) is True
