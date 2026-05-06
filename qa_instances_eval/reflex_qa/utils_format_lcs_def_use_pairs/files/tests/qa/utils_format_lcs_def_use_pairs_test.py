from __future__ import annotations

from reflex.utils.format import length_of_largest_common_substring


class TestUtilsFormatLcsDefUsePairsQA:
    def test_utils_format_lcs_def_use_pairs_case(self):
        left = "abracadabra-trace"
        right = "cadabra-trial"

        result = length_of_largest_common_substring(left, right)

        assert result == 10
