from __future__ import annotations

import numpy as np
import pybamm


class TestParameterValuesProcessModelCallCoverageQA:
    def _make_model(self, seed, mode):
        params = pybamm.ParameterValues(
            {
                f"qa p {seed}": seed + 1.0,
                f"qa q {seed}": seed + 2.0,
                f"qa r {seed}": seed + 3.0,
                f"qa f {seed}": lambda x: x**2 + pybamm.Scalar(seed / 2),
            }
        )
        model = pybamm.BaseModel(f"qa process model {seed}")
        a = pybamm.Variable(
            f"qa a {seed}",
            scale=pybamm.Parameter(f"qa p {seed}"),
            reference=pybamm.Parameter(f"qa q {seed}"),
        )
        b = pybamm.Variable(f"qa b {seed}")
        function_param = pybamm.FunctionParameter(f"qa f {seed}", {"x": a})
        x = np.linspace(0, 3, 4)
        y = np.sin(x + seed / 10) + seed
        interpolant = pybamm.Interpolant(
            x, y, [a], extrapolate=False, name=f"qa interpolant {seed}"
        )
        model.rhs = {
            a: -pybamm.Parameter(f"qa p {seed}") * a
            + function_param
            + interpolant
        }
        if mode in {"algebraic", "full"}:
            model.algebraic = {
                b: b - pybamm.Parameter(f"qa q {seed}") + pybamm.sin(a)
            }
            model.initial_conditions[b] = pybamm.Scalar(seed / 4)

        model.initial_conditions[a] = pybamm.Parameter(f"qa r {seed}")
        model.variables = {
            a.name: a,
            f"qa combo {seed}": pybamm.maximum(a, pybamm.Parameter(f"qa q {seed}"))
            + interpolant,
            f"qa rate {seed}": function_param - pybamm.cos(a),
        }
        model.events = [
            pybamm.Event(
                f"qa lower event {seed}", pybamm.Parameter(f"qa r {seed}") - a
            )
        ]
        if mode in {"boundary", "full"}:
            model.boundary_conditions = {
                a: {
                    "left": (pybamm.Parameter(f"qa p {seed}"), "Dirichlet"),
                    "right": (pybamm.Parameter(f"qa q {seed}"), "Neumann"),
                }
            }
        return params, model

    def _process(self, seed, mode, inplace):
        params, model = self._make_model(seed, mode)
        processed = params.process_model(model, inplace=inplace)
        assert len(processed.rhs) == 1
        assert len(processed.variables) == 3
        assert len(processed.events) == 3
        if mode in {"algebraic", "full"}:
            assert len(processed.algebraic) == 1
        if mode in {"boundary", "full"}:
            assert len(processed.boundary_conditions) == 1
        return processed

    def test_case_01(self): assert self._process(1, "base", False).name
    def test_case_02(self): assert self._process(2, "algebraic", False).name
    def test_case_03(self): assert self._process(3, "boundary", False).name
    def test_case_04(self): assert self._process(4, "full", False).name
    def test_case_05(self): assert self._process(5, "base", True).name
    def test_case_06(self): assert self._process(6, "algebraic", True).name
    def test_case_07(self): assert self._process(7, "boundary", True).name
    def test_case_08(self): assert self._process(8, "full", True).name
    def test_case_09(self): assert self._process(9, "boundary", False).name
    def test_case_10(self): assert self._process(10, "full", True).name
