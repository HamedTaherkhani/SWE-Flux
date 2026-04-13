from __future__ import annotations

import pytest

from yt_dlp.latch_banner import banner_lane


class TestLatchBannerValuesQA:
    @pytest.mark.parametrize(
        ("seed", "key"),
        [
            (0, ""),
            (1, ""),
            (2, ""),
            (3, ""),
            (4, ""),
            (5, ""),
            (6, ""),
            (7, ""),
            (18, "ab"),
            (9, "zzz"),
            (20, ""),
            (13, "q"),
            (8, "abcd"),
            (15, ""),
            (100, "m"),
            (200, "n"),
            (3, "abcdef"),
            (22, "p"),
            (0x1A, "uv"),
        ],
    )
    def test_latch_banner_values_probe_cases(self, seed: int, key: str) -> None:
        r = banner_lane(seed, key)
        assert isinstance(r, int)
        assert 0 <= r <= 0xFF
