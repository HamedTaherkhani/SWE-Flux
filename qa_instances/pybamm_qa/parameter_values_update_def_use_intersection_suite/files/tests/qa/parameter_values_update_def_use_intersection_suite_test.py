from __future__ import annotations

import numpy as np
import pybamm


class TestParameterValuesUpdateDefUseIntersectionQA:
    def _build(self, values):
        params = pybamm.ParameterValues(values)
        assert set(values).issubset(set(params.keys()))
        return params

    def test_case_01(self):
        params = self._build({"qa scalar": 1.5, "qa other": 2})
        assert params["qa scalar"] == 1.5

    def test_case_02(self):
        params = self._build({"qa string scalar": "3.25", "qa count": "4"})
        assert params["qa string scalar"] == 3.25

    def test_case_03(self):
        params = self._build({"qa input": "[input]", "qa scalar": 0.2})
        assert isinstance(params["qa input"], pybamm.InputParameter)

    def test_case_04(self):
        data = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 4.0]])
        params = self._build({"qa data": ("curve", data), "qa scalar": 9.0})
        assert params["qa data"][0] == "curve"

    def test_case_05(self):
        params = self._build({"qa symbol": pybamm.Scalar(7), "qa scalar": 1})
        assert isinstance(params["qa symbol"], pybamm.Scalar)

    def test_case_06(self):
        params = self._build({"qa callable": lambda x: x + 1, "qa scalar": 2.0})
        assert callable(params["qa callable"])

    def test_case_07(self):
        params = self._build({"qa array": np.array([1.0, 2.0]), "qa scalar": "5"})
        assert params["qa array"].shape == (2,)

    def test_case_08(self):
        params = self._build({"qa bool": True, "qa string scalar": "6.5"})
        assert params["qa bool"] is True

    def test_case_09(self):
        params = self._build({"qa tuple": ("raw", (["x"], [1.0])), "qa scalar": 3})
        assert params["qa tuple"][0] == "raw"

    def test_case_10(self):
        params = self._build({"qa none": None, "qa scalar": "8.75"})
        assert params["qa none"] is None
