from __future__ import annotations

import pytest

from yt_dlp.raster_stride import stride_snap


class TestStrideRepeatProbeQA:
    @pytest.mark.parametrize(
        ("a", "b"),
        [
            (3, 14),
            (19, 5),
            (0, 0),
            (0x2C, 1),
            (7, 7),
            (11, 0xFD),
            (200, 55),
            (1, 2),
            (0xFF, 0xFF),
            (16, 32),
            (42, 9),
            (8, 8),
            (50, 51),
            (13, 87),
            (22, 22),
            (6, 0x10),
            (0x80, 0x7F),
            (31, 99),
        ],
    )
    def test_stride_repeat_probe_cases(self, a: int, b: int) -> None:
        r = stride_snap(a, b)
        assert isinstance(r, int)
        assert 0 <= r <= 0xFF
