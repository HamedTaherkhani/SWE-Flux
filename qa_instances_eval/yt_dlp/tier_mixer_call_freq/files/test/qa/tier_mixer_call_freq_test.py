from __future__ import annotations

from yt_dlp.tier_mixer import merge_ticks


class TestTierMixerCallFreqQA:
    def test_tier_mixer_call_freq_case(self) -> None:
        r = merge_ticks(0x2B, ("a", "xyz", ""))
        assert isinstance(r, int)
        assert 0 <= r <= 0xFF
