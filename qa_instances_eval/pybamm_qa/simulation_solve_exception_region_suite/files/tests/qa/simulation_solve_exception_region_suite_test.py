import pybamm


class TestSimulationSolveExceptionRegionQA:
    def _simulation(self, kind="ode", solver=None):
        model = pybamm.BaseModel(f"qa simulation {kind}")
        x = pybamm.Variable("x")
        if kind == "ode":
            model.rhs = {x: -x}
            model.initial_conditions = {x: pybamm.Scalar(1)}
        elif kind == "algebraic":
            model.algebraic = {x: x - 1}
            model.initial_conditions = {x: pybamm.Scalar(1)}
        elif kind == "input":
            u = pybamm.InputParameter("decay rate")
            model.rhs = {x: -u * x}
            model.initial_conditions = {x: pybamm.Scalar(1)}
        model.variables = {"x": x}
        return pybamm.Simulation(model, solver=solver)

    def _solve(self, simulation, **kwargs):
        solution = simulation.solve(**kwargs)
        assert solution.t.size > 0

    def test_case_01(self):
        self._solve(self._simulation(), t_eval=[0, 1])

    def test_case_02(self):
        self._solve(self._simulation())

    def test_case_03(self):
        self._solve(self._simulation(), t_eval=[0, 1], save_at_cycles=2)

    def test_case_04(self):
        self._solve(self._simulation(), t_eval=[0, 1], starting_solution="invalid")

    def test_case_05(self):
        self._solve(
            self._simulation("input"),
            t_eval=[0, 1],
            inputs={"decay rate": 2},
        )

    def test_case_06(self):
        self._solve(self._simulation("input"), t_eval=[0, 1])

    def test_case_07(self):
        self._solve(self._simulation(), t_eval=[1, 0])

    def test_case_08(self):
        self._solve(
            self._simulation("algebraic", pybamm.AlgebraicSolver()), t_eval=[0, 1]
        )

    def test_case_09(self):
        self._solve(self._simulation("ode", pybamm.AlgebraicSolver()), t_eval=[0, 1])

    def test_case_10(self):
        self._solve(self._simulation("algebraic", pybamm.ScipySolver()), t_eval=[0, 1])
