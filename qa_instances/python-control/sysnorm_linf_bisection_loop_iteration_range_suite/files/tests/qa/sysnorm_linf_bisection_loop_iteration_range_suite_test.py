import numpy as np

from control.statesp import ss
from control.sysnorm import system_norm
from control.xferfcn import tf


def _assert_finite_norm(sys, tol):
    value = system_norm(
        sys, p="inf", tol=tol, method="scipy", print_warning=False
    )
    assert np.isfinite(value)
    assert value > 0
    return value


class TestSysnormBisectionFirstOrderTightQA:
    def test_first_order_transfer_function_tight_tolerance(self):
        sys = tf([1.0], [1.0, 1.2])
        _assert_finite_norm(sys, 1e-5)


class TestSysnormBisectionFirstOrderLooseQA:
    def test_first_order_transfer_function_loose_tolerance(self):
        sys = tf([2.0], [1.0, 4.0])
        _assert_finite_norm(sys, 5e-2)


class TestSysnormBisectionSecondOrderPeakedQA:
    def test_second_order_transfer_function_peaked_response(self):
        sys = tf([1.5, 0.2], [1.0, 0.35, 2.0])
        _assert_finite_norm(sys, 1e-4)


class TestSysnormBisectionSecondOrderDampedQA:
    def test_second_order_transfer_function_damped_response(self):
        sys = tf([0.75], [1.0, 2.8, 3.0])
        _assert_finite_norm(sys, 2e-3)


class TestSysnormBisectionStateSpaceDirectFeedthroughQA:
    def test_state_space_with_direct_feedthrough(self):
        sys = ss(
            [[-1.0, 0.25], [-0.5, -2.5]],
            [[1.0], [0.4]],
            [[0.3, -1.2]],
            [[0.15]],
        )
        _assert_finite_norm(sys, 1e-4)


class TestSysnormBisectionStateSpaceMIMOQA:
    def test_mimo_state_space_two_by_two(self):
        sys = ss(
            [[-1.0, 0.2], [-0.3, -1.8]],
            [[1.0, 0.0], [0.2, 0.7]],
            [[0.5, -0.2], [1.0, 0.3]],
            [[0.1, 0.0], [0.0, -0.05]],
        )
        _assert_finite_norm(sys, 8e-4)


class TestSysnormBisectionThirdOrderStateSpaceQA:
    def test_third_order_state_space(self):
        sys = ss(
            [[-0.7, 0.4, 0.0], [-0.2, -1.3, 0.5], [0.0, -0.4, -2.1]],
            [[1.0], [0.3], [0.2]],
            [[0.4, -0.8, 0.6]],
            [[0.0]],
        )
        _assert_finite_norm(sys, 3e-5)


class TestSysnormBisectionDiscreteTransferFunctionQA:
    def test_discrete_transfer_function_bilinear_path(self):
        sys = tf([0.2, 0.05], [1.0, -0.55], 0.2)
        _assert_finite_norm(sys, 1e-3)


class TestSysnormBisectionDiscreteStateSpaceQA:
    def test_discrete_state_space_bilinear_path(self):
        sys = ss(
            [[0.5, 0.1], [0.0, 0.25]],
            [[1.0], [0.5]],
            [[0.25, -0.4]],
            [[0.02]],
            dt=0.1,
        )
        _assert_finite_norm(sys, 2e-4)


class TestSysnormBisectionLargerMIMOStateSpaceQA:
    def test_larger_mimo_state_space_path(self):
        sys = ss(
            [
                [-0.8, 0.2, 0.0, 0.1],
                [-0.3, -1.4, 0.4, 0.0],
                [0.0, -0.2, -2.2, 0.5],
                [0.1, 0.0, -0.4, -3.1],
            ],
            [[1.0, 0.0], [0.2, 0.5], [0.0, 0.7], [0.4, 0.1]],
            [[0.6, -0.2, 0.0, 0.3], [0.1, 0.4, -0.5, 0.2]],
            [[0.05, -0.02], [0.01, 0.04]],
        )
        _assert_finite_norm(sys, 6e-4)
