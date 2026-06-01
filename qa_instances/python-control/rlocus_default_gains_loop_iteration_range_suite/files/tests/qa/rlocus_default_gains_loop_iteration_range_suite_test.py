import numpy as np

from control.rlocus import _default_gains


def _run(num_coeffs, den_coeffs):
    gains, roots, xlim, ylim = _default_gains(
        np.poly1d(num_coeffs), np.poly1d(den_coeffs), None, None
    )
    assert gains.ndim == 1
    assert roots.shape[0] == gains.size
    assert roots.shape[1] == len(den_coeffs) - 1
    assert len(xlim) == 2
    assert len(ylim) == 2
    return gains, roots


class TestDefaultGainsRepeatedRealPolesQA:
    def test_repeated_real_poles(self):
        gains, roots = _run([1.0], [1.0, 2.0, 1.0])
        assert gains.size > 50
        assert roots.shape[1] == 2


class TestDefaultGainsTriplePoleQA:
    def test_triple_real_pole(self):
        gains, roots = _run([1.0], [1.0, 3.0, 3.0, 1.0])
        assert gains.size > 50
        assert roots.shape[1] == 3


class TestDefaultGainsFourthOrderWithZeroQA:
    def test_fourth_order_with_nearby_zero(self):
        gains, roots = _run([1.0, 1.0], [1.0, 4.0, 6.0, 4.0, 1.0])
        assert gains.size > 50
        assert roots.shape[1] == 4


class TestDefaultGainsLightlyDampedCubicQA:
    def test_lightly_damped_cubic(self):
        gains, roots = _run([1.0, 2.0], [1.0, 0.8, 2.0, 0.5])
        assert gains.size > 100
        assert roots.shape[1] == 3


class TestDefaultGainsIntegratorLikeCubicQA:
    def test_integrator_like_cubic(self):
        gains, roots = _run([1.0], [1.0, 0.2, 4.0, 0.1])
        assert gains.size > 50
        assert roots.shape[1] == 3


class TestDefaultGainsFourthOrderMixedZerosQA:
    def test_fourth_order_mixed_zeros(self):
        gains, roots = _run([1.0, 0.5], [1.0, 1.2, 3.4, 2.1, 1.0])
        assert gains.size > 50
        assert roots.shape[1] == 4


class TestDefaultGainsQuarticWithTwoZerosQA:
    def test_quartic_with_two_zeros(self):
        gains, roots = _run([1.0, 3.0, 2.0], [1.0, 2.0, 5.0, 6.0, 2.0])
        assert gains.size > 100
        assert roots.shape[1] == 4


class TestDefaultGainsSymmetricQuarticQA:
    def test_symmetric_quartic_denominator(self):
        gains, roots = _run([1.0], [1.0, 0.0, 2.0, 0.0, 1.0])
        assert gains.size > 50
        assert roots.shape[1] == 4


class TestDefaultGainsSharpCubicQA:
    def test_sharp_cubic_geometry(self):
        gains, roots = _run([1.0, 0.1], [1.0, 0.5, 0.5, 0.2])
        assert gains.size > 150
        assert roots.shape[1] == 3


class TestDefaultGainsQuarticSparseQA:
    def test_sparse_quartic_geometry(self):
        gains, roots = _run([1.0, 1.0], [1.0, 0.4, 3.0, 0.2, 2.0])
        assert gains.size > 50
        assert roots.shape[1] == 4
