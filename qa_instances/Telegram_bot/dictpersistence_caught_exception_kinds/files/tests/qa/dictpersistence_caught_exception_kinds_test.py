import json

import pytest

from telegram.ext import DictPersistence


class TestDictPersistenceCaughtExceptionKindsQA:
    def test_dictpersistence_caught_exception_kinds_case(self):
        base_entries = [
            ("aa", "not-a-float", {"k": 1}),
            ("bb", "still-not-a-float", {"k": 2}),
        ]

        malformed_float_payload = json.dumps([
            [base_entries[(len(base_entries) + 1) % len(base_entries)]],
            {"meta": "x"},
        ])

        malformed_index_payload = json.dumps([
            [
                [
                    "cc",
                    str((sum(ord(ch) for ch in "index-trigger") % 17) + 0.125),
                    {"z": 9},
                ]
            ]
        ])

        payloads = [malformed_float_payload, malformed_index_payload]
        for raw_callback_json in payloads:
            with pytest.raises(Exception):
                DictPersistence(callback_data_json=raw_callback_json)
