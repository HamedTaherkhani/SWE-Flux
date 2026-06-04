import pybamm


class TestMeshInitExceptionDiversityQA:
    def _mesh(self, geometry, submesh_types, var_pts):
        try:
            return pybamm.Mesh(geometry, submesh_types, var_pts)
        except Exception:
            return None

    def _simple(self, maximum=1):
        x = pybamm.SpatialVariable("qa x", domain="negative electrode")
        geometry = {"negative electrode": {x: {"min": 0, "max": maximum}}}
        types = {"negative electrode": pybamm.Uniform1DSubMesh}
        return x, geometry, types

    def test_case_01(self):
        x, geometry, types = self._simple()
        self._mesh(geometry, types, {x: 8})

    def test_case_02(self):
        _, geometry, types = self._simple()
        self._mesh(geometry, types, {})

    def test_case_03(self):
        x, geometry, types = self._simple()
        geometry["negative electrode"].update({"a": {}, "b": {}, "c": {}})
        self._mesh(geometry, types, {x: 8})

    def test_case_04(self):
        _, geometry, types = self._simple()
        geometry["negative electrode"] = {"primary": {"min": 0, "max": 1}}
        self._mesh(geometry, types, {})

    def test_case_05(self):
        x, geometry, types = self._simple(pybamm.Parameter("qa length"))
        self._mesh(geometry, types, {x: 8})

    def test_case_06(self):
        x, geometry, types = self._simple(pybamm.Variable("qa unknown limit"))
        self._mesh(geometry, types, {x: 8})

    def test_case_07(self):
        _, geometry, types = self._simple()
        geometry["negative electrode"] = {"not_a_spatial_variable": {"min": 0, "max": 1}}
        self._mesh(geometry, types, {})

    def test_case_08(self):
        x, geometry, _ = self._simple()
        self._mesh(geometry, {}, {x: 8})

    def test_case_09(self):
        z = pybamm.SpatialVariable("qa z", domain="current collector")
        geometry = {"current collector": {"z": {"position": 0.5}}}
        self._mesh(geometry, {"current collector": pybamm.SubMesh0D}, {z: 1})

    def test_case_10(self):
        x, geometry, types = self._simple(pybamm.InputParameter("qa input length"))
        self._mesh(geometry, types, {x: 6})
