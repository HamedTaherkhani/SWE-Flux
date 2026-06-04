from __future__ import annotations

import pybamm


class TestSymbolDomainsSetterDefUseIntersectionQA:
    def _make_symbol(self, name, domain):
        symbol = pybamm.Symbol(name, domain=domain)
        assert symbol.domain == [domain]
        return symbol

    def test_case_01(self):
        assert self._make_symbol("qa domain 01", "negative electrode").domain[0]

    def test_case_02(self):
        assert self._make_symbol("qa domain 02", "separator").domain[0]

    def test_case_03(self):
        assert self._make_symbol("qa domain 03", "positive electrode").domain[0]

    def test_case_04(self):
        assert self._make_symbol("qa domain 04", "current collector").domain[0]

    def test_case_05(self):
        assert self._make_symbol("qa domain 05", "negative particle").domain[0]

    def test_case_06(self):
        assert self._make_symbol("qa domain 06", "positive particle").domain[0]

    def test_case_07(self):
        assert self._make_symbol("qa domain 07", "negative particle size").domain[0]

    def test_case_08(self):
        assert self._make_symbol("qa domain 08", "positive particle size").domain[0]

    def test_case_09(self):
        assert self._make_symbol("qa domain 09", "negative electrode").name

    def test_case_10(self):
        assert self._make_symbol("qa domain 10", "positive electrode").name
