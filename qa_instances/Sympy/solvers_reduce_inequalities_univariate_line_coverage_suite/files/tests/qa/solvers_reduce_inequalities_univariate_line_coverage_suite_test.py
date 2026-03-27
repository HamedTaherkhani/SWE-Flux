from __future__ import annotations

import pytest

from sympy import S, acos, asin, atan, cos, cosh, exp, log, reduce_inequalities, sin, sinh, sqrt, symbols, tan


x = symbols("x", real=True)

CASES = [
    sin(x) > 0,
    sin(2*x) >= S.Half,
    cos(x) < 0,
    tan(x) <= 1,
    exp(x) > 3,
    log(x) < 2,
    sin(x) + cos(x) > 0,
    sin(x) - cos(2*x) <= 0,
    exp(sin(x)) - 1 >= 0,
    log(x + 3) > 0,
    atan(x) < 1,
    asin(x) <= 0,
    acos(x) >= S.Pi/3,
    sinh(x) > 0,
    cosh(x) >= 2,
    sqrt(x + 5) > 2,
    sin(x)**2 <= S.Half,
    cos(x)**2 >= S.Half,
    sin(x)*cos(x) > 0,
    tan(2*x) > -1,
    sin(x/2) < S(1)/3,
    cos(3*x) >= -S.Half,
    exp(-x) <= 5,
    log(2*x + 5) >= 1,
]


class TestSolversReduceInequalitiesUnivariateLineCoverageSuiteQA:
    @pytest.mark.parametrize("ineq", CASES)
    def test_solvers_reduce_inequalities_univariate_line_coverage_suite_case(self, ineq):
        # Indirect call: reduce_inequalities delegates to solve_univariate_inequality.
        result = reduce_inequalities(ineq, x)

        assert result is not None
        assert result != S.NaN
