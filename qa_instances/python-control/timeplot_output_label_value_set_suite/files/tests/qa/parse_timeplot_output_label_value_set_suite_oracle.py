#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


TARGET_FUNC = "control.timeplot.time_response_plot"
TARGET_FILE = "/testbed/control/timeplot.py"
TARGET_LINE = 430
TARGET_VARIABLE = "label"

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/control/(?!tests/)[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
    r".*? locals=(?P<locals>\{.*\})$"
)


def extract_value_set(trace_text: str) -> dict:
    values: set[str] = set()
    current_label: str | None = None

    for raw_line in trace_text.splitlines():
        match = TRACE_RE.match(raw_line)
        if not match:
            continue
        if (
            match.group("path") != TARGET_FILE
            or match.group("func") != TARGET_FUNC
            or match.group("event") != "line"
        ):
            continue
        locals_dict = ast.literal_eval(match.group("locals"))
        if TARGET_VARIABLE in locals_dict:
            current_label = ast.literal_eval(locals_dict[TARGET_VARIABLE])
        if int(match.group("lineno")) == TARGET_LINE:
            if current_label is None:
                raise ValueError("Reached target line before observing label.")
            values.add(current_label)

    if not values:
        raise ValueError("No label values observed.")
    return {"unique_values": sorted(values)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default="/testbed/logs/qa_instances/timeplot_output_label_value_set_suite/trace.log")
    parser.add_argument("--out", default="/testbed/logs/qa_instances/timeplot_output_label_value_set_suite/oracle.json")
    args = parser.parse_args()

    answer = extract_value_set(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "M3_ProgramState",
        "question": (
            "Run the full test suite in "
            "`tests/qa/timeplot_output_label_value_set_suite_test.py` (all 10 "
            "test methods in `TestTimePlotLabelValueSetQA`, in file order: "
            "`test_case_01`, `test_case_02`, `test_case_03`, `test_case_04`, "
            "`test_case_05`, `test_case_06`, `test_case_07`, `test_case_08`, "
            "`test_case_09`, and `test_case_10`). The tests import the target "
            "directly with `from control.timeplot import time_response_plot` "
            "and construct response objects with `from control.timeresp import "
            "TimeResponseData`. Focus on the local variable `label` inside "
            "`control.timeplot.time_response_plot` at line 430, where the "
            "output plotting call passes `label=label`. Across all executions "
            "of line 430 caused by this suite, what is the set of unique string "
            "values held by `label`? Return only `unique_values` as a "
            "lexicographically sorted list of strings."
        ),
        "template_answer": {"unique_values": ["str"]},
        "oracle_answer": answer,
    }
    Path(args.out).write_text(
        json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
