from __future__ import annotations

import reflex as rx


class TestComponentsNestedRenderCallFrequencyQA:
    def test_components_nested_render_call_frequency_case(self):
        dashboard = rx.vstack(
            rx.heading("Daily metrics", size="5"),
            rx.hstack(
                rx.badge("open", color_scheme="green"),
                rx.text("12"),
                rx.button("refresh", variant="soft"),
                spacing="2",
            ),
            rx.grid(
                rx.card(rx.text("alpha"), rx.text("42")),
                rx.card(rx.text("beta"), rx.text("17")),
                rx.card(rx.text("gamma"), rx.text("23")),
                columns="3",
                spacing="2",
            ),
            rx.box(rx.text("footer"), padding="2"),
            spacing="3",
        )

        rendered = dashboard.render()

        assert rendered["name"] == "RadixThemesFlex"
        assert len(rendered["children"]) == 4
        assert rendered["children"][1]["name"] == "RadixThemesFlex"
        assert rendered["children"][2]["name"] == "RadixThemesGrid"
        assert len(rendered["children"][2]["children"]) == 3
