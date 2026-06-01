import numpy as np
import scipy.optimize as opt

from control.optimal import _process_constraints


def _nl_fun(x):
    return np.array([x[0] + x[1]])


def _lin(scale):
    return opt.LinearConstraint(np.array([[scale, 1.0]]), [-scale], [scale])


def _nonlin(offset):
    return opt.NonlinearConstraint(_nl_fun, [-offset], [offset])


def _tuple(kind, payload, low, high):
    return (kind, payload, low, high)


class TestProcessConstraintsDependencyVariabilityQA:
    def test_case_01(self):
        assert _process_constraints(None, "case01") == []

    def test_case_02(self):
        out = _process_constraints(_tuple(opt.LinearConstraint, np.eye(2), [0, 0], [1, 1]), "case02")
        assert len(out) == 1

    def test_case_03(self):
        out = _process_constraints(_lin(2.0), "case03")
        assert len(out) == 1

    def test_case_04(self):
        out = _process_constraints(_nonlin(3.0), "case04")
        assert len(out) == 1

    def test_case_05(self):
        out = _process_constraints([_lin(4.0), _nonlin(5.0)], "case05")
        assert len(out) == 2

    def test_case_06(self):
        out = _process_constraints([_tuple(opt.NonlinearConstraint, _nl_fun, [-1], [1]), _lin(6.0)], "case06")
        assert len(out) == 2

    def test_case_07(self):
        out = _process_constraints([_tuple(opt.LinearConstraint, [[1, 0]], [0], [2])], "case07")
        assert len(out) == 1

    def test_case_08(self):
        out = _process_constraints([_nonlin(7.0), _tuple(opt.LinearConstraint, [[0, 1]], [-2], [2])], "case08")
        assert len(out) == 2

    def test_case_09(self):
        out = _process_constraints([_lin(8.0), _lin(9.0)], "case09")
        assert len(out) == 2

    def test_case_10(self):
        out = _process_constraints([_nonlin(10.0), _nonlin(11.0)], "case10")
        assert len(out) == 2
