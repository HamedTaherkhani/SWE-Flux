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
from cfnlint.jsonschema._resolvers_cfn import join
from cfnlint.jsonschema.validators import CfnTemplateValidator

def _make_validator():
    context = Context(
        parameters={
            "Env": Parameter(
                {"Type": "String", "AllowedValues": ["prod", "dev"]}
            ),
            "Suffix": Parameter({"Type": "String", "Default": "tail"}),
        },
    )
    return CfnTemplateValidator().evolve(context=context)

class TestResolversJoinDefUsePairsQA:
    def test_resolvers_join_def_use_pairs_case(self):
        v = _make_validator()

        out_a = list(join(v, [",", ["a", "b", "c"]]))
        assert any(r[0] == "a,b,c" for r in out_a)

        out_b = list(join(v, ["-", ["only"]]))
        assert any(r[0] == "only" for r in out_b)

        out_c = list(join(v, [":", []]))
        assert out_c == []

        out_d = list(join(v, [["bad", "delim"], ["a", "b"]]))
        assert out_d == []

        out_e = list(join(v, [",", "not-a-list"]))
        assert out_e == []

        out_f = list(join(v, "not-an-array"))
        assert out_f == []

        out_g = list(join(v, [",", ["a"], "extra"]))
        assert out_g == []

        out_h = list(join(v, [{"Ref": "AWS::Region"}, ["pre", "post"]]))
        assert all("pre" in r[0] and "post" in r[0] for r in out_h)

        out_i = list(join(v, [{"Ref": "Env"}, ["x", "y"]]))
        assert {r[0] for r in out_i} == {"xprody", "xdevy"}

        out_j = list(join(v, [",", [{"Ref": "Env"}, "literal"]]))
        assert {r[0] for r in out_j} == {"prod,literal", "dev,literal"}

        out_k = list(join(v, [",", [{"NestedNotFn": "x"}]]))
        assert out_k == []

        out_l = list(
            join(
                v,
                [
                    {"Ref": "Env"},
                    [{"Ref": "Env"}, "tail"],
                ],
            )
        )
        assert {r[0] for r in out_l} == {"prodprodtail", "devdevtail"}
