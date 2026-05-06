from __future__ import annotations

import reflex as rx
from reflex.app import UnevaluatedPage
from reflex.compiler.compiler import compile_unevaluated_page
from reflex.constants import DefaultPage


class CompilePathState(rx.State):
    flag: bool = True
    count: int = 7
    labels: list[str] = ["red", "green", "blue"]

    def bump(self, amount: int = 1):
        self.count += amount


def compiler_path_page():
    return rx.vstack(
        rx.text(CompilePathState.count, id="count-value", color="tomato"),
        rx.cond(
            CompilePathState.flag,
            rx.badge("enabled", data_state="on"),
            rx.badge("disabled", data_state="off"),
        ),
        rx.foreach(
            CompilePathState.labels,
            lambda label: rx.hstack(
                rx.text(label, class_name=["label", "entry"]),
                rx.badge(label.length()),
                spacing="2",
            ),
        ),
        rx.button("bump", on_click=CompilePathState.bump(2), data_action="increment"),
        spacing="4",
        id="compiler-path-root",
    )


class TestCompilerUnevaluatedPageExecutionPathLinesQA:
    def test_compiler_unevaluated_page_execution_path_lines_case(self):
        page = UnevaluatedPage(
            component=compiler_path_page,
            route="qa/control-flow/[item]",
            title="Compiler Path QA",
            description="Compiler execution path probe",
            image=DefaultPage.IMAGE,
            on_load=None,
            meta=[{"name": "robots", "content": "noindex"}],
        )

        component, enable_state = compile_unevaluated_page(
            "qa/control-flow/[item]",
            page,
            state=None,
            style={
                rx.vstack: {"padding": "1rem", "gap": "0.5rem"},
                rx.text: {"font_weight": "700"},
            },
            theme=None,
        )

        assert type(component).__name__ == "OverlayFragment"
        assert enable_state is True
        assert any(type(child).__name__ == "Head" for child in component.children)
