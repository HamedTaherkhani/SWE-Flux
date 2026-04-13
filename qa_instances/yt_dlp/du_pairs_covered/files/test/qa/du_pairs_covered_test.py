from yt_dlp.dupairs import analyze_payload


class TestDUPairsCoveredQA:
    def test_du_pairs_covered_case(self) -> None:
        payload = "  Alpha alpha BETA 12 12 7 gamma DELTA  "
        out = analyze_payload(payload)
        assert isinstance(out, int)
        assert 0 <= out < 65536

