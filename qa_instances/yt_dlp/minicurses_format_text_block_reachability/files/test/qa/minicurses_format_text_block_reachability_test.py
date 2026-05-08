from yt_dlp.minicurses import format_text


FORMAT_SPEC = "bold light red on cyan"


class TestMinicursesFormatTextBlockReachabilityQA:
    def test_minicurses_format_text_block_reachability_case(self):
        result = format_text("Hello", FORMAT_SPEC)

        # Shape-only assertions; do not reveal any branch outcomes.
        assert isinstance(result, str)
        assert "Hello" in result
