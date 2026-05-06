from __future__ import annotations

import json

import reflex as rx
from reflex.components.base.bare import Bare, _components_from_var
from reflex.vars import Var, VarData


def _style_dict(component) -> dict[str, str]:
    return {key: str(value) for key, value in sorted(component.style.items())}


class TestBaseBareAddStyleRecursiveLoopStateQA:
    def test_base_bare_add_style_recursive_loop_state_case(self):
        embedded_box = rx.box(
            "box child",
            id="embedded-box",
            style={"padding": "1px", "bg": "lavender"},
        )
        embedded_text = rx.text(
            "text child",
            id="embedded-text",
            style={"color": "purple"},
        )
        embedded_button = rx.button(
            "button child",
            id="embedded-button",
            style={"border": "1px solid black"},
        )
        content_var = Var(
            _js_expr="embeddedValue",
            _var_type=str,
            _var_data=VarData(
                components=[embedded_box, embedded_text, embedded_button],
            ),
        )
        bare = Bare.create(content_var)
        style = {
            rx.box: {"margin_y": "2px", "border_radius": "4px"},
            rx.text: {"font_weight": "700", "letter_spacing": "0"},
            rx.button: {"background": "mintcream", "padding_x": "6px"},
        }

        returned = bare._add_style_recursive(style, theme=None)

        embedded_components = list(_components_from_var(bare.contents))
        result = {
            "are_components_touched": any(
                bool(component.style) for component in embedded_components
            ),
            "new_self is self": returned is bare,
            "new_self.style": _style_dict(returned),
            "self.contents._get_all_var_data().components": [
                {
                    "__class__": type(component).__name__,
                    "id": component.id,
                    "style": _style_dict(component),
                }
                for component in embedded_components
            ],
        }
        print("QA_RESULT_JSON=" + json.dumps(result, sort_keys=True))

        assert result["are_components_touched"] is True
        assert [
            component["__class__"]
            for component in result["self.contents._get_all_var_data().components"]
        ] == ["Box", "Text", "Button"]
