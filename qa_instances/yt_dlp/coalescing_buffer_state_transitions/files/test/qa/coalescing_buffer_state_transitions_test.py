from yt_dlp.coalescing_buffer import schedule_window_merge


class TestCoalescingBufferStateTransitionsQA:
    def test_coalescing_buffer_state_transitions_case(self) -> None:
        out = schedule_window_merge(6, "xYz9")
        assert isinstance(out, str)
        assert len(out) >= 4
