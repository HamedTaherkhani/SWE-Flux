from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

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
from cfnlint.template.transforms import _language_extensions as _le
from cfnlint.template.transforms._language_extensions import (
    _ForEachValueFnFindInMap,
    _ResolveError,
)

def _drive_value(mapping_name: str, mapping_dict: Mapping[str, Any]) -> None:
    _le._ACCOUNT_ID = None
    template_dict = {
        "Mappings": {mapping_name: dict(mapping_dict)},
        "Parameters": {},
        "Resources": {"Bucket": {"Type": "AWS::S3::Bucket"}},
    }
    cfn = Template("foo.yaml", template_dict, ["us-east-1"])
    fim_obj = [mapping_name, {"Ref": "AWS::AccountId"}, "v"]
    fim = _ForEachValueFnFindInMap(get_hash(fim_obj), fim_obj)
    try:
        fim.value(cfn, {})
    except _ResolveError:
        pass

_FIRST_VAL = {"v": ["a", "b"]}

class TestFindInMapValueFallbackMaxLengthConditionSnapshotQA:

    def test_snapshot_case_01(self):
        _drive_value(
            "MyMap",
            {
                "111111111111": _FIRST_VAL,
                "222222222222": {"v": "scalar"},
                "extra": "unrelated",
            },
        )

    def test_snapshot_case_02(self):
        _drive_value(
            "AcctMap",
            {
                "AcctA": _FIRST_VAL,
                "AcctB": {"v": ["x", "y", "z", "q"]},
            },
        )

    def test_snapshot_case_03(self):
        _drive_value(
            "BigMap",
            {
                "kk0": _FIRST_VAL,
                "kk1": {"different_key": ["ignored"]},
                "kk2": [1, 2, 3],
            },
        )

    def test_snapshot_case_04(self):
        _drive_value(
            "TableA",
            {
                "alpha": _FIRST_VAL,
                "beta": "str-val",
                "gamma": 123,
            },
        )

    def test_snapshot_case_05(self):
        _drive_value(
            "Lookup",
            {
                "row-1": _FIRST_VAL,
                "row-2": None,
                "row-3": True,
            },
        )

    def test_snapshot_case_06(self):
        _drive_value(
            "RegionMap",
            {
                "us-east-1": _FIRST_VAL,
                "us-west-2": {"v": ["only-one"]},
                "eu-west-1": {"v": ["a", "b", "c"]},
            },
        )

    def test_snapshot_case_07(self):
        _drive_value(
            "AccountIds",
            {
                "111111111111": _FIRST_VAL,
                "999999999999": {"w": ["unused"]},
            },
        )

    def test_snapshot_case_08(self):
        _drive_value(
            "EnvMap",
            {
                "dev": _FIRST_VAL,
                "stage": {"v": {"nested": "dict"}},
                "prod": {"v": ["p1", "p2", "p3", "p4"]},
            },
        )

    def test_snapshot_case_09(self):
        _drive_value(
            "ZeroEntry",
            {
                "first": _FIRST_VAL,
                "second": {},
                "third": [],
            },
        )

    def test_snapshot_case_10(self):
        _drive_value(
            "MixMap",
            {
                "key0": _FIRST_VAL,
                "key1": "string-val",
                "key2": {"other": "ignored"},
                "key3": {"v": ["only"]},
            },
        )

    def test_snapshot_case_11(self):
        _drive_value(
            "FreshNames",
            {
                "AAAA": _FIRST_VAL,
                "BBBB": {"v": ["x"]},
                "CCCC": {"v": ["x", "y", "z"]},
                "DDDD": {"v": "scalar"},
            },
        )

    def test_snapshot_case_12(self):
        _drive_value(
            "EnvAcctMap",
            {
                "main": _FIRST_VAL,
                "secondary": {"v": ["aa", "bb", "cc"]},
            },
        )

    def test_snapshot_case_13(self):
        _drive_value(
            "RegionAcctMap",
            {
                "primary": _FIRST_VAL,
                "backup": {"v": ["x", "y"]},
                "tertiary": {"v": ["only"]},
            },
        )

    def test_snapshot_case_14(self):
        _drive_value(
            "TestMap_14",
            {
                "first_iter": _FIRST_VAL,
                "second_iter": {"v": ["one", "two", "three", "four"]},
                "third_iter": "decoy",
            },
        )

    def test_snapshot_case_15(self):
        _drive_value(
            "FinalMap",
            {
                "topkey": _FIRST_VAL,
                "midkey": {"different": ["aaa"]},
                "lowkey": {"v": ["x", "y", "z", "q", "w"]},
            },
        )
