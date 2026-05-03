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
from cfnlint.template.transforms import _language_extensions
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
    "Parameters": {
    },
    "Resources": {
        "Bucket": {"Type": "AWS::S3::Bucket"},
    },
}

def _make_cfn() -> Template:
    return Template("foo.yaml", _TEMPLATE, ["us-east-1"])

def _call(cfn: Template, ref_name_or_literal) -> None:
    obj = ["MyMap", {"Ref": ref_name_or_literal}, "v"]
    fim = _ForEachValueFnFindInMap(get_hash(obj), obj)
    try:
        fim.value(cfn, {})
    except _ResolveError:
        pass

class TestFindInMapValueFallbackLoopIterationsQA:

    def test_findinmap_value_fallback_loop_iterations_case_01(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "NotInTemplate")
        _call(cfn, "AWS::AccountId")
        assert _language_extensions._ACCOUNT_ID == "111111111111"

    def test_findinmap_value_fallback_loop_iterations_case_02(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AWS::AccountId")
        _call(cfn, "NotInTemplate")
        assert _language_extensions._ACCOUNT_ID == "111111111111"

    def test_findinmap_value_fallback_loop_iterations_case_03(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "MissingOne")
        _call(cfn, "MissingTwo")
        assert _language_extensions._ACCOUNT_ID is None

    def test_findinmap_value_fallback_loop_iterations_case_04(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "MissingX")
        _call(cfn, "AWS::AccountId")
        _call(cfn, "AWS::Region")

    def test_findinmap_value_fallback_loop_iterations_case_05(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "MissingY")
        _call(cfn, "AWS::Region")
        _call(cfn, "AWS::AccountId")

    def test_findinmap_value_fallback_loop_iterations_case_06(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AWS::Region")
        _call(cfn, "MissingZ")
        _call(cfn, "AWS::AccountId")

    def test_findinmap_value_fallback_loop_iterations_case_07(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AWS::AccountId")
        _call(cfn, "AWS::Region")
        _call(cfn, "Phantom")

    def test_findinmap_value_fallback_loop_iterations_case_08(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AWS::AccountId")
        _call(cfn, "Ghost")
        _call(cfn, "AWS::Region")

    def test_findinmap_value_fallback_loop_iterations_case_09(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AWS::Region")
        _call(cfn, "AWS::AccountId")
        _call(cfn, "Spectre")

    def test_findinmap_value_fallback_loop_iterations_case_10(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AbsentX")
        _call(cfn, "AWS::AccountId")
        _call(cfn, "AWS::AccountId")
        assert _language_extensions._ACCOUNT_ID == "111111111111"

    def test_findinmap_value_fallback_loop_iterations_case_11(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AWS::AccountId")
        _call(cfn, "AbsentY")
        _call(cfn, "AWS::AccountId")
        assert _language_extensions._ACCOUNT_ID == "111111111111"

    def test_findinmap_value_fallback_loop_iterations_case_12(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AWS::AccountId")
        _call(cfn, "AWS::AccountId")
        _call(cfn, "AbsentZ")
        assert _language_extensions._ACCOUNT_ID == "111111111111"

    def test_findinmap_value_fallback_loop_iterations_case_13(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AbsentA")
        _call(cfn, "AWS::Region")
        _call(cfn, "AWS::AccountId")
        _call(cfn, "AWS::Region")

    def test_findinmap_value_fallback_loop_iterations_case_14(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AWS::Region")
        _call(cfn, "AWS::AccountId")
        _call(cfn, "AbsentB")
        _call(cfn, "AWS::Region")

    def test_findinmap_value_fallback_loop_iterations_case_15(self):
        _language_extensions._ACCOUNT_ID = None
        cfn = _make_cfn()
        _call(cfn, "AWS::Region")
        _call(cfn, "AbsentC")
        _call(cfn, "AWS::Region")
        _call(cfn, "AWS::AccountId")
        _call(cfn, "AWS::Region")
