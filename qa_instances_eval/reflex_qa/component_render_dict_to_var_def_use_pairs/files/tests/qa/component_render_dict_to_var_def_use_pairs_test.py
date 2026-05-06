from __future__ import annotations

from reflex.components.component import render_dict_to_var
from reflex.vars.base import Var


class TestComponentRenderDictToVarDefUsePairsQA:
    def test_component_render_dict_to_var_def_use_pairs_case(self):
        tag = {
            "name": "match",
            "cond": Var.create("status"),
            "default": {
                "name": "section",
                "props": ["id={\"fallback\"}", "data-count={items.length}"],
                "contents": "\"fallback\"",
                "children": [
                    {
                        "name": "span",
                        "props": ["className={\"muted\"}"],
                        "contents": "\"child\"",
                        "children": [],
                    }
                ],
            },
            "match_cases": [
                [
                    Var.create("ready"),
                    Var.create("done"),
                    {
                        "name": "strong",
                        "props": ["title={\"complete\"}"],
                        "contents": "\"yes\"",
                        "children": [],
                    },
                ],
                [
                    Var.create("waiting"),
                    {
                        "name": "em",
                        "props": [],
                        "contents": "\"maybe\"",
                        "children": [],
                    },
                ],
            ],
        }

        rendered = render_dict_to_var(tag, {"Box", "Text"})

        rendered_text = str(rendered)
        assert "JSON.stringify" in rendered_text
        assert "fallback" in rendered_text
        assert "complete" in rendered_text

