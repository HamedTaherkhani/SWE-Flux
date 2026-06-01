import numpy as np

from control.rlocus import _default_gains


def _execute(num_coeffs, den_coeffs, xlim=None, ylim=None):
    gains, roots, used_xlim, used_ylim = _default_gains(
        np.poly1d(num_coeffs), np.poly1d(den_coeffs), xlim, ylim)
    assert gains.ndim == 1
    assert gains.size >= 53
    assert roots.shape[0] == gains.size
    assert roots.shape[1] == len(den_coeffs) - 1
    assert len(used_xlim) == 2
    assert len(used_ylim) == 2
    assert np.all(np.isfinite(gains))
    return gains, roots


class TestDefaultGainsStateRangeQA:
    def test_case_01(self):
        gains, roots = _execute([1.0], [1.0, 2.0, 1.0])
        assert roots.shape[1] == 2
        assert gains[-1] > gains[0]

    def test_case_02(self):
        gains, roots = _execute(
            [1.0, 0.6], [1.0, 0.8, 2.2, 0.4], xlim=[-6.0, 1.5])
        assert roots.shape[1] == 3
        assert np.isfinite(roots).all()

    def test_case_03(self):
        gains, roots = _execute(
            [1.0], [1.0, 0.0, 2.0, 0.0, 1.0], ylim=[-0.4, 0.4])
        assert roots.shape[1] == 4
        assert gains.size > 60

    def test_case_04(self):
        gains, roots = _execute(
            [1.0, 1.2], [1.0, 3.5, 4.6, 2.0, 0.4],
            xlim=[-8.0, 2.0], ylim=[-3.0, 3.0])
        assert roots.shape[1] == 4
        assert gains[-1] > 0

    def test_case_05(self):
        gains, roots = _execute([1.0], [1.0, 3.0, 3.0, 1.0])
        assert roots.shape[1] == 3
        assert np.max(gains) > 100

    def test_case_06(self):
        gains, roots = _execute(
            [1.0, 0.2], [1.0, 0.45, 0.55, 0.18], ylim=[-6.0, 6.0])
        assert roots.shape[1] == 3
        assert gains.size > 100

    def test_case_07(self):
        gains, roots = _execute(
            [1.0, 2.5, 1.0], [1.0, 1.5, 4.0, 2.0, 0.7],
            xlim=[-2.0, 0.5], ylim=[-9.0, 9.0])
        assert roots.shape[1] == 4
        assert np.isfinite(roots).all()

    def test_case_08(self):
        gains, roots = _execute(
            [1.0, -0.4], [1.0, 0.9, 2.8, 1.1, 0.3], xlim=[-12.0, 3.0])
        assert roots.shape[1] == 4
        assert gains.size > 50

    def test_case_09(self):
        gains, roots = _execute(
            [1.0, 0.1], [1.0, 0.5, 0.5, 0.2],
            xlim=[-1.2, 0.2], ylim=[-0.9, 0.9])
        assert roots.shape[1] == 3
        assert gains[-1] > gains[1]

    def test_case_10(self):
        gains, roots = _execute(
            [1.0, 1.0], [1.0, 0.4, 3.0, 0.2, 2.0])
        assert roots.shape[1] == 4
        assert np.isfinite(roots).all()
