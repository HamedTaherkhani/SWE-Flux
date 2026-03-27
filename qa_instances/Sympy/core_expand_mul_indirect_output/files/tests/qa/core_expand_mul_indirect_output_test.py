from sympy import expand, symbols


class TestCoreExpandMulIndirectOutputQA:
    def test_core_expand_mul_indirect_output_case(self):
        x, y, z = symbols("x y z")
        composite_expr = (x + 2*y - z)**3 * (x - y + z/2)

        expanded_expr = expand(
            composite_expr,
            mul=True,
            power_exp=True,
            power_base=True,
        )

        assert expanded_expr.is_Add
        assert expanded_expr.has(x, y, z)
        assert expanded_expr.as_poly(x, y, z) is not None
