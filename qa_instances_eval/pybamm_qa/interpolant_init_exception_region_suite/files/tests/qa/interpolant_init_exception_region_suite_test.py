import numpy as np
import pybamm


class TestInterpolantInitExceptionRegionQA:
    def _construct(self, x, y, children, **kwargs):
        result = pybamm.Interpolant(x, y, children, **kwargs)
        assert result.dimension in (1, 2, 3)

    def test_case_01(self):
        x = np.linspace(-2, 3, 21); self._construct(x, np.sin(x) + x**2, pybamm.Time(), interpolator="linear", extrapolate=False)
    def test_case_02(self):
        x = np.linspace(0, 4, 17); y = np.column_stack([np.exp(-x), np.cos(x), x**3]); self._construct(x, y, pybamm.Scalar(1.5), interpolator="cubic")
    def test_case_03(self):
        x = np.linspace(0, 2, 14); self._construct(x, np.linspace(0, 1, 15), pybamm.Time(), interpolator="pchip")
    def test_case_04(self):
        x = np.array([0.0, 0.4, 1.2, 0.9, 2.5]); self._construct(x, np.sin(x), pybamm.Time(), interpolator="linear")
    def test_case_05(self):
        x1, x2 = np.linspace(-1, 1, 7), np.linspace(0, 3, 9); y = x1[:, None] ** 2 + np.cos(x2[None, :]); self._construct((x1, x2), y, (pybamm.Scalar(0.2), pybamm.Scalar(1.1)), interpolator="cubic")
    def test_case_06(self):
        x1, x2 = np.linspace(0, 1, 5), np.linspace(0, 2, 6); self._construct((x1, x2), np.linspace(0, 1, 30), (pybamm.Time(), pybamm.Scalar(1)), interpolator="linear")
    def test_case_07(self):
        x1, x2 = np.linspace(0, 1, 6), np.linspace(-1, 1, 8); self._construct((x1, x2), x1[:, None] + x2[None, :], (pybamm.Time(), pybamm.Scalar(0)), interpolator="pchip")
    def test_case_08(self):
        x1, x2, x3 = np.linspace(0, 1, 5), np.linspace(-1, 1, 6), np.linspace(2, 4, 7); y = x1[:, None, None] + x2[None, :, None] ** 2 + x3[None, None, :]; self._construct((x1, x2, x3), y, (pybamm.Scalar(0.1), pybamm.Scalar(0.2), pybamm.Scalar(2.5)), interpolator="linear", extrapolate=False)
    def test_case_09(self):
        x1, x2, x3 = np.linspace(0, 1, 5), np.linspace(0, 2, 6), np.linspace(0, 3, 7); self._construct((x1, x2, x3), np.ones((5, 6, 7)), (pybamm.Time(), pybamm.Scalar(1), pybamm.Scalar(2)), interpolator="pchip")
    def test_case_10(self):
        x1, x2 = np.linspace(0, 1, 7), np.linspace(0, 2, 8); self._construct((x1, x2), x1[:, None] * x2[None, :], (pybamm.Time(),), interpolator="linear")
