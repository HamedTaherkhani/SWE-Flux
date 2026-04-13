#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/ext/_handlers/conversationhandler.py"
TARGET_FUNC = "telegram.ext._handlers.conversationhandler.ConversationHandler.check_update"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
)


def extract_covered_lines(trace_text: str) -> list[int]:
    covered: set[int] = set()

    for raw_line in trace_text.splitlines():
        match = EVENT_RE.match(raw_line)
        if not match:
            continue
        if match.group("path") != TARGET_PATH:
            continue
        if match.group("func") != TARGET_FUNC:
            continue
        if match.group("event") != "line":
            continue

        covered.add(int(match.group("lineno")))

    return sorted(covered)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "conversationhandler_check_update_line_coverage_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "conversationhandler_check_update_line_coverage_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    covered_lines = extract_covered_lines(trace_text)

    qa = {
        "question_kind": "coverage_prediction",
        "question": (
            "Run the full test suite in `tests/qa/conversationhandler_check_update_line_coverage_suite_test.py` "
            "(all tests in that file, 18 tests total). Focus only on "
            "`telegram/ext/_handlers/conversationhandler.py`, function "
            "`telegram.ext._handlers.conversationhandler.ConversationHandler.check_update` "
            "(lines 707-796). Count a line as covered only if the trace contains an `event=line` "
            "entry whose file path and fully qualified function name exactly match this target "
            "function. Do not count matching `event=call`, `event=return`, or `event=exception` "
            "entries, so the function entry/call line is included only if it also appears as an "
            "`event=line` entry. Which exact line numbers in this target function are covered at "
            "least once by this suite? Return a JSON object with exactly one key `covered_lines`, "
            "where the value is a sorted list of unique integers in ascending order: "
            "`{\"covered_lines\": [<int>, ...]}`."
        ),
        "template_answer": {
            "covered_lines": [],
        },
        "oracle_answer": {
            "covered_lines": covered_lines,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
