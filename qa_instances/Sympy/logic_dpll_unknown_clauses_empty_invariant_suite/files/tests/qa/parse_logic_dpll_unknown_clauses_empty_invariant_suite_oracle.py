#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/sympy/logic/algorithms/dpll.py"
TARGET_FUNC = "sympy.logic.algorithms.dpll.dpll_int_repr"
TARGET_LINE = 129
TARGET_VAR = "val"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/logic/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _parse_locals(raw_line: str) -> dict[str, object]:
    marker = " locals="
    index = raw_line.find(marker)
    if index < 0:
        return {}
    raw_locals = raw_line[index + len(marker):].strip()
    try:
        parsed = ast.literal_eval(raw_locals)
    except (SyntaxError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _decode_local_value(value_repr: object):
    if not isinstance(value_repr, str):
        return value_repr
    try:
        return ast.literal_eval(value_repr)
    except (SyntaxError, ValueError):
        return value_repr


def extract_invariant(trace_text: str) -> dict[str, bool]:
    seen_any = False
    property_holds_for_all = True

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

        seen_any = True
        val = _decode_local_value(locals_dict[TARGET_VAR])
        if val is not False:
            property_holds_for_all = False

    invariant_exists = seen_any and property_holds_for_all
    return {"invariant_exists": invariant_exists}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "logic_dpll_unknown_clauses_empty_invariant_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "logic_dpll_unknown_clauses_empty_invariant_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_invariant(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in "
            "`tests/qa/logic_dpll_unknown_clauses_empty_invariant_suite_test.py` "
            "(all generated test cases in class "
            "`TestLogicDpllUnknownClausesEmptyInvariantSuiteQA`, 24 tests). "
            "Focus on `sympy/logic/algorithms/dpll.py`, function "
            "`sympy.logic.algorithms.dpll.dpll_int_repr`. "
            "At line `129` (`if val is False:`), consider local variable `val`. "
            "Across all evaluations of this line over the full suite (including recursive "
            "invocations), is the property `val is False` an invariant property? "
            "Return JSON as `{\\\"invariant_exists\\\": <bool>}` where `true` means "
            "the property holds for every evaluation and `false` means it does not hold."
        ),
        "template_answer": {
            "invariant_exists": "bool"
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
