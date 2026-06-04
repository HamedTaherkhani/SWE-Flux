import pybamm


class TestBaseModelExportCasadiExceptionRegionQA:
    def _model(self, kind="ode"):
        model = pybamm.BaseModel(f"qa casadi export {kind}"); a, b = pybamm.Variable("a"), pybamm.Variable("b")
        if kind == "input":
            p, q = pybamm.InputParameter("p"), pybamm.InputParameter("q"); model.rhs = {a: -p * a + q * b, b: a - (p + q) * b}
        elif kind == "dae":
            model.rhs = {a: -a + b}; model.algebraic = {b: b - pybamm.sin(a)}
        elif kind == "spatial":
            a = pybamm.Variable("a", domain="negative electrode"); model.rhs = {a: -a}; model.initial_conditions = {a: 1}; model.variables = {"a": a}; return model
        else:
            model.rhs = {a: -a + pybamm.sin(b), b: a - 2 * b}
        model.initial_conditions = {a: pybamm.Scalar(1), b: pybamm.Scalar(0.2)}
        model.variables = {"a": a, "b": b, "energy": a**2 + b**2, "mixed": pybamm.exp(-a) + pybamm.cos(b)}
        return model
    def _export(self, model, variables, order=None):
        result = model.export_casadi_objects(variables, order); assert set(result["variables"]) == set(variables)
    def test_case_01(self): self._export(self._model(), ["a", "energy", "mixed"])
    def test_case_02(self): self._export(self._model("input"), ["a", "b", "energy"], ["p", "q"])
    def test_case_03(self): self._export(self._model("input"), ["a", "mixed"])
    def test_case_04(self): self._export(self._model("input"), ["energy", "mixed"], ["p", "missing", "q"])
    def test_case_05(self): self._export(self._model(), ["a", "missing diagnostic", "mixed"])
    def test_case_06(self): self._export(self._model("dae"), ["a", "b", "energy"])
    def test_case_07(self): self._export(self._model("spatial"), ["a"])
    def test_case_08(self): self._export(self._model(), ["a", "b", "energy", "mixed"], [])
    def test_case_09(self): self._export(self._model("input"), ["mixed", "energy", "a"], ["q", "p"])
    def test_case_10(self): self._export(self._model("dae"), ["missing", "a"], [])
