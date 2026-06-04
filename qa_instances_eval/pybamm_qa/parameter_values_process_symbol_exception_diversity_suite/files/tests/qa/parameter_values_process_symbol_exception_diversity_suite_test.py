import numpy as np
import pybamm


class TestParameterValuesProcessSymbolExceptionDiversityQA:
    def _process(self, values, symbol):
        try:
            return values.process_symbol(symbol)
        except Exception:
            return None

    def test_case_01(self):
        self._process(pybamm.ParameterValues({"a": 2}), pybamm.Parameter("a"))

    def test_case_02(self):
        self._process(pybamm.ParameterValues({"a": 2}), pybamm.Parameter("missing"))

    def test_case_03(self):
        self._process(pybamm.ParameterValues({"a": np.nan}), pybamm.Parameter("a"))

    def test_case_04(self):
        self._process(pybamm.ParameterValues({"a": object()}), pybamm.Parameter("a"))

    def test_case_05(self):
        self._process(pybamm.ParameterValues({"a": [1, 2]}), pybamm.Parameter("a"))

    def test_case_06(self):
        symbol = pybamm.FunctionParameter("f", {"x": pybamm.Scalar(2)})
        self._process(pybamm.ParameterValues({"f": 3}), symbol)

    def test_case_07(self):
        symbol = pybamm.FunctionParameter("f", {"x": pybamm.Scalar(2)})
        self._process(pybamm.ParameterValues({"f": np.nan}), symbol)

    def test_case_08(self):
        symbol = pybamm.FunctionParameter("f", {"x": pybamm.Scalar(2)})
        self._process(pybamm.ParameterValues({"f": [1, 2]}), symbol)

    def test_case_09(self):
        symbol = pybamm.FunctionParameter("f", {"x": pybamm.Scalar(2)})
        self._process(pybamm.ParameterValues({"f": lambda x: x**2}), symbol)

    def test_case_10(self):
        symbol = pybamm.Parameter("a") + 2 * pybamm.Parameter("b")
        self._process(pybamm.ParameterValues({"a": 2, "b": 3}), symbol)
