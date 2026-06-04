import numpy as np
import pybamm


class TestQuickPlotInitCallCoverageQA:
    def _solution(self, seed, end=120):
        model = pybamm.lithium_ion.BaseModel(name=f"qa quick plot model {seed}")
        a = pybamm.Variable("a")
        b = pybamm.Variable("b")
        model.rhs = {a: -a / (seed + 2), b: pybamm.sin(a) - b / (seed + 3)}
        model.initial_conditions = {a: seed / 5 + 1, b: seed / 10}
        model.variables = {
            "a": a,
            "b": b,
            "sum": a + b,
            "energy": a**2 + pybamm.exp(b),
            "cell field": pybamm.FullBroadcast(
                a + b,
                ["negative electrode", "separator", "positive electrode"],
                "current collector",
            ),
            "particle field": pybamm.FullBroadcast(
                a, "negative particle", {"secondary": "negative electrode"}
            ),
        }
        geometry = model.default_geometry
        params = model.default_parameter_values
        params.process_model(model)
        params.process_geometry(geometry)
        mesh = pybamm.Mesh(geometry, model.default_submesh_types, model.default_var_pts)
        pybamm.Discretisation(mesh, model.default_spatial_methods).process_model(model)
        return pybamm.ScipySolver().solve(model, np.linspace(0, end, 7))

    def _plot(self, seed, **kwargs):
        plot = pybamm.QuickPlot(**kwargs)
        assert plot.axis_limits
        assert plot.variables
        return plot

    def test_case_01(self):
        sol = self._solution(1)
        assert self._plot(1, solutions=sol, output_variables=["a", "sum"])

    def test_case_02(self):
        sol = self._solution(2)
        assert self._plot(
            2, solutions=sol, output_variables=[["a", "b"], "energy"], variable_limits="tight"
        )

    def test_case_03(self):
        sol = self._solution(3)
        assert self._plot(3, solutions=sol, output_variables=["cell field"])

    def test_case_04(self):
        sol = self._solution(4)
        assert self._plot(4, solutions=sol, output_variables=["particle field"])

    def test_case_05(self):
        sol = self._solution(5, end=7200)
        assert self._plot(5, solutions=sol, output_variables=["a", "energy"])

    def test_case_06(self):
        sol = self._solution(6)
        assert self._plot(
            6,
            solutions=sol,
            output_variables=["a", ["sum", "energy"], "cell field"],
            time_unit="minutes",
            spatial_unit="mm",
            n_rows=2,
            figsize=(9, 7),
        )

    def test_case_07(self):
        sol = self._solution(7)
        assert self._plot(
            7,
            solutions=sol,
            output_variables=["a", "b"],
            variable_limits={"a": (-1, 3), "b": "tight"},
            colors=["navy", "gold"],
            linestyles=["--", "-."],
        )

    def test_case_08(self):
        first, second = self._solution(8), self._solution(9)
        assert self._plot(
            8,
            solutions=[first, second],
            output_variables=[["a", "b"], "sum"],
            labels=["baseline", "comparison"],
            time_unit="seconds",
        )

    def test_case_09(self):
        sol = self._solution(10)
        sim = pybamm.Simulation(sol.all_models[0])
        sim._solution = sol
        assert self._plot(9, solutions=[sim, sol], output_variables=["energy", "cell field"])

    def test_case_10(self):
        sol = self._solution(11)
        assert self._plot(
            10,
            solutions=sol,
            output_variables=["a", ["sum", "energy"], "cell field", "particle field"],
            variable_limits={("sum", "energy"): (-1, 5), "cell field": "tight"},
            time_unit="hours",
            spatial_unit="m",
            shading="nearest",
            n_t_linear=12,
        )
