#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TARGET_FUNC = "control.freqplot._compute_curve_offset"
TARGET_FILE = "/testbed/control/freqplot.py"
LOOP_BODY_LINE = 2102

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

        if active_depth > 0 and event == "line":
            if path == TARGET_FILE and func == TARGET_FUNC and lineno == LOOP_BODY_LINE:
                current_count += 1

        if active_depth > 0 and func == TARGET_FUNC and event in {"return", "exception"}:
            active_depth = max(0, active_depth - 1)
            if active_depth == 0:
                counts.append(current_count)
                current_count = 0

    if not counts:
        raise ValueError("No _compute_curve_offset executions were observed.")

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
            "freqplot_curve_offset_loop_iteration_range_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "freqplot_curve_offset_loop_iteration_range_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    answer = extract_iteration_range(Path(args.trace_log).read_text(encoding="utf-8"))

    qa = {
        "question_kind": "M3_Loops",
        "question": (
            "Run the full test suite in "
            "`tests/qa/freqplot_curve_offset_loop_iteration_range_suite_test.py` "
            "(all test methods in its 10 test classes). The tests import the "
            "target directly with `from control.freqplot import "
            "_compute_curve_offset`. Focus on the outer scan loop in "
            "`control/freqplot.py` inside `control.freqplot._compute_curve_offset`: "
            "the loop header is line 2100, `while i < resp.size:`, and one "
            "iteration is counted each time execution reaches line 2102, "
            "`while i < resp.size and mask[i]:`, which is the first statement "
            "inside that outer loop. Do not count the nested regular-segment "
            "loop at lines 2102-2107 or the nested scaled-segment loop at "
            "lines 2117-2122 as separate target loops. Count the target outer "
            "loop separately for each invocation caused by the suite. What are "
            "the minimum and maximum numbers of iterations performed by this "
            "specific loop across all suite executions? Return only "
            "`min_iterations` and `max_iterations`."
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
