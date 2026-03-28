import json

import pytest

from telegram.request._baserequest import BaseRequest


class SimulatedRequest(BaseRequest):
    def __init__(self, scenarios, selected_index):
        self._scenarios = scenarios
        self._selected_index = selected_index

    @property
    def read_timeout(self):
        return 5.0

    async def initialize(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def do_request(
        self,
        url: str,
        method: str,
        request_data=None,
        read_timeout=BaseRequest.DEFAULT_NONE,
        write_timeout=BaseRequest.DEFAULT_NONE,
        connect_timeout=BaseRequest.DEFAULT_NONE,
        pool_timeout=BaseRequest.DEFAULT_NONE,
    ):
        status_code, payload_dict = self._scenarios[self._selected_index]
        payload = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return status_code, payload


class TestBaseRequestWrapperExceptionKindQA:
    @pytest.mark.asyncio
    async def test_baserequest_wrapper_exception_kind_case(self):
        scenarios = [
            (403, {"ok": False, "description": "forbidden branch"}),
            (401, {"ok": False, "description": "unauthorized branch"}),
            (
                400,
                {
                    "ok": False,
                    "description": "bad request branch",
                    "parameters": {"retry_after": 9},
                },
            ),
            (
                400,
                {
                    "ok": False,
                    "description": "bad request branch",
                    "parameters": {"migrate_to_chat_id": -100444222111},
                },
            ),
        ]

        seed_text = "omega|sigma|delta|kappa"
        weighted_sum = sum((idx + 2) * ord(ch) for idx, ch in enumerate(seed_text))
        selected_index = (weighted_sum // 8) % len(scenarios)

        request = SimulatedRequest(scenarios=scenarios, selected_index=selected_index)

        with pytest.raises(Exception):
            await request.post(url="https://api.telegram.org/bot123:ABC/someMethod")
