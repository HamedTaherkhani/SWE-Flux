import warnings

import numpy as np

from control.nlsys import _process_vector_argument


def _assert_vector(out, size):
    val, nelem = out
    assert isinstance(val, np.ndarray)
    assert val.shape == (size,)
    assert nelem == size
    assert val[-1] == 0


class TestProcessVectorArgumentDefUseIntersectionQA:
    def test_case_01(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = _process_vector_argument(([1.0], [2.0], [0.0]), "case01", 6)
        _assert_vector(out, 6)

    def test_case_02(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = _process_vector_argument(([1.0, 2.0], [0.0]), "case02", 5)
        _assert_vector(out, 5)

    def test_case_03(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = _process_vector_argument((np.array([3.0]), [4.0], [0.0]), "case03", 5)
        _assert_vector(out, 5)

    def test_case_04(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = _process_vector_argument(([5.0, 6.0], np.array([0.0])), "case04", 6)
        _assert_vector(out, 6)

    def test_case_05(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = _process_vector_argument(([7.0], (8.0,), [0.0]), "case05", 7)
        _assert_vector(out, 7)

    def test_case_06(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = _process_vector_argument((np.array([[1.0, 2.0]]), [0.0]), "case06", 6)
        _assert_vector(out, 6)

    def test_case_07(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = _process_vector_argument(([9.0], np.array([[10.0]]), [0.0]), "case07", 6)
        _assert_vector(out, 6)

    def test_case_08(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = _process_vector_argument(([11.0, 12.0], [13.0], [0.0]), "case08", 7)
        _assert_vector(out, 7)

    def test_case_09(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = _process_vector_argument((np.array([14.0]), np.array([0.0])), "case09", 5)
        _assert_vector(out, 5)

    def test_case_10(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = _process_vector_argument(([15.0], [16.0, 17.0], [0.0]), "case10", 8)
        _assert_vector(out, 8)
