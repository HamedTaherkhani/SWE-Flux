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

_TEMPLATE = {
    "Resources": {
        "Stack": {
            "Type": "AWS::CloudFormation::Stack",
            "Properties": {
                "Parameters": {
                    "Greeting": {"Fn::Sub": "Hi ${World}"},
                    "Region": {"Fn::Select": [0, {"Fn::GetAZs": ""}]},
                    "Env": {"Ref": "EnvName"},
                },
                "Tags": [
                    {
                        "Key": "When",
                        "Value": {"Fn::If": ["IsProd", "now", "later"]},
                    },
                    {"Key": "Where", "Value": "static"},
                ],
                "Transform": {
                    "Fn::Transform": {
                        "Name": "Macro",
                        "Parameters": {"Foo": {"Fn::Sub": "x-${Y}"}},
                    },
                },
            },
        },
    },
    "Outputs": {
        "Bucket": {"Value": {"Fn::GetAtt": ["S3Bucket", "Arn"]}},
    },
}

class TestTemplateSearchDeepKeysOuterPathsStateQA:
    def test_template_search_deep_keys_outer_paths_state_case(self):
        cfn = Template("", _TEMPLATE)
        result = cfn.search_deep_keys(re.compile(r"^Fn::"), includeGlobals=False)
        assert isinstance(result, list)
        assert len(result) >= 1
