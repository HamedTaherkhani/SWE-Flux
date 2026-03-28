from __future__ import annotations

from telegram import CallbackQuery, Update, User
from telegram.ext import CallbackQueryHandler


async def _noop(update, context):
    return None


def _build_update(update_id: int, data=..., game_short_name=None) -> Update:
    user = User(id=987654, first_name="Branch", is_bot=False, username="branch_user")
    kwargs = {}
    if data is not ...:
        kwargs["data"] = data
    if game_short_name is not None:
        kwargs["game_short_name"] = game_short_name

    callback_query = CallbackQuery(
        id=f"cq-{update_id}",
        from_user=user,
        chat_instance=f"ci-{update_id}",
        **kwargs,
    )
    return Update(update_id=update_id, callback_query=callback_query)


class TestCallbackQueryHandlerCheckUpdateBranchOutcomesQA:
    def test_callbackqueryhandler_check_update_branch_outcomes_case(self):
        regex_handler = CallbackQueryHandler(
            _noop,
            pattern=r"^id:[0-9]{2}$",
            game_pattern=r"^game_[a-z]+$",
        )

        assert regex_handler.check_update(object()) is None

        assert regex_handler.check_update(_build_update(1, data="id:42")) is not None
        assert regex_handler.check_update(_build_update(2, data="bad")) is False
        assert regex_handler.check_update(_build_update(3, data=777)) is False
        assert (
            regex_handler.check_update(_build_update(4, data=None, game_short_name="game_alpha"))
            is not None
        )
        assert regex_handler.check_update(_build_update(5, data=None, game_short_name="zzz")) is False
        assert regex_handler.check_update(_build_update(6, data=None, game_short_name=None)) is True

        game_only_handler = CallbackQueryHandler(_noop, game_pattern=r"^g$")
        assert game_only_handler.check_update(_build_update(7, data="payload")) is False

        no_pattern_handler = CallbackQueryHandler(_noop)
        assert no_pattern_handler.check_update(_build_update(8, data="anything")) is True

        type_handler = CallbackQueryHandler(_noop, pattern=dict)
        assert type_handler.check_update(_build_update(9, data={"x": 1})) is True
        assert type_handler.check_update(_build_update(10, data=["x"])) is False

        callable_handler = CallbackQueryHandler(
            _noop,
            pattern=lambda value: isinstance(value, str) and value.endswith(":ok"),
        )
        assert callable_handler.check_update(_build_update(11, data="z:ok")) is True
        assert callable_handler.check_update(_build_update(12, data="z:no")) is False

        pattern_only_handler = CallbackQueryHandler(_noop, pattern=r"^x$")
        assert pattern_only_handler.check_update(
            _build_update(13, data=None, game_short_name="game_beta")
        ) is False
