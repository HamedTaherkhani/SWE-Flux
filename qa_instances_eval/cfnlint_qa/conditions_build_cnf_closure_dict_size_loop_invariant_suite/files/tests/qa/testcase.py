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

from cfnlint.conditions.conditions import Conditions

class _CfnStub:

    def __init__(self, template):
        self.template = template

class TestConditionsBuildCnfClosureDictSizeLoopInvariantSuiteQA:

    def test_single_parameter_condition(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                },
                "Parameters": {"Env": {"Type": "String"}},
            }
        )
        c = Conditions(cfn)
        assert "IsProd" in c._conditions

    def test_two_conditions_distinct_parameters(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    "IsBig": {"Fn::Equals": [{"Ref": "Size"}, "large"]},
                },
                "Parameters": {
                    "Env": {"Type": "String"},
                    "Size": {"Type": "String"},
                },
            }
        )
        c = Conditions(cfn)
        assert set(c._conditions.keys()) == {"IsProd", "IsBig"}

    def test_three_conditions_shared_parameter_NAND(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    "IsDev": {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
                    "IsStage": {"Fn::Equals": [{"Ref": "Env"}, "stage"]},
                },
                "Parameters": {"Env": {"Type": "String"}},
            }
        )
        c = Conditions(cfn)
        assert len(c._conditions) == 3

    def test_static_true_condition(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "AlwaysTrue": {"Fn::Equals": ["same", "same"]},
                },
            }
        )
        c = Conditions(cfn)
        assert "AlwaysTrue" in c._conditions

    def test_static_false_condition(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "AlwaysFalse": {"Fn::Equals": ["alpha", "beta"]},
                },
            }
        )
        c = Conditions(cfn)
        assert "AlwaysFalse" in c._conditions

    def test_mixed_static_and_dynamic_conditions(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "AlwaysTrue": {"Fn::Equals": ["same", "same"]},
                    "AlwaysFalse": {"Fn::Equals": ["alpha", "beta"]},
                    "DynamicProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    "DynamicDev": {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
                },
                "Parameters": {"Env": {"Type": "String"}},
            }
        )
        c = Conditions(cfn)
        assert len(c._conditions) == 4

    def test_duplicate_equals_hash_triggers_continue_branch(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsProdA": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    "IsProdB": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                },
                "Parameters": {"Env": {"Type": "String"}},
            }
        )
        c = Conditions(cfn)
        assert set(c._conditions.keys()) == {"IsProdA", "IsProdB"}

    def test_condition_with_fn_and_compound(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "ProdAndBig": {
                        "Fn::And": [
                            {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                            {"Fn::Equals": [{"Ref": "Size"}, "large"]},
                            {"Fn::Equals": [{"Ref": "Tier"}, "premium"]},
                        ]
                    }
                },
                "Parameters": {
                    "Env": {"Type": "String"},
                    "Size": {"Type": "String"},
                    "Tier": {"Type": "String"},
                },
            }
        )
        c = Conditions(cfn)
        assert "ProdAndBig" in c._conditions

    def test_condition_with_fn_or_compound(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "AnyOf": {
                        "Fn::Or": [
                            {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                            {"Fn::Equals": [{"Ref": "Env"}, "stage"]},
                            {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
                            {"Fn::Equals": [{"Ref": "Env"}, "qa"]},
                        ]
                    }
                },
                "Parameters": {"Env": {"Type": "String"}},
            }
        )
        c = Conditions(cfn)
        assert "AnyOf" in c._conditions

    def test_condition_with_fn_not_wrapping_equals(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "NotProd": {
                        "Fn::Not": [{"Fn::Equals": [{"Ref": "Env"}, "prod"]}]
                    }
                },
                "Parameters": {"Env": {"Type": "String"}},
            }
        )
        c = Conditions(cfn)
        assert "NotProd" in c._conditions

    def test_condition_with_nested_and_or_not(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "Compound": {
                        "Fn::And": [
                            {
                                "Fn::Or": [
                                    {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                                    {"Fn::Equals": [{"Ref": "Env"}, "stage"]},
                                ]
                            },
                            {
                                "Fn::Not": [
                                    {"Fn::Equals": [{"Ref": "Disabled"}, "true"]}
                                ]
                            },
                            {"Fn::Equals": [{"Ref": "Region"}, "us-east-1"]},
                        ]
                    }
                },
                "Parameters": {
                    "Env": {"Type": "String"},
                    "Disabled": {"Type": "String"},
                    "Region": {"Type": "String"},
                },
            }
        )
        c = Conditions(cfn)
        assert "Compound" in c._conditions

    def test_condition_with_named_condition_reference(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    "AlsoProd": {"Condition": "IsProd"},
                },
                "Parameters": {"Env": {"Type": "String"}},
            }
        )
        c = Conditions(cfn)
        assert set(c._conditions.keys()) == {"IsProd", "AlsoProd"}

    def test_condition_with_aws_region_compare_dynamic(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsUSEast1": {
                        "Fn::Equals": [{"Ref": "AWS::Region"}, "us-east-1"]
                    }
                },
            }
        )
        c = Conditions(cfn)
        assert "IsUSEast1" in c._conditions

    def test_condition_with_pseudo_partition_compare(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsCommercial": {
                        "Fn::Equals": [{"Ref": "AWS::Partition"}, "aws"]
                    }
                },
            }
        )
        c = Conditions(cfn)
        assert "IsCommercial" in c._conditions

    def test_conditions_with_rules_assertions(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                },
                "Parameters": {
                    "Env": {"Type": "String"},
                    "Region": {"Type": "String"},
                },
                "Rules": {
                    "RegionRule": {
                        "Assertions": [
                            {
                                "Assert": {
                                    "Fn::Equals": [{"Ref": "Region"}, "us-east-1"]
                                },
                                "AssertDescription": "Must be us-east-1",
                            }
                        ]
                    }
                },
            }
        )
        c = Conditions(cfn)
        assert "IsProd" in c._conditions

    def test_two_rules_each_with_multiple_assertions(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                },
                "Parameters": {
                    "Env": {"Type": "String"},
                    "Region": {"Type": "String"},
                    "Size": {"Type": "String"},
                },
                "Rules": {
                    "RegionRule": {
                        "Assertions": [
                            {
                                "Assert": {
                                    "Fn::Equals": [{"Ref": "Region"}, "us-east-1"]
                                },
                                "AssertDescription": "us-east-1 only",
                            },
                            {
                                "Assert": {
                                    "Fn::Equals": [{"Ref": "Region"}, "eu-west-1"]
                                },
                                "AssertDescription": "or eu-west-1",
                            },
                        ]
                    },
                    "SizeRule": {
                        "Assertions": [
                            {
                                "Assert": {
                                    "Fn::Equals": [{"Ref": "Size"}, "large"]
                                },
                                "AssertDescription": "large only",
                            },
                            {
                                "Assert": {
                                    "Fn::Equals": [{"Ref": "Size"}, "xlarge"]
                                },
                                "AssertDescription": "or xlarge",
                            },
                        ]
                    },
                },
            }
        )
        c = Conditions(cfn)
        assert "IsProd" in c._conditions

    def test_rules_only_no_conditions(self):
        cfn = _CfnStub(
            {
                "Parameters": {"Env": {"Type": "String"}},
                "Rules": {
                    "EnvRule": {
                        "Assertions": [
                            {
                                "Assert": {
                                    "Fn::Equals": [{"Ref": "Env"}, "prod"]
                                },
                                "AssertDescription": "prod only",
                            }
                        ]
                    }
                },
            }
        )
        c = Conditions(cfn)
        assert c._conditions == {}

    def test_conditions_with_allowed_values_drive_iteration_two(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    "IsAllowedExtra": {
                        "Fn::Equals": [{"Ref": "Env"}, "absent-from-allowed"]
                    },
                },
                "Parameters": {
                    "Env": {
                        "Type": "String",
                        "AllowedValues": ["prod", "dev"],
                    },
                },
            }
        )
        c = Conditions(cfn)
        assert "IsProd" in c._conditions

    def test_conditions_with_allowed_values_all_consumed(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    "IsDev": {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
                },
                "Parameters": {
                    "Env": {
                        "Type": "String",
                        "AllowedValues": ["prod", "dev"],
                    }
                },
            }
        )
        c = Conditions(cfn)
        assert set(c._conditions.keys()) == {"IsProd", "IsDev"}

    def test_many_distinct_conditions_for_volume(self):
        conds = {
            f"IsCase{i}": {"Fn::Equals": [{"Ref": "Env"}, f"case-{i}"]}
            for i in range(8)
        }
        cfn = _CfnStub(
            {"Conditions": conds, "Parameters": {"Env": {"Type": "String"}}}
        )
        c = Conditions(cfn)
        assert len(c._conditions) == 8

    def test_alternating_static_dynamic_volume(self):
        conds = {}
        for i in range(5):
            conds[f"StaticTrue{i}"] = {"Fn::Equals": [f"x{i}", f"x{i}"]}
        for i in range(5):
            conds[f"Dynamic{i}"] = {
                "Fn::Equals": [{"Ref": "Env"}, f"value-{i}"]
            }
        cfn = _CfnStub(
            {"Conditions": conds, "Parameters": {"Env": {"Type": "String"}}}
        )
        c = Conditions(cfn)
        assert len(c._conditions) == 10

    def test_compositors_plus_rules_plus_allowed_values(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "Compound": {
                        "Fn::And": [
                            {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                            {
                                "Fn::Or": [
                                    {"Fn::Equals": [{"Ref": "Tier"}, "gold"]},
                                    {"Fn::Equals": [{"Ref": "Tier"}, "platinum"]},
                                ]
                            },
                        ]
                    },
                    "Plain": {"Fn::Equals": [{"Ref": "Region"}, "us-east-1"]},
                },
                "Parameters": {
                    "Env": {
                        "Type": "String",
                        "AllowedValues": ["prod", "dev"],
                    },
                    "Tier": {"Type": "String"},
                    "Region": {"Type": "String"},
                },
                "Rules": {
                    "RegionRule": {
                        "Assertions": [
                            {
                                "Assert": {
                                    "Fn::Equals": [{"Ref": "Region"}, "us-east-1"]
                                },
                                "AssertDescription": "must be us-east-1",
                            }
                        ]
                    }
                },
            }
        )
        c = Conditions(cfn)
        assert set(c._conditions.keys()) == {"Compound", "Plain"}

    def test_repeated_static_true_then_dynamic(self):
        cfn = _CfnStub(
            {
                "Conditions": {
                    "Tautology": {"Fn::Equals": ["alpha", "alpha"]},
                    "DynamicAlpha": {
                        "Fn::Equals": [{"Ref": "Env"}, "alpha"]
                    },
                },
                "Parameters": {"Env": {"Type": "String"}},
            }
        )
        c = Conditions(cfn)
        assert set(c._conditions.keys()) == {"Tautology", "DynamicAlpha"}
