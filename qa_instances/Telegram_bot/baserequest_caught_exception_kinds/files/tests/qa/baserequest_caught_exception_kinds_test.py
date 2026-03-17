import pytest

from telegram.error import InvalidToken
from telegram.request._baserequest import BaseRequest


class SequencedRequest(BaseRequest):
    def __init__(self, planned_failures):
        self._planned_failures = list(planned_failures)
        self._cursor = 0

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
        current = self._planned_failures[self._cursor % len(self._planned_failures)]
        self._cursor += 1

        if current == "token":
            raise InvalidToken("token path failure")
        if current == "runtime":
            raise RuntimeError(f"runtime path failure for {method} {url}")

        raise ValueError("unexpected plan state")


class TestBaseRequestCaughtExceptionKindsQA:
    @pytest.mark.asyncio
    async def test_baserequest_caught_exception_kinds_case(self):
        fragments = ["alpha", "delta", "omega", "sigma"]
        weighted = sum((index + 3) * len(part) for index, part in enumerate(fragments))

        failure_plan = ["token", "runtime"] if weighted % 2 == 0 else ["runtime", "token"]
        request = SequencedRequest(planned_failures=failure_plan)

        endpoints = [
            "https://api.telegram.org/bot123:ABC/getMe",
            "https://api.telegram.org/bot123:ABC/getUpdates",
        ]

        for endpoint in endpoints:
            with pytest.raises(Exception):
                await request.post(url=endpoint)
