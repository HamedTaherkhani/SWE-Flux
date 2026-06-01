import numpy as np

from control.bdalg import combine_tf
from control.xferfcn import TransferFunction, tf


def _assert_tf_shape(sys, outputs, inputs):
    assert isinstance(sys, TransferFunction)
    assert sys.noutputs == outputs
    assert sys.ninputs == inputs


class TestCombineTfDefUseIntersectionQA:
    def test_case_01(self):
        s = tf([1, 0], [1])
        out = combine_tf([[1 / (s + 1), s / (s + 2)]], name="case01")
        _assert_tf_shape(out, 1, 2)

    def test_case_02(self):
        s = tf([1, 0], [1])
        out = combine_tf([[s + 1], [2 / (s + 3)]], outputs=["a", "b"])
        _assert_tf_shape(out, 2, 1)

    def test_case_03(self):
        s = tf([1, 0], [1])
        out = combine_tf([[s, 0], [1 / (s + 4), -2]], inputs=["u0", "u1"])
        _assert_tf_shape(out, 2, 2)

    def test_case_04(self):
        s = tf([1, 0], [1])
        block = tf(
            [[[1], [2]], [[3], [4]]],
            [[[1, 1], [1, 2]], [[1, 3], [1, 4]]],
        )
        second = tf([[[1]], [[1]]], [[[1, 5]], [[1, 6]]])
        out = combine_tf([[block, second]])
        _assert_tf_shape(out, 2, 3)

    def test_case_05(self):
        s = tf([1, 0], [1])
        out = combine_tf(
            [[np.eye(2), np.zeros((2, 1))],
             [np.zeros((1, 2)), s / (s + 1)]])
        _assert_tf_shape(out, 3, 3)

    def test_case_06(self):
        z = tf([1, 0], [1], 0.2)
        out = combine_tf([[z / (z - 0.4), 1], [0, (z + 0.1) / (z - 0.8)]])
        _assert_tf_shape(out, 2, 2)
        assert out.dt == 0.2

    def test_case_07(self):
        z = tf([1, 0], [1], 0.5)
        block = tf([[[1], [0.5]]], [[[1, -0.3], [1, -0.2]]], 0.5)
        out = combine_tf([[block], [z / (z - 0.1), 2]])
        _assert_tf_shape(out, 2, 2)
        assert out.dt == 0.5

    def test_case_08(self):
        s = tf([1, 0], [1])
        out = combine_tf([[[1, 2], s + 1], [[0, 3], 1 / (s + 6)]])
        _assert_tf_shape(out, 2, 3)

    def test_case_09(self):
        s = tf([1, 0], [1])
        out = combine_tf([[s / (s + 1), 2, 3 / (s + 7)]], inputs=3)
        _assert_tf_shape(out, 1, 3)

    def test_case_10(self):
        s = tf([1, 0], [1])
        out = combine_tf([[1], [s / (s + 2)], [np.array([[3]])]])
        _assert_tf_shape(out, 3, 1)
