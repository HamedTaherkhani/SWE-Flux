from __future__ import annotations

import numpy as np
import pybamm


class TestDiscretisationProcessDictDefUseDiverseQA:
    def _variables(self, seed):
        a = pybamm.Variable(f"qa disc a {seed}", scale=seed + 1, reference=seed / 10)
        b = pybamm.Variable(f"qa disc b {seed}", scale=seed + 2, reference=seed / 5)
        c = pybamm.Variable(f"qa disc c {seed}", scale=seed + 3, reference=seed / 7)
        return a, b, c

    def _disc(self, *variables):
        disc = pybamm.Discretisation()
        start = 0
        slices = {}
        for var in variables:
            width = 2 if "b" in var.name else 1
            slices[var] = [slice(start, start + width)]
            start += width
        disc.y_slices = slices
        return disc

    def _process(self, seed, mode):
        a, b, c = self._variables(seed)
        disc = self._disc(a, b, c)
        if mode == "scalar_rhs":
            eqns = {
                a: pybamm.Scalar(seed + 0.25),
                b: a + pybamm.Scalar(seed),
                f"diagnostic {seed}": pybamm.sin(a + b),
            }
            out = disc.process_dict(eqns, ics=False)
        elif mode == "scaled_ics":
            eqns = {
                a: pybamm.Scalar(seed + 1.5),
                b: pybamm.Vector(np.array([seed, seed + 1])),
                c: a * pybamm.Scalar(seed + 2),
            }
            out = disc.process_dict(eqns, ics=True)
        elif mode == "mixed_expression":
            eqns = {
                a: (b[0] if hasattr(b, "__getitem__") else b) + pybamm.Scalar(seed),
                b: pybamm.Vector(np.array([seed + 2, seed + 3])),
                c: pybamm.maximum(a, pybamm.Scalar(seed / 2)),
            }
            out = disc.process_dict(eqns, ics=False)
        else:
            eqns = {
                f"summary {seed}": pybamm.cos(a) + pybamm.Scalar(seed),
                a: pybamm.Scalar(seed - 0.125),
                c: a + pybamm.Scalar(seed / 3),
            }
            out = disc.process_dict(eqns, ics=True)
        assert len(out) == len(eqns)
        assert all(hasattr(value, "shape") for value in out.values())
        return out

    def test_case_01(self): assert len(self._process(1, "scalar_rhs")) == 3
    def test_case_02(self): assert len(self._process(2, "scaled_ics")) == 3
    def test_case_03(self): assert len(self._process(3, "mixed_expression")) == 3
    def test_case_04(self): assert len(self._process(4, "string_key")) == 3
    def test_case_05(self): assert len(self._process(5, "scaled_ics")) == 3
    def test_case_06(self): assert len(self._process(6, "scalar_rhs")) == 3
    def test_case_07(self): assert len(self._process(7, "string_key")) == 3
    def test_case_08(self): assert len(self._process(8, "mixed_expression")) == 3
    def test_case_09(self): assert len(self._process(9, "scaled_ics")) == 3
    def test_case_10(self): assert len(self._process(10, "scalar_rhs")) == 3
