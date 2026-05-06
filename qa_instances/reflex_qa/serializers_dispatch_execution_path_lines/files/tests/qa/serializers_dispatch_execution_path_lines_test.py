from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from reflex.base import Base
from reflex.utils.serializers import can_serialize, has_serializer, serialize


class DispatchStatus(Enum):
    READY = "ready"
    DONE = "done"


class DispatchPayload(Base):
    name: str
    count: int


class TestSerializersDispatchExecutionPathLinesQA:
    def test_serializers_dispatch_execution_path_lines_case(self):
        payload = DispatchPayload(name="alpha", count=3)
        checked = (
            has_serializer(type(payload), dict),
            can_serialize(tuple, list),
        )

        serialized_payload, payload_type = serialize(payload, get_type=True)
        serialized_path, path_type = serialize(Path("assets/report.json"), get_type=True)
        serialized_time, time_type = serialize(
            datetime(2024, 2, 3, 4, 5, 6), get_type=True
        )
        serialized_status, status_type = serialize(DispatchStatus.READY, get_type=True)
        serialized_tuple, tuple_type = serialize(("left", "right"), get_type=True)

        assert checked == (True, True)
        assert serialized_payload == {"name": "alpha", "count": 3}
        assert payload_type is dict
        assert serialized_path == "assets/report.json"
        assert path_type is str
        assert serialized_time == "2024-02-03 04:05:06"
        assert time_type is str
        assert serialized_status == "ready"
        assert status_type is str
        assert serialized_tuple == ["left", "right"]
        assert tuple_type is list
