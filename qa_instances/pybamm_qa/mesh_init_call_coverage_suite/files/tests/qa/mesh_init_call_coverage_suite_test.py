from __future__ import annotations

import pybamm


class TestMeshInitCallCoverageQA:
    def _one_dimensional(self, seed, submesh_type, coord_sys="cartesian"):
        x = pybamm.SpatialVariable(f"qa mesh x {seed}", domain=f"qa domain {seed}", coord_sys=coord_sys)
        geometry = {f"qa domain {seed}": {x: {"min": pybamm.Scalar(seed / 10), "max": pybamm.Scalar(seed / 10 + 1)}}}
        mesh = pybamm.Mesh(geometry, {f"qa domain {seed}": submesh_type}, {x: 6 + seed})
        assert mesh[f"qa domain {seed}"].npts >= 6
        return mesh

    def _multi_domain(self, seed, symbolic=False):
        a = pybamm.SpatialVariable(f"qa a {seed}", domain=f"qa left {seed}", coord_sys="cartesian")
        b = pybamm.SpatialVariable(f"qa b {seed}", domain=f"qa right {seed}", coord_sys="cartesian")
        boundary = pybamm.InputParameter(f"qa length {seed}") if symbolic else pybamm.Scalar(1)
        geometry = {
            f"qa left {seed}": {a: {"min": pybamm.Scalar(0), "max": pybamm.Scalar(1)}},
            f"qa right {seed}": {b: {"min": pybamm.Scalar(1), "max": boundary + 1}},
        }
        typ = pybamm.SymbolicUniform1DSubMesh if symbolic else pybamm.Uniform1DSubMesh
        mesh = pybamm.Mesh(geometry, {f"qa left {seed}": typ, f"qa right {seed}": typ}, {a: 5 + seed, b: 6 + seed})
        assert len(mesh.base_domains) == 2
        return mesh

    def _zero_dimensional(self, seed):
        z = pybamm.SpatialVariable(f"qa z {seed}", domain=f"qa zero {seed}")
        mesh = pybamm.Mesh({f"qa zero {seed}": {z: {"position": pybamm.Scalar(seed)}}}, {f"qa zero {seed}": pybamm.SubMesh0D}, {})
        assert mesh[f"qa zero {seed}"].npts == 1
        return mesh

    def test_case_01(self): assert self._one_dimensional(1, pybamm.Uniform1DSubMesh)
    def test_case_02(self): assert self._one_dimensional(2, pybamm.Chebyshev1DSubMesh)
    def test_case_03(self): assert self._one_dimensional(3, pybamm.Exponential1DSubMesh)
    def test_case_04(self): assert self._one_dimensional(4, pybamm.MeshGenerator(pybamm.Exponential1DSubMesh, {"side": "left", "stretch": 1.8}))
    def test_case_05(self): assert self._one_dimensional(5, pybamm.MeshGenerator(pybamm.Exponential1DSubMesh, {"side": "right", "stretch": 2.7}))
    def test_case_06(self): assert self._one_dimensional(6, pybamm.Uniform1DSubMesh, "spherical polar")
    def test_case_07(self): assert self._multi_domain(7, False)
    def test_case_08(self): assert self._multi_domain(8, True)
    def test_case_09(self): assert self._zero_dimensional(9)
    def test_case_10(self): assert self._one_dimensional(10, pybamm.MeshGenerator(pybamm.Exponential1DSubMesh, {"side": "symmetric", "stretch": 1.4}))
