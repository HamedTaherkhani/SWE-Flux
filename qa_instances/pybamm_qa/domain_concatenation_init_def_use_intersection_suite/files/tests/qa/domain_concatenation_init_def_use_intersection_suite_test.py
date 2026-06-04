from __future__ import annotations

import numpy as np
import pybamm


class FakeSubMesh:
    def __init__(self, npts):
        self.npts = npts


class FakeMesh:
    def __init__(self):
        self._items = {
            "negative electrode": FakeSubMesh(2),
            "separator": FakeSubMesh(3),
            "positive electrode": FakeSubMesh(4),
            "negative particle": FakeSubMesh(5),
            "positive particle": FakeSubMesh(6),
            ("current collector",): FakeSubMesh(2),
        }

    def __getitem__(self, key):
        if isinstance(key, list):
            key = tuple(key)
        return self._items[key]


MESH = FakeMesh()


def _child(domain, offset):
    npts = MESH[domain].npts * MESH[["current collector"]].npts
    entries = np.arange(offset, offset + npts, dtype=float)
    return pybamm.Vector(
        entries,
        domain=domain,
        auxiliary_domains={"secondary": "current collector"},
    )


class TestDomainConcatenationInitDefUseIntersectionQA:
    def _concat(self, domains):
        children = [_child(domain, 10 * i) for i, domain in enumerate(domains)]
        result = pybamm.simplified_domain_concatenation(children, MESH)
        expected = sum(MESH[domain].npts for domain in domains) * MESH[
            ["current collector"]
        ].npts
        assert result.evaluate().shape == (expected, 1)
        return result

    def test_case_01(self):
        assert self._concat(["negative electrode", "separator"]).size == 10

    def test_case_02(self):
        assert self._concat(["separator", "positive electrode"]).size == 14

    def test_case_03(self):
        assert self._concat(["negative electrode", "positive electrode"]).size == 12

    def test_case_04(self):
        assert self._concat(["negative particle", "positive particle"]).size == 22

    def test_case_05(self):
        assert self._concat(["negative electrode", "separator", "positive electrode"]).size == 18

    def test_case_06(self):
        assert self._concat(["negative particle", "negative electrode"]).size == 14

    def test_case_07(self):
        assert self._concat(["positive electrode", "positive particle"]).size == 20

    def test_case_08(self):
        assert self._concat(["negative electrode", "negative particle", "separator"]).size == 20

    def test_case_09(self):
        assert self._concat(["separator", "positive electrode", "positive particle"]).size == 26

    def test_case_10(self):
        assert self._concat(["negative particle", "positive particle", "positive electrode"]).size == 30
