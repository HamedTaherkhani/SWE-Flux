from __future__ import annotations

import pybamm


class TestBinaryDivideProductCancellationDefUseIntersectionQA:
    def _build_case(self, seed):
        shared = pybamm.Addition(
            pybamm.Variable(f"qa divide shared {seed}"),
            pybamm.Scalar(seed + 1.5),
        )
        tail = pybamm.Subtraction(
            pybamm.Variable(f"qa divide tail {seed}"),
            pybamm.Variable(f"qa divide offset {seed}"),
        )
        left = pybamm.Multiplication(shared, tail)
        result = pybamm.divide(left, shared)
        assert isinstance(result, pybamm.Subtraction)
        assert result == tail
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
