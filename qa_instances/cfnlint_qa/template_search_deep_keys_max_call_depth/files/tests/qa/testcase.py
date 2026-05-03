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

_TEMPLATE = {
    "Description": "test",
    "Outputs": {
        "OutA": {"Value": {"Ref": "Bucket"}},
    },
    "Resources": {
        "Bucket": {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": "shallow",
                "Tags": [
                    {"Key": "Env", "Value": "prod"},
                    [
                        [
                            {"Inner": {"Tag": {"Key": "k", "Value": "v"}}}
                        ]
                    ],
                ],
            },
        },
        "OtherR": {
            "Type": "AWS::S3::Bucket",
            "Properties": {"Name": "x"},
        },
    },
}

class TestTemplateSearchDeepKeysMaxCallDepthQA:
    def test_template_search_deep_keys_max_call_depth_case(self):
        cfn = Template("foo.yaml", _TEMPLATE, ["us-east-1"])
        assert "Ref" in cfn.transform_pre
        assert "Fn::Sub" in cfn.transform_pre
        assert "Fn::If" in cfn.transform_pre
        assert "Fn::FindInMap" in cfn.transform_pre
        assert "Fn::ForEach" in cfn.transform_pre
        ref_paths = cfn.transform_pre["Ref"]
        assert len(ref_paths) == 1
        assert ref_paths[0][:5] == ["Outputs", "OutA", "Value", "Ref", "Bucket"]
