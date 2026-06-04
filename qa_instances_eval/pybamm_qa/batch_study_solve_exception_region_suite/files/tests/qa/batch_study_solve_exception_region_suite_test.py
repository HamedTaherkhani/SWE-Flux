import numpy as np
import pybamm


class TestBatchStudySolveExceptionRegionQA:
    def _model(self, name, with_input=False):
        model = pybamm.BaseModel(name); a, b = pybamm.Variable("a"), pybamm.Variable("b")
        rate = pybamm.InputParameter("rate") if with_input else pybamm.Scalar(1)
        model.rhs = {a: -rate * a + pybamm.sin(b), b: a - (rate + 1) * b}
        model.initial_conditions = {a: pybamm.Scalar(1), b: pybamm.Scalar(0.25)}
        model.variables = {"a": a, "b": b, "energy": a**2 + b**2, "mixed": pybamm.exp(-a) + pybamm.cos(b)}
        return model
    def _solve(self, study, **kwargs):
        study.solve(**kwargs); assert study.sims
    def test_case_01(self):
        self._solve(pybamm.BatchStudy(models={"alpha": self._model("alpha"), "beta": self._model("beta"), "gamma": self._model("gamma")}), t_eval=np.array([0, 0.2, 0.7, 1.5]))
    def test_case_02(self):
        self._solve(pybamm.BatchStudy(models={"alpha": self._model("alpha"), "beta": self._model("beta")}, solvers={"bdf": pybamm.ScipySolver(method="BDF"), "radau": pybamm.ScipySolver(method="Radau")}, output_variables={"first": ["a", "energy"], "second": ["b", "mixed"]}), t_eval=np.array([0, 0.1, 0.4, 1]))
    def test_case_03(self):
        self._solve(pybamm.BatchStudy(models={"alpha": self._model("alpha"), "beta": self._model("beta")}, solvers={"valid": pybamm.ScipySolver(), "invalid": pybamm.AlgebraicSolver()}), t_eval=[0, 0.5, 1])
    def test_case_04(self):
        self._solve(pybamm.BatchStudy(models={"alpha": self._model("alpha"), "beta": self._model("beta")}))
    def test_case_05(self):
        self._solve(pybamm.BatchStudy(models={"input-alpha": self._model("input-alpha", True), "input-beta": self._model("input-beta", True)}), t_eval=np.array([0, 0.2, 0.8, 1.2]))
    def test_case_06(self):
        self._solve(pybamm.BatchStudy(models={"input-alpha": self._model("input-alpha", True), "input-beta": self._model("input-beta", True)}, solvers={"bdf": pybamm.ScipySolver(), "radau": pybamm.ScipySolver(method="Radau")}), t_eval=np.array([0, 0.2, 0.8, 1.2]), inputs={"rate": 1.75})
    def test_case_07(self):
        self._solve(pybamm.BatchStudy(models={"alpha": self._model("alpha")}, repeats=0), t_eval=[0, 1])
    def test_case_08(self):
        self._solve(pybamm.BatchStudy(models={"alpha": self._model("alpha"), "beta": self._model("beta")}, solvers={"bdf": pybamm.ScipySolver(), "algebraic": pybamm.AlgebraicSolver()}, output_variables={"state": ["a", "b"], "derived": ["energy", "mixed"]}, permutations=True), t_eval=[0, 0.3, 1])
    def test_case_09(self):
        self._solve(pybamm.BatchStudy(models={"alpha": self._model("alpha"), "beta": self._model("beta")}, solvers={"one": pybamm.ScipySolver(), "two": pybamm.ScipySolver(method="RK45")}), t_eval=np.array([1.5, 0.8, 0.1]))
    def test_case_10(self):
        self._solve(pybamm.BatchStudy(models={"alpha": self._model("alpha"), "beta": self._model("beta")}, solvers={"bdf": pybamm.ScipySolver(method="BDF"), "rk": pybamm.ScipySolver(method="RK45")}, repeats=2), t_eval=np.array([0, 0.25, 0.75, 1.5]))
