import numpy as np

from control.xferfcn import _clean_part


def _assert_poly_matrix(out, rows, cols):
    assert out.shape == (rows, cols)
    for i in range(rows):
        for j in range(cols):
            assert isinstance(out[i, j], np.ndarray)
            assert out[i, j].ndim == 1


class TestCleanPartDefUseIntersectionQA:
    def test_case_01(self):
        out = _clean_part([[[1, 2], [3]], [[4], [5, 6]]], "case01")
        _assert_poly_matrix(out, 2, 2)

    def test_case_02(self):
        out = _clean_part([[[0], [2, 1]], [[3, 0], [4]]], "case02")
        _assert_poly_matrix(out, 2, 2)

    def test_case_03(self):
        out = _clean_part([[[1.5], [2]], [[3, 4], [5.0, 6.0]]], "case03")
        _assert_poly_matrix(out, 2, 2)

    def test_case_04(self):
        out = _clean_part([[[1], [2], [3]], [[4, 0], [5], [6, 1]]], "case04")
        _assert_poly_matrix(out, 2, 3)

    def test_case_05(self):
        out = _clean_part([[[1], [2]], [[3], [4]], [[5, 6], [7]]], "case05")
        _assert_poly_matrix(out, 3, 2)

    def test_case_06(self):
        out = _clean_part([[(1, 0), (2, 3)], [(4,), (5, 0)]], "case06")
        _assert_poly_matrix(out, 2, 2)

    def test_case_07(self):
        out = _clean_part([[[np.int64(1)], [2]], [[3], [4, 5]]], "case07")
        _assert_poly_matrix(out, 2, 2)

    def test_case_08(self):
        out = _clean_part([[[1 + 0j], [2]], [[3], [4 - 1j]]], "case08")
        _assert_poly_matrix(out, 2, 2)

    def test_case_09(self):
        out = _clean_part([[[2, 0, 1], [3]], [[4], [5, 0, 6]]], "case09")
        _assert_poly_matrix(out, 2, 2)

    def test_case_10(self):
        out = _clean_part([[[1], [2, 2], [3]], [[4], [5], [6, 0]]], "case10")
        _assert_poly_matrix(out, 2, 3)
