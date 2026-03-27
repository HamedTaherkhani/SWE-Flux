from sympy import Mul, Pow
from sympy.physics.quantum import Dagger
from sympy.physics.quantum.boson import BosonOp
from sympy.physics.quantum.operatorordering import _normal_ordered_form_factor


class TestOperatorOrderingNormalOrderedFormFactorDirectOutputQA:
    def test_operatorordering_normal_ordered_form_factor_direct_output_case(self):
        a = BosonOp("a")
        ad = Dagger(a)

        input_expr = Mul(
            Pow(a, 2, evaluate=False),
            ad,
            a,
            ad,
            evaluate=False,
        )

        result_expr = _normal_ordered_form_factor(
            input_expr,
            independent=False,
            recursive_limit=15,
        )

        assert result_expr != input_expr
        assert result_expr.has(a)
        assert result_expr.has(ad)
