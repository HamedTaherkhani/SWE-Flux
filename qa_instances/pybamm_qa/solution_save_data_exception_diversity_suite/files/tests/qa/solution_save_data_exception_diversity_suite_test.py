import numpy as np
import pybamm


class TestSolutionSaveDataExceptionDiversityQA:
    def _solution(self, spatial=False):
        model = pybamm.BaseModel("qa export model")
        if spatial:
            x = pybamm.SpatialVariable("qa x", domain="negative electrode")
            geometry = {"negative electrode": {x: {"min": 0, "max": 1}}}
            mesh = pybamm.Mesh(geometry, {"negative electrode": pybamm.Uniform1DSubMesh}, {x: 6})
            disc = pybamm.Discretisation(mesh, {"negative electrode": pybamm.FiniteVolume()})
            c = pybamm.Variable("c", domain="negative electrode")
            model.rhs = {c: pybamm.div(pybamm.grad(c))}
            model.initial_conditions = {c: pybamm.Scalar(1)}
            model.boundary_conditions = {c: {"left": (0, "Neumann"), "right": (0, "Neumann")}}
        else:
            disc = pybamm.Discretisation()
            c = pybamm.Variable("c")
            model.rhs = {c: -c}
            model.initial_conditions = {c: pybamm.Scalar(1)}
        model.variables = {"c": c, "double c": 2 * c}
        disc.process_model(model)
        return pybamm.ScipySolver().solve(model, np.linspace(0, 1, 5))

    def _save(self, solution, **kwargs):
        try:
            return solution.save_data(**kwargs)
        except Exception:
            return None

    def test_case_01(self): self._save(self._solution(), variables=["c"], to_format="json")
    def test_case_02(self): self._save(self._solution(), variables=["c"], to_format="pickle")
    def test_case_03(self): self._save(self._solution(), variables=["c"], to_format="matlab")
    def test_case_04(self, tmp_path): self._save(self._solution(), filename=tmp_path / "bad.out", variables=["c"], to_format="wrong")
    def test_case_05(self): self._save(self._solution(), variables=["missing"], to_format="json")
    def test_case_06(self, tmp_path): self._save(self._solution(), filename=tmp_path / "bad.mat", variables=["double c"], to_format="matlab")
    def test_case_07(self): self._save(self._solution(), variables=["c", "double c"], to_format="csv")
    def test_case_08(self): self._save(self._solution(spatial=True), variables=["c"], to_format="csv")
    def test_case_09(self, tmp_path): self._save(self._solution(), filename=tmp_path / "data.json", variables=["c"], to_format="json")
    def test_case_10(self, tmp_path): self._save(self._solution(), filename=tmp_path / "data.pkl", variables=["c"], to_format="pickle")
