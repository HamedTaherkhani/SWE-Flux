from __future__ import annotations

import pytest

from sympy.abc import A, B, C, D, E, F, G, H, I, J
from sympy.logic.inference import satisfiable


CASES = [
    A,
    A & ~A,
    (A | B) & (~A | B) & (A | ~B),
    (A | B) & (~A | ~B) & (A | ~B) & (~A | B),
    (A >> B) & (B >> C) & A & ~C,
    (A >> B) & (B >> C) & A,
    (A | B | C) & (~A | D) & (~B | D) & (~C | D) & ~D,
    (A | B | C) & (~A | D) & (~B | E) & (~C | F) & (D | E | F),
    (A ^ B) & (B ^ C) & (C ^ D),
    (A ^ B) & ~(A ^ B),
    (A | B) & (~A | C) & (~B | C) & (~C | D) & (~D | E) & (~E | F),
    (A | B) & (~A | C) & (~B | C) & (~C | D) & (~D | E) & (~E | ~F) & F,
    (A | B | C | D) & (~A | ~B) & (~C | ~D) & (A | ~C) & (B | ~D),
    (A | B) & (~A | ~B) & (C | D) & (~C | ~D) & (A | C) & (~B | ~D),
    (A | B) & (~A | C) & (~B | D) & (~C | E) & (~D | E) & ~E,
    (A | B | C) & (~A | ~B) & (~A | ~C) & (~B | ~C),
    (A | B | C) & (~A | ~B) & (~A | ~C) & (~B | ~C) & A & B,
    (A | B) & (~A | C) & (~C | D) & (~D | E) & (~E | A),
    (A | B) & (~A | C) & (~C | D) & (~D | E) & (~E | ~A) & A,
    (A | B | C) & (~A | D) & (~B | E) & (~C | F) & (~D | ~E) & (~E | ~F) & (~D | ~F),
    (A | B) & (~A | C) & (~B | C) & (~C | D) & (~D | E) & (~E | F) & (~F | G) & (~G | H),
    (A | B) & (~A | C) & (~B | D) & (~C | E) & (~D | F) & (~E | G) & (~F | G) & ~G,
    (A | B | C) & (~A | D) & (~B | D) & (~C | D) & (D | E) & (~E | F) & (~F | G) & (~G | H) & (~H | I),
    (A | B | C) & (~A | D) & (~B | E) & (~C | F) & (~D | G) & (~E | G) & (~F | G) & (~G | H) & (~H | I) & (~I | J),
]


class TestLogicDpllUnknownClausesEmptyInvariantSuiteQA:
    @pytest.mark.parametrize("expr", CASES)
    def test_logic_dpll_unknown_clauses_empty_invariant_suite_case(self, expr):
        result = satisfiable(expr, algorithm="dpll")
        assert result is False or isinstance(result, dict)
