from sympy import Identity, MatrixSymbol
from sympy.matrices.expressions import BlockMatrix
from sympy.matrices.expressions.blockmatrix import block_collapse


class TestMatricesBlockmatrixFunctionCallOrderQA:
    def test_matrices_blockmatrix_function_call_order_case(self):
        n = 2
        A = MatrixSymbol("A", n, n)
        B = MatrixSymbol("B", n, n)
        C = MatrixSymbol("C", n, n)
        D = MatrixSymbol("D", n, n)
        I = Identity(n)

        X = BlockMatrix([[A, B], [C, D]])
        Y = BlockMatrix([[I, B], [C, I]])

        expr = (X + Y.T) * X + X.I
        collapsed = block_collapse(expr)

        assert collapsed.shape == (2*n, 2*n)
        assert collapsed != expr
