from sympy import cos, sin, symbols, trigsimp


class TestSimplifyTrigsimpMaxCallDepthQA:
    def test_simplify_trigsimp_max_call_depth_case(self):
        x = symbols("x")

        expr = sin(x)**4 - 2*sin(x)**2*cos(x)**2 + cos(x)**4
        simplified = trigsimp(expr)

        assert (simplified - cos(2*x)**2).expand(trig=True) == 0
