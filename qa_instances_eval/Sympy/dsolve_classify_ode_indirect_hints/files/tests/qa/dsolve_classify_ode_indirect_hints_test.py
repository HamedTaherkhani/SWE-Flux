from sympy import Eq, Function, dsolve, exp, symbols


class TestDsolveClassifyOdeIndirectHintsQA:
    def test_dsolve_classify_ode_indirect_hints_case(self):
        x = symbols("x")
        y = Function("y")

        ode_expr = Eq(
            y(x).diff(x, 2) - 3 * y(x).diff(x) + 2 * y(x),
            exp(x),
        )

        solution = dsolve(ode_expr)

        assert solution.lhs == y(x)
        assert solution.rhs.has(exp(x))
        assert "C1" in str(solution.rhs)
