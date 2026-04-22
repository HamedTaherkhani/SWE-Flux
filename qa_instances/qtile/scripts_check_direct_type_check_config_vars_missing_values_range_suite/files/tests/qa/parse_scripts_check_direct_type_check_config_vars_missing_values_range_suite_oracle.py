#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_FUNC = "libqtile.scripts.check.type_check_config_vars"
TARGET_PATH = "/testbed/libqtile/scripts/check.py"
TARGET_MISSING_LINE = 61

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/libqtile/scripts/check\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>\w+).*? locals=(?P<locals>\{.*\})$"
)


def extract_missing_lengths(trace_text: str) -> list[int]:
    values: list[int] = []
    current_last: int | None = None

    for line in trace_text.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue

        if m.group("path") != TARGET_PATH:
            continue
        if m.group("func") != TARGET_FUNC:
            continue

        try:
            local_map = ast.literal_eval(m.group("locals"))
        except Exception:
            continue

        event = m.group("event")
        lineno = int(m.group("lineno"))

        if event == "call":
            current_last = None
            continue

        if event == "line" and lineno == TARGET_MISSING_LINE and "missing_vars" in local_map:
            try:
                missing_list = ast.literal_eval(local_map["missing_vars"])
                current_last = len(missing_list)
            except Exception:
                pass
            continue

        if event in {"return", "exception"}:
            if current_last is not None:
                values.append(current_last)
                current_last = None
            continue

    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "scripts_check_direct_type_check_config_vars_missing_values_range_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "scripts_check_direct_type_check_config_vars_missing_values_range_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    lengths = extract_missing_lengths(trace_text)

    if not lengths:
        raise RuntimeError("No observed values found for variable 'missing_vars'.")

    qa = {
        "question_kind": "value_range_analysis",
        "question": (
            "Use the full test suite in "
            "`tests/qa/scripts_check_direct_type_check_config_vars_missing_values_range_suite_test.py` "
            "(all generated test cases in class "
            "`TestScriptsCheckDirectTypeCheckConfigVarsMissingValuesRangeSuiteQA`, 15 tests). "
            "Focus only on function `libqtile.scripts.check.type_check_config_vars` in file "
            "`libqtile/scripts/check.py`. "
            "Use local variable `missing_vars` at line `61` (the loop over stubtest output). "
            "For each invocation, take the final value reached by `missing_vars` before the function "
            "returns or raises, and compute `len(missing_vars)`. Across the full suite, what is the "
            "inclusive numeric range of `len(missing_vars)`? Return JSON with exactly these keys: "
            "`variable`, `min_value`, `max_value`."
        ),
        "template_answer": {
            "min_value": "int",
            "max_value": "int",
        },
        "oracle_answer": {
            "variable": "len(missing_vars)",
            "min_value": min(lengths),
            "max_value": max(lengths),
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
