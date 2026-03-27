from sympy.logic.inference import satisfiable
from sympy.abc import A, B, C, D, E, F, G, H


class TestLogicDpllUnknownClauseLoopIterationsQA:
    def test_logic_dpll_unknown_clause_loop_iterations_case(self):
        expr = (A | B) & (~A | C) & (~B | C) & (~C | D) & (E | ~D) & (~E | F) & (G | H) & (~G | ~H)
        model = satisfiable(expr, algorithm="dpll")

        assert isinstance(model, dict)
        assert model
