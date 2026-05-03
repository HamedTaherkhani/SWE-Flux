from __future__ import annotations

import sys
from pathlib import Path

def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "src" / "cfnlint").is_dir():
            return p
    raise RuntimeError("Could not locate cfnlint source tree (expected .../src/cfnlint).")

sys.path.insert(0, str(_find_repo_root() / "src"))

from cfnlint.context.conditions._utils import build_instance_from_scenario
from cfnlint.context.context import Context
from cfnlint.decode.mark import Mark
from cfnlint.decode.node import dict_node, list_node

class TestConditionsBuildInstanceFromScenarioDefUsePairsQA:
    def test_conditions_build_instance_from_scenario_def_use_pairs_case(self):
        mark = Mark(0, 0)
        context = Context(functions=["Fn::If", "Ref"])
        scenario = {
            "UseProd": True,
            "UseFeature": False,
            "EnableDeep": True,
        }

        template = dict_node(
            {
                "Title": {"Fn::If": ["UseProd", "production", "sandbox"]},
                "Meta": dict_node(
                    {
                        "Fn::If": [
                            "UseProd",
                            {
                                "Fn::If": [
                                    "UseFeature",
                                    {"Fn::If": ["UseProd", "A", "B"]},
                                    {"Fn::If": ["EnableDeep", 100, 200]},
                                ]
                            },
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    mark,
                    mark,
                ),
                "Items": list_node(
                    [
                        {"Fn::If": ["MissingCondition", "never", "also-never"]},
                        {"Ref": "AWS::NoValue"},
                        {
                            "Fn::If": [
                                "EnableDeep",
                                {
                                    "Fn::If": [
                                        "UseProd",
                                        dict_node({"leaf": "ok"}, mark, mark),
                                        "fallback",
                                    ]
                                },
                                None,
                            ]
                        },
                    ],
                    mark,
                    mark,
                ),
            },
            mark,
            mark,
        )

        result = build_instance_from_scenario(template, scenario, True, context)

        assert result["Title"] == "production"
        assert result["Meta"] == 100
        assert isinstance(result["Items"], list)
        assert len(result["Items"]) == 2
        assert "Fn::If" in result["Items"][0]
        assert result["Items"][1] == {"leaf": "ok"}
