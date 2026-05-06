from __future__ import annotations

import json
from typing import Any

import pytest

import reflex as rx
from reflex.event import Event
from reflex.istate.data import RouterData
from reflex.state import BaseState, StateUpdate


class ProcessPayload(rx.Base):
    """Payload object used to exercise dict-to-Base conversion."""

    name: str
    delta: int


class ProcessEventDirectState(BaseState):
    """State used by the direct BaseState._process_event output probe."""

    count: int = 0
    tags_seen: list[str] = []
    pair_total: int = 0
    history: list[str] = []

    @rx.var
    def score(self) -> int:
        return self.count + self.pair_total + len(self.tags_seen)

    @rx.var
    def status(self) -> str:
        return f"{self.count}:{len(self.history)}:{self.score}"

    def record(self, marker: str):
        self.history.append(marker)

    def complex_generator(
        self,
        amount: int,
        tags: set[str],
        pair: tuple[int, int],
        payload: ProcessPayload,
    ):
        self.count += amount
        self.tags_seen = sorted(tags)
        self.pair_total = sum(pair)
        self.history.append(f"first:{payload.name}:{payload.delta}")
        yield type(self).record("queued_first")

        self.count += payload.delta
        self.history.append(f"second:{len(tags)}:{pair[1]}")
        yield [
            type(self).record("queued_second"),
            rx.console_log(f"count={self.count}"),
        ]

        self.count -= pair[0]
        self.history.append("returning")
        return type(self).record("queued_return")


def _event_to_dict(event: Event) -> dict[str, Any]:
    return {
        "token": event.token,
        "name": event.name,
        "payload": event.payload,
        "router_data": event.router_data,
    }


def _update_to_dict(update: StateUpdate) -> dict[str, Any]:
    return {
        "delta": update.delta,
        "events": [_event_to_dict(event) for event in update.events],
        "final": update.final,
    }


class TestStateProcessEventGeneratorDirectOutputQA:
    @pytest.mark.asyncio
    async def test_state_process_event_generator_direct_output_case(self):
        state = ProcessEventDirectState()
        router_data = {
            "token": "qa-token",
            "sid": "qa-sid",
            "client_ip": "203.0.113.10",
            "query": {"page": "direct"},
        }
        state.router_data = router_data
        state.router = RouterData(router_data)
        state._clean()

        handler = ProcessEventDirectState.event_handlers["complex_generator"]
        payload = {
            "amount": "4",
            "tags": ["zeta", "alpha", "zeta"],
            "pair": [3, 8],
            "payload": {"name": "mix", "delta": 5, "ignored": "kept-by-base"},
        }

        updates = []
        async for update in state._process_event(
            handler=handler,
            state=state,
            payload=payload,
        ):
            updates.append(_update_to_dict(update))

        result = {
            "coerced_payload_after_call": {
                "amount": payload["amount"],
                "tags": sorted(payload["tags"]),
                "pair": list(payload["pair"]),
                "payload_type": type(payload["payload"]).__name__,
                "payload_dict": payload["payload"].dict(),
            },
            "updates": updates,
            "final_state": {
                "count": state.count,
                "tags_seen": state.tags_seen,
                "pair_total": state.pair_total,
                "history": state.history,
                "score": state.score,
                "status": state.status,
                "dirty_vars": sorted(state.dirty_vars),
            },
        }
        print("QA_RESULT_JSON=" + json.dumps(result, sort_keys=True))

        assert len(updates) == 4
        assert updates[-1]["final"] is True
        assert result["final_state"]["count"] == 6
