from sympy.logic.algorithms.dpll import dpll_satisfiable
from sympy.abc import A, B, C, D, E, F, G, H


class TestLogicDpllIntReprDefUsePairsQA:
    def test_logic_dpll_int_repr_def_use_pairs_case(self):
        expr_sat = (A | B) & (~A | C) & (~B | C) & (~C | D) & (E | ~D) & (~E | F) & (G | H) & (~G | ~H)
        expr_unsat = (A | B) & (~A | B) & (A | ~B) & (~A | ~B)
        expr_chain_unsat = (A | B | C) & (~A | D) & (~B | D) & (~C | D) & (~D | E) & (~E | F) & (~F | G) & (~G)

        model_sat = dpll_satisfiable(expr_sat)
        model_unsat = dpll_satisfiable(expr_unsat)
        model_chain_unsat = dpll_satisfiable(expr_chain_unsat)

        assert isinstance(model_sat, dict)
        assert model_sat
        assert model_unsat is False
        assert model_chain_unsat is False
