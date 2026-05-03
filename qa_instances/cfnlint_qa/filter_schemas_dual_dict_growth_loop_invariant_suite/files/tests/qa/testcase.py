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
from cfnlint.jsonschema._filter import FunctionFilter
from cfnlint.jsonschema.validators import CfnTemplateValidator
from cfnlint.template import Template

def _make_validator():
    cfn = Template("", {"Resources": {}}, regions=["us-east-1"])
    v_cls = CfnTemplateValidator({}).extend(validators={})
    v = v_cls({}).evolve(context=create_context_for_template(cfn))
    return v.evolve(context=v.context.evolve(functions=["Fn::If"]))

def _drive(schema):
    f = FunctionFilter()
    return list(f.filter(_make_validator(), {}, schema))

class TestFilterSchemasDualDictGrowthLoopInvariantSuiteQA:

    def test_standard_only_single_key(self):
        _drive({"type": "string"})

    def test_standard_only_three_keys(self):
        _drive({"type": "object", "title": "demo", "description": "test"})

    def test_standard_only_six_keys(self):
        _drive(
            {
                "type": "string",
                "title": "t",
                "description": "d",
                "minLength": 1,
                "maxLength": 50,
                "pattern": ".*",
            }
        )

    def test_standard_only_with_pattern_properties(self):
        _drive({"type": "object", "patternProperties": {".*": {"type": "string"}}})

    def test_standard_only_array_with_items(self):
        _drive({"type": "array", "items": {"type": "string"}})

    def test_group_only_single_required(self):
        _drive({"required": ["x"]})

    def test_group_only_two_keys_required_minitems(self):
        _drive({"required": ["x"], "minItems": 1})

    def test_group_only_three_keys(self):
        _drive({"required": ["x"], "minItems": 1, "maxItems": 5})

    def test_group_only_five_keys(self):
        _drive(
            {
                "required": ["a"],
                "minItems": 1,
                "maxItems": 10,
                "minProperties": 1,
                "maxProperties": 5,
            }
        )

    def test_group_only_dependencies(self):
        _drive({"dependencies": {"a": ["b"]}, "dependentRequired": {"a": ["c"]}})

    def test_group_only_uniqueitems(self):
        _drive({"uniqueItems": True, "minItems": 1, "maxItems": 100})

    def test_group_only_required_or(self):
        _drive({"requiredOr": ["a", "b"], "requiredXor": ["c", "d"]})

    def test_mixed_required_then_type(self):
        _drive({"required": ["x"], "type": "object"})

    def test_mixed_minitems_then_type(self):
        _drive({"minItems": 1, "type": "array"})

    def test_mixed_if_then_type(self):
        _drive({"if": {"type": "string"}, "type": "object"})

    def test_mixed_type_then_required(self):
        _drive({"type": "object", "required": ["x"]})

    def test_mixed_type_then_min_max_items(self):
        _drive({"type": "array", "minItems": 1, "maxItems": 10})

    def test_schema_with_ref_no_cfnlint_keyword(self):
        _drive({"$ref": "#/definitions/x", "type": "object"})

    def test_schema_with_ref_and_required(self):
        _drive({"$ref": "#/definitions/x", "required": ["a"]})

    def test_empty_schema(self):
        _drive({})

    def test_mixed_alternating_six_keys(self):
        _drive(
            {
                "required": ["a"],
                "type": "object",
                "minItems": 1,
                "title": "t",
                "maxItems": 10,
                "description": "d",
            }
        )

    def test_mixed_lots_of_groups_and_few_standards(self):
        _drive(
            {
                "required": ["a"],
                "minItems": 1,
                "maxItems": 5,
                "minProperties": 1,
                "maxProperties": 2,
                "uniqueItems": True,
                "type": "array",
                "title": "t",
            }
        )
