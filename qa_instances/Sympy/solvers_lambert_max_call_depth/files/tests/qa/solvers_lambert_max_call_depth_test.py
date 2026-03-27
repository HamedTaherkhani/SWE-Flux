from sympy import exp, symbols
from sympy.solvers.solvers import solve


class TestSolversLambertMaxCallDepthQA:
    def test_solvers_lambert_max_call_depth_case(self):
        x = symbols("x")

        solutions = solve(x + exp(x), x, dict=True)

        assert isinstance(solutions, list)
        assert len(solutions) == 1
        assert x in solutions[0]
