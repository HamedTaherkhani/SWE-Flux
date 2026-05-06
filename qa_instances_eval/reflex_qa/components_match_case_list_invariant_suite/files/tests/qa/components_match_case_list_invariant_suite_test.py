from __future__ import annotations

from reflex.components.core.match import Match


class TestComponentsMatchCaseListInvariantOneQA:
    def test_two_element_case(self):
        result = Match._process_match_cases([("a", "A")])
        assert len(result[0]) == 2


class TestComponentsMatchCaseListInvariantTwoQA:
    def test_three_element_case(self):
        result = Match._process_match_cases([("a", "b", "AB")])
        assert len(result[0]) == 3


class TestComponentsMatchCaseListInvariantThreeQA:
    def test_two_cases(self):
        result = Match._process_match_cases([("x", "X"), ("y", "Y")])
        assert len(result) == 2


class TestComponentsMatchCaseListInvariantFourQA:
    def test_four_element_case(self):
        result = Match._process_match_cases([("w", "x", "y", "Z")])
        assert len(result[0]) == 4


class TestComponentsMatchCaseListInvariantFiveQA:
    def test_mixed_case_lengths(self):
        result = Match._process_match_cases([("ready", "done"), ("wait", "hold", "pending")])
        assert [len(case) for case in result] == [2, 3]


class TestComponentsMatchCaseListInvariantSixQA:
    def test_numeric_conditions(self):
        result = Match._process_match_cases([(1, 2, "small"), (3, "large")])
        assert len(result) == 2


class TestComponentsMatchCaseListInvariantSevenQA:
    def test_boolean_conditions(self):
        result = Match._process_match_cases([(True, "yes"), (False, "no")])
        assert len(result[0]) == 2


class TestComponentsMatchCaseListInvariantEightQA:
    def test_many_patterns(self):
        result = Match._process_match_cases([("n", "e", "s", "w", "direction")])
        assert len(result[0]) == 5


class TestComponentsMatchCaseListInvariantNineQA:
    def test_three_cases_with_aliases(self):
        result = Match._process_match_cases([("a1", "a2", "A"), ("b1", "B"), ("c1", "c2", "C")])
        assert len(result) == 3


class TestComponentsMatchCaseListInvariantTenQA:
    def test_long_final_case(self):
        result = Match._process_match_cases([("low", "L"), ("mid", "middle", "M"), ("h1", "h2", "h3", "H")])
        assert [len(case) for case in result] == [2, 3, 4]
