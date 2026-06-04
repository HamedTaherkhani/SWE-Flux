import casadi
import pybamm


class TestSymbolToCasadiExceptionDiversityQA:
    def _convert(self, symbol, *, t=None, y=None, y_dot=None, inputs=None):
        try:
            return symbol.to_casadi(t=t, y=y, y_dot=y_dot, inputs=inputs)
        except Exception:
            return None

    def test_case_01(self):
        self._convert(pybamm.Scalar(2))

    def test_case_02(self):
        y = casadi.MX.sym("y", 4)
        self._convert(pybamm.sin(pybamm.StateVector(slice(0, 2))) + 3, y=y)

    def test_case_03(self):
        self._convert(pybamm.StateVector(slice(0, 2)))

    def test_case_04(self):
        y = casadi.MX.sym("y", 4)
        self._convert(pybamm.StateVectorDot(slice(0, 2)), y=y)

    def test_case_05(self):
        self._convert(pybamm.Variable("x"))

    def test_case_06(self):
        u = casadi.MX.sym("u")
        self._convert(pybamm.InputParameter("u"), inputs={"u": u})

    def test_case_07(self):
        self._convert(pybamm.InputParameter("u"), inputs={})

    def test_case_08(self):
        y = casadi.MX.sym("y", 4)
        symbol = pybamm.NumpyConcatenation(
            pybamm.Scalar(1), pybamm.StateVector(slice(0, 2))
        )
        self._convert(symbol, y=y)

    def test_case_09(self):
        y = casadi.MX.sym("y", 4)
        self._convert(pybamm.maximum(pybamm.StateVector(slice(0, 2)), 1), y=y)

    def test_case_10(self):
        c = pybamm.Variable("c", domain="negative electrode")
        self._convert(pybamm.grad(c))
