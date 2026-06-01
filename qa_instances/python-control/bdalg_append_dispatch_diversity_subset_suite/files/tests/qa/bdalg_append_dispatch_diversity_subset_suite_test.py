import numpy as np

from control.bdalg import append
from control.frdata import FRD
from control.statesp import ss
from control.xferfcn import tf


def _ss_a(dt=0):
    return ss(
        [[-1.0, 0.2], [0.0, -2.0]],
        [[1.0], [0.5]],
        [[0.0, 1.0]],
        [[0.1]],
        dt=dt,
    )


def _ss_b(dt=0):
    return ss(
        [[-3.0]],
        [[2.0]],
        [[-0.5]],
        [[0.0]],
        dt=dt,
    )


def _tf_a(dt=0):
    if dt:
        return tf([0.4, 0.2], [1.0, -0.3], dt)
    return tf([1.0, 0.5], [1.0, 2.0, 1.5])


def _omega():
    return np.array([0.3, 0.8, 1.7, 3.5])


def _frd_a():
    omega = _omega()
    return FRD(1.0 / (1.0 + 1j * omega), omega)


def _frd_b():
    omega = _omega()
    return FRD((0.5 + 0.1j * omega) / (2.0 + 1j * omega), omega)


class TestAppendStateSpacePairQA:
    def test_state_space_first_with_state_space_second(self):
        combined = append(_ss_a(), _ss_b())
        assert combined.nstates == 3
        assert combined.ninputs == 2
        assert combined.noutputs == 2


class TestAppendStateSpaceWithTransferFunctionQA:
    def test_state_space_first_converts_transfer_function_second(self):
        combined = append(_ss_a(), _tf_a())
        assert combined.ninputs == 2
        assert combined.noutputs == 2
        assert combined.nstates >= 3


class TestAppendStateSpaceTripleQA:
    def test_state_space_first_multiple_operands(self):
        combined = append(_ss_a(), _ss_b(), _ss_b())
        assert combined.nstates == 4
        assert combined.ninputs == 3
        assert combined.noutputs == 3


class TestAppendStateSpaceDiscreteQA:
    def test_discrete_state_space_operands(self):
        combined = append(_ss_a(dt=0.25), _ss_b(dt=0.25))
        assert combined.dt == 0.25
        assert combined.nstates == 3


class TestAppendStateSpaceWithNamesQA:
    def test_state_space_append_then_wrapper_updates_names(self):
        combined = append(
            _ss_a(), _tf_a(),
            inputs=["ua", "ub"],
            outputs=["ya", "yb"],
            name="qa_appended_ss",
        )
        assert combined.name == "qa_appended_ss"
        assert combined.input_labels == ["ua", "ub"]
        assert combined.output_labels == ["ya", "yb"]


class TestAppendFRDPairQA:
    def test_frd_first_with_frd_second(self):
        combined = append(_frd_a(), _frd_b())
        assert combined.frdata.shape == (2, 2, 4)
        assert combined.ninputs == 2
        assert combined.noutputs == 2


class TestAppendFRDWithTransferFunctionQA:
    def test_frd_first_converts_transfer_function_second(self):
        combined = append(_frd_a(), _tf_a())
        assert combined.frdata.shape == (2, 2, 4)
        assert np.all(np.isfinite(combined.frdata))


class TestAppendFRDWithStateSpaceQA:
    def test_frd_first_converts_state_space_second(self):
        combined = append(_frd_b(), _ss_b())
        assert combined.frdata.shape == (2, 2, 4)
        assert combined.omega.size == 4


class TestAppendFRDTripleQA:
    def test_frd_first_multiple_operands(self):
        combined = append(_frd_a(), _frd_b(), _tf_a())
        assert combined.frdata.shape == (3, 3, 4)
        assert combined.ninputs == 3
        assert combined.noutputs == 3


class TestAppendFRDWithNamesQA:
    def test_frd_append_then_wrapper_updates_names(self):
        combined = append(
            _frd_a(), _frd_b(),
            inputs=["uf0", "uf1"],
            outputs=["yf0", "yf1"],
            name="qa_appended_frd",
        )
        assert combined.name == "qa_appended_frd"
        assert combined.input_labels == ["uf0", "uf1"]
        assert combined.output_labels == ["yf0", "yf1"]
