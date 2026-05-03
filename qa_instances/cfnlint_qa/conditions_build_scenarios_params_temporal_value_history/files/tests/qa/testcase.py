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

def _make_cfn() -> Template:
    template = {
        "Parameters": {
            "Env": {
                "Type": "String",
                "AllowedValues": ["prod", "dev", "stage", "qa"],
            },
        },
        "Conditions": {
            "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
            "IsDev": {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
            "IsStage": {"Fn::Equals": [{"Ref": "Env"}, "stage"]},
            "IsQa": {"Fn::Equals": [{"Ref": "Env"}, "qa"]},
        },
    }
    return Template("", template)

class TestConditionsBuildScenariosParamsTemporalHistoryQA:
    def test_conditions_build_scenarios_params_temporal_value_history_case(self):
        cfn = _make_cfn()

        assert list(cfn.conditions.build_scenarios({})) == []

        list(cfn.conditions.build_scenarios({"IsProd": None}))

        list(cfn.conditions.build_scenarios({"IsProd": None, "IsDev": None}))

        list(
            cfn.conditions.build_scenarios(
                {"IsProd": None, "IsDev": None, "IsStage": None}
            )
        )

        list(
            cfn.conditions.build_scenarios({"IsProd": {True}, "IsDev": None})
        )

        list(
            cfn.conditions.build_scenarios({"IsProd": {False}, "IsDev": None})
        )

        list(
            cfn.conditions.build_scenarios(
                {"IsProd": {True}, "IsDev": {False}}
            )
        )

        list(
            cfn.conditions.build_scenarios(
                {
                    "IsProd": {True},
                    "IsDev": {False},
                    "IsStage": {False},
                }
            )
        )

        list(
            cfn.conditions.build_scenarios({"IsStage": None, "IsProd": None})
        )

        list(
            cfn.conditions.build_scenarios(
                {
                    "IsProd": {True},
                    "IsDev": None,
                    "IsStage": {False},
                }
            )
        )

        list(cfn.conditions.build_scenarios({"GhostCondition": None}))

        list(
            cfn.conditions.build_scenarios(
                {"Ghost1": None, "Ghost2": None}
            )
        )

        list(
            cfn.conditions.build_scenarios(
                {"Ghost": None, "IsProd": None}
            )
        )

        list(cfn.conditions.build_scenarios({"IsProd": None}))

        list(
            cfn.conditions.build_scenarios({"IsProd": {True, False}})
        )
