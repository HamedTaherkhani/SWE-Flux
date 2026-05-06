from __future__ import annotations

import reflex as rx


class TestComponentsStyleRecursiveCallFrequencyQA:
    def test_components_style_recursive_call_frequency_case(self):
        panel = rx.box(
            rx.vstack(
                rx.text("north"),
                rx.hstack(
                    rx.text("east"),
                    rx.text("west"),
                    rx.button("sync", variant="outline"),
                    spacing="2",
                ),
                rx.card(rx.text("inside card"), rx.badge("ready")),
                rx.grid(
                    rx.text("a"),
                    rx.text("b"),
                    rx.text("c"),
                    columns="3",
                ),
                spacing="3",
            ),
            padding="4",
            background="mint",
        )

        styled_panel = panel._add_style_recursive(
            {
                rx.box: {"border_radius": "8px"},
                rx.text: {"font_weight": "500"},
                rx.button: {"cursor": "pointer"},
            }
        )

        assert styled_panel is panel
        assert str(panel.style["padding"]) == '"4"'
        assert str(panel.style["background"]) == '"mint"'
        assert len(panel.children[0].children) == 4
