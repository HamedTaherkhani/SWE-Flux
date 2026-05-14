#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/_utils/markup.py"
TARGET_FUNC = "telegram._utils.markup.check_keyboard_type"
TARGET_LINE = 47
TARGET_VAR = "inner"

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


def _is_str_value_repr(value_repr: object) -> bool:
    if not isinstance(value_repr, str):
        return False
    try:
        decoded = ast.literal_eval(value_repr)
    except (SyntaxError, ValueError):
        return False
    return isinstance(decoded, str)


def extract_invariant(trace_text: str) -> dict[str, bool]:
    seen_inner = False
    all_inner_are_str = True

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

        seen_inner = True
        if not _is_str_value_repr(locals_dict[TARGET_VAR]):
            all_inner_are_str = False

    invariant_holds = seen_inner and all_inner_are_str
    return {"invariant_exists": invariant_holds}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "markup_inner_string_invariant_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "markup_inner_string_invariant_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_invariant(trace_text)

    qa = {
        "question_kind": "M7_Invariants",
        "question": (
            "Use the full test suite in `tests/qa/markup_inner_string_invariant_suite_test.py` "
            "(all test methods in class `TestMarkupInnerStringInvariantSuiteQA`, 16 tests). "
            "Focus on `telegram/_utils/markup.py`, function "
            "`telegram._utils.markup.check_keyboard_type`. At line `47` "
            "(`if isinstance(inner, Sequence) and not isinstance(inner, str):`), "
            "consider the local variable `inner`. "
            "Across all evaluations of this line over the full suite, is the property "
            "`inner is a str` an invariant property? Return JSON as "
            "`{\\\"invariant_exists\\\": <bool>}` where `true` means invariant holds and "
            "`false` means it does not hold."
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
