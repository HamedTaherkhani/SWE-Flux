from sympy import cse, symbols


class TestSimplifyCseMatchCommonArgsDefUsePairsQA:
    def test_simplify_cse_match_common_args_def_use_pairs_case(self):
        x0, x1, x2, x3, x4, x5 = symbols("x0:6")

        exprs = [
            (x0 + x1 + x2 + x3) * (x0 + x1 + x4),
            (x0 + x1 + x2 + x3) * (x0 + x1 + x5),
            (x0 + x1 + x2 + x4) * (x0 + x1 + x5),
            (x0 + x1 + x2 + x3 + x4 + x5) ** 2,
        ]

        replacements, reduced = cse(exprs, order="canonical")

        assert len(reduced) == 4
        assert len(replacements) >= 1
