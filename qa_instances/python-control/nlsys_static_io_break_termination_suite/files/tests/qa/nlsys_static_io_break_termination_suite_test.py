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
    systems = [_static_gain(f"{prefix}_{idx}", idx + 1) for idx in range(length)]
    connections = [[(idx, 0), (idx - 1, 0)] for idx in range(1, length)] or False
    return interconnect(
        systems, connections=connections, inplist=[(0, 0)],
        outlist=[(length - 1, 0)], inputs=1, outputs=1,
        check_unused=False, name=f"{prefix}_chain",
    )


def _self_loop(prefix, gain):
    system = _static_gain(f"{prefix}_sys", gain)
    return interconnect(
        [system], connections=[[(0, 0), (0, 0)]],
        inplist=[(0, 0)], outlist=[(0, 0)], inputs=1, outputs=1,
        check_unused=False, name=f"{prefix}_self_loop",
    )


def _two_system_cycle(prefix, gain_a, gain_b):
    systems = [
        _static_gain(f"{prefix}_a", gain_a),
        _static_gain(f"{prefix}_b", gain_b),
    ]
    return interconnect(
        systems,
        connections=[[(0, 0), (1, 0)], [(1, 0), (0, 0)]],
        inplist=[(0, 0)], outlist=[(1, 0)], inputs=1, outputs=1,
        check_unused=False, name=f"{prefix}_cycle",
    )


def _branched(prefix):
    systems = [_static_gain(f"{prefix}_{idx}", idx + 2) for idx in range(5)]
    connections = [
        [(1, 0), (0, 0)],
        [(2, 0), (0, 0)],
        [(3, 0), (1, 0), (2, 0)],
        [(4, 0), (3, 0)],
    ]
    return interconnect(
        systems, connections=connections, inplist=[(0, 0)],
        outlist=[(4, 0)], inputs=1, outputs=1,
        check_unused=False, name=f"{prefix}_branched",
    )


def _two_source(prefix):
    systems = [_static_gain(f"{prefix}_{idx}", idx + 1.5) for idx in range(6)]
    connections = [
        [(2, 0), (0, 0)],
        [(3, 0), (1, 0)],
        [(4, 0), (2, 0), (3, 0)],
        [(5, 0), (4, 0)],
    ]
    return interconnect(
        systems, connections=connections,
        inplist=[(0, 0), (1, 0)], outlist=[(5, 0)],
        inputs=2, outputs=1, check_unused=False,
        name=f"{prefix}_two_source",
    )


def _evaluate(sys, u):
    ulist, ylist = sys._compute_static_io(0.0, np.zeros(sys.nstates), u)
    assert np.all(np.isfinite(ulist))
    assert np.all(np.isfinite(ylist))
    return ulist, ylist


class TestStaticIOTerminationQA:
    def test_case_01(self):
        sys = _chain(1, "case_01")
        ulist, ylist = _evaluate(sys, [2.0])
        assert ulist.shape == (1,)
        assert ylist[-1] == 2.0

    def test_case_02(self):
        sys = _chain(3, "case_02")
        ulist, ylist = _evaluate(sys, [0.75])
        assert ulist.shape == (3,)
        assert np.isclose(ylist[2], 4.5)

    def test_case_03(self):
        sys = _self_loop("case_03", 0.5)
        with pytest.raises(RuntimeError, match="algebraic loop"):
            _evaluate(sys, [1.0])

    def test_case_04(self):
        sys = _self_loop("case_04", 0.0)
        ulist, ylist = _evaluate(sys, [1.0])
        assert ulist.shape == (1,)
        assert ylist[0] == 0.0

    def test_case_05(self):
        sys = _self_loop("case_05", 1.0)
        with pytest.raises(RuntimeError, match="algebraic loop"):
            _evaluate(sys, [1.0])

    def test_case_06(self):
        sys = _branched("case_06")
        ulist, ylist = _evaluate(sys, [1.0])
        assert ulist.shape == (5,)
        assert np.isclose(ylist[4], 420.0)

    def test_case_07(self):
        sys = _two_system_cycle("case_07", 0.5, 0.75)
        with pytest.raises(RuntimeError, match="algebraic loop"):
            _evaluate(sys, [1.0])

    def test_case_08(self):
        sys = _two_source("case_08")
        ulist, ylist = _evaluate(sys, [1.0, -0.5])
        assert ulist.shape == (6,)
        assert np.isfinite(ylist[5])

    def test_case_09(self):
        sys = _two_system_cycle("case_09", -0.5, 0.75)
        with pytest.raises(RuntimeError, match="algebraic loop"):
            _evaluate(sys, [1.0])

    def test_case_10(self):
        sys = _chain(6, "case_10")
        ulist, ylist = _evaluate(sys, [-0.125])
        assert ulist.shape == (6,)
        assert np.isclose(ylist[5], -90.0)
