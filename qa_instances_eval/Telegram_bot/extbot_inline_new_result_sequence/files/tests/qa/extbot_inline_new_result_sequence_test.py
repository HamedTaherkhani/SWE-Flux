from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.ext import ExtBot


class TestExtBotInlineNewResultSequenceQA:
    def test_extbot_inline_new_result_sequence_case(self):
        bot = ExtBot(token="123456:INLINE_SEQUENCE_TOKEN", arbitrary_callback_data=True)

        keyboard_a = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="A1", callback_data={"k": "a1"})]]
        )
        keyboard_b = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(text="B1", callback_data={"k": "b1"})],
                [InlineKeyboardButton(text="B2", callback_data={"k": "b2"})],
            ]
        )
        keyboard_c = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="C1", callback_data={"k": "c1"})]]
        )

        results = [
            InlineQueryResultArticle(
                id="art_1",
                title="Title 1",
                input_message_content=InputTextMessageContent(message_text="payload 1"),
                reply_markup=keyboard_a,
                description="desc 1",
            ),
            InlineQueryResultArticle(
                id="art_2",
                title="Title 2",
                input_message_content=InputTextMessageContent(message_text="payload 2"),
                reply_markup=keyboard_b,
                description="desc 2",
            ),
            InlineQueryResultArticle(
                id="art_3",
                title="Title 3",
                input_message_content=InputTextMessageContent(message_text="payload 3"),
                reply_markup=keyboard_c,
                description="desc 3",
            ),
            InlineQueryResultArticle(
                id="art_4",
                title="Title 4",
                input_message_content=InputTextMessageContent(message_text="payload 4"),
                reply_markup=keyboard_a,
                description="desc 4",
            ),
        ]

        effective_results, next_offset = bot._effective_inline_results(
            results=results,
            next_offset="next_77",
        )

        assert len(effective_results) == 4
        assert next_offset == "next_77"
        assert all(hasattr(r, "reply_markup") for r in effective_results)
