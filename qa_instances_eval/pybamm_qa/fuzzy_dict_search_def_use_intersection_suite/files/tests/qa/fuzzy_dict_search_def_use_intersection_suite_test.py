from __future__ import annotations

import contextlib
import io

import pybamm


PARAMETERS = {
    "Negative electrode capacity [Ah]": 1.0,
    "Positive electrode capacity [Ah]": 2.0,
    "Cell capacity [Ah]": 3.0,
    "Nominal cell capacity [Ah]": 4.0,
    "Initial concentration [mol.m-3]": 5.0,
    "Final concentration [mol.m-3]": 6.0,
    "Separator thickness [m]": 7.0,
    "Negative particle radius [m]": 8.0,
    "Positive particle radius [m]": 9.0,
    "Electrolyte conductivity [S.m-1]": 10.0,
}


class TestFuzzyDictSearchDefUseIntersectionQA:
    def _search(self, key):
        params = pybamm.ParameterValues(PARAMETERS)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            params.search(key, print_values=False)
        output = stream.getvalue()
        assert "Results for" in output
        return output

    def test_case_01(self):
        assert "Negative electrode capacity" in self._search("negative electrode")

    def test_case_02(self):
        assert "Positive electrode capacity" in self._search("positive electrode")

    def test_case_03(self):
        assert "Cell capacity" in self._search("cell capacity")

    def test_case_04(self):
        assert "Nominal cell capacity" in self._search("nominal cell")

    def test_case_05(self):
        assert "Initial concentration" in self._search("initial concentration")

    def test_case_06(self):
        assert "Final concentration" in self._search("final concentration")

    def test_case_07(self):
        assert "Separator thickness" in self._search("separator thickness")

    def test_case_08(self):
        assert "Negative particle radius" in self._search("negative particle")

    def test_case_09(self):
        assert "Positive particle radius" in self._search("positive particle")

    def test_case_10(self):
        assert "Electrolyte conductivity" in self._search("electrolyte conductivity")
