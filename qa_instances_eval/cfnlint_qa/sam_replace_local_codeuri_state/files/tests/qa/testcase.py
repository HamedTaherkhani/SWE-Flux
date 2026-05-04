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

from cfnlint.helpers import REGION_PRIMARY
from cfnlint.template.transforms._sam import Transform

_TEMPLATE = {
    "Transform": "AWS::Serverless-2016-10-31",
    "Globals": {
        "Function": {
            "AutoPublishAlias": {"Ref": "AliasParam"},
        },
    },
    "Parameters": {
        "AliasParam": {"Type": "String"},
        "OtherParam": {"Type": "String"},
    },
    "Resources": {
        "F1": {
            "Type": "AWS::Serverless::Function",
            "Properties": {
                "CodeUri": "./local",
                "AutoPublishAlias": {"Ref": "AliasParam"},
                "AutoPublishCodeSha256": {"Fn::Sub": "sha"},
            },
        },
        "F2": {
            "Type": "AWS::Serverless::Function",
            "Properties": {
                "PackageType": "Image",
                "ImageUri": "./img",
                "AutoPublishAlias": {"Ref": "NotInParams"},
            },
        },
        "F3": {
            "Type": "AWS::Serverless::Function",
            "Properties": {
                "CodeUri": "s3://existing/path",
                "AutoPublishCodeSha256": "sha-as-string",
            },
        },
        "L1": {
            "Type": "AWS::Serverless::LayerVersion",
            "Properties": {"ContentUri": "./layer"},
        },
        "L2": {
            "Type": "AWS::Serverless::LayerVersion",
            "Properties": {},
        },
        "A1": {
            "Type": "AWS::Serverless::Api",
            "Properties": {"StageName": "prod"},
        },
        "A2": {
            "Type": "AWS::Serverless::Api",
            "Properties": {
                "StageName": "prod",
                "DefinitionBody": {"swagger": "2.0"},
            },
        },
        "A3": {
            "Type": "AWS::Serverless::Api",
            "Properties": {
                "StageName": "prod",
                "Cors": {"AllowOrigins": ["*"]},
            },
        },
        "App1": {
            "Type": "AWS::Serverless::Application",
            "Properties": {
                "Location": {"Bucket": "b", "Key": "k", "Version": "1"},
            },
        },
        "App2": {
            "Type": "AWS::Serverless::Application",
            "Properties": {"Location": "./local-app"},
        },
        "S1": {
            "Type": "AWS::Serverless::StateMachine",
            "Properties": {"DefinitionUri": "./sm"},
        },
        "S2": {
            "Type": "AWS::Serverless::StateMachine",
            "Properties": {"DefinitionString": "inline"},
        },
        "NoProps": {"Type": "AWS::Serverless::Function"},
        "BadProps": {
            "Type": "AWS::Serverless::Function",
            "Properties": "broken",
        },
        "Bucket": {
            "Type": "AWS::S3::Bucket",
            "Properties": {"BucketName": "foo"},
        },
    },
}

class TestSamReplaceLocalCodeuriStateQA:
    def test_sam_replace_local_codeuri_state_case(self):
        t = Transform("foo.yaml", _TEMPLATE, REGION_PRIMARY)
        t._replace_local_codeuri()
        assert t._parameters == {"AliasParam": "Alias"}
        assert t._template["Resources"]["F1"]["Properties"]["CodeUri"] == "s3://bucket/value"
