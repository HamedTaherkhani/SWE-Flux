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
from cfnlint.jsonschema._keywords import contains as contains_keyword
from cfnlint.jsonschema.validators import CfnTemplateValidator
from cfnlint.template import Template

def _make_validator():
    cfn = Template("", {"Resources": {}}, regions=["us-east-1"])
    v_cls = CfnTemplateValidator({}).extend(validators={})
    return v_cls({}).evolve(context=create_context_for_template(cfn))

def _drive(contains_sub, instance_arr, schema_extra=None):
    schema = {"contains": contains_sub}
    if schema_extra:
        schema.update(schema_extra)
    v = _make_validator()
    return list(contains_keyword(v, contains_sub, instance_arr, schema))

class TestContainsMatchesMaxContainsLoopInvariantSuiteQA:

    def test_max_contains_2_array_3_integers(self):
        errs = _drive({"type": "integer"}, [1, 2, 3], {"maxContains": 2})
        assert any("Too many" in str(e) for e in errs)

    def test_max_contains_1_array_2_strings(self):
        errs = _drive({"type": "string"}, ["a", "b"], {"maxContains": 1})
        assert any("Too many" in str(e) for e in errs)

    def test_max_contains_3_array_4_integers(self):
        errs = _drive({"type": "integer"}, [10, 20, 30, 40], {"maxContains": 3})
        assert any("Too many" in str(e) for e in errs)

    def test_max_contains_4_array_5_booleans(self):
        errs = _drive(
            {"type": "boolean"}, [True, False, True, True, False], {"maxContains": 4}
        )
        assert any("Too many" in str(e) for e in errs)

    def test_max_contains_2_array_3_strings_with_one_nonmatching(self):
        errs = _drive({"type": "string"}, ["a", 99, "b", "c"], {"maxContains": 2})
        assert any("Too many" in str(e) for e in errs)

    def test_max_contains_1_array_3_integers_with_two_nonmatching(self):
        errs = _drive(
            {"type": "integer"}, ["x", 5, "y", 6], {"maxContains": 1}
        )
        assert any("Too many" in str(e) for e in errs)

    def test_max_contains_5_array_6_integers(self):
        errs = _drive({"type": "integer"}, [1, 2, 3, 4, 5, 6], {"maxContains": 5})
        assert any("Too many" in str(e) for e in errs)

    def test_max_contains_zero_array_1_integer(self):
        errs = _drive({"type": "integer"}, [42], {"maxContains": 0})
        assert any("Too many" in str(e) for e in errs)

    def test_no_max_contains_default_is_len_instance(self):
        errs = _drive({"type": "integer"}, [1, 2, 3, 4])
        assert errs == []

    def test_max_contains_5_array_3_only(self):
        errs = _drive({"type": "integer"}, [1, 2, 3], {"maxContains": 5})
        assert errs == []

    def test_max_contains_2_with_only_nonmatching(self):
        errs = _drive({"type": "integer"}, ["a", "b", "c"], {"maxContains": 2})
        assert any("does not contain" in str(e) for e in errs)

    def test_min_contains_walk_full_array(self):
        errs = _drive(
            {"type": "integer"}, [1, 2, 3], {"minContains": 5}
        )
        assert any("Too few" in str(e) for e in errs)

    def test_contains_dict_schema_overshoot(self):
        sub = {"type": "object", "properties": {"x": {"type": "integer"}}}
        errs = _drive(
            sub,
            [{"x": 1}, {"x": 2}, {"x": 3}],
            {"maxContains": 2},
        )
        assert any("Too many" in str(e) for e in errs)

    def test_contains_dict_schema_partial_match_no_overshoot(self):
        sub = {
            "type": "object",
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
        }
        errs = _drive(
            sub,
            [{"x": 1}, {"y": "no"}, {"x": 2}],
            {"maxContains": 2},
        )
        assert errs == []

    def test_contains_with_array_subschema_overshoot(self):
        sub = {"type": "array"}
        errs = _drive(sub, [[1], [2], [3], [4]], {"maxContains": 3})
        assert any("Too many" in str(e) for e in errs)

    def test_max_contains_2_array_2_no_overshoot(self):
        errs = _drive({"type": "integer"}, [1, 2], {"maxContains": 2})
        assert errs == []

    def test_empty_instance_no_iterations(self):
        errs = _drive({"type": "integer"}, [], {"maxContains": 1})
        assert any("does not contain" in str(e) for e in errs)

    def test_max_contains_3_array_4_dicts_overshoot(self):
        sub = {"type": "object"}
        errs = _drive(
            sub, [{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}], {"maxContains": 3}
        )
        assert any("Too many" in str(e) for e in errs)

    def test_min_and_max_contains_no_overshoot(self):
        errs = _drive(
            {"type": "integer"},
            [1, 2, 3],
            {"minContains": 2, "maxContains": 5},
        )
        assert errs == []

    def test_max_contains_1_array_2_no_overshoot(self):
        errs = _drive({"type": "integer"}, [1, 2], {"maxContains": 1})
        assert any("Too many" in str(e) for e in errs)

    def test_max_contains_2_alternating_valid_invalid(self):
        errs = _drive(
            {"type": "integer"},
            [1, "x", 2, "y", 3, "z"],
            {"maxContains": 2},
        )
        assert any("Too many" in str(e) for e in errs)
