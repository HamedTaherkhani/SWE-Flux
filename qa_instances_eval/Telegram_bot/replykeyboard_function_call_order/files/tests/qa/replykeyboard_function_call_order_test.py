from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo


class TestReplyKeyboardFunctionCallOrderQA:
    def test_replykeyboard_function_call_order_case(self):
        web_app = WebAppInfo(url="https://example.org/miniapp")

        rows = [
            ["plain_a", KeyboardButton(text="web_app_button", web_app=web_app)],
            [KeyboardButton(text="contact_button", request_contact=True), "plain_b"],
            ["plain_c", "plain_d"],
        ]

        markup = ReplyKeyboardMarkup(
            keyboard=rows,
            resize_keyboard=True,
            one_time_keyboard=False,
            selective=True,
            input_field_placeholder="pick one",
            is_persistent=True,
        )

        markup_dict = markup.to_dict()

        assert isinstance(markup_dict, dict)
        assert "keyboard" in markup_dict
        assert len(markup_dict["keyboard"]) == 3
