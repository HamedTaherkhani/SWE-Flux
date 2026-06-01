from __future__ import annotations

import numpy as np
import pytest
import scipy as sp

from control.nlsys import nlsys
from control.optimal import (
    input_poly_constraint,
    input_range_constraint,
    output_range_constraint,
    quadratic_cost,
    solve_optimal_trajectory,
    state_poly_constraint,
    state_range_constraint,
)
from control.statesp import ss


def _discrete_double_integrator(name="dint"):
    return ss(
        [[1.0, 1.0], [0.0, 1.0]],
        [[0.5], [1.0]],
        np.eye(2),
        [[0.0], [0.0]],
        dt=1,
        name=name,
        inputs=["u"],
        outputs=["x0", "x1"],
        states=["x0", "x1"],
    )


def _continuous_oscillator(name="osc"):
    return ss(
        [[0.0, 1.0], [-1.0, -0.2]],
        [[0.0], [1.0]],
        np.eye(2),
        [[0.0], [0.0]],
        name=name,
        inputs=["u"],
        outputs=["x0", "x1"],
        states=["x0", "x1"],
    )


def _fast_options(maxiter=2):
    return {"maxiter": maxiter, "disp": False}


class TestOptimalDiscreteUnconstrainedQA:
    def test_discrete_unconstrained_quadratic(self):
        sys = _discrete_double_integrator()
        timepts = np.arange(0, 4)
        cost = quadratic_cost(sys, np.eye(2), np.eye(1))

        res = solve_optimal_trajectory(
            sys, timepts, initial_state=[1.0, -0.5], integral_cost=cost,
            trajectory_method="shooting", print_summary=False,
            minimize_method="SLSQP", minimize_options=_fast_options(8),
        )

        assert res.time.shape == timepts.shape
        assert res.inputs.shape[-1] == timepts.size


class TestOptimalDiscreteInputRangeQA:
    def test_discrete_input_range_constraint(self):
        sys = _discrete_double_integrator("input_range")
        timepts = np.arange(0, 5)
        cost = quadratic_cost(sys, np.diag([1.0, 0.5]), [[0.2]])
        constraints = [input_range_constraint(sys, [-0.4], [0.6])]

        res = solve_optimal_trajectory(
            sys, timepts, [2.0, 0.0], cost, constraints,
            trajectory_method="shooting", print_summary=False,
            minimize_method="SLSQP", minimize_options=_fast_options(),
        )

        assert res.states.shape[0] == 2
        assert np.isfinite(res.cost)


class TestOptimalDiscreteStatePolyQA:
    def test_discrete_state_poly_constraint(self):
        sys = _discrete_double_integrator("state_poly")
        timepts = np.arange(0, 4)
        cost = quadratic_cost(sys, np.eye(2), [[0.1]])
        constraints = [
            state_poly_constraint(sys, [[1.0, 0.0], [-1.0, 0.0]], [3.0, 3.0]),
        ]

        res = solve_optimal_trajectory(
            sys, timepts, [1.0, 0.5], cost,
            trajectory_constraints=constraints, trajectory_method="shooting",
            print_summary=False, minimize_method="SLSQP",
            minimize_options=_fast_options(),
        )

        assert len(res.time) == 4
        assert res.states.shape[1] == 4


class TestOptimalDiscreteEqConstraintQA:
    def test_discrete_equality_constraint_path(self):
        sys = _discrete_double_integrator("eq_state")
        timepts = np.arange(0, 3)
        cost = quadratic_cost(sys, np.eye(2), np.eye(1))
        constraints = [state_range_constraint(sys, [0.0, -10.0], [0.0, 10.0])]

        res = solve_optimal_trajectory(
            sys, timepts, [0.0, 0.2], cost, constraints,
            trajectory_method="shooting", print_summary=False,
            minimize_method="SLSQP", minimize_options=_fast_options(),
        )

        assert res.inputs.shape[-1] == timepts.size
        assert np.isfinite(res.cost)


class TestOptimalDiscreteOutputConstraintQA:
    def test_discrete_output_range_constraint(self):
        sys = _discrete_double_integrator("output_range")
        timepts = np.arange(0, 4)
        cost = quadratic_cost(sys, np.eye(2), [[0.3]])
        constraints = [output_range_constraint(sys, [-4.0, -4.0], [4.0, 4.0])]

        res = solve_optimal_trajectory(
            sys, timepts, [1.5, -0.1], cost,
            trajectory_constraints=constraints, trajectory_method="shooting",
            print_summary=False, minimize_method="SLSQP",
            minimize_options=_fast_options(),
        )

        assert res.states.shape[0] == 2
        assert np.isfinite(res.cost)


class TestOptimalTerminalCostAndConstraintQA:
    def test_terminal_cost_and_terminal_constraint(self):
        sys = _discrete_double_integrator("terminal")
        timepts = np.arange(0, 4)
        running_cost = quadratic_cost(sys, 0.2 * np.eye(2), [[0.1]])
        terminal_cost = quadratic_cost(sys, 2.0 * np.eye(2), None)
        terminal_constraints = [
            state_poly_constraint(sys, [[1.0, 1.0], [-1.0, 0.0]], [5.0, 5.0]),
        ]

        res = solve_optimal_trajectory(
            sys, timepts, [2.0, -1.0], running_cost,
            terminal_cost=terminal_cost,
            terminal_constraints=terminal_constraints,
            trajectory_method="shooting", print_summary=False,
            minimize_method="SLSQP", minimize_options=_fast_options(),
        )

        assert res.time[-1] == timepts[-1]
        assert np.isfinite(res.cost)


class TestOptimalContinuousShootingQA:
    def test_continuous_shooting_simulation_path(self):
        sys = _continuous_oscillator("cont_shoot")
        timepts = np.linspace(0.0, 0.6, 4)
        cost = quadratic_cost(sys, np.eye(2), [[0.25]])

        res = solve_optimal_trajectory(
            sys, timepts, [0.5, 0.0], cost,
            trajectory_method="shooting", print_summary=False,
            minimize_method="SLSQP", minimize_options=_fast_options(),
        )

        assert res.time.size == 4
        assert res.states.shape[0] == 2


class TestOptimalContinuousCollocationQA:
    def test_continuous_collocation_constraint_path(self):
        sys = _continuous_oscillator("cont_colloc")
        timepts = np.linspace(0.0, 0.4, 3)
        cost = quadratic_cost(sys, np.eye(2), [[0.5]])
        initial_guess = (np.zeros((2, timepts.size)), np.zeros((1, timepts.size)))

        res = solve_optimal_trajectory(
            sys, timepts, [0.25, -0.1], cost,
            trajectory_method="collocation", initial_guess=initial_guess,
            print_summary=False, minimize_method="SLSQP",
            minimize_options=_fast_options(),
        )

        assert res.inputs.shape[-1] == timepts.size
        assert res.states.shape[1] == timepts.size


class TestOptimalAliasKeywordsQA:
    def test_alias_keywords_and_return_without_states(self):
        sys = _discrete_double_integrator("aliases")
        timepts = np.arange(0, 3)
        cost = quadratic_cost(sys, np.eye(2), np.eye(1))

        res = solve_optimal_trajectory(
            sys, timepts, X0=[0.5, 0.25], cost=cost,
            constraints=[input_poly_constraint(sys, [[1.0], [-1.0]], [1.0, 1.0])],
            return_x=False, trajectory_method="shooting",
            print_summary=False, minimize_method="SLSQP",
            minimize_options=_fast_options(),
        )

        assert res.time.size == 3
        assert res.inputs.shape[-1] == 3


class TestOptimalNonlinearSystemQA:
    def test_nonlinear_discrete_system_path(self):
        def update(t, x, u, params):
            return [x[0] + params["dt"] * (np.tanh(u[0]) - 0.2 * x[0])]

        def output(t, x, u, params):
            return [x[0]]

        sys = nlsys(
            update, output, states=["x"], inputs=["u"], outputs=["y"],
            dt=1, params={"dt": 0.5}, name="nl_opt")

        def cost(x, u):
            return float(x[0] ** 2 + 0.1 * u[0] ** 2)

        def nonlinear_constraint(x, u):
            return np.array([x[0] + u[0]])

        constraints = [
            (sp.optimize.NonlinearConstraint, nonlinear_constraint, [-2.0], [2.0])
        ]
        res = solve_optimal_trajectory(
            sys, np.arange(0, 4), initial_state=[0.4], integral_cost=cost,
            trajectory_constraints=constraints, trajectory_method="shooting",
            print_summary=False, minimize_method="SLSQP",
            minimize_options=_fast_options(),
        )

        assert res.time.size == 4
        assert np.isfinite(res.cost)
