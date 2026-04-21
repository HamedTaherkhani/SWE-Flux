from yt_dlp.minicurses import format_text


class TestNodeRuntimePathAfterCallQA:
    def test_node_runtime_path_after_call_case(self) -> None:
        out = format_text("status line", "bold light green on blue")
        assert isinstance(out, str)
        assert len(out) > 0
