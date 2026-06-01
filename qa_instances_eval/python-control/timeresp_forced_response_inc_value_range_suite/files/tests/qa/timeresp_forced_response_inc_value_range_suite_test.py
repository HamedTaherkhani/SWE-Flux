import numpy as np

from control.statesp import StateSpace
from control.timeresp import forced_response


def _system(sample_time, pole, feedthrough):
    a = np.array([[pole, 0.05], [0.0, 0.35 * pole]])
    b = np.array([[1.0], [0.25 + 0.1 * pole]])
    c = np.array([[1.0 - 0.2 * pole, 0.4]])
    d = np.array([[feedthrough]])
    return StateSpace(a, b, c, d, dt=sample_time)


def _input_series(length, scale, phase):
    grid = np.arange(length, dtype=float)
    return scale * (1.0 + 0.2 * grid + np.sin(phase + 0.7 * grid))


def _exercise(sample_time, output_step, length, offset, pole, scale, phase):
    sys = _system(sample_time, pole, 0.03 * scale)
    timepts = offset + output_step * np.arange(length, dtype=float)
    inputs = _input_series(length, scale, phase)
    response = forced_response(
        sys, T=timepts, U=inputs, X0=[0.2 * scale, -0.1 * pole],
        squeeze=False,
    )
    assert np.allclose(response.time, timepts)
    assert response.outputs.shape[-1] == length
    assert response.states.shape[-1] == length
    assert np.all(np.isfinite(response.outputs))
    assert np.all(np.isfinite(response.states))
    return response


class TestForcedResponseStateRangeQA:
    def test_case_01(self):
        response = _exercise(0.2, 0.2, 7, 0.0, 0.42, 0.7, 0.10)
        assert response.outputs.shape == (1, 7)

    def test_case_02(self):
        response = _exercise(0.1, 0.3, 6, 0.2, 0.50, -0.4, 0.25)
        assert response.time[0] == 0.2

    def test_case_03(self):
        response = _exercise(0.05, 0.45, 5, 0.45, -0.15, 1.1, 0.40)
        assert response.outputs.size == 5

    def test_case_04(self):
        response = _exercise(True, 0.25, 8, 0.0, 0.33, 0.5, 0.55)
        assert response.states.shape == (2, 8)

    def test_case_05(self):
        response = _exercise(0.125, 0.5, 7, 0.125, 0.62, -0.8, 0.70)
        assert response.time[-1] > response.time[0]

    def test_case_06(self):
        response = _exercise(0.2, 1.0, 4, 0.4, -0.25, 0.9, 0.85)
        assert response.outputs.shape[-1] == 4

    def test_case_07(self):
        response = _exercise(0.15, 0.45, 6, 0.15, 0.28, 1.4, 1.00)
        assert np.max(response.time) > 2.0

    def test_case_08(self):
        response = _exercise(0.08, 0.64, 5, 0.0, 0.58, -1.2, 1.15)
        assert response.states.shape[-1] == 5

    def test_case_09(self):
        response = _exercise(0.25, 0.75, 6, 0.5, -0.45, 0.6, 1.30)
        assert response.time[1] - response.time[0] == 0.75

    def test_case_10(self):
        response = _exercise(0.4, 0.8, 5, 0.8, 0.18, -0.9, 1.45)
        assert response.outputs.shape == (1, 5)
