from __future__ import annotations

import pybamm


class TestBinaryMultiplyDivisionCancellationDefUseIntersectionQA:
    def _build_case(self, seed):
        base = pybamm.Addition(
            pybamm.Variable(f"qa multiply base {seed}"),
            pybamm.Scalar(seed + 2.0),
        )
        numerator = pybamm.Subtraction(
            pybamm.Variable(f"qa multiply numerator {seed}"),
            pybamm.Variable(f"qa multiply correction {seed}"),
        )
        right = pybamm.Division(numerator, base)
        result = pybamm.multiply(base, right)
        assert result is numerator
        return result

    def test_case_01(self):
        assert isinstance(self._build_case(1), pybamm.Subtraction)

    def test_case_02(self):
        assert isinstance(self._build_case(2), pybamm.Subtraction)

    def test_case_03(self):
        assert isinstance(self._build_case(3), pybamm.Subtraction)

    def test_case_04(self):
        assert isinstance(self._build_case(4), pybamm.Subtraction)

    def test_case_05(self):
        assert isinstance(self._build_case(5), pybamm.Subtraction)

    def test_case_06(self):
        assert isinstance(self._build_case(6), pybamm.Subtraction)

    def test_case_07(self):
        assert isinstance(self._build_case(7), pybamm.Subtraction)

    def test_case_08(self):
        assert isinstance(self._build_case(8), pybamm.Subtraction)

    def test_case_09(self):
        assert isinstance(self._build_case(9), pybamm.Subtraction)

    def test_case_10(self):
        assert isinstance(self._build_case(10), pybamm.Subtraction)
