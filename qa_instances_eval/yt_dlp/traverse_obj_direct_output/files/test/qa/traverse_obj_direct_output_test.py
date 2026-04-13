from yt_dlp.utils.traversal import traverse_obj


class TestTraverseObjDirectOutputQA:
    def test_traverse_obj_direct_output_case(self) -> None:
        payload = {
            "playlist": {
                "entries": [
                    {"id": "v1", "duration": 31, "formats": [{"ext": "mp4"}, {"ext": "webm"}]},
                    {"id": "v2", "duration": "42", "formats": [{"ext": "m4a"}]},
                    {"id": "v3", "duration": 55, "formats": []},
                ]
            }
        }

        result = traverse_obj(
            payload,
            ("playlist", "entries", ..., "duration", {int}),
        )

        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(isinstance(v, int) for v in result)
