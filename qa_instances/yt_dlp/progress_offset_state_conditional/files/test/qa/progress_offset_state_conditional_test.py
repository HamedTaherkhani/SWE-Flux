from yt_dlp.utils.progress import ProgressCalculator


class TestProgressOffsetStateConditionalQA:
    def test_progress_offset_state_conditional_case(self) -> None:
        pc = ProgressCalculator(initial=10)
        pc.total = 20
        pc.thread_reset()

        # Ensure _update does not early-return on sampling rate gate.
        pc._last_update = 0
        pc.update(16)

        assert pc.downloaded == 26
