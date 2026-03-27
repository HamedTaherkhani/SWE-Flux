from sympy import Symbol
from sympy.physics.hydrogen import Psi_nlm


class TestHydrogenPsiNlmIndirectRadialOutputQA:
    def test_hydrogen_psi_nlm_indirect_radial_output_case(self):
        r = Symbol("r", positive=True)
        phi = Symbol("phi", real=True)
        theta = Symbol("theta", real=True)
        Z = Symbol("Z", positive=True, integer=True, nonzero=True)

        psi_expr = Psi_nlm(7, 3, 1, r, phi, theta, Z)

        assert psi_expr != 0
        assert psi_expr.has(r)
        assert psi_expr.has(phi)
        assert psi_expr.has(theta)
        assert psi_expr.has(Z)
