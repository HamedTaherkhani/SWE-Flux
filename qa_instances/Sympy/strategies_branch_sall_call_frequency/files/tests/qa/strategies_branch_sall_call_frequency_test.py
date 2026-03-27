from sympy.core.basic import Basic
from sympy.strategies.branch import yieldify
from sympy.strategies.branch.tools import canon
from sympy.strategies.rl import flatten


class TestStrategiesBranchSallCallFrequencyQA:
    def test_strategies_branch_sall_call_frequency_case(self):
        leaf = Basic()
        expr_tree = Basic(
            Basic(leaf, Basic(leaf, leaf)),
            Basic(Basic(leaf, leaf), leaf),
            Basic(leaf, Basic(leaf, Basic(leaf, leaf))),
        )

        canonical_rule = canon(yieldify(flatten))
        results = tuple(canonical_rule(expr_tree))

        assert len(results) == 1
        assert isinstance(results[0], Basic)
