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

from cfnlint.context._mappings import Mappings

_INSTANCE = {
    "Fn::Transform": {"Name": "macro1"},
    "Sizes": {
        "small": {
            "cpu": "256",
            "mem": 512,
            "flag": True,
            "absent": None,
            "config": {"deep": "x"},
        },
        "large": {
            "cpu": "1024",
            "mem": 2048,
            "tags": ["a", "b", "c"],
            "limit": 9.5,
            "tuple_v": (1, 2, 3),
        },
        "weird": {123: "ignored", "valid": "ok"},
        "Fn::Transform": {"Name": "ignored"},
    },
    "Regions": {
        "us-east-1": {"ami": "ami-1"},
        "Fn::Transform": {"Name": "y"},
        "us-west-2": {"ami": "ami-2"},
    },
    42: {"ignored": "yes"},
    "BadValue": "not a dict",
}

class TestMappingsCreateFromDictStateQA:
    def test_mappings_create_from_dict_state_case(self):
        result = Mappings.create_from_dict(_INSTANCE)
        assert result.is_transform is True
        assert "Sizes" in result.maps
        assert "Regions" in result.maps
        assert "BadValue" in result.maps
