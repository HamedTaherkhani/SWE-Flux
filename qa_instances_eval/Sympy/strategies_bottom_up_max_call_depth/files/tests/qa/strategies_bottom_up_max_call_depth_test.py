from sympy import sin, symbols
from sympy.strategies.core import identity
from sympy.strategies.traverse import bottom_up


class TestStrategiesBottomUpMaxCallDepthQA:
    def test_strategies_bottom_up_max_call_depth_case(self):
        x = symbols("x")

        expr = x
        for _ in range(16):
            expr = sin(expr)

        rewritten = bottom_up(identity)(expr)

        assert rewritten == expr
