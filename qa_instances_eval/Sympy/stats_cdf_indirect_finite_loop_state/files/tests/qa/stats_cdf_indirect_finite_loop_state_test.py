from sympy import Rational
from sympy.stats import Binomial, cdf


class TestStatsCdfIndirectFiniteLoopStateQA:
    def test_stats_cdf_indirect_finite_loop_state_case(self):
        x = Binomial("x", 20, Rational(2, 5))

        transformed = x**3 - 4*x + 7
        cdf_result = cdf(transformed)

        assert isinstance(cdf_result, dict)
        assert len(cdf_result) > 10
        assert min(cdf_result.values()) > 0
        assert max(cdf_result.values()) == 1
