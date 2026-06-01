import numpy as np
import pytest

from control.frdata import FRD
from control.lti import evalfr
from control.statesp import ss
from control.xferfcn import tf


def _continuous_siso_ss():
    return ss(
        [[-1.0, 0.4], [-0.2, -2.0]],
        [[1.0], [0.25]],
        [[0.5, -1.0]],
        [[0.05]],
    )


def _continuous_mimo_ss():
    return ss(
        [[-1.0, 0.0], [0.3, -3.0]],
        [[1.0, 0.0], [0.2, 0.5]],
        [[1.0, 0.0], [0.0, -1.0]],
        [[0.0, 0.1], [0.2, 0.0]],
    )


def _discrete_siso_ss():
    return ss([[0.7]], [[1.0]], [[0.4]], [[0.05]], dt=0.2)


def _continuous_siso_tf():
    return tf([2.0, 1.0], [1.0, 3.0, 2.0])


def _continuous_mimo_tf():
    return tf(
        [[[1.0], [0.5, 1.0]], [[0.25], [1.0, -0.2]]],
        [
            [[1.0, 1.0], [1.0, 2.0, 2.0]],
            [[1.0, 3.0], [1.0, 0.5, 1.0]],
        ],
    )


def _discrete_siso_tf():
    return tf([0.2, 0.1], [1.0, -0.4], 0.25)


def _frd_siso(smooth=False):
    omega = np.array([0.25, 0.75, 1.5, 3.0])
    response = (1.0 + 0.2j * omega) / (1.0 + 1j * omega)
    return FRD(response, omega, smooth=smooth)


class TestEvalfrStateSpaceContinuousScalarQA:
    def test_continuous_state_space_scalar_frequency(self):
        value = evalfr(_continuous_siso_ss(), 0.5j)
        assert np.asarray(value).shape == ()
        assert np.isfinite(value)


class TestEvalfrStateSpaceMIMOScalarQA:
    def test_mimo_state_space_keeps_matrix_shape(self):
        value = evalfr(_continuous_mimo_ss(), 1.2j, squeeze=False)
        assert value.shape == (2, 2)
        assert np.all(np.isfinite(value))


class TestEvalfrStateSpaceVectorQA:
    def test_state_space_vector_frequency_response(self):
        value = evalfr(_continuous_siso_ss(), [0.3j, 0.9j, 1.7j], squeeze=False)
        assert value.shape == (1, 1, 3)
        assert np.all(np.isfinite(value))


class TestEvalfrStateSpaceDiscreteQA:
    def test_discrete_state_space_z_plane_point(self):
        z = np.exp(1j * 0.6 * 0.2)
        value = evalfr(_discrete_siso_ss(), z)
        assert np.asarray(value).shape == ()
        assert np.isfinite(value)


class TestEvalfrTransferFunctionContinuousScalarQA:
    def test_continuous_transfer_function_scalar_frequency(self):
        value = evalfr(_continuous_siso_tf(), 0.4j)
        assert np.asarray(value).shape == ()
        assert np.isfinite(value)


class TestEvalfrTransferFunctionMIMOQA:
    def test_mimo_transfer_function_matrix_response(self):
        value = evalfr(_continuous_mimo_tf(), 1.1j, squeeze=False)
        assert value.shape == (2, 2)
        assert np.all(np.isfinite(value))


class TestEvalfrTransferFunctionDiscreteVectorQA:
    def test_discrete_transfer_function_vector_response(self):
        points = np.exp(1j * np.array([0.2, 0.8]) * 0.25)
        value = evalfr(_discrete_siso_tf(), points, squeeze=False)
        assert value.shape == (1, 1, 2)
        assert np.all(np.isfinite(value))


class TestEvalfrFRDExactScalarQA:
    def test_frd_exact_grid_scalar_frequency(self):
        value = evalfr(_frd_siso(), 0.75j)
        assert np.asarray(value).shape == ()
        assert np.isfinite(value)


class TestEvalfrFRDInterpolatingVectorQA:
    def test_interpolating_frd_vector_frequency(self):
        value = evalfr(_frd_siso(smooth=True), [0.5j, 1.0j, 2.0j], squeeze=False)
        assert value.shape == (1, 1, 3)
        assert np.all(np.isfinite(value))


class TestEvalfrFRDRejectsNonImaginaryQA:
    def test_frd_nonimaginary_point_still_dispatches_before_error(self):
        with pytest.raises(ValueError):
            evalfr(_frd_siso(), 1.0 + 0.75j)
