from __future__ import annotations

import pytest

from yt_dlp.bind_lane import tube_digest


class TestLaneDuSuiteProbeQA:
    @pytest.mark.parametrize(
        ("seed", "label"),
        [
            (0, ""),
            (1, "x"),
            (2, "x"),
            (0, "ab"),
            (1, "ab"),
            (3, "xy"),
            (4, "zzz"),
            (0xFE, ""),
            (0xFF, "a"),
            (7, "mn"),
            (8, "pq"),
            (9, ""),
            (10, "b"),
            (11, "cd"),
            (12, "efg"),
            (13, "h"),
            (14, "ijk"),
            (15, "l"),
            (16, "mnop"),
            (17, ""),
            (18, "qrst"),
        ],
    )
    def test_lane_du_suite_probe_cases(self, seed: int, label: str) -> None:
        r = tube_digest(seed, label)
        assert isinstance(r, int)
        assert 0 <= r <= 0xFF
