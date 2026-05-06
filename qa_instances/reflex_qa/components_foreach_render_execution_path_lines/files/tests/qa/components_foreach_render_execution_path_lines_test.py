from __future__ import annotations

import reflex as rx
from reflex.vars.base import Var
from reflex.vars.sequence import ArrayVar


def render_row(item, ix):
    return rx.hstack(
        rx.text(item["name"], class_name=["name", "cell"]),
        rx.badge(ix),
        rx.text(item["status"].upper()),
        spacing="2",
    )


class TestComponentsForeachRenderExecutionPathLinesQA:
    def test_components_foreach_render_execution_path_lines_case(self):
        rows = Var(
            _js_expr="state.rows.filter((row) => row.visible)",
            _var_type=list[dict[str, str]],
        ).to(ArrayVar, list[dict[str, str]])

        component = rx.foreach(rows, render_row)
        rendered = component.render()

        assert type(component).__name__ == "Foreach"
        assert rendered["arg_name"] == "item"
        assert str(rendered["arg_index"]) == "ix"
        assert len(component.children) == 1
