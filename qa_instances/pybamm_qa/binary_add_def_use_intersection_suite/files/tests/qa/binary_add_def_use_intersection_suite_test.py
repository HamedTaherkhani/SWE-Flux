from __future__ import annotations

import pybamm


class TestBinaryAddDefUseIntersectionQA:
    def _make_sum(self, left_name, right_name):
        left = pybamm.Variable(left_name)
        right = pybamm.Variable(right_name)
        expression = left + right
        assert isinstance(expression, pybamm.Addition)
        assert expression.children[0] is left
        assert expression.children[1] is right
        return expression

    def test_case_01(self):
        assert self._make_sum("qa add left 01", "qa add right 01").name == "+"

    def test_case_02(self):
        assert self._make_sum("qa add left 02", "qa add right 02").name == "+"

    def test_case_03(self):
        assert self._make_sum("qa add left 03", "qa add right 03").name == "+"

    def test_case_04(self):
        assert self._make_sum("qa add left 04", "qa add right 04").name == "+"

    def test_case_05(self):
        assert self._make_sum("qa add left 05", "qa add right 05").name == "+"

    def test_case_06(self):
        assert self._make_sum("qa add left 06", "qa add right 06").name == "+"

    def test_case_07(self):
        assert self._make_sum("qa add left 07", "qa add right 07").name == "+"

    def test_case_08(self):
        assert self._make_sum("qa add left 08", "qa add right 08").name == "+"

    def test_case_09(self):
        assert self._make_sum("qa add left 09", "qa add right 09").name == "+"

    def test_case_10(self):
        assert self._make_sum("qa add left 10", "qa add right 10").name == "+"
