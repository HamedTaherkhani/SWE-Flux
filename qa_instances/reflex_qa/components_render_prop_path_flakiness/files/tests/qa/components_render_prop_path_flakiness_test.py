from __future__ import annotations

from collections.abc import Callable
from typing import Any

import reflex as rx
from reflex.components.tags.tag import render_prop


def qa_callback() -> str:
    return "callback-result"


def make_component() -> rx.Component:
    return rx.hstack(rx.text("component"), rx.badge("rendered"))


def make_tuple() -> tuple[str, str]:
    return ("tuple-left", "tuple-right")


def make_nested_tuple() -> tuple[str, tuple[str, str]]:
    return ("outer", ("inner-left", "inner-right"))


def make_callable() -> Callable[[], str]:
    return qa_callback


def make_literal() -> str:
    return "literal-leaf"


FACTORIES: dict[str, Callable[[], Any]] = {
    "component": make_component,
    "tuple": make_tuple,
    "nested_tuple": make_nested_tuple,
    "callable": make_callable,
    "literal": make_literal,
}


class TestComponentsRenderPropPathFlakinessQA:
    def test_components_render_prop_path_flakiness_case(self):
        ordered_keys = set(FACTORIES)
        values = [FACTORIES[key]() for key in ordered_keys]

        rendered = render_prop(values)

        assert len(rendered) == len(FACTORIES)
        assert None in rendered
        assert any(isinstance(item, dict) and item.get("name") == "RadixThemesFlex" for item in rendered)
        assert any(isinstance(item, list) and "tuple-left" in item for item in rendered)
