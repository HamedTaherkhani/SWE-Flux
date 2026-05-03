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

from cfnlint.context._mappings import Mappings
from cfnlint.context.context import Context, Parameter
from cfnlint.jsonschema import ValidationError
from cfnlint.jsonschema.validators import CfnTemplateValidator

class TestJsonschemaFindInMapDefUsePairsQA:
    def test_jsonschema_find_in_map_def_use_pairs_case(self):
        context = Context(
            parameters={
                "Tier": Parameter(
                    {
                        "Type": "String",
                        "AllowedValues": ["gold", "silver"],
                    }
                ),
            },
            mappings=Mappings.create_from_dict(
                {
                    "App": {
                        "us-east-1": {"cpu": "1024", "mem": "512"},
                        "eu-west-1": {"cpu": "2048", "mem": "256"},
                    },
                    "Acct": {"123456789012": {"profile": "prod", "alt": "dr"}},
                    "Nums": {"1": {"2": "forty-two"}},
                    "Tiers": {
                        "gold": {"quota": "high"},
                        "silver": {"quota": "low"},
                    },
                }
            ),
        )
        v = CfnTemplateValidator().evolve(context=context)

        def resolve(inst):
            return list(v.resolve_value(inst))

        out_default = resolve(
            {
                "Fn::FindInMap": [
                    "App",
                    "us-east-1",
                    "cpu",
                    {"DefaultValue": "fallback-cpu"},
                ]
            }
        )
        assert any(r[0] == "fallback-cpu" for r in out_default)
        assert any(r[0] == "1024" for r in out_default)

        bad_map = resolve({"Fn::FindInMap": ["NoSuch", "a", "b"]})
        assert any(isinstance(r[2], ValidationError) for r in bad_map)

        bad_top = resolve({"Fn::FindInMap": ["App", "unknown-region", "cpu"]})
        assert any(isinstance(r[2], ValidationError) for r in bad_top)

        acct = resolve(
            {"Fn::FindInMap": ["Acct", {"Ref": "AWS::AccountId"}, "profile"]}
        )
        assert any(r[0] == "prod" for r in acct)

        nums = resolve({"Fn::FindInMap": ["Nums", 1, 2]})
        assert any(r[0] == "forty-two" for r in nums)

        tiers = resolve({"Fn::FindInMap": ["Tiers", {"Ref": "Tier"}, "quota"]})
        assert {r[0] for r in tiers if r[2] is None} == {"high", "low"}
