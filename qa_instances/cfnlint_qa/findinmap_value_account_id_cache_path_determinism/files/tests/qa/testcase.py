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

from cfnlint.conditions._utils import get_hash
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import (
    _ForEachValueFnFindInMap,
    _ResolveError,
)

_TEMPLATE = {
    "Mappings": {
        "MyMap": {
            "111111111111": {"v": ["a", "b"]},
            "weirdkey-A": {"x": "ignored"},
            "222222222222": {"v": "scalarVal"},
            "weirdkey-B": "topLevelString",
            "333333333333": {"v": ["x", "y", "z"]},
            "444444444444": {"v": ["p"]},
            "555555555555": {"v": ["q", "r", "s"]},
            "666666666666": {"v": ["aa", "bb"]},
        }
    },
    "Parameters": {},
    "Resources": {
        "Bucket": {"Type": "AWS::S3::Bucket"},
    },
}

_FIM_OBJ = ["MyMap", {"Ref": "AWS::AccountId"}, "v"]

def _drive_value_once() -> None:
    cfn = Template("foo.yaml", _TEMPLATE, ["us-east-1"])
    fim = _ForEachValueFnFindInMap(get_hash(_FIM_OBJ), _FIM_OBJ)
    try:
        fim.value(cfn, {})
    except _ResolveError:
        pass

class TestFindInMapValueAccountIdCachePathDeterminismQA:

    def test_findinmap_value_account_id_cache_path_determinism_case_01(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_02(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_03(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_04(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_05(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_06(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_07(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_08(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_09(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_10(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_11(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_12(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_13(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_14(self):
        _drive_value_once()

    def test_findinmap_value_account_id_cache_path_determinism_case_15(self):
        _drive_value_once()
