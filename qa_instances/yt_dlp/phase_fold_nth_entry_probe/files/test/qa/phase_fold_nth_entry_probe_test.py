from yt_dlp.phase_coupler import fold_phase_edges


class TestPhaseFoldNthEntryProbeQA:
    def test_phase_fold_nth_entry_probe_case(self) -> None:
        out = fold_phase_edges(0x55, "pqR")
        assert isinstance(out, int)
        assert 0 <= out < 256
