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

from cfnlint.schema.resolver._resolver import RefResolver

class TestResolverWalkCfnPointerPointerTemporalHistoryQA:
    def test_resolver_walk_cfn_pointer_pointer_temporal_value_history_case(self):
        schema_tags = {
            "properties": {
                "Tags": {
                    "type": "array",
                    "items": {
                        "properties": {
                            "Name": {"type": "string"},
                            "Weight": {"type": "number"},
                        }
                    },
                }
            }
        }
        r_tags = RefResolver.from_schema(schema_tags)
        assert r_tags.resolve_cfn_pointer("/properties/Tags/*/Name") == {"type": "string"}
        assert r_tags.resolve_cfn_pointer("/properties/Tags/*/Weight") == {"type": "number"}

        schema_anyof_deep = {
            "properties": {
                "Ambiguous": {
                    "anyOf": [
                        {"properties": {"Decoy1": {"type": "string"}}},
                        {
                            "properties": {
                                "Y": {"properties": {"Zombie": {"type": "boolean"}}}
                            }
                        },
                        {
                            "properties": {
                                "Y": {"properties": {"Z": {"type": "integer"}}},
                            }
                        },
                        {"not": {}},
                    ]
                }
            }
        }
        r_any = RefResolver.from_schema(schema_anyof_deep)
        assert r_any.resolve_cfn_pointer("/properties/Ambiguous/Y/Z") == {"type": "integer"}

        schema_allof = {
            "properties": {
                "Fusion": {
                    "allOf": [
                        {"properties": {"ShardA": {"type": "string"}}},
                        {"properties": {"ShardB": {"type": "string"}}},
                        {
                            "properties": {
                                "Nest": {
                                    "properties": {
                                        "Deep": {"type": "number"},
                                    }
                                }
                            }
                        },
                    ]
                }
            }
        }
        r_all = RefResolver.from_schema(schema_allof)
        assert r_all.resolve_cfn_pointer("/properties/Fusion/Nest/Deep") == {"type": "number"}

        schema_oneof = {
            "properties": {
                "PickOne": {
                    "oneOf": [
                        {"not": {}},
                        {"properties": {"Wrong": {"type": "string"}}},
                        {"maxLength": 1},
                        {"properties": {"Leaf": {"type": "boolean"}}},
                    ]
                }
            }
        }
        r_one = RefResolver.from_schema(schema_oneof)
        assert r_one.resolve_cfn_pointer("/properties/PickOne/Leaf") == {"type": "boolean"}

        schema_ref_chain = {
            "$id": "https://example.invalid/cfnlint-qa-resolver-temporal-chain.json",
            "properties": {"Entry": {"$ref": "#/definitions/alpha"}},
            "definitions": {
                "alpha": {"$ref": "#/definitions/beta"},
                "beta": {
                    "properties": {
                        "Leaf": {
                            "type": "array",
                            "items": {"properties": {"K": {"type": "boolean"}}},
                        }
                    }
                },
            },
        }
        r_ref = RefResolver.from_schema(schema_ref_chain)
        assert r_ref.resolve_cfn_pointer("/properties/Entry/Leaf/*/K") == {"type": "boolean"}

        schema_nested_arrays = {
            "properties": {
                "Groups": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {
                            "properties": {
                                "Id": {"type": "string"},
                                "Flag": {"type": "boolean"},
                            }
                        },
                    },
                }
            }
        }
        r_mat = RefResolver.from_schema(schema_nested_arrays)
        assert r_mat.resolve_cfn_pointer("/properties/Groups/*/*/Id") == {"type": "string"}
        assert r_mat.resolve_cfn_pointer("/properties/Groups/*/*/Flag") == {"type": "boolean"}

        r_misc = RefResolver.from_schema({"properties": {}})
        assert r_misc.resolve_cfn_pointer("/properties/CfnLintAllTypes")["type"] == [
            "string",
            "integer",
            "number",
            "boolean",
            "object",
            "array",
        ]
        assert r_misc.resolve_cfn_pointer("/properties/CfnLintStringType") == {
            "type": ["string"]
        }

        schema_outer = {
            "$id": "https://example.invalid/cfnlint-qa-resolver-temporal-outer.json",
            "properties": {"Outer": {"$ref": "#/definitions/outerBody"}},
            "definitions": {
                "outerBody": {
                    "properties": {
                        "Outer": {
                            "type": "array",
                            "items": {"properties": {"Token": {"type": "string"}}},
                        }
                    }
                }
            },
        }
        r_outer = RefResolver.from_schema(schema_outer)
        assert r_outer.resolve_cfn_pointer("/properties/Outer/Outer/*/Token") == {"type": "string"}

        dup_ptr = "/properties/Tags/*/Name"
        assert r_tags.resolve_cfn_pointer(dup_ptr) == {"type": "string"}
        assert r_tags.resolve_cfn_pointer(dup_ptr) == {"type": "string"}
