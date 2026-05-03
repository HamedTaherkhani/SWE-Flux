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

class TestSchemaResolverWalkCfnPointerDefUsePairsQA:
    def test_schema_resolver_walk_cfn_pointer_def_use_pairs_case(self):
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
        r1 = RefResolver.from_schema(schema_tags)
        leaf_a = r1.resolve_cfn_pointer("/properties/Tags/*/Name")
        leaf_b = r1.resolve_cfn_pointer("/properties/Tags/*/Weight")
        assert leaf_a == {"type": "string"}
        assert leaf_b == {"type": "number"}

        schema_anyof = {
            "properties": {
                "Ambiguous": {
                    "anyOf": [
                        {
                            "properties": {
                                "Decoy": {"type": "string"},
                            }
                        },
                        {
                            "properties": {
                                "Y": {
                                    "properties": {
                                        "Z": {"type": "integer"},
                                    }
                                }
                            }
                        },
                    ]
                }
            }
        }
        r2 = RefResolver.from_schema(schema_anyof)
        leaf_c = r2.resolve_cfn_pointer("/properties/Ambiguous/Y/Z")
        assert leaf_c == {"type": "integer"}

        schema_oneof = {
            "properties": {
                "PickOne": {
                    "oneOf": [
                        {"not": {}},
                        {
                            "properties": {
                                "Leaf": {"type": "boolean"},
                            }
                        },
                    ]
                }
            }
        }
        r3 = RefResolver.from_schema(schema_oneof)
        leaf_d = r3.resolve_cfn_pointer("/properties/PickOne/Leaf")
        assert leaf_d == {"type": "boolean"}

        schema_ref = {
            "$id": "https://example.invalid/cfnlint-qa-resolver.json",
            "properties": {
                "Outer": {"$ref": "#/definitions/outerBody"},
            },
            "definitions": {
                "outerBody": {
                    "properties": {
                        "Outer": {
                            "type": "array",
                            "items": {
                                "properties": {
                                    "Token": {"type": "string"},
                                }
                            },
                        }
                    }
                }
            },
        }
        r4 = RefResolver.from_schema(schema_ref)
        leaf_e = r4.resolve_cfn_pointer("/properties/Outer/Outer/*/Token")
        assert leaf_e == {"type": "string"}
