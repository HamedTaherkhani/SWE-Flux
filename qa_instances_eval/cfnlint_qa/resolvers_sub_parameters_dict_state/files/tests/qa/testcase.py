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
from cfnlint.jsonschema._resolvers_cfn import sub
from cfnlint.jsonschema.validators import CfnTemplateValidator

def _make_validator():
    context = Context(
        parameters={
            "Env": Parameter(
                {"Type": "String", "AllowedValues": ["prod", "dev"]}
            ),
            "StackName": Parameter({"Type": "String", "Default": "demo"}),
            "Owner": Parameter({"Type": "String", "Default": "team"}),
        },
    )
    return CfnTemplateValidator().evolve(context=context)

class TestResolversSubParametersDictStateQA:
    def test_resolvers_sub_parameters_dict_state_case(self):
        v = _make_validator()
        instance = [
            (
                "${StackName}-${!literal}-${StackName}."
                "${Domain.Suffix}+${Env}_${Domain.Subdomain}@${Owner}"
            ),
            {"Env": "prod", "Domain.Suffix": "example.com"},
        ]
        list(sub(v, instance))
