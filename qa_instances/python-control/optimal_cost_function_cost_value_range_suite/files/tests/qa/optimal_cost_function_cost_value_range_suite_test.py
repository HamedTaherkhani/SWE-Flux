import numpy as np

from control.optimal import OptimalControlProblem, quadratic_cost
from control.statesp import ss


def _discrete_system(scale):
    return ss(
        [[1.0, scale], [0.0, 0.75]],
        [[0.5 * scale], [1.0]],
        np.eye(2),
        [[0.0], [0.0]],
        dt=1.0,
        inputs=["u"],
        outputs=["x0", "x1"],
        states=["x0", "x1"],
    )


def _continuous_system(damping):
    return ss(
        [[0.0, 1.0], [-1.4, -damping]],
        [[0.0], [1.0]],
        np.eye(2),
        [[0.0], [0.0]],
        inputs=["u"],
        outputs=["x0", "x1"],
        states=["x0", "x1"],
    )


def _make_problem(sys, timepts, x0, qscale, rscale, method):
    cost = quadratic_cost(sys, qscale * np.diag([1.0, 0.35]), [[rscale]])
    problem = OptimalControlProblem(
        sys, timepts, cost, initial_guess=np.zeros((1, len(timepts))),
        trajectory_method=method, minimize_method="SLSQP",
        minimize_options={"maxiter": 1, "disp": False},
        _kwargs_check=False,
    )
    problem.x = np.asarray(x0, dtype=float)
    return problem


def _run_discrete(scale, timepts, x0, inputs, qscale, rscale):
    problem = _make_problem(
        _discrete_system(scale), np.asarray(timepts, dtype=float),
        x0, qscale, rscale, "shooting")
    value = problem._cost_function(np.asarray(inputs, dtype=float).reshape(-1))
    assert np.isfinite(value)
    assert problem.cost_evaluations == 1
    return value


def _run_continuous(damping, timepts, x0, inputs, qscale, rscale):
    problem = _make_problem(
        _continuous_system(damping), np.asarray(timepts, dtype=float),
        x0, qscale, rscale, "collocation")
    states = np.vstack([
        np.linspace(x0[0], x0[0] + 0.15 * len(timepts), len(timepts)),
        np.linspace(x0[1], x0[1] - 0.08 * len(timepts), len(timepts)),
    ])
    coeffs = np.hstack([
        np.asarray(inputs, dtype=float).reshape(-1),
        states.reshape(-1),
    ])
    value = problem._cost_function(coeffs)
    assert np.isfinite(value)
    assert problem.cost_evaluations == 1
    return value


class TestOptimalCostStateRangeQA:
    def test_case_01(self):
        value = _run_discrete(
            1.0, [0, 1, 2, 3], [1.0, -0.25],
            [0.2, -0.1, 0.05, 0.0], 1.0, 0.25)
        assert value >= 0

    def test_case_02(self):
        value = _run_discrete(
            0.6, [0, 1, 2, 3, 4], [-0.8, 0.5],
            [-0.3, 0.15, 0.4, -0.2, 0.1], 0.7, 0.4)
        assert value >= 0

    def test_case_03(self):
        value = _run_continuous(
            0.2, np.linspace(0.0, 0.6, 4), [0.35, -0.1],
            [0.05, 0.15, -0.05, 0.1], 1.2, 0.3)
        assert value >= 0

    def test_case_04(self):
        value = _run_discrete(
            1.4, [0, 1, 2], [1.8, -0.9],
            [0.6, -0.4, 0.2], 1.5, 0.2)
        assert value >= 0

    def test_case_05(self):
        value = _run_continuous(
            0.45, np.linspace(0.0, 0.8, 5), [-0.2, 0.6],
            [-0.2, -0.1, 0.0, 0.1, 0.2], 0.9, 0.7)
        assert value >= 0

    def test_case_06(self):
        value = _run_discrete(
            0.8, [0, 1, 2, 3, 4, 5], [0.25, 0.75],
            [0.0, 0.1, 0.2, 0.1, -0.1, -0.2], 0.45, 0.15)
        assert value >= 0

    def test_case_07(self):
        value = _run_continuous(
            0.65, np.linspace(0.0, 1.0, 6), [1.1, -0.4],
            [0.3, 0.1, -0.1, -0.2, 0.0, 0.2], 1.1, 0.45)
        assert value >= 0

    def test_case_08(self):
        value = _run_discrete(
            1.2, [0, 1, 2, 3], [-1.3, -0.6],
            [-0.5, -0.25, 0.25, 0.5], 1.8, 0.55)
        assert value >= 0

    def test_case_09(self):
        value = _run_continuous(
            0.35, np.linspace(0.0, 0.5, 3), [0.05, 0.2],
            [0.0, -0.05, 0.05], 0.6, 0.25)
        assert value >= 0

    def test_case_10(self):
        value = _run_discrete(
            0.5, [0, 1, 2, 3, 4], [2.0, 0.25],
            [0.4, 0.2, 0.0, -0.2, -0.4], 1.3, 0.35)
        assert value >= 0
