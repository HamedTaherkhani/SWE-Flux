#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TARGET_FUNC = "control.rlocus._default_gains"
TARGET_FILE = "/testbed/control/rlocus.py"
LOOP_BODY_LINE = 299

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
        raise ValueError("No _default_gains executions were observed.")

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
            "rlocus_default_gains_loop_iteration_range_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "rlocus_default_gains_loop_iteration_range_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    answer = extract_iteration_range(Path(args.trace_log).read_text(encoding="utf-8"))

    qa = {
        "question_kind": "M2_Loops",
        "question": (
            "Run the full test suite in "
            "`tests/qa/rlocus_default_gains_loop_iteration_range_suite_test.py` "
            "(all test methods in its 10 test classes). The tests import the "
            "target directly with `from control.rlocus import _default_gains`. "
            "Focus on the adaptive root-locus refinement loop in "
            "`control/rlocus.py` inside `control.rlocus._default_gains`: the "
            "loop header is line 298, `while len(indexes_too_far) > 0 and "
            "kvect.size < 5000:`, and one loop iteration is counted each time "
            "execution reaches line 299, `for counter, index in "
            "enumerate(indexes_too_far):`, the first statement inside that "
            "while loop. Do not count iterations of the nested `for` loop over "
            "`indexes_too_far`, and do not count helper loops in `_RLFindRoots`, "
            "`_RLSortRoots`, `_indexes_filt`, `_break_points`, or `_k_max`. "
            "Count the target loop separately for each invocation caused by "
            "the suite. What are the minimum and maximum numbers of iterations "
            "performed by this specific loop across all suite executions? "
            "Return only `min_iterations` and `max_iterations`."
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
