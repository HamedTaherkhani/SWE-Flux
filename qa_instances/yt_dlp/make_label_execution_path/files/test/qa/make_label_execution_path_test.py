from yt_dlp.update import _make_label


class TestMakeLabelExecutionPathQA:
    def test_make_label_execution_path_case(self) -> None:
        out = _make_label("yt-dlp/yt-dlp", "2024.01.01", "2024.01.01")
        assert isinstance(out, str)
        assert len(out) > 0
