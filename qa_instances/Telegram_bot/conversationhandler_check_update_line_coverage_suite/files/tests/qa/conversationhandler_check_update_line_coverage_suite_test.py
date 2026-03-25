from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timezone

import pytest

from telegram import CallbackQuery, Chat, Message, Update, User
from telegram.ext import CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram.ext._handlers.conversationhandler import PendingState


async def _noop(update, context):
    return None


async def _raise_runtime_error() -> int:
    raise RuntimeError("boom")


async def _return_state(value: int) -> int:
    return value


def _build_message(update_id: int, text: str, *, with_user: bool = True) -> Message:
    chat = Chat(id=-1001234500, type="supergroup", title="coverage-room")
    user = User(id=99001, first_name="qa", is_bot=False, username="qa_user") if with_user else None
    return Message(
        message_id=update_id,
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        chat=chat,
        from_user=user,
        text=text,
    )


def _build_message_update(update_id: int, text: str, *, with_user: bool = True) -> Update:
    return Update(update_id=update_id, message=_build_message(update_id, text, with_user=with_user))


def _build_channel_post_update(update_id: int, text: str) -> Update:
    channel_chat = Chat(id=-100424242, type="channel", title="channel")
    channel_message = Message(
        message_id=update_id,
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        chat=channel_chat,
        from_user=None,
        text=text,
    )
    return Update(update_id=update_id, channel_post=channel_message)


def _build_callback_update(
    update_id: int,
    *,
    data: str,
    with_message: bool,
    inline_message_id: str | None = None,
) -> Update:
    user = User(id=99001, first_name="qa", is_bot=False, username="qa_user")
    message = _build_message(update_id, text="callback payload", with_user=True) if with_message else None
    callback_query = CallbackQuery(
        id=f"cq-{update_id}",
        from_user=user,
        chat_instance=f"inst-{update_id}",
        message=message,
        data=data,
        inline_message_id=inline_message_id,
    )
    return Update(update_id=update_id, callback_query=callback_query)


def _build_conversation(
    *,
    per_chat: bool = True,
    per_user: bool = True,
    per_message: bool = False,
    allow_reentry: bool = False,
    include_callback_entry: bool = False,
) -> ConversationHandler:
    if per_message:
        entry_points = [CallbackQueryHandler(_noop, pattern=r"^go$")]
        states = {
            1: [CallbackQueryHandler(_noop, pattern=r"^statecb$")],
            ConversationHandler.WAITING: [CallbackQueryHandler(_noop, pattern=r"^waitcb$")],
        }
        fallbacks = [CallbackQueryHandler(_noop, pattern=r"^fallback$")]
    else:
        entry_points = [MessageHandler(filters.TEXT & filters.Regex(r"^start$"), _noop)]
        if include_callback_entry:
            entry_points.insert(0, CallbackQueryHandler(_noop, pattern=r"^go$"))

        states = {
            1: [MessageHandler(filters.TEXT & filters.Regex(r"^state\s+[a-z]+$"), _noop)],
            ConversationHandler.WAITING: [MessageHandler(filters.TEXT & filters.Regex(r"^wait$"), _noop)],
        }
        fallbacks = [MessageHandler(filters.TEXT & filters.Regex(r"^cancel$"), _noop)]

    return ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=fallbacks,
        allow_reentry=allow_reentry,
        per_chat=per_chat,
        per_user=per_user,
        per_message=per_message,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case_id",
    [
        "non_update_object",
        "channel_post_ignored",
        "per_chat_missing_effective_chat",
        "per_user_missing_effective_user",
        "per_message_without_callback",
        "callback_missing_message_per_chat_true",
        "state_none_no_entry_match",
        "state_none_entry_match",
        "state_handler_match",
        "fallback_handler_match",
        "state_no_match_returns_none",
        "allow_reentry_uses_entry",
        "pending_waiting_handler_match",
        "pending_waiting_handler_no_match",
        "pending_done_exception_old_state_none",
        "pending_done_resolve_to_state",
        "callback_entry_match_per_message_true",
        "callback_state_handler_match",
    ],
)
async def test_conversationhandler_check_update_line_coverage_suite(case_id: str) -> None:
    cleanup_task = None

    try:
        if case_id == "non_update_object":
            conv = _build_conversation()
            assert conv.check_update(object()) is None

        elif case_id == "channel_post_ignored":
            conv = _build_conversation()
            update = _build_channel_post_update(101, "channel post")
            assert conv.check_update(update) is None

        elif case_id == "per_chat_missing_effective_chat":
            conv = _build_conversation(per_chat=True, per_user=True, per_message=False)
            update = _build_callback_update(102, data="go", with_message=False, inline_message_id="im-1")
            assert conv.check_update(update) is None

        elif case_id == "per_user_missing_effective_user":
            conv = _build_conversation(per_chat=True, per_user=True)
            update = _build_message_update(103, "start", with_user=False)
            assert conv.check_update(update) is None

        elif case_id == "per_message_without_callback":
            conv = _build_conversation(per_chat=True, per_user=True, per_message=True)
            update = _build_message_update(104, "start", with_user=True)
            assert conv.check_update(update) is None

        elif case_id == "callback_missing_message_per_chat_true":
            conv = _build_conversation(per_chat=True, per_user=True, per_message=True)
            update = _build_callback_update(105, data="go", with_message=False, inline_message_id="im-2")
            assert conv.check_update(update) is None

        elif case_id == "state_none_no_entry_match":
            conv = _build_conversation()
            update = _build_message_update(106, "unknown", with_user=True)
            assert conv.check_update(update) is None

        elif case_id == "state_none_entry_match":
            conv = _build_conversation()
            update = _build_message_update(107, "start", with_user=True)
            result = conv.check_update(update)
            assert result is not None

        elif case_id == "state_handler_match":
            conv = _build_conversation()
            update = _build_message_update(108, "state alpha", with_user=True)
            conv._conversations[conv._get_key(update)] = 1
            result = conv.check_update(update)
            assert result is not None

        elif case_id == "fallback_handler_match":
            conv = _build_conversation()
            update = _build_message_update(109, "cancel", with_user=True)
            conv._conversations[conv._get_key(update)] = 1
            result = conv.check_update(update)
            assert result is not None

        elif case_id == "state_no_match_returns_none":
            conv = _build_conversation()
            update = _build_message_update(110, "state unmatched value", with_user=True)
            conv._conversations[conv._get_key(update)] = 1
            assert conv.check_update(update) is None

        elif case_id == "allow_reentry_uses_entry":
            conv = _build_conversation(allow_reentry=True)
            update = _build_message_update(111, "start", with_user=True)
            conv._conversations[conv._get_key(update)] = 1
            result = conv.check_update(update)
            assert result is not None

        elif case_id == "pending_waiting_handler_match":
            conv = _build_conversation()
            update = _build_message_update(112, "wait", with_user=True)
            key = conv._get_key(update)
            cleanup_task = asyncio.create_task(asyncio.sleep(60))
            conv._conversations[key] = PendingState(cleanup_task, 1)
            result = conv.check_update(update)
            assert result is not None

        elif case_id == "pending_waiting_handler_no_match":
            conv = _build_conversation()
            update = _build_message_update(113, "not waiting", with_user=True)
            key = conv._get_key(update)
            cleanup_task = asyncio.create_task(asyncio.sleep(60))
            conv._conversations[key] = PendingState(cleanup_task, 1)
            assert conv.check_update(update) is None

        elif case_id == "pending_done_exception_old_state_none":
            conv = _build_conversation()
            update = _build_message_update(114, "start", with_user=True)
            key = conv._get_key(update)
            task = asyncio.create_task(_raise_runtime_error())
            await asyncio.sleep(0)
            conv._conversations[key] = PendingState(task, None)
            result = conv.check_update(update)
            assert result is not None

        elif case_id == "pending_done_resolve_to_state":
            conv = _build_conversation()
            update = _build_message_update(115, "state alpha", with_user=True)
            key = conv._get_key(update)
            task = asyncio.create_task(_return_state(1))
            await asyncio.sleep(0)
            conv._conversations[key] = PendingState(task, 0)
            result = conv.check_update(update)
            assert result is not None

        elif case_id == "callback_entry_match_per_message_true":
            conv = _build_conversation(
                per_chat=True,
                per_user=True,
                per_message=True,
            )
            update = _build_callback_update(116, data="go", with_message=True)
            result = conv.check_update(update)
            assert result is not None

        elif case_id == "callback_state_handler_match":
            conv = _build_conversation(
                per_chat=True,
                per_user=True,
                per_message=True,
            )
            update = _build_callback_update(117, data="statecb", with_message=True)
            conv._conversations[conv._get_key(update)] = 1
            result = conv.check_update(update)
            assert result is not None

        else:
            raise AssertionError(f"unexpected case: {case_id}")

    finally:
        if cleanup_task is not None:
            cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cleanup_task
