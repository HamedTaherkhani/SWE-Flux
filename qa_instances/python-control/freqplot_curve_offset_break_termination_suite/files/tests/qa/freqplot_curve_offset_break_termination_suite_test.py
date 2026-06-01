import numpy as np

from control.freqplot import _compute_curve_offset


def _curve(n, twist):
    t = np.linspace(0.0, 1.0, n)
    wobble = 0.08 * np.sin((np.arange(n) + 1) * (twist + 0.17))
    radius = 1.0 + 0.25 * t + wobble
    phase = twist + 3.5 * np.pi * t + 0.18 * np.cos(2.0 * np.pi * t)
    return radius * np.exp(1j * phase)


def _evaluate(mask, twist):
    bool_mask = np.asarray(mask, dtype=bool)
    offset = _compute_curve_offset(_curve(bool_mask.size, twist), bool_mask, 0.32)
    assert offset.shape == (bool_mask.size,)
    assert np.all(np.isfinite(offset))
    assert np.min(offset) > -1e-12
    return offset


class TestCurveOffsetTerminationQA:
    def test_case_01(self):
        offset = _evaluate([True, True, True, True, True, True, True, True], 0.11)
        assert np.allclose(offset, 0.0)

    def test_case_02(self):
        offset = _evaluate([False, False, True, True, True, True], 0.23)
        assert offset.size == 6

    def test_case_03(self):
        offset = _evaluate([True, True, False, False, False, False], 0.37)
        assert offset.shape == (6,)

    def test_case_04(self):
        offset = _evaluate(
            [True, True, False, False, True, True, True, True],
            0.49,
        )
        assert np.any(offset > 0)

    def test_case_05(self):
        offset = _evaluate([False, False, False, False, False, False], 0.61)
        assert offset.size == 6

    def test_case_06(self):
        offset = _evaluate(
            [False, False, True, True, False, False, True, True, True],
            0.73,
        )
        assert offset.shape == (9,)

    def test_case_07(self):
        offset = _evaluate(
            [True, True, True, False, False, True, True, False, False],
            0.89,
        )
        assert offset.size == 9

    def test_case_08(self):
        offset = _evaluate(
            [True, True, False, False, True, True, False, False, True, True],
            1.03,
        )
        assert np.max(offset) > 0

    def test_case_09(self):
        offset = _evaluate(
            [False, False, True, True, True, False, False, False],
            1.17,
        )
        assert offset.shape == (8,)

    def test_case_10(self):
        offset = _evaluate(
            [
                True, True, False, False, True, True, False, False,
                True, True, True,
            ],
            1.31,
        )
        assert np.any(offset > 0)
