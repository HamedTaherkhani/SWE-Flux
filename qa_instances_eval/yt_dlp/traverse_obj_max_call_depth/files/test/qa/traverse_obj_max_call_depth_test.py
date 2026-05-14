from yt_dlp.utils.traversal import traverse_obj


DATA = {
    "L1": [
        {"L2a": [{"k": 1}, {"k": 2}]},
        {"L2b": {"L3": [{"k": 3}]}},
    ],
}

PATH = ("L1", ..., (("L2a", ..., "k"), ("L2b", "L3", ..., "k")))


class TestTraverseObjMaxCallDepthQA:
    def test_traverse_obj_max_call_depth_case(self):
        result = traverse_obj(DATA, PATH)

        # Shape-only assertion; do not reveal the result or any depth.
        assert isinstance(result, list)
