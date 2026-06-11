#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


TARGET_FUNC = "control.timeresp.forced_response"
TARGET_FILE = "/testbed/control/timeresp.py"
TARGET_LINE = 1246
TARGET_VARIABLE = "inc"

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/control/(?!tests/)[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
    r".*? locals=(?P<locals>\{.*\})$"
)


def extract_value_range(trace_text: str) -> dict:
    values: list[int] = []

    for raw_line in trace_text.splitlines():
        match = TRACE_RE.match(raw_line)
        if not match:
            continue

        if (
            match.group("path") != TARGET_FILE
            or int(match.group("lineno")) != TARGET_LINE
            or match.group("func") != TARGET_FUNC
            or match.group("event") != "line"
        ):
            continue

        locals_dict = ast.literal_eval(match.group("locals"))
        if TARGET_VARIABLE not in locals_dict:
            raise ValueError(
                f"Line {TARGET_LINE} did not contain local {TARGET_VARIABLE!r}."
            )
        values.append(int(locals_dict[TARGET_VARIABLE]))

    if len(values) != 10:
        raise ValueError(
            f"Expected 10 observed {TARGET_VARIABLE!r} values at line "
            f"{TARGET_LINE}, observed {len(values)}: {values!r}."
        )

    return {
        "min_value": min(values),
        "max_value": max(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "timeresp_forced_response_inc_value_range_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "timeresp_forced_response_inc_value_range_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    answer = extract_value_range(Path(args.trace_log).read_text(encoding="utf-8"))

    qa = {
        "question_kind": "M3_ProgramState",
        "question": (
            "Run the full test suite in "
            "`tests/qa/timeresp_forced_response_inc_value_range_suite_test.py` "
            "(all 10 test methods in `TestForcedResponseStateRangeQA`, in "
            "file order: `test_case_01`, `test_case_02`, `test_case_03`, "
            "`test_case_04`, `test_case_05`, `test_case_06`, `test_case_07`, "
            "`test_case_08`, `test_case_09`, and `test_case_10`). The tests "
            "import the target directly with `from control.timeresp import "
            "forced_response` and construct discrete systems with "
            "`from control.statesp import StateSpace`. Focus on the local "
            "variable `inc` inside `control.timeresp.forced_response`. It is "
            "assigned on line 1245 as `inc = int(round(dt / sys_dt))` in the "
            "discrete-time non-interpolating branch, and its value is visible "
            "at line 1246, `tout = T`. Across all executions of line 1246 "
            "caused by this suite, what are the minimum and maximum values "
            "reached by `inc`? Return only `min_value` and `max_value` as "
            "numbers."
        ),
        "template_answer": {
            "min_value": "number",
            "max_value": "number",
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
