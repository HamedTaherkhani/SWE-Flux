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
from cfnlint.template.transforms._language_extensions import (
    _Transform,
)

_TEMPLATE = {
    "Transform": "AWS::LanguageExtensions",
    "Conditions": {"c": {"Fn::Equals": ["a", "a"]}},
    "Mappings": {
        "M": {
            "X": {"v": "alpha"},
            "Y": {"v": "beta"},
        },
        "N": {
            "k": {"out": "X"},
        },
    },
    "Resources": {
        "Fn::ForEach::L": [
            "L",
            ["X", "Y"],
            {
                "Bucket${L}": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "Mapped": {
                            "Fn::FindInMap": ["M", {"Ref": "L"}, "v"]
                        },
                        "Mapped2": {
                            "Fn::FindInMap": [
                                "M",
                                {"Fn::If": ["c", "X", "Y"]},
                                "v",
                            ]
                        },
                        "Mapped3": {
                            "Fn::FindInMap": [
                                "M",
                                {"Fn::FindInMap": ["N", "k", "out"]},
                                "v",
                            ]
                        },
                    },
                }
            },
        ]
    },
}

class TestLanguageExtensionsForEachValueCreateDispatchQA:
    def test_language_extensions_foreach_value_create_dispatch_case(self):
        cfn = Template("foo.yaml", _TEMPLATE, ["us-east-1"])
        transform = _Transform()
        matches, transformed = transform.transform(cfn)
        assert matches == []
        for letter in ("X", "Y"):
            props = transformed["Resources"][f"Bucket{letter}"]["Properties"]
            assert props["Mapped"] == ("alpha" if letter == "X" else "beta")
            assert props["Mapped2"] == "beta"
            assert props["Mapped3"] == "alpha"
