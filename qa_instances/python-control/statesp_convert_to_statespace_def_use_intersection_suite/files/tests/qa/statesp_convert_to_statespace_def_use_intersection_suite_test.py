import numpy as np

from control.statesp import StateSpace, _convert_to_statespace
from control.xferfcn import tf


def _assert_state_space(sys):
    assert isinstance(sys, StateSpace)
    assert sys.ninputs == 1
    assert sys.noutputs == 1
    assert np.all(np.isfinite(np.asarray(sys.D)))


class TestConvertToStateSpaceDefUseIntersectionQA:
    def test_case_01(self):
        plant = tf([1.0], [1.0, 2.0], name="case01")
        out = _convert_to_statespace(plant, method="scipy")
        _assert_state_space(out)

    def test_case_02(self):
        plant = tf([2.0, 1.0], [1.0, 4.0, 3.0], name="case02")
        out = _convert_to_statespace(plant, use_prefix_suffix=True, method="scipy")
        _assert_state_space(out)

    def test_case_03(self):
        plant = tf([0.5, -1.0], [1.0, 0.8, 0.25], 0.1, name="case03")
        out = _convert_to_statespace(plant, method="scipy")
        _assert_state_space(out)
        assert out.dt == 0.1

    def test_case_04(self):
        plant = tf([1.0, 0.0, 3.0], [1.0, 2.0, 5.0, 6.0], name="case04")
        out = _convert_to_statespace(plant, use_prefix_suffix=True, method="scipy")
        _assert_state_space(out)

    def test_case_05(self):
        plant = tf([-1.5, 0.25], [1.0, 3.0, 2.0], 0.25, name="case05")
        out = _convert_to_statespace(plant, method="scipy")
        _assert_state_space(out)
        assert out.dt == 0.25

    def test_case_06(self):
        plant = tf([3.0, 0.0, 1.0], [1.0, 5.0, 9.0, 7.0], name="case06")
        out = _convert_to_statespace(plant, method="scipy")
        _assert_state_space(out)

    def test_case_07(self):
        plant = tf([1.0, -0.5], [1.0, -0.1, 0.02], 0.05, name="case07")
        out = _convert_to_statespace(plant, use_prefix_suffix=True, method="scipy")
        _assert_state_space(out)
        assert out.dt == 0.05

    def test_case_08(self):
        plant = tf([4.0], [1.0, 0.4], name="case08")
        out = _convert_to_statespace(plant, method="scipy")
        _assert_state_space(out)

    def test_case_09(self):
        plant = tf([1.0, 2.0], [1.0, 2.0, 2.0], name="case09")
        out = _convert_to_statespace(plant, use_prefix_suffix=True, method="scipy")
        _assert_state_space(out)

    def test_case_10(self):
        plant = tf([0.75, -0.25], [1.0, -1.2, 0.36], 0.2, name="case10")
        out = _convert_to_statespace(plant, method="scipy")
        _assert_state_space(out)
        assert out.dt == 0.2
