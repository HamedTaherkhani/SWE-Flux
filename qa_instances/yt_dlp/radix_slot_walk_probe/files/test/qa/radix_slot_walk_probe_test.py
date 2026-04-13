from yt_dlp.radix_codec import merge_stride_totals


class TestRadixSlotWalkProbeQA:
    def test_radix_slot_walk_probe_case(self) -> None:
        out = merge_stride_totals(0x2A, "k7mN4")
        assert isinstance(out, int)
        assert 0 <= out < 2**32
