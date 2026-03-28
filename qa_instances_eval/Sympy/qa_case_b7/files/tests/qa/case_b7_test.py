from sympy import Eq, Function, exp, symbols
from sympy.solvers.deutils import _desolve


class TestCaseB7QA:
    def test_case_b7(self):
        x = symbols("x")
        y = Function("y")

        ode_expr = Eq(
            y(x).diff(x, 2) - 3 * y(x).diff(x) + 2 * y(x),
            exp(x),
        )

        result_payload = _desolve(ode_expr, hint="default", type="ode")

        assert isinstance(result_payload, dict)
        assert "hint" in result_payload
        assert "order" in result_payload
        assert "func" in result_payload
        assert result_payload["order"] >= 1
        assert result_payload["func"] == y(x)
