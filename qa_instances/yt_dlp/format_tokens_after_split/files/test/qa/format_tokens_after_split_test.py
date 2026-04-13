from yt_dlp.minicurses import format_text


class TestFormatTokensAfterSplitQA:
    def test_format_tokens_after_split_case(self) -> None:
        out = format_text("status line", "bold light green on blue")
        assert isinstance(out, str)
        assert len(out) > 0
