from sympy.logic.boolalg import simplify_logic
from sympy.abc import w, x, y, z


class TestLogicSimplifyLogicFunctionCallOrderQA:
    def test_logic_simplify_logic_function_call_order_case(self):
        clauses = [
            x & y,
            x & z,
            ~x & w,
            y & z & w,
            x & ~w,
            (~y & z & ~w) | (x & y & ~z),
        ]
        expr = clauses[0]
        for clause in clauses[1:]:
            expr = expr | clause

        simplified = simplify_logic(expr, form="dnf", deep=True, force=True)

        assert simplified.free_symbols == {w, x, y, z}
        assert simplified != expr
