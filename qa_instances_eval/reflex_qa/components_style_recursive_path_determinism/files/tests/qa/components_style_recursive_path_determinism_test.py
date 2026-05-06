from __future__ import annotations

import reflex as rx


class TestComponentsStyleRecursivePathDeterminismQA:
    def test_components_style_recursive_path_determinism_case(self):
        panel = rx.box(
            rx.vstack(
                rx.heading("Operations", size="5", id="title"),
                rx.hstack(
                    rx.badge("queued", color_scheme="amber"),
                    rx.text("north"),
                    rx.button("sync", variant="outline"),
                    spacing="2",
                ),
                rx.grid(
                    rx.card(rx.text("alpha"), rx.text("42")),
                    rx.card(rx.text("beta"), rx.badge("ready")),
                    rx.box(rx.text("footer"), padding="2"),
                    columns="3",
                    spacing="2",
                ),
                rx.flex(
                    rx.text("left"),
                    rx.text("right"),
                    direction="row",
                    gap="2",
                ),
                spacing="3",
            ),
            padding="4",
            background="mint",
            border_radius="12px",
        )

        styled = panel._add_style_recursive(
            {
                rx.box: {"border": "1px solid var(--gray-5)"},
                rx.vstack: {"gap": "1rem"},
                rx.hstack: {"align_items": "center"},
                rx.text: {"font_weight": "500"},
                rx.button: {"cursor": "pointer"},
                rx.card: {"box_shadow": "sm"},
            }
        )

        assert styled is panel
        assert len(panel.children[0].children) == 4
        assert str(panel.style["padding"]) == '"4"'
