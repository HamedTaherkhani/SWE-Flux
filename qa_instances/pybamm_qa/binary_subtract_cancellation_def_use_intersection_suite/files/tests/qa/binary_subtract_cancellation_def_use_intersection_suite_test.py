from __future__ import annotations

import pybamm


class TestBinarySubtractCancellationDefUseIntersectionQA:
    def _build_case(self, seed):
        anchor = pybamm.Variable(f"qa subtract anchor {seed}")
        nested = pybamm.Addition(
            pybamm.Variable(f"qa subtract nested {seed}"),
            pybamm.Scalar(seed + 0.25),
        )
        right = pybamm.Addition(nested, pybamm.Variable(f"qa subtract tail {seed}"))
        left = pybamm.Addition(anchor, right)
        result = pybamm.subtract(left, right)
        assert result is anchor
        return result

    def test_case_01(self):
        assert self._build_case(1).name.endswith("1")

    def test_case_02(self):
        assert self._build_case(2).name.endswith("2")

    def test_case_03(self):
        assert self._build_case(3).name.endswith("3")

    def test_case_04(self):
        assert self._build_case(4).name.endswith("4")

    def test_case_05(self):
        assert self._build_case(5).name.endswith("5")

    def test_case_06(self):
        assert self._build_case(6).name.endswith("6")

    def test_case_07(self):
        assert self._build_case(7).name.endswith("7")

    def test_case_08(self):
        assert self._build_case(8).name.endswith("8")

    def test_case_09(self):
        assert self._build_case(9).name.endswith("9")

    def test_case_10(self):
        assert self._build_case(10).name.endswith("10")
