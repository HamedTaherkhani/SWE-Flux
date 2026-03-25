from __future__ import annotations

import pytest

from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup


class TestMarkupInnerStringInvariantSuiteQA:
    def test_case_01_reply_simple_strings(self):
        markup = ReplyKeyboardMarkup([["A", "B"], ["C"]])
        assert markup.keyboard

    def test_case_02_reply_tuple_rows_strings(self):
        markup = ReplyKeyboardMarkup((("A", "B"), ("C",)))
        assert len(markup.keyboard) == 2

    def test_case_03_reply_row_as_string_invalid(self):
        with pytest.raises(ValueError):
            ReplyKeyboardMarkup(["AB"])

    def test_case_04_reply_nested_list_button_invalid(self):
        with pytest.raises(ValueError):
            ReplyKeyboardMarkup([[["X"]]])

    def test_case_05_reply_bytes_button_invalid(self):
        with pytest.raises(ValueError):
            ReplyKeyboardMarkup([[b"X"]])

    def test_case_06_reply_int_buttons_valid(self):
        markup = ReplyKeyboardMarkup([[1, 2], [3]])
        assert len(markup.keyboard) == 2

    def test_case_07_reply_tuple_button_invalid(self):
        with pytest.raises(ValueError):
            ReplyKeyboardMarkup([[("x", "y")]])

    def test_case_08_reply_empty_keyboard_valid(self):
        markup = ReplyKeyboardMarkup([])
        assert markup.keyboard == ()

    def test_case_09_reply_empty_row_valid(self):
        markup = ReplyKeyboardMarkup([[]])
        assert len(markup.keyboard) == 1

    def test_case_10_inline_list_of_strings_valid(self):
        markup = InlineKeyboardMarkup([["x", "y"], ["z"]])
        assert len(markup.inline_keyboard) == 2

    def test_case_11_inline_nested_tuple_button_invalid(self):
        with pytest.raises(ValueError):
            InlineKeyboardMarkup([[("x", "y")]])

    def test_case_12_inline_from_row_strings_valid(self):
        markup = InlineKeyboardMarkup.from_row(("a", "b", "c"))
        assert len(markup.inline_keyboard) == 1

    def test_case_13_reply_from_column_strings_valid(self):
        markup = ReplyKeyboardMarkup.from_column(["L1", "L2", "L3"])
        assert len(markup.keyboard) == 3

    def test_case_14_inline_from_column_strings_valid(self):
        markup = InlineKeyboardMarkup.from_column(["I1", "I2"])
        assert len(markup.inline_keyboard) == 2

    def test_case_15_reply_keyboard_bytes_invalid(self):
        with pytest.raises(ValueError):
            ReplyKeyboardMarkup(b"abc")

    def test_case_16_inline_keyboard_string_invalid(self):
        with pytest.raises(ValueError):
            InlineKeyboardMarkup("abc")
