from __future__ import annotations

from reflex.utils.format import length_of_largest_common_substring


class TestUtilsFormatLcsMaxLengthLoopStateQA:
    def test_utils_format_lcs_max_length_loop_state_case(self):
        str1 = (
            "pre_STATE::/dashboard/[team]/metrics__ErrorBoundary__"
            "fallback_render::post::fallback"
        )
        str2 = (
            "xx/dashboard/[team]/metrics__ErrorBoundary__"
            "fallback_render::yy::fallback"
        )

        returned = length_of_largest_common_substring(str1, str2)

        assert returned == 59
