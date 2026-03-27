from sympy import Eq, Function, symbols
from sympy.solvers.ode.systems import dsolve_system


class TestSolversDsolveSystemComponentFailureQA:
    def test_solvers_dsolve_system_component_failure_case(self):
        f, g = symbols("f g", cls=Function)
        t = symbols("t")

        equations = (
            Eq(f(t).diff(t), 12 * f(t) - 6 * g(t)),
            Eq(g(t).diff(t) ** 2, 11 * f(t) + 3 * g(t)),
        )

        dsolve_system(equations)
