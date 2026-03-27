from sympy.logic.inference import satisfiable
from sympy.abc import A, B, C, D, E, F


class TestLogicDpll2FindModelDefUsePairsQA:
    def test_logic_dpll2_find_model_def_use_pairs_case(self):
        expr_multi = (A | B) & (~A | ~B) & (C | D) & (~C | ~D)
        model_stream = satisfiable(expr_multi, algorithm="dpll2", all_models=True)
        model_one = next(model_stream)
        model_two = next(model_stream)

        expr_unsat = A & ~A
        unsat_model = satisfiable(expr_unsat, algorithm="dpll2")

        expr_sat = (A | B) & (~A | C) & (~B | C) & (~C | D) & (D | E) & (~E | F)
        sat_model = satisfiable(expr_sat, algorithm="dpll2")

        assert isinstance(model_one, dict)
        assert isinstance(model_two, dict)
        assert model_one != model_two
        assert unsat_model is False
        assert isinstance(sat_model, dict)
