from __future__ import annotations

import pytest

from sympy import Matrix, S
from sympy.stats import DiscreteMarkovChain


MATRICES = [
    Matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
    Matrix([[S(1)/2, S(1)/2, 0], [S(1)/3, S(2)/3, 0], [0, 0, 1]]),
    Matrix([[0, 1, 0], [1, 0, 0], [S(1)/2, S(1)/2, 0]]),
    Matrix([[S(1)/3, S(1)/3, S(1)/3], [0, 1, 0], [0, 0, 1]]),
    Matrix([[S(1)/4, S(3)/4, 0, 0], [S(1)/2, S(1)/2, 0, 0], [0, 0, 1, 0], [0, 0, S(1)/3, S(2)/3]]),
    Matrix([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]]),
    Matrix([[S(1)/2, 0, S(1)/2], [S(1)/4, S(1)/2, S(1)/4], [0, S(1)/3, S(2)/3]]),
    Matrix([[S(2)/5, S(3)/5, 0], [S(1)/5, S(4)/5, 0], [S(1)/2, 0, S(1)/2]]),
    Matrix([[0, 1, 0, 0, 0], [S(1)/2, 0, S(1)/2, 0, 0], [0, S(1)/2, 0, S(1)/2, 0], [0, 0, S(1)/2, 0, S(1)/2], [0, 0, 0, 0, 1]]),
    Matrix([[S(1)/3, S(1)/3, S(1)/3, 0], [S(1)/2, 0, S(1)/2, 0], [0, S(1)/2, 0, S(1)/2], [0, 0, 0, 1]]),
    Matrix([[1, 0, 0, 0], [S(1)/2, S(1)/2, 0, 0], [0, S(1)/2, S(1)/2, 0], [0, 0, S(1)/2, S(1)/2]]),
    Matrix([[S(1)/2, S(1)/2, 0, 0], [0, S(1)/2, S(1)/2, 0], [0, 0, S(1)/2, S(1)/2], [S(1)/2, 0, 0, S(1)/2]]),
    Matrix([[S(3)/4, S(1)/4, 0], [S(1)/4, S(3)/4, 0], [S(1)/3, S(1)/3, S(1)/3]]),
    Matrix([[S(1)/2, S(1)/4, S(1)/4], [S(1)/4, S(1)/2, S(1)/4], [S(1)/4, S(1)/4, S(1)/2]]),
    Matrix([[0, S(1)/2, S(1)/2, 0], [S(1)/2, 0, S(1)/2, 0], [S(1)/2, S(1)/2, 0, 0], [0, 0, 0, 1]]),
    Matrix([[S(1)/5, S(4)/5, 0, 0], [S(2)/5, S(3)/5, 0, 0], [0, 0, S(1)/2, S(1)/2], [0, 0, S(1)/2, S(1)/2]]),
    Matrix([[S(1)/2, 0, 0, S(1)/2], [0, S(1)/2, S(1)/2, 0], [0, S(1)/2, S(1)/2, 0], [S(1)/2, 0, 0, S(1)/2]]),
    Matrix([[S(1)/3, S(2)/3, 0, 0, 0], [S(1)/3, S(1)/3, S(1)/3, 0, 0], [0, S(1)/2, S(1)/2, 0, 0], [0, 0, 0, S(1)/2, S(1)/2], [0, 0, 0, S(1)/2, S(1)/2]]),
    Matrix([[0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1], [1, 0, 0, 0]]),
    Matrix([[S(2)/3, S(1)/3, 0, 0], [S(1)/3, S(2)/3, 0, 0], [0, 0, S(3)/4, S(1)/4], [0, 0, S(1)/4, S(3)/4]]),
    Matrix([[S(1)/2, S(1)/2, 0, 0, 0], [S(1)/2, S(1)/2, 0, 0, 0], [0, 0, S(1)/2, S(1)/2, 0], [0, 0, S(1)/2, S(1)/2, 0], [0, 0, 0, 0, 1]]),
    Matrix([[S(1)/4, S(1)/4, S(1)/4, S(1)/4], [S(1)/2, S(1)/2, 0, 0], [0, 0, S(1)/2, S(1)/2], [S(1)/3, 0, S(1)/3, S(1)/3]]),
    Matrix([[S(1)/2, 0, S(1)/2, 0], [0, S(1)/2, 0, S(1)/2], [S(1)/2, 0, S(1)/2, 0], [0, S(1)/2, 0, S(1)/2]]),
    Matrix([[S(1)/3, S(1)/3, S(1)/3], [S(1)/3, S(1)/3, S(1)/3], [S(1)/3, S(1)/3, S(1)/3]]),
]


class TestStatsMarkovCanonicalLevelRelationInvariantSuiteQA:
    @pytest.mark.parametrize("transitions", MATRICES)
    def test_stats_markov_canonical_level_relation_invariant_suite_case(self, transitions):
        chain = DiscreteMarkovChain("X", trans_probs=transitions)
        states, canonical = chain.canonical_form()
        assert len(states) == transitions.shape[0]
        assert canonical.shape == transitions.shape
