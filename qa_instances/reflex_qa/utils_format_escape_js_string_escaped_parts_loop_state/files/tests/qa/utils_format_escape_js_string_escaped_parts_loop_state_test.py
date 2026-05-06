from __future__ import annotations

from reflex.utils.format import _escape_js_string


class TestUtilsFormatEscapeJsStringEscapedPartsLoopStateQA:
    def test_utils_format_escape_js_string_escaped_parts_loop_state_case(self):
        string = (
            "pre`one`${state.value}`mid\\`literal`"
            "${items.map((x) => `${x.id}`)}`tail`end"
        )

        returned = _escape_js_string(string)

        assert returned == (
            "pre\\`one\\`${state.value}\\`mid\\`literal\\`"
            "${items.map((x) => `${x.id}\\`)}\\`tail\\`end"
        )
