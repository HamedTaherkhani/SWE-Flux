from __future__ import annotations

import pybamm


class TestSimulationBuildCallCoverageQA:
    def _zero(self, seed, parameterized, already_discretised):
        model = pybamm.BaseModel(f"qa simulation zero {seed}")
        v = pybamm.Variable(f"qa sim v {seed}")
        rate = pybamm.Parameter(f"qa rate {seed}") if parameterized else pybamm.Scalar(seed / 20)
        model.rhs = {v: -rate * v + pybamm.sin(v) / (seed + 10)}
        model.initial_conditions = {v: pybamm.Scalar(1)}
        model.variables = {v.name: v, f"qa square {seed}": v**2}
        params = pybamm.ParameterValues({f"qa rate {seed}": seed / 10}) if parameterized else pybamm.ParameterValues({})
        if already_discretised:
            pybamm.Discretisation().process_model(model)
        sim = pybamm.Simulation(model, parameter_values=params, solver=pybamm.ScipySolver())
        sim.build()
        assert sim.built_model.is_discretised
        return sim

    def _spatial(self, seed, nonlinear):
        x = pybamm.SpatialVariable(f"qa sim x {seed}", domain="negative electrode")
        geometry = {"negative electrode": {x: {"min": pybamm.Scalar(0), "max": pybamm.Parameter(f"qa length {seed}")}}}
        model = pybamm.BaseModel(f"qa simulation spatial {seed}")
        c = pybamm.Variable(f"qa sim c {seed}", domain="negative electrode")
        model.rhs = {c: pybamm.div(pybamm.grad(c)) + (pybamm.sin(c) if nonlinear else 0)}
        model.initial_conditions = {c: pybamm.Scalar(seed / 50)}
        model.boundary_conditions = {c: {"left": (0, "Neumann"), "right": (0, "Neumann")}}
        model.variables = {c.name: c, f"qa avg {seed}": pybamm.x_average(c)}
        sim = pybamm.Simulation(
            model,
            geometry=geometry,
            parameter_values=pybamm.ParameterValues({f"qa length {seed}": 1 + seed / 20}),
            submesh_types={"negative electrode": pybamm.Uniform1DSubMesh},
            var_pts={x: 5 + seed % 3},
            spatial_methods={"negative electrode": pybamm.FiniteVolume()},
            solver=pybamm.ScipySolver(),
        )
        sim.build()
        assert sim.built_model.len_rhs > 1
        return sim

    def test_case_01(self): assert self._zero(1, False, False).built_model
    def test_case_02(self): assert self._zero(2, True, False).built_model
    def test_case_03(self): assert self._zero(3, False, True).built_model
    def test_case_04(self): assert self._spatial(4, False).built_model
    def test_case_05(self): assert self._spatial(5, True).built_model
    def test_case_06(self): assert self._zero(6, True, False).built_model
    def test_case_07(self): assert self._zero(7, False, True).built_model
    def test_case_08(self): assert self._spatial(8, True).built_model
    def test_case_09(self): assert self._spatial(9, False).built_model
    def test_case_10(self): assert self._zero(10, True, False).built_model
