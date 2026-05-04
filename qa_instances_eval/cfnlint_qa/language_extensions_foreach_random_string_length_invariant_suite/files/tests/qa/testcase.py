from __future__ import annotations

import sys
from pathlib import Path

import pytest

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
from cfnlint.template.transforms import _language_extensions as _le
from cfnlint.template.transforms._language_extensions import (
    _ForEachCollection,
    _ResolveError,
)

def _make_cfn(parameters=None, mappings=None, regions=None):
    template = {}
    if parameters is not None:
        template["Parameters"] = parameters
    if mappings is not None:
        template["Mappings"] = mappings
    return Template("", template, regions=regions or ["us-east-1"])

@pytest.fixture(autouse=True)
def _reset_account_id_global():
    saved = _le._ACCOUNT_ID
    _le._ACCOUNT_ID = None
    try:
        yield
    finally:
        _le._ACCOUNT_ID = saved

class TestLanguageExtensionsForEachRandomStringLengthInvariantSuiteQA:

    def test_collection_branch_all_unresolvable_refs(self):
        cfn = _make_cfn(parameters={})
        cache = {}
        fec = _ForEachCollection(
            [
                {"Ref": "AbsentAlpha"},
                {"Ref": "AbsentBeta"},
                {"Ref": "AbsentGamma"},
                {"Ref": "AbsentDelta"},
            ]
        )
        out = list(fec.values(cfn, cache, {}))
        assert len(out) == 4
        for s in out:
            assert isinstance(s, str)
            assert len(s) == 7
        assert len(cache) == 4

    def test_collection_branch_mixed_resolvable_and_unresolvable(self):
        cfn = _make_cfn(parameters={})
        cache = {}
        fec = _ForEachCollection(
            [
                "literal-1",
                {"Ref": "AbsentMix1"},
                "literal-2",
                {"Ref": "AbsentMix2"},
                "literal-3",
                {"Ref": "AbsentMix3"},
            ]
        )
        out = list(fec.values(cfn, cache, {}))
        assert out[0] == "literal-1"
        assert out[2] == "literal-2"
        assert out[4] == "literal-3"
        assert len(out[1]) == 7
        assert len(out[3]) == 7
        assert len(out[5]) == 7
        assert len(cache) == 3

    def test_collection_branch_all_resolvable_scalars(self):
        cfn = _make_cfn(parameters={})
        cache = {}
        fec = _ForEachCollection(["one", "two", "three", "four"])
        out = list(fec.values(cfn, cache, {}))
        assert out == ["one", "two", "three", "four"]
        assert cache == {}

    def test_collection_branch_param_refs_resolved_via_default(self):
        cfn = _make_cfn(
            parameters={
                "WithDefaultA": {"Type": "String", "Default": "alpha"},
                "WithDefaultB": {"Type": "String", "Default": "beta"},
            }
        )
        cache = {}
        fec = _ForEachCollection([{"Ref": "WithDefaultA"}, {"Ref": "WithDefaultB"}])
        out = list(fec.values(cfn, cache, {}))
        assert out == ["alpha", "beta"]
        assert cache == {}

    def test_collection_branch_param_refs_resolved_via_allowed_values(self):
        cfn = _make_cfn(
            parameters={
                "OnlyAllowed": {
                    "Type": "String",
                    "AllowedValues": ["chosen", "other"],
                }
            }
        )
        cache = {}
        fec = _ForEachCollection([{"Ref": "OnlyAllowed"}])
        out = list(fec.values(cfn, cache, {}))
        assert out == ["chosen"]
        assert cache == {}

    def test_collection_branch_pseudo_param_aws_region_resolves(self):
        cfn = _make_cfn(parameters={}, regions=["us-west-2"])
        cache = {}
        fec = _ForEachCollection([{"Ref": "AWS::Region"}])
        out = list(fec.values(cfn, cache, {}))
        assert out == ["us-west-2"]
        assert cache == {}

    def test_collection_branch_pseudo_params_partition_urlsuffix_resolve(self):
        cfn = _make_cfn(parameters={}, regions=["us-east-1"])
        cache = {}
        fec = _ForEachCollection(
            [{"Ref": "AWS::Partition"}, {"Ref": "AWS::URLSuffix"}]
        )
        out = list(fec.values(cfn, cache, {}))
        assert out == ["aws", "amazonaws.com"]
        assert cache == {}

    def test_collection_branch_pseudo_param_aws_accountid_unresolvable(self):
        cfn = _make_cfn(parameters={}, regions=["us-east-1"])
        cache = {}
        fec = _ForEachCollection(
            [
                {"Ref": "AWS::AccountId"},
                {"Ref": "AWS::AccountId"},
                {"Ref": "AWS::AccountId"},
            ]
        )
        out = list(fec.values(cfn, cache, {}))
        assert len(out) == 3
        for s in out:
            assert isinstance(s, str) and len(s) == 7

    def test_collection_branch_findinmap_resolves_via_default_value(self):
        cfn = _make_cfn(parameters={}, mappings={})
        cache = {}
        fec = _ForEachCollection(
            [
                {
                    "Fn::FindInMap": [
                        "MissingMap",
                        "MissingTop",
                        "MissingSecond",
                        {"DefaultValue": "fallback-value"},
                    ]
                }
            ]
        )
        out = list(fec.values(cfn, cache, {}))
        assert out == ["fallback-value"]
        assert cache == {}

    def test_collection_branch_findinmap_unresolvable_no_default(self):
        cfn = _make_cfn(parameters={}, mappings={})
        cache = {}
        fec = _ForEachCollection(
            [
                {"Fn::FindInMap": ["MissingA", "k1", "k2"]},
                {"Fn::FindInMap": ["MissingB", "k1", "k2"]},
                {"Fn::FindInMap": ["MissingC", "k1", "k2"]},
                {"Fn::FindInMap": ["MissingD", "k1", "k2"]},
            ]
        )
        out = list(fec.values(cfn, cache, {}))
        assert len(out) == 4
        for s in out:
            assert isinstance(s, str) and len(s) == 7

    def test_collection_branch_findinmap_mixed_resolvable_and_not(self):
        cfn = _make_cfn(
            parameters={},
            mappings={"GoodMap": {"top": {"sec": "resolved"}}},
        )
        cache = {}
        fec = _ForEachCollection(
            [
                {"Fn::FindInMap": ["GoodMap", "top", "sec"]},
                {"Fn::FindInMap": ["NoMap", "absentTop", "absentSec"]},
            ]
        )
        out = list(fec.values(cfn, cache, {}))
        assert out[0] == "resolved"
        assert isinstance(out[1], str) and len(out[1]) == 7
        assert len(cache) == 1

    def test_fn_branch_unresolvable_ref_populates_cache(self):
        cfn = _make_cfn(parameters={})
        cache = {}
        fec = _ForEachCollection({"Ref": "AbsentForFn"})
        out = list(fec.values(cfn, cache, {}))
        assert len(out) == 2
        for s in out:
            assert isinstance(s, str) and len(s) == 7
        assert len(cache) == 1
        cached_list = next(iter(cache.values()))
        assert isinstance(cached_list, list) and len(cached_list) == 2

    def test_fn_branch_uses_existing_cache_no_rebind(self):
        cfn = _make_cfn(parameters={})
        cache = {}
        fec_first = _ForEachCollection({"Ref": "AbsentReusedFn"})
        first = list(fec_first.values(cfn, cache, {}))
        assert len(first) == 2
        fec_second = _ForEachCollection({"Ref": "AbsentReusedFn"})
        second = list(fec_second.values(cfn, cache, {}))
        assert second == first

    def test_fn_branch_resolvable_commadelimitedlist_no_rebind(self):
        cfn = _make_cfn(
            parameters={"AccountIds": {"Type": "CommaDelimitedList"}}
        )
        cache = {}
        fec = _ForEachCollection({"Ref": "AccountIds"})
        out = list(fec.values(cfn, cache, {}))
        assert out == [
            {"Fn::Select": [0, {"Ref": "AccountIds"}]},
            {"Fn::Select": [1, {"Ref": "AccountIds"}]},
        ]
        assert cache == {}

    def test_fn_branch_findinmap_unresolvable_falls_back_to_random(self):
        cfn = _make_cfn(parameters={}, mappings={})
        cache = {}
        fec = _ForEachCollection(
            {"Fn::FindInMap": ["MissingMap", "MissingTopKey", "MissingSecondKey"]}
        )
        out = list(fec.values(cfn, cache, {}))
        assert len(out) == 2
        for s in out:
            assert isinstance(s, str) and len(s) == 7

    def test_fn_branch_findinmap_default_list_yields_each(self):
        cfn = _make_cfn(parameters={}, mappings={})
        cache = {}
        fec = _ForEachCollection(
            {
                "Fn::FindInMap": [
                    "MissingMap",
                    "MissingK1",
                    "MissingK2",
                    {"DefaultValue": ["alpha", "beta", "gamma"]},
                ]
            }
        )
        out = list(fec.values(cfn, cache, {}))
        assert out == ["alpha", "beta", "gamma"]
        assert cache == {}

    def test_fn_branch_ref_to_list_param_with_default_resolves(self):
        cfn = _make_cfn(
            parameters={
                "Subnets": {
                    "Type": "List<AWS::EC2::Subnet::Id>",
                    "Default": "subnet-1, subnet-2, subnet-3",
                }
            }
        )
        cache = {}
        fec = _ForEachCollection({"Ref": "Subnets"})
        out = list(fec.values(cfn, cache, {}))
        assert out == ["subnet-1", "subnet-2", "subnet-3"]
        assert cache == {}

    def test_collection_branch_single_unresolvable_then_repeat(self):
        cfn = _make_cfn(parameters={})
        cache_a = {}
        fec = _ForEachCollection([{"Ref": "AbsentSolo"}])
        out_a = list(fec.values(cfn, cache_a, {}))
        assert len(out_a) == 1 and len(out_a[0]) == 7

        cache_b = {}
        out_b = list(fec.values(cfn, cache_b, {}))
        assert len(out_b) == 1 and len(out_b[0]) == 7

    def test_chained_unresolvable_fns_share_cache(self):
        cfn = _make_cfn(parameters={})
        cache = {}
        for ref_name in ("AbsentChainA", "AbsentChainB", "AbsentChainC"):
            fec = _ForEachCollection({"Ref": ref_name})
            out = list(fec.values(cfn, cache, {}))
            assert len(out) == 2
            for s in out:
                assert len(s) == 7
        assert len(cache) == 3

    def test_fn_branch_unresolvable_then_immediate_replay(self):
        cfn = _make_cfn(parameters={})
        cache = {}
        fec_a = _ForEachCollection({"Ref": "AbsentReplay"})
        out_a = list(fec_a.values(cfn, cache, {}))
        fec_b = _ForEachCollection({"Ref": "AbsentReplay"})
        out_b = list(fec_b.values(cfn, cache, {}))
        assert out_a == out_b
        assert len(out_a) == 2
        assert all(len(s) == 7 for s in out_a)

    def test_collection_branch_volume_eight_unresolvable(self):
        cfn = _make_cfn(parameters={})
        cache = {}
        items = [{"Ref": f"AbsentVolume{i}"} for i in range(8)]
        fec = _ForEachCollection(items)
        out = list(fec.values(cfn, cache, {}))
        assert len(out) == 8
        for s in out:
            assert isinstance(s, str) and len(s) == 7
        assert len(cache) == 8
