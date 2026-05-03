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
from cfnlint.template.transforms._language_extensions import _Transform

def _make_cfn(extra: dict) -> Template:
    template = {
        "Transform": ["AWS::LanguageExtensions"],
        "Mappings": {
            "Sizes": {
                "small": {"cpu": "256", "mem": "512"},
                "large": {"cpu": "1024", "mem": "2048"},
            }
        },
        "Parameters": {
            "Env": {
                "Type": "String",
                "AllowedValues": ["dev", "prod"],
                "Default": "dev",
            },
        },
        "Resources": {},
    }
    template.update(extra)
    return Template("", template)

class TestLanguageExtensionsWalkDefUsePairsQA:
    def test_language_extensions_walk_def_use_pairs_case(self):
        cfn_a = _make_cfn(
            {
                "Resources": {
                    "Fn::ForEach::EnvLoop": [
                        "Env",
                        ["dev", "prod"],
                        {
                            "Bucket${Env}": {
                                "Type": "AWS::S3::Bucket",
                                "Properties": {
                                    "BucketName": {"Fn::Sub": "${Env}-bucket"},
                                },
                            }
                        },
                    ]
                }
            }
        )
        errors, out = _Transform().transform(cfn_a)
        assert errors == []
        assert "Bucketdev" in out["Resources"]
        assert "Bucketprod" in out["Resources"]

        cfn_b = _make_cfn(
            {"Resources": {"X": {"Properties": {"P": {"Fn::ToJsonString": {"a": 1}}}}}}
        )
        _, out = _Transform().transform(cfn_b)
        assert "Fn::ToJsonString" in out["Resources"]["X"]["Properties"]["P"]

        cfn_c = _make_cfn(
            {
                "Resources": {
                    "X": {
                        "Properties": {
                            "ListForm": {"Fn::GetAtt": ["Resource1", "Arn"]},
                            "StrForm": {"Fn::GetAtt": "Resource1.Arn"},
                        }
                    }
                }
            }
        )
        _, out = _Transform().transform(cfn_c)
        assert out["Resources"]["X"]["Properties"]["ListForm"] is not None

        cfn_d = _make_cfn(
            {"Resources": {"X": {"Properties": {"P": {"Fn::Sub": "literal"}}}}}
        )
        _, out = _Transform().transform(cfn_d)

        cfn_e = _make_cfn(
            {
                "Resources": {
                    "X": {
                        "Properties": {
                            "P": {
                                "Fn::Sub": [
                                    "${Custom}-suffix",
                                    {"Custom": "rendered"},
                                ]
                            }
                        }
                    }
                }
            }
        )
        _, out = _Transform().transform(cfn_e)

        cfn_f = _make_cfn(
            {
                "Resources": {
                    "X": {
                        "Properties": {
                            "Cpu": {"Fn::FindInMap": ["Sizes", "small", "cpu"]},
                        }
                    }
                }
            }
        )
        _, out = _Transform().transform(cfn_f)
        assert out["Resources"]["X"]["Properties"]["Cpu"] == "256"

        cfn_g = _make_cfn(
            {
                "Resources": {
                    "X": {
                        "Properties": {
                            "Cpu": {
                                "Fn::FindInMap": [
                                    "MissingMap",
                                    {"Ref": "Env"},
                                    "cpu",
                                ]
                            }
                        }
                    }
                }
            }
        )
        _, out = _Transform().transform(cfn_g)

        cfn_h = _make_cfn(
            {
                "Resources": {
                    "Fn::ForEach::EnvLoop": [
                        "Env",
                        ["alpha"],
                        {
                            "Q${Env}": {
                                "Type": "AWS::Custom",
                                "Properties": {
                                    "InParams": {"Ref": "Env"},
                                    "NotInParams": {"Ref": "AWS::Region"},
                                    "DictRef": {"Ref": {"Fn::Sub": "Env"}},
                                },
                            }
                        },
                    ],
                }
            }
        )
        _, out = _Transform().transform(cfn_h)

        cfn_i = _make_cfn(
            {
                "Outputs": {
                    "Items": [
                        "literal-1",
                        {"Ref": "Env"},
                        42,
                        None,
                        {"Fn::Sub": "${Env}-x"},
                    ],
                },
            }
        )
        _, out = _Transform().transform(cfn_i)

        cfn_j = _make_cfn(
            {
                "Outputs": {
                    "Foo": {"Drop": None, "Keep": "kept"},
                },
            }
        )
        _, out = _Transform().transform(cfn_j)
        assert out["Outputs"]["Foo"].get("Keep") == "kept"
