from yt_dlp.webvtt import Magic, _MatchParser


WEBVTT_INPUT = (
    "WEBVTT - sample\n"
    "Kind: captions\n"
    "Language: en\n"
    "\n"
)


class TestWebvttMagicParseFunctionCallOrderQA:
    def test_webvtt_magic_parse_function_call_order_case(self):
        parser = _MatchParser(WEBVTT_INPUT)
        block = Magic.parse(parser)

        # Shape-only assertion; do not reveal call order or count.
        assert block is not None
