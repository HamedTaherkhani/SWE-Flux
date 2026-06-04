from __future__ import annotations

import numpy as np
import pybamm


class TestInterpolantFunctionEvaluateDefUseIntersectionQA:
    def _evaluate_at(self, point):
        x = np.array([0.0, 1.0, 2.0, 3.0])
        y = np.array([0.0, 2.0, 4.0, 6.0])
        interpolant = pybamm.Interpolant(
            x, y, pybamm.Scalar(point), interpolator="linear", extrapolate=True
        )
        result = interpolant.evaluate()
        assert result.shape == (1, 1)
        return float(result[0, 0])

    def test_case_01(self):
        assert self._evaluate_at(0.1) == 0.2

    def test_case_02(self):
        assert self._evaluate_at(0.2) == 0.4

    def test_case_03(self):
        assert self._evaluate_at(0.3) == 0.6

    def test_case_04(self):
        assert self._evaluate_at(0.4) == 0.8

    def test_case_05(self):
        assert self._evaluate_at(0.5) == 1.0

    def test_case_06(self):
        assert self._evaluate_at(0.6) == 1.2

    def test_case_07(self):
        assert self._evaluate_at(0.7) == 1.4

    def test_case_08(self):
        assert self._evaluate_at(0.8) == 1.6

    def test_case_09(self):
        assert self._evaluate_at(0.9) == 1.8

    def test_case_10(self):
        assert self._evaluate_at(1.0) == 2.0
