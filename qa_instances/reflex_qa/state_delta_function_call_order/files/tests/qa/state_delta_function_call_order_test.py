from __future__ import annotations

from reflex.state import BaseState


class DeltaOrderState(BaseState):
    count: int = 1
    label: str = "idle"
    note: str = "start"


class TestStateDeltaFunctionCallOrderQA:
    def test_state_delta_function_call_order_case(self):
        state = DeltaOrderState(_reflex_internal_init=True)
        state.count = 5
        state.label = "done"

        delta = state.get_delta()

        subdelta = next(iter(delta.values()))
        assert subdelta == {"count": 5, "label": "done"}
