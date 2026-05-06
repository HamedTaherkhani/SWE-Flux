from __future__ import annotations

from typing import Any

import pytest

import reflex as rx
from reflex.components.component import Component
from reflex.components.core.foreach import Foreach, ForeachRenderError, ForeachVarError
from reflex.state import BaseState, ComponentState
from reflex.vars.base import Var


class ForeachCoverageState(BaseState):
    colors: list[str] = ["red", "blue"]
    rows: list[list[str]] = [["a", "b"], ["c", "d"]]
    profile: dict[str, str] = {"name": "Ada", "role": "admin"}
    title: str = "abcd"
    maybe_colors: rx.Field[list[str] | None] = rx.field(None)
    maybe_profile: rx.Field[dict[str, str] | None] = rx.field({"name": "Lin"})
    untyped_items: list = [["x"], ["y"]]


class ForeachCoverageComponentState(ComponentState):
    flag: bool

    @classmethod
    def get_component(cls, *children, **props) -> Component:
        return rx.box(*children, **props)


class TestCoreForeachCreateLineCoverageOneQA:
    def test_state_list_one_arg_render(self):
        component = rx.foreach(ForeachCoverageState.colors, lambda color: rx.text(color))

        assert isinstance(component, Foreach)


class TestCoreForeachCreateLineCoverageTwoQA:
    def test_state_list_two_arg_render(self):
        component = rx.foreach(
            ForeachCoverageState.rows,
            lambda row, index: rx.hstack(rx.text(row[0]), rx.text(index)),
        )

        assert isinstance(component, Foreach)


class TestCoreForeachCreateLineCoverageThreeQA:
    def test_state_dict_entries_render(self):
        component = rx.foreach(
            ForeachCoverageState.profile,
            lambda item: rx.text(item[0], item[1]),
        )

        assert "Object.entries" in component.render()["iterable_state"]


class TestCoreForeachCreateLineCoverageFourQA:
    def test_state_string_split_render(self):
        component = rx.foreach(ForeachCoverageState.title, lambda char: rx.text(char))

        assert ".split" in component.render()["iterable_state"]


class TestCoreForeachCreateLineCoverageFiveQA:
    def test_optional_list_uses_conditional_fallback(self):
        component = rx.foreach(ForeachCoverageState.maybe_colors, lambda color: rx.text(color))

        assert isinstance(component, Foreach)


class TestCoreForeachCreateLineCoverageSixQA:
    def test_optional_dict_uses_entries_and_conditional_fallback(self):
        component = rx.foreach(
            ForeachCoverageState.maybe_profile,
            lambda item: rx.text(item[0], item[1]),
        )

        assert isinstance(component, Foreach)


class TestCoreForeachCreateLineCoverageSevenQA:
    def test_literal_list_iterable(self):
        component = rx.foreach(["north", "south"], lambda label: rx.text(label))

        assert component.render()["iterable_state"] == '["north", "south"]'


class TestCoreForeachCreateLineCoverageEightQA:
    def test_any_typed_var_raises(self):
        with pytest.raises(ForeachVarError):
            rx.foreach(Var(_js_expr="state.dynamic_items", _var_type=Any), lambda item: rx.text(item))


class TestCoreForeachCreateLineCoverageNineQA:
    def test_component_state_render_fn_raises(self):
        with pytest.raises(TypeError):
            rx.foreach(ForeachCoverageState.colors, ForeachCoverageComponentState.create)


class TestCoreForeachCreateLineCoverageTenQA:
    def test_bad_render_signature_raises(self):
        def render_with_no_args() -> Any:
            return rx.text("missing")

        with pytest.raises(ForeachRenderError):
            rx.foreach(ForeachCoverageState.colors, render_with_no_args)
