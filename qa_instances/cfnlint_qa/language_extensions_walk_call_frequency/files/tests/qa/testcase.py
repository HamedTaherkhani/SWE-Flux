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
    "Mappings": {
        "M": {
            "A": {"v": "alpha"},
            "B": {"v": "beta"},
            "C": {"v": "gamma"},
        }
    },
    "Resources": {
        "Fn::ForEach::L": [
            "L",
            ["A", "B", "C"],
            {
                "Bucket${L}": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "BucketName": {
                            "Fn::Sub": [
                                "pre-${L}-suf",
                                {"L": {"Ref": "L"}},
                            ]
                        },
                        "Mapped": {
                            "Fn::FindInMap": ["M", {"Ref": "L"}, "v"]
                        },
                        "Tags": [
                            {"Key": "Env", "Value": "prod"},
                            {"Key": "Letter", "Value": {"Ref": "L"}},
                        ],
                    },
                }
            },
        ]
    },
}

class TestLanguageExtensionsWalkCallFrequencyQA:
    def test_language_extensions_walk_call_frequency_case(self):
        cfn = Template("foo.yaml", _TEMPLATE, ["us-east-1"])
        transform = _Transform()
        matches, transformed = transform.transform(cfn)
        assert matches == []
        for letter in ("A", "B", "C"):
            bucket = transformed["Resources"][f"Bucket{letter}"]
            assert bucket["Type"] == "AWS::S3::Bucket"
            assert bucket["Properties"]["BucketName"] == f"pre-{letter}-suf"
            assert bucket["Properties"]["Mapped"] == (
                "alpha" if letter == "A"
                else "beta" if letter == "B"
                else "gamma"
            )
            tags = bucket["Properties"]["Tags"]
            assert tags[0] == {"Key": "Env", "Value": "prod"}
            assert tags[1] == {"Key": "Letter", "Value": letter}
        assert "Fn::ForEach::L" not in transformed["Resources"]
