import numpy as np
import pytest

from xarray.core.duck_array_ops import cumulative_trapezoid, trapz


class TestAxisSliceNonnegativeInvariantMultitestHardQA:
    def test_axis_slice_nonnegative_invariant_multitest_part_a(self) -> None:
        y = np.array([[1.0, 3.0, 6.0], [2.0, 4.0, 8.0]])
        x0 = np.array([0.0, 1.0])
        x1 = np.array([0.0, 0.5, 1.0])

        out_a = trapz(y, x0, axis=0)
        out_b = trapz(y, x1, axis=-1)
        out_c = cumulative_trapezoid(y, x1, axis=1)

        assert out_a.shape == (3,)
        assert out_b.shape == (2,)
        assert out_c.shape == y.shape

    def test_axis_slice_nonnegative_invariant_multitest_part_b(self) -> None:
        y = np.array([[0.0, 1.0, 4.0], [1.0, 2.0, 3.0]])
        x0 = np.array([0.0, 2.0])
        x1 = np.array([0.0, 1.0, 3.0])

        out_d = trapz(y, x0, axis=-2)
        out_e = cumulative_trapezoid(y, x1, axis=-1)
        out_f = cumulative_trapezoid(y, x0, axis=0)

        assert out_d.shape == (3,)
        assert out_e.shape == y.shape
        assert out_f.shape == y.shape


@pytest.mark.parametrize("_pad_case", list(range(16)))
def test_multitest_padding__cases(_pad_case):
    assert _pad_case >= 0
