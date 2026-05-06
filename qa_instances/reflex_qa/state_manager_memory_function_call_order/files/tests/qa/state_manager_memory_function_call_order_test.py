from __future__ import annotations

import pytest

from reflex.state import BaseState, StateManagerMemory


class ManagerOrderState(BaseState):
    total: int = 0


class TestStateManagerMemoryFunctionCallOrderQA:
    @pytest.mark.asyncio
    async def test_state_manager_memory_function_call_order_case(self):
        manager = StateManagerMemory(state=ManagerOrderState)
        manager.states = {}
        manager._states_locks = {}

        async with manager.modify_state("client-token_child") as state:
            state.total = 9

        same_state = await manager.get_state("client-token_other")
        await manager.set_state("client-token", same_state)

        assert isinstance(same_state, ManagerOrderState)
        assert list(manager.states) == ["client-token"]
