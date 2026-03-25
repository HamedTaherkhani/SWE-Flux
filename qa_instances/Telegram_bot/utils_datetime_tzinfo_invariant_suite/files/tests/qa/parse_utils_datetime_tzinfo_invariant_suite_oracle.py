#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/_utils/datetime.py"
TARGET_FUNC = "telegram._utils.datetime.to_float_timestamp"
TARGET_LINE = 145
TARGET_VAR = "aware_datetime"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _parse_locals(raw_line: str) -> dict[str, object]:
    marker = " locals="
    index = raw_line.find(marker)
    if index < 0:
        return {}
    raw_locals = raw_line[index + len(marker) :].strip()
    try:
        parsed = ast.literal_eval(raw_locals)
    except (SyntaxError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _tzinfo_is_none_from_repr(value_repr: object) -> bool | None:
    if not isinstance(value_repr, str):
        return None
    # tracer logs repr(obj) as string; for datetime repr, tz-aware objects contain "tzinfo="
    if not value_repr.startswith("datetime.datetime("):
        return None
    return "tzinfo=" not in value_repr


def extract_invariant(trace_text: str) -> dict[str, bool]:
    seen_truth_values: set[bool] = set()

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if (
            m.group("path") != TARGET_PATH
            or m.group("func") != TARGET_FUNC
            or m.group("event") != "line"
            or int(m.group("lineno")) != TARGET_LINE
        ):
            continue

        locals_dict = _parse_locals(raw_line)
        if TARGET_VAR not in locals_dict:
            continue

        parsed = _tzinfo_is_none_from_repr(locals_dict[TARGET_VAR])
        if parsed is not None:
            seen_truth_values.add(parsed)

    invariant_exists = len(seen_truth_values) == 1 and bool(seen_truth_values)
    return {"invariant_exists": invariant_exists}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "utils_datetime_tzinfo_invariant_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "utils_datetime_tzinfo_invariant_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_invariant(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in "
            "`tests/qa/utils_datetime_tzinfo_invariant_suite_test.py` "
            "(all test methods in class `TestUtilsDatetimeTzinfoInvariantSuiteQA`, 18 tests). "
            "Focus on `telegram/_utils/datetime.py`, function "
            "`telegram._utils.datetime.to_float_timestamp`. At line `145` "
            "(`if aware_datetime.tzinfo is None:`), consider the local variable "
            "`aware_datetime`. Across all evaluations of this line over the full suite, "
            "is the property `aware_datetime.tzinfo is None` an invariant property? "
            "Return JSON as `{\\\"invariant_exists\\\": <bool>}` where `true` means invariant "
            "holds and `false` means it does not hold."
        ),
        "template_answer": {
            "invariant_exists": "bool"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
