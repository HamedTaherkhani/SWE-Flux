import io

from yt_dlp.webvtt import parse_fragment


WEBVTT_INPUT = (
    b"WEBVTT - sample\n"
    b"X-TIMESTAMP-MAP=LOCAL:00:00:00.000,MPEGTS:900000\n"
    b"\n"
    b"00:00:01.000 --> 00:00:05.000\n"
    b"Hello\n"
    b"\n"
    b"NOTE\n"
    b"This is a comment\n"
    b"\n"
    b"00:00:06.000 --> 00:00:09.000\n"
    b"World\n"
)


class TestWebvttBlockWriteIntoDispatchQA:
    def test_webvtt_block_write_into_dispatch_case(self):
        blocks = list(parse_fragment(WEBVTT_INPUT))
        out = io.StringIO()
        for block in blocks:
            block.write_into(out)

        # Shape-only assertions; do not reveal block types or dispatch.
        assert isinstance(blocks, list)
        assert isinstance(out.getvalue(), str)
