import numpy as np
import pytest

from control.nlsys import interconnect, nlsys


def _static_gain(name, gain):
    def update(t, x, u, params):
        return []

    def output(t, x, u, params):
        return [gain * u[0]]

    return nlsys(update, output, states=0, inputs=1, outputs=1, name=name)


def _chain(length, prefix):
    systems = [_static_gain(f"{prefix}_{idx}", 1.0 + 0.25 * idx)
               for idx in range(length)]
    connections = [[(idx, 0), (idx - 1, 0)] for idx in range(1, length)] or False
    return interconnect(
        systems, connections=connections, inplist=[(0, 0)],
        outlist=[(length - 1, 0)], inputs=1, outputs=1,
        check_unused=False, name=f"{prefix}_chain",
    )


def _parallel(length, prefix):
    systems = [_static_gain(f"{prefix}_{idx}", 0.5 + idx)
               for idx in range(length)]
    return interconnect(
        systems, connections=False,
        inplist=[(idx, 0) for idx in range(length)],
        outlist=[(idx, 0) for idx in range(length)],
        inputs=length, outputs=length, check_unused=False,
        name=f"{prefix}_parallel",
    )


def _fanout(prefix):
    systems = [_static_gain(f"{prefix}_{idx}", idx + 1.0) for idx in range(5)]
    connections = [
        [(1, 0), (0, 0)],
        [(2, 0), (0, 0)],
        [(3, 0), (1, 0), (2, 0)],
        [(4, 0), (3, 0)],
    ]
    return interconnect(
        systems, connections=connections, inplist=[(0, 0)],
        outlist=[(2, 0), (4, 0)], inputs=1, outputs=2,
        check_unused=False, name=f"{prefix}_fanout",
    )


def _feedback(prefix, gain_a, gain_b):
    systems = [
        _static_gain(f"{prefix}_a", gain_a),
        _static_gain(f"{prefix}_b", gain_b),
    ]
    return interconnect(
        systems,
        connections=[[(0, 0), (1, 0)], [(1, 0), (0, 0)]],
        inplist=[(0, 0)], outlist=[(1, 0)], inputs=1, outputs=1,
        check_unused=False, name=f"{prefix}_feedback",
    )


def _evaluate(sys, u):
    ulist, ylist = sys._compute_static_io(0.0, np.zeros(sys.nstates), u)
    assert np.all(np.isfinite(ulist))
    assert np.all(np.isfinite(ylist))
    return ulist, ylist


class TestStaticIOStateRangeQA:
    def test_case_01(self):
        ulist, ylist = _evaluate(_parallel(1, "case_01"), [2.0])
        assert ulist.shape == (1,)
        assert ylist[0] == 1.0

    def test_case_02(self):
        ulist, ylist = _evaluate(_parallel(6, "case_02"), [1, 2, 3, 4, 5, 6])
        assert ulist.shape == (6,)
        assert ylist.shape[0] == 12

    def test_case_03(self):
        ulist, ylist = _evaluate(_chain(3, "case_03"), [0.75])
        assert ulist.shape == (3,)
        assert np.isfinite(ylist[-1])

    def test_case_04(self):
        with pytest.raises(RuntimeError, match="algebraic loop"):
            _evaluate(_feedback("case_04", 0.5, 0.75), [1.0])

    def test_case_05(self):
        ulist, ylist = _evaluate(_fanout("case_05"), [0.5])
        assert ulist.shape == (5,)
        assert ylist.shape[0] == 10

    def test_case_06(self):
        ulist, ylist = _evaluate(_chain(5, "case_06"), [-0.25])
        assert ulist.shape == (5,)
        assert np.isfinite(ylist[-1])

    def test_case_07(self):
        ulist, ylist = _evaluate(_parallel(4, "case_07"), [0.1, -0.2, 0.3, -0.4])
        assert ulist.shape == (4,)
        assert np.all(np.isfinite(ylist))

    def test_case_08(self):
        with pytest.raises(RuntimeError, match="algebraic loop"):
            _evaluate(_feedback("case_08", -0.4, 0.25), [1.0])

    def test_case_09(self):
        ulist, ylist = _evaluate(_chain(1, "case_09"), [3.0])
        assert ulist.shape == (1,)
        assert ylist[0] == 3.0

    def test_case_10(self):
        ulist, ylist = _evaluate(_chain(7, "case_10"), [0.125])
        assert ulist.shape == (7,)
        assert np.isfinite(ylist[-1])
