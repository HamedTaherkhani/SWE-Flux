from sympy import Eq, S, oo, symbols
from sympy.solvers.solveset import solveset
from sympy.sets.sets import Set


class TestSolvesetRationalCaughtExceptionKindsQA:
    def test_solveset_rational_caught_exception_kinds_case(self):
        x, a = symbols("x a")

        equations = [
            Eq((x**5 - x + a) / (x + 1), 0),
            Eq(oo*x**2 + x + 1, 0),
        ]

        outputs = [solveset(eq, x, S.Complexes) for eq in equations]

        assert len(outputs) == 2
        assert all(isinstance(out, Set) for out in outputs)
