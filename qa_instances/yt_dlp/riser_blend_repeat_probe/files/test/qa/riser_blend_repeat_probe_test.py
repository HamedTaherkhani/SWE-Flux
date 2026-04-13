from __future__ import annotations

import pytest

from yt_dlp.heft_counter import blend_quota


class TestRiserBlendRepeatQA:
    @pytest.mark.parametrize(
        ("seed", "span"),
        [
            (12, 3),
            (0x2A, 11),
            (41, 7),
            (0, 0),
            (200, 55),
            (1, 2),
            (0xFF, 0xFE),
            (16, 32),
            (42, 9),
            (8, 8),
            (50, 51),
            (13, 87),
            (22, 22),
            (6, 0x10),
            (0x80, 0x7F),
            (31, 99),
            (5, 5),
            (0x7D, 4),
        ],
    )
    def test_riser_blend_repeat_probe_cases(self, seed: int, span: int) -> None:
        r = blend_quota(seed, span)
        assert isinstance(r, int)
        assert 0 <= r <= 0xFF
