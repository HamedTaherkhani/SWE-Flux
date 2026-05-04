from __future__ import annotations

import sys
from pathlib import Path

import regex as re

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

def _make_template(body):
    return Template("", body, regions=["us-east-1"])

class TestTemplateSearchDeepKeysChronologicalMonotonicitySuiteQA:

    def test_search_ref_in_flat_resources(self):
        cfn = _make_template(
            {
                "Resources": {
                    "B": {
                        "Type": "AWS::S3::Bucket",
                        "Properties": {"BucketName": {"Ref": "Name"}},
                    }
                }
            }
        )
        out = cfn.search_deep_keys("Ref")
        assert any(p[-2] == "Ref" for p in out)

    def test_search_no_matches(self):
        cfn = _make_template({"Resources": {"X": {"Type": "AWS::S3::Bucket"}}})
        out = cfn.search_deep_keys("Fn::Sub")
        assert out == []

    def test_search_in_empty_template(self):
        cfn = _make_template({})
        out = cfn.search_deep_keys("Ref")
        assert out == []

    def test_search_ref_nested_two_levels(self):
        cfn = _make_template(
            {
                "Resources": {
                    "Q": {
                        "Type": "AWS::SQS::Queue",
                        "Properties": {
                            "Tags": [{"Key": "k", "Value": {"Ref": "EnvParam"}}]
                        },
                    }
                }
            }
        )
        out = cfn.search_deep_keys("Ref")
        assert len(out) >= 1

    def test_search_ref_nested_three_levels(self):
        cfn = _make_template(
            {
                "Resources": {
                    "T": {
                        "Type": "AWS::DynamoDB::Table",
                        "Properties": {
                            "AttributeDefinitions": [
                                {"AttributeName": {"Ref": "AttrA"}, "AttributeType": "S"},
                                {"AttributeName": {"Ref": "AttrB"}, "AttributeType": "N"},
                            ]
                        },
                    }
                }
            }
        )
        out = cfn.search_deep_keys("Ref")
        assert len(out) >= 2

    def test_search_with_list_inside_dict_inside_list(self):
        cfn = _make_template(
            {
                "Resources": {
                    "R": {
                        "Type": "Demo",
                        "Properties": {
                            "Outer": [
                                {"Inner": [{"Leaf": {"Ref": "P1"}}]},
                                {"Inner": [{"Leaf": {"Ref": "P2"}}]},
                            ]
                        },
                    }
                }
            }
        )
        out = cfn.search_deep_keys("Ref")
        assert len(out) == 2

    def test_search_across_multiple_sections(self):
        cfn = _make_template(
            {
                "Parameters": {"P": {"Type": "String", "Default": "x"}},
                "Conditions": {"C": {"Fn::Equals": [{"Ref": "P"}, "x"]}},
                "Resources": {
                    "R": {
                        "Type": "AWS::S3::Bucket",
                        "Properties": {"BucketName": {"Ref": "P"}},
                    }
                },
                "Outputs": {"O": {"Value": {"Ref": "R"}}},
            }
        )
        out = cfn.search_deep_keys("Ref")
        assert len(out) == 3

    def test_search_regex_pattern_matches_fn_double_colon(self):
        cfn = _make_template(
            {
                "Resources": {
                    "R": {
                        "Type": "AWS::S3::Bucket",
                        "Properties": {
                            "BucketName": {"Fn::Sub": "bn-${AWS::Region}"},
                            "Tags": [{"Key": "k", "Value": {"Fn::Join": [",", ["a", "b"]]}}],
                        },
                    }
                }
            }
        )
        pat = re.compile(r"^Fn::.*$")
        out = cfn.search_deep_keys(pat)
        assert len(out) >= 2

    def test_search_regex_pattern_no_match(self):
        cfn = _make_template({"Resources": {"R": {"Type": "Demo"}}})
        pat = re.compile(r"^DoesNotExist$")
        out = cfn.search_deep_keys(pat)
        assert out == []

    def test_search_includes_globals_when_present(self):
        cfn = _make_template(
            {
                "Resources": {
                    "R": {
                        "Type": "AWS::S3::Bucket",
                        "Properties": {"BucketName": {"Ref": "Name"}},
                    }
                }
            }
        )
        cfn.transform_pre = {"Globals": {"Function": {"Tags": {"K": {"Ref": "Other"}}}}}
        out = cfn.search_deep_keys("Ref", includeGlobals=True)
        assert any(p[0] == "Globals" for p in out)
        assert any(p[0] == "Resources" for p in out)

    def test_search_excludes_globals_when_disabled(self):
        cfn = _make_template(
            {
                "Resources": {
                    "R": {
                        "Type": "AWS::S3::Bucket",
                        "Properties": {"BucketName": {"Ref": "Name"}},
                    }
                }
            }
        )
        cfn.transform_pre = {"Globals": {"Function": {"Tags": {"K": {"Ref": "Other"}}}}}
        out = cfn.search_deep_keys("Ref", includeGlobals=False)
        assert all(p[0] != "Globals" for p in out)

    def test_search_in_list_only_root(self):
        cfn = _make_template({})
        out = cfn._search_deep_keys(
            "Ref", [{"Ref": "A"}, {"Ref": "B"}, [{"Ref": "C"}]], []
        )
        assert len(out) == 3

    def test_search_deeply_nested_six_levels(self):
        deep = {
            "L1": {
                "L2": {
                    "L3": {
                        "L4": {
                            "L5": {
                                "L6": {"Ref": "DeepParam"}
                            }
                        }
                    }
                }
            }
        }
        cfn = _make_template({"Resources": {"R": {"Type": "Demo", "Properties": deep}}})
        out = cfn.search_deep_keys("Ref")
        assert len(out) == 1
        assert out[0][-2] == "Ref"
        assert out[0][-1] == "DeepParam"

    def test_search_wide_branching_many_siblings(self):
        sib = {f"Field{i}": {"Ref": f"P{i}"} for i in range(8)}
        cfn = _make_template({"Resources": {"R": {"Type": "Demo", "Properties": sib}}})
        out = cfn.search_deep_keys("Ref")
        assert len(out) == 8

    def test_search_mixed_breadth_and_depth(self):
        cfn = _make_template(
            {
                "Resources": {
                    "A": {"Type": "X", "Properties": {"V1": {"Ref": "P1"}}},
                    "B": {"Type": "X", "Properties": {"V2": {"Ref": "P2"}}},
                    "C": {
                        "Type": "X",
                        "Properties": {
                            "V3": {
                                "Nest": {
                                    "Deeper": {"Ref": "P3"},
                                }
                            },
                            "V4": [{"Ref": "P4"}, {"Ref": "P5"}],
                        },
                    },
                }
            }
        )
        out = cfn.search_deep_keys("Ref")
        assert len(out) == 5

    def test_search_fn_sub_multiple_locations(self):
        cfn = _make_template(
            {
                "Resources": {
                    "R1": {
                        "Type": "Demo",
                        "Properties": {
                            "A": {"Fn::Sub": "x-${AWS::Region}"},
                            "B": {"Fn::Sub": "y-${AWS::AccountId}"},
                        },
                    },
                    "R2": {
                        "Type": "Demo",
                        "Properties": {"C": {"Fn::Sub": "z-${AWS::StackName}"}},
                    },
                }
            }
        )
        out = cfn.search_deep_keys("Fn::Sub")
        assert len(out) == 3

    def test_search_fn_getatt_with_dotted_string(self):
        cfn = _make_template(
            {
                "Resources": {
                    "R": {
                        "Type": "Demo",
                        "Properties": {
                            "Att1": {"Fn::GetAtt": ["X", "Arn"]},
                            "Att2": {"Fn::GetAtt": "X.Arn"},
                        },
                    }
                }
            }
        )
        out = cfn.search_deep_keys("Fn::GetAtt")
        assert len(out) == 2

    def test_search_volume_many_resources(self):
        resources = {}
        for i in range(6):
            resources[f"R{i}"] = {
                "Type": "Demo",
                "Properties": {"Name": {"Ref": f"P{i}"}, "Other": "literal"},
            }
        cfn = _make_template({"Resources": resources})
        out = cfn.search_deep_keys("Ref")
        assert len(out) == 6

    def test_search_repeated_search_same_template(self):
        cfn = _make_template(
            {
                "Resources": {
                    "R": {
                        "Type": "Demo",
                        "Properties": {"V": {"Ref": "P"}, "W": {"Fn::Sub": "x"}},
                    }
                }
            }
        )
        a = cfn.search_deep_keys("Ref")
        b = cfn.search_deep_keys("Fn::Sub")
        assert len(a) == 1
        assert len(b) == 1

    def test_search_against_ref_pattern_regex(self):
        cfn = _make_template(
            {
                "Resources": {
                    "R": {
                        "Type": "Demo",
                        "Properties": {"V1": {"Ref": "A"}, "V2": {"Ref": "B"}},
                    }
                }
            }
        )
        pat = re.compile(r"^Ref$")
        out = cfn.search_deep_keys(pat)
        assert len(out) == 2

    def test_search_deeply_nested_with_lists_at_every_level(self):
        deep = {
            "Tier1": [
                {"Tier2": [{"Tier3": {"Leaf": {"Ref": "P1"}}}]},
                {"Tier2": [{"Tier3": {"Leaf": {"Ref": "P2"}}}]},
            ]
        }
        cfn = _make_template({"Resources": {"R": {"Type": "Demo", "Properties": deep}}})
        out = cfn.search_deep_keys("Ref")
        assert len(out) == 2
