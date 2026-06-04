import pybamm


class TestDiscretisationProcessModelExceptionRegionQA:
    def _process(self, model, disc):
        result = disc.process_model(model)
        assert result.concatenated_initial_conditions is not None

    def _spatial_setup(self):
        x = pybamm.SpatialVariable("x", domain="negative electrode")
        geometry = {"negative electrode": {x: {"min": 0, "max": 1}}}
        mesh = pybamm.Mesh(
            geometry, {"negative electrode": pybamm.Uniform1DSubMesh}, {x: 8}
        )
        model = pybamm.BaseModel()
        c = pybamm.Variable("c", domain="negative electrode")
        model.rhs = {c: pybamm.div(pybamm.grad(c))}
        model.initial_conditions = {c: pybamm.Scalar(1)}
        model.boundary_conditions = {
            c: {"left": (0, "Neumann"), "right": (0, "Neumann")}
        }
        return model, mesh

    def test_case_01(self):
        model = pybamm.BaseModel()
        c = pybamm.Variable("c")
        model.rhs = {c: -c}
        model.initial_conditions = {c: pybamm.Scalar(1)}
        model.variables = {"c": c}
        self._process(model, pybamm.Discretisation())

    def test_case_02(self):
        model = pybamm.BaseModel()
        c = pybamm.Variable("c")
        model.rhs = {c: -c}
        model.variables = {"c": c}
        self._process(model, pybamm.Discretisation())

    def test_case_03(self):
        model = pybamm.BaseModel()
        c = pybamm.Variable("c", bounds=(0, 2))
        model.rhs = {c: 1 - c}
        model.initial_conditions = {c: pybamm.Scalar(1)}
        self._process(model, pybamm.Discretisation())

    def test_case_04(self):
        model = pybamm.BaseModel()
        c = pybamm.Variable("c", bounds=(0, 2))
        model.rhs = {c: 1 - c}
        model.initial_conditions = {c: pybamm.Scalar(3)}
        self._process(model, pybamm.Discretisation())

    def test_case_05(self):
        model = pybamm.BaseModel()
        c, d = pybamm.Variable("c"), pybamm.Variable("d")
        model.rhs = {c: -c + d}
        model.algebraic = {d: d - c}
        model.initial_conditions = {c: pybamm.Scalar(1), d: pybamm.Scalar(1)}
        self._process(model, pybamm.Discretisation())

    def test_case_06(self):
        model = pybamm.BaseModel()
        c = pybamm.Variable("c")
        model.rhs = {c: pybamm.Vector([1, 1])}
        model.initial_conditions = {c: pybamm.Vector([1, 1, 1])}
        self._process(model, pybamm.Discretisation())

    def test_case_07(self):
        self._process(pybamm.BaseModel(), pybamm.Discretisation())

    def test_case_08(self):
        model, mesh = self._spatial_setup()
        self._process(
            model,
            pybamm.Discretisation(
                mesh, {"negative electrode": pybamm.FiniteVolume()}
            ),
        )

    def test_case_09(self):
        model, mesh = self._spatial_setup()
        self._process(model, pybamm.Discretisation(mesh, {}))

    def test_case_10(self):
        model, mesh = self._spatial_setup()
        c = next(iter(model.rhs))
        model.boundary_conditions = {
            c: {"left": (0, "Neumann"), "middle": (0, "Neumann")}
        }
        self._process(
            model,
            pybamm.Discretisation(
                mesh, {"negative electrode": pybamm.FiniteVolume()}
            ),
        )
