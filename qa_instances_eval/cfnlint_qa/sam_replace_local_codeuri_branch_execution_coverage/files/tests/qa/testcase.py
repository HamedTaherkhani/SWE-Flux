from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

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

from cfnlint.template.transforms._sam import Transform

def _drive(template: Mapping[str, Any]) -> None:
    Transform("foo.yaml", dict(template), "us-east-1")._replace_local_codeuri()

class TestSamReplaceLocalCodeUriBranchExecutionCoverageQA:

    def test_branch_execution_case_01(self):
        _drive({})

    def test_branch_execution_case_02(self):
        _drive(
            {
                "Globals": {
                    "Function": {
                        "AutoPublishAlias": {"Ref": "P", "Extra": "x"}
                    }
                },
                "Parameters": {"P": {"Type": "String"}},
            }
        )

    def test_branch_execution_case_03(self):
        _drive(
            {
                "Globals": {
                    "Function": {"AutoPublishAlias": {"Ref": "P"}}
                },
                "Parameters": {"P": {"Type": "String"}},
            }
        )

    def test_branch_execution_case_04(self):
        _drive(
            {
                "Globals": {
                    "Function": {"AutoPublishAlias": {"Ref": "Undeclared"}}
                },
                "Parameters": {"Other": {"Type": "String"}},
            }
        )

    def test_branch_execution_case_05(self):
        _drive(
            {
                "Globals": {
                    "Function": {"AutoPublishAlias": {"Fn::Sub": "x"}}
                },
                "Parameters": {},
            }
        )

    def test_branch_execution_case_06(self):
        _drive(
            {
                "Resources": {
                    "Bad": {"Type": "AWS::S3::Bucket", "Properties": None}
                }
            }
        )

    def test_branch_execution_case_07(self):
        _drive(
            {
                "Resources": {
                    "Fn1": {
                        "Type": "AWS::Serverless::Function",
                        "Properties": {
                            "PackageType": "Image",
                            "ImageUri": "./img",
                        },
                    }
                }
            }
        )

    def test_branch_execution_case_08(self):
        _drive(
            {
                "Resources": {
                    "Fn2": {
                        "Type": "AWS::Serverless::Function",
                        "Properties": {"CodeUri": "./code"},
                    }
                }
            }
        )

    def test_branch_execution_case_09(self):
        _drive(
            {
                "Parameters": {"MyParam": {"Type": "String"}},
                "Resources": {
                    "Fn3": {
                        "Type": "AWS::Serverless::Function",
                        "Properties": {
                            "CodeUri": "./code",
                            "AutoPublishAlias": {"Ref": "MyParam"},
                        },
                    }
                },
            }
        )

    def test_branch_execution_case_10(self):
        _drive(
            {
                "Resources": {
                    "Fn4": {
                        "Type": "AWS::Serverless::Function",
                        "Properties": {
                            "CodeUri": "./code",
                            "AutoPublishCodeSha256": {"Ref": "Sha"},
                        },
                    }
                }
            }
        )

    def test_branch_execution_case_11(self):
        _drive(
            {
                "Resources": {
                    "L1": {
                        "Type": "AWS::Serverless::LayerVersion",
                        "Properties": {"ContentUri": "./layer"},
                    }
                }
            }
        )

    def test_branch_execution_case_12(self):
        _drive(
            {
                "Resources": {
                    "App1": {
                        "Type": "AWS::Serverless::Application",
                        "Properties": {
                            "Location": {"ApplicationId": "x"},
                        },
                    }
                }
            }
        )

    def test_branch_execution_case_13(self):
        _drive(
            {
                "Resources": {
                    "Api1": {
                        "Type": "AWS::Serverless::Api",
                        "Properties": {
                            "DefinitionUri": "./api",
                            "StageName": "prod",
                        },
                    }
                }
            }
        )

    def test_branch_execution_case_14(self):
        _drive(
            {
                "Resources": {
                    "Api2": {
                        "Type": "AWS::Serverless::Api",
                        "Properties": {
                            "DefinitionBody": {"openapi": "3.0"},
                            "StageName": "prod",
                        },
                    }
                }
            }
        )

    def test_branch_execution_case_15(self):
        _drive(
            {
                "Resources": {
                    "Sm1": {
                        "Type": "AWS::Serverless::StateMachine",
                        "Properties": {"DefinitionUri": "./sm.asl.json"},
                    }
                }
            }
        )
