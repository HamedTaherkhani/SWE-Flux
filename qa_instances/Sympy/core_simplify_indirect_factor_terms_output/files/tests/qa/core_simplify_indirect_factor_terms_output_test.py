from sympy import cos, exp, simplify, sin, symbols


class TestCoreSimplifyIndirectFactorTermsOutputQA:
    def test_core_simplify_indirect_factor_terms_output_case(self):
        x, y = symbols("x y")

        composite_expr = (
            (x**2 + 2*x*y + y**2) / (x + y)
            + sin(x)**2
            + cos(x)**2
            + exp(x) * exp(y)
            - exp(x + y)
        )

        simplified_expr = simplify(composite_expr)

        assert simplified_expr.is_Add
        assert simplified_expr.has(x, y)
        assert simplified_expr.as_coeff_add()[0].is_Integer
