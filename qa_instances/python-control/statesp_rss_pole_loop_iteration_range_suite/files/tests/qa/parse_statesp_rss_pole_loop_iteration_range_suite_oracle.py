#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TARGET_FUNC = "control.statesp._rss_generate"
TARGET_FILE = "/testbed/control/statesp.py"
LOOP_BODY_LINE = 2499

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/control/(?!tests/)[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
)


def extract_iteration_range(trace_text: str) -> dict:
    active_depth = 0
    current_count = 0
    counts: list[int] = []

    for raw_line in trace_text.splitlines():
        match = TRACE_RE.match(raw_line)
        if not match:
            continue

        path = match.group("path")
        lineno = int(match.group("lineno"))
        func = match.group("func")
        event = match.group("event")

        if event == "call" and func == TARGET_FUNC:
            active_depth += 1
            if active_depth == 1:
                current_count = 0
            continue

        if active_depth > 0 and event == "line" and path == TARGET_FILE:
            if func == TARGET_FUNC and lineno == LOOP_BODY_LINE:
                current_count += 1

        if active_depth > 0 and func == TARGET_FUNC and event in {"return", "exception"}:
            active_depth = max(0, active_depth - 1)
            if active_depth == 0:
                counts.append(current_count)
                current_count = 0

    if not counts:
        raise ValueError("No _rss_generate loop executions were observed.")

    return {
        "min_iterations": min(counts),
        "max_iterations": max(counts),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "statesp_rss_pole_loop_iteration_range_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "statesp_rss_pole_loop_iteration_range_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_iteration_range(trace_text)

    qa = {
        "question_kind": "M3_Loops",
        "question": (
            "Run the full test suite in "
            "`tests/qa/statesp_rss_pole_loop_iteration_range_suite_test.py` "
            "(all test methods in its 10 test classes). The tests import the "
            "public generators directly with `from control.statesp import drss, "
            "rss`; these calls reach the private helper "
            "`control.statesp._rss_generate`. Focus on the first pole-generation "
            "loop in `control/statesp.py` inside `_rss_generate`: the loop "
            "header is line 2498, `while i < states:`, and one loop iteration "
            "is counted each time execution reaches the first body statement "
            "on line 2499, `if rand() < pRepeat and i != 0 and i != states - 1:`. "
            "This is not the later loop that builds matrix `A`, and not the "
            "retry loops for `T`, `Bmask`, or `Cmask`. Count this loop separately "
            "for each invocation of `_rss_generate` caused by the test suite, "
            "including invocations reached through `drss`. What are the minimum "
            "and maximum numbers of iterations performed by this specific loop "
            "across all suite executions? Return only `min_iterations` and "
            "`max_iterations`."
        ),
        "template_answer": {
            "min_iterations": "int",
            "max_iterations": "int",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(
        json.dumps(qa, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
