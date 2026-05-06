import pytest

from yt_dlp.webvtt import parse_fragment


WEBVTT_BYTES = (
    b"WEBVTT - sample file\n"
    b"X-TIMESTAMP-MAP=LOCAL:00:00:00.000,MPEGTS:900000\n"
    b"\n"
    b"NOTE\n"
    b"This is a note before any cue\n"
    b"\n"
    b"00:00:01.500 --> 00:00:05.000 align:start position:30%\n"
    b"First caption\n"
    b"\n"
    b"BAD_LINE_NOT_A_CUE\n"
)


class TestWebvttParseFragmentUncaughtExceptionQA:
    def test_webvtt_parse_fragment_uncaught_exception_case(self):
        with pytest.raises(Exception):
            list(parse_fragment(WEBVTT_BYTES))
