#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/libqtile/backend/x11/core.py"
TARGET_FUNCS = {
    "libqtile.backend.x11.core._xpoll",
    "libqtile.backend.x11.core.Core._xpoll",
}

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/backend/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
)


def extract_covered_lines(trace_text: str) -> list[int]:
    covered: set[int] = set()

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if m.group("path") != TARGET_PATH:
            continue
        if m.group("func") not in TARGET_FUNCS:
            continue
        if m.group("event") != "line":
            continue
        covered.add(int(m.group("lineno")))

    return sorted(covered)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "backend_x11_core_direct_xpoll_line_coverage_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "backend_x11_core_direct_xpoll_line_coverage_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    covered_lines = extract_covered_lines(trace_text)

    qa = {
        "question_kind": "M1_IntraProceduralCFG",
        "question": (
            "Run the full test suite in "
            "`tests/qa/backend_x11_core_direct_xpoll_line_coverage_suite_test.py` "
            "(all tests in that file, 11 tests total). Focus only on "
            "`libqtile/backend/x11/core.py`, function "
            "`libqtile.backend.x11.core.Core._xpoll` (lines 308-367). "
            "The suite calls `_xpoll()` directly with synthetic X11 event streams that "
            "exercise motion-event deferral, ignored event types, order-sensitive dispatch, "
            "recoverable X/render errors, and disconnect-vs-non-disconnect exception paths. "
            "Which exact line numbers in the target function are covered at least once by "
            "this suite? Return a JSON object with exactly one key `covered_lines`, where "
            "the value is a sorted list of unique integers in ascending order: "
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
