from __future__ import annotations

import pytest

from yt_dlp.voxel_route import route_cells


class TestGridPathProbeQA:
    @pytest.mark.parametrize(
        ("u", "v"),
        [
            (6, 9),
            (1, 1),
            (0, 15),
            (3, 12),
            (8, 8),
            (2, 7),
            (14, 1),
            (5, 5),
            (11, 4),
            (9, 0),
            (13, 13),
            (4, 11),
            (10, 6),
            (7, 3),
            (12, 14),
            (15, 2),
            (0, 0),
            (1, 14),
        ],
    )
    def test_grid_path_probe_cases(self, u: int, v: int) -> None:
        r = route_cells(u, v)
        assert isinstance(r, int)
        assert 0 <= r <= 0xFF
