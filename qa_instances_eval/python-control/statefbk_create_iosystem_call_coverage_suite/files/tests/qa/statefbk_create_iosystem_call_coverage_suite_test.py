from __future__ import annotations

import numpy as np
import pytest

import control as ct


def _plant(name="plant", dt=0, inputs=None, outputs=None):
    inputs = ["u"] if inputs is None else inputs
    outputs = ["x0", "x1"] if outputs is None else outputs
    return ct.ss(
        [[0.0, 1.0], [-2.0, -0.8]],
        [[0.0], [1.0]],
        np.eye(2),
        np.zeros((2, 1)),
        dt=dt,
        name=name,
        inputs=inputs,
        outputs=outputs,
        states=["x0", "x1"],
    )


class TestStatefbkLinearTrajgenQA:
    def test_linear_trajgen_controller(self):
        sys = _plant(name="linear_trajgen")
        gain = np.array([[3.0, 2.0]])

        ctrl, closed = ct.create_statefbk_iosystem(sys, gain, name="ctrl")

        assert ctrl.ninputs == 5
        assert ctrl.noutputs == 1
        assert closed.nstates >= sys.nstates


class TestStatefbkCustomLabelsQA:
    def test_custom_desired_state_and_input_labels(self):
        sys = _plant(name="custom_labels", inputs=["throttle"])
        gain = np.array([[2.5, 1.25]])

        ctrl, closed = ct.create_statefbk_iosystem(
            sys, gain, xd_labels=["ref_pos", "ref_vel"],
            ud_labels=["ref_force"], name="label_ctrl")

        assert "ref_pos" in ctrl.input_labels
        assert "ref_force" in closed.input_labels


class TestStatefbkIntegralActionQA:
    def test_linear_controller_with_integral_action(self):
        sys = _plant(name="integral_action")
        gain = np.array([[4.0, 2.0, 0.75]])
        integral_action = np.array([[1.0, 0.0]])

        ctrl, closed = ct.create_statefbk_iosystem(
            sys, gain, integral_action=integral_action, name="int_ctrl")

        assert ctrl.nstates == 1
        assert closed.nstates >= 3


class TestStatefbkReferenceGainQA:
    def test_reference_gain_pattern(self):
        sys = _plant(name="refgain")
        gain = np.array([[2.0, 1.0]])
        feedforward = np.array([[1.5]])

        ctrl, closed = ct.create_statefbk_iosystem(
            sys, gain, feedfwd_gain=feedforward,
            feedfwd_pattern="refgain", ref_labels=["command"],
            name="ref_ctrl")

        assert ctrl.input_labels[0] == "command"
        assert closed.noutputs == 3


class TestStatefbkDiscreteIntegralQA:
    def test_discrete_time_integral_controller(self):
        sys = _plant(name="discrete_integral", dt=0.2)
        gain = np.array([[1.2, 0.8, 0.4]])
        integral_action = np.array([[0.0, 1.0]])

        ctrl, closed = ct.create_statefbk_iosystem(
            sys, gain, integral_action=integral_action, name="dint_ctrl")

        assert ctrl.dt == 0.2
        assert closed.dt == 0.2


class TestStatefbkNonlinearControllerQA:
    def test_array_gain_as_nonlinear_controller(self):
        sys = _plant(name="nonlinear_ctrl")
        gain = np.array([[1.8, 0.9]])

        ctrl, closed = ct.create_statefbk_iosystem(
            sys, gain, controller_type="nonlinear", name="nl_ctrl")

        assert isinstance(ctrl, ct.NonlinearIOSystem)
        assert closed.ninputs == 3


class TestStatefbkGainScheduleNearestQA:
    def test_one_dimensional_gain_schedule_nearest(self):
        sys = _plant(name="sched_nearest")
        gains = [np.array([[1.0, 0.4]]), np.array([[2.0, 0.9]]), np.array([[3.0, 1.4]])]
        points = [np.array([0.0]), np.array([1.0]), np.array([2.0])]

        ctrl, closed = ct.create_statefbk_iosystem(
            sys, (gains, points), gainsched_indices=[0],
            gainsched_method="nearest", name="sched_nearest_ctrl")

        assert ctrl.ninputs == 5
        assert closed.noutputs == 3


class TestStatefbkGainScheduleLinearQA:
    def test_two_dimensional_gain_schedule_linear(self):
        sys = _plant(name="sched_linear")
        gains = [
            np.array([[1.0, 0.4]]),
            np.array([[1.5, 0.7]]),
            np.array([[2.0, 1.0]]),
            np.array([[2.5, 1.3]]),
        ]
        points = [
            np.array([0.0, 0.0]),
            np.array([1.0, 0.0]),
            np.array([0.0, 1.0]),
            np.array([1.0, 1.0]),
        ]

        ctrl, closed = ct.create_statefbk_iosystem(
            sys, (gains, points), gainsched_indices=[0, 1],
            gainsched_method="linear", name="sched_linear_ctrl")

        assert ctrl.nstates == 0
        assert closed.nstates >= 2


class TestStatefbkIOSGainQA:
    def test_iosystem_gain_controller(self):
        sys = _plant(name="ios_gain")

        def comp_update(t, x, u, params):
            return [-0.5 * x[0] + u[0]]

        def comp_output(t, x, u, params):
            return [-2.0 * u[0] - 0.75 * u[1] + x[0]]

        fbk = ct.nlsys(
            comp_update, comp_output, states=["xc"],
            inputs=["e0", "e1"], outputs=["u"], name="fbk_ios")

        ctrl, closed = ct.create_statefbk_iosystem(
            sys, fbk, controller_type="iosystem", name="ios_ctrl")

        assert ctrl.nstates == 1
        assert closed.nstates >= 3


class TestStatefbkNonlinearPlantQA:
    def test_nonlinear_plant_controller_construction(self):
        def update(t, x, u, params):
            return [x[1], -params["damp"] * x[1] + np.tanh(u[0]) - x[0]]

        def output(t, x, u, params):
            return [x[0], x[1]]

        sys = ct.nlsys(
            update, output, states=["x0", "x1"], inputs=["u"],
            outputs=["x0", "x1"], params={"damp": 0.3}, name="nlplant")
        gain = np.array([[1.4, 0.6]])

        with pytest.warns(UserWarning, match="cannot verify system output"):
            ctrl, closed = ct.create_statefbk_iosystem(
                sys, gain, controller_type="nonlinear",
                params={"damp": 0.3}, name="nlplant_ctrl")

        assert ctrl.noutputs == 1
        assert closed.nstates >= 2
