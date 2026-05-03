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
    "Mappings": {
        "M1": {"A": {"val": "111"}, "B": {"val": "222"}},
    },
    "Resources": {
        "Fn::ForEach::Items": [
            "Letter",
            ["A", "B"],
            {
                "Server${Letter}": {
                    "Type": "AWS::EC2::Instance",
                    "Properties": {
                        "Tag": "tag-${Letter}",
                        "Name": {"Fn::Sub": "srv-${Letter}"},
                        "Subnet": {"Ref": "Letter"},
                        "Index": {"Ref": "Region"},
                        "Description": {
                            "Fn::Sub": [
                                "shared-${Letter}-${X}",
                                {"X": "extra"},
                            ]
                        },
                        "GetMap": {"Fn::FindInMap": ["M1", {"Ref": "Letter"}, "val"]},
                        "GetMissing": {
                            "Fn::FindInMap": ["M1", {"Ref": "Letter"}, "absent"]
                        },
                    },
                }
            },
        ]
    },
}

class TestTransformWalkForeachOuterStateQA:
    def test_transform_walk_foreach_outer_state_case(self):
        cfn = Template("", _TEMPLATE)
        transformer = _Transform()
        _matches, walked = transformer.transform(cfn)
        assert isinstance(walked, dict)
        assert "Resources" in walked
        assert "ServerA" in walked["Resources"]
        assert "ServerB" in walked["Resources"]
        assert "Fn::ForEach::Items" not in walked["Resources"]
