from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    User,
)
from telegram.ext import ExtBot


class _NoNetworkExtBot(ExtBot):
    async def _post(self, endpoint, data, **kwargs):  # type: ignore[override]
        return True


class TestInlineQueryAnswerConditionSnapshotQA:
    async def test_inlinequery_answer_condition_snapshot_case(self):
        bot = _NoNetworkExtBot(token="123:TEST")

        user = User(id=91002, first_name="Mina", is_bot=False, username="mina_qax")
        inline_query = InlineQuery(
            id="iq_91001",
            from_user=user,
            query="mix alpha gamma",
            offset="3",
            chat_type="supergroup",
        )
        inline_query.set_bot(bot)

        seed_titles = ("Vector", "Matrix", "Tensor", "Scalar")
        derived_current_offset = str((sum(ord(title[0]) for title in seed_titles) + len(user.username)) % 5 + 1)
        derived_auto_pagination = (
            len({len(title) for title in seed_titles}) % 2 == 0
            and inline_query.query.startswith("mix")
        )

        def _results_provider(page_idx: int):
            buttons = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(text=f"B{page_idx}A", callback_data=f"cb_{page_idx}_a")],
                    [InlineKeyboardButton(text=f"B{page_idx}B", callback_data=f"cb_{page_idx}_b")],
                ]
            )
            results = [
                InlineQueryResultArticle(
                    id=f"r{page_idx}_1",
                    title=f"{seed_titles[0]}-{page_idx}",
                    input_message_content=InputTextMessageContent(
                        message_text=f"payload {page_idx} one"
                    ),
                    reply_markup=buttons,
                    description="desc one",
                ),
                InlineQueryResultArticle(
                    id=f"r{page_idx}_2",
                    title=f"{seed_titles[1]}-{page_idx}",
                    input_message_content=InputTextMessageContent(
                        message_text=f"payload {page_idx} two"
                    ),
                    reply_markup=buttons,
                    description="desc two",
                ),
                InlineQueryResultArticle(
                    id=f"r{page_idx}_3",
                    title=f"{seed_titles[2]}-{page_idx}",
                    input_message_content=InputTextMessageContent(
                        message_text=f"payload {page_idx} three"
                    ),
                    reply_markup=buttons,
                    description="desc three",
                ),
            ]
            start = page_idx % 2
            return results[start : start + 2]

        ok = await inline_query.answer(
            results=_results_provider,
            cache_time=123,
            is_personal=True,
            current_offset=derived_current_offset,
            auto_pagination=derived_auto_pagination,
            next_offset=None,
        )

        assert ok is True
