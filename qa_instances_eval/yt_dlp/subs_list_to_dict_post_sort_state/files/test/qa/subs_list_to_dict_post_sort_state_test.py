import copy

from yt_dlp.utils.traversal import subs_list_to_dict


SUBS_INPUT = [
    {"url": "http://ex.com/a.vtt", "ext": "vtt", "id": "en", "quality": 5},
    {"url": "http://ex.com/b.vtt", "ext": "vtt", "id": "en", "quality": 0},
    {"url": "http://ex.com/c.vtt", "ext": "vtt", "id": "en"},
    {"url": "invalid", "data": "<srt>...", "id": "es", "quality": 7},
    {"data": "<vtt>...", "ext": 42, "quality": 2},
    {"url": "https://ex.com/sub.srt", "id": "fr", "ext": "srt", "quality": -3},
]


class TestSubsListToDictPostSortStateQA:
    def test_subs_list_to_dict_post_sort_state_case(self):
        subs = copy.deepcopy(SUBS_INPUT)
        result = subs_list_to_dict(subs, ext="vtt")

        # Shape-only assertions; do not reveal mid-loop or final values.
        assert isinstance(result, dict)
        assert all(isinstance(k, str) for k in result)
        assert all(isinstance(v, list) for v in result.values())
