from __future__ import annotations

import numpy as np

import control as ct


TIME_SHORT = np.linspace(0.0, 2.0, 7)
TIME_MEDIUM = np.linspace(0.0, 4.0, 9)


def _siso_ss(name="sys", pole=-1.0, gain=1.0, feedthrough=0.0, dt=0):
    return ct.ss(
        [[pole]], [[gain]], [[1.0]], [[feedthrough]],
        name=name, inputs=["u"], outputs=["y"], dt=dt)


class TestStepResponseContinuousSisoQA:
    def test_continuous_siso_state_space(self):
        sys = _siso_ss(name="csiso", pole=-1.5, gain=2.0)
        resp = ct.step_response(sys, TIME_SHORT)

        assert resp.time.shape == TIME_SHORT.shape
        assert resp.outputs.shape == TIME_SHORT.shape
        assert np.isfinite(resp.outputs[-1])


class TestStepResponseContinuousMimoQA:
    def test_continuous_mimo_all_inputs(self):
        sys = ct.ss(
            [[-1.0, 0.25], [-0.1, -2.0]],
            [[1.0, 0.0], [0.5, 1.0]],
            [[1.0, 0.0], [0.0, 1.0]],
            [[0.0, 0.2], [0.1, 0.0]],
            name="cmimo",
            inputs=["u[0]", "u[1]"],
            outputs=["y[0]", "y[1]"],
        )
        resp = ct.step_response(sys, TIME_SHORT)

        assert resp.y.shape == (2, 2, TIME_SHORT.size)
        assert resp.x.shape == (2, 2, TIME_SHORT.size)


class TestStepResponseSelectedChannelsQA:
    def test_selected_input_and_output(self):
        sys = ct.ss(
            np.diag([-0.7, -1.4, -2.1]),
            [[1.0, 0.0], [0.0, 1.0], [0.5, -0.25]],
            [[1.0, 0.0, 0.5], [0.0, 1.0, -1.0]],
            [[0.0, 0.0], [0.2, 0.0]],
            name="selected",
            inputs=["left", "right"],
            outputs=["top", "bottom"],
        )
        resp = ct.step_response(
            sys, TIME_MEDIUM, input_indices=1, output_indices=0,
            return_states=True)

        assert resp.issiso
        assert resp.x.shape == (3, 1, TIME_MEDIUM.size)


class TestStepResponseTransferFunctionQA:
    def test_continuous_transfer_function_conversion(self):
        sys = ct.tf([1.0, 3.0], [1.0, 2.0, 5.0], name="tf_cont")
        resp = ct.step_response(sys, TIME_MEDIUM)

        assert resp.time.size == TIME_MEDIUM.size
        assert np.all(np.isfinite(resp.outputs))


class TestStepResponseDiscreteTransferFunctionQA:
    def test_discrete_transfer_function(self):
        sys = ct.tf([0.25, 0.1], [1.0, -0.4, 0.12], dt=0.5, name="tf_disc")
        timepts = np.arange(0.0, 4.5, 0.5)
        resp = ct.step_response(sys, timepts)

        assert resp.time.shape == timepts.shape
        assert np.all(np.isfinite(resp.outputs))


class TestStepResponseDiscreteStateSpaceQA:
    def test_discrete_state_space_unspecified_dt(self):
        sys = ct.ss(
            [[0.6, 0.2], [0.0, 0.3]],
            [[1.0], [0.5]],
            [[1.0, -1.0]],
            [[0.0]],
            dt=True,
            name="dss_unspecified",
        )
        resp = ct.step_response(sys, np.arange(0, 6))

        assert resp.time.size == 6
        assert resp.x.shape == (2, 1, 6)


class TestStepResponseListInputQA:
    def test_list_of_systems(self):
        systems = [
            _siso_ss(name="fast", pole=-3.0, gain=1.0),
            ct.tf([2.0], [1.0, 4.0], name="tf_fast"),
            _siso_ss(name="slow", pole=-0.4, gain=0.5),
        ]
        resp_list = ct.step_response(systems, TIME_SHORT)

        assert len(resp_list) == 3
        assert all(resp.time.size == TIME_SHORT.size for resp in resp_list)


class TestStepResponseAutomaticTimeVectorQA:
    def test_auto_time_vector_for_stable_system(self):
        sys = ct.tf([5.0], [1.0, 2.0, 5.0], name="auto_time")
        resp = ct.step_response(sys, timepts_num=31)

        assert resp.time.size == 31
        assert np.isfinite(resp.outputs[-1])


class TestStepResponseStaticGainQA:
    def test_static_gain_state_space(self):
        sys = ct.ss([], [], [], [[2.0, -1.0]], inputs=["u0", "u1"], outputs=["y"])
        resp = ct.step_response(sys, TIME_SHORT)

        assert resp.y.shape == (1, 2, TIME_SHORT.size)
        assert np.allclose(resp.y[0, 0, :], 2.0)
        assert np.allclose(resp.y[0, 1, :], -1.0)


class TestStepResponseNonlinearDelegationQA:
    def test_nonlinear_system_delegates_to_input_output_response(self):
        def update(t, x, u, params):
            return [-params["rate"] * x[0] + np.sin(u[0])]

        def output(t, x, u, params):
            return [x[0] + params["offset"]]

        sys = ct.nlsys(
            update, output, states=["x"], inputs=["u"], outputs=["y"],
            params={"rate": 0.8, "offset": 0.15}, name="nl_step")
        resp = ct.step_response(
            sys, TIME_SHORT, params={"rate": 0.8, "offset": 0.15})

        assert resp.time.size == TIME_SHORT.size
        assert resp.y.shape == (1, 1, TIME_SHORT.size)
