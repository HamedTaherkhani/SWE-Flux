from sympy import cse, symbols


class TestSimplifyTreeCseDefUsePairsQA:
    def test_simplify_tree_cse_def_use_pairs_case(self):
        x0, x1, x2, x3, x4, x5, x6, x7 = symbols("x0:8")

        exprs = [
            (x0 + x1 + x2 + x3) * (x0 + x1 + x4 + x5),
            (x0 + x1 + x2 + x3) * (x0 + x1 + x6 + x7),
            (x0 + x1 + x2 + x4) * (x0 + x1 + x6 + x7),
            (x0 + x1 + x2 + x3 + x4 + x5 + x6 + x7) ** 2,
            (x0 + x1 + x2) * (x3 + x4 + x5) + (x0 + x1 + x2) * (x6 + x7),
        ]

        replacements, reduced = cse(exprs, order="canonical")

        assert len(reduced) == 5
        assert len(replacements) >= 3
