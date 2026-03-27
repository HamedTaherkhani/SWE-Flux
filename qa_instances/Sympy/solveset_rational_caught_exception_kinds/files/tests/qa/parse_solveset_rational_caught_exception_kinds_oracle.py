#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/sympy/solvers/solveset\.py:(?P<lineno>\d+) "
    r"(?P<func>sympy\.solvers\.solveset\._solve_as_rational) "
    r"event=exception exc=(?P<exc>[^:]+): ",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    seen = []
    for m in EXC_RE.finditer(trace_text):
        kind = m.group("exc").strip()
        if kind not in seen:
            seen.append(kind)

    if not seen:
        raise ValueError("Could not find exception events for _solve_as_rational in trace log.")

    return {"caught_exception_kinds": seen}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/solveset_rational_caught_exception_kinds/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/solveset_rational_caught_exception_kinds/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "abnormal_behavior_prediction",
        "question": (
            "Use `tests/qa/solveset_rational_caught_exception_kinds_test.py`, class "
            "`TestSolvesetRationalCaughtExceptionKindsQA`, method "
            "`test_solveset_rational_caught_exception_kinds_case`. "
            "The list comprehension on line 15 evaluates `solveset(eq, x, S.Complexes)` for the two equations defined in lines 10-13. "
            "This indirectly enters `sympy/solvers/solveset.py::_solve_as_rational` (defined at line 773). "
            "In `_solve_as_rational`, the internal handling around lines 778-787 catches exceptions while trying to solve the numerator as a polynomial. "
            "What are the exact kinds of exceptions that are caught internally during this test execution, in first-seen order?"
        ),
        "template_answer": {
            "caught_exception_kinds": ["str"]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
