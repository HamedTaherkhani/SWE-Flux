import numpy as np

from control.margins import _poly_z_invz, _poly_z_wstab
from control.xferfcn import tf


def _evaluate(num, den, dt):
    args = _poly_z_invz(tf(num, den, dt))
    z, w = _poly_z_wstab(*args, epsw=0.0)
    assert np.asarray(z).shape == np.asarray(w).shape
    assert np.all(np.isfinite(np.asarray(w, dtype=float)))
    return z, w


class TestDiscreteStabilityGuessRangeQA:
    def test_case_01(self):
        z, w = _evaluate([0.4, 0.15], [1.0, -0.35, 0.12], 0.10)
        assert np.asarray(w).size <= 1

    def test_case_02(self):
        z, w = _evaluate([0.2, -0.05], [1.0, -0.7, 0.24], 0.20)
        assert np.asarray(z).size <= 1

    def test_case_03(self):
        z, w = _evaluate([0.08, 0.03, -0.01], [1.0, -0.55, 0.18, -0.02], 0.15)
        assert np.asarray(w).ndim <= 1

    def test_case_04(self):
        z, w = _evaluate([0.6], [1.0, -0.2, 0.05], 0.25)
        assert np.asarray(z).ndim <= 1

    def test_case_05(self):
        z, w = _evaluate([0.15, 0.02], [1.0, -1.05, 0.42], 0.12)
        assert np.asarray(w).size <= 1

    def test_case_06(self):
        z, w = _evaluate([0.35, -0.12], [1.0, -0.25, 0.5, -0.08], 0.30)
        assert np.asarray(z).shape == np.asarray(w).shape

    def test_case_07(self):
        z, w = _evaluate([0.5, 0.1], [1.0, -0.9, 0.3], 0.18)
        assert np.asarray(w).ndim <= 1

    def test_case_08(self):
        z, w = _evaluate([0.12, -0.04], [1.0, -0.15, 0.35], 0.08)
        assert np.asarray(z).size <= 1

    def test_case_09(self):
        z, w = _evaluate([0.25, 0.05, 0.01], [1.0, -0.62, 0.22, -0.04], 0.22)
        assert np.asarray(w).shape == np.asarray(z).shape

    def test_case_10(self):
        z, w = _evaluate([0.18], [1.0, -0.48, 0.11], 0.16)
        assert np.asarray(w).size <= 1
