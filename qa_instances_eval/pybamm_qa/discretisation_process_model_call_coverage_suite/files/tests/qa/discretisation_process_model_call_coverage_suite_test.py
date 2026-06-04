from __future__ import annotations

import pybamm


class TestDiscretisationProcessModelCallCoverageQA:
    def _zero_dimensional(self, seed, algebraic, inplace, check_model):
        model = pybamm.BaseModel(f"qa zero model {seed}")
        a = pybamm.Variable(f"qa zero a {seed}", scale=seed + 1, reference=seed / 10)
        model.rhs = {a: -a + pybamm.sin(a) + pybamm.Scalar(seed / 5)}
        model.initial_conditions = {a: pybamm.Scalar(seed / 20)}
        model.variables = {a.name: a, f"qa cos {seed}": pybamm.cos(a)}
        model.events = [pybamm.Event(f"qa event {seed}", pybamm.Scalar(3) - a)]
        if algebraic:
            b = pybamm.Variable(f"qa zero b {seed}")
            model.algebraic = {b: b - a + pybamm.Scalar(seed / 7)}
            model.initial_conditions[b] = pybamm.Scalar(0)
            model.variables[b.name] = b
        disc = pybamm.Discretisation(check_model=check_model)
        result = disc.process_model(model, inplace=inplace)
        assert result.len_rhs == 1 and result.len_alg == int(algebraic)
        return result

    def _spatial(self, seed, inplace, check_model, nonlinear):
        x = pybamm.SpatialVariable(f"qa x {seed}", domain="negative electrode")
        geometry = {"negative electrode": {x: {"min": 0, "max": 1}}}
        mesh = pybamm.Mesh(
            geometry,
            {"negative electrode": pybamm.Uniform1DSubMesh},
            {x: 5 + seed % 3},
        )
        disc = pybamm.Discretisation(
            mesh,
            {"negative electrode": pybamm.FiniteVolume()},
            check_model=check_model,
        )
        model = pybamm.BaseModel(f"qa spatial model {seed}")
        c = pybamm.Variable(f"qa concentration {seed}", domain="negative electrode")
        diffusion = pybamm.div(pybamm.grad(c))
        model.rhs = {c: diffusion + (pybamm.sin(c) if nonlinear else 0)}
        model.initial_conditions = {c: pybamm.Scalar(seed / 50)}
        model.boundary_conditions = {
            c: {
                "left": (pybamm.Scalar(seed / 100), "Dirichlet"),
                "right": (pybamm.Scalar(0), "Neumann"),
            }
        }
        model.variables = {
            c.name: c,
            f"qa average {seed}": pybamm.x_average(c),
            f"qa boundary {seed}": pybamm.boundary_value(c, "right"),
        }
        model.events = [pybamm.Event(f"qa max event {seed}", 4 - pybamm.max(c))]
        result = disc.process_model(model, inplace=inplace)
        assert result.len_rhs == mesh["negative electrode"].npts
        return result

    def test_case_01(self): assert self._zero_dimensional(1, False, False, True).is_discretised
    def test_case_02(self): assert self._zero_dimensional(2, True, False, True).is_discretised
    def test_case_03(self): assert self._spatial(3, False, True, False).is_discretised
    def test_case_04(self): assert self._spatial(4, False, True, True).is_discretised
    def test_case_05(self): assert self._zero_dimensional(5, False, True, False).is_discretised
    def test_case_06(self): assert self._zero_dimensional(6, True, True, False).is_discretised
    def test_case_07(self): assert self._spatial(7, True, False, False).is_discretised
    def test_case_08(self): assert self._spatial(8, True, False, True).is_discretised
    def test_case_09(self): assert self._zero_dimensional(9, True, False, True).is_discretised
    def test_case_10(self): assert self._spatial(10, False, True, True).is_discretised
