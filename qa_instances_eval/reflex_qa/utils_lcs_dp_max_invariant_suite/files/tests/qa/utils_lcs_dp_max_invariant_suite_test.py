from __future__ import annotations

from reflex.utils.format import length_of_largest_common_substring


class TestUtilsLcsInvariantOneQA:
    def test_prefix_and_suffix_match(self):
        assert length_of_largest_common_substring("abcXz", "abcYz") == 3


class TestUtilsLcsInvariantTwoQA:
    def test_shifted_longer_middle(self):
        assert length_of_largest_common_substring("zzhelloQx", "aahelloRx") == 5


class TestUtilsLcsInvariantThreeQA:
    def test_repeated_short_after_long(self):
        assert length_of_largest_common_substring("mountain-path", "plain-mountain-x") == 9


class TestUtilsLcsInvariantFourQA:
    def test_single_tail_after_pair(self):
        assert length_of_largest_common_substring("ab12c", "ab34c") == 2


class TestUtilsLcsInvariantFiveQA:
    def test_separated_tokens(self):
        assert length_of_largest_common_substring("red-blue-green", "xx-blue-yy-green") == 6


class TestUtilsLcsInvariantSixQA:
    def test_overlap_at_end(self):
        assert length_of_largest_common_substring("compile-cache-z", "recompile-store-z") == 8


class TestUtilsLcsInvariantSevenQA:
    def test_numbers_and_letters(self):
        assert length_of_largest_common_substring("id-12345-x", "zz-12345-y-x") == 7


class TestUtilsLcsInvariantEightQA:
    def test_common_word_then_letter(self):
        assert length_of_largest_common_substring("alpha_beta_q", "alpha_gamma_q") == 6


class TestUtilsLcsInvariantNineQA:
    def test_two_clusters(self):
        assert length_of_largest_common_substring("startMIDend", "xxMIDyyend") == 3


class TestUtilsLcsInvariantTenQA:
    def test_longer_terminal_cluster(self):
        assert length_of_largest_common_substring("aa-render-b", "zz-render-c-b") == 8
