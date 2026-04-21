from __future__ import annotations

import pytest

from yt_dlp.knot_table import resolve_knot


class TestTwineCoveredLinesQA:
    @pytest.mark.parametrize(
        ("warp", "weft", "tag"),
        [
            (0, "", ""),
            (1, "", "x"),
            (2, "z", ""),
            (3, "ab", "t"),
            (4, "cd", ""),
            (5, "", "yy"),
            (6, "m", "n"),
            (7, "pq", "r"),
            (8, "st", ""),
            (0x1F, "", ""),
            (10, "u", "vw"),
            (11, "xy", "z"),
            (12, "AAA", ""),
            (13, "", "bbb"),
            (14, "c", ""),
            (15, "de", "f"),
            (16, "", ""),
            (17, "gh", "ij"),
        ],
    )
    def test_twine_covered_lines_probe_cases(self, warp: int, weft: str, tag: str) -> None:
        r = resolve_knot(warp, weft, tag)
        assert isinstance(r, int)
        assert 0 <= r <= 0xFF
