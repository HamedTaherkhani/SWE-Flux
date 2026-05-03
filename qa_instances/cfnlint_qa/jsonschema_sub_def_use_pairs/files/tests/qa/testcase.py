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

from cfnlint.context.context import Context, Parameter
from cfnlint.jsonschema.validators import CfnTemplateValidator

class TestJsonschemaSubDefUsePairsQA:
    def test_jsonschema_sub_def_use_pairs_case(self):
        context = Context(
            parameters={
                "Tier": Parameter(
                    {
                        "Type": "String",
                        "AllowedValues": ["gold", "silver"],
                    }
                ),
                "Code": Parameter(
                    {
                        "Type": "String",
                        "AllowedValues": ["pid-9"],
                    }
                ),
            },
        )
        v = CfnTemplateValidator().evolve(context=context)

        def consume(inst):
            return list(v.resolve_value(inst))

        out1 = consume({"Fn::Sub": ["${a}|${b}|${c}", {"a": "1", "b": "2", "c": "3"}]})
        assert any(r[0] == "1|2|3" for r in out1)

        out2 = consume({"Fn::Sub": ["id-${Code}", {}]})
        assert {r[0] for r in out2 if r[2] is None} == {"id-pid-9"}

        out3 = consume({"Fn::Sub": ["${AWS::Region}-${AWS::URLSuffix}", {}]})
        assert any(r[0] == "us-east-1-amazonaws.com" for r in out3 if r[2] is None)

        out4 = consume({"Fn::Sub": "${Tier}-static"})
        tiers = {r[0] for r in out4 if r[2] is None}
        assert tiers == {"gold-static", "silver-static"}

        out5 = consume({"Fn::Sub": ["no-vars", {}]})
        assert len(out5) == 1 and out5[0][0] == "no-vars" and out5[0][2] is None

        out6 = consume({"Fn::Sub": ["${Tier}/${Code}", {"Code": "z"}]})
        assert {r[0] for r in out6 if r[2] is None} == {"gold/z", "silver/z"}
