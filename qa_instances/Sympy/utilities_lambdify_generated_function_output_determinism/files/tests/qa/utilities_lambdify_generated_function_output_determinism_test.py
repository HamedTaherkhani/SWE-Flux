from __future__ import annotations

from sympy import sin, symbols
from sympy.utilities.lambdify import lambdify


class TestUtilitiesLambdifyGeneratedFunctionOutputDeterminismQA:
    def test_utilities_lambdify_generated_function_output_determinism_case(self):
        x = symbols("x")
        expr = sin(x) + x**2

        generated = lambdify(x, expr, "math")
        assert callable(generated)
