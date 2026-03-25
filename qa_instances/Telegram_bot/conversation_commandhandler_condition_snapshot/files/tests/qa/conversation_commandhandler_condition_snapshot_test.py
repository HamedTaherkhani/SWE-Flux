from datetime import datetime, timezone

from telegram import Chat, Message, MessageEntity, Update, User
from telegram.ext import (
    BusinessConnectionHandler,
    ChatMemberHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    PrefixHandler,
    filters,
)


class _DummyBot:
    def __init__(self, username: str):
        self.username = username


async def _callback(update, context):
    return None


class TestConversationCommandHandlerConditionSnapshotQA:
    def test_conversation_commandhandler_condition_snapshot_case(self):
        command_token = "/Start@WrongBot"

        chat = Chat(id=84001, type=Chat.GROUP, title="condition room")
        user = User(id=84002, first_name="Lena", is_bot=False, username="lena_u")
        message = Message(
            message_id=84003,
            date=datetime(2025, 10, 5, 12, 0, tzinfo=timezone.utc),
            chat=chat,
            from_user=user,
            text=f"{command_token} alpha beta gamma",
            entities=(
                MessageEntity(
                    type=MessageEntity.BOT_COMMAND,
                    offset=0,
                    length=len(command_token),
                ),
            ),
        )
        message.set_bot(_DummyBot("qa_bot"))

        update = Update(update_id=84004, message=message)

        state_handlers = [
            CommandHandler(["start", "help"], _callback),
            PrefixHandler(prefix=("!", "/"), command=("go", "run"), callback=_callback),
            ChatMemberHandler(_callback, chat_member_types=ChatMemberHandler.ANY_CHAT_MEMBER),
            BusinessConnectionHandler(_callback, username="biz_user"),
            MessageHandler(filters.TEXT & filters.Regex(r"\bbeta\b"), _callback),
        ]

        conversation = ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & filters.Regex(r"^init$"), _callback)],
            states={"ACTIVE": state_handlers},
            fallbacks=[MessageHandler(filters.ALL, _callback)],
            per_chat=True,
            per_user=True,
            per_message=False,
        )

        key = conversation._get_key(update)
        conversation._conversations[key] = "ACTIVE"

        result = conversation.check_update(update)

        assert result is not None
        current_state, result_key, selected_handler, check = result
        assert current_state == "ACTIVE"
        assert result_key == key
        assert selected_handler is not None
        assert check is not None and check is not False
