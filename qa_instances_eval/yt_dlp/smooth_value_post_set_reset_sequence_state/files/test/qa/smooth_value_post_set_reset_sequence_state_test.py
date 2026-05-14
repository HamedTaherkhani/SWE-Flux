from yt_dlp.utils.progress import SmoothValue


class TestSmoothValuePostSetResetSequenceStateQA:
    def test_smooth_value_post_set_reset_sequence_state_case(self):
        sv = SmoothValue(2.0, 0.6)
        sv.set(10.0)
        sv.set(20.0)
        sv.set(5.0)
        sv.reset()
        sv.set(100.0)
        sv.set(50.0)
        sv.set(25.0)
        final_value = sv.value
        final_smooth = sv.smooth
        final_initial = sv._initial
        final_smoothing = sv._smoothing
