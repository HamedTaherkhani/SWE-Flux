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


async def _callback(update, context):
    return None


class TestConversationHandlerStateCandidatesLoopIterationsQA:
    def test_conversationhandler_state_candidates_loop_iterations_case(self):
        chat = Chat(id=73001, type=Chat.GROUP, title="loop room")
        user = User(id=73002, first_name="Ava", is_bot=False, username="ava_u")
        message = Message(
            message_id=73003,
            date=datetime(2025, 9, 9, 9, 9, tzinfo=timezone.utc),
            chat=chat,
            from_user=user,
            text="alpha beta gamma theta",
            entities=(MessageEntity(type=MessageEntity.BOLD, offset=6, length=4),),
        )
        update = Update(update_id=73004, message=message)

        state_handlers = [
            ChatMemberHandler(_callback, chat_member_types=ChatMemberHandler.ANY_CHAT_MEMBER),
            BusinessConnectionHandler(_callback, username="biz_user"),
            CommandHandler(["start", "help"], _callback, filters=filters.ChatType.GROUPS),
            PrefixHandler(prefix=("/", "!"), command=("go", "run"), callback=_callback),
            MessageHandler(filters.CaptionRegex(r"(urgent|todo)"), _callback),
            MessageHandler(
                filters.TEXT & filters.Regex(r"\btheta\b") & filters.Entity(MessageEntity.URL),
                _callback,
            ),
            MessageHandler((filters.TEXT & filters.Regex(r"\balpha\b")) & filters.FORWARDED, _callback),
            MessageHandler(
                filters.TEXT
                & (~filters.COMMAND)
                & (filters.Regex(r"\bbeta\b") | filters.Regex(r"\bgamma\b")),
                _callback,
            ),
            MessageHandler(filters.ALL, _callback),
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
