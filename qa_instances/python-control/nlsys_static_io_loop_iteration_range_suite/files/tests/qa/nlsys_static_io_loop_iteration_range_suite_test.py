import numpy as np

from control.nlsys import interconnect, nlsys


def _static_gain(name, gain):
    def update(t, x, u, params):
        return []

    def output(t, x, u, params):
        return [gain * u[0]]

    return nlsys(
        update, output, states=0, inputs=1, outputs=1,
        name=name,
    )


def _chain(length, prefix):
    systems = [_static_gain(f"{prefix}_{idx}", idx + 1) for idx in range(length)]
    connections = [[(idx, 0), (idx - 1, 0)] for idx in range(1, length)] or False
    return interconnect(
        systems, connections=connections, inplist=[(0, 0)],
        outlist=[(length - 1, 0)], inputs=1, outputs=1,
        check_unused=False, name=f"{prefix}_chain",
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


class TestStaticIOSingleSystemQA:
    def test_single_system_stabilizes_immediately(self):
        sys = _chain(1, "qa_static_one")
        ulist, ylist = _evaluate(sys, [2.0])
        assert ulist.shape == (1,)
        assert ylist[-1] == 2.0


class TestStaticIOTwoSystemChainQA:
    def test_two_system_chain(self):
        sys = _chain(2, "qa_static_two")
        ulist, ylist = _evaluate(sys, [1.25])
        assert ulist.shape == (2,)
        assert ylist[1] == 2.5


class TestStaticIOThreeSystemChainQA:
    def test_three_system_chain(self):
        sys = _chain(3, "qa_static_three")
        ulist, ylist = _evaluate(sys, [0.75])
        assert ulist.shape == (3,)
        assert ylist[2] == 4.5


class TestStaticIOFourSystemChainQA:
    def test_four_system_chain(self):
        sys = _chain(4, "qa_static_four")
        ulist, ylist = _evaluate(sys, [0.5])
        assert ulist.shape == (4,)
        assert ylist[3] == 12.0


class TestStaticIOFiveSystemChainQA:
    def test_five_system_chain(self):
        sys = _chain(5, "qa_static_five")
        ulist, ylist = _evaluate(sys, [0.2])
        assert ulist.shape == (5,)
        assert np.isclose(ylist[4], 24.0)


class TestStaticIOSixSystemChainQA:
    def test_six_system_chain(self):
        sys = _chain(6, "qa_static_six")
        ulist, ylist = _evaluate(sys, [0.1])
        assert ulist.shape == (6,)
        assert np.isclose(ylist[5], 72.0)


class TestStaticIOSevenSystemChainQA:
    def test_seven_system_chain(self):
        sys = _chain(7, "qa_static_seven")
        ulist, ylist = _evaluate(sys, [0.05])
        assert ulist.shape == (7,)
        assert np.isclose(ylist[6], 252.0)


class TestStaticIOBranchedGraphQA:
    def test_branched_feedthrough_graph(self):
        sys = _branched("qa_static_branch")
        ulist, ylist = _evaluate(sys, [1.0])
        assert ulist.shape == (5,)
        assert np.isclose(ylist[4], 420.0)


class TestStaticIOTwoSourceGraphQA:
    def test_two_external_sources_merge_late(self):
        sys = _two_source("qa_static_two_src")
        ulist, ylist = _evaluate(sys, [1.0, -0.5])
        assert ulist.shape == (6,)
        assert np.isfinite(ylist[5])


class TestStaticIOScaledLongChainQA:
    def test_long_chain_with_negative_input(self):
        sys = _chain(6, "qa_static_neg")
        ulist, ylist = _evaluate(sys, [-0.125])
        assert ulist.shape == (6,)
        assert ylist[5] == -90.0
