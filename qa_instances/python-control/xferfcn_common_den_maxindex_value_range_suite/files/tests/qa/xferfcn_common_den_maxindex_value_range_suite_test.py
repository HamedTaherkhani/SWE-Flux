import numpy as np

from control.xferfcn import tf


def _inspect(sys):
    num, den, denorder = sys._common_den()
    assert den.shape[0] == sys.ninputs
    assert den.shape[1] == int(np.max(denorder)) + 1
    assert denorder.shape == (sys.ninputs,)
    assert np.all(denorder >= 0)
    assert np.all(np.isfinite(den))
    if num is not None:
        assert np.all(np.isfinite(num))
    return denorder


class TestCommonDenStateRangeQA:
    def test_case_01(self):
        denorder = _inspect(tf([2.0], [1.0]))
        assert denorder.tolist() == [0]

    def test_case_02(self):
        denorder = _inspect(tf([1.0, 0.4], [1.0, 2.0, 1.0]))
        assert denorder.tolist() == [2]

    def test_case_03(self):
        sys = tf(
            [[[1.0]], [[1.5]]],
            [[[1.0, 1.0]], [[1.0, 2.0]]],
        )
        denorder = _inspect(sys)
        assert denorder.tolist() == [2]

    def test_case_04(self):
        sys = tf(
            [[[1.0]], [[0.0]], [[1.0, -0.2]]],
            [[[1.0, 1.0]], [[1.0]], [[1.0, 0.5, 2.0]]],
        )
        denorder = _inspect(sys)
        assert denorder.tolist() == [3]

    def test_case_05(self):
        sys = tf(
            [[[1.0], [0.5]], [[2.0], [1.0, -0.2]]],
            [
                [[1.0, 1.0], [1.0, 4.0]],
                [[1.0, 1.0], [1.0, 4.0]],
            ],
        )
        denorder = _inspect(sys)
        assert denorder.tolist() == [1, 1]

    def test_case_06(self):
        sys = tf(
            [[[1.0], [1.0]], [[1.0], [0.7]], [[0.5], [1.0]]],
            [
                [[1.0, 1.0], [1.0, 0.3, 1.2]],
                [[1.0, 3.0], [1.0, 0.3, 1.2]],
                [[1.0, 5.0], [1.0, 2.0]],
            ],
        )
        denorder = _inspect(sys)
        assert denorder.tolist() == [3, 3]

    def test_case_07(self):
        sys = tf(
            [[[1.0], [0.3]], [[1.0, 0.2], [1.0]]],
            [
                [[1.0, 0.4, 4.0], [1.0, 0.2, 1.0]],
                [[1.0, 0.4, 4.0], [1.0, 0.8, 3.0]],
            ],
        )
        denorder = _inspect(sys)
        assert denorder.tolist() == [2, 4]

    def test_case_08(self):
        sys = tf(
            [
                [[1.0], [0.0], [1.0, 0.2]],
                [[0.5], [1.0], [0.0]],
                [[1.0, -0.3], [0.4], [2.0]],
            ],
            [
                [[1.0, 1.0], [1.0], [1.0, 2.0, 2.0]],
                [[1.0, 3.0], [1.0, 0.8], [1.0]],
                [[1.0, 1.0], [1.0, 2.5], [1.0, 0.6, 1.0]],
            ],
        )
        denorder = _inspect(sys)
        assert denorder.shape == (3,)
        assert np.max(denorder) >= 3

    def test_case_09(self):
        sys = tf(
            [[[1.0]], [[1.0, 1.0]], [[0.25]], [[1.0, -0.5]]],
            [
                [[1.0, 2.0, 1.0]],
                [[1.0, 1.0]],
                [[1.0, 3.0]],
                [[1.0, 0.5, 0.25]],
            ],
        )
        denorder = _inspect(sys)
        assert denorder.tolist() == [5]

    def test_case_10(self):
        sys = tf(
            [
                [[1.0], [0.2], [1.0, 0.5]],
                [[0.0], [1.0], [0.4]],
                [[1.0, -0.1], [0.3, 0.1], [0.8]],
            ],
            [
                [[1.0, 1.0], [1.0, 0.5, 1.5], [1.0, 0.1, 2.0]],
                [[1.0], [1.0, 0.5, 1.5], [1.0, 4.0]],
                [[1.0, 2.0, 2.0], [1.0, 0.25, 0.75], [1.0, 0.1, 2.0]],
            ],
        )
        denorder = _inspect(sys)
        assert denorder.shape == (3,)
        assert np.max(denorder) >= 4
