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
from cfnlint.template.transforms._language_extensions import _Transform

_TEMPLATE = {
    "Transform": "AWS::LanguageExtensions",
    "Parameters": {},
    "Resources": {
        "Fn::ForEach::L": [
            "L",
            [
                {"Ref": "UnresolvableParam"},
                {"Ref": "AnotherUnresolvableParam"},
            ],
            {
                "Bucket${L}": {
                    "Type": "AWS::S3::Bucket",
                }
            },
        ]
    },
}

def _drive_transform_once() -> None:
    cfn = Template("foo.yaml", _TEMPLATE, ["us-east-1"])
    _Transform().transform(cfn)

class TestTransformWalkRandomForEachPathDeterminismQA:

    def test_transform_walk_random_foreach_path_determinism_case_01(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_02(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_03(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_04(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_05(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_06(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_07(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_08(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_09(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_10(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_11(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_12(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_13(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_14(self):
        _drive_transform_once()

    def test_transform_walk_random_foreach_path_determinism_case_15(self):
        _drive_transform_once()
