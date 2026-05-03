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
    "Resources": {
        "Fn::ForEach::Outer": [
            "X",
            ["a", "b"],
            {
                "Wrap${X}": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "Tags": {
                            "Fn::ForEach::Inner": [
                                "Y",
                                ["1", "2"],
                                {
                                    "Tag${X}${Y}": [
                                        {"Key": "k", "Value": {"Ref": "Y"}},
                                        {"Key": "kk", "Value": {"Ref": "X"}},
                                    ]
                                },
                            ]
                        }
                    },
                }
            },
        ]
    },
}

class TestLanguageExtensionsWalkMaxCallDepthQA:
    def test_language_extensions_walk_max_call_depth_case(self):
        cfn = Template("foo.yaml", _TEMPLATE, ["us-east-1"])
        transform = _Transform()
        matches, transformed = transform.transform(cfn)
        assert matches == []
        for x in ("a", "b"):
            wrap = transformed["Resources"][f"Wrap{x}"]
            tags = wrap["Properties"]["Tags"]
            assert "Fn::ForEach::Inner" not in tags
            for y in ("1", "2"):
                key = f"Tag{x}{y}"
                assert tags[key][0] == {"Key": "k", "Value": y}
                assert tags[key][1] == {"Key": "kk", "Value": x}
        assert "Fn::ForEach::Outer" not in transformed["Resources"]
