from __future__ import annotations

from yt_dlp.hinge_cascade import outer_wire


class TestShadowBlendProbeQA:
    def test_shadow_blend_probe_case(self) -> None:
        r = outer_wire(5, "ab")
        assert isinstance(r, int)
        assert 0 <= r <= 0xFF
