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

from cfnlint.context.context import create_context_for_template
from cfnlint.jsonschema._resolvers_cfn import sub
from cfnlint.jsonschema.validators import CfnTemplateValidator
from cfnlint.template import Template

def _make_validator(parameters=None):
    template = {"Resources": {}}
    if parameters is not None:
        template["Parameters"] = parameters
    cfn = Template("", template, regions=["us-east-1"])
    v_cls = CfnTemplateValidator({}).extend(validators={})
    return v_cls({}).evolve(context=create_context_for_template(cfn))

def _drive(instance, parameters=None):
    return list(sub(_make_validator(parameters), instance))

class TestSubParameterExpansionKeyInParametersInvariantSuiteQA:

    def test_sub_string_zero_parameters(self):
        out = _drive("plain-no-placeholders")
        assert out and out[0][0] == "plain-no-placeholders"

    def test_sub_string_one_parameter(self):
        out = _drive(
            "x-${P1}",
            parameters={"P1": {"Type": "String", "Default": "alpha"}},
        )
        assert out and out[0][0] == "x-alpha"

    def test_sub_string_two_parameters(self):
        out = _drive(
            "x-${P1}-${P2}",
            parameters={
                "P1": {"Type": "String", "Default": "alpha"},
                "P2": {"Type": "String", "Default": "beta"},
            },
        )
        assert out and out[0][0] == "x-alpha-beta"

    def test_sub_string_three_parameters(self):
        out = _drive(
            "x-${P1}-${P2}-${P3}",
            parameters={
                "P1": {"Type": "String", "Default": "a"},
                "P2": {"Type": "String", "Default": "b"},
                "P3": {"Type": "String", "Default": "c"},
            },
        )
        assert out and out[0][0] == "x-a-b-c"

    def test_sub_string_four_parameters(self):
        out = _drive(
            "x-${P1}-${P2}-${P3}-${P4}",
            parameters={
                "P1": {"Type": "String", "Default": "a"},
                "P2": {"Type": "String", "Default": "b"},
                "P3": {"Type": "String", "Default": "c"},
                "P4": {"Type": "String", "Default": "d"},
            },
        )
        assert out and out[0][0] == "x-a-b-c-d"

    def test_sub_string_pseudoparam_aws_region(self):
        out = _drive("region-${AWS::Region}")
        assert out and "us-east-1" in out[0][0]

    def test_sub_string_pseudoparam_partition(self):
        out = _drive("p-${AWS::Partition}")
        assert out and "aws" in out[0][0]

    def test_sub_string_mixed_pseudo_and_default(self):
        out = _drive(
            "${AWS::Region}/${P1}/${P2}",
            parameters={
                "P1": {"Type": "String", "Default": "x"},
                "P2": {"Type": "String", "Default": "y"},
            },
        )
        assert out and out[0][0].endswith("/x/y")

    def test_sub_list_form_explicit_one_param(self):
        out = _drive(["v-${P1}", {"P1": "literal-alpha"}])
        assert out and out[0][0] == "v-literal-alpha"

    def test_sub_list_form_explicit_two_params(self):
        out = _drive(
            ["v-${P1}-${P2}", {"P1": "first", "P2": "second"}]
        )
        assert out and out[0][0] == "v-first-second"

    def test_sub_list_form_explicit_three_params(self):
        out = _drive(
            ["v-${P1}-${P2}-${P3}", {"P1": "a", "P2": "b", "P3": "c"}]
        )
        assert out and out[0][0] == "v-a-b-c"

    def test_sub_list_form_explicit_four_params(self):
        out = _drive(
            [
                "v-${P1}-${P2}-${P3}-${P4}",
                {"P1": "a", "P2": "b", "P3": "c", "P4": "d"},
            ]
        )
        assert out and out[0][0] == "v-a-b-c-d"

    def test_sub_list_form_explicit_six_params(self):
        out = _drive(
            [
                "v-${A}-${B}-${C}-${D}-${E}-${F}",
                {"A": "1", "B": "2", "C": "3", "D": "4", "E": "5", "F": "6"},
            ]
        )
        assert out and out[0][0] == "v-1-2-3-4-5-6"

    def test_sub_string_seven_parameters(self):
        params = {f"P{i}": {"Type": "String", "Default": f"v{i}"} for i in range(7)}
        placeholders = "-".join(f"${{{k}}}" for k in params.keys())
        out = _drive(f"x-{placeholders}", parameters=params)
        assert out

    def test_sub_string_eight_parameters_drive_full_recursion(self):
        params = {f"P{i}": {"Type": "String", "Default": f"v{i}"} for i in range(8)}
        placeholders = "-".join(f"${{{k}}}" for k in params.keys())
        out = _drive(f"x-{placeholders}", parameters=params)
        assert out

    def test_sub_string_param_with_allowed_values_first(self):
        out = _drive(
            "x-${P}",
            parameters={"P": {"Type": "String", "AllowedValues": ["v1", "v2"]}},
        )
        assert out and out[0][0] == "x-v1"

    def test_sub_string_two_pseudo_refs_resolve_chain(self):
        out = _drive("${AWS::Region}-${AWS::Partition}")
        assert out and out[0][0].startswith("us-east-1-")

    def test_sub_list_form_with_pseudo_ref_value(self):
        out = _drive(
            ["${P1}-${P2}", {"P1": "literal", "P2": {"Ref": "AWS::Region"}}]
        )
        assert out and out[0][0].startswith("literal-")

    def test_sub_string_six_parameters_depth_six_recursion(self):
        params = {f"K{i}": {"Type": "String", "Default": f"d{i}"} for i in range(6)}
        placeholders = "-".join(f"${{{k}}}" for k in params.keys())
        out = _drive(f"x-{placeholders}", parameters=params)
        assert out

    def test_sub_list_form_eight_keys_drive_full_recursion(self):
        out = _drive(
            [
                "${A}-${B}-${C}-${D}-${E}-${F}-${G}-${H}",
                {
                    "A": "a", "B": "b", "C": "c", "D": "d",
                    "E": "e", "F": "f", "G": "g", "H": "h",
                },
            ]
        )
        assert out and out[0][0] == "a-b-c-d-e-f-g-h"

    def test_sub_string_with_defaultless_param_unresolvable(self):
        out = _drive(
            "${P1}",
            parameters={"P1": {"Type": "String"}},
        )
        assert isinstance(out, list)
