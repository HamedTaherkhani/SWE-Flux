from __future__ import annotations

import reflex as rx
from reflex.state import BaseState


class IterTagPathState(BaseState):
    labels: list[str] = ["alpha", "beta"]
    rows: list[list[str]] = [["north", "east"], ["south", "west"]]
    flags: list[bool] = [True, False]


class TestComponentsItertagRenderComponentPathDeterminismQA:
    def test_components_itertag_render_component_path_determinism_case(self):
        tuple_foreach = rx.foreach(
            IterTagPathState.labels,
            lambda label: (rx.text(label), rx.badge("item")),
        )
        cond_foreach = rx.foreach(
            IterTagPathState.flags,
            lambda flag, index: rx.cond(
                flag,
                rx.hstack(rx.text("yes"), rx.text(index)),
                rx.hstack(rx.text("no"), rx.text(index)),
            ),
        )
        nested_foreach = rx.foreach(
            IterTagPathState.rows,
            lambda row: rx.foreach(row, lambda cell: rx.text(cell)),
        )

        dashboard = rx.vstack(tuple_foreach, cond_foreach, nested_foreach)
        rendered = dashboard.render()

        assert rendered["name"] == "RadixThemesFlex"
        assert len(rendered["children"]) == 3
