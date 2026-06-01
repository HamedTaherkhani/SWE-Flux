import numpy as np

from control.xferfcn import tf


def _check_common_den(sys):
    num, den, denorder = sys._common_den()
    assert den.shape[0] == sys.ninputs
    assert denorder.shape == (sys.ninputs,)
    assert num.shape[1] >= sys.ninputs
    assert np.all(denorder >= 0)
    assert np.all(np.isfinite(den))
    assert np.all(np.isfinite(num))
    return num, den, denorder


class TestCommonDenSISOFirstOrderQA:
    def test_siso_first_order_has_no_prior_poles_to_match(self):
        sys = tf([1.0], [1.0, 2.0])
        _, den, denorder = _check_common_den(sys)
        assert den.shape[0] == 1
        assert denorder.tolist() == [1]


class TestCommonDenTwoByOneSharedPoleQA:
    def test_two_outputs_one_input_shared_denominator(self):
        sys = tf(
            [[[1.0]], [[2.0, 1.0]]],
            [[[1.0, 2.0]], [[1.0, 2.0]]],
        )
        _, den, denorder = _check_common_den(sys)
        assert den.shape[0] == 1
        assert denorder[0] == 1


class TestCommonDenTwoByOneDifferentPolesQA:
    def test_two_outputs_one_input_different_first_order_poles(self):
        sys = tf(
            [[[1.0]], [[1.0]]],
            [[[1.0, 1.0]], [[1.0, 3.0]]],
        )
        _, den, denorder = _check_common_den(sys)
        assert denorder[0] == 2


class TestCommonDenThreeByOneMixedZerosQA:
    def test_three_outputs_one_input_with_zero_transfer_entry(self):
        sys = tf(
            [[[1.0]], [[0.0]], [[1.0, 0.5]]],
            [[[1.0, 1.0]], [[1.0]], [[1.0, 2.0, 2.0]]],
        )
        _, den, denorder = _check_common_den(sys)
        assert denorder[0] >= 3


class TestCommonDenTwoByTwoColumnSharedQA:
    def test_two_by_two_with_columnwise_shared_denominators(self):
        sys = tf(
            [[[1.0], [0.5]], [[2.0], [1.0, -0.2]]],
            [
                [[1.0, 1.0], [1.0, 4.0]],
                [[1.0, 1.0], [1.0, 4.0]],
            ],
        )
        _, den, denorder = _check_common_den(sys)
        assert denorder.tolist() == [1, 1]


class TestCommonDenTwoByTwoColumnDifferentQA:
    def test_two_by_two_with_columnwise_different_poles(self):
        sys = tf(
            [[[1.0], [1.0]], [[1.0], [1.0]]],
            [
                [[1.0, 1.0], [1.0, 2.0]],
                [[1.0, 3.0], [1.0, 5.0]],
            ],
        )
        _, den, denorder = _check_common_den(sys)
        assert denorder.tolist() == [2, 2]


class TestCommonDenRepeatedPoleQA:
    def test_repeated_poles_and_single_poles_in_same_input(self):
        sys = tf(
            [[[1.0]], [[1.0, 1.0]], [[0.25]]],
            [
                [[1.0, 2.0, 1.0]],
                [[1.0, 1.0]],
                [[1.0, 3.0]],
            ],
        )
        _, den, denorder = _check_common_den(sys)
        assert denorder[0] >= 3


class TestCommonDenThreeByTwoMixedQA:
    def test_three_outputs_two_inputs_mixed_orders(self):
        sys = tf(
            [
                [[1.0], [0.2, 0.1]],
                [[0.5], [1.0]],
                [[1.0, -0.1], [0.0]],
            ],
            [
                [[1.0, 1.0], [1.0, 0.5, 1.5]],
                [[1.0, 2.0, 2.0], [1.0, 0.5, 1.5]],
                [[1.0, 4.0], [1.0]],
            ],
        )
        _, den, denorder = _check_common_den(sys)
        assert denorder.shape == (2,)
        assert np.all(denorder >= [3, 2])


class TestCommonDenThreeByThreeSparseQA:
    def test_three_by_three_sparse_mimo(self):
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
        _, den, denorder = _check_common_den(sys)
        assert denorder.shape == (3,)
        assert np.all(denorder >= 1)


class TestCommonDenComplexPairLikeQA:
    def test_second_order_complex_pair_like_denominators(self):
        sys = tf(
            [[[1.0], [0.75]], [[0.5, 0.1], [1.0]]],
            [
                [[1.0, 0.4, 4.0], [1.0, 0.2, 1.0]],
                [[1.0, 0.4, 4.0], [1.0, 0.8, 3.0]],
            ],
        )
        _, den, denorder = _check_common_den(sys)
        assert denorder.tolist() == [2, 4]
