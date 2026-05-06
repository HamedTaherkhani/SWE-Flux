from __future__ import annotations

from typing import Any

import pytest

import reflex as rx
from reflex.istate.data import RouterData
from reflex.state import BaseState


class PathPayload(rx.Base):
    name: str
    delta: int


class GeneratorPathState(BaseState):
    count: int = 1
    tags_seen: list[str] = []
    pair_total: int = 0
    history: list[str] = []

    @rx.var
    def score(self) -> int:
        return self.count + self.pair_total + len(self.tags_seen)

    def record(self, marker: str):
        self.history.append(marker)

    def complex_generator(
        self,
        amount: int,
        tags: set[str],
        pair: tuple[int, int],
        payload: PathPayload,
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


class TestStateGeneratorProcessEventExecutionPathLinesQA:
    @pytest.mark.asyncio
    async def test_state_generator_process_event_execution_path_lines_case(self):
        state = GeneratorPathState()
        router_data = {
            "token": "qa-token",
            "sid": "qa-sid",
            "client_ip": "203.0.113.25",
            "query": {"mode": "path"},
        }
        state.router_data = router_data
        state.router = RouterData(router_data)
        state._clean()

        handler = GeneratorPathState.event_handlers["complex_generator"]
        payload: dict[str, Any] = {
            "amount": "4",
            "tags": ["zeta", "alpha", "zeta"],
            "pair": [3, 8],
            "payload": {"name": "mix", "delta": 5, "ignored": "discarded"},
        }

        updates = []
        async for update in state._process_event(
            handler=handler,
            state=state,
            payload=payload,
        ):
            updates.append(update)

        assert len(updates) == 4
        assert updates[-1].final is True
        assert state.count == 7
        assert state.history[-1] == "returning"
