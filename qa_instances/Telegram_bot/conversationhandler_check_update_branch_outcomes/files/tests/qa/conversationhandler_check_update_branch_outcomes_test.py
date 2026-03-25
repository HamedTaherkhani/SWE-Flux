from __future__ import annotations

from datetime import datetime, timezone

from telegram import Chat, Message, Update, User
from telegram.ext import ConversationHandler, MessageHandler, filters


async def _noop(update, context):
    return None


def _build_update(update_id: int, text: str, with_user: bool = True) -> Update:
    chat = Chat(id=-100222333, type="supergroup", title="qa-chat")
    user = (
        User(id=777001, first_name="qa", is_bot=False, username="qa_user")
        if with_user
        else None
    )
    message = Message(
        message_id=update_id,
        date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        chat=chat,
        from_user=user,
        text=text,
    )
    return Update(update_id=update_id, message=message)


class TestConversationHandlerCheckUpdateBranchOutcomesQA:
    def test_conversationhandler_check_update_branch_outcomes_case(self):
        entry_handlers = [
            MessageHandler(filters.TEXT & filters.Regex(r"^never$"), _noop),
            MessageHandler(filters.TEXT & filters.Regex(r"^start\s+\d+$"), _noop),
        ]
        state_handlers = [
            MessageHandler(filters.TEXT & filters.Regex(r"^state\s+X$"), _noop),
            MessageHandler(filters.TEXT & filters.Regex(r"^state\s+[a-z]+$"), _noop),
        ]
        fallback_handlers = [
            MessageHandler(filters.TEXT & filters.Regex(r"^cancel$"), _noop),
            MessageHandler(filters.TEXT & filters.Regex(r"^fallback\s+trigger$"), _noop),
        ]

        conv = ConversationHandler(
            entry_points=entry_handlers,
            states={1: state_handlers},
            fallbacks=fallback_handlers,
            allow_reentry=False,
            per_chat=True,
            per_user=True,
            per_message=False,
        )

        assert conv.check_update(object()) is None

        missing_user_update = _build_update(update_id=101, text="start 11", with_user=False)
        assert conv.check_update(missing_user_update) is None

        no_entry_match_update = _build_update(update_id=102, text="no match here", with_user=True)
        assert conv.check_update(no_entry_match_update) is None

        entry_match_update = _build_update(update_id=103, text="start 42", with_user=True)
        assert conv.check_update(entry_match_update) is not None

        state_match_update = _build_update(update_id=104, text="state alpha", with_user=True)
        conv._conversations[conv._get_key(state_match_update)] = 1
        assert conv.check_update(state_match_update) is not None

        fallback_match_update = _build_update(update_id=105, text="fallback trigger", with_user=True)
        conv._conversations[conv._get_key(fallback_match_update)] = 1
        assert conv.check_update(fallback_match_update) is not None
