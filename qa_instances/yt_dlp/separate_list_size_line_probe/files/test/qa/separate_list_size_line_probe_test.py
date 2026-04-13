from yt_dlp.jsinterp import JSInterpreter


class TestSeparateListSizeLineProbeQA:
    def test_separate_list_size_line_probe_case(self) -> None:
        left, right = JSInterpreter._separate_at_paren("(x+y) : tail", delim=")")
        assert isinstance(left, str)
        assert isinstance(right, str)
