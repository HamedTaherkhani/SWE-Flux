from __future__ import annotations

import numpy as np
import pybamm


class TestBaseSolverSolveCallCoverageQA:
    def _model(self, seed, with_event=False, with_input=False, second_state=False):
        model = pybamm.BaseModel(f"qa solve model {seed}")
        v = pybamm.Variable(f"qa solve v {seed}")
        rate = pybamm.InputParameter(f"qa rate {seed}") if with_input else pybamm.Scalar(0.15 + seed / 100)
        model.rhs = {v: -rate * v + pybamm.sin(v) / (seed + 20)}
        model.initial_conditions = {v: pybamm.Scalar(1)}
        model.variables = {v.name: v, f"qa energy {seed}": v**2}
        if second_state:
            u = pybamm.Variable(f"qa solve u {seed}")
            model.rhs[u] = v - pybamm.Scalar(0.2) * u
            model.initial_conditions[u] = pybamm.Scalar(seed / 20)
            model.variables[u.name] = u
        if with_event:
            model.events = [pybamm.Event(f"qa cutoff {seed}", v - pybamm.Scalar(0.55))]
        pybamm.Discretisation().process_model(model)
        return model

    def _solve(self, seed, solver, t_eval, event=False, input_value=None, second=False):
        model = self._model(seed, event, input_value is not None, second)
        inputs = {f"qa rate {seed}": input_value} if input_value is not None else None
        solution = solver.solve(model, t_eval=t_eval, inputs=inputs)
        assert len(solution.t) >= 2
        return solution

    def test_case_01(self): assert self._solve(1, pybamm.ScipySolver(method="RK45"), [0, 1]).termination == "final time"
    def test_case_02(self): assert self._solve(2, pybamm.ScipySolver(method="BDF"), np.linspace(0, 8, 30), True).termination.startswith("event")
    def test_case_03(self): assert self._solve(3, pybamm.ScipySolver(method="Radau"), np.linspace(0, 2, 15), False, None, True).termination == "final time"
    def test_case_04(self): assert self._solve(4, pybamm.ScipySolver(method="DOP853"), [0, 3], False, 0.3).termination == "final time"
    def test_case_05(self): assert self._solve(5, pybamm.CasadiSolver(mode="fast"), np.linspace(0, 1, 8)).termination == "final time"
    def test_case_06(self): assert self._solve(6, pybamm.CasadiSolver(mode="safe"), np.linspace(0, 2, 12), False, 0.25).termination == "final time"
    def test_case_07(self): assert self._solve(7, pybamm.ScipySolver(method="LSODA"), np.linspace(0, 4, 20), False, None, True).termination == "final time"
    def test_case_08(self): assert self._solve(8, pybamm.CasadiSolver(mode="fast with events"), np.linspace(0, 8, 25), True).termination.startswith("event")
    def test_case_09(self): assert self._solve(9, pybamm.ScipySolver(method="RK23"), np.linspace(0, 2, 11), False, 0.4, True).termination == "final time"
    def test_case_10(self): assert self._solve(10, pybamm.CasadiSolver(mode="safe"), [0, 2], False, None, True).termination == "final time"
