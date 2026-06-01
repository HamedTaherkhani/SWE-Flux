import numpy as np

from control.statesp import ss
from control.sysnorm import system_norm


def _system(a00, a11, bscale, c0, c1, dval):
    return ss(
        [[a00, 0.08], [0.0, a11]],
        [[bscale], [0.35 * bscale]],
        [[c0, c1]],
        [[dval]],
    )


def _evaluate(sys, tol):
    value = system_norm(sys, p="inf", method="scipy", tol=tol)
    assert np.isfinite(value)
    assert value >= 0
    return value


class TestLinfBisectionStateRangeQA:
    def test_case_01(self):
        assert _evaluate(_system(-1.2, -2.0, 0.6, 1.0, 0.2, 0.0), 1e-2) >= 0

    def test_case_02(self):
        assert _evaluate(_system(-0.8, -1.5, 1.1, 0.7, -0.4, 0.1), 8e-3) >= 0

    def test_case_03(self):
        assert _evaluate(_system(-2.5, -0.9, 0.4, -1.2, 0.8, -0.05), 7e-3) >= 0

    def test_case_04(self):
        assert _evaluate(_system(-0.6, -1.1, 1.4, 1.3, 0.6, 0.2), 6e-3) >= 0

    def test_case_05(self):
        assert _evaluate(_system(-1.8, -2.8, 0.9, 0.5, -1.0, -0.15), 5e-3) >= 0

    def test_case_06(self):
        assert _evaluate(_system(-0.45, -1.7, 1.2, -0.9, 0.3, 0.05), 9e-3) >= 0

    def test_case_07(self):
        assert _evaluate(_system(-1.0, -3.0, 0.7, 1.6, -0.2, 0.25), 4e-3) >= 0

    def test_case_08(self):
        assert _evaluate(_system(-2.2, -1.3, 1.5, 0.4, 1.1, -0.1), 8e-3) >= 0

    def test_case_09(self):
        assert _evaluate(_system(-0.7, -2.4, 0.8, -1.4, -0.5, 0.12), 6e-3) >= 0

    def test_case_10(self):
        assert _evaluate(_system(-1.6, -0.75, 1.0, 0.9, 0.9, -0.2), 5e-3) >= 0
