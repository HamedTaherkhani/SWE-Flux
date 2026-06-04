from __future__ import annotations

import pybamm


class TestParameterValuesProcessBoundaryConditionsDefUseIntersectionQA:
    def _process(self, seed):
        params = pybamm.ParameterValues({
            f"qa p {seed}": seed + 1.0,
            f"qa q {seed}": seed + 2.0,
            f"qa r {seed}": seed + 3.0,
            f"qa s {seed}": seed + 4.0,
        })
        model = pybamm.BaseModel(f"qa bc model {seed}")
        variable = pybamm.Variable(f"qa var {seed}", domain="negative electrode")
        model.rhs = {
            variable: -pybamm.Parameter(f"qa p {seed}") * variable
            + pybamm.Parameter(f"qa q {seed}")
        }
        model.initial_conditions = {variable: pybamm.Parameter(f"qa r {seed}")}
        model.variables = {
            f"qa var {seed}": variable,
            f"qa shifted {seed}": variable + pybamm.Parameter(f"qa s {seed}"),
        }
        model.boundary_conditions = {
            variable: {
                "left": (pybamm.Parameter(f"qa p {seed}") + 1, "Dirichlet"),
                "right": (pybamm.Parameter(f"qa q {seed}") * 2, "Neumann"),
                "x_min": (pybamm.Parameter(f"qa r {seed}") - 1, "Dirichlet"),
                "x_max": (pybamm.Parameter(f"qa s {seed}") / 2, "Neumann"),
            }
        }
        processed = params.process_model(model, inplace=False)
        bcs = next(iter(processed.boundary_conditions.values()))
        assert set(bcs) == {"left", "right", "x_min", "x_max"}
        return bcs

    def test_case_01(self): assert self._process(1)["left"][1] == "Dirichlet"
    def test_case_02(self): assert self._process(2)["right"][1] == "Neumann"
    def test_case_03(self): assert self._process(3)["x_min"][1] == "Dirichlet"
    def test_case_04(self): assert self._process(4)["x_max"][1] == "Neumann"
    def test_case_05(self): assert self._process(5)["left"][1] == "Dirichlet"
    def test_case_06(self): assert self._process(6)["right"][1] == "Neumann"
    def test_case_07(self): assert self._process(7)["x_min"][1] == "Dirichlet"
    def test_case_08(self): assert self._process(8)["x_max"][1] == "Neumann"
    def test_case_09(self): assert self._process(9)["left"][1] == "Dirichlet"
    def test_case_10(self): assert self._process(10)["right"][1] == "Neumann"
