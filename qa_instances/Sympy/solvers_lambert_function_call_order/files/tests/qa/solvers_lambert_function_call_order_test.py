from sympy import exp, symbols
from sympy.solvers.solvers import solve


class TestSolversLambertFunctionCallOrderQA:
    def test_solvers_lambert_function_call_order_case(self):
        x = symbols("x")

        results = [
            solve(x + exp(x), x, dict=True),
            solve(2*x + exp(2*x), x, dict=True),
        ]

        assert len(results) == 2
        assert all(isinstance(item, list) for item in results)
        assert all(item for item in results)
