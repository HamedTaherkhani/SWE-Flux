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

from cfnlint.template import Template

def _cfn(template: dict) -> Template:
    return Template("foo.yaml", template, ["us-east-1"])

def _valid_resources(n: int) -> dict:
    out = {}
    for i in range(n):
        out[f"R{i}"] = {
            "Type": "AWS::S3::Bucket",
            "Properties": {},
            "Metadata": {
                "cfn-lint": {
                    "config": {
                        "ignore_checks": [f"E1{i:03d}", f"W3{i:03d}"]
                    }
                }
            },
        }
    return out

def _resources_without_type(n: int) -> dict:
    out = {}
    for i in range(n):
        out[f"NoType{i}"] = {"Properties": {"BucketName": f"bk-{i}"}}
    return out

def _resources_non_dict(n: int) -> dict:
    return {f"NotDict{i}": f"plain-string-{i}" for i in range(n)}

def _resources_with_null_type(n: int) -> dict:
    out = {}
    for i in range(n):
        out[f"NullType{i}"] = {"Type": None, "Properties": {}}
    return out

class TestTemplateGetDirectivesOuterLoopTotalIterationsQA:

    def test_template_get_directives_outer_loop_total_iterations_case_01(self):
        _cfn({"Resources": _valid_resources(8)}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_02(self):
        mix = {**_valid_resources(8), **_resources_without_type(5)}
        _cfn({"Resources": mix}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_03(self):
        mix = {**_valid_resources(8), **_resources_non_dict(4)}
        _cfn({"Resources": mix}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_04(self):
        mix = {**_valid_resources(8), **_resources_with_null_type(3)}
        _cfn({"Resources": mix}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_05(self):
        mix = {
            **_valid_resources(8),
            **_resources_without_type(2),
            **_resources_non_dict(2),
            **_resources_with_null_type(2),
        }
        _cfn({"Resources": mix}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_06(self):
        _cfn({"Resources": _valid_resources(4)}).get_directives()
        _cfn({"Resources": _valid_resources(4)}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_07(self):
        for _ in range(4):
            _cfn({"Resources": _valid_resources(2)}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_08(self):
        for _ in range(8):
            _cfn({"Resources": _valid_resources(1)}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_09(self):
        _cfn({"Resources": _valid_resources(5)}).get_directives()
        _cfn({"Resources": _valid_resources(3)}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_10(self):
        _cfn({"Resources": _valid_resources(7)}).get_directives()
        _cfn({"Resources": _valid_resources(1)}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_11(self):
        _cfn({"Resources": _valid_resources(3)}).get_directives()
        _cfn({"Resources": _valid_resources(3)}).get_directives()
        _cfn({"Resources": _valid_resources(2)}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_12(self):
        _cfn({"Description": "no resources here"}).get_directives()
        _cfn({"Resources": _valid_resources(8)}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_13(self):
        _cfn({"Resources": {}}).get_directives()
        _cfn({"Resources": _valid_resources(8)}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_14(self):
        _cfn({"Resources": _resources_without_type(20)}).get_directives()
        _cfn({"Resources": _valid_resources(8)}).get_directives()

    def test_template_get_directives_outer_loop_total_iterations_case_15(self):
        _cfn({"Resources": _valid_resources(3)}).get_directives()
        _cfn({"Resources": _resources_with_null_type(10)}).get_directives()
        _cfn({"Resources": _valid_resources(5)}).get_directives()
        _cfn({}).get_directives()
