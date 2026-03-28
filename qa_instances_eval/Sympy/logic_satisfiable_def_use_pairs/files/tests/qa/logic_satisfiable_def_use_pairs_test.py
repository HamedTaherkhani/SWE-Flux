from sympy.logic.inference import satisfiable
from sympy.abc import A, B, C


class TestLogicSatisfiableDefUsePairsQA:
    def test_logic_satisfiable_def_use_pairs_case(self):
        model_default = satisfiable(A & ~B)

        unsat_stream = satisfiable(A & ~A, all_models=True)
        unsat_marker = next(unsat_stream)

        model_dpll = satisfiable((A | B) & (~A | C), algorithm="dpll")
        model_dpll2 = satisfiable((A | B) & (~A | C), algorithm="dpll2")
        model_minisat_fallback = satisfiable((A | B) & (~A | C), algorithm="minisat22")

        assert isinstance(model_default, dict)
        assert unsat_marker is False
        assert isinstance(model_dpll, dict)
        assert isinstance(model_dpll2, dict)
        assert isinstance(model_minisat_fallback, dict)
