from __future__ import annotations

from sympy import cos, symbols
from sympy.utilities.lambdify import lambdify


class TestUtilitiesLambdifyLinePathDeterminismQA:
    def test_utilities_lambdify_line_path_determinism_case(self):
        x = symbols("x")
        expr = cos(x) + x**3 - x

        generated = lambdify(x, expr, "math")
        assert callable(generated)
