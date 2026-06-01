import numpy as np
import pytest

from control.bdalg import feedback
from control.exception import ControlMIMONotImplemented
from control.frdata import FRD
from control.nlsys import nlsys
from control.statesp import ss
from control.xferfcn import tf


def _siso_ss(dt=0):
    return ss(
        [[-1.0, 0.25], [-0.5, -2.0]],
        [[1.0], [0.0]],
        [[0.0, 1.0]],
        [[0.05]],
        dt=dt,
    )


def _siso_tf(dt=0):
    if dt:
        return tf([0.2, 0.1], [1.0, -0.4], dt)
    return tf([1.0, 2.0], [1.0, 3.0, 2.0])


def _siso_frd():
    omega = np.array([0.4, 1.0, 2.0, 4.0])
    response = 1.0 / (1.0 + 1j * omega)
    return FRD(response, omega)


def _static_nonlinear_gain(scale=1.0):
    def update(t, x, u, params):
        return []

    def output(t, x, u, params):
        return [scale * np.tanh(u[0])]

    return nlsys(
        update, output, states=0, inputs=1, outputs=1,
        name=f"sat_gain_{int(scale * 100):03d}",
    )


class TestFeedbackTransferFunctionUnityQA:
    def test_transfer_function_unity_feedback(self):
        closed = feedback(_siso_tf(), 1)
        assert closed.ninputs == 1
        assert closed.noutputs == 1


class TestFeedbackTransferFunctionDynamicQA:
    def test_transfer_function_dynamic_feedback(self):
        closed = feedback(_siso_tf(), tf([0.5], [1.0, 1.5]), sign=1)
        assert closed.dt == 0
        assert len(closed.poles()) >= 2


class TestFeedbackTransferFunctionDiscreteQA:
    def test_discrete_transfer_function_feedback(self):
        closed = feedback(_siso_tf(dt=0.2), tf([0.3], [1.0, -0.1], 0.2))
        assert closed.dt == 0.2
        assert closed.ninputs == closed.noutputs == 1


class TestFeedbackStateSpaceUnityQA:
    def test_state_space_unity_feedback(self):
        closed = feedback(_siso_ss(), 1)
        assert closed.nstates == 2
        assert closed.ninputs == closed.noutputs == 1


class TestFeedbackStateSpaceDynamicQA:
    def test_state_space_dynamic_feedback(self):
        plant = _siso_ss()
        controller = ss([[-3.0]], [[1.0]], [[2.0]], [[0.0]])
        closed = feedback(plant, controller, sign=1)
        assert closed.nstates == 3
        assert closed.dt == 0


class TestFeedbackScalarWithStateSpaceSecondQA:
    def test_scalar_first_argument_uses_state_space_second_type(self):
        closed = feedback(2.0, _siso_ss())
        assert closed.nstates == 2
        assert closed.ninputs == closed.noutputs == 1


class TestFeedbackFRDUnityQA:
    def test_frd_unity_feedback(self):
        closed = feedback(_siso_frd(), 1)
        assert closed.frdata.shape == (1, 1, 4)
        assert np.all(np.isfinite(closed.frdata))


class TestFeedbackScalarWithFRDSecondQA:
    def test_scalar_first_argument_uses_frd_second_type(self):
        closed = feedback(0.75, _siso_frd(), sign=1)
        assert closed.frdata.shape == (1, 1, 4)
        assert closed.omega.size == 4


class TestFeedbackNonlinearSystemsQA:
    def test_nonlinear_feedback_path(self):
        plant = _static_nonlinear_gain(0.8)
        controller = _static_nonlinear_gain(0.5)
        closed = feedback(plant, controller)
        assert closed.ninputs == 1
        assert closed.noutputs == 1


class TestFeedbackMIMOTransferFunctionExceptionQA:
    def test_mimo_transfer_function_feedback_reaches_tf_implementation(self):
        mimo = tf(
            [[[1.0], [0.5]], [[0.25], [1.0]]],
            [[[1.0, 1.0], [1.0, 2.0]], [[1.0, 3.0], [1.0, 4.0]]],
        )
        with pytest.raises(ControlMIMONotImplemented):
            feedback(mimo, 1)
