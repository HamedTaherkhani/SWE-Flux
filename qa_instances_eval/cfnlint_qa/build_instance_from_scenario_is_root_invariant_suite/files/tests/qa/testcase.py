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

from cfnlint.context.conditions._utils import build_instance_from_scenario
from cfnlint.context.context import create_context_for_template
from cfnlint.template import Template

def _make_context(functions=("Fn::If", "Ref")):
    cfn = Template("", {"Resources": {}}, regions=["us-east-1"])
    return create_context_for_template(cfn).evolve(functions=list(functions))

def _drive(instance, scenario, ctx=None):
    return build_instance_from_scenario(
        instance,
        scenario,
        is_root=True,
        context=ctx or _make_context(),
    )

class TestBuildInstanceFromScenarioIsRootInvariantSuiteQA:

    def test_scalar_string_instance(self):
        out = _drive("plain-string", {})
        assert out == "plain-string"

    def test_scalar_int_instance(self):
        out = _drive(42, {})
        assert out == 42

    def test_scalar_none_instance(self):
        out = _drive(None, {})
        assert out is None

    def test_ref_no_value_short_circuits(self):
        out = _drive({"Ref": "AWS::NoValue"}, {})
        assert out is None

    def test_empty_list_no_recursion(self):
        out = _drive([], {})
        assert out == []

    def test_list_of_scalars(self):
        out = _drive([1, 2, "three", None], {})
        assert out == [1, 2, "three"]

    def test_list_with_fn_if_first(self):
        out = _drive(
            [{"Fn::If": ["C", "x", "y"]}, "literal"],
            {"C": True},
        )
        assert out == ["x", "literal"]

    def test_root_dict_two_keys_no_fn_if(self):
        out = _drive({"A": "alpha", "B": "beta"}, {})
        assert out == {"A": "alpha", "B": "beta"}

    def test_root_dict_with_nested_fn_if_value(self):
        out = _drive(
            {"Name": {"Fn::If": ["C", "yes", "no"]}, "Other": "literal"},
            {"C": True},
        )
        assert out == {"Name": "yes", "Other": "literal"}

    def test_root_dict_with_no_value_filtered_out(self):
        out = _drive(
            {"Keep": "v", "Drop": {"Ref": "AWS::NoValue"}},
            {},
        )
        assert out == {"Keep": "v"}

    def test_root_fn_if_resolved_true_branch_scalar(self):
        out = _drive(
            {"Fn::If": ["C", "true-branch", "false-branch"]},
            {"C": True},
        )
        assert out == "true-branch"

    def test_root_fn_if_resolved_false_branch_scalar(self):
        out = _drive(
            {"Fn::If": ["C", "true-branch", "false-branch"]},
            {"C": False},
        )
        assert out == "false-branch"

    def test_root_fn_if_unresolved_returns_instance(self):
        instance = {"Fn::If": ["UnknownC", "x", "y"]}
        out = _drive(instance, {})
        assert out == instance

    def test_root_fn_if_branch_is_dict_recurses(self):
        out = _drive(
            {"Fn::If": ["C", {"InnerKey": "v"}, "fallback"]},
            {"C": True},
        )
        assert out == {"InnerKey": "v"} or out == "v"

    def test_nested_fn_if_with_inner_fn_if(self):
        out = _drive(
            {"Fn::If": ["Outer", {"Fn::If": ["Inner", "deep-true", "deep-false"]}, "no"]},
            {"Outer": True, "Inner": True},
        )
        assert out == "deep-true"

    def test_deep_mixed_root_dict_list_fn_if(self):
        instance = {
            "A": {"Fn::If": ["C1", "v1", "v2"]},
            "B": [{"Fn::If": ["C2", "x", "y"]}, "lit"],
            "C": {"K": {"Fn::If": ["C3", "p", "q"]}},
        }
        out = _drive(
            instance,
            {"C1": True, "C2": False, "C3": True},
        )
        assert out["A"] == "v1"
        assert out["B"] == ["y", "lit"]

    def test_root_list_of_dicts_each_with_fn_if(self):
        instance = [
            {"Fn::If": ["C", "true-a", "false-a"]},
            {"Fn::If": ["C", "true-b", "false-b"]},
            "literal",
        ]
        out = _drive(instance, {"C": True})
        assert out == ["true-a", "true-b", "literal"]

    def test_dict_with_fn_if_returning_none_branch(self):
        instance = {
            "Keep": "v",
            "Maybe": {"Fn::If": ["C", "yes", {"Ref": "AWS::NoValue"}]},
        }
        out = _drive(instance, {"C": False})
        assert "Maybe" not in out
        assert out.get("Keep") == "v"

    def test_root_dict_six_keys_drives_six_recursive_calls(self):
        instance = {f"K{i}": f"v{i}" for i in range(6)}
        out = _drive(instance, {})
        assert out == instance

    def test_root_dict_with_fn_if_at_unsupported_position(self):
        ctx = _make_context(functions=())
        instance = {"Fn::If": ["C", "a", "b"]}
        out = _drive(instance, {"C": True}, ctx=ctx)
        assert isinstance(out, dict)

    def test_volume_eight_top_level_keys_no_fn_if(self):
        instance = {f"Field{i}": [f"item{i}-1", f"item{i}-2"] for i in range(4)}
        out = _drive(instance, {})
        assert out == instance
