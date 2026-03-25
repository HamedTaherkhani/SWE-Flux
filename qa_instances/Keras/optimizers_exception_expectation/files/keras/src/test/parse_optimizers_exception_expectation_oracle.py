#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def extract_value(trace_text: str, key: str) -> str:
    pattern = re.compile(rf"'{re.escape(key)}':\s*\"([^\"]+)\"|'{re.escape(key)}':\s*'([^']+)'")
    matches = pattern.findall(trace_text)
    if not matches:
        raise ValueError(f"Could not find `{key}` in trace log.")
    last = matches[-1]
    value = last[0] or last[1]
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        value = value[1:-1]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_exception_expectation/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_exception_expectation/oracle.json",
    )
    args = parser.parse_args()

    trace_path = Path(args.trace_log)
    trace_text = trace_path.read_text(encoding="utf-8")

    exception_type = extract_value(trace_text, "caught_exception_type")
    exception_message = extract_value(trace_text, "caught_exception_message")

    qa = {
        "question_kind": "abnormal_behavior_prediction",
        "question": (
            "Use `keras/src/test/optimizers/optimizers_exception_expectation_test.py`, "
            "class `OptimizersExceptionExpectationQATest`, method "
            "`test_expected_exception_type_and_pattern`. In this method, "
            "`optimizers.SGD(learning_rate=0.1, clipnorm=1.0, clipvalue=0.2)` "
            "is executed and any raised exception is captured into "
            "`caught_exception_type` and `caught_exception_message`. "
            "What exception signature (type and message) does this project call raise?"
        ),
        "oracle_answer": {
            "exception_type": exception_type,
            "exception_message": exception_message,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
