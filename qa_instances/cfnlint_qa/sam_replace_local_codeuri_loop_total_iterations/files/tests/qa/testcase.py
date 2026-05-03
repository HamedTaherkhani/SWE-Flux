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

from cfnlint.template.transforms._sam import Transform

def _resources(n: int, kind: str = "S3") -> dict:
    out = {}
    for i in range(n):
        key = f"R{i}"
        if kind == "S3":
            out[key] = {"Type": "AWS::S3::Bucket", "Properties": {}}
        elif kind == "FN":
            out[key] = {"Type": "AWS::Serverless::Function", "Properties": {"CodeUri": "./code/"}}
        elif kind == "API":
            out[key] = {"Type": "AWS::Serverless::Api", "Properties": {}}
        elif kind == "LAYER":
            out[key] = {"Type": "AWS::Serverless::LayerVersion", "Properties": {"ContentUri": "./layer/"}}
        elif kind == "NOPROPS":
            out[key] = {"Type": "AWS::S3::Bucket"}
        elif kind == "BADPROPS":
            out[key] = {"Type": "AWS::S3::Bucket", "Properties": "not-a-dict"}
        elif kind == "NOTYPE":
            out[key] = {"Properties": {}}
        elif kind == "MIXED":
            r = i % 3
            if r == 0:
                out[key] = {"Type": "AWS::S3::Bucket", "Properties": {}}
            elif r == 1:
                out[key] = {"Type": "AWS::Serverless::Function", "Properties": {"CodeUri": "./code/"}}
            else:
                out[key] = {"Type": "AWS::Serverless::LayerVersion", "Properties": {"ContentUri": "./layer/"}}
        else:
            raise ValueError(f"unknown kind: {kind}")
    return out

def _t(template: dict) -> Transform:
    return Transform("foo.yaml", template, "us-east-1")

class TestSamReplaceLocalCodeUriLoopTotalIterationsQA:

    def test_sam_replace_local_codeuri_loop_total_iterations_case_01(self):
        _t({"Resources": _resources(10, "S3")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_02(self):
        _t({"Resources": _resources(10, "FN")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_03(self):
        _t({"Resources": _resources(10, "MIXED")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_04(self):
        _t({"Resources": _resources(10, "BADPROPS")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_05(self):
        _t({"Resources": _resources(10, "NOPROPS")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_06(self):
        _t({"Resources": _resources(5, "S3")})._replace_local_codeuri()
        _t({"Resources": _resources(5, "FN")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_07(self):
        for _ in range(5):
            _t({"Resources": _resources(2, "MIXED")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_08(self):
        for _ in range(10):
            _t({"Resources": _resources(1, "API")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_09(self):
        _t({"Resources": _resources(7, "S3")})._replace_local_codeuri()
        _t({"Resources": _resources(3, "LAYER")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_10(self):
        _t({"Resources": _resources(8, "MIXED")})._replace_local_codeuri()
        _t({"Resources": _resources(2, "S3")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_11(self):
        _t({"Resources": _resources(4, "S3")})._replace_local_codeuri()
        _t({"Resources": _resources(3, "FN")})._replace_local_codeuri()
        _t({"Resources": _resources(3, "MIXED")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_12(self):
        _t({"Resources": {}})._replace_local_codeuri()
        _t({"Resources": _resources(10, "S3")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_13(self):
        _t({"Description": "no resources here"})._replace_local_codeuri()
        _t({"Resources": _resources(10, "MIXED")})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_14(self):
        _t({"Resources": _resources(6, "MIXED")})._replace_local_codeuri()
        _t({"Resources": {}})._replace_local_codeuri()
        _t({"Resources": _resources(4, "FN")})._replace_local_codeuri()
        _t({})._replace_local_codeuri()

    def test_sam_replace_local_codeuri_loop_total_iterations_case_15(self):
        mix = {}
        for i in range(4):
            mix[f"X{i}"] = {"Type": "AWS::S3::Bucket"}
        for i in range(3):
            mix[f"Y{i}"] = {"Type": "AWS::S3::Bucket", "Properties": {}}
        for i in range(3):
            mix[f"Z{i}"] = {"Type": "AWS::Serverless::Function",
                            "Properties": {"CodeUri": "./code/"}}
        _t({"Resources": mix})._replace_local_codeuri()
