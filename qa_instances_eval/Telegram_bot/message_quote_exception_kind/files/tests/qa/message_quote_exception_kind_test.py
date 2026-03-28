from datetime import datetime, timezone

import pytest

from telegram import Chat, Message, User


class TestMessageQuoteExceptionKindQA:
    def test_message_quote_exception_kind_case(self):
        text_value = "alpha beta🙂gamma alpha beta🙂gamma epsilon"
        quote_candidates = ["beta🙂gamma", "alpha beta", "epsilon"]

        selected_quote = quote_candidates[(len(text_value) // 7) % len(quote_candidates)]
        quote_count = text_value.count(selected_quote)
        quote_index = quote_count + (len(selected_quote) % 3) + 1

        message = Message(
            message_id=9901,
            date=datetime(2025, 4, 5, 8, 30, tzinfo=timezone.utc),
            chat=Chat(id=-100441122, type=Chat.SUPERGROUP, title="qa_room"),
            from_user=User(id=7012, is_bot=False, first_name="Casey"),
            text=text_value,
        )

        with pytest.raises(Exception):
            message.build_reply_arguments(
                quote=selected_quote,
                quote_index=quote_index,
                target_chat_id=message.chat_id,
                allow_sending_without_reply=True,
            )
