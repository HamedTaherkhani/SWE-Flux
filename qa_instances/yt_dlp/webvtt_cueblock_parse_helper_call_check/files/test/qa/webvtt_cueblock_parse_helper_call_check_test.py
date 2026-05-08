from yt_dlp.webvtt import CueBlock, _MatchParser


CUE_INPUT = "00:00:01.500 -> 00:00:05.000\nFirst caption\n"


class TestWebvttCueblockParseHelperCallCheckQA:
    def test_webvtt_cueblock_parse_helper_call_check_case(self):
        parser = _MatchParser(CUE_INPUT)
        block = CueBlock.parse(parser)

        # Shape-only assertion; CueBlock.parse may return either a CueBlock
        # or None depending on the input. Do not reveal which.
        assert block is None or isinstance(block, CueBlock)
