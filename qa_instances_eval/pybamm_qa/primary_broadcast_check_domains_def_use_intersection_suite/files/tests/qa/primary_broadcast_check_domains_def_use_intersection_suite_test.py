from __future__ import annotations

import pybamm


class TestPrimaryBroadcastCheckDomainsDefUseIntersectionQA:
    def _broadcast(self, value, domain):
        broadcast = pybamm.PrimaryBroadcast(pybamm.Scalar(value), domain)
        assert broadcast.broadcast_domain == [domain]
        assert broadcast.domain == [domain]
        return broadcast

    def test_case_01(self):
        assert self._broadcast(1.0, "negative electrode").broadcast_type

    def test_case_02(self):
        assert self._broadcast(2.0, "separator").broadcast_type

    def test_case_03(self):
        assert self._broadcast(3.0, "positive electrode").broadcast_type

    def test_case_04(self):
        assert self._broadcast(4.0, "negative particle").broadcast_type

    def test_case_05(self):
        assert self._broadcast(5.0, "positive particle").broadcast_type

    def test_case_06(self):
        assert self._broadcast(6.0, "negative particle size").broadcast_type

    def test_case_07(self):
        assert self._broadcast(7.0, "positive particle size").broadcast_type

    def test_case_08(self):
        assert self._broadcast(8.0, "negative electrode").domain

    def test_case_09(self):
        assert self._broadcast(9.0, "separator").domain

    def test_case_10(self):
        assert self._broadcast(10.0, "positive electrode").domain
