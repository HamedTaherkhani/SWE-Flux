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

def _build(template):
    return Template("", template)

class TestConditionsBuildCnfDefUsePairsQA:
    def test_conditions_build_cnf_def_use_pairs_case(self):
        cfn_a = _build({"Resources": {}, "Conditions": {}})
        _ = cfn_a.conditions

        cfn_b = _build(
            {
                "Resources": {},
                "Parameters": {"Env": {"Type": "String"}},
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                },
            }
        )
        _ = cfn_b.conditions

        cfn_c = _build(
            {
                "Resources": {},
                "Parameters": {
                    "Env": {
                        "Type": "String",
                        "AllowedValues": ["prod", "dev"],
                    }
                },
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    "IsDev": {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
                },
            }
        )
        _ = cfn_c.conditions

        cfn_d = _build(
            {
                "Resources": {},
                "Parameters": {
                    "Env": {
                        "Type": "String",
                        "AllowedValues": ["prod", "dev", "stage"],
                    }
                },
                "Conditions": {
                    "IsForeign": {"Fn::Equals": [{"Ref": "Env"}, "qa"]},
                },
            }
        )
        _ = cfn_d.conditions

        cfn_e = _build(
            {
                "Resources": {},
                "Parameters": {
                    "Env": {
                        "Type": "String",
                        "AllowedValues": ["prod", "dev"],
                    }
                },
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                },
                "Rules": {
                    "IsProdImpliesEastUs": {
                        "RuleCondition": {
                            "Fn::Equals": [{"Ref": "Env"}, "prod"]
                        },
                        "Assertions": [
                            {
                                "Assert": {
                                    "Fn::Equals": [{"Ref": "Env"}, "prod"]
                                },
                                "AssertDescription": "Env must be prod",
                            }
                        ],
                    }
                },
            }
        )
        _ = cfn_e.conditions

        cfn_f = _build(
            {
                "Resources": {},
                "Parameters": {
                    "Env": {
                        "Type": "String",
                        "AllowedValues": ["prod", "dev"],
                    },
                    "Region": {
                        "Type": "String",
                        "AllowedValues": ["us-east-1", "us-west-2"],
                    },
                },
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    "IsDev": {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
                    "IsEast": {
                        "Fn::Equals": [{"Ref": "Region"}, "us-east-1"]
                    },
                },
            }
        )
        _ = cfn_f.conditions

        cfn_g = _build(
            {
                "Resources": {},
                "Parameters": {
                    "Env": {
                        "Type": "String",
                        "AllowedValues": ["prod", "dev", "stage"],
                    }
                },
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    "IsDev": {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
                    "IsStage": {
                        "Fn::Equals": [{"Ref": "Env"}, "stage"]
                    },
                },
            }
        )
        _ = cfn_g.conditions

        cfn_h = _build(
            {
                "Resources": {},
                "Parameters": {
                    "A": {"Type": "String"},
                    "B": {"Type": "String"},
                },
                "Conditions": {
                    "AeqB": {"Fn::Equals": [{"Ref": "A"}, {"Ref": "B"}]},
                },
            }
        )
        _ = cfn_h.conditions

        cfn_i = _build(
            {
                "Resources": {},
                "Parameters": {
                    "Env": {
                        "Type": "String",
                        "AllowedValues": ["prod", "dev"],
                    }
                },
                "Conditions": {
                    "Trivial": {"Fn::Equals": ["x", "x"]},
                    "AlwaysFalse": {"Fn::Equals": ["x", "y"]},
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                },
            }
        )
        _ = cfn_i.conditions
