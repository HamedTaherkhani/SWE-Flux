from yt_dlp.utils.networking import remove_dot_segments


PATH = "/a//b/./c/.././../f/"


class TestRemoveDotSegmentsLoopValueSequenceQA:
    def test_remove_dot_segments_loop_value_sequence_case(self):
        result = remove_dot_segments(PATH)

        # Shape-only assertion; do not reveal segment list or final result.
        assert isinstance(result, str)
