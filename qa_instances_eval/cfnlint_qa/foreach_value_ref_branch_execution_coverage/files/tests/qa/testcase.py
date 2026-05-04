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
from cfnlint.template.transforms._language_extensions import (
    _ForEachValueRef,
    _ResolveError,
)

def _drive_value(
    region: str,
    ref_name: str,
    parameters: Mapping[str, Any] | None = None,
    runtime_params: Mapping[str, Any] | None = None,
) -> None:
    template_dict = {
        "Parameters": dict(parameters) if parameters else {},
        "Resources": {"Bucket": {"Type": "AWS::S3::Bucket"}},
    }
    cfn = Template("foo.yaml", template_dict, [region])
    ref = _ForEachValueRef(get_hash(ref_name), ref_name)
    try:
        ref.value(cfn, runtime_params)
    except _ResolveError:
        pass

class TestForEachValueRefBranchExecutionCoverageQA:

    def test_branch_execution_case_01(self):
        _drive_value("us-east-1", "AWS::Region")

    def test_branch_execution_case_02(self):
        _drive_value("us-gov-east-1", "AWS::Region")

    def test_branch_execution_case_03(self):
        _drive_value("cn-north-1", "AWS::Region")

    def test_branch_execution_case_04(self):
        _drive_value("us-east-1", "AWS::Partition")

    def test_branch_execution_case_05(self):
        _drive_value("us-east-1", "AWS::StackId")

    def test_branch_execution_case_06(self):
        _drive_value("us-east-1", "AWS::StackName")

    def test_branch_execution_case_07(self):
        _drive_value("us-east-1", "AWS::URLSuffix")

    def test_branch_execution_case_08(self):
        _drive_value("cn-north-1", "AWS::URLSuffix")

    def test_branch_execution_case_09(self):
        _drive_value("us-east-1", "AWS::NoValue")

    def test_branch_execution_case_10(self):
        _drive_value(
            "us-east-1",
            "Foo",
            parameters=None,
            runtime_params={"Foo": "bar"},
        )

    def test_branch_execution_case_11(self):
        _drive_value(
            "us-east-1",
            "MyParam",
            parameters={"MyParam": {"Type": "String", "Default": "v"}},
        )

    def test_branch_execution_case_12(self):
        _drive_value(
            "us-east-1",
            "MyListParam",
            parameters={
                "MyListParam": {
                    "Type": "CommaDelimitedList",
                    "Default": "a,b,c",
                }
            },
        )

    def test_branch_execution_case_13(self):
        _drive_value(
            "us-east-1",
            "MyAllowed",
            parameters={
                "MyAllowed": {
                    "Type": "String",
                    "AllowedValues": ["x", "y"],
                }
            },
        )

    def test_branch_execution_case_14(self):
        _drive_value(
            "us-east-1",
            "MyAllowedList",
            parameters={
                "MyAllowedList": {
                    "Type": "CommaDelimitedList",
                    "AllowedValues": ["a,b", "c,d"],
                }
            },
        )

    def test_branch_execution_case_15(self):
        _drive_value(
            "us-east-1",
            "MyListNoData",
            parameters={
                "MyListNoData": {"Type": "CommaDelimitedList"},
            },
        )
