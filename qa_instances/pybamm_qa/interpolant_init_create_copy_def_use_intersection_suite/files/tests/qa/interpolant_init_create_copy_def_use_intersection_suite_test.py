from __future__ import annotations

import numpy as np
import pybamm


def _base_interpolant(offset):
    x1 = np.array([0.0, 1.0, 2.0])
    x2 = np.array([-1.0, 0.5, 2.0])
    x3 = np.array([10.0, 20.0, 30.0])
    y = (
        x1[:, np.newaxis, np.newaxis]
        + 2 * x2[np.newaxis, :, np.newaxis]
        - 0.1 * x3[np.newaxis, np.newaxis, :]
        + offset
    )
    children = [pybamm.Scalar(0.5), pybamm.Scalar(0.0), pybamm.Scalar(15.0)]
    return pybamm.Interpolant((x1, x2, x3), y, children, interpolator="linear")


BASE_INTERPOLANTS = [_base_interpolant(float(i)) for i in range(10)]


class TestInterpolantInitCreateCopyDefUseIntersectionQA:
    def _copy_and_evaluate(self, index, point):
        copied = BASE_INTERPOLANTS[index].create_copy(
            [pybamm.Scalar(point[0]), pybamm.Scalar(point[1]), pybamm.Scalar(point[2])]
        )
        value = copied.evaluate()
        assert np.asarray(value).shape == (1,)
        assert np.isfinite(float(np.asarray(value)[0]))
        return copied

    def test_case_01(self):
        assert self._copy_and_evaluate(0, (0.25, -0.5, 12.0)).dimension == 3

    def test_case_02(self):
        assert self._copy_and_evaluate(1, (0.75, 0.0, 18.0)).dimension == 3

    def test_case_03(self):
        assert self._copy_and_evaluate(2, (1.25, 0.5, 22.0)).dimension == 3

    def test_case_04(self):
        assert self._copy_and_evaluate(3, (1.75, 1.0, 28.0)).dimension == 3

    def test_case_05(self):
        assert self._copy_and_evaluate(4, (0.1, 1.5, 11.0)).dimension == 3

    def test_case_06(self):
        assert self._copy_and_evaluate(5, (0.9, -0.25, 19.0)).dimension == 3

    def test_case_07(self):
        assert self._copy_and_evaluate(6, (1.1, 1.25, 21.0)).dimension == 3

    def test_case_08(self):
        assert self._copy_and_evaluate(7, (1.9, 1.75, 29.0)).dimension == 3

    def test_case_09(self):
        assert self._copy_and_evaluate(8, (0.4, 0.25, 16.0)).dimension == 3

    def test_case_10(self):
        assert self._copy_and_evaluate(9, (1.6, -0.75, 24.0)).dimension == 3
