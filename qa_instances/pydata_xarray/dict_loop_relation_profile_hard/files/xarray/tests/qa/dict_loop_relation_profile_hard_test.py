from xarray.core.utils import remove_incompatible_items


class TestDictLoopRelationProfileHardQA:
    def test_dict_loop_relation_profile_hard_part_a(self) -> None:
        first = {"a": 1, "b": 2, "c": 3}
        second = {}
        remove_incompatible_items(first, second)
        assert first == {}

    def test_dict_loop_relation_profile_hard_part_b(self) -> None:
        first = {"w": 10, "x": 20, "y": 30, "z": 40}
        second = {"other": 999}
        remove_incompatible_items(first, second)
        assert first == {}
