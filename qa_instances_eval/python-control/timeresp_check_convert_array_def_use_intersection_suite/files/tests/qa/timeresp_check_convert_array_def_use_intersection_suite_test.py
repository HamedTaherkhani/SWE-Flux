import numpy as np

from control.timeresp import _check_convert_array


def _assert_numeric_array(out):
    assert isinstance(out, np.ndarray)
    assert out.dtype.kind in {"i", "f", "c"}
    assert out.size >= 1


class TestCheckConvertArrayDefUseIntersectionQA:
    def test_case_01(self):
        out = _check_convert_array(2.5, [(3,), (1, 3)], "case01: ", squeeze=False)
        _assert_numeric_array(out)
        assert out.shape == (3,)

    def test_case_02(self):
        out = _check_convert_array([[1.0, 2.0, 3.0]], [(3,), (1, 3)], "case02: ", squeeze=True)
        _assert_numeric_array(out)
        assert out.shape == (3,)

    def test_case_03(self):
        out = _check_convert_array([[1.0], [2.0], [3.0]], [(3,), (1, 3)], "case03: ", squeeze=True, transpose=True)
        _assert_numeric_array(out)
        assert out.shape == (3,)

    def test_case_04(self):
        out = _check_convert_array(np.array([[1, 2], [3, 4]]), [(2, 2), (4,)], "case04: ")
        _assert_numeric_array(out)
        assert out.shape == (2, 2)

    def test_case_05(self):
        out = _check_convert_array([1 + 2j, 3 + 4j], [(2,), (1, 2)], "case05: ", squeeze=False)
        _assert_numeric_array(out)
        assert out.shape == (2,)

    def test_case_06(self):
        out = _check_convert_array(np.array([[5.0, 6.0]]), [(1, "any"), (2,)], "case06: ")
        _assert_numeric_array(out)
        assert out.shape == (1, 2)

    def test_case_07(self):
        out = _check_convert_array([[7.0], [8.0]], [(2,), ("any", 1)], "case07: ", squeeze=False)
        _assert_numeric_array(out)
        assert out.shape == (2, 1)

    def test_case_08(self):
        out = _check_convert_array(np.array([[[1.0], [2.0]]]), [(1, 2, 1), (2,)], "case08: ", squeeze=True)
        _assert_numeric_array(out)
        assert out.shape == (2,)

    def test_case_09(self):
        out = _check_convert_array(np.float64(9.0), [(1,), (1, 1)], "case09: ", squeeze=True)
        _assert_numeric_array(out)
        assert out.shape == (1,)

    def test_case_10(self):
        out = _check_convert_array([[10.0, 11.0]], [(2,), (1, 2)], "case10: ", squeeze=False)
        _assert_numeric_array(out)
        assert out.shape == (1, 2)
