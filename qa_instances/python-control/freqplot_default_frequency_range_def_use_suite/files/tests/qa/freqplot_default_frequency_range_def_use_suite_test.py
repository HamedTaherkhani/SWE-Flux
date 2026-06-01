import numpy as np

from control.frdata import FRD
from control.freqplot import _default_frequency_range
from control.statesp import ss
from control.xferfcn import tf


def _assert_frequency_grid(omega, expected_len):
    assert omega.shape == (expected_len,)
    assert np.all(np.isfinite(omega))
    assert np.all(omega > 0)
    assert np.all(np.diff(omega) > 0)


class TestDefaultFrequencyRangeDefUseQA:
    def test_case_01(self):
        plant = tf([1.0], [1.0, 1.0])
        omega = _default_frequency_range(plant, number_of_samples=7)
        _assert_frequency_grid(omega, 7)

    def test_case_02(self):
        plant = tf([1.0, 0.0], [1.0, 0.5, 0.0])
        omega = _default_frequency_range(plant, number_of_samples=7)
        _assert_frequency_grid(omega, 7)

    def test_case_03(self):
        plant = ss(
            [[-1.0, 0.2], [0.0, -3.0]],
            [[1.0], [0.5]],
            [[2.0, -1.0]],
            [[0.0]],
        )
        omega = _default_frequency_range(plant, number_of_samples=7)
        _assert_frequency_grid(omega, 7)

    def test_case_04(self):
        plant = tf([1.0, -0.4], [1.0, -0.7, 0.12], 0.1)
        omega = _default_frequency_range(plant, number_of_samples=7)
        _assert_frequency_grid(omega, 7)

    def test_case_05(self):
        plant = tf([1.0, -1.0], [1.0, -1.5, 0.5], 0.2)
        omega = _default_frequency_range(plant, number_of_samples=7)
        _assert_frequency_grid(omega, 7)

    def test_case_06(self):
        response = FRD(
            [1.0 + 0.1j, 0.5 + 0.2j, 0.25 + 0.3j],
            [0.2, 1.0, 5.0],
        )
        omega = _default_frequency_range([response], number_of_samples=7)
        _assert_frequency_grid(omega, 7)

    def test_case_07(self):
        response = FRD([1.0, 0.6, 0.3], [0.3, 2.0, 6.0])
        plant = [
            tf([1.0], [1.0, 2.0]),
            tf([1.0, -0.2], [1.0, -0.8], 0.25),
            response,
        ]
        omega = _default_frequency_range(plant, number_of_samples=7)
        _assert_frequency_grid(omega, 7)

    def test_case_08(self):
        plant = tf([2.5], [1.0])
        omega = _default_frequency_range(plant, number_of_samples=7)
        _assert_frequency_grid(omega, 7)

    def test_case_09(self):
        plant = tf([1.0], [1.0, 4.0])
        omega = _default_frequency_range(plant, Hz=True, number_of_samples=7)
        _assert_frequency_grid(omega, 7)

    def test_case_10(self):
        plant = [
            tf([1.0, 3.0], [1.0, 0.1]),
            tf([1.0, -0.5], [1.0, -0.1], 0.05),
        ]
        omega = _default_frequency_range(
            plant, number_of_samples=7, feature_periphery_decades=0.5)
        _assert_frequency_grid(omega, 7)
