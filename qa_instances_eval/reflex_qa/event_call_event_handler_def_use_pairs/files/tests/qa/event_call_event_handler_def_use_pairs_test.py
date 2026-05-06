from __future__ import annotations

from reflex.event import EventHandler, call_event_handler
from reflex.utils import format
from reflex.vars.base import Var


def qa_handler(_, amount: int, label: str):
    pass


def qa_spec_mismatch(count: Var[int], name: Var[str]) -> tuple[Var[str], Var[int]]:
    return name, count


def qa_spec_match(amount: Var[int], label: Var[str]) -> tuple[Var[int], Var[str]]:
    return amount, label


class TestEventCallEventHandlerDefUsePairsQA:
    def test_event_call_event_handler_def_use_pairs_case(self):
        qa_handler.__qualname__ = "qa_handler"
        handler = EventHandler(fn=qa_handler, state_full_name="QAState")

        event_spec = call_event_handler(
            handler,
            [qa_spec_mismatch, qa_spec_match],
            key="on_change",
        )

        assert len(event_spec.args) == 2
        assert format.format_event(event_spec) == 'Event("QAState.qa_handler", {amount:_name,label:_count})'

