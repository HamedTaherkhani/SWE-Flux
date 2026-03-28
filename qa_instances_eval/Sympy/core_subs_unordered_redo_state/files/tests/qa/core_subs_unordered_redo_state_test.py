from sympy import Rational, exp, nan, oo, symbols, zoo


class TestCoreSubsUnorderedRedoStateQA:
    def test_core_subs_unordered_redo_state_case(self):
        x, y, z, a, b = symbols("x y z a b")

        expr = exp((x + y)/(z + 1)) + (a + b)/(x - y) + (x + y + z)**2

        replacements = {
            x + y: oo,
            z + 1: zoo,
            a + b: oo,
            x - y: Rational(3, 2),
        }

        substituted = expr.subs(replacements)

        assert substituted != expr
        assert substituted.has(oo) or substituted.has(zoo) or substituted is nan
