from datetime import datetime, timezone

from telegram import Chat, Message, MessageEntity, Update, User
from telegram.ext import filters


class TestFiltersMergedOrReachabilityQA:
    def test_filters_merged_or_reachability_case(self):
        user = User(id=424242, first_name="Case", is_bot=False, username="case_user")
        chat = Chat(id=787878, type=Chat.PRIVATE)

        text = "start https://ptb.example/path finish"
        entities = (
            MessageEntity(type=MessageEntity.URL, offset=6, length=24),
            MessageEntity(type=MessageEntity.BOLD, offset=0, length=5),
        )

        message = Message(
            message_id=31337,
            date=datetime(2024, 5, 17, 12, 0, tzinfo=timezone.utc),
            chat=chat,
            from_user=user,
            text=text,
            entities=entities,
            caption="caption layer",
        )
        update = Update(update_id=515151, message=message)

        left_branch = (
            filters.Regex(r"(?P<prefix>start)\s+(?P<link>https://\S+)")
            & filters.Entity(MessageEntity.URL)
        )

        right_branch = (
            (filters.CaptionRegex(r"(?P<cap>caption)\s+(?P<tail>layer)")
            & filters.CaptionEntity(MessageEntity.BOLD))
            | (filters.User(user_id=999999) & filters.ChatType.GROUP)
        )

        merged_filter = left_branch | right_branch

        result = merged_filter.check_update(update)

        assert isinstance(result, dict)
        assert "matches" in result
        assert result["matches"]
