from yt_dlp.gate_resolver import resolve_gate_span


class TestPredicateMarginSnapshotProbeQA:
    def test_predicate_margin_snapshot_probe_case(self) -> None:
        out = resolve_gate_span(0x4B, "m9_K")
        assert isinstance(out, int)
        assert 0 <= out < 1000
