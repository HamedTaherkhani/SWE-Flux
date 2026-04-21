from __future__ import annotations

from yt_dlp.fault_relay import absorb_chain


class TestFaultRelayCaughtKindsQA:
    def test_fault_relay_caught_kinds_case(self) -> None:
        r = absorb_chain(0, "")
        assert isinstance(r, int)
        assert 0 <= r < 256
