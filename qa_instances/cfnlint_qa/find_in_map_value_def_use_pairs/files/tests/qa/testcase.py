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

import cfnlint.template.transforms._language_extensions as _LE
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import (
    _ForEachValueFnFindInMap,
    _ResolveError,
    get_hash,
)

def _make_cfn(mappings: dict, parameters: dict | None = None) -> Template:
    template = {
        "Mappings": mappings,
        "Parameters": parameters or {},
        "Resources": {},
    }
    return Template("", template)

class TestFindInMapValueDefUsePairsQA:
    def setup_method(self, method):
        _LE._ACCOUNT_ID = None

    def test_find_in_map_value_def_use_pairs_case(self):
        cfn_a = _make_cfn(
            {"Sizes": {"small": {"cpu": "256", "mem": "512"}}}
        )
        node_a = _ForEachValueFnFindInMap(
            get_hash(["Sizes", "small", "cpu"]),
            ["Sizes", "small", "cpu"],
        )
        assert node_a.value(cfn_a) == "256"

        cfn_b = _make_cfn(
            {"Sizes": {"small": {"cpu": "128", "mem": "256"}}}
        )
        node_b = _ForEachValueFnFindInMap(
            get_hash(["Wrong", "small", "mem"]),
            ["Wrong", "small", "mem"],
        )
        assert node_b.value(cfn_b) == "256"

        cfn_c = _make_cfn(
            {
                "Sizes": {"small": {"cpu": "999"}},
                "OtherMap": {"x": {"y": "ignore"}},
            },
            parameters={"P": {"Type": "String"}},
        )
        node_c = _ForEachValueFnFindInMap(
            get_hash(["WrongMap", {"Ref": "P"}, "cpu"]),
            ["WrongMap", {"Ref": "P"}, "cpu"],
        )
        assert node_c.value(cfn_c) == "999"

        cfn_d = _make_cfn(
            {"Sizes": {"small": {"cpu": "1024"}}}
        )
        node_d = _ForEachValueFnFindInMap(
            get_hash(["Sizes", "small", "missingthird", {"DefaultValue": "fb"}]),
            ["Sizes", "small", "missingthird", {"DefaultValue": "fb"}],
        )
        assert node_d.value(cfn_d) == "fb"

        cfn_e = _make_cfn(
            {
                "Lists": {
                    "key1": {"items": ["a", "b", "c"]},
                }
            },
            parameters={"Q": {"Type": "String"}},
        )
        node_e = _ForEachValueFnFindInMap(
            get_hash(["Lists", "key1", {"Ref": "Q"}]),
            ["Lists", "key1", {"Ref": "Q"}],
        )
        assert node_e.value(cfn_e) == ["a", "b", "c"]

        cfn_f = _make_cfn(
            {
                "Sizes": {"small": {"cpu": "1"}},
                "Other": {"large": {"mem": "2"}},
            }
        )
        node_f = _ForEachValueFnFindInMap(
            get_hash(["NoSuchMap", "absentTop", "absentSec"]),
            ["NoSuchMap", "absentTop", "absentSec"],
        )
        try:
            node_f.value(cfn_f, default_on_resolver_failure=False)
            raise AssertionError("expected _ResolveError")
        except _ResolveError:
            pass

        cfn_g = _make_cfn(
            {
                "Acct": {
                    "111111111111": {"prefixes": ["a"]},
                    "222222222222": {"prefixes": ["a", "b", "c"]},
                    "333333333333": {"prefixes": ["a", "b"]},
                }
            },
            parameters={"P": {"Type": "String"}},
        )
        node_g = _ForEachValueFnFindInMap(
            get_hash(["Acct", {"Ref": "AWS::AccountId"}, "prefixes"]),
            ["Acct", {"Ref": "AWS::AccountId"}, "prefixes"],
        )
        result_g = node_g.value(cfn_g)
        assert result_g == ["a", "b", "c"]

        cfn_h = _make_cfn(
            {
                "Acct": {
                    "111111111111": {"profile": "prod"},
                }
            },
            parameters={"P": {"Type": "String"}},
        )
        node_h = _ForEachValueFnFindInMap(
            get_hash(
                [
                    "Acct",
                    {"Ref": "AWS::AccountId"},
                    "profile",
                    {"DefaultValue": "fallback-h"},
                ]
            ),
            [
                "Acct",
                {"Ref": "AWS::AccountId"},
                "profile",
                {"DefaultValue": "fallback-h"},
            ],
        )
        out_h = node_h.value(cfn_h)
        assert out_h in ("prod", "fallback-h")
