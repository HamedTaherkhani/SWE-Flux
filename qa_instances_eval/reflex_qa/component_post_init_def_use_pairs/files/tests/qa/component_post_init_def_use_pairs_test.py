from __future__ import annotations

import reflex as rx
from reflex.components.radix.themes.layout.box import Box


class TestComponentPostInitDefUsePairsQA:
    def test_component_post_init_def_use_pairs_case(self):
        component = Box.create(
            rx.text(
                "Alpha",
                data_role="label",
                style={"font_weight": "600"},
            ),
            id="qa-box",
            class_name=["outer", "dense"],
            style=[
                {"color": "tomato", "padding": "1"},
                {"padding": "2", "margin_top": "3"},
            ],
            data_state="open",
            aria_label="QA panel",
            on_click=rx.console_log("clicked"),
        )

        assert isinstance(component, Box)
        assert component.id == "qa-box"
        assert component.class_name == "outer dense"
        assert component.custom_attrs["data-state"] == "open"
        assert component.custom_attrs["aria-label"] == "QA panel"
        assert str(component.style["padding"]) == '"2"'

