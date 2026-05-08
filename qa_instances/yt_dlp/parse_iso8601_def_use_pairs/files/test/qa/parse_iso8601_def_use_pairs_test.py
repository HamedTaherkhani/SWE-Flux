from yt_dlp.utils._utils import parse_iso8601


class TestParseIso8601DefUsePairsQA:
    def test_parse_iso8601_def_use_pairs_case(self):
        parse_iso8601("2024-03-15T10:30:00.123Z")
