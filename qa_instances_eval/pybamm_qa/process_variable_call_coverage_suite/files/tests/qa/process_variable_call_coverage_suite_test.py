from __future__ import annotations

import numpy as np
import pybamm


class TestProcessVariableCallCoverageQA:
    def _scalar_solution(self, seed, expression):
        model = pybamm.BaseModel(f"qa pv zero {seed}")
        v = pybamm.Variable(f"qa pv v {seed}")
        model.rhs = {v: -pybamm.Scalar(seed / 20) * v}
        model.initial_conditions = {v: pybamm.Scalar(1)}
        model.variables = {v.name: v, f"qa output {seed}": expression(v)}
        pybamm.Discretisation().process_model(model)
        return pybamm.ScipySolver().solve(model, np.linspace(0, 1, 5))

    def _spatial_solution(self, seed, edge):
        x = pybamm.SpatialVariable(f"qa pv x {seed}", domain="negative electrode")
        geometry = {"negative electrode": {x: {"min": 0, "max": 1}}}
        mesh = pybamm.Mesh(geometry, {"negative electrode": pybamm.Uniform1DSubMesh}, {x: 5 + seed % 3})
        disc = pybamm.Discretisation(mesh, {"negative electrode": pybamm.FiniteVolume()})
        model = pybamm.BaseModel(f"qa pv spatial {seed}")
        c = pybamm.Variable(f"qa pv c {seed}", domain="negative electrode")
        model.rhs = {c: pybamm.div(pybamm.grad(c))}
        model.initial_conditions = {c: pybamm.Scalar(seed / 20)}
        model.boundary_conditions = {c: {"left": (0, "Neumann"), "right": (0, "Neumann")}}
        model.variables = {c.name: c, f"qa output {seed}": pybamm.grad(c) if edge else c}
        disc.process_model(model)
        return pybamm.ScipySolver().solve(model, np.linspace(0, 0.5, 5))

    def _process(self, seed, kind):
        name = f"qa output {seed}"
        if kind == "scalar":
            solution = self._scalar_solution(seed, lambda v: v)
        elif kind == "function":
            solution = self._scalar_solution(seed, lambda v: pybamm.sin(v) + v**2)
        else:
            solution = self._spatial_solution(seed, kind == "edge")
        processed = solution[name]
        assert processed.entries.size > 0
        return processed

    def test_case_01(self): assert self._process(1, "scalar")
    def test_case_02(self): assert self._process(2, "function")
    def test_case_03(self): assert self._process(3, "node")
    def test_case_04(self): assert self._process(4, "edge")
    def test_case_05(self): assert self._process(5, "scalar")
    def test_case_06(self): assert self._process(6, "node")
    def test_case_07(self): assert self._process(7, "function")
    def test_case_08(self): assert self._process(8, "edge")
    def test_case_09(self): assert self._process(9, "node")
    def test_case_10(self): assert self._process(10, "function")
