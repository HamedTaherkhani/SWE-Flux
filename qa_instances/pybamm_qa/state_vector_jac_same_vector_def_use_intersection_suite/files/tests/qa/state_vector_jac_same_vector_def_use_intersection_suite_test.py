from __future__ import annotations

import pybamm


class TestStateVectorJacSameVectorDefUseIntersectionQA:
    def _jacobian(self, y_slices, variable_slice, expected_rows):
        symbol = pybamm.StateVector(*y_slices)
        variable = pybamm.StateVector(variable_slice)
        jacobian = symbol.jac(variable)
        assert jacobian.entries.shape == (
            expected_rows,
            variable_slice.stop - variable_slice.start,
        )
        return jacobian

    def test_case_01(self):
        assert self._jacobian((slice(0, 3), slice(5, 8)), slice(1, 7), 6).entries.nnz == 4

    def test_case_02(self):
        assert self._jacobian((slice(2, 6), slice(9, 12)), slice(0, 10), 7).entries.nnz == 5

    def test_case_03(self):
        assert self._jacobian((slice(4, 7), slice(7, 11)), slice(5, 13), 7).entries.nnz == 6

    def test_case_04(self):
        assert self._jacobian((slice(1, 2), slice(3, 6), slice(8, 10)), slice(0, 9), 6).entries.nnz == 5

    def test_case_05(self):
        assert self._jacobian((slice(0, 2), slice(4, 9)), slice(3, 8), 7).entries.nnz == 4

    def test_case_06(self):
        assert self._jacobian((slice(6, 9), slice(10, 14)), slice(7, 12), 7).entries.nnz == 4

    def test_case_07(self):
        assert self._jacobian((slice(2, 5), slice(12, 15)), slice(0, 13), 6).entries.nnz == 4

    def test_case_08(self):
        assert self._jacobian((slice(5, 8), slice(8, 12), slice(14, 16)), slice(6, 15), 9).entries.nnz == 7

    def test_case_09(self):
        assert self._jacobian((slice(0, 1), slice(2, 5), slice(6, 9)), slice(1, 7), 7).entries.nnz == 4

    def test_case_10(self):
        assert self._jacobian((slice(3, 6), slice(11, 14)), slice(4, 12), 6).entries.nnz == 3
