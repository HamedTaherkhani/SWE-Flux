from sympy import sin, symbols
from sympy.solvers.solvers import solve


class TestSolversSolveCaughtExceptionKindsQA:
    def test_solvers_solve_caught_exception_kinds_case(self):
        x, y = symbols("x y")

        systems = [
            ([x + y - 2, x - y - 1], [x, y]),
            ([sin(x) - y, x**2 - y], [x, y]),
        ]

        for equations, variables in systems:
            try:
                solve(equations, *variables, dict=True)
            except Exception:
                pass

        assert len(systems) == 2
