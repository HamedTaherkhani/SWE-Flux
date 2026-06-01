import numpy as np

from control.freqplot import _compute_curve_offset


def _curve(n, twist=0.2):
    t = np.linspace(0.0, 1.0, n)
    return (1.0 + 0.3 * t) * np.exp(1j * (twist + 4.0 * np.pi * t))


def _run(mask, twist=0.2):
    resp = _curve(len(mask), twist=twist)
    offset = _compute_curve_offset(resp, np.asarray(mask, dtype=bool), 0.35)
    assert offset.shape == (len(mask),)
    assert np.all(np.isfinite(offset))
    return offset


class TestCurveOffsetSingleScaledBlockQA:
    def test_one_middle_scaled_block(self):
        offset = _run([True, True, False, False, False, True, True], 0.1)
        assert np.any(offset > 0)


class TestCurveOffsetLeadingScaledBlockQA:
    def test_leading_scaled_block_then_regular(self):
        offset = _run([False, False, True, True, True, False, False, True], 0.3)
        assert offset.size == 8


class TestCurveOffsetAlternatingBlocksQA:
    def test_multiple_alternating_blocks(self):
        offset = _run(
            [True, True, False, False, True, False, False, True, True, False, False, True],
            0.5,
        )
        assert np.max(offset) > 0


class TestCurveOffsetAllRegularQA:
    def test_all_regular_mask(self):
        offset = _run([True] * 9, 0.7)
        assert np.allclose(offset, 0)


class TestCurveOffsetTrailingScaledQA:
    def test_trailing_scaled_region(self):
        offset = _run([True, True, False, False, True, True, False, False], 0.9)
        assert offset.size == 8


class TestCurveOffsetDenseSegmentsQA:
    def test_dense_mask_with_many_segments(self):
        offset = _run(
            [False, False, True, False, False, True, False, False, True, False, False, True],
            1.1,
        )
        assert offset.shape == (12,)


class TestCurveOffsetLongRegularRunsQA:
    def test_long_regular_runs_between_scaled_blocks(self):
        offset = _run(
            [True, True, True, True, False, False, True, True, True, False, False, True],
            1.3,
        )
        assert np.any(offset > 0)


class TestCurveOffsetTwoSeparatedScaledQA:
    def test_two_separated_scaled_blocks(self):
        offset = _run([True, False, False, True, True, False, False, True], 1.5)
        assert offset.size == 8


class TestCurveOffsetLateSingleBlockQA:
    def test_late_single_scaled_block(self):
        offset = _run([True, True, True, True, True, False, False, True, True], 1.7)
        assert np.max(offset) > 0


class TestCurveOffsetManyShortRegularQA:
    def test_many_short_regular_regions(self):
        offset = _run(
            [False, False, True, False, False, True, True, False, False, True, False, False, True],
            1.9,
        )
        assert offset.shape == (13,)
