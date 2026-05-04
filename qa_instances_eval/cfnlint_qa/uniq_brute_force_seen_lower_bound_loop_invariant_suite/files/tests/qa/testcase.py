from __future__ import annotations

import sys
from pathlib import Path

def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "src" / "cfnlint").is_dir():
            return p
    raise RuntimeError("Could not locate cfnlint source tree (expected .../src/cfnlint).")

_REPO_ROOT = _find_repo_root()
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from cfnlint.jsonschema._utils import uniq

class TestUniqBruteForceSeenLowerBoundLoopInvariantSuiteQA:

    def test_int_and_dict_mix(self):
        assert uniq([1, {"a": 1}]) is True

    def test_str_and_dict_mix(self):
        assert uniq(["x", {"a": 1}, "y"]) is True

    def test_int_dict_str_mix(self):
        assert uniq([1, {"a": 1}, "x", 2, {"b": 2}, "y"]) is True

    def test_int_and_list_mix(self):
        assert uniq([1, [1, 2], 2, [3, 4]]) is True

    def test_str_and_list_mix(self):
        assert uniq(["a", [1], "b", [2]]) is True

    def test_dict_and_list_mix(self):
        assert uniq([{"a": 1}, [1, 2], {"b": 2}, [3, 4]]) is True

    def test_duplicate_dict_late(self):
        assert uniq([1, "x", {"a": 1}, "y", {"a": 1}]) is False

    def test_duplicate_list_late(self):
        assert uniq([1, "x", [1, 2], "y", [1, 2]]) is False

    def test_duplicate_at_iter_three(self):
        assert uniq([1, "x", {"k": "v"}, {"k": "v"}, "z"]) is False

    def test_duplicate_at_iter_six(self):
        assert uniq(
            [1, "x", {"a": 1}, [1], "y", {"b": 2}, [1]]
        ) is False

    def test_bool_int_dict_mix(self):
        assert uniq([True, 1, {"a": 1}, False, 0]) is True

    def test_bool_dict_only_pair(self):
        assert uniq([True, {"a": 1}]) is True

    def test_volume_eight_unsortable_no_duplicate(self):
        assert uniq(
            [1, {"a": 1}, "x", [1], 2, {"b": 2}, "y", [2]]
        ) is True

    def test_volume_ten_unsortable_no_duplicate(self):
        assert uniq(
            [1, "x", {"a": 1}, [1], 2, "y", {"b": 2}, [2], 3, [3]]
        ) is True

    def test_volume_twelve_with_duplicate_at_end(self):
        assert uniq(
            [1, "x", {"a": 1}, [1], 2, "y", {"b": 2}, [2], 3, [3], "z", "x"]
        ) is False

    def test_single_dict_no_iterations_in_inner(self):
        assert uniq([{"a": 1}]) is True

    def test_two_dicts_distinct(self):
        assert uniq([{"a": 1}, {"b": 2}]) is True

    def test_two_dicts_equal(self):
        assert uniq([{"a": 1}, {"a": 1}]) is False

    def test_two_lists_distinct(self):
        assert uniq([[1, 2], [3, 4]]) is True

    def test_two_lists_equal(self):
        assert uniq([[1, 2], [1, 2]]) is False

    def test_empty_container_no_iterations(self):
        assert uniq([]) is True
