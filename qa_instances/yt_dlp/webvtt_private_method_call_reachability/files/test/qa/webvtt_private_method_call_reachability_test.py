from yt_dlp.webvtt import parse_fragment


class TestWebvttPrivateMethodCallReachabilityQA:
    def test_webvtt_private_method_call_reachability_case(self) -> None:
        frag = (
            b"WEBVTT\n"
            b"X-TIMESTAMP-MAP=LOCAL:00:00:00.000,MPEGTS:900000\n"
            b"\n"
            b"00:00:00.000 --> 00:00:01.000\n"
            b"hello\n"
            b"\n"
        )
        blocks = list(parse_fragment(frag))
        assert blocks
