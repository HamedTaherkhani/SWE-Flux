from __future__ import annotations

import json
from typing import Any

import reflex as rx
from reflex.app import UnevaluatedPage
from reflex.compiler.compiler import compile_unevaluated_page
from reflex.components.component import Component
from reflex.constants import DefaultPage
from reflex.event import EventChain, EventSpec
from reflex.utils import format


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


class CompileDirectState(rx.State):
    """State used by the direct compile output probe."""

    flag: bool = True
    count: int = 2
    labels: list[str] = ["alpha", "beta", "gamma"]

    def bump(self, amount: int = 1):
        self.count += amount

    def set_label(self, label: str):
        self.labels = [label, *self.labels]


def direct_page():
    """A page that forces compile_unevaluated_page through many internal paths."""
    return rx.vstack(
        rx.hstack(
            rx.text("Counter", id="caption", class_name=["headline", "dense"]),
            rx.cond(
                CompileDirectState.flag,
                rx.badge("live", color_scheme="green", data_kind="truthy"),
                rx.badge("paused", color_scheme="gray", data_kind="falsey"),
            ),
            spacing="3",
        ),
        rx.text(
            CompileDirectState.count,
            id="count-value",
            color="blue",
            margin_x="0.25rem",
        ),
        rx.foreach(
            CompileDirectState.labels,
            lambda label, ix: rx.hstack(
                rx.text(label, class_name=["label", "item"]),
                rx.button("select", on_click=CompileDirectState.set_label(label)),
                rx.text(ix),
                spacing="2",
            ),
        ),
        rx.button(
            "increment",
            on_click=[CompileDirectState.bump(3), rx.console_log("bumped")],
            data_action="primary",
            aria_label="increment counter",
        ),
        spacing="4",
        id="root-stack",
        style=[
            {"padding": "1rem", "bg": "white"},
            {"padding_x": "2rem", "color": "black"},
        ],
    )


def _walk_component(component: Component, depth: int = 0) -> list[dict[str, Any]]:
    row = {
        "depth": depth,
        "type": type(component).__name__,
        "tag": component.tag,
        "id": _stringify(component.id),
        "children": len(component.children),
        "events": sorted(component.event_triggers),
    }
    rows = [row]
    for child in component.children:
        if isinstance(child, Component):
            rows.extend(_walk_component(child, depth + 1))
        else:
            rows.append(
                {
                    "depth": depth + 1,
                    "type": type(child).__name__,
                    "tag": getattr(child, "tag", None),
                    "id": None,
                    "children": 0,
                    "events": [],
                }
            )
    return rows


def _button_event_summary(component: Component, path: str = "") -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    if type(component).__name__ == "Button":
        chain = component.event_triggers.get("on_click")
        events = []
        if isinstance(chain, EventChain):
            for event in chain.events:
                if isinstance(event, EventSpec):
                    events.append(
                        {
                            "handler": format.format_event_handler(event.handler),
                            "client_handler": event.client_handler_name,
                            "args": [
                                {
                                    "name": arg._js_expr,
                                    "expr": str(value),
                                    "literal": getattr(value, "_var_value", None),
                                }
                                for arg, value in event.args
                            ],
                        }
                    )
                else:
                    events.append({"var": str(event)})
        summaries.append(
            {
                "path": path,
                "text": [str(getattr(child, "contents", "")) for child in component.children],
                "custom_attrs": {
                    key: str(value) for key, value in sorted(component.custom_attrs.items())
                },
                "events": events,
            }
        )
    for index, child in enumerate(component.children):
        if isinstance(child, Component):
            child_path = f"{path}/{type(component).__name__}[{index}]"
            summaries.extend(_button_event_summary(child, child_path))
    return summaries


def _summarize_return(component: Component, enable_state: bool) -> dict[str, Any]:
    main = component.children[0]
    return {
        "returned_component_type": type(component).__name__,
        "enable_state": enable_state,
        "top_level_child_types": [type(child).__name__ for child in component.children],
        "main_child_types": [type(child).__name__ for child in main.children],
        "main_style": {
            key: str(value) for key, value in sorted(main.style.items())
        },
        "imports": sorted(component._get_all_imports().keys()),
        "hook_count": len(component._get_all_hooks()),
        "refs": sorted(component._get_all_refs()),
        "component_walk": _walk_component(component),
        "button_events": _button_event_summary(component),
    }


class TestCompilerCompileUnevaluatedPageDirectOutputQA:
    def test_compile_unevaluated_page_direct_output_case(self):
        page = UnevaluatedPage(
            component=direct_page,
            route="qa/[section]/[[...rest]]",
            title="Direct Compile QA",
            description="Direct compile output probe",
            image=DefaultPage.IMAGE,
            on_load=None,
            meta=[{"name": "robots", "content": "noindex"}],
        )

        component, enable_state = compile_unevaluated_page(
            "qa/[section]/[[...rest]]",
            page,
            state=None,
            style={
                rx.vstack: {"gap": "1rem", "border_radius": "8px"},
                rx.text: {"font_weight": "600"},
            },
            theme=rx.theme(accent_color="crimson"),
        )

        summary = _summarize_return(component, enable_state)
        print("QA_RESULT_JSON=" + json.dumps(summary, sort_keys=True))

        assert summary["returned_component_type"] == "OverlayFragment"
        assert summary["enable_state"] is True
        assert summary["main_child_types"] == ["HStack", "Text", "Foreach", "Button"]
