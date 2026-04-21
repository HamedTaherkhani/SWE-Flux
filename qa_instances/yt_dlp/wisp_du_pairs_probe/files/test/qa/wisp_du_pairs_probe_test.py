from __future__ import annotations

from yt_dlp.wisp_trace import fold_scalar


class TestWispDuPairsProbeQA:
    def test_wisp_du_pairs_probe_case(self) -> None:
        r = fold_scalar(20, "abc")
        assert isinstance(r, int)
        assert 0 <= r <= 0xFF
